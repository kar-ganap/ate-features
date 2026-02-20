"""Tests for ate_features.config."""

from ate_features.config import load_features, load_treatments


class TestLoadFeatures:
    def test_loads_all_features(self) -> None:
        portfolio = load_features()
        assert len(portfolio.features) == 8
        assert portfolio.langgraph_pin == "b0f14649e0669a6399cb790d23672591a2a52884"

    def test_feature_ids(self) -> None:
        portfolio = load_features()
        ids = [f.id for f in portfolio.features]
        assert ids == ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]

    def test_subsystems(self) -> None:
        portfolio = load_features()
        subsystems = {f.subsystem for f in portfolio.features}
        assert subsystems == {"serializer", "state", "streaming"}


class TestLoadTreatments:
    def test_loads_all_treatments(self) -> None:
        config = load_treatments()
        assert len(config.treatments) == 8

    def test_treatment_ids(self) -> None:
        config = load_treatments()
        ids = [t.id for t in config.treatments]
        assert ids == ["0a", "0b", 1, "2a", "2b", 3, 4, 5]

    def test_correlation_pairs(self) -> None:
        config = load_treatments()
        assert len(config.correlation_pairs) == 4
        names = [p.name for p in config.correlation_pairs]
        assert "serializer_new_types" in names
        assert "state_management" in names

    def test_feature_assignments(self) -> None:
        config = load_treatments()
        explicit = config.feature_assignments.explicit
        assert explicit.agent_1 == ["F1", "F5"]
        assert explicit.agent_2 == ["F2", "F6"]
        assert explicit.agent_3 == ["F3", "F7"]
        assert explicit.agent_4 == ["F4", "F8"]
