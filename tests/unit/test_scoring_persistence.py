"""Tests for score persistence (save/load)."""

import json
from pathlib import Path

from ate_features.models import TieredScore
from ate_features.scoring import load_all_scores, load_scores, save_scores


def _make_score(feature_id: str, treatment_id: int | str) -> TieredScore:
    return TieredScore(
        feature_id=feature_id,
        treatment_id=treatment_id,
        t1_passed=3, t1_total=3,
        t2_passed=4, t2_total=5,
        t3_passed=2, t3_total=3,
        t4_passed=1, t4_total=2,
    )


class TestSaveScores:
    def test_creates_json_file(self, tmp_path: Path) -> None:
        scores = [_make_score("F1", "0a"), _make_score("F2", "0a")]
        path = save_scores(scores, "0a", data_dir=tmp_path)
        assert path.exists()
        assert path.name == "treatment-0a.json"
        assert path.parent.name == "scores"

    def test_json_is_valid(self, tmp_path: Path) -> None:
        scores = [_make_score("F1", "0a")]
        path = save_scores(scores, "0a", data_dir=tmp_path)
        data = json.loads(path.read_text())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["feature_id"] == "F1"
        assert data[0]["t2_passed"] == 4

    def test_creates_scores_directory(self, tmp_path: Path) -> None:
        scores = [_make_score("F1", 3)]
        save_scores(scores, 3, data_dir=tmp_path)
        assert (tmp_path / "scores").is_dir()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        scores_v1 = [_make_score("F1", "0a")]
        save_scores(scores_v1, "0a", data_dir=tmp_path)
        scores_v2 = [_make_score("F1", "0a"), _make_score("F2", "0a")]
        path = save_scores(scores_v2, "0a", data_dir=tmp_path)
        data = json.loads(path.read_text())
        assert len(data) == 2


class TestLoadScores:
    def test_round_trip(self, tmp_path: Path) -> None:
        original = [_make_score("F1", "0a"), _make_score("F2", "0a")]
        save_scores(original, "0a", data_dir=tmp_path)
        loaded = load_scores("0a", data_dir=tmp_path)
        assert len(loaded) == 2
        assert loaded[0].feature_id == "F1"
        assert loaded[1].feature_id == "F2"
        assert loaded[0].t2_passed == 4

    def test_returns_tiered_score_objects(self, tmp_path: Path) -> None:
        save_scores([_make_score("F1", "0a")], "0a", data_dir=tmp_path)
        loaded = load_scores("0a", data_dir=tmp_path)
        assert isinstance(loaded[0], TieredScore)
        assert loaded[0].t1_score == 1.0

    def test_missing_treatment_raises(self, tmp_path: Path) -> None:
        import pytest

        with pytest.raises(FileNotFoundError):
            load_scores("nonexistent", data_dir=tmp_path)

    def test_integer_treatment_id(self, tmp_path: Path) -> None:
        save_scores([_make_score("F1", 3)], 3, data_dir=tmp_path)
        loaded = load_scores(3, data_dir=tmp_path)
        assert loaded[0].treatment_id == 3


class TestLoadAllScores:
    def test_loads_multiple_treatments(self, tmp_path: Path) -> None:
        save_scores([_make_score("F1", "0a")], "0a", data_dir=tmp_path)
        save_scores([_make_score("F1", "0b")], "0b", data_dir=tmp_path)
        all_scores = load_all_scores(data_dir=tmp_path)
        assert len(all_scores) == 2
        assert "0a" in all_scores
        assert "0b" in all_scores

    def test_empty_directory(self, tmp_path: Path) -> None:
        all_scores = load_all_scores(data_dir=tmp_path)
        assert all_scores == {}

    def test_returns_tiered_scores(self, tmp_path: Path) -> None:
        save_scores(
            [_make_score("F1", "0a"), _make_score("F2", "0a")],
            "0a",
            data_dir=tmp_path,
        )
        all_scores = load_all_scores(data_dir=tmp_path)
        assert len(all_scores["0a"]) == 2
        assert all(isinstance(s, TieredScore) for s in all_scores["0a"])

    def test_ignores_non_treatment_files(self, tmp_path: Path) -> None:
        scores_dir = tmp_path / "scores"
        scores_dir.mkdir()
        (scores_dir / "readme.txt").write_text("not a score file")
        save_scores([_make_score("F1", "0a")], "0a", data_dir=tmp_path)
        all_scores = load_all_scores(data_dir=tmp_path)
        assert len(all_scores) == 1
