"""F8: Input message dedup for nested structures.

on_chain_start() in StreamMessagesHandler pre-seeds the `seen` set to
prevent re-emitting input messages. But it only scans two levels deep
(same limitation as F7). If a node receives messages nested in a Pydantic
model/dataclass and returns them flattened in output, they are emitted as
"new" duplicates — the dedup mechanism fails for nested input.
"""

import operator
from dataclasses import dataclass, field
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel


class Context(BaseModel):
    """Nested container holding messages that on_chain_start can't traverse."""

    history: list[BaseMessage] = []


@dataclass
class DataContext:
    """Dataclass variant of nested message container."""

    messages: list[BaseMessage] = field(default_factory=list)


class StateWithUnwrap(TypedDict):
    """State where a node unwraps nested messages into a flat field."""

    context: Context
    messages: Annotated[list[BaseMessage], operator.add]


class StateWithDCUnwrap(TypedDict):
    """State with dataclass context for unwrapping."""

    ctx: DataContext
    messages: Annotated[list[BaseMessage], operator.add]


def _collect_messages(events: list) -> list[BaseMessage]:
    """Extract BaseMessage objects from stream_mode='messages' events."""
    msgs: list[BaseMessage] = []
    for event in events:
        if isinstance(event, tuple) and len(event) == 2:
            msg, _ = event
            if isinstance(msg, BaseMessage):
                msgs.append(msg)
        elif isinstance(event, BaseMessage):
            msgs.append(event)
    return msgs


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_nested_pydantic_input_deduped(self) -> None:
        """Message in Pydantic input, returned flat, should NOT be re-emitted."""
        from langgraph.graph import StateGraph

        existing_msg = HumanMessage(content="hello", id="existing-1")

        def unwrap(state: StateWithUnwrap) -> dict:
            # Unwrap nested messages + add a new one
            return {
                "messages": state["context"].history + [AIMessage(content="new_reply", id="new-1")]
            }

        graph = StateGraph(StateWithUnwrap)
        graph.add_node("unwrap", unwrap)
        graph.set_entry_point("unwrap")
        graph.set_finish_point("unwrap")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "context": Context(history=[existing_msg]),
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        # existing_msg was in the input (nested) — should be deduped
        assert "existing-1" not in streamed_ids, (
            f"Nested input message 'existing-1' should be deduped, "
            f"but was emitted. Streamed IDs: {streamed_ids}"
        )
        # new_reply is genuinely new — should be emitted
        assert "new-1" in streamed_ids, (
            f"New message 'new-1' should be emitted. Streamed IDs: {streamed_ids}"
        )

    def test_nested_dataclass_input_deduped(self) -> None:
        """Message in dataclass input, returned flat, should NOT be re-emitted."""
        from langgraph.graph import StateGraph

        existing_msg = HumanMessage(content="hi", id="dc-existing-1")

        def unwrap(state: StateWithDCUnwrap) -> dict:
            return {
                "messages": state["ctx"].messages + [AIMessage(content="response", id="dc-new-1")]
            }

        graph = StateGraph(StateWithDCUnwrap)
        graph.add_node("unwrap", unwrap)
        graph.set_entry_point("unwrap")
        graph.set_finish_point("unwrap")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "ctx": DataContext(messages=[existing_msg]),
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        assert "dc-existing-1" not in streamed_ids, (
            f"Nested dataclass input should be deduped. Got: {streamed_ids}"
        )
        assert "dc-new-1" in streamed_ids

    def test_nested_dict_input_deduped(self) -> None:
        """Message in nested dict input, returned flat, should NOT be re-emitted."""
        from langgraph.graph import StateGraph

        existing_msg = HumanMessage(content="hey", id="dict-existing-1")

        class DictState(TypedDict):
            data: dict
            messages: Annotated[list[BaseMessage], operator.add]

        def unwrap(state: DictState) -> dict:
            nested_msgs = state["data"].get("history", [])
            return {"messages": nested_msgs + [AIMessage(content="reply", id="dict-new-1")]}

        graph = StateGraph(DictState)
        graph.add_node("unwrap", unwrap)
        graph.set_entry_point("unwrap")
        graph.set_finish_point("unwrap")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "data": {"history": [existing_msg]},
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        assert "dict-existing-1" not in streamed_ids, (
            f"Nested dict input should be deduped. Got: {streamed_ids}"
        )


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_deeply_nested_input_deduped(self) -> None:
        """Message 3 levels deep in input should be deduped when returned flat."""
        from langgraph.graph import StateGraph

        class Inner(BaseModel):
            msgs: list[BaseMessage] = []

        class Outer(BaseModel):
            inner: Inner = Inner()

        class DeepState(TypedDict):
            wrapper: Outer
            messages: Annotated[list[BaseMessage], operator.add]

        deep_msg = HumanMessage(content="deep", id="deep-1")

        def unwrap(state: DeepState) -> dict:
            return {
                "messages": state["wrapper"].inner.msgs + [AIMessage(content="new", id="deep-new")]
            }

        graph = StateGraph(DeepState)
        graph.add_node("unwrap", unwrap)
        graph.set_entry_point("unwrap")
        graph.set_finish_point("unwrap")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "wrapper": Outer(inner=Inner(msgs=[deep_msg])),
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        assert "deep-1" not in streamed_ids, (
            f"Deeply nested input should be deduped. Got: {streamed_ids}"
        )
        assert "deep-new" in streamed_ids

    def test_mixed_nested_and_new(self) -> None:
        """Only new messages emitted when mixed with nested input pass-throughs."""
        from langgraph.graph import StateGraph

        old_msg = HumanMessage(content="old", id="mix-old")

        def process(state: StateWithUnwrap) -> dict:
            return {
                "messages": state["context"].history
                + [
                    AIMessage(content="new_1", id="mix-new-1"),
                    AIMessage(content="new_2", id="mix-new-2"),
                ]
            }

        graph = StateGraph(StateWithUnwrap)
        graph.add_node("process", process)
        graph.set_entry_point("process")
        graph.set_finish_point("process")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "context": Context(history=[old_msg]),
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        assert "mix-old" not in streamed_ids, "Old nested message should be deduped"
        assert "mix-new-1" in streamed_ids, "New message 1 should be emitted"
        assert "mix-new-2" in streamed_ids, "New message 2 should be emitted"

    def test_multiple_nested_fields_deduped(self) -> None:
        """Messages from multiple nested fields should all be deduped."""
        from langgraph.graph import StateGraph

        class MultiContext(TypedDict):
            ctx_a: Context
            ctx_b: Context
            messages: Annotated[list[BaseMessage], operator.add]

        msg_a = HumanMessage(content="a", id="multi-a")
        msg_b = HumanMessage(content="b", id="multi-b")

        def unwrap(state: MultiContext) -> dict:
            return {
                "messages": (
                    state["ctx_a"].history
                    + state["ctx_b"].history
                    + [AIMessage(content="new", id="multi-new")]
                )
            }

        graph = StateGraph(MultiContext)
        graph.add_node("unwrap", unwrap)
        graph.set_entry_point("unwrap")
        graph.set_finish_point("unwrap")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "ctx_a": Context(history=[msg_a]),
                    "ctx_b": Context(history=[msg_b]),
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        assert "multi-a" not in streamed_ids, "msg_a from ctx_a should be deduped"
        assert "multi-b" not in streamed_ids, "msg_b from ctx_b should be deduped"
        assert "multi-new" in streamed_ids, "New message should be emitted"

    def test_partial_unwrap_dedup(self) -> None:
        """Only the unwrapped messages are deduped, new ones are emitted."""
        from langgraph.graph import StateGraph

        input_msg = HumanMessage(content="input", id="partial-1")

        def selective_unwrap(state: StateWithUnwrap) -> dict:
            # Only return some messages from context, plus new ones
            return {
                "messages": [
                    state["context"].history[0],  # pass-through
                    AIMessage(content="brand_new", id="partial-new"),
                ]
            }

        graph = StateGraph(StateWithUnwrap)
        graph.add_node("unwrap", selective_unwrap)
        graph.set_entry_point("unwrap")
        graph.set_finish_point("unwrap")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "context": Context(history=[input_msg]),
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        assert "partial-1" not in streamed_ids, "Pass-through should be deduped"
        assert "partial-new" in streamed_ids, "New message should be emitted"

    def test_nested_across_node_boundaries(self) -> None:
        """First node has nested input; second node unwraps — dedup still works."""
        from langgraph.graph import StateGraph

        old_msg = HumanMessage(content="old", id="boundary-old")

        def node_a(state: StateWithUnwrap) -> dict:
            return {"messages": [AIMessage(content="from_a", id="boundary-a")]}

        def node_b(state: StateWithUnwrap) -> dict:
            return {
                "messages": state["context"].history
                + [AIMessage(content="from_b", id="boundary-b")]
            }

        graph = StateGraph(StateWithUnwrap)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "context": Context(history=[old_msg]),
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        # old_msg was in nested input — should be deduped even when node_b returns it
        assert "boundary-old" not in streamed_ids, (
            f"Nested input from context should be deduped across nodes. Got: {streamed_ids}"
        )


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_exact_emission_count(self) -> None:
        """Verify exact count of emitted messages with nested dedup."""
        from langgraph.graph import StateGraph

        old_1 = HumanMessage(content="old1", id="count-old-1")
        old_2 = HumanMessage(content="old2", id="count-old-2")

        def process(state: StateWithUnwrap) -> dict:
            return {
                "messages": state["context"].history
                + [
                    AIMessage(content="new1", id="count-new-1"),
                    AIMessage(content="new2", id="count-new-2"),
                    AIMessage(content="new3", id="count-new-3"),
                ]
            }

        graph = StateGraph(StateWithUnwrap)
        graph.add_node("process", process)
        graph.set_entry_point("process")
        graph.set_finish_point("process")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "context": Context(history=[old_1, old_2]),
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)

        # 2 old (deduped) + 3 new = only 3 should be emitted
        new_ids = {"count-new-1", "count-new-2", "count-new-3"}
        old_ids = {"count-old-1", "count-old-2"}
        streamed_ids = {m.id for m in streamed}

        assert old_ids.isdisjoint(streamed_ids), (
            f"Old messages should be deduped. Leaked: {old_ids & streamed_ids}"
        )
        assert new_ids.issubset(streamed_ids), (
            f"All new messages should be emitted. Missing: {new_ids - streamed_ids}"
        )

    def test_dedup_with_checkpoint(self) -> None:
        """Nested dedup works correctly with checkpointer enabled."""
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import StateGraph

        old_msg = HumanMessage(content="old", id="ckpt-old")

        def unwrap(state: StateWithUnwrap) -> dict:
            return {
                "messages": state["context"].history + [AIMessage(content="new", id="ckpt-new")]
            }

        graph = StateGraph(StateWithUnwrap)
        graph.add_node("unwrap", unwrap)
        graph.set_entry_point("unwrap")
        graph.set_finish_point("unwrap")

        memory = InMemorySaver()
        compiled = graph.compile(checkpointer=memory)
        config = {"configurable": {"thread_id": "f8-ckpt"}}

        events = list(
            compiled.stream(
                {
                    "context": Context(history=[old_msg]),
                    "messages": [],
                },
                stream_mode="messages",
                config=config,
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        assert "ckpt-old" not in streamed_ids, "Should dedup even with checkpoint"
        assert "ckpt-new" in streamed_ids

    def test_no_false_dedup(self) -> None:
        """Different-ID messages emitted; same-ID nested input messages deduped."""
        from langgraph.graph import StateGraph

        nested_msg = HumanMessage(content="same text", id="false-1")

        def process(state: StateWithUnwrap) -> dict:
            # Return the nested input message (pass-through) + a new one
            return {
                "messages": state["context"].history
                + [AIMessage(content="same text", id="false-2")]
            }

        graph = StateGraph(StateWithUnwrap)
        graph.add_node("process", process)
        graph.set_entry_point("process")
        graph.set_finish_point("process")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "context": Context(history=[nested_msg]),
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        # false-2 is a NEW message (different ID) — should be emitted
        assert "false-2" in streamed_ids, (
            "New message with different ID should not be falsely deduped"
        )
        # false-1 was in nested input — should be deduped (not re-emitted)
        assert "false-1" not in streamed_ids, (
            f"Nested input message should be deduped. Got: {streamed_ids}"
        )


class TestT4Smoke:
    """Smoke/integration tests — realistic multi-node workflows."""

    def test_agent_handoff_dedup(self) -> None:
        """Realistic agent handoff: context messages not re-emitted on handoff."""
        from langgraph.graph import END, StateGraph

        class AgentContext(BaseModel):
            conversation: list[BaseMessage] = []

        class AgentState(TypedDict):
            context: AgentContext
            messages: Annotated[list[BaseMessage], operator.add]
            status: str

        user_msg = HumanMessage(content="Book a flight", id="agent-user")

        def agent_a(state: AgentState) -> dict:
            # Agent A processes and hands off, passing through the user message
            return {
                "messages": state["context"].conversation
                + [AIMessage(content="Routing to travel agent", id="agent-a-1")],
                "status": "handoff",
            }

        def agent_b(state: AgentState) -> dict:
            return {
                "messages": [AIMessage(content="I'll book that for you", id="agent-b-1")],
                "status": "done",
            }

        def route(state: AgentState) -> str:
            return "agent_b" if state["status"] == "handoff" else END

        graph = StateGraph(AgentState)
        graph.add_node("agent_a", agent_a)
        graph.add_node("agent_b", agent_b)
        graph.add_conditional_edges("agent_a", route)
        graph.add_edge("agent_b", END)
        graph.set_entry_point("agent_a")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "context": AgentContext(conversation=[user_msg]),
                    "messages": [],
                    "status": "start",
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        # user_msg was in context (nested) — should NOT be re-emitted
        assert "agent-user" not in streamed_ids, (
            f"User message from nested context should be deduped. Got: {streamed_ids}"
        )
        # Agent responses should be emitted
        assert "agent-a-1" in streamed_ids or "agent-b-1" in streamed_ids, (
            f"Agent responses should be emitted. Got: {streamed_ids}"
        )

    def test_multi_turn_nested_dedup(self) -> None:
        """Multi-turn conversation with nested context — no duplicate emissions."""
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import StateGraph

        turn_1_msg = HumanMessage(content="turn 1", id="mt-turn1")

        def responder(state: StateWithUnwrap) -> dict:
            # Unwraps context history and adds response
            return {
                "messages": state["context"].history + [AIMessage(content="response", id="mt-resp")]
            }

        graph = StateGraph(StateWithUnwrap)
        graph.add_node("respond", responder)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")

        memory = InMemorySaver()
        compiled = graph.compile(checkpointer=memory)
        config = {"configurable": {"thread_id": "f8-multi-turn"}}

        events = list(
            compiled.stream(
                {
                    "context": Context(history=[turn_1_msg]),
                    "messages": [],
                },
                stream_mode="messages",
                config=config,
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        assert "mt-turn1" not in streamed_ids, "Nested context message should be deduped"
        assert "mt-resp" in streamed_ids, "New response should be emitted"


class TestT5Robustness:
    """Robustness edge cases — spec-derived tests a QA engineer would flag."""

    def test_same_message_in_flat_and_nested_input(self) -> None:
        """Message present in both flat list and nested container — deduped from both."""
        from langgraph.graph import StateGraph

        shared_msg = HumanMessage(content="shared", id="shared-1")

        def process(state: StateWithUnwrap) -> dict:
            return {
                "messages": state["context"].history
                + [AIMessage(content="new", id="shared-new")]
            }

        graph = StateGraph(StateWithUnwrap)
        graph.add_node("process", process)
        graph.set_entry_point("process")
        graph.set_finish_point("process")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "context": Context(history=[shared_msg]),
                    "messages": [shared_msg],  # same msg in flat list too
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        assert "shared-1" not in streamed_ids, (
            f"Message in both flat and nested input should be deduped. Got: {streamed_ids}"
        )
        assert "shared-new" in streamed_ids

    def test_many_nested_messages_all_deduped(self) -> None:
        """10 messages in nested input all deduped when returned flat."""
        from langgraph.graph import StateGraph

        nested_msgs = [
            HumanMessage(content=f"msg_{i}", id=f"many-{i}")
            for i in range(10)
        ]

        def unwrap(state: StateWithUnwrap) -> dict:
            return {
                "messages": state["context"].history
                + [AIMessage(content="the_new_one", id="many-new")]
            }

        graph = StateGraph(StateWithUnwrap)
        graph.add_node("unwrap", unwrap)
        graph.set_entry_point("unwrap")
        graph.set_finish_point("unwrap")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "context": Context(history=nested_msgs),
                    "messages": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        streamed_ids = {m.id for m in streamed}

        # All 10 nested input messages should be deduped
        for i in range(10):
            assert f"many-{i}" not in streamed_ids, (
                f"Nested input message many-{i} should be deduped"
            )
        assert "many-new" in streamed_ids, "New message should be emitted"
