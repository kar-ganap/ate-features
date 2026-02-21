"""Tests for composite scoring on TieredScore."""

from ate_features.models import TieredScore

DEFAULT_WEIGHTS = {"t1": 0.15, "t2": 0.35, "t3": 0.30, "t4": 0.20}


class TestComposite:
    def test_perfect_score(self) -> None:
        score = TieredScore(
            feature_id="F1", treatment_id="0a",
            t1_passed=3, t1_total=3,
            t2_passed=5, t2_total=5,
            t3_passed=3, t3_total=3,
            t4_passed=2, t4_total=2,
        )
        assert score.composite(DEFAULT_WEIGHTS) == 1.0

    def test_zero_score(self) -> None:
        score = TieredScore(
            feature_id="F1", treatment_id="0a",
            t1_passed=0, t1_total=3,
            t2_passed=0, t2_total=5,
            t3_passed=0, t3_total=3,
            t4_passed=0, t4_total=2,
        )
        assert score.composite(DEFAULT_WEIGHTS) == 0.0

    def test_partial_score(self) -> None:
        score = TieredScore(
            feature_id="F1", treatment_id="0a",
            t1_passed=3, t1_total=3,   # 1.0 × 0.15 = 0.15
            t2_passed=0, t2_total=5,   # 0.0 × 0.35 = 0.00
            t3_passed=0, t3_total=3,   # 0.0 × 0.30 = 0.00
            t4_passed=0, t4_total=2,   # 0.0 × 0.20 = 0.00
        )
        assert abs(score.composite(DEFAULT_WEIGHTS) - 0.15) < 1e-9

    def test_weighted_combination(self) -> None:
        score = TieredScore(
            feature_id="F1", treatment_id="0a",
            t1_passed=3, t1_total=3,   # 1.0 × 0.15 = 0.15
            t2_passed=3, t2_total=5,   # 0.6 × 0.35 = 0.21
            t3_passed=2, t3_total=3,   # 0.667 × 0.30 = 0.20
            t4_passed=1, t4_total=2,   # 0.5 × 0.20 = 0.10
        )
        expected = 0.15 + 0.21 + (2 / 3) * 0.30 + 0.10
        assert abs(score.composite(DEFAULT_WEIGHTS) - expected) < 1e-9

    def test_equal_weights(self) -> None:
        score = TieredScore(
            feature_id="F1", treatment_id="0a",
            t1_passed=1, t1_total=2,
            t2_passed=1, t2_total=2,
            t3_passed=1, t3_total=2,
            t4_passed=1, t4_total=2,
        )
        assert score.composite({"t1": 0.25, "t2": 0.25, "t3": 0.25, "t4": 0.25}) == 0.5

    def test_zero_totals_contribute_zero(self) -> None:
        score = TieredScore(
            feature_id="F1", treatment_id="0a",
            t1_passed=0, t1_total=0,
            t2_passed=0, t2_total=0,
            t3_passed=0, t3_total=0,
            t4_passed=0, t4_total=0,
        )
        assert score.composite(DEFAULT_WEIGHTS) == 0.0
