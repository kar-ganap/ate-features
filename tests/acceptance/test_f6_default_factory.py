"""F6: BinaryOperatorAggregate ignores dataclass default_factory.

BinaryOperatorAggregate.__init__() always calls typ() for the initial
channel value. Dataclass field(default_factory=...) values are completely
ignored — the channel starts at typ() (e.g., list() = []) instead of the
factory output (e.g., ["seed"]).
"""

import operator
from dataclasses import dataclass, field
from typing import Annotated


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_default_factory_list(self) -> None:
        """Dataclass default_factory list value should be channel's initial value."""
        from langgraph.graph import StateGraph

        @dataclass
        class State:
            items: Annotated[list[str], operator.add] = field(default_factory=lambda: ["seed"])

        def appender(state: State) -> dict:
            return {"items": ["added"]}

        graph = StateGraph(State)
        graph.add_node("work", appender)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        # Invoke without providing 'items' — should use default_factory
        result = compiled.invoke({})
        assert result["items"] == ["seed", "added"], (
            f"Expected default_factory ['seed'] + node ['added'], got {result['items']}"
        )

    def test_default_factory_dict(self) -> None:
        """Dataclass default_factory dict value should be channel's initial value."""
        from langgraph.graph import StateGraph

        def merge_dicts(a: dict, b: dict) -> dict:
            return {**a, **b}

        @dataclass
        class State:
            config: Annotated[dict, merge_dicts] = field(default_factory=lambda: {"version": 1})

        def updater(state: State) -> dict:
            return {"config": {"name": "test"}}

        graph = StateGraph(State)
        graph.add_node("work", updater)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert result["config"] == {"version": 1, "name": "test"}, (
            f"Expected merged config, got {result['config']}"
        )

    def test_default_factory_with_accumulation(self) -> None:
        """Factory default accumulates with node output via reducer."""
        from langgraph.graph import StateGraph

        @dataclass
        class State:
            log: Annotated[list[str], operator.add] = field(default_factory=lambda: ["init"])

        def step_1(state: State) -> dict:
            return {"log": ["step_1"]}

        def step_2(state: State) -> dict:
            return {"log": ["step_2"]}

        graph = StateGraph(State)
        graph.add_node("s1", step_1)
        graph.add_node("s2", step_2)
        graph.add_edge("s1", "s2")
        graph.set_entry_point("s1")
        graph.set_finish_point("s2")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert result["log"] == ["init", "step_1", "step_2"], (
            f"Expected ['init', 'step_1', 'step_2'], got {result['log']}"
        )


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_multiple_fields_with_factories(self) -> None:
        """Multiple fields each with different default_factory values."""
        from langgraph.graph import StateGraph

        @dataclass
        class State:
            tags: Annotated[list[str], operator.add] = field(default_factory=lambda: ["base"])
            scores: Annotated[list[int], operator.add] = field(default_factory=lambda: [0])

        def node(state: State) -> dict:
            return {"tags": ["new"], "scores": [10]}

        graph = StateGraph(State)
        graph.add_node("work", node)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert result["tags"] == ["base", "new"]
        assert result["scores"] == [0, 10]

    def test_non_trivial_factory(self) -> None:
        """default_factory returning complex nested structure."""
        from langgraph.graph import StateGraph

        @dataclass
        class State:
            items: Annotated[list[str], operator.add] = field(
                default_factory=lambda: ["alpha", "beta", "gamma"]
            )

        def node(state: State) -> dict:
            return {"items": ["delta"]}

        graph = StateGraph(State)
        graph.add_node("work", node)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert result["items"] == ["alpha", "beta", "gamma", "delta"]

    def test_factory_with_custom_reducer(self) -> None:
        """default_factory with a custom (non-operator) reducer."""
        from langgraph.graph import StateGraph

        def union_reducer(a: list, b: list) -> list:
            return list(set(a) | set(b))

        @dataclass
        class State:
            unique_items: Annotated[list[str], union_reducer] = field(
                default_factory=lambda: ["base"]
            )

        def node(state: State) -> dict:
            # Does NOT include "base" — only factory provides it
            return {"unique_items": ["new", "extra"]}

        graph = StateGraph(State)
        graph.add_node("work", node)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({})
        # "base" should come from default_factory, "new" and "extra" from node
        assert "base" in result["unique_items"], (
            f"Factory default 'base' missing from result: {result['unique_items']}"
        )
        assert "new" in result["unique_items"]

    def test_mixed_default_and_no_default(self) -> None:
        """Field with default_factory alongside field without default."""
        from langgraph.graph import StateGraph

        @dataclass
        class State:
            items: Annotated[list[str], operator.add] = field(default_factory=lambda: ["pre"])
            name: str = ""

        def node(state: State) -> dict:
            return {"items": ["post"], "name": "done"}

        graph = StateGraph(State)
        graph.add_node("work", node)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({"name": "start"})
        assert result["items"] == ["pre", "post"], (
            f"Expected factory default preserved, got {result['items']}"
        )

    def test_factory_independence(self) -> None:
        """Each graph invocation gets fresh default_factory value (no sharing)."""
        from langgraph.graph import StateGraph

        call_count = 0

        def counting_factory() -> list[str]:
            nonlocal call_count
            call_count += 1
            return [f"call_{call_count}"]

        @dataclass
        class State:
            items: Annotated[list[str], operator.add] = field(default_factory=counting_factory)

        def node(state: State) -> dict:
            return {"items": ["node"]}

        graph = StateGraph(State)
        graph.add_node("work", node)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result1 = compiled.invoke({})
        result2 = compiled.invoke({})

        # Each invocation should start from a fresh factory call
        assert result1["items"][0].startswith("call_")
        assert result2["items"][0].startswith("call_")
        assert result1["items"] != result2["items"], (
            "Each invocation should get a fresh default_factory value"
        )


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_checkpoint_preserves_factory_default(self) -> None:
        """Factory default survives checkpoint round-trip."""
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import StateGraph

        @dataclass
        class State:
            items: Annotated[list[str], operator.add] = field(default_factory=lambda: ["seed"])

        def appender(state: State) -> dict:
            return {"items": ["added"]}

        graph = StateGraph(State)
        graph.add_node("work", appender)
        graph.set_entry_point("work")
        graph.set_finish_point("work")

        memory = InMemorySaver()
        compiled = graph.compile(checkpointer=memory)
        config = {"configurable": {"thread_id": "f6-checkpoint"}}

        compiled.invoke({}, config=config)
        state = compiled.get_state(config)

        assert state.values["items"] == ["seed", "added"], (
            f"Checkpoint should preserve factory default, got {state.values['items']}"
        )

    def test_factory_default_read_by_first_node(self) -> None:
        """First node in pipeline should see factory default as initial state."""
        from langgraph.graph import StateGraph

        observed: list[list[str]] = []

        @dataclass
        class State:
            items: Annotated[list[str], operator.add] = field(default_factory=lambda: ["initial"])

        def observer(state: State) -> dict:
            observed.append(list(state.items))
            return {"items": ["observed"]}

        graph = StateGraph(State)
        graph.add_node("observe", observer)
        graph.set_entry_point("observe")
        graph.set_finish_point("observe")
        compiled = graph.compile()

        compiled.invoke({})

        assert observed[0] == ["initial"], (
            f"First node should see factory default ['initial'], but saw {observed[0]}"
        )

    def test_conditional_routing_uses_factory_default(self) -> None:
        """Routing decisions based on factory default value work correctly."""
        from langgraph.graph import END, StateGraph

        @dataclass
        class State:
            items: Annotated[list[str], operator.add] = field(default_factory=lambda: ["start"])

        def route(state: State) -> str:
            return END if "start" in state.items else "work"

        def work(state: State) -> dict:
            return {"items": ["should_not_run"]}

        graph = StateGraph(State)
        graph.add_node("check", lambda s: s)
        graph.add_node("work", work)
        graph.add_conditional_edges("check", route)
        graph.set_entry_point("check")
        compiled = graph.compile()

        result = compiled.invoke({})
        # Factory provides ["start"] → route returns END → "work" never runs
        assert "should_not_run" not in result["items"], (
            f"Routing should have terminated based on factory default, got {result['items']}"
        )


