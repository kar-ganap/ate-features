"""Execution harness for treatment sessions."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ate_features.models import (
    Feature,
    FeatureAssignment,
    PreflightResult,
    PromptSpecificity,
    RunMetadata,
    Specialization,
    TeamSize,
    Treatment,
)

DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data"


# --- Preflight Checks ---


def preflight_check(
    langgraph_dir: Path,
    *,
    expected_pin: str | None = None,
) -> PreflightResult:
    """Run preflight checks on the LangGraph directory.

    Checks:
    1. Directory exists
    2. .git directory exists
    3. HEAD matches expected pin
    4. Working tree is clean
    5. Records Claude Code version (informational)

    Returns PreflightResult with issues list and recorded CC version.
    """
    issues: list[str] = []

    # 1. Directory exists
    if not langgraph_dir.exists():
        issues.append(f"LangGraph directory does not exist: {langgraph_dir}")
        return PreflightResult(issues=issues)

    # 2. .git exists
    if not (langgraph_dir / ".git").exists():
        issues.append(f"No .git directory in {langgraph_dir}")
        return PreflightResult(issues=issues)

    # 3. HEAD matches expected pin
    if expected_pin is not None:
        head_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=langgraph_dir,
            capture_output=True,
            text=True,
        )
        head = head_result.stdout.strip()
        if not head.startswith(expected_pin):
            issues.append(
                f"Commit mismatch: HEAD={head[:12]}, expected={expected_pin[:12]}"
            )

    # 4. Clean working tree
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=langgraph_dir,
        capture_output=True,
        text=True,
    )
    if status_result.stdout.strip():
        issues.append("Working tree is not clean (dirty)")

    # 5. Record CC version (informational, never an issue)
    cc_version = "unknown"
    try:
        cc_result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
        )
        if cc_result.returncode == 0 and cc_result.stdout.strip():
            cc_version = cc_result.stdout.strip()
    except FileNotFoundError:
        pass

    return PreflightResult(issues=issues, claude_code_version=cc_version)


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


# --- Scaffolding ---


def scaffold_treatment(
    treatment_id: int | str,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> list[Path]:
    """Create session directory structure for a treatment.

    Per-feature treatments (0b, 6) get one directory per feature.
    All others get a single session directory.
    Returns list of created file paths.
    """
    from ate_features.config import load_features, load_treatments

    config = load_treatments()
    treatment = next(t for t in config.treatments if t.id == treatment_id)
    features = load_features().features

    created: list[Path] = []

    if is_per_feature_treatment(treatment):
        for feat in features:
            run_dir = get_run_dir(treatment_id, feature_id=feat.id, data_dir=data_dir)
            created.extend(
                _scaffold_session(treatment, [feat], run_dir)
            )
    else:
        run_dir = get_run_dir(treatment_id, data_dir=data_dir)
        created.extend(
            _scaffold_session(treatment, features, run_dir)
        )

    return created


def _scaffold_session(
    treatment: Treatment,
    features: list[Feature],
    run_dir: Path,
) -> list[Path]:
    """Create session files in a run directory."""
    run_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    # Session guide (always overwritten)
    guide_path = run_dir / "session_guide.md"
    guide_path.write_text(render_session_guide(treatment, features, run_dir))
    created.append(guide_path)

    # Metadata (always overwritten with fresh template)
    from ate_features.models import ExecutionMode, RunMetadata

    meta = RunMetadata(
        treatment_id=treatment.id,
        feature_ids=[f.id for f in features],
        mode=ExecutionMode(treatment.execution.mode),
        agent_teams_enabled=uses_agent_teams(treatment),
        team_size=treatment.dimensions.team_size,
    )
    meta_path = save_metadata(meta, run_dir)
    created.append(meta_path)

    # Notes (never overwritten)
    notes_path = run_dir / "notes.md"
    if not notes_path.exists():
        notes_path.write_text(
            f"# Notes: Treatment {treatment.id}\n\n"
            "<!-- Add session observations here -->\n"
        )
    created.append(notes_path)

    return created


# --- Patch Management ---


def apply_patch(patch_path: Path, langgraph_dir: Path) -> bool:
    """Apply a patch file to the LangGraph directory.

    Runs --check first to verify, then applies. Returns True on success.
    """
    check = subprocess.run(
        ["git", "apply", "--check", str(patch_path)],
        cwd=langgraph_dir,
        capture_output=True,
    )
    if check.returncode != 0:
        return False

    result = subprocess.run(
        ["git", "apply", str(patch_path)],
        cwd=langgraph_dir,
        capture_output=True,
    )
    return result.returncode == 0


def revert_langgraph(langgraph_dir: Path) -> None:
    """Revert LangGraph directory to clean state (checkout + clean)."""
    subprocess.run(
        ["git", "checkout", "."],
        cwd=langgraph_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "clean", "-fd"],
        cwd=langgraph_dir,
        check=True,
        capture_output=True,
    )
