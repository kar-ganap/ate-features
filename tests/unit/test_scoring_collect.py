"""Tests for score collection pipeline (apply → test → parse → revert)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ate_features.models import TieredScore
from ate_features.scoring import collect_scores

SAMPLE_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="4">
    <testcase classname="tests.acceptance.test_f1.TestT1Basic" name="a"/>
    <testcase classname="tests.acceptance.test_f1.TestT2EdgeCases" name="b">
      <failure>fail</failure>
    </testcase>
    <testcase classname="tests.acceptance.test_f1.TestT3Quality" name="c"/>
    <testcase classname="tests.acceptance.test_f1.TestT4Smoke" name="d"/>
  </testsuite>
</testsuites>
"""


@pytest.fixture()
def setup_dirs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create langgraph dir, data dir with patches, and return both."""
    langgraph_dir = tmp_path / "langgraph"
    langgraph_dir.mkdir()
    data_dir = tmp_path / "data"

    # Create patch files for F1 and F2
    for fid in ["F1", "F2"]:
        patch_dir = data_dir / "patches" / "treatment-0a"
        patch_dir.mkdir(parents=True, exist_ok=True)
        (patch_dir / f"{fid}.patch").write_text("fake patch")

    return langgraph_dir, data_dir, tmp_path


class TestCollectScores:
    def test_returns_scores_for_each_feature_with_patch(
        self, setup_dirs: tuple[Path, Path, Path]
    ) -> None:
        langgraph_dir, data_dir, _ = setup_dirs

        def fake_run(args: list[str], **kwargs: object) -> MagicMock:
            result = MagicMock()
            result.returncode = 0
            # When pytest is called, write a JUnit XML file
            if args and args[0] == "pytest":
                for arg in args:
                    if arg.startswith("--junitxml="):
                        xml_path = Path(arg.split("=", 1)[1])
                        xml_path.parent.mkdir(parents=True, exist_ok=True)
                        xml_path.write_text(SAMPLE_XML)
                        break
            return result

        with patch("ate_features.scoring.subprocess.run", side_effect=fake_run):
            scores = collect_scores("0a", langgraph_dir, data_dir=data_dir)

        assert len(scores) == 2
        assert all(isinstance(s, TieredScore) for s in scores)
        feature_ids = {s.feature_id for s in scores}
        assert feature_ids == {"F1", "F2"}

    def test_skips_features_without_patches(
        self, setup_dirs: tuple[Path, Path, Path]
    ) -> None:
        langgraph_dir, data_dir, _ = setup_dirs
        # Remove F2 patch
        (data_dir / "patches" / "treatment-0a" / "F2.patch").unlink()

        def fake_run(args: list[str], **kwargs: object) -> MagicMock:
            result = MagicMock()
            result.returncode = 0
            if args and args[0] == "pytest":
                for arg in args:
                    if arg.startswith("--junitxml="):
                        xml_path = Path(arg.split("=", 1)[1])
                        xml_path.parent.mkdir(parents=True, exist_ok=True)
                        xml_path.write_text(SAMPLE_XML)
                        break
            return result

        with patch("ate_features.scoring.subprocess.run", side_effect=fake_run):
            scores = collect_scores("0a", langgraph_dir, data_dir=data_dir)

        assert len(scores) == 1
        assert scores[0].feature_id == "F1"

    def test_persists_scores_to_disk(
        self, setup_dirs: tuple[Path, Path, Path]
    ) -> None:
        langgraph_dir, data_dir, _ = setup_dirs

        def fake_run(args: list[str], **kwargs: object) -> MagicMock:
            result = MagicMock()
            result.returncode = 0
            if args and args[0] == "pytest":
                for arg in args:
                    if arg.startswith("--junitxml="):
                        xml_path = Path(arg.split("=", 1)[1])
                        xml_path.parent.mkdir(parents=True, exist_ok=True)
                        xml_path.write_text(SAMPLE_XML)
                        break
            return result

        with patch("ate_features.scoring.subprocess.run", side_effect=fake_run):
            collect_scores("0a", langgraph_dir, data_dir=data_dir)

        score_file = data_dir / "scores" / "treatment-0a.json"
        assert score_file.exists()

    def test_reverts_after_each_feature(
        self, setup_dirs: tuple[Path, Path, Path]
    ) -> None:
        langgraph_dir, data_dir, _ = setup_dirs
        revert_calls: list[list[str]] = []

        def fake_run(args: list[str], **kwargs: object) -> MagicMock:
            result = MagicMock()
            result.returncode = 0
            if args[:2] == ["git", "checkout"]:
                revert_calls.append(args)
            if args and args[0] == "pytest":
                for arg in args:
                    if arg.startswith("--junitxml="):
                        xml_path = Path(arg.split("=", 1)[1])
                        xml_path.parent.mkdir(parents=True, exist_ok=True)
                        xml_path.write_text(SAMPLE_XML)
                        break
            return result

        with patch("ate_features.scoring.subprocess.run", side_effect=fake_run):
            collect_scores("0a", langgraph_dir, data_dir=data_dir)

        # Should revert after each feature (2 features with patches)
        assert len(revert_calls) == 2

    def test_patch_apply_failure_skips_feature(
        self, setup_dirs: tuple[Path, Path, Path]
    ) -> None:
        langgraph_dir, data_dir, _ = setup_dirs
        call_count = 0

        def fake_run(args: list[str], **kwargs: object) -> MagicMock:
            nonlocal call_count
            result = MagicMock()
            # Fail the first git apply --check
            if args[:2] == ["git", "apply"] and "--check" in args:
                call_count += 1
                result.returncode = 1 if call_count == 1 else 0
                return result
            result.returncode = 0
            if args and args[0] == "pytest":
                for arg in args:
                    if arg.startswith("--junitxml="):
                        xml_path = Path(arg.split("=", 1)[1])
                        xml_path.parent.mkdir(parents=True, exist_ok=True)
                        xml_path.write_text(SAMPLE_XML)
                        break
            return result

        with patch("ate_features.scoring.subprocess.run", side_effect=fake_run):
            scores = collect_scores("0a", langgraph_dir, data_dir=data_dir)

        # Only 1 score — the other feature's patch failed to apply
        assert len(scores) == 1

    def test_no_patches_directory_returns_empty(self, tmp_path: Path) -> None:
        langgraph_dir = tmp_path / "langgraph"
        langgraph_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        scores = collect_scores("0a", langgraph_dir, data_dir=data_dir)
        assert scores == []
