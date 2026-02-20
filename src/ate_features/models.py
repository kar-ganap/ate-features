"""Data models for the Agent Teams Eval (Feature Implementation) experiment."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# --- Enums ---


class Subsystem(StrEnum):
    SERIALIZER = "serializer"
    STATE = "state"
    GRAPH = "graph"
    STREAMING = "streaming"


class AcceptanceTier(StrEnum):
    T1_BASIC = "t1_basic"
    T2_EDGE = "t2_edge"
    T3_QUALITY = "t3_quality"
    T4_SMOKE = "t4_smoke"


class Decomposition(StrEnum):
    EXPLICIT = "explicit"
    AUTONOMOUS = "autonomous"


class PromptSpecificity(StrEnum):
    DETAILED = "detailed"
    VAGUE = "vague"


class TeamSize(StrEnum):
    ONE_BY_EIGHT = "1x8"
    FOUR_BY_TWO = "4x2"
    EIGHT_BY_ONE = "8x1"


class CommunicationMode(StrEnum):
    NEUTRAL = "neutral"
    ENCOURAGE = "encourage"
    DISCOURAGE = "discourage"


class Specialization(StrEnum):
    VANILLA = "vanilla"
    SPECIALIZED = "specialized"


class ExecutionMode(StrEnum):
    INTERACTIVE = "interactive"


# --- Feature Models ---


class Feature(BaseModel):
    """A LangGraph feature in the experiment portfolio."""

    id: str
    title: str
    subsystem: Subsystem
    spec: str


class FeaturePortfolio(BaseModel):
    """Complete feature portfolio with LangGraph pin information."""

    langgraph_pin: str
    langgraph_pin_date: str
    features: list[Feature]

    def get_feature(self, feature_id: str) -> Feature | None:
        for feature in self.features:
            if feature.id == feature_id:
                return feature
        return None


# --- Treatment Models ---


class TreatmentDimensions(BaseModel):
    """Experimental dimension values for a treatment."""

    decomposition: Decomposition
    prompt_specificity: PromptSpecificity
    delegate_mode: bool | None = None
    team_size: TeamSize
    communication: CommunicationMode | None = None
    specialization: Specialization = Specialization.VANILLA


class ExecutionConfig(BaseModel):
    """Execution configuration for a treatment."""

    mode: ExecutionMode
    soft_budget: str | None = None


class Treatment(BaseModel):
    """A treatment in the experiment."""

    id: int | str
    label: str
    paired_with: int | str | None = None
    dimensions: TreatmentDimensions
    execution: ExecutionConfig


class CorrelationPair(BaseModel):
    """A correlation pair between two features sharing a subsystem."""

    name: str
    feature_a: str
    feature_b: str
    shared: str


class FeatureAssignment(BaseModel):
    """Feature assignment for explicit treatments."""

    agent_1: list[str]
    agent_2: list[str]
    agent_3: list[str]
    agent_4: list[str]


class FeatureAssignments(BaseModel):
    """Feature assignments for all treatment types."""

    explicit: FeatureAssignment
    autonomous: None = None


class TreatmentConfig(BaseModel):
    """Complete treatment configuration."""

    treatments: list[Treatment]
    feature_assignments: FeatureAssignments
    correlation_pairs: list[CorrelationPair]


# --- Score Models ---


class TieredScore(BaseModel):
    """Tiered acceptance test score for a feature x treatment."""

    feature_id: str
    treatment_id: int | str
    t1_passed: int = Field(ge=0)
    t1_total: int = Field(ge=0)
    t2_passed: int = Field(ge=0)
    t2_total: int = Field(ge=0)
    t3_passed: int = Field(ge=0)
    t3_total: int = Field(ge=0)
    t4_passed: int = Field(default=0, ge=0)
    t4_total: int = Field(default=0, ge=0)

    @property
    def t1_score(self) -> float:
        return self.t1_passed / self.t1_total if self.t1_total > 0 else 0.0

    @property
    def t2_score(self) -> float:
        return self.t2_passed / self.t2_total if self.t2_total > 0 else 0.0

    @property
    def t3_score(self) -> float:
        return self.t3_passed / self.t3_total if self.t3_total > 0 else 0.0

    @property
    def t4_score(self) -> float:
        return self.t4_passed / self.t4_total if self.t4_total > 0 else 0.0


# --- Run Tracking ---


class RunMetadata(BaseModel):
    """Metadata for a single treatment execution session."""

    treatment_id: int | str
    feature_ids: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    wall_clock_seconds: float | None = None
    session_id: str | None = None
    model: str | None = None
    mode: ExecutionMode
    agent_teams_enabled: bool = False
    team_size: TeamSize | None = None
    notes: str | None = None
