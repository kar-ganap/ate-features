"""Runbook generation for experiment sessions."""

from __future__ import annotations

from pathlib import Path

from ate_features.config import (
    load_execution_config,
    load_features,
    load_treatments,
)
from ate_features.harness import (
    get_opening_prompt,
    is_per_feature_treatment,
    uses_agent_teams,
)
from ate_features.models import (
    Feature,
    FeatureAssignment,
    Treatment,
)


def _shell_command(treatment: Treatment) -> str:
    """Return the shell command to start Claude Code for this treatment."""
    if uses_agent_teams(treatment):
        return "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude"
    return "claude"


def _dimensions_table(treatment: Treatment) -> str:
    """Render a markdown table of treatment dimensions."""
    d = treatment.dimensions
    lines = [
        "| Dimension | Value |",
        "|-----------|-------|",
        f"| Decomposition | {d.decomposition} |",
        f"| Prompt specificity | {d.prompt_specificity} |",
        f"| Delegate mode | {d.delegate_mode} |",
        f"| Team size | {d.team_size} |",
        f"| Communication | {d.communication} |",
        f"| Specialization | {d.specialization} |",
    ]
    return "\n".join(lines)


def _monitoring_section(treatment: Treatment, escape_minutes: int) -> str:
    """Generate the monitoring guidance section."""
    lines = [
        "## Monitoring\n",
        f"**Escape threshold:** ~{escape_minutes} min per feature. "
        "If the agent is stuck for >10 min on a single approach, consider "
        "nudging.\n",
        "**Nudge templates:**",
        "- **Stuck:** \"Have you considered looking at the test file for "
        "hints about the expected behavior?\"",
        "- **Forgot patch:** \"Please save a patch before moving on: "
        "`git diff > data/patches/treatment-{tid}/{FN}.patch`\"",
        "- **Forgot reset:** \"Please reset before the next feature: "
        "`git checkout . && git clean -fd`\"",
        "",
    ]
    return "\n".join(lines)


def _transcript_path_note(transcript_hint: str) -> str:
    """Note about where to find JSONL transcripts."""
    return (
        f"**Transcript location:** `{transcript_hint}`\n"
        "Look for the most recent `.jsonl` file matching the session time."
    )


def generate_runbook(
    treatment: Treatment,
    features: list[Feature],
    *,
    assignments: FeatureAssignment | None = None,
    specialization_context: str | None = None,
    communication_nudge: str | None = None,
) -> str:
    """Generate a complete markdown runbook for a treatment."""
    exec_config = load_execution_config()
    escape_minutes = int(str(exec_config.get("escape_threshold_minutes", 45)))
    transcript_hint = str(
        exec_config.get("transcript_path_hint", "~/.claude/projects/")
    )

    tid = treatment.id
    sections: list[str] = []

    # Header
    sections.append(f"# Runbook: Treatment {tid} — {treatment.label}\n")
    sections.append(_dimensions_table(treatment))
    sections.append("")
    if uses_agent_teams(treatment):
        sections.append("**Agent Teams:** ON")
    else:
        sections.append("**Agent Teams:** OFF")
    sections.append("")

    # Pre-session setup
    sections.append("## Pre-session Setup\n")
    sections.append("```bash")
    sections.append("# 1. Run preflight (records CC version)")
    sections.append("ate-features exec preflight")
    sections.append("")
    sections.append("# 2. Scaffold session directories")
    sections.append(f"ate-features exec scaffold {tid}")
    sections.append("")
    sections.append("# 3. Create patches directory")
    sections.append(f"mkdir -p data/patches/treatment-{tid}")
    sections.append("")
    sections.append("# 4. Record start time")
    sections.append(f"echo \"Started: $(date -Iseconds)\" >> "
                    f"data/transcripts/treatment-{tid}/notes.md")
    sections.append("```\n")

    per_feature = is_per_feature_treatment(treatment)

    if per_feature:
        # Per-feature: 8 sub-sections
        sections.append("---\n")
        for feat in features:
            sections.append(f"## Feature: {feat.id} — {feat.title}\n")
            sections.append("### Start Session\n")
            sections.append("```bash")
            sections.append("cd data/langgraph")
            cmd = _shell_command(treatment)
            sections.append(cmd)
            sections.append("```\n")

            # Opening prompt for this single feature
            prompt = get_opening_prompt(
                treatment,
                [feat],
                assignments=assignments,
                specialization_context=specialization_context,
                communication_nudge=communication_nudge,
            )
            sections.append("### Opening Prompt\n")
            sections.append("```")
            sections.append(prompt)
            sections.append("```\n")

            sections.append(_monitoring_section(treatment, escape_minutes))

            sections.append("### Post-feature\n")
            sections.append("```bash")
            sections.append(
                f"ate-features exec verify-patches {tid}"
            )
            sections.append("```\n")
            sections.append("---\n")
    else:
        # Single session
        sections.append("## Start Session\n")
        sections.append("```bash")
        sections.append("cd data/langgraph")
        cmd = _shell_command(treatment)
        sections.append(cmd)
        sections.append("```\n")

        # Opening prompt
        prompt = get_opening_prompt(
            treatment,
            features,
            assignments=assignments,
            specialization_context=specialization_context,
            communication_nudge=communication_nudge,
        )
        sections.append("### Opening Prompt\n")
        sections.append("```")
        sections.append(prompt)
        sections.append("```\n")

        sections.append(_monitoring_section(treatment, escape_minutes))

    # Post-session
    sections.append("## Post-session\n")
    sections.append("```bash")
    sections.append("# 1. Check for unsaved work")
    sections.append("cd data/langgraph && git diff --stat")
    sections.append("")
    sections.append("# 2. Verify patches")
    sections.append(f"ate-features exec verify-patches {tid}")
    sections.append("")
    sections.append("# 3. Record end time")
    sections.append(f"echo \"Ended: $(date -Iseconds)\" >> "
                    f"data/transcripts/treatment-{tid}/notes.md")
    sections.append("")
    sections.append("# 4. Revert LangGraph to clean state")
    sections.append("cd data/langgraph && git checkout . && git clean -fd")
    sections.append("```\n")

    sections.append(_transcript_path_note(transcript_hint))
    sections.append("")

    # Final checklist
    sections.append("## Final Checklist\n")
    sections.append("- [ ] Preflight passed")
    sections.append("- [ ] Session scaffolded")
    sections.append("- [ ] Start time recorded")
    sections.append("- [ ] Opening prompt pasted")
    sections.append("- [ ] All features implemented")
    sections.append("- [ ] Patches saved (one per feature)")
    sections.append("- [ ] Patches verified")
    sections.append("- [ ] End time recorded")
    sections.append("- [ ] Transcript located")
    sections.append("- [ ] LangGraph reverted to clean state")
    sections.append("- [ ] Notes finalized")
    sections.append("")

    return "\n".join(sections)


def generate_all_runbooks() -> dict[int | str, str]:
    """Generate runbooks for all 11 treatments."""
    config = load_treatments()
    features = load_features().features
    assignments = config.feature_assignments.explicit

    runbooks: dict[int | str, str] = {}
    for treatment in config.treatments:
        runbooks[treatment.id] = generate_runbook(
            treatment,
            features,
            assignments=assignments,
        )
    return runbooks


def save_runbooks(
    runbooks: dict[int | str, str],
    output_dir: Path,
) -> list[Path]:
    """Save runbooks to files in output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for tid, content in runbooks.items():
        path = output_dir / f"treatment-{tid}.md"
        path.write_text(content)
        paths.append(path)
    return paths
