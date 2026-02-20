"""Execution harness for treatment sessions."""

from __future__ import annotations

import json
from pathlib import Path

from ate_features.models import (
    Feature,
    FeatureAssignment,
    PromptSpecificity,
    RunMetadata,
    Specialization,
    TeamSize,
    Treatment,
)

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


# --- Prompt Generation ---


def get_opening_prompt(
    treatment: Treatment,
    features: list[Feature],
    *,
    assignments: FeatureAssignment | None = None,
    specialization_context: str | None = None,
    communication_nudge: str | None = None,
) -> str:
    """Generate the opening prompt for a treatment session."""
    parts: list[str] = []

    # Specialization preamble (only for specialized treatments)
    if (
        specialization_context
        and treatment.dimensions.specialization == Specialization.SPECIALIZED
    ):
        parts.append("# Domain Context\n")
        parts.append(specialization_context)
        parts.append("")

    # Communication nudge
    if communication_nudge:
        parts.append(f"**Communication guidance:** {communication_nudge}\n")

    is_detailed = (
        treatment.dimensions.prompt_specificity == PromptSpecificity.DETAILED
    )

    if is_detailed:
        parts.append(_detailed_prompt(treatment, features, assignments))
    else:
        parts.append(_vague_prompt(features))

    return "\n".join(parts)


def _detailed_prompt(
    treatment: Treatment,
    features: list[Feature],
    assignments: FeatureAssignment | None,
) -> str:
    """Build a detailed opening prompt with full specs and test paths."""
    lines: list[str] = []
    lines.append("# Feature Implementation Task\n")
    lines.append(
        "Implement the following features in the pinned LangGraph repository. "
        "For each feature: explore the codebase, implement the fix, run the "
        "acceptance tests, and create a patch file.\n"
    )

    for feat in features:
        lines.append(f"## {feat.id}: {feat.title}")
        lines.append(f"**Subsystem:** {feat.subsystem}")
        lines.append(f"**Spec:** {feat.spec}")
        test_dir = f"tests/acceptance/test_{feat.id.lower()}_*.py"
        lines.append(f"**Tests:** `{test_dir}`\n")

    if assignments and uses_agent_teams(treatment):
        lines.append("## Feature Assignments\n")
        for agent_num, feats in [
            (1, assignments.agent_1),
            (2, assignments.agent_2),
            (3, assignments.agent_3),
            (4, assignments.agent_4),
        ]:
            lines.append(f"- **Agent {agent_num}:** {', '.join(feats)}")
        lines.append("")

    return "\n".join(lines)


def _vague_prompt(features: list[Feature]) -> str:
    """Build a vague opening prompt with just titles and subsystems."""
    lines: list[str] = []
    lines.append("# Feature Implementation Task\n")
    lines.append(
        "Implement the following features in the LangGraph repository. "
        "Acceptance tests are in the `tests/acceptance/` directory.\n"
    )

    for feat in features:
        lines.append(f"- **{feat.title}** ({feat.subsystem})")

    lines.append("")
    return "\n".join(lines)


# --- Session Guide ---


def render_session_guide(
    treatment: Treatment,
    features: list[Feature],
    run_dir: Path,
    *,
    assignments: FeatureAssignment | None = None,
    specialization_context: str | None = None,
    communication_nudge: str | None = None,
) -> str:
    """Render a complete session guide markdown document."""
    sections: list[str] = []

    # Header
    sections.append(f"# Session Guide: Treatment {treatment.id}\n")
    sections.append(f"**Label:** {treatment.label}")
    sections.append(f"**Run directory:** `{run_dir}`\n")

    # Treatment config
    sections.append("## Treatment Configuration\n")
    d = treatment.dimensions
    sections.append(f"- Decomposition: {d.decomposition}")
    sections.append(f"- Prompt specificity: {d.prompt_specificity}")
    sections.append(f"- Delegate mode: {d.delegate_mode}")
    sections.append(f"- Team size: {d.team_size}")
    sections.append(f"- Communication: {d.communication}")
    sections.append(f"- Specialization: {d.specialization}")
    if treatment.paired_with is not None:
        sections.append(f"- Paired with: treatment {treatment.paired_with}")
    sections.append("")

    # Feature details
    sections.append("## Features\n")
    for feat in features:
        sections.append(f"### {feat.id}: {feat.title}")
        sections.append(f"- Subsystem: {feat.subsystem}")
        sections.append(f"- Spec: {feat.spec}\n")

    # Assignments
    if assignments:
        sections.append("## Feature Assignments\n")
        for agent_num, feats in [
            (1, assignments.agent_1),
            (2, assignments.agent_2),
            (3, assignments.agent_3),
            (4, assignments.agent_4),
        ]:
            sections.append(f"- Agent {agent_num}: {', '.join(feats)}")
        sections.append("")

    # Communication guidance
    if communication_nudge:
        sections.append("## Communication Guidance\n")
        sections.append(communication_nudge)
        sections.append("")

    # Specialization context
    if specialization_context:
        sections.append("## Specialization Context\n")
        sections.append(specialization_context)
        sections.append("")

    # Opening prompt
    prompt = get_opening_prompt(
        treatment,
        features,
        assignments=assignments,
        specialization_context=specialization_context,
        communication_nudge=communication_nudge,
    )
    sections.append("## Opening Prompt\n")
    sections.append("```")
    sections.append(prompt)
    sections.append("```\n")

    # Data collection checklist
    sections.append("## Data Collection Checklist\n")
    sections.append("- [ ] Session transcript saved")
    sections.append("- [ ] Patches extracted per feature")
    sections.append("- [ ] Acceptance tests run against patches")
    sections.append("- [ ] metadata.json updated with timestamps")
    sections.append("- [ ] Notes captured in notes.md")
    sections.append("")

    return "\n".join(sections)
