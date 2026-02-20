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
