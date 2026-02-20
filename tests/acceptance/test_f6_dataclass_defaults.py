"""F6: Dataclass default values with reducer channels.

When a dataclass field has both a default/default_factory AND a reducer via
Annotated[type, reducer], the default_factory return value is NOT used as the
channel's initial value. BinaryOperatorAggregate always self-initializes via
typ() (e.g., list() -> []).
"""

from __future__ import annotations

import dataclasses
import operator
from typing import Annotated

import pytest


@dataclasses.dataclass
class SimpleDefaultState:
    name: str = "default_name"
    count: int = 0


@dataclasses.dataclass
class FactoryDefaultState:
    items: Annotated[list[str], operator.add] = dataclasses.field(default_factory=list)
    label: str = "untitled"


@dataclasses.dataclass
class NonTrivialDefaultState:
    tags: Annotated[list[str], operator.add] = dataclasses.field(
        default_factory=lambda: ["initial"]
    )


@dataclasses.dataclass
class MultiFieldDefaultState:
    items: Annotated[list[str], operator.add] = dataclasses.field(default_factory=list)
    counts: Annotated[list[int], operator.add] = dataclasses.field(default_factory=list)
    label: str = "default"


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_default_with_reducer_compiles(self) -> None:
        """Dataclass with default + reducer compiles without error."""
        from langgraph.graph import StateGraph

        graph = StateGraph(FactoryDefaultState)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        assert compiled is not None

    def test_scalar_default_preserved(self) -> None:
        """Scalar default value is used when field not provided in input."""
        from langgraph.graph import StateGraph

        graph = StateGraph(SimpleDefaultState)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        result = compiled.invoke({"name": "custom"})
        assert result["name"] == "custom"
        # count should use default
        assert result["count"] == 0

    def test_default_factory_with_reducer(self) -> None:
        """default_factory=list with add reducer starts from empty list."""
        from langgraph.graph import StateGraph

        graph = StateGraph(FactoryDefaultState)
        graph.add_node("add", lambda s: {"items": ["hello"]})
        graph.set_entry_point("add")
        graph.set_finish_point("add")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert "hello" in result["items"]


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_non_trivial_default_factory(self) -> None:
        """default_factory returning non-empty list is used as initial channel value."""
        from langgraph.graph import StateGraph

        graph = StateGraph(NonTrivialDefaultState)
        graph.add_node("add", lambda s: {"tags": ["added"]})
        graph.set_entry_point("add")
        graph.set_finish_point("add")
        compiled = graph.compile()

        result = compiled.invoke({})
        # The non-trivial default ["initial"] should be the starting value,
        # then reducer appends ["added"]
        assert "initial" in result["tags"]
        assert "added" in result["tags"]

    def test_multiple_fields_with_defaults(self) -> None:
        """Multiple fields each with defaults and reducers."""
        from langgraph.graph import StateGraph

        graph = StateGraph(MultiFieldDefaultState)
        graph.add_node("add", lambda s: {"items": ["a"], "counts": [1]})
        graph.set_entry_point("add")
        graph.set_finish_point("add")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert "a" in result["items"]
        assert 1 in result["counts"]

    def test_explicit_input_overrides_default(self) -> None:
        """Explicit input overrides the default value for scalar fields."""
        from langgraph.graph import StateGraph

        graph = StateGraph(SimpleDefaultState)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        result = compiled.invoke({"name": "explicit", "count": 99})
        assert result["name"] == "explicit"
        assert result["count"] == 99

    def test_reducer_accumulates_over_default(self) -> None:
        """Reducer accumulates on top of the initial default value."""
        from langgraph.graph import StateGraph

        @dataclasses.dataclass
        class AccumState:
            values: Annotated[list[int], operator.add] = dataclasses.field(default_factory=list)

        def step1(state: AccumState) -> dict:
            return {"values": [1]}

        def step2(state: AccumState) -> dict:
            return {"values": [2]}

        graph = StateGraph(AccumState)
        graph.add_node("s1", step1)
        graph.add_node("s2", step2)
        graph.add_edge("s1", "s2")
        graph.set_entry_point("s1")
        graph.set_finish_point("s2")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert result["values"] == [1, 2]

    def test_nested_dataclass_default(self) -> None:
        """Nested dataclass field with default round-trips."""
        from langgraph.graph import StateGraph

        @dataclasses.dataclass
        class Inner:
            x: int = 10

        @dataclasses.dataclass
        class Outer:
            inner: Inner = dataclasses.field(default_factory=Inner)
            label: str = "default"

        graph = StateGraph(Outer)
        graph.add_node("noop", lambda s: s)
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert result["label"] == "default"


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_checkpoint_round_trip(self) -> None:
        """Default state survives checkpoint serialization."""
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import StateGraph

        graph = StateGraph(FactoryDefaultState)
        graph.add_node("add", lambda s: {"items": ["x"]})
        graph.set_entry_point("add")
        graph.set_finish_point("add")
        memory = InMemorySaver()
        compiled = graph.compile(checkpointer=memory)

        config = {"configurable": {"thread_id": "test-defaults"}}
        compiled.invoke({"label": "test"}, config=config)

        state = compiled.get_state(config)
        assert "x" in state.values["items"]
        assert state.values["label"] == "test"

    def test_reducer_on_top_of_default(self) -> None:
        """Reducer with non-trivial default_factory correctly accumulates."""
        from langgraph.graph import StateGraph

        graph = StateGraph(NonTrivialDefaultState)

        def add_tag(state: NonTrivialDefaultState) -> dict:
            return {"tags": ["step1"]}

        graph.add_node("add", add_tag)
        graph.set_entry_point("add")
        graph.set_finish_point("add")
        compiled = graph.compile()

        result = compiled.invoke({})
        # Should have the default "initial" plus the added "step1"
        assert "initial" in result["tags"]
        assert "step1" in result["tags"]

    @pytest.mark.timeout(5)
    def test_concurrent_reducers(self) -> None:
        """Multiple reducer fields accumulate independently."""
        from langgraph.graph import StateGraph

        graph = StateGraph(MultiFieldDefaultState)

        def node_a(state: MultiFieldDefaultState) -> dict:
            return {"items": ["a1", "a2"], "counts": [10]}

        def node_b(state: MultiFieldDefaultState) -> dict:
            return {"items": ["b1"], "counts": [20, 30]}

        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        compiled = graph.compile()

        result = compiled.invoke({})
        assert set(result["items"]) >= {"a1", "a2", "b1"}
        assert set(result["counts"]) >= {10, 20, 30}
