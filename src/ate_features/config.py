"""Load and validate experiment configuration from YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from ate_features.models import (
    CorrelationPair,
    ExecutionConfig,
    Feature,
    FeatureAssignment,
    FeatureAssignments,
    FeaturePortfolio,
    Treatment,
    TreatmentConfig,
    TreatmentDimensions,
)

DEFAULT_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def load_features(config_dir: Path = DEFAULT_CONFIG_DIR) -> FeaturePortfolio:
    """Load feature portfolio from features.yaml."""
    features_path = config_dir / "features.yaml"
    if not features_path.exists():
        msg = f"features.yaml not found at {features_path}"
        raise FileNotFoundError(msg)

    with open(features_path) as f:
        raw = yaml.safe_load(f)

    features = [Feature(**feat) for feat in raw.get("features", [])]

    return FeaturePortfolio(
        langgraph_pin=raw["langgraph_pin"],
        langgraph_pin_date=raw["langgraph_pin_date"],
        features=features,
    )


def load_treatments(config_dir: Path = DEFAULT_CONFIG_DIR) -> TreatmentConfig:
    """Load treatment configuration from treatments.yaml."""
    treatments_path = config_dir / "treatments.yaml"
    if not treatments_path.exists():
        msg = f"treatments.yaml not found at {treatments_path}"
        raise FileNotFoundError(msg)

    with open(treatments_path) as f:
        raw = yaml.safe_load(f)

    treatments = []
    for t in raw.get("treatments", []):
        treatments.append(
            Treatment(
                id=t["id"],
                label=t["label"],
                paired_with=t.get("paired_with"),
                dimensions=TreatmentDimensions(**t["dimensions"]),
                execution=ExecutionConfig(**t["execution"]),
            )
        )

    explicit_raw = raw.get("feature_assignments", {}).get("explicit", {})
    feature_assignments = FeatureAssignments(
        explicit=FeatureAssignment(**explicit_raw),
    )

    correlation_pairs = [
        CorrelationPair(**pair) for pair in raw.get("correlation_pairs", [])
    ]

    return TreatmentConfig(
        treatments=treatments,
        feature_assignments=feature_assignments,
        correlation_pairs=correlation_pairs,
    )


_SPECIALIZATION_FILES: dict[int, str] = {
    1: "serde_types_and_state_channels.md",
    2: "serde_pydantic_and_state_reducers.md",
    3: "serde_enums_and_stream_emission.md",
    4: "serde_nested_and_stream_dedup.md",
}


def load_specialization(
    agent_num: int, config_dir: Path = DEFAULT_CONFIG_DIR
) -> str:
    """Load specialization context for an agent role (1-4)."""
    if agent_num not in _SPECIALIZATION_FILES:
        msg = f"agent_num must be 1-4, got {agent_num}"
        raise ValueError(msg)

    filename = _SPECIALIZATION_FILES[agent_num]
    spec_path = config_dir / "specializations" / filename
    if not spec_path.exists():
        msg = f"Specialization file not found at {spec_path}"
        raise FileNotFoundError(msg)

    return spec_path.read_text()


def load_scoring_config(
    config_dir: Path = DEFAULT_CONFIG_DIR,
) -> dict[str, object]:
    """Load scoring configuration (weights, thresholds) from YAML."""
    scoring_path = config_dir / "scoring.yaml"
    if not scoring_path.exists():
        msg = f"scoring.yaml not found at {scoring_path}"
        raise FileNotFoundError(msg)

    with open(scoring_path) as f:
        result: dict[str, object] = yaml.safe_load(f)
    return result


def load_communication_nudges(
    config_dir: Path = DEFAULT_CONFIG_DIR,
) -> dict[str, dict[str, str]]:
    """Load communication nudge prompts from YAML."""
    nudges_path = config_dir / "prompts" / "communication_nudges.yaml"
    if not nudges_path.exists():
        msg = f"communication_nudges.yaml not found at {nudges_path}"
        raise FileNotFoundError(msg)

    with open(nudges_path) as f:
        result: dict[str, dict[str, str]] = yaml.safe_load(f)
    return result
