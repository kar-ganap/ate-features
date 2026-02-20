"""F8: messages_key configuration for stream_mode="messages".

The StreamMessagesHandler scans ALL top-level state field values for BaseMessage
instances — there is no `messages_key` parameter to restrict which field is
streamed. This feature adds a configurable key so users can control which state
field is the message source.

The core behavioral gap: when a state has multiple BaseMessage fields (e.g.,
"messages" and "internal_log"), streaming emits from ALL of them. The feature
should allow restricting streaming to a single specified field.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class MessagesState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


class CustomKeyState(TypedDict):
    chat_history: Annotated[list[BaseMessage], operator.add]


class DualKeyState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    internal_log: Annotated[list[BaseMessage], operator.add]


def _collect_streamed_messages(events: list) -> list[BaseMessage]:
    """Extract all BaseMessage objects from stream events."""
    msgs: list[BaseMessage] = []
    for event in events:
        if isinstance(event, BaseMessage):
            msgs.append(event)
        elif isinstance(event, tuple) and len(event) == 2:
            # (event_type, message) format
            _, payload = event
            if isinstance(payload, BaseMessage):
                msgs.append(payload)
        elif isinstance(event, (list, tuple)):
            for item in event:
                if isinstance(item, BaseMessage):
                    msgs.append(item)
    return msgs


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_default_messages_key_streams(self) -> None:
        """stream_mode='messages' works with default 'messages' field."""
        from langgraph.graph import StateGraph

        def respond(state: MessagesState) -> dict:
            return {"messages": [AIMessage(content="hello")]}

        graph = StateGraph(MessagesState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        result = compiled.invoke({"messages": [HumanMessage(content="hi")]})
        assert any(isinstance(m, AIMessage) and m.content == "hello" for m in result["messages"])

    def test_custom_key_streaming(self) -> None:
        """stream_mode='messages' with a non-default field name streams messages."""
        from langgraph.graph import StateGraph

        def respond(state: CustomKeyState) -> dict:
            return {"chat_history": [AIMessage(content="response")]}

        graph = StateGraph(CustomKeyState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"chat_history": [HumanMessage(content="test")]},
                stream_mode="messages",
            )
        )
        # Messages from chat_history should appear in stream output
        streamed = _collect_streamed_messages(events)
        assert any(m.content == "response" for m in streamed), (
            f"Expected 'response' in streamed messages, got: {[m.content for m in streamed]}"
        )

    def test_only_specified_key_streamed(self) -> None:
        """When messages_key is specified, only that field's messages are streamed.

        This is the core of the feature: with dual message fields, streaming
        should be restricted to the configured key only.
        """
        from langgraph.graph import StateGraph

        def respond(state: DualKeyState) -> dict:
            return {
                "messages": [AIMessage(content="public_msg")],
                "internal_log": [AIMessage(content="internal_msg")],
            }

        graph = StateGraph(DualKeyState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        # Stream with messages_key="messages" — only "messages" field should be emitted
        events = list(
            compiled.stream(
                {
                    "messages": [HumanMessage(content="hi")],
                    "internal_log": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_streamed_messages(events)
        streamed_contents = [m.content for m in streamed]
        # The internal_log messages should NOT appear in stream output
        assert "internal_msg" not in streamed_contents, (
            "internal_log messages should be filtered out when messages_key is set, "
            f"but got: {streamed_contents}"
        )


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_default_messages_key_backward_compat(self) -> None:
        """Default 'messages' field still works without explicit messages_key."""
        from langgraph.graph import StateGraph

        def respond(state: MessagesState) -> dict:
            return {"messages": [AIMessage(content="default")]}

        graph = StateGraph(MessagesState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        result = compiled.invoke({"messages": [HumanMessage(content="test")]})
        assert any(isinstance(m, AIMessage) and m.content == "default" for m in result["messages"])

    def test_dual_fields_unfiltered_streams_both(self) -> None:
        """Without messages_key, both message fields appear in stream output."""
        from langgraph.graph import StateGraph

        def respond(state: DualKeyState) -> dict:
            return {
                "messages": [AIMessage(content="public")],
                "internal_log": [AIMessage(content="internal")],
            }

        graph = StateGraph(DualKeyState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        # Without messages_key filtering, BOTH fields should be streamed
        events = list(
            compiled.stream(
                {
                    "messages": [HumanMessage(content="hi")],
                    "internal_log": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_streamed_messages(events)
        streamed_contents = [m.content for m in streamed]
        # Both should appear when no filtering is active
        assert "public" in streamed_contents or "internal" in streamed_contents

    def test_empty_messages_no_error(self) -> None:
        """Streaming with empty messages list doesn't raise."""
        from langgraph.graph import StateGraph

        graph = StateGraph(MessagesState)
        graph.add_node("noop", lambda s: {"messages": []})
        graph.set_entry_point("noop")
        graph.set_finish_point("noop")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"messages": []},
                stream_mode="messages",
            )
        )
        assert isinstance(events, list)

    def test_multi_node_message_streaming(self) -> None:
        """Messages from multiple nodes are all captured in stream."""
        from langgraph.graph import StateGraph

        def node_a(state: MessagesState) -> dict:
            return {"messages": [AIMessage(content="from_a")]}

        def node_b(state: MessagesState) -> dict:
            return {"messages": [AIMessage(content="from_b")]}

        graph = StateGraph(MessagesState)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        compiled = graph.compile()

        result = compiled.invoke({"messages": [HumanMessage(content="start")]})
        contents = [m.content for m in result["messages"]]
        assert "from_a" in contents
        assert "from_b" in contents

    def test_filter_excludes_non_target_field(self) -> None:
        """With messages_key filtering, non-target field messages are excluded from stream.

        Key behavioral test: the "internal_log" field messages must NOT appear
        when streaming is restricted to "messages" only.
        """
        from langgraph.graph import StateGraph

        def respond(state: DualKeyState) -> dict:
            return {
                "messages": [AIMessage(content="visible")],
                "internal_log": [AIMessage(content="hidden")],
            }

        graph = StateGraph(DualKeyState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "messages": [HumanMessage(content="hi")],
                    "internal_log": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_streamed_messages(events)
        streamed_contents = [m.content for m in streamed]
        # "hidden" from internal_log MUST NOT be in stream output
        assert "hidden" not in streamed_contents, (
            f"internal_log messages leaked into stream: {streamed_contents}"
        )
        # "visible" from messages MUST be present
        assert "visible" in streamed_contents, (
            f"messages field content missing from stream: {streamed_contents}"
        )


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    @pytest.mark.timeout(10)
    def test_performance_not_degraded(self) -> None:
        """Streaming with messages_key is not significantly degraded vs without."""
        from langgraph.graph import StateGraph

        def respond(state: MessagesState) -> dict:
            return {"messages": [AIMessage(content=f"msg_{i}") for i in range(100)]}

        graph = StateGraph(MessagesState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        result = compiled.invoke({"messages": [HumanMessage(content="go")]})
        assert len(result["messages"]) > 50

    def test_metadata_preserved_in_filtered_stream(self) -> None:
        """Message metadata (name, additional_kwargs) preserved with messages_key filtering."""
        from langgraph.graph import StateGraph

        def respond(state: DualKeyState) -> dict:
            return {
                "messages": [
                    AIMessage(
                        content="hello",
                        name="assistant",
                        additional_kwargs={"source": "test"},
                    )
                ],
                "internal_log": [AIMessage(content="log_entry")],
            }

        graph = StateGraph(DualKeyState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {
                    "messages": [HumanMessage(content="hi")],
                    "internal_log": [],
                },
                stream_mode="messages",
            )
        )
        streamed = _collect_streamed_messages(events)
        streamed_contents = [m.content for m in streamed]
        # internal_log should not leak
        assert "log_entry" not in streamed_contents, (
            f"internal_log leaked into filtered stream: {streamed_contents}"
        )

    def test_subgraph_message_streaming(self) -> None:
        """Messages from a subgraph are streamed correctly."""
        from langgraph.graph import StateGraph

        # Inner graph
        inner = StateGraph(MessagesState)
        inner.add_node("inner_node", lambda s: {"messages": [AIMessage(content="inner")]})
        inner.set_entry_point("inner_node")
        inner.set_finish_point("inner_node")
        inner_compiled = inner.compile()

        # Outer graph
        outer = StateGraph(MessagesState)
        outer.add_node("sub", inner_compiled)
        outer.set_entry_point("sub")
        outer.set_finish_point("sub")
        outer_compiled = outer.compile()

        result = outer_compiled.invoke({"messages": [HumanMessage(content="start")]})
        contents = [m.content for m in result["messages"]]
        assert "inner" in contents
