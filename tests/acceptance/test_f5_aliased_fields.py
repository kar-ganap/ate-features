"""F5: Pydantic aliased-field support in StateGraph.

LangGraph creates channels from `get_type_hints()` which returns Python attribute
names. When a Pydantic model uses Field(alias=...) or alias_generator, the
`_coerce_state(schema, input)` call fails because it passes attribute names but
Pydantic expects aliases (unless populate_by_name=True).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class AliasedState(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_name: str = Field(alias="userName")
    item_count: int = Field(alias="itemCount")


class StrictAliasState(BaseModel):
    """No populate_by_name — Pydantic expects alias only."""

    user_name: str = Field(alias="userName")


class GeneratorAliasState(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda field_name: field_name.replace("_", "-"),
        populate_by_name=True,
    )

    first_name: str
    last_name: str


class MixedState(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plain: str
    aliased_field: str = Field(alias="aliasedField")


def _add_one(current: int, update: int) -> int:
    return current + update


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_aliased_state_compiles(self) -> None:
        """StateGraph with aliased Pydantic model compiles without error."""
        from langgraph.graph import StateGraph

        graph = StateGraph(AliasedState)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        assert compiled is not None

    def test_aliased_state_invoke(self) -> None:
        """StateGraph with aliased Pydantic model can be invoked."""
        from langgraph.graph import StateGraph

        graph = StateGraph(AliasedState)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        result = compiled.invoke({"user_name": "Alice", "item_count": 5})
        assert result["user_name"] == "Alice"
        assert result["item_count"] == 5

    def test_aliased_field_accessible_by_attr_name(self) -> None:
        """Node receives state where aliased fields are accessible by attribute name."""
        from langgraph.graph import StateGraph

        captured = {}

        def capture(state: AliasedState) -> dict:
            captured["user_name"] = state.user_name
            captured["item_count"] = state.item_count
            return {}

        graph = StateGraph(AliasedState)
        graph.add_node("capture", capture)
        graph.set_entry_point("capture")
        graph.set_finish_point("capture")
        compiled = graph.compile()

        compiled.invoke({"user_name": "Bob", "item_count": 10})
        assert captured["user_name"] == "Bob"
        assert captured["item_count"] == 10


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_alias_generator(self) -> None:
        """State with alias_generator compiles and runs."""
        from langgraph.graph import StateGraph

        graph = StateGraph(GeneratorAliasState)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        result = compiled.invoke({"first_name": "Jane", "last_name": "Doe"})
        assert result["first_name"] == "Jane"

    def test_populate_by_name_true(self) -> None:
        """With populate_by_name=True, both alias and attr name work."""
        from langgraph.graph import StateGraph

        graph = StateGraph(AliasedState)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        # Input using attribute names (channels use attr names)
        result = compiled.invoke({"user_name": "X", "item_count": 1})
        assert result["user_name"] == "X"

    def test_mixed_aliased_and_plain_fields(self) -> None:
        """State with a mix of aliased and non-aliased fields."""
        from langgraph.graph import StateGraph

        graph = StateGraph(MixedState)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        result = compiled.invoke({"plain": "hello", "aliased_field": "world"})
        assert result["plain"] == "hello"
        assert result["aliased_field"] == "world"

    def test_node_update_via_alias(self) -> None:
        """Node output using alias name updates state correctly."""
        from langgraph.graph import StateGraph

        def update(state: AliasedState) -> dict:
            return {"user_name": state.user_name.upper()}

        graph = StateGraph(AliasedState)
        graph.add_node("upper", update)
        graph.set_entry_point("upper")
        graph.set_finish_point("upper")
        compiled = graph.compile()

        result = compiled.invoke({"user_name": "alice", "item_count": 1})
        assert result["user_name"] == "ALICE"

    def test_strict_alias_state(self) -> None:
        """State with alias but NO populate_by_name should still compile and run."""
        from langgraph.graph import StateGraph

        graph = StateGraph(StrictAliasState)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        result = compiled.invoke({"user_name": "Test"})
        assert result["user_name"] == "Test"


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_end_to_end_graph_run(self) -> None:
        """Full graph run with aliased state through multiple nodes."""
        from langgraph.graph import END, StateGraph

        def node_a(state: AliasedState) -> dict:
            return {"item_count": state.item_count + 1}

        def node_b(state: AliasedState) -> dict:
            return {"user_name": state.user_name + "!"}

        graph = StateGraph(AliasedState)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.add_edge("b", END)
        compiled = graph.compile()

        result = compiled.invoke({"user_name": "hi", "item_count": 0})
        assert result["user_name"] == "hi!"
        assert result["item_count"] == 1

    def test_checkpoint_round_trip_aliased(self) -> None:
        """Aliased state survives checkpoint serialization round-trip."""
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import StateGraph

        graph = StateGraph(AliasedState)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        memory = InMemorySaver()
        compiled = graph.compile(checkpointer=memory)

        config = {"configurable": {"thread_id": "test-alias"}}
        result = compiled.invoke({"user_name": "Alice", "item_count": 42}, config=config)
        assert result["user_name"] == "Alice"

        # Retrieve checkpoint state
        state = compiled.get_state(config)
        assert state.values["user_name"] == "Alice"
        assert state.values["item_count"] == 42

    def test_aliased_with_reducer(self) -> None:
        """Aliased field with a reducer annotation works correctly."""
        import operator

        class ReducerAliasState(BaseModel):
            model_config = ConfigDict(populate_by_name=True)

            items: Annotated[list[str], operator.add] = Field(
                alias="itemList", default_factory=list
            )
            label: str = Field(alias="labelText", default="")

        from langgraph.graph import StateGraph

        graph = StateGraph(ReducerAliasState)
        graph.add_node("add", lambda s: {"items": ["new"]})
        graph.set_entry_point("add")
        graph.set_finish_point("add")
        compiled = graph.compile()

        result = compiled.invoke({"items": ["existing"], "label": "test"})
        assert "new" in result["items"]
