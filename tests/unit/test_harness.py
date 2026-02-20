"""Tests for harness directory management and treatment introspection."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ate_features.config import load_treatments
from ate_features.harness import (
    get_patch_path,
    get_run_dir,
    is_per_feature_treatment,
    save_metadata,
    uses_agent_teams,
)
from ate_features.models import ExecutionMode, RunMetadata


@pytest.fixture
def treatments():
    return load_treatments()


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


class TestGetRunDir:
    def test_single_session_treatment(self, data_dir: Path) -> None:
        run_dir = get_run_dir("0a", data_dir=data_dir)
        assert run_dir == data_dir / "transcripts" / "treatment-0a"

    def test_per_feature_treatment(self, data_dir: Path) -> None:
        run_dir = get_run_dir("0b", feature_id="F1", data_dir=data_dir)
        assert run_dir == data_dir / "transcripts" / "treatment-0b" / "F1"

    def test_numeric_treatment_id(self, data_dir: Path) -> None:
        run_dir = get_run_dir(1, data_dir=data_dir)
        assert run_dir == data_dir / "transcripts" / "treatment-1"

    def test_feature_id_appended(self, data_dir: Path) -> None:
        run_dir = get_run_dir(5, feature_id="F3", data_dir=data_dir)
        assert run_dir == data_dir / "transcripts" / "treatment-5" / "F3"


class TestGetPatchPath:
    def test_returns_patch_path(self, data_dir: Path) -> None:
        path = get_patch_path("0a", "F1", data_dir=data_dir)
        assert path == data_dir / "patches" / "treatment-0a" / "F1.patch"

    def test_numeric_treatment_id(self, data_dir: Path) -> None:
        path = get_patch_path(1, "F5", data_dir=data_dir)
        assert path == data_dir / "patches" / "treatment-1" / "F5.patch"


class TestSaveMetadata:
    def test_creates_file(self, tmp_path: Path) -> None:
        meta = RunMetadata(
            treatment_id="0a",
            mode=ExecutionMode.INTERACTIVE,
        )
        path = save_metadata(meta, tmp_path)
        assert path.exists()
        assert path.name == "metadata.json"

    def test_content_is_valid_json(self, tmp_path: Path) -> None:
        meta = RunMetadata(
            treatment_id=1,
            feature_ids=["F1", "F5"],
            started_at=datetime.now(tz=UTC),
            mode=ExecutionMode.INTERACTIVE,
            agent_teams_enabled=True,
        )
        path = save_metadata(meta, tmp_path)
        loaded = json.loads(path.read_text())
        assert loaded["treatment_id"] == 1
        assert loaded["feature_ids"] == ["F1", "F5"]
        assert loaded["agent_teams_enabled"] is True

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        meta = RunMetadata(
            treatment_id="0b",
            mode=ExecutionMode.INTERACTIVE,
        )
        path = save_metadata(meta, nested)
        assert path.exists()


class TestIsPerFeatureTreatment:
    def test_0b_is_per_feature(self, treatments) -> None:
        t = next(t for t in treatments.treatments if t.id == "0b")
        assert is_per_feature_treatment(t) is True

    def test_6_is_per_feature(self, treatments) -> None:
        t = next(t for t in treatments.treatments if t.id == 6)
        assert is_per_feature_treatment(t) is True

    def test_0a_is_not_per_feature(self, treatments) -> None:
        t = next(t for t in treatments.treatments if t.id == "0a")
        assert is_per_feature_treatment(t) is False

    def test_1_is_not_per_feature(self, treatments) -> None:
        t = next(t for t in treatments.treatments if t.id == 1)
        assert is_per_feature_treatment(t) is False

    def test_5_is_not_per_feature(self, treatments) -> None:
        """5 is 8×1 but uses Agent Teams, so single session."""
        t = next(t for t in treatments.treatments if t.id == 5)
        assert is_per_feature_treatment(t) is False


class TestUsesAgentTeams:
    def test_0a_no_agent_teams(self, treatments) -> None:
        t = next(t for t in treatments.treatments if t.id == "0a")
        assert uses_agent_teams(t) is False

    def test_0b_no_agent_teams(self, treatments) -> None:
        t = next(t for t in treatments.treatments if t.id == "0b")
        assert uses_agent_teams(t) is False

    def test_1_uses_agent_teams(self, treatments) -> None:
        t = next(t for t in treatments.treatments if t.id == 1)
        assert uses_agent_teams(t) is True

    def test_4_uses_agent_teams(self, treatments) -> None:
        """4 has delegate_mode=false but still uses Agent Teams."""
        t = next(t for t in treatments.treatments if t.id == 4)
        assert uses_agent_teams(t) is True

    def test_6_no_agent_teams(self, treatments) -> None:
        t = next(t for t in treatments.treatments if t.id == 6)
        assert uses_agent_teams(t) is False
