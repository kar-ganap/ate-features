"""Tests for scoring configuration loading."""

from ate_features.config import load_scoring_config


class TestLoadScoringConfig:
    def test_loads_weights(self) -> None:
        config = load_scoring_config()
        assert "weights" in config
        weights = config["weights"]
        assert "t1" in weights
        assert "t2" in weights
        assert "t3" in weights
        assert "t4" in weights

    def test_weights_sum_to_one(self) -> None:
        config = load_scoring_config()
        w = config["weights"]
        total = w["t1"] + w["t2"] + w["t3"] + w["t4"]
        assert abs(total - 1.0) < 1e-9

    def test_all_weights_non_negative(self) -> None:
        config = load_scoring_config()
        for tier, weight in config["weights"].items():
            assert weight >= 0, f"Weight for {tier} must be non-negative"

    def test_has_wave2_threshold(self) -> None:
        config = load_scoring_config()
        assert "wave2_cv_threshold" in config
        assert config["wave2_cv_threshold"] > 0
