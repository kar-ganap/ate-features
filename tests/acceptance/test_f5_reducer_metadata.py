"""F5: Reducer metadata ordering dependency in _is_field_binop().

_is_field_binop() only checks meta[-1] (the last Annotated metadata item)
for a callable reducer. When the reducer is NOT the last metadata item
(e.g., Annotated[list, operator.add, "description"]), it is silently
dropped and the field becomes LastValue instead of BinaryOperatorAggregate.
No error or warning is produced — accumulation silently stops working.
"""

import operator
from typing import Annotated, TypedDict

import pytest


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_reducer_with_trailing_string(self) -> None:
        """Annotated[list, add, "doc"] should still use reducer, not LastValue."""
        from langgraph.graph import StateGraph

        class State(TypedDict):
            items: Annotated[list[str], operator.add, "A documented field"]

        def node_a(state: State) -> dict:
            return {"items": ["a"]}

        def node_b(state: State) -> dict:
            return {"items": ["b"]}

        graph = StateGraph(State)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        compiled = graph.compile()

        result = compiled.invoke({"items": []})
        # With reducer: ["a", "b"]. With LastValue (bug): ["b"]
        assert result["items"] == ["a", "b"], (
            f"Reducer silently dropped — got LastValue behavior {result['items']} "
            f"instead of accumulation ['a', 'b']"
        )

    def test_reducer_with_trailing_int(self) -> None:
        """Annotated[list, add, 42] should still use reducer."""
        from langgraph.graph import StateGraph

        class State(TypedDict):
            values: Annotated[list[int], operator.add, 42]

        def node(state: State) -> dict:
            return {"values": [1]}

        graph = StateGraph(State)
        graph.add_node("work", node)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({"values": [0]})
        assert result["values"] == [0, 1], (
            f"Expected accumulation [0, 1] but got {result['values']}"
        )

    def test_two_node_accumulation(self) -> None:
        """Two sequential nodes both accumulate into a documented field."""
        from langgraph.graph import StateGraph

        class State(TypedDict):
            log: Annotated[list[str], operator.add, "Execution log"]

        def step_1(state: State) -> dict:
            return {"log": ["step_1"]}

        def step_2(state: State) -> dict:
            return {"log": ["step_2"]}

        graph = StateGraph(State)
        graph.add_node("step_1", step_1)
        graph.add_node("step_2", step_2)
        graph.add_edge("step_1", "step_2")
        graph.set_entry_point("step_1")
        graph.set_finish_point("step_2")
        compiled = graph.compile()

        result = compiled.invoke({"log": ["init"]})
        assert result["log"] == ["init", "step_1", "step_2"], (
            f"Expected full accumulation but got {result['log']}"
        )


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_reducer_first_of_three_metadata(self) -> None:
        """Annotated[list, add, "x", 99] — reducer is first of three metadata."""
        from langgraph.graph import StateGraph

        class State(TypedDict):
            items: Annotated[list[str], operator.add, "documented", 99]

        def node_a(state: State) -> dict:
            return {"items": ["a"]}

        def node_b(state: State) -> dict:
            return {"items": ["b"]}

        graph = StateGraph(State)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        compiled = graph.compile()

        result = compiled.invoke({"items": []})
        assert result["items"] == ["a", "b"]

    def test_reducer_in_middle(self) -> None:
        """Annotated[list, "before", add, "after"] — reducer in the middle."""
        from langgraph.graph import StateGraph

        class State(TypedDict):
            items: Annotated[list[str], "before_doc", operator.add, "after_doc"]

        def node(state: State) -> dict:
            return {"items": ["appended"]}

        graph = StateGraph(State)
        graph.add_node("work", node)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({"items": ["start"]})
        assert result["items"] == ["start", "appended"]

    def test_multiple_fields_mixed_positions(self) -> None:
        """Multiple fields with reducers at different metadata positions."""
        from langgraph.graph import StateGraph

        class State(TypedDict):
            a: Annotated[list[str], operator.add, "doc_a"]
            b: Annotated[list[str], "doc_b", operator.add]

        def node(state: State) -> dict:
            return {"a": ["x"], "b": ["y"]}

        graph = StateGraph(State)
        graph.add_node("work", node)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({"a": ["init"], "b": ["init"]})
        assert result["a"] == ["init", "x"], (
            f"Field 'a' (reducer first): expected accumulation, got {result['a']}"
        )
        assert result["b"] == ["init", "y"], (
            f"Field 'b' (reducer middle): expected accumulation, got {result['b']}"
        )

    def test_custom_reducer_not_last(self) -> None:
        """Named function reducer followed by non-callable metadata."""
        from langgraph.graph import StateGraph

        def my_reducer(a: list, b: list) -> list:
            return a + b

        class State(TypedDict):
            items: Annotated[list[str], my_reducer, "description"]

        def node(state: State) -> dict:
            return {"items": ["added"]}

        graph = StateGraph(State)
        graph.add_node("work", node)
        graph.set_entry_point("work")
        graph.set_finish_point("work")
        compiled = graph.compile()

        result = compiled.invoke({"items": ["base"]})
        assert result["items"] == ["base", "added"]

    def test_trailing_none_metadata(self) -> None:
        """Annotated[list, add, None] — None trailing the reducer."""
        from langgraph.graph import StateGraph

        class State(TypedDict):
            items: Annotated[list[str], operator.add, None]

        def node_a(state: State) -> dict:
            return {"items": ["a"]}

        def node_b(state: State) -> dict:
            return {"items": ["b"]}

        graph = StateGraph(State)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        compiled = graph.compile()

        result = compiled.invoke({"items": []})
        # With reducer: ["a", "b"]. With LastValue (bug): ["b"]
        assert result["items"] == ["a", "b"]


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_invalid_reducer_not_last_raises(self) -> None:
        """Single-arg callable not at last position should still raise ValueError."""
        from langgraph.graph import StateGraph

        def bad_reducer(x: list) -> list:
            return x

        class State(TypedDict):
            items: Annotated[list[str], bad_reducer, "doc"]

        with pytest.raises(ValueError, match="Invalid reducer"):
            graph = StateGraph(State)
            graph.add_node("dummy", lambda s: s)
            graph.set_entry_point("dummy")
            graph.set_finish_point("dummy")
            graph.compile()

    def test_channel_type_is_binop(self) -> None:
        """Channel for documented reducer should be BinaryOperatorAggregate."""
        from langgraph.channels.binop import BinaryOperatorAggregate
        from langgraph.graph.state import _is_field_binop

        typ = Annotated[list[str], operator.add, "documented"]
        channel = _is_field_binop(typ)
        assert isinstance(channel, BinaryOperatorAggregate), (
            f"Expected BinaryOperatorAggregate, got {type(channel)}"
        )

    def test_three_node_sequential_accumulation(self) -> None:
        """Three sequential nodes accumulate into documented reducer field."""
        from langgraph.graph import StateGraph

        class State(TypedDict):
            log: Annotated[list[str], operator.add, "Execution trace"]

        def node_a(state: State) -> dict:
            return {"log": ["a"]}

        def node_b(state: State) -> dict:
            return {"log": ["b"]}

        def node_c(state: State) -> dict:
            return {"log": ["c"]}

        graph = StateGraph(State)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_node("c", node_c)
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.set_entry_point("a")
        graph.set_finish_point("c")
        compiled = graph.compile()

        result = compiled.invoke({"log": []})
        assert result["log"] == ["a", "b", "c"]