class TestT4Smoke:
    """Smoke/integration tests — realistic multi-node workflows."""

    def test_three_node_pipeline(self) -> None:
        """Three-node pipeline with factory defaults accumulates correctly."""
        from langgraph.graph import StateGraph

        @dataclass
        class State:
            log: Annotated[list[str], operator.add] = field(
                default_factory=lambda: ["pipeline_start"]
            )
            stage: int = 0

        def stage_1(state: State) -> dict:
            return {"log": ["stage_1"], "stage": 1}

        def stage_2(state: State) -> dict:
            return {"log": ["stage_2"], "stage": 2}

        def stage_3(state: State) -> dict:
            return {"log": ["stage_3"], "stage": 3}

        graph = StateGraph(State)
        graph.add_node("s1", stage_1)
        graph.add_node("s2", stage_2)
        graph.add_node("s3", stage_3)
        graph.add_edge("s1", "s2")
        graph.add_edge("s2", "s3")
        graph.set_entry_point("s1")
        graph.set_finish_point("s3")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert result["log"] == ["pipeline_start", "stage_1", "stage_2", "stage_3"]
        assert result["stage"] == 3

    def test_factory_defaults_survive_checkpoint_roundtrip(self) -> None:
        """Full checkpoint round-trip with factory defaults and multiple invocations."""
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import END, StateGraph

        @dataclass
        class State:
            history: Annotated[list[str], operator.add] = field(
                default_factory=lambda: ["session_start"]
            )
            turn: int = 0

        def process(state: State) -> dict:
            return {
                "history": [f"turn_{state.turn}"],
                "turn": state.turn + 1,
            }

        def route(state: State) -> str:
            return END if state.turn >= 2 else "process"

        graph = StateGraph(State)
        graph.add_node("process", process)
        graph.add_conditional_edges("process", route)
        graph.set_entry_point("process")

        memory = InMemorySaver()
        compiled = graph.compile(checkpointer=memory)
        config = {"configurable": {"thread_id": "f6-roundtrip"}}

        compiled.invoke({}, config=config)
        state = compiled.get_state(config)

        assert state.values["history"] == ["session_start", "turn_0", "turn_1"]


