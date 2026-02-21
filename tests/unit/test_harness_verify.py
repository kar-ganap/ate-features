"""Tests for patch verification."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ate_features.harness import verify_patches
from ate_features.models import PatchStatus


@pytest.fixture
def patches_dir(tmp_path: Path) -> Path:
    """Create a data directory with patches subdirectory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


class TestVerifyPatches:
    def test_all_missing(self, patches_dir: Path) -> None:
        result = verify_patches("0a", data_dir=patches_dir)
        assert all(v == PatchStatus.MISSING for v in result.values())
        assert len(result) == 8  # F1-F8

    def test_all_valid_without_langgraph(self, patches_dir: Path) -> None:
        """Without langgraph_dir, non-empty files are VALID."""
        patch_dir = patches_dir / "patches" / "treatment-0a"
        patch_dir.mkdir(parents=True)
        for i in range(1, 9):
            (patch_dir / f"F{i}.patch").write_text("diff --git a/foo b/foo\n")
        result = verify_patches("0a", data_dir=patches_dir)
        assert all(v == PatchStatus.VALID for v in result.values())

    def test_empty_patch(self, patches_dir: Path) -> None:
        patch_dir = patches_dir / "patches" / "treatment-1"
        patch_dir.mkdir(parents=True)
        (patch_dir / "F1.patch").write_text("")
        result = verify_patches(1, data_dir=patches_dir)
        assert result["F1"] == PatchStatus.EMPTY
        assert result["F2"] == PatchStatus.MISSING

    def test_invalid_patch_with_langgraph(
        self, patches_dir: Path, tmp_path: Path
    ) -> None:
        """With langgraph_dir, git apply --check is run."""
        patch_dir = patches_dir / "patches" / "treatment-0a"
        patch_dir.mkdir(parents=True)
        (patch_dir / "F1.patch").write_text("diff --git a/foo b/foo\n")

        lg_dir = tmp_path / "langgraph"
        lg_dir.mkdir()

        with patch("ate_features.harness.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1  # --check fails
            result = verify_patches(
                "0a", langgraph_dir=lg_dir, data_dir=patches_dir
            )
        assert result["F1"] == PatchStatus.INVALID

    def test_valid_patch_with_langgraph(
        self, patches_dir: Path, tmp_path: Path
    ) -> None:
        patch_dir = patches_dir / "patches" / "treatment-0a"
        patch_dir.mkdir(parents=True)
        (patch_dir / "F1.patch").write_text("diff --git a/foo b/foo\n")

        lg_dir = tmp_path / "langgraph"
        lg_dir.mkdir()

        with patch("ate_features.harness.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0  # --check passes
            result = verify_patches(
                "0a", langgraph_dir=lg_dir, data_dir=patches_dir
            )
        assert result["F1"] == PatchStatus.VALID

    def test_partial_patches(self, patches_dir: Path) -> None:
        patch_dir = patches_dir / "patches" / "treatment-2a"
        patch_dir.mkdir(parents=True)
        (patch_dir / "F1.patch").write_text("diff\n")
        (patch_dir / "F3.patch").write_text("diff\n")
        (patch_dir / "F5.patch").write_text("")  # empty
        result = verify_patches("2a", data_dir=patches_dir)
        assert result["F1"] == PatchStatus.VALID
        assert result["F2"] == PatchStatus.MISSING
        assert result["F3"] == PatchStatus.VALID
        assert result["F5"] == PatchStatus.EMPTY

    def test_string_treatment_id(self, patches_dir: Path) -> None:
        patch_dir = patches_dir / "patches" / "treatment-0b"
        patch_dir.mkdir(parents=True)
        (patch_dir / "F1.patch").write_text("diff\n")
        result = verify_patches("0b", data_dir=patches_dir)
        assert result["F1"] == PatchStatus.VALID
        assert result["F2"] == PatchStatus.MISSING
