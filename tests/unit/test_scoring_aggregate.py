"""Tests for score aggregation (per-treatment summaries)."""

from ate_features.models import TieredScore
from ate_features.scoring import summarize_all, summarize_treatment

DEFAULT_WEIGHTS = {"t1": 0.15, "t2": 0.35, "t3": 0.30, "t4": 0.20}


def _make_score(
    feature_id: str,
    treatment_id: int | str,
    *,
    t1: tuple[int, int] = (3, 3),
    t2: tuple[int, int] = (5, 5),
    t3: tuple[int, int] = (3, 3),
    t4: tuple[int, int] = (2, 2),
) -> TieredScore:
    return TieredScore(
        feature_id=feature_id,
        treatment_id=treatment_id,
        t1_passed=t1[0], t1_total=t1[1],
        t2_passed=t2[0], t2_total=t2[1],
        t3_passed=t3[0], t3_total=t3[1],
        t4_passed=t4[0], t4_total=t4[1],
    )


class TestSummarizeTreatment:
    def test_perfect_scores(self) -> None:
        scores = [_make_score(f"F{i}", "0a") for i in range(1, 9)]
        summary = summarize_treatment(scores, DEFAULT_WEIGHTS)
        assert summary["treatment_id"] == "0a"
        assert summary["mean_composite"] == 1.0
        assert summary["n_features"] == 8

    def test_mixed_scores(self) -> None:
        scores = [
            _make_score("F1", "0a"),  # perfect = 1.0
            _make_score("F2", "0a", t1=(0, 3), t2=(0, 5), t3=(0, 3), t4=(0, 2)),  # 0.0
        ]
        summary = summarize_treatment(scores, DEFAULT_WEIGHTS)
        assert summary["mean_composite"] == 0.5
        assert summary["min_composite"] == 0.0
        assert summary["max_composite"] == 1.0

    def test_per_feature_composites(self) -> None:
        scores = [
            _make_score("F1", "0a"),
            _make_score("F2", "0a", t2=(3, 5)),
        ]
        summary = summarize_treatment(scores, DEFAULT_WEIGHTS)
        composites = summary["per_feature"]
        assert composites["F1"] == 1.0
        assert abs(composites["F2"] - (0.15 + 0.6 * 0.35 + 0.30 + 0.20)) < 1e-9

    def test_single_feature(self) -> None:
        scores = [_make_score("F1", "0a", t1=(1, 3))]
        summary = summarize_treatment(scores, DEFAULT_WEIGHTS)
        assert summary["n_features"] == 1
        assert summary["min_composite"] == summary["max_composite"]

    def test_empty_scores(self) -> None:
        summary = summarize_treatment([], DEFAULT_WEIGHTS)
        assert summary["n_features"] == 0
        assert summary["mean_composite"] == 0.0


class TestSummarizeAll:
    def test_multiple_treatments(self) -> None:
        all_scores = {
            "0a": [_make_score("F1", "0a")],
            "0b": [_make_score("F1", "0b", t1=(0, 3))],
        }
        result = summarize_all(all_scores, DEFAULT_WEIGHTS)
        assert len(result) == 2
        assert "0a" in result
        assert "0b" in result
        assert result["0a"]["mean_composite"] == 1.0

    def test_empty_dict(self) -> None:
        result = summarize_all({}, DEFAULT_WEIGHTS)
        assert result == {}
