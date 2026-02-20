"""Execution harness for treatment sessions."""

from __future__ import annotations

import json
from pathlib import Path

from ate_features.models import RunMetadata, TeamSize, Treatment

DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_run_dir(
    treatment_id: int | str,
    feature_id: str | None = None,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> Path:
    """Return the run directory for a treatment (and optional feature)."""
    base = data_dir / "transcripts" / f"treatment-{treatment_id}"
    if feature_id is not None:
        return base / feature_id
    return base


def get_patch_path(
    treatment_id: int | str,
    feature_id: str,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> Path:
    """Return the patch file path for a treatment × feature."""
    return data_dir / "patches" / f"treatment-{treatment_id}" / f"{feature_id}.patch"


def save_metadata(metadata: RunMetadata, run_dir: Path) -> Path:
    """Write metadata.json into the run directory, creating parents."""
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "metadata.json"
    path.write_text(json.dumps(metadata.model_dump(mode="json"), indent=2))
    return path


def is_per_feature_treatment(treatment: Treatment) -> bool:
    """True if each feature runs in its own session (8×1 without Agent Teams)."""
    return (
        treatment.dimensions.team_size == TeamSize.EIGHT_BY_ONE
        and treatment.dimensions.delegate_mode is None
    )


def uses_agent_teams(treatment: Treatment) -> bool:
    """True if the treatment uses Agent Teams (delegate_mode is not None)."""
    return treatment.dimensions.delegate_mode is not None
