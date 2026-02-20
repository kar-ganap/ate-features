"""Tests for Phase 2 model additions: T4 tier, RunMetadata."""

from datetime import UTC, datetime

from ate_features.models import (
    AcceptanceTier,
    ExecutionMode,
    RunMetadata,
    TeamSize,
    TieredScore,
)


class TestAcceptanceTierT4:
    def test_t4_smoke_value(self) -> None:
        assert AcceptanceTier.T4_SMOKE == "t4_smoke"

    def test_all_tiers(self) -> None:
        values = [t.value for t in AcceptanceTier]
        assert "t1_basic" in values
        assert "t2_edge" in values
        assert "t3_quality" in values
        assert "t4_smoke" in values


class TestTieredScoreT4:
    def test_t4_score(self) -> None:
        score = TieredScore(
            feature_id="F1",
            treatment_id="0a",
            t1_passed=3, t1_total=3,
            t2_passed=4, t2_total=5,
            t3_passed=2, t3_total=3,
            t4_passed=1, t4_total=2,
        )
        assert score.t4_score == 0.5

    def test_t4_score_zero_total(self) -> None:
        score = TieredScore(
            feature_id="F1",
            treatment_id="0a",
            t1_passed=0, t1_total=0,
            t2_passed=0, t2_total=0,
            t3_passed=0, t3_total=0,
            t4_passed=0, t4_total=0,
        )
        assert score.t4_score == 0.0

    def test_t4_defaults_to_zero(self) -> None:
        """Backward compat: TieredScore without t4 fields still works."""
        score = TieredScore(
            feature_id="F1",
            treatment_id="0a",
            t1_passed=3, t1_total=3,
            t2_passed=0, t2_total=0,
            t3_passed=0, t3_total=0,
        )
        assert score.t4_passed == 0
        assert score.t4_total == 0
        assert score.t4_score == 0.0

    def test_all_tiers_score(self) -> None:
        score = TieredScore(
            feature_id="F5",
            treatment_id=7,
            t1_passed=3, t1_total=3,
            t2_passed=5, t2_total=5,
            t3_passed=3, t3_total=3,
            t4_passed=2, t4_total=2,
        )
        assert score.t1_score == 1.0
        assert score.t2_score == 1.0
        assert score.t3_score == 1.0
        assert score.t4_score == 1.0


class TestRunMetadata:
    def test_create_minimal(self) -> None:
        meta = RunMetadata(
            treatment_id="0b",
            mode=ExecutionMode.INTERACTIVE,
        )
        assert meta.treatment_id == "0b"
        assert meta.feature_ids == []
        assert meta.started_at is None
        assert meta.completed_at is None
        assert meta.session_id is None
        assert meta.agent_teams_enabled is False

    def test_create_full(self) -> None:
        now = datetime.now(tz=UTC)
        meta = RunMetadata(
            treatment_id=1,
            feature_ids=["F1", "F2", "F5", "F6"],
            started_at=now,
            completed_at=now,
            wall_clock_seconds=300.0,
            session_id="abc-123",
            model="claude-opus-4-6",
            mode=ExecutionMode.INTERACTIVE,
            agent_teams_enabled=True,
            team_size=TeamSize.FOUR_BY_TWO,
            notes="Test run",
        )
        assert meta.treatment_id == 1
        assert len(meta.feature_ids) == 4
        assert meta.agent_teams_enabled is True
        assert meta.team_size == TeamSize.FOUR_BY_TWO

    def test_defaults(self) -> None:
        meta = RunMetadata(
            treatment_id="0a",
            mode=ExecutionMode.INTERACTIVE,
        )
        assert meta.wall_clock_seconds is None
        assert meta.model is None
        assert meta.team_size is None
        assert meta.notes is None

    def test_model_dump_serializable(self) -> None:
        now = datetime.now(tz=UTC)
        meta = RunMetadata(
            treatment_id=1,
            feature_ids=["F1", "F5"],
            started_at=now,
            mode=ExecutionMode.INTERACTIVE,
            agent_teams_enabled=True,
            team_size=TeamSize.FOUR_BY_TWO,
        )
        dumped = meta.model_dump(mode="json")
        assert isinstance(dumped, dict)
        assert dumped["treatment_id"] == 1
        assert dumped["feature_ids"] == ["F1", "F5"]
        assert dumped["agent_teams_enabled"] is True
