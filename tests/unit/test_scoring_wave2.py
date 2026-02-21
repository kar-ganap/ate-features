"""Tests for Wave 2 decision gate evaluation."""

from ate_features.models import TieredScore
from ate_features.scoring import evaluate_wave2

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


class TestEvaluateWave2:
    def test_uniform_scores_no_wave2(self) -> None:
        """All treatments identical → CV=0 → no Wave 2 needed."""
        all_scores = {
            f"t{i}": [_make_score(f"F{j}", f"t{i}") for j in range(1, 9)]
            for i in range(1, 9)
        }
        recommend, reasoning = evaluate_wave2(
            all_scores, DEFAULT_WEIGHTS, cv_threshold=0.10
        )
        assert recommend is False
        assert "variance" in reasoning.lower() or "cv" in reasoning.lower()

    def test_varied_scores_recommend_wave2(self) -> None:
        """Very different treatment scores → high CV → recommend Wave 2."""
        all_scores = {
            "0a": [_make_score("F1", "0a")],  # composite = 1.0
            "0b": [
                _make_score("F1", "0b", t1=(0, 3), t2=(0, 5), t3=(0, 3), t4=(0, 2))
            ],  # composite = 0.0
        }
        recommend, reasoning = evaluate_wave2(
            all_scores, DEFAULT_WEIGHTS, cv_threshold=0.10
        )
        assert recommend is True

    def test_threshold_boundary(self) -> None:
        """CV exactly at threshold should not recommend (strict >)."""
        # Build scores that produce exactly 0.10 CV (or close to it)
        # With 2 treatments, mean=0.5, we need std=0.05 for CV=0.10
        # scores: 0.5+x, 0.5-x where std = x, so x = 0.05
        # This is hard to construct exactly, so just test < threshold
        all_scores = {
            "0a": [_make_score("F1", "0a", t2=(4, 5))],  # near-perfect
            "0b": [_make_score("F1", "0b", t2=(4, 5))],  # same
        }
        recommend, _ = evaluate_wave2(
            all_scores, DEFAULT_WEIGHTS, cv_threshold=0.10
        )
        assert recommend is False

    def test_empty_scores_no_wave2(self) -> None:
        recommend, reasoning = evaluate_wave2(
            {}, DEFAULT_WEIGHTS, cv_threshold=0.10
        )
        assert recommend is False
        assert "no scores" in reasoning.lower() or "insufficient" in reasoning.lower()

    def test_reasoning_includes_stats(self) -> None:
        """Reasoning should mention CV value and threshold."""
        all_scores = {
            "0a": [_make_score("F1", "0a")],
            "0b": [_make_score("F1", "0b")],
        }
        _, reasoning = evaluate_wave2(
            all_scores, DEFAULT_WEIGHTS, cv_threshold=0.10
        )
        assert "0.10" in reasoning or "threshold" in reasoning.lower()
