"""F7: Nested message detection in stream_mode="messages".

_find_and_emit_messages() in StreamMessagesHandler scans only two levels:
top-level state field values, then one level of Sequence. Messages nested
inside Pydantic models, dataclasses, or dicts-within-state are invisible
to the streaming handler — they are silently dropped from stream output.
"""

import operator
from dataclasses import dataclass, field
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel


class Context(BaseModel):
    """A nested container holding messages — invisible to current streaming."""

    history: list[BaseMessage] = []


@dataclass
class DataContext:
    """Dataclass variant of nested message container."""

    messages: list[BaseMessage] = field(default_factory=list)


class StateWithContext(TypedDict):
    context: Context
    output: Annotated[list[str], operator.add]


class StateWithDataContext(TypedDict):
    ctx: DataContext
    output: Annotated[list[str], operator.add]


class StateWithNestedDict(TypedDict):
    data: dict
    output: Annotated[list[str], operator.add]


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

    def test_messages_in_pydantic_model(self) -> None:
        """Messages inside a Pydantic model field should appear in stream."""
        from langgraph.graph import StateGraph

        def respond(state: StateWithContext) -> dict:
            return {
                "context": Context(history=[AIMessage(content="nested_reply", id="msg-1")]),
                "output": ["done"],
            }

        graph = StateGraph(StateWithContext)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"context": Context(), "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "nested_reply" in contents, (
            f"Message inside Pydantic model not found in stream. Got: {contents}"
        )

    def test_messages_in_dataclass(self) -> None:
        """Messages inside a dataclass field should appear in stream."""
        from langgraph.graph import StateGraph

        def respond(state: StateWithDataContext) -> dict:
            return {
                "ctx": DataContext(messages=[AIMessage(content="dc_reply", id="msg-dc")]),
                "output": ["done"],
            }

        graph = StateGraph(StateWithDataContext)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"ctx": DataContext(), "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "dc_reply" in contents, (
            f"Message inside dataclass not found in stream. Got: {contents}"
        )

    def test_messages_in_nested_dict(self) -> None:
        """Messages inside a dict-within-state should appear in stream."""
        from langgraph.graph import StateGraph

        def respond(state: StateWithNestedDict) -> dict:
            return {
                "data": {"msgs": [AIMessage(content="dict_reply", id="msg-dict")]},
                "output": ["done"],
            }

        graph = StateGraph(StateWithNestedDict)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"data": {}, "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "dict_reply" in contents, (
            f"Message inside nested dict not found in stream. Got: {contents}"
        )


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_deeply_nested_messages(self) -> None:
        """Messages 3 levels deep should be found."""
        from langgraph.graph import StateGraph

        class Inner(BaseModel):
            msgs: list[BaseMessage] = []

        class Middle(BaseModel):
            inner: Inner = Inner()

        class DeepState(TypedDict):
            wrapper: Middle
            output: Annotated[list[str], operator.add]

        def respond(state: DeepState) -> dict:
            return {
                "wrapper": Middle(inner=Inner(msgs=[AIMessage(content="deep_msg", id="msg-deep")])),
                "output": ["done"],
            }

        graph = StateGraph(DeepState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"wrapper": Middle(), "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "deep_msg" in contents, f"Deeply nested message not found. Got: {contents}"

    def test_mixed_flat_and_nested(self) -> None:
        """Both flat and nested messages should appear in stream."""
        from langgraph.graph import StateGraph

        class MixedState(TypedDict):
            flat_msgs: Annotated[list[BaseMessage], operator.add]
            context: Context

        def respond(state: MixedState) -> dict:
            return {
                "flat_msgs": [AIMessage(content="flat_msg", id="msg-flat")],
                "context": Context(history=[AIMessage(content="nested_msg", id="msg-nested")]),
            }

        graph = StateGraph(MixedState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"flat_msgs": [], "context": Context()},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        # Flat should always work
        # Nested is the bug — it should ALSO appear
        assert "nested_msg" in contents, (
            f"Nested message missing from mixed stream. Got: {contents}"
        )

    def test_multiple_nested_containers(self) -> None:
        """Multiple Pydantic models each with messages should all emit."""
        from langgraph.graph import StateGraph

        class MultiState(TypedDict):
            ctx_a: Context
            ctx_b: Context
            output: Annotated[list[str], operator.add]

        def respond(state: MultiState) -> dict:
            return {
                "ctx_a": Context(history=[AIMessage(content="from_a", id="msg-a")]),
                "ctx_b": Context(history=[AIMessage(content="from_b", id="msg-b")]),
                "output": ["done"],
            }

        graph = StateGraph(MultiState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"ctx_a": Context(), "ctx_b": Context(), "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "from_a" in contents, f"Messages from ctx_a missing. Got: {contents}"
        assert "from_b" in contents, f"Messages from ctx_b missing. Got: {contents}"

    def test_pydantic_model_with_single_message(self) -> None:
        """Pydantic model containing a single BaseMessage (not a list)."""
        from langgraph.graph import StateGraph

        class SingleMsgContext(BaseModel):
            last_msg: BaseMessage | None = None

        class SingleState(TypedDict):
            ctx: SingleMsgContext
            output: Annotated[list[str], operator.add]

        def respond(state: SingleState) -> dict:
            return {
                "ctx": SingleMsgContext(last_msg=AIMessage(content="single", id="msg-single")),
                "output": ["done"],
            }

        graph = StateGraph(SingleState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"ctx": SingleMsgContext(), "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "single" in contents, f"Single message in Pydantic model not found. Got: {contents}"

    def test_dataclass_with_message_list(self) -> None:
        """Dataclass field containing list[BaseMessage] should emit."""
        from langgraph.graph import StateGraph

        @dataclass
        class ToolResult:
            tool_name: str = ""
            messages: list[BaseMessage] = field(default_factory=list)

        class ToolState(TypedDict):
            result: ToolResult
            output: Annotated[list[str], operator.add]

        def tool_node(state: ToolState) -> dict:
            return {
                "result": ToolResult(
                    tool_name="search",
                    messages=[AIMessage(content="tool_output", id="msg-tool")],
                ),
                "output": ["done"],
            }

        graph = StateGraph(ToolState)
        graph.add_node("tool", tool_node)
        graph.set_entry_point("tool")
        graph.set_finish_point("tool")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"result": ToolResult(), "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "tool_output" in contents, (
            f"Message in dataclass tool result not found. Got: {contents}"
        )


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_nested_message_metadata_preserved(self) -> None:
        """Message metadata (name, additional_kwargs) preserved in nested emission."""
        from langgraph.graph import StateGraph

        def respond(state: StateWithContext) -> dict:
            return {
                "context": Context(
                    history=[
                        AIMessage(
                            content="rich_msg",
                            name="assistant",
                            additional_kwargs={"source": "test"},
                            id="msg-rich",
                        )
                    ]
                ),
                "output": ["done"],
            }

        graph = StateGraph(StateWithContext)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"context": Context(), "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        rich_msgs = [m for m in streamed if m.content == "rich_msg"]
        assert len(rich_msgs) == 1, f"Expected exactly 1 rich_msg, got {len(rich_msgs)}"
        assert rich_msgs[0].name == "assistant"
        assert rich_msgs[0].additional_kwargs.get("source") == "test"

    def test_nested_model_with_mixed_fields(self) -> None:
        """Nested model with both messages and non-messages: messages found, others not."""
        from langgraph.graph import StateGraph

        class MixedContext(BaseModel):
            data: list[str] = []
            count: int = 0
            important_msg: BaseMessage | None = None

        class MixedState(TypedDict):
            ctx: MixedContext
            output: Annotated[list[str], operator.add]

        def respond(state: MixedState) -> dict:
            return {
                "ctx": MixedContext(
                    data=["not_a_message"],
                    count=1,
                    important_msg=AIMessage(content="found_me", id="msg-found"),
                ),
                "output": ["done"],
            }

        graph = StateGraph(MixedState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"ctx": MixedContext(), "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        # Nested message should be found
        assert "found_me" in contents, (
            f"Nested message in mixed model not found. Got: {contents}"
        )
        # Non-message data should NOT appear
        assert "not_a_message" not in contents

    def test_nested_messages_from_two_nodes(self) -> None:
        """Nested messages from multiple sequential nodes all appear in stream."""
        from langgraph.graph import StateGraph

        class MultiNodeState(TypedDict):
            context: Context
            output: Annotated[list[str], operator.add]

        def node_a(state: MultiNodeState) -> dict:
            return {
                "context": Context(history=[AIMessage(content="from_node_a", id="msg-na")]),
                "output": ["a_done"],
            }

        def node_b(state: MultiNodeState) -> dict:
            return {
                "context": Context(history=[AIMessage(content="from_node_b", id="msg-nb")]),
                "output": ["b_done"],
            }

        graph = StateGraph(MultiNodeState)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"context": Context(), "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "from_node_a" in contents, f"Nested message from node_a missing. Got: {contents}"
        assert "from_node_b" in contents, f"Nested message from node_b missing. Got: {contents}"


class TestT4Smoke:
    """Smoke/integration tests — realistic multi-node workflows."""

    def test_agent_context_streaming(self) -> None:
        """Realistic agent with context object — nested messages stream correctly."""
        from langgraph.graph import END, StateGraph

        class AgentContext(BaseModel):
            conversation: list[BaseMessage] = []
            tool_outputs: list[BaseMessage] = []

        class AgentState(TypedDict):
            context: AgentContext
            status: str

        def think(state: AgentState) -> dict:
            return {
                "context": AgentContext(
                    conversation=[AIMessage(content="Let me search for that.", id="think-1")]
                ),
                "status": "thinking",
            }

        def act(state: AgentState) -> dict:
            return {
                "context": AgentContext(
                    tool_outputs=[AIMessage(content="Search result: found it.", id="act-1")]
                ),
                "status": "done",
            }

        graph = StateGraph(AgentState)
        graph.add_node("think", think)
        graph.add_node("act", act)
        graph.add_edge("think", "act")
        graph.add_edge("act", END)
        graph.set_entry_point("think")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"context": AgentContext(), "status": "start"},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert any("search" in c.lower() for c in contents), (
            f"Agent context messages not found in stream. Got: {contents}"
        )

    def test_multi_node_with_checkpoint_nested_streaming(self) -> None:
        """Multi-node graph with checkpoint and nested message streaming."""
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import StateGraph

        def processor(state: StateWithContext) -> dict:
            return {
                "context": Context(
                    history=[
                        AIMessage(content="processed", id="msg-proc"),
                    ]
                ),
                "output": ["processed"],
            }

        graph = StateGraph(StateWithContext)
        graph.add_node("process", processor)
        graph.set_entry_point("process")
        graph.set_finish_point("process")

        memory = InMemorySaver()
        compiled = graph.compile(checkpointer=memory)
        config = {"configurable": {"thread_id": "f7-smoke"}}

        events = list(
            compiled.stream(
                {"context": Context(), "output": []},
                stream_mode="messages",
                config=config,
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "processed" in contents, f"Nested message missing with checkpoint. Got: {contents}"


class TestT5Robustness:
    """Robustness edge cases — spec-derived tests a QA engineer would flag."""

    def test_messages_in_dict_of_dicts(self) -> None:
        """Messages inside dict→dict→list structure should be found."""
        from langgraph.graph import StateGraph

        class DeepDictState(TypedDict):
            data: dict
            output: Annotated[list[str], operator.add]

        def respond(state: DeepDictState) -> dict:
            return {
                "data": {
                    "section": {
                        "responses": [AIMessage(content="deep_dict_msg", id="msg-dd")]
                    }
                },
                "output": ["done"],
            }

        graph = StateGraph(DeepDictState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"data": {}, "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "deep_dict_msg" in contents, (
            f"Message in dict-of-dicts not found in stream. Got: {contents}"
        )

    def test_mixed_message_types_in_nested_container(self) -> None:
        """HumanMessage and AIMessage in same nested container both emitted."""
        from langchain_core.messages import HumanMessage
        from langgraph.graph import StateGraph

        class MixedMsgContext(BaseModel):
            msgs: list[BaseMessage] = []

        class MixedMsgState(TypedDict):
            ctx: MixedMsgContext
            output: Annotated[list[str], operator.add]

        def respond(state: MixedMsgState) -> dict:
            return {
                "ctx": MixedMsgContext(
                    msgs=[
                        HumanMessage(content="user_q", id="msg-human"),
                        AIMessage(content="ai_reply", id="msg-ai"),
                    ]
                ),
                "output": ["done"],
            }

        graph = StateGraph(MixedMsgState)
        graph.add_node("respond", respond)
        graph.set_entry_point("respond")
        graph.set_finish_point("respond")
        compiled = graph.compile()

        events = list(
            compiled.stream(
                {"ctx": MixedMsgContext(), "output": []},
                stream_mode="messages",
            )
        )
        streamed = _collect_messages(events)
        contents = [m.content for m in streamed]
        assert "user_q" in contents, f"HumanMessage not found. Got: {contents}"
        assert "ai_reply" in contents, f"AIMessage not found. Got: {contents}"