class TestT5Robustness:
    """Robustness edge cases — spec-derived tests a QA engineer would flag."""

    def test_factory_returning_nested_structure(self) -> None:
        """default_factory returning a complex nested dict as initial value."""
        from langgraph.graph import StateGraph

        def merge_dicts(a: dict, b: dict) -> dict:
            return {**a, **b}

        @dataclass
        class State:
            config: Annotated[dict, merge_dicts] = field(
                default_factory=lambda: {"level": 1, "tags": ["base"], "nested": {"a": 1}}
            )

        def updater(state: State) -> dict:
            return {"config": {"tags": ["updated"], "extra": True}}

        graph = StateGraph(State)
        graph.add_node("work", updater)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({})
        # Factory default should be the starting point, then merged with updater
        assert result["config"]["tags"] == ["updated"], (
            f"Expected merged tags, got {result['config']}"
        )
        assert result["config"]["extra"] is True

    def test_plain_default_value_with_reducer(self) -> None:
        """Plain default= (not factory) on a field with a reducer."""
        from langgraph.graph import StateGraph

        @dataclass
        class State:
            counter: Annotated[int, operator.add] = 10

        def add_5(state: State) -> dict:
            return {"counter": 5}

        graph = StateGraph(State)
        graph.add_node("work", add_5)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert result["counter"] == 15, (
            f"Expected default(10) + node(5) = 15, got {result['counter']}"
        )
