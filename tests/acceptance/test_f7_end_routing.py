"""F7: END routing in conditional edges.

Conditional edges can return END to terminate the graph. This is handled by
filtering out END in get_writes() — the loop terminates naturally when no
successor node is triggered. Send() to END is explicitly forbidden.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest


class SimpleState(TypedDict):
    value: str


class CountState(TypedDict):
    count: int
    log: list[str]


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_conditional_edge_returns_end(self) -> None:
        """Conditional edge returning END terminates the graph."""
        from langgraph.graph import END, StateGraph

        def route(state: SimpleState) -> str:
            return END

        graph = StateGraph(SimpleState)
        graph.add_node("start_node", lambda s: s)
        graph.add_conditional_edges("start_node", route)
        graph.set_entry_point("start_node")
        compiled = graph.compile()

        result = compiled.invoke({"value": "hello"})
        assert result["value"] == "hello"

    def test_graph_compiles_with_end_edge(self) -> None:
        """Graph with conditional edge to END compiles without error."""
        from langgraph.graph import END, StateGraph

        graph = StateGraph(SimpleState)
        graph.add_node("a", lambda s: s)
        graph.add_conditional_edges("a", lambda s: END)
        graph.set_entry_point("a")
        compiled = graph.compile()

        assert compiled is not None

    def test_end_terminates_execution(self) -> None:
        """After END, no further nodes execute."""
        from langgraph.graph import END, StateGraph

        executed = []

        def node_a(state: SimpleState) -> dict:
            executed.append("a")
            return {"value": "from_a"}

        def node_b(state: SimpleState) -> dict:
            executed.append("b")
            return {"value": "from_b"}

        graph = StateGraph(SimpleState)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_conditional_edges("a", lambda s: END)
        graph.set_entry_point("a")
        compiled = graph.compile()

        compiled.invoke({"value": "start"})
        assert "a" in executed
        assert "b" not in executed


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_mixed_end_and_node_targets(self) -> None:
        """Conditional edge returns END or a node name depending on state."""
        from langgraph.graph import END, StateGraph

        def route(state: SimpleState) -> str:
            if state["value"] == "done":
                return END
            return "continue_node"

        graph = StateGraph(SimpleState)
        graph.add_node("check", lambda s: s)
        graph.add_node("continue_node", lambda s: {"value": "done"})
        graph.add_conditional_edges("check", route)
        graph.add_edge("continue_node", "check")
        graph.set_entry_point("check")
        compiled = graph.compile()

        result = compiled.invoke({"value": "not_done"})
        assert result["value"] == "done"

    def test_conditional_entry_point_to_end(self) -> None:
        """set_conditional_entry_point can route directly to END."""
        from langgraph.graph import END, StateGraph

        graph = StateGraph(SimpleState)
        graph.add_node("a", lambda s: s)
        graph.set_conditional_entry_point(lambda s: END)
        compiled = graph.compile()

        result = compiled.invoke({"value": "skip"})
        assert result["value"] == "skip"

    def test_multiple_conditional_edges_with_end(self) -> None:
        """Multiple nodes each with conditional edges, some leading to END."""
        from langgraph.graph import END, StateGraph

        graph = StateGraph(SimpleState)
        graph.add_node("a", lambda s: {"value": s["value"] + "_a"})
        graph.add_node("b", lambda s: {"value": s["value"] + "_b"})
        graph.add_conditional_edges("a", lambda s: "b")
        graph.add_conditional_edges("b", lambda s: END)
        graph.set_entry_point("a")
        compiled = graph.compile()

        result = compiled.invoke({"value": "start"})
        assert result["value"] == "start_a_b"

    def test_path_map_with_end(self) -> None:
        """path_map mapping a return value to END."""
        from langgraph.graph import END, StateGraph

        graph = StateGraph(SimpleState)
        graph.add_node("check", lambda s: s)
        graph.add_node("process", lambda s: {"value": "processed"})
        graph.add_conditional_edges(
            "check",
            lambda s: "stop" if s["value"] == "halt" else "go",
            {"stop": END, "go": "process"},
        )
        graph.add_edge("process", END)
        graph.set_entry_point("check")
        compiled = graph.compile()

        # Route to END
        result = compiled.invoke({"value": "halt"})
        assert result["value"] == "halt"

        # Route to process
        result = compiled.invoke({"value": "go"})
        assert result["value"] == "processed"

    def test_send_to_end_raises(self) -> None:
        """Send() targeting END raises InvalidUpdateError."""
        from langgraph.graph import END, StateGraph
        from langgraph.types import Send

        graph = StateGraph(SimpleState)
        graph.add_node("a", lambda s: s)
        graph.add_node("b", lambda s: s)
        graph.add_conditional_edges(
            "a",
            lambda s: [Send("b", {"value": "ok"}), Send(END, {"value": "bad"})],
        )
        graph.set_entry_point("a")
        compiled = graph.compile()

        with pytest.raises(Exception):  # InvalidUpdateError
            compiled.invoke({"value": "test"})


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_visualization_with_end(self) -> None:
        """Graph with END edges can be drawn/visualized (get_graph works)."""
        from langgraph.graph import END, StateGraph

        graph = StateGraph(SimpleState)
        graph.add_node("a", lambda s: s)
        graph.add_conditional_edges("a", lambda s: END)
        graph.set_entry_point("a")
        compiled = graph.compile()

        # get_graph() should work without error
        drawable = compiled.get_graph()
        assert drawable is not None

        # END should appear in the graph representation
        node_ids = {n.id for n in drawable.nodes.values()}
        assert "__end__" in node_ids

    def test_state_preserved_at_end(self) -> None:
        """Final state is fully preserved when graph terminates via END."""
        from langgraph.graph import END, StateGraph

        class AccumState(TypedDict):
            log: Annotated[list[str], operator.add]

        def node_a(state: AccumState) -> dict:
            return {"log": ["visited_a"]}

        def node_b(state: AccumState) -> dict:
            return {"log": ["visited_b"]}

        graph = StateGraph(AccumState)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.add_conditional_edges("b", lambda s: END)
        graph.set_entry_point("a")
        compiled = graph.compile()

        result = compiled.invoke({"log": []})
        assert "visited_a" in result["log"]
        assert "visited_b" in result["log"]

    def test_checkpoint_at_end(self) -> None:
        """Checkpoint is saved when graph terminates via conditional END."""
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import END, StateGraph

        graph = StateGraph(SimpleState)
        graph.add_node("work", lambda s: {"value": "done"})
        graph.add_conditional_edges("work", lambda s: END)
        graph.set_entry_point("work")

        memory = InMemorySaver()
        compiled = graph.compile(checkpointer=memory)

        config = {"configurable": {"thread_id": "test-end-checkpoint"}}
        compiled.invoke({"value": "start"}, config=config)

        state = compiled.get_state(config)
        assert state.values["value"] == "done"
