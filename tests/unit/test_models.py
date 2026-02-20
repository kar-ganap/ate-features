"""Tests for ate_features.models."""

from ate_features.models import (
    AcceptanceTier,
    Feature,
    FeaturePortfolio,
    Subsystem,
    TieredScore,
)


class TestSubsystem:
    def test_values(self) -> None:
        assert Subsystem.SERIALIZER == "serializer"
        assert Subsystem.STATE == "state"
        assert Subsystem.GRAPH == "graph"
        assert Subsystem.STREAMING == "streaming"


class TestAcceptanceTier:
    def test_values(self) -> None:
        assert AcceptanceTier.T1_BASIC == "t1_basic"
        assert AcceptanceTier.T2_EDGE == "t2_edge"
        assert AcceptanceTier.T3_QUALITY == "t3_quality"


class TestFeature:
    def test_create(self) -> None:
        f = Feature(
            id="F1",
            title="Test feature",
            subsystem=Subsystem.SERIALIZER,
            spec="Do something.",
        )
        assert f.id == "F1"
        assert f.subsystem == Subsystem.SERIALIZER


class TestFeaturePortfolio:
    def test_get_feature(self) -> None:
        f1 = Feature(id="F1", title="A", subsystem=Subsystem.SERIALIZER, spec="s")
        f2 = Feature(id="F2", title="B", subsystem=Subsystem.STATE, spec="s")
        portfolio = FeaturePortfolio(
            langgraph_pin="abc123",
            langgraph_pin_date="2026-01-01",
            features=[f1, f2],
        )
        assert portfolio.get_feature("F1") == f1
        assert portfolio.get_feature("F2") == f2
        assert portfolio.get_feature("F99") is None


class TestTieredScore:
    def test_scores(self) -> None:
        score = TieredScore(
            feature_id="F1",
            treatment_id="0a",
            t1_passed=3,
            t1_total=5,
            t2_passed=1,
            t2_total=3,
            t3_passed=0,
            t3_total=2,
        )
        assert score.t1_score == 3 / 5
        assert score.t2_score == 1 / 3
        assert score.t3_score == 0.0

    def test_zero_total(self) -> None:
        score = TieredScore(
            feature_id="F1",
            treatment_id="0a",
            t1_passed=0,
            t1_total=0,
            t2_passed=0,
            t2_total=0,
            t3_passed=0,
            t3_total=0,
        )
        assert score.t1_score == 0.0
        assert score.t2_score == 0.0
        assert score.t3_score == 0.0
