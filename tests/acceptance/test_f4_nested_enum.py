"""F4: Nested Enum deserialization fix.

Top-level Enum values round-trip correctly, but when nested inside containers
(lists, dicts, dataclass fields), they deserialize as plain string/int.
"""

from __future__ import annotations

import dataclasses
from enum import Enum, IntEnum

import pytest


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class TestT1Basic:
    """Basic functionality — any first-attempt solution should pass these."""

    def test_enum_in_dict(self) -> None:
        """Enum nested inside a dict round-trips correctly."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"config": {"status": Status.ACTIVE}}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["config"]["status"], Status)
        assert result["config"]["status"] == Status.ACTIVE

    def test_enum_in_list(self) -> None:
        """Enum nested inside a list round-trips correctly."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"statuses": [Status.ACTIVE, Status.INACTIVE]}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert all(isinstance(s, Status) for s in result["statuses"])

    def test_top_level_still_works(self) -> None:
        """Top-level enum round-trip still works (regression check)."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"status": Status.ACTIVE}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["status"], Status)


class TestT2EdgeCases:
    """Edge cases — a naive first attempt may miss these."""

    def test_enum_in_dataclass(self) -> None:
        """Enum nested inside a dataclass field round-trips."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        @dataclasses.dataclass
        class Task:
            name: str
            status: Status
            priority: Priority

        serde = JsonPlusSerializer()
        data = {"task": Task(name="fix", status=Status.ACTIVE, priority=Priority.HIGH)}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["task"].status, Status)
        assert isinstance(result["task"].priority, Priority)

    def test_three_levels_deep(self) -> None:
        """Enum nested 3 levels deep (list of dicts of enums)."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"items": [{"status": Status.ACTIVE}, {"status": Status.INACTIVE}]}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        for item in result["items"]:
            assert isinstance(item["status"], Status)

    def test_int_enum_in_container(self) -> None:
        """IntEnum inside a container round-trips as IntEnum, not plain int."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"priorities": [Priority.LOW, Priority.HIGH]}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert all(isinstance(p, Priority) for p in result["priorities"])

    def test_mixed_enum_types_in_container(self) -> None:
        """Mix of different Enum types in the same container."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"values": [Status.ACTIVE, Priority.HIGH]}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["values"][0], Status)
        assert isinstance(result["values"][1], Priority)

    def test_enum_in_tuple(self) -> None:
        """Enum inside a tuple (immutable container)."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"pair": (Status.ACTIVE, Priority.HIGH)}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        # Tuples may become lists in msgpack, but enum types should be preserved
        assert isinstance(result["pair"][0], Status)
        assert isinstance(result["pair"][1], Priority)


class TestT3Quality:
    """Quality constraints — first approach probably fails these."""

    def test_recursive_multi_level(self) -> None:
        """Enums at multiple nesting levels all preserved."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {
            "top": Status.ACTIVE,
            "nested": {
                "mid": Priority.MEDIUM,
                "deep": [{"s": Status.INACTIVE}],
            },
        }

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert isinstance(result["top"], Status)
        assert isinstance(result["nested"]["mid"], Priority)
        assert isinstance(result["nested"]["deep"][0]["s"], Status)

    def test_enum_in_pydantic_in_dict(self) -> None:
        """Enum inside a Pydantic model field inside a dict — all types preserved."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        from pydantic import BaseModel

        class TaskModel(BaseModel):
            status: Status
            priority: Priority

        serde = JsonPlusSerializer()
        data = {
            "tasks": {
                "task1": TaskModel(status=Status.ACTIVE, priority=Priority.HIGH),
            }
        }

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        task = result["tasks"]["task1"]
        assert isinstance(task.status, Status)
        assert isinstance(task.priority, Priority)

    @pytest.mark.timeout(5)
    def test_performance_large_list(self) -> None:
        """1000-element list of enums round-trips efficiently."""
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

        serde = JsonPlusSerializer()
        data = {"statuses": [Status.ACTIVE if i % 2 == 0 else Status.INACTIVE for i in range(1000)]}

        serialized = serde.dumps(data)
        result = serde.loads(serialized)

        assert all(isinstance(s, Status) for s in result["statuses"])
        assert len(result["statuses"]) == 1000
