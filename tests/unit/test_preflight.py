"""Tests for preflight checks."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ate_features.harness import preflight_check


@pytest.fixture
def fake_git_dir(tmp_path: Path) -> Path:
    """Create a fake LangGraph directory with .git."""
    git_dir = tmp_path / "langgraph"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()
    return git_dir


class TestPreflightCheck:
    def test_dir_missing(self, tmp_path: Path) -> None:
        result = preflight_check(tmp_path / "nonexistent")
        assert any("not found" in issue.lower() or "not exist" in issue.lower()
                    for issue in result.issues)

    def test_no_git_dir(self, tmp_path: Path) -> None:
        plain_dir = tmp_path / "langgraph"
        plain_dir.mkdir()
        result = preflight_check(plain_dir)
        assert any(".git" in issue for issue in result.issues)

    def test_wrong_commit(self, fake_git_dir: Path) -> None:
        with patch("ate_features.harness.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "deadbeef\n"
            result = preflight_check(
                fake_git_dir, expected_pin="b0f14649"
            )
        assert any("commit" in issue.lower() for issue in result.issues)

    def test_dirty_tree(self, fake_git_dir: Path) -> None:
        with patch("ate_features.harness.subprocess.run") as mock_run:
            def side_effect(cmd, **kwargs):
                mock = type(mock_run.return_value)()
                mock.returncode = 0
                if "rev-parse" in cmd:
                    mock.stdout = "b0f14649\n"
                elif "status" in cmd:
                    mock.stdout = " M libs/langgraph/langgraph/foo.py\n"
                elif "claude" in cmd[0]:
                    mock.stdout = "2.1.50\n"
                else:
                    mock.stdout = ""
                return mock

            mock_run.side_effect = side_effect
            result = preflight_check(
                fake_git_dir, expected_pin="b0f14649"
            )
        assert any("dirty" in issue.lower() or "clean" in issue.lower()
                    for issue in result.issues)

    def test_all_pass(self, fake_git_dir: Path) -> None:
        with patch("ate_features.harness.subprocess.run") as mock_run:
            def side_effect(cmd, **kwargs):
                mock = type(mock_run.return_value)()
                mock.returncode = 0
                if "rev-parse" in cmd:
                    mock.stdout = "b0f14649\n"
                elif "status" in cmd:
                    mock.stdout = ""
                elif "claude" in cmd[0]:
                    mock.stdout = "2.1.50\n"
                else:
                    mock.stdout = ""
                return mock

            mock_run.side_effect = side_effect
            result = preflight_check(
                fake_git_dir, expected_pin="b0f14649"
            )
        assert result.issues == []

    def test_records_cc_version(self, fake_git_dir: Path) -> None:
        with patch("ate_features.harness.subprocess.run") as mock_run:
            def side_effect(cmd, **kwargs):
                mock = type(mock_run.return_value)()
                mock.returncode = 0
                if "rev-parse" in cmd:
                    mock.stdout = "b0f14649\n"
                elif "status" in cmd:
                    mock.stdout = ""
                elif "claude" in cmd[0]:
                    mock.stdout = "2.1.50\n"
                else:
                    mock.stdout = ""
                return mock

            mock_run.side_effect = side_effect
            result = preflight_check(
                fake_git_dir, expected_pin="b0f14649"
            )
        assert result.claude_code_version == "2.1.50"

    def test_cc_version_unknown_on_failure(self, fake_git_dir: Path) -> None:
        with patch("ate_features.harness.subprocess.run") as mock_run:
            def side_effect(cmd, **kwargs):
                mock = type(mock_run.return_value)()
                if "rev-parse" in cmd:
                    mock.returncode = 0
                    mock.stdout = "b0f14649\n"
                elif "status" in cmd:
                    mock.returncode = 0
                    mock.stdout = ""
                elif "claude" in cmd[0]:
                    mock.returncode = 1
                    mock.stdout = ""
                else:
                    mock.returncode = 0
                    mock.stdout = ""
                return mock

            mock_run.side_effect = side_effect
            result = preflight_check(
                fake_git_dir, expected_pin="b0f14649"
            )
        assert result.claude_code_version == "unknown"
        # Should not be an issue — version is informational
        assert result.issues == []

    def test_multiple_issues(self, tmp_path: Path) -> None:
        plain_dir = tmp_path / "langgraph"
        plain_dir.mkdir()
        # No .git dir → should report issue
        result = preflight_check(plain_dir)
        assert len(result.issues) >= 1
