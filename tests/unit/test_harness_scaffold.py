"""Tests for treatment scaffolding."""

from pathlib import Path

import pytest

from ate_features.harness import scaffold_treatment


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


class TestScaffoldSingleSession:
    """Treatments that run all features in one session (0a, 1, 2a, etc.)."""

    def test_creates_session_guide(self, data_dir: Path) -> None:
        paths = scaffold_treatment("0a", data_dir=data_dir)
        guide = data_dir / "transcripts" / "treatment-0a" / "session_guide.md"
        assert guide.exists()
        assert guide in paths

    def test_creates_metadata(self, data_dir: Path) -> None:
        scaffold_treatment("0a", data_dir=data_dir)
        meta = data_dir / "transcripts" / "treatment-0a" / "metadata.json"
        assert meta.exists()

    def test_creates_notes(self, data_dir: Path) -> None:
        scaffold_treatment("0a", data_dir=data_dir)
        notes = data_dir / "transcripts" / "treatment-0a" / "notes.md"
        assert notes.exists()

    def test_numeric_treatment_id(self, data_dir: Path) -> None:
        paths = scaffold_treatment(1, data_dir=data_dir)
        guide = data_dir / "transcripts" / "treatment-1" / "session_guide.md"
        assert guide.exists()
        assert guide in paths

    def test_returns_created_paths(self, data_dir: Path) -> None:
        paths = scaffold_treatment("0a", data_dir=data_dir)
        assert len(paths) >= 3  # guide + metadata + notes


class TestScaffoldPerFeature:
    """Per-feature treatments: 0b, 6 (8×1 without Agent Teams)."""

    def test_creates_per_feature_dirs(self, data_dir: Path) -> None:
        scaffold_treatment("0b", data_dir=data_dir)
        base = data_dir / "transcripts" / "treatment-0b"
        for fid in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]:
            assert (base / fid / "session_guide.md").exists()
            assert (base / fid / "metadata.json").exists()
            assert (base / fid / "notes.md").exists()

    def test_returns_all_created_paths(self, data_dir: Path) -> None:
        paths = scaffold_treatment("0b", data_dir=data_dir)
        # 8 features × 3 files = 24
        assert len(paths) >= 24

    def test_treatment_6_is_per_feature(self, data_dir: Path) -> None:
        scaffold_treatment(6, data_dir=data_dir)
        base = data_dir / "transcripts" / "treatment-6"
        assert (base / "F1" / "session_guide.md").exists()
        assert (base / "F8" / "session_guide.md").exists()


class TestScaffoldIdempotent:
    def test_notes_not_overwritten(self, data_dir: Path) -> None:
        scaffold_treatment("0a", data_dir=data_dir)
        notes_path = data_dir / "transcripts" / "treatment-0a" / "notes.md"
        notes_path.write_text("My important notes")

        # Scaffold again
        scaffold_treatment("0a", data_dir=data_dir)
        assert notes_path.read_text() == "My important notes"

    def test_guide_is_overwritten(self, data_dir: Path) -> None:
        scaffold_treatment("0a", data_dir=data_dir)
        guide = data_dir / "transcripts" / "treatment-0a" / "session_guide.md"
        original = guide.read_text()
        guide.write_text("stale")

        scaffold_treatment("0a", data_dir=data_dir)
        assert guide.read_text() == original
