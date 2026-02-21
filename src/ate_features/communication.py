"""Communication analysis infrastructure for transcript parsing and event classification."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

# --- Enums ---


class CommunicationEventType(StrEnum):
    """Type of communication event in a transcript."""

    SEND_MESSAGE = "send_message"
    SHUTDOWN_REQUEST = "shutdown_request"


class CommunicationTaxonomy(StrEnum):
    """Classification of communication content."""

    STATUS_UPDATE = "status_update"
    FINDING_SHARED = "finding_shared"
    QUESTION = "question"
    HELP_REQUEST = "help_request"
    SUBSYSTEM_INSIGHT = "subsystem_insight"


# --- Models ---


class CommunicationEvent(BaseModel):
    """A single inter-agent communication event extracted from a transcript."""

    session_id: str
    timestamp: datetime
    sender: str
    recipient: str
    content: str
    event_type: CommunicationEventType
    message_type: str | None = None
    taxonomy: CommunicationTaxonomy | None = None


class CommunicationSummary(BaseModel):
    """Aggregate communication statistics for a treatment run."""

    treatment_id: int | str
    session_id: str
    total_events: int = 0
    events_by_taxonomy: dict[str, int] = Field(default_factory=dict)
    unique_senders: int = 0
    unique_recipients: int = 0
    unique_pairs: int = 0
    events: list[CommunicationEvent] = Field(default_factory=list)


# --- Transcript path ---

TRANSCRIPT_BASE = Path.home() / ".claude" / "projects"
# Sessions launched from ate-features root
_ATE_FEATURES_COMPONENT = (
    "-Users-kartikganapathi-Documents-Personal-random_projects"
    "-others-projects-checkout-ate-features"
)
# Sessions launched from data/langgraph (the experiment working dir)
_LANGGRAPH_COMPONENT = (
    "-Users-kartikganapathi-Documents-Personal-random-projects"
    "-others-projects-checkout-ate-features-data-langgraph"
)


def get_transcript_dir(session_id: str | None = None) -> Path:
    """Return the Claude Code transcript directory for a session.

    Checks both the ate-features and data/langgraph project dirs,
    since sessions are launched from data/langgraph.
    """
    if session_id:
        for component in [_LANGGRAPH_COMPONENT, _ATE_FEATURES_COMPONENT]:
            candidate = TRANSCRIPT_BASE / component / f"{session_id}.jsonl"
            if candidate.exists():
                return TRANSCRIPT_BASE / component
    return TRANSCRIPT_BASE / _ATE_FEATURES_COMPONENT


# --- Parser ---


def parse_transcript(transcript_path: Path) -> list[CommunicationEvent]:
    """Parse a Claude Code JSONL transcript and extract SendMessage events."""
    events: list[CommunicationEvent] = []
    session_id = transcript_path.stem

    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record: dict[str, object] = json.loads(line)
            except json.JSONDecodeError:
                continue

            if record.get("type") != "assistant":
                continue

            message = record.get("message")
            if not isinstance(message, dict):
                continue
            content_blocks = message.get("content")
            if not isinstance(content_blocks, list):
                continue

            timestamp_str = record.get("timestamp", "")
            team_name = record.get("teamName", "unknown")

            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                if block.get("name") != "SendMessage":
                    continue

                input_data = block.get("input")
                if not isinstance(input_data, dict):
                    continue

                recipient = str(input_data.get("recipient", ""))
                content = str(input_data.get("content", ""))
                msg_type = input_data.get("type")

                if msg_type == "shutdown_request":
                    event_type = CommunicationEventType.SHUTDOWN_REQUEST
                else:
                    event_type = CommunicationEventType.SEND_MESSAGE

                try:
                    ts = datetime.fromisoformat(str(timestamp_str))
                except (ValueError, TypeError):
                    ts = datetime(1970, 1, 1, tzinfo=UTC)

                event = CommunicationEvent(
                    session_id=session_id,
                    timestamp=ts,
                    sender=str(team_name),
                    recipient=recipient,
                    content=content,
                    event_type=event_type,
                    message_type=str(msg_type) if msg_type is not None else None,
                )
                events.append(event)

    return events


# --- Summary ---


def summarize_communication(
    events: list[CommunicationEvent],
    treatment_id: int | str,
    session_id: str,
) -> CommunicationSummary:
    """Build aggregate statistics from communication events."""
    taxonomy_counts: dict[str, int] = {}
    senders: set[str] = set()
    recipients: set[str] = set()
    pairs: set[tuple[str, str]] = set()

    for event in events:
        senders.add(event.sender)
        recipients.add(event.recipient)
        pairs.add((event.sender, event.recipient))
        if event.taxonomy is not None:
            key = event.taxonomy.value
            taxonomy_counts[key] = taxonomy_counts.get(key, 0) + 1

    return CommunicationSummary(
        treatment_id=treatment_id,
        session_id=session_id,
        total_events=len(events),
        events_by_taxonomy=taxonomy_counts,
        unique_senders=len(senders),
        unique_recipients=len(recipients),
        unique_pairs=len(pairs),
        events=events,
    )
