"""Tests for patch management (apply_patch, revert_langgraph)."""

import subprocess
from pathlib import Path

import pytest

from ate_features.harness import apply_patch, revert_langgraph


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with a committed file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, check=True, capture_output=True,
    )
    (repo / "file.py").write_text("original\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo, check=True, capture_output=True,
    )
    return repo


@pytest.fixture
def patch_file(tmp_path: Path, git_repo: Path) -> Path:
    """Create a valid patch file."""
    patch = tmp_path / "fix.patch"
    patch.write_text(
        "diff --git a/file.py b/file.py\n"
        "--- a/file.py\n"
        "+++ b/file.py\n"
        "@@ -1 +1 @@\n"
        "-original\n"
        "+modified\n"
    )
    return patch


class TestApplyPatch:
    def test_applies_valid_patch(self, git_repo: Path, patch_file: Path) -> None:
        result = apply_patch(patch_file, git_repo)
        assert result is True
        assert (git_repo / "file.py").read_text() == "modified\n"

    def test_returns_false_for_invalid_patch(self, git_repo: Path, tmp_path: Path) -> None:
        bad_patch = tmp_path / "bad.patch"
        bad_patch.write_text("not a valid patch\n")
        result = apply_patch(bad_patch, git_repo)
        assert result is False

    def test_returns_false_for_already_applied(self, git_repo: Path, patch_file: Path) -> None:
        apply_patch(patch_file, git_repo)
        # Apply same patch again
        result = apply_patch(patch_file, git_repo)
        assert result is False

    def test_original_unchanged_on_failure(self, git_repo: Path, tmp_path: Path) -> None:
        bad_patch = tmp_path / "bad.patch"
        bad_patch.write_text("not a valid patch\n")
        apply_patch(bad_patch, git_repo)
        assert (git_repo / "file.py").read_text() == "original\n"


class TestRevertLanggraph:
    def test_reverts_modified_file(self, git_repo: Path) -> None:
        (git_repo / "file.py").write_text("modified\n")
        revert_langgraph(git_repo)
        assert (git_repo / "file.py").read_text() == "original\n"

    def test_removes_untracked_files(self, git_repo: Path) -> None:
        (git_repo / "new_file.txt").write_text("untracked\n")
        revert_langgraph(git_repo)
        assert not (git_repo / "new_file.txt").exists()

    def test_removes_untracked_directories(self, git_repo: Path) -> None:
        subdir = git_repo / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("nested\n")
        revert_langgraph(git_repo)
        assert not subdir.exists()

    def test_idempotent_on_clean_repo(self, git_repo: Path) -> None:
        revert_langgraph(git_repo)
        assert (git_repo / "file.py").read_text() == "original\n"