class TestT4Smoke:
    """Smoke/integration tests — realistic multi-node workflows."""

    def test_checkpoint_with_documented_reducer(self) -> None:
        """Multi-node graph with documented reducer survives checkpoint."""
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import StateGraph

        class State(TypedDict):
            items: Annotated[list[str], operator.add, "Accumulated items"]

        def step_1(state: State) -> dict:
            return {"items": ["first"]}

        def step_2(state: State) -> dict:
            return {"items": ["second"]}

        graph = StateGraph(State)
        graph.add_node("step_1", step_1)
        graph.add_node("step_2", step_2)
        graph.add_edge("step_1", "step_2")
        graph.set_entry_point("step_1")
        graph.set_finish_point("step_2")

        memory = InMemorySaver()
        compiled = graph.compile(checkpointer=memory)
        config = {"configurable": {"thread_id": "f5-smoke"}}

        result = compiled.invoke({"items": ["seed"]}, config=config)
        assert result["items"] == ["seed", "first", "second"]

        state = compiled.get_state(config)
        assert state.values["items"] == ["seed", "first", "second"]

    def test_conditional_routing_with_documented_reducer(self) -> None:
        """Conditional routing loop with documented reducer accumulates."""
        from langgraph.graph import END, StateGraph

        class State(TypedDict):
            count: int
            log: Annotated[list[str], operator.add, "Step log for debugging"]

        def process(state: State) -> dict:
            return {
                "count": state["count"] + 1,
                "log": [f"step_{state['count']}"],
            }

        def route(state: State) -> str:
            return END if state["count"] >= 3 else "process"

        graph = StateGraph(State)
        graph.add_node("process", process)
        graph.add_conditional_edges("process", route)
        graph.set_entry_point("process")
        compiled = graph.compile()

        result = compiled.invoke({"count": 0, "log": []})
        assert result["log"] == ["step_0", "step_1", "step_2"]
