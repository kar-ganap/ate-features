"""Tests for ate_features.communication."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ate_features.communication import (
    CommunicationEvent,
    CommunicationEventType,
    CommunicationSummary,
    CommunicationTaxonomy,
    get_transcript_dir,
    parse_transcript,
    summarize_communication,
)


class TestCommunicationEventType:
    def test_values(self) -> None:
        assert CommunicationEventType.SEND_MESSAGE == "send_message"
        assert CommunicationEventType.SHUTDOWN_REQUEST == "shutdown_request"


class TestCommunicationTaxonomy:
    def test_values(self) -> None:
        assert CommunicationTaxonomy.STATUS_UPDATE == "status_update"
        assert CommunicationTaxonomy.FINDING_SHARED == "finding_shared"
        assert CommunicationTaxonomy.QUESTION == "question"
        assert CommunicationTaxonomy.HELP_REQUEST == "help_request"
        assert CommunicationTaxonomy.SUBSYSTEM_INSIGHT == "subsystem_insight"


class TestCommunicationEvent:
    def test_create(self) -> None:
        event = CommunicationEvent(
            session_id="abc123",
            timestamp=datetime(2026, 2, 20, tzinfo=UTC),
            sender="agent-1",
            recipient="agent-2",
            content="Found shared code path in jsonplus.py",
            event_type=CommunicationEventType.SEND_MESSAGE,
        )
        assert event.sender == "agent-1"
        assert event.recipient == "agent-2"
        assert event.event_type == CommunicationEventType.SEND_MESSAGE

    def test_defaults(self) -> None:
        event = CommunicationEvent(
            session_id="abc123",
            timestamp=datetime(2026, 2, 20, tzinfo=UTC),
            sender="agent-1",
            recipient="agent-2",
            content="hello",
            event_type=CommunicationEventType.SEND_MESSAGE,
        )
        assert event.message_type is None
        assert event.taxonomy is None

    def test_with_taxonomy(self) -> None:
        event = CommunicationEvent(
            session_id="abc123",
            timestamp=datetime(2026, 2, 20, tzinfo=UTC),
            sender="agent-1",
            recipient="agent-2",
            content="EXT_CONSTRUCTOR uses codes 100-110",
            event_type=CommunicationEventType.SEND_MESSAGE,
            taxonomy=CommunicationTaxonomy.SUBSYSTEM_INSIGHT,
        )
        assert event.taxonomy == CommunicationTaxonomy.SUBSYSTEM_INSIGHT


class TestCommunicationSummary:
    def test_empty(self) -> None:
        summary = CommunicationSummary(
            treatment_id="2a",
            session_id="abc123",
        )
        assert summary.total_events == 0
        assert summary.events_by_taxonomy == {}
        assert summary.unique_senders == 0
        assert summary.unique_recipients == 0
        assert summary.unique_pairs == 0
        assert summary.events == []

    def test_with_events(self) -> None:
        events = [
            CommunicationEvent(
                session_id="abc123",
                timestamp=datetime(2026, 2, 20, tzinfo=UTC),
                sender="agent-1",
                recipient="agent-2",
                content="hello",
                event_type=CommunicationEventType.SEND_MESSAGE,
                taxonomy=CommunicationTaxonomy.FINDING_SHARED,
            ),
            CommunicationEvent(
                session_id="abc123",
                timestamp=datetime(2026, 2, 20, tzinfo=UTC),
                sender="agent-2",
                recipient="agent-1",
                content="thanks",
                event_type=CommunicationEventType.SEND_MESSAGE,
                taxonomy=CommunicationTaxonomy.STATUS_UPDATE,
            ),
        ]
        summary = CommunicationSummary(
            treatment_id="2a",
            session_id="abc123",
            total_events=2,
            events_by_taxonomy={"finding_shared": 1, "status_update": 1},
            unique_senders=2,
            unique_recipients=2,
            unique_pairs=2,
            events=events,
        )
        assert summary.total_events == 2
        assert len(summary.events) == 2


class TestParseTranscript:
    def _write_jsonl(self, path: Path, records: list[dict[str, object]]) -> None:
        with open(path, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")

    def test_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        events = parse_transcript(p)
        assert events == []

    def test_no_send_messages(self, tmp_path: Path) -> None:
        p = tmp_path / "no_send.jsonl"
        self._write_jsonl(p, [
            {
                "type": "assistant",
                "timestamp": "2026-02-20T10:00:00+00:00",
                "message": {
                    "content": [
                        {"type": "text", "text": "thinking..."}
                    ]
                },
            }
        ])
        events = parse_transcript(p)
        assert events == []

    def test_single_send_message(self, tmp_path: Path) -> None:
        p = tmp_path / "single.jsonl"
        self._write_jsonl(p, [
            {
                "type": "assistant",
                "timestamp": "2026-02-20T10:00:00+00:00",
                "teamName": "agent-1",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "SendMessage",
                            "input": {
                                "recipient": "agent-2",
                                "content": "Found shared code path",
                            },
                        }
                    ]
                },
            }
        ])
        events = parse_transcript(p)
        assert len(events) == 1
        assert events[0].sender == "agent-1"
        assert events[0].recipient == "agent-2"
        assert events[0].content == "Found shared code path"
        assert events[0].event_type == CommunicationEventType.SEND_MESSAGE

    def test_multiple_send_messages(self, tmp_path: Path) -> None:
        p = tmp_path / "multi.jsonl"
        self._write_jsonl(p, [
            {
                "type": "assistant",
                "timestamp": "2026-02-20T10:00:00+00:00",
                "teamName": "agent-1",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "SendMessage",
                            "input": {"recipient": "agent-2", "content": "msg1"},
                        },
                        {
                            "type": "tool_use",
                            "name": "SendMessage",
                            "input": {"recipient": "agent-3", "content": "msg2"},
                        },
                    ]
                },
            }
        ])
        events = parse_transcript(p)
        assert len(events) == 2
        assert events[0].recipient == "agent-2"
        assert events[1].recipient == "agent-3"

    def test_shutdown_request(self, tmp_path: Path) -> None:
        p = tmp_path / "shutdown.jsonl"
        self._write_jsonl(p, [
            {
                "type": "assistant",
                "timestamp": "2026-02-20T10:00:00+00:00",
                "teamName": "lead",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "SendMessage",
                            "input": {
                                "recipient": "agent-1",
                                "content": "shutdown",
                                "type": "shutdown_request",
                            },
                        }
                    ]
                },
            }
        ])
        events = parse_transcript(p)
        assert len(events) == 1
        assert events[0].event_type == CommunicationEventType.SHUTDOWN_REQUEST
        assert events[0].message_type == "shutdown_request"

    def test_ignores_non_assistant_messages(self, tmp_path: Path) -> None:
        p = tmp_path / "user_msg.jsonl"
        self._write_jsonl(p, [
            {
                "type": "user",
                "timestamp": "2026-02-20T10:00:00+00:00",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "SendMessage",
                            "input": {"recipient": "agent-1", "content": "hi"},
                        }
                    ]
                },
            }
        ])
        events = parse_transcript(p)
        assert events == []

    def test_ignores_non_tool_use_content(self, tmp_path: Path) -> None:
        p = tmp_path / "text_only.jsonl"
        self._write_jsonl(p, [
            {
                "type": "assistant",
                "timestamp": "2026-02-20T10:00:00+00:00",
                "message": {
                    "content": [
                        {"type": "text", "text": "SendMessage is a tool"},
                    ]
                },
            }
        ])
        events = parse_transcript(p)
        assert events == []

    def test_ignores_non_sendmessage_tool_use(self, tmp_path: Path) -> None:
        p = tmp_path / "other_tool.jsonl"
        self._write_jsonl(p, [
            {
                "type": "assistant",
                "timestamp": "2026-02-20T10:00:00+00:00",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"path": "/some/file"},
                        }
                    ]
                },
            }
        ])
        events = parse_transcript(p)
        assert events == []

    def test_malformed_json_lines_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / "malformed.jsonl"
        with open(p, "w") as f:
            f.write("not valid json\n")
            f.write(json.dumps({
                "type": "assistant",
                "timestamp": "2026-02-20T10:00:00+00:00",
                "teamName": "agent-1",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "SendMessage",
                            "input": {"recipient": "agent-2", "content": "hi"},
                        }
                    ]
                },
            }) + "\n")
        events = parse_transcript(p)
        assert len(events) == 1

    def test_session_id_from_filename(self, tmp_path: Path) -> None:
        p = tmp_path / "my-session-id.jsonl"
        self._write_jsonl(p, [
            {
                "type": "assistant",
                "timestamp": "2026-02-20T10:00:00+00:00",
                "teamName": "agent-1",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "SendMessage",
                            "input": {"recipient": "agent-2", "content": "hi"},
                        }
                    ]
                },
            }
        ])
        events = parse_transcript(p)
        assert events[0].session_id == "my-session-id"


class TestSummarizeCommunication:
    def test_empty_events(self) -> None:
        summary = summarize_communication([], "2a", "abc123")
        assert summary.total_events == 0
        assert summary.unique_senders == 0
        assert summary.unique_pairs == 0

    def test_counts_taxonomies(self) -> None:
        events = [
            CommunicationEvent(
                session_id="abc",
                timestamp=datetime(2026, 2, 20, tzinfo=UTC),
                sender="a1",
                recipient="a2",
                content="x",
                event_type=CommunicationEventType.SEND_MESSAGE,
                taxonomy=CommunicationTaxonomy.FINDING_SHARED,
            ),
            CommunicationEvent(
                session_id="abc",
                timestamp=datetime(2026, 2, 20, tzinfo=UTC),
                sender="a1",
                recipient="a2",
                content="y",
                event_type=CommunicationEventType.SEND_MESSAGE,
                taxonomy=CommunicationTaxonomy.FINDING_SHARED,
            ),
            CommunicationEvent(
                session_id="abc",
                timestamp=datetime(2026, 2, 20, tzinfo=UTC),
                sender="a2",
                recipient="a1",
                content="z",
                event_type=CommunicationEventType.SEND_MESSAGE,
                taxonomy=CommunicationTaxonomy.QUESTION,
            ),
        ]
        summary = summarize_communication(events, "2a", "abc")
        assert summary.total_events == 3
        assert summary.events_by_taxonomy == {"finding_shared": 2, "question": 1}

    def test_unique_pairs(self) -> None:
        events = [
            CommunicationEvent(
                session_id="abc",
                timestamp=datetime(2026, 2, 20, tzinfo=UTC),
                sender="a1",
                recipient="a2",
                content="x",
                event_type=CommunicationEventType.SEND_MESSAGE,
            ),
            CommunicationEvent(
                session_id="abc",
                timestamp=datetime(2026, 2, 20, tzinfo=UTC),
                sender="a1",
                recipient="a2",
                content="y",
                event_type=CommunicationEventType.SEND_MESSAGE,
            ),
            CommunicationEvent(
                session_id="abc",
                timestamp=datetime(2026, 2, 20, tzinfo=UTC),
                sender="a2",
                recipient="a1",
                content="z",
                event_type=CommunicationEventType.SEND_MESSAGE,
            ),
        ]
        summary = summarize_communication(events, "2a", "abc")
        assert summary.unique_senders == 2
        assert summary.unique_recipients == 2
        assert summary.unique_pairs == 2  # (a1->a2) and (a2->a1)

    def test_no_taxonomy_excluded_from_counts(self) -> None:
        events = [
            CommunicationEvent(
                session_id="abc",
                timestamp=datetime(2026, 2, 20, tzinfo=UTC),
                sender="a1",
                recipient="a2",
                content="x",
                event_type=CommunicationEventType.SEND_MESSAGE,
                taxonomy=None,
            ),
        ]
        summary = summarize_communication(events, "2a", "abc")
        assert summary.total_events == 1
        assert summary.events_by_taxonomy == {}


class TestGetTranscriptDir:
    def test_returns_path(self) -> None:
        result = get_transcript_dir()
        assert isinstance(result, Path)
        assert "claude" in str(result)
