"""Tests for communication nudge prompt loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from ate_features.config import load_communication_nudges


class TestLoadCommunicationNudges:
    def test_loads_all_modes(self) -> None:
        nudges = load_communication_nudges()
        assert "encourage" in nudges
        assert "discourage" in nudges
        assert "neutral" in nudges

    def test_encourage_has_system_context(self) -> None:
        nudges = load_communication_nudges()
        assert "system_context" in nudges["encourage"]
        assert "USEFUL" in nudges["encourage"]["system_context"]

    def test_discourage_has_system_context(self) -> None:
        nudges = load_communication_nudges()
        assert "system_context" in nudges["discourage"]
        assert "WASTEFUL" in nudges["discourage"]["system_context"]

    def test_neutral_has_system_context(self) -> None:
        nudges = load_communication_nudges()
        assert "system_context" in nudges["neutral"]

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_communication_nudges(config_dir=tmp_path)
