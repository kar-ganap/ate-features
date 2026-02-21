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
    TeamSize,
    Treatment,
)


def _shell_command(treatment: Treatment) -> str:
    """Return the shell command to start Claude Code for this treatment."""
    if uses_agent_teams(treatment):
        return "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude"
    return "claude"


def _treatment_description(treatment: Treatment) -> str:
    """Generate a human-readable description of the treatment."""
    d = treatment.dimensions
    at = uses_agent_teams(treatment)
    per_feature = is_per_feature_treatment(treatment)

    parts: list[str] = []
    if per_feature:
        parts.append("8 separate interactive Claude Code sessions, "
                      "one per feature.")
    elif at:
        parts.append("1 interactive Claude Code session with Agent Teams.")
    else:
        parts.append("1 interactive Claude Code session covering "
                      "all 8 features sequentially.")

    if at:
        parts.append(f"Team size: {d.team_size}.")
        if d.delegate_mode:
            parts.append("Delegate mode ON.")
        elif d.delegate_mode is False:
            parts.append("Delegate mode OFF (player-coach).")
    if d.prompt_specificity.value == "detailed":
        parts.append("Detailed prompts with full specs.")
    else:
        parts.append("Vague prompts (titles + subsystems only).")
    if d.communication:
        parts.append(f"Communication: {d.communication}.")

    return " ".join(parts)


def _dimensions_table(treatment: Treatment) -> str:
    """Render a markdown table of treatment dimensions."""
    d = treatment.dimensions
    lines = [
        "| Dimension | Value |",
        "|-----------|-------|",
        f"| Decomposition | **{d.decomposition.value.title()}** |",
        f"| Prompt specificity | {d.prompt_specificity} |",
        f"| Delegate mode | {d.delegate_mode} |",
        f"| Team size | {d.team_size} |",
        f"| Communication | {d.communication} |",
        f"| Specialization | {d.specialization} |",
    ]
    return "\n".join(lines)


def _signal_action_table(
    treatment: Treatment, scoring_mode: str = "isolated",
) -> str:
    """Generate the signal/action monitoring table."""
    at = uses_agent_teams(treatment)
    lines = [
        "| Signal | Action |",
        "|--------|--------|",
        "| Agent making steady progress (reading, coding, testing) "
        "| No action needed |",
        "| Agent going in circles (re-reading same files, same approach) "
        "| Note time; prepare to nudge at threshold |",
        "| Agent asks a clarifying question "
        "| Answer promptly |",
        "| Agent forgot to save patch before next feature "
        "| Intervene immediately (see nudge examples) |",
    ]
    if scoring_mode == "isolated":
        lines.append(
            "| Agent forgot to reset (`git checkout . && git clean -fd`) "
            "| Intervene immediately |"
        )
    lines.extend([
        "| Agent stuck on unrelated build/test errors "
        "| Nudge toward a different approach |",
        "| No output for >2 minutes "
        "| Check if waiting for input |",
    ])
    if scoring_mode == "cumulative":
        lines.append(
            "| Agent completed all features but not yet saved final patch "
            "| Remind to save cumulative.patch |"
        )
    if at:
        lines.append(
            "| Lead forming team and delegating "
            "| Note the confirmation |"
        )
    return "\n".join(lines)


def _per_feature_tracking_table(features: list[Feature]) -> str:
    """Generate a per-feature tracking table for real-time monitoring."""
    lines = [
        "| # | Feature | Subsystem | Started | Finished "
        "| Patch Saved | Reset Done | Notes |",
        "|---|---------|-----------|---------|----------"
        "|-------------|------------|-------|",
    ]
    for i, feat in enumerate(features, 1):
        lines.append(
            f"| {i} | {feat.id} | {feat.subsystem} "
            f"| ___:___ | ___:___ | [ ] | [ ] | |"
        )
    return "\n".join(lines)


def _nudge_templates(
    treatment: Treatment, scoring_mode: str = "isolated",
) -> str:
    """Generate nudge template examples."""
    tid = treatment.id
    at = uses_agent_teams(treatment)
    lines: list[str] = ["### 3.4 Nudge examples\n"]
    lines.append("Use these as templates. Adapt to the situation.\n")

    if scoring_mode == "cumulative":
        lines.append("**If stuck on a feature past the threshold:**")
        lines.append("```")
        lines.append("Let's move on to the next feature. "
                     "You'll save a final combined patch at the end.")
        lines.append("```\n")

        lines.append(
            "**If agent completed all features but forgot patch:**"
        )
        lines.append("```")
        lines.append("Great! Now save your combined patch with:")
        lines.append(f"git diff --staged > data/patches/treatment-{tid}/"
                     "cumulative.patch")
        lines.append("```\n")

        lines.append("**If agent is going in circles:**")
        lines.append("```")
        lines.append("You seem to be revisiting the same approach. "
                     "Can you try a different angle?")
        lines.append("If you're stuck, it's OK to move on to the "
                     "next feature.")
        lines.append("```")
    else:
        lines.append("**If stuck on a feature past the threshold:**")
        lines.append("```")
        lines.append("Let's move on. Save whatever patch you have "
                     "(even if incomplete) with:")
        lines.append(f"git diff > data/patches/treatment-{tid}/"
                     "<feature-id>.patch")
        lines.append("Then reset with: git checkout . && git clean -fd")
        lines.append("And proceed to the next feature.")
        lines.append("```\n")

        lines.append("**If agent forgot to save a patch:**")
        lines.append("```")
        lines.append("Before moving on, please save the patch for the "
                     "feature you just finished:")
        lines.append(f"git diff > data/patches/treatment-{tid}/"
                     "<feature-id>.patch")
        lines.append("Then reset: git checkout . && git clean -fd")
        lines.append("```\n")

        lines.append("**If agent forgot to reset LangGraph:**")
        lines.append("```")
        lines.append("Please reset the LangGraph source before starting "
                     "the next feature:")
        lines.append("git checkout . && git clean -fd")
        lines.append("Verify with: git diff --stat")
        lines.append("```\n")

        lines.append("**If agent is going in circles:**")
        lines.append("```")
        lines.append("You seem to be revisiting the same approach. "
                     "Can you try a different angle?")
        lines.append("If you're stuck, it's OK to save what you have "
                     "and move on to the next feature.")
        lines.append("```")

    if at:
        lines.append("")
        lines.append("**If a specific agent is stuck (team treatments):**")
        lines.append("```")
        lines.append("Agent [N] seems stuck on [feature]. "
                     "Can it try a different approach?")
        lines.append("```")

    lines.append("")
    return "\n".join(lines)


def _notes_template(treatment: Treatment) -> str:
    """Generate the notes template section."""
    tid = treatment.id
    at = uses_agent_teams(treatment)
    lines = [
        "### 4.6 Write session notes\n",
        "Record observations in "
        f"`data/transcripts/treatment-{tid}/notes.md`. "
        "Use this format:\n",
        "```markdown",
        f"# Notes: Treatment {tid} — {treatment.label}\n",
    ]

    if at:
        lines.append("## Assignment Confirmation")
        if treatment.dimensions.team_size == TeamSize.EIGHT_BY_ONE:
            for i in range(1, 9):
                lines.append(f"- Agent {i}: F{i} (confirmed by lead)")
        else:
            lines.extend([
                "- Agent 1: F1, F5 (confirmed by lead)",
                "- Agent 2: F2, F6 (confirmed by lead)",
                "- Agent 3: F3, F7 (confirmed by lead)",
                "- Agent 4: F4, F8 (confirmed by lead)",
            ])
        lines.append("")

    lines.extend([
        "## Timeline",
        "- HH:MM Session started",
        "- HH:MM Agent began Feature F1",
        "- ...\n",
        "## Per-Feature Outcomes",
        "| Feature | Outcome | Time |",
        "|---------|---------|------|",
        "| F1 | fix/partial/stuck | ~X min |",
        "| ... | ... | ... |\n",
        "## Interventions",
        "- (timestamp): (what you said)\n",
    ])

    if at:
        lines.extend([
            "## Inter-Agent Communication",
            "- (any SendMessage events between agents)\n",
        ])

    lines.extend([
        "## Observations",
        "- Notable behavior: (anything interesting)",
        "- Approximate tool calls: ~N",
        "```\n",
        "- [ ] Notes written",
        "",
    ])
    return "\n".join(lines)


def _feature_quick_reference(features: list[Feature]) -> str:
    """Generate a feature quick reference appendix."""
    lines = [
        "## Appendix: Feature Quick Reference\n",
        "| # | ID | Title | Subsystem |",
        "|---|----|-------|-----------|",
    ]
    for i, feat in enumerate(features, 1):
        lines.append(
            f"| {i} | {feat.id} | {feat.title} | {feat.subsystem} |"
        )
    lines.append("")
    return "\n".join(lines)


def generate_runbook(
    treatment: Treatment,
    features: list[Feature],
    *,
    assignments: FeatureAssignment | None = None,
    specialization_context: str | None = None,
    communication_nudge: str | None = None,
    scoring_mode: str = "isolated",
) -> str:
    """Generate a complete markdown runbook for a treatment."""
    exec_config = load_execution_config()
    escape_minutes = int(str(exec_config.get("escape_threshold_minutes", 45)))
    transcript_hint = str(
        exec_config.get("transcript_path_hint", "~/.claude/projects/")
    )

    tid = treatment.id
    at = uses_agent_teams(treatment)
    per_feature = is_per_feature_treatment(treatment)
    sections: list[str] = []

    # --- Header ---
    sections.append(f"# Runbook: Treatment {tid} — {treatment.label}\n")
    sections.append(f"**Treatment**: {tid} ({treatment.label})")
    sections.append(
        f"**Description**: {_treatment_description(treatment)}"
    )
    sections.append("**Expected Duration**: 2-6 hours")
    sections.append(f"**Agent Teams**: "
                    f"{'ON' if at else 'OFF'}"
                    f"{' (`' + _shell_command(treatment) + '`)' if at else ''}")
    sections.append("")
    sections.append(_dimensions_table(treatment))
    sections.append("\n---\n")

    # --- §1 Pre-Session Setup ---
    sections.append("## 1. Pre-Session Setup\n")
    sections.append("Run these commands from the ate-features repo root.\n")

    sections.append("### 1.1 Run preflight checks\n")
    sections.append("```bash")
    sections.append("ate-features exec preflight")
    sections.append("```\n")
    sections.append("- [ ] Preflight passed (LangGraph at correct pin, "
                    "clean working tree)")
    sections.append("- [ ] CC version recorded: `___________`\n")

    sections.append("### 1.2 Scaffold session directories\n")
    sections.append("```bash")
    sections.append(f"ate-features exec scaffold {tid}")
    sections.append("```\n")
    sections.append(f"- [ ] `data/transcripts/treatment-{tid}/` created")
    sections.append("- [ ] `session_guide.md`, `metadata.json`, "
                    "`notes.md` present\n")

    sections.append("### 1.3 Create patches directory\n")
    sections.append("```bash")
    sections.append(f"mkdir -p data/patches/treatment-{tid}")
    sections.append("```\n")
    sections.append(f"- [ ] `data/patches/treatment-{tid}/` exists\n")

    sections.append("### 1.4 Verify LangGraph is clean\n")
    sections.append("```bash")
    sections.append("git -C data/langgraph status")
    sections.append("git -C data/langgraph diff --stat")
    sections.append("```\n")
    sections.append("- [ ] Working tree clean (no modifications, "
                    "no untracked files)\n")

    sections.append("### 1.5 Record session start\n")
    sections.append("```bash")
    sections.append("date -u +\"%Y-%m-%dT%H:%M:%SZ\"")
    sections.append("```\n")
    sections.append("- [ ] Start time: `___________`\n")

    sections.append("---\n")

    # --- §2 Opening Prompt ---
    sections.append("## 2. Opening Prompt\n")

    if per_feature:
        sections.append(
            "This is a per-feature treatment — run 8 separate sessions, "
            "one per feature. See the sub-sections below.\n"
        )
        sections.append("---\n")
        for feat in features:
            sections.append(
                f"### 2.{feat.id} — {feat.title}\n"
            )
            sections.append("Launch Claude Code:\n")
            sections.append("```bash")
            sections.append("cd data/langgraph")
            sections.append(_shell_command(treatment))
            sections.append("```\n")

            if at:
                sections.append(
                    f"- [ ] Confirmed: launched with "
                    f"`{_shell_command(treatment)}`\n"
                )
            else:
                sections.append(
                    "- [ ] Confirmed: launched with plain `claude` "
                    "(no Agent Teams env var)\n"
                )

            prompt = get_opening_prompt(
                treatment,
                [feat],
                assignments=assignments,
                specialization_context=specialization_context,
                communication_nudge=communication_nudge,
                scoring_mode=scoring_mode,
            )
            sections.append("Paste the following prompt:\n")
            sections.append("````")
            sections.append(prompt)
            sections.append("````\n")
            sections.append("- [ ] Pasted opening prompt")
            sections.append(f"- [ ] Agent began working on {feat.id}\n")
            sections.append("---\n")
    else:
        sections.append("Launch Claude Code:\n")
        sections.append("```bash")
        sections.append("cd data/langgraph")
        sections.append(_shell_command(treatment))
        sections.append("```\n")

        if at:
            sections.append(
                f"- [ ] Confirmed: launched with "
                f"`{_shell_command(treatment)}`\n"
            )
        else:
            sections.append(
                "- [ ] Confirmed: launched with plain `claude` "
                "(NOT `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude`)\n"
            )

        sections.append("### 2.1 Paste the opening prompt\n")
        sections.append(
            "Copy and paste the **entire block below** as a single "
            "message:\n"
        )
        sections.append("---\n")

        prompt = get_opening_prompt(
            treatment,
            features,
            assignments=assignments,
            specialization_context=specialization_context,
            communication_nudge=communication_nudge,
            scoring_mode=scoring_mode,
        )
        sections.append("````")
        sections.append(prompt)
        sections.append("````\n")
        sections.append("---\n")
        sections.append("- [ ] Pasted the full opening prompt")
        sections.append("- [ ] Agent acknowledged the features and began "
                        "working\n")

    sections.append("---\n")

    # --- §3 Monitoring ---
    sections.append("## 3. Monitoring Guidelines\n")

    sections.append("### 3.1 Cadence\n")
    sections.append(
        "Glance at the session every **2-3 minutes**. You do not need to "
        "watch continuously, but check progress regularly to catch "
        "stalls early.\n"
    )

    sections.append("### 3.2 What to watch for\n")
    sections.append(_signal_action_table(treatment, scoring_mode))
    sections.append("")

    sections.append("### 3.3 Escape time thresholds\n")
    sections.append(
        f"Wall-clock time limit per feature: **~{escape_minutes} minutes**. "
        "If the agent has not produced a patch (or acknowledged it cannot) "
        "within the threshold, intervene.\n"
    )

    sections.append(_nudge_templates(treatment, scoring_mode))

    if not per_feature:
        sections.append("### 3.5 Per-feature tracking\n")
        sections.append(
            "Use this table to track progress in real time "
            "(fill in as you go):\n"
        )
        sections.append(_per_feature_tracking_table(features))
        sections.append("")

    sections.append("\n---\n")

    # --- §4 After-Session Steps ---
    sections.append("## 4. After-Session Steps\n")

    sections.append("### 4.1 Record end timestamp\n")
    sections.append("```bash")
    sections.append("date -u +\"%Y-%m-%dT%H:%M:%SZ\"")
    sections.append("```\n")
    sections.append("- [ ] End time: `___________`\n")

    sections.append("### 4.2 Check for unsaved work\n")
    sections.append("```bash")
    sections.append("git -C data/langgraph diff --stat")
    sections.append("```\n")

    if scoring_mode == "cumulative":
        sections.append(
            "If the agent did not save the final combined patch, "
            "save it now:\n"
        )
        sections.append("```bash")
        sections.append(
            f"git -C data/langgraph diff > "
            f"data/patches/treatment-{tid}/cumulative.patch"
        )
        sections.append("```\n")
    else:
        sections.append(
            "If there are uncommitted changes, save them as a "
            "remaining patch:\n"
        )
        sections.append("```bash")
        sections.append(
            f"git -C data/langgraph diff > "
            f"data/patches/treatment-{tid}/remaining.patch"
        )
        sections.append("git -C data/langgraph checkout . && "
                        "git -C data/langgraph clean -fd")
        sections.append("```\n")

    sections.append("### 4.3 Verify patches\n")
    sections.append("```bash")
    sections.append(f"ate-features exec verify-patches {tid}")
    sections.append(f"ls -la data/patches/treatment-{tid}/")
    sections.append("```\n")

    if scoring_mode == "cumulative":
        sections.append(
            "Expected: `cumulative.patch` (combined result) plus "
            "per-feature snapshots (`F1.patch` through `F8.patch`).\n"
        )
    else:
        sections.append(
            "Expected: up to 8 files (`F1.patch` through `F8.patch`). "
            "Some may be empty (0 bytes) if the agent could not implement "
            "that feature.\n"
        )
    sections.append("- [ ] Verified patch files present")
    sections.append("- [ ] Non-empty patches: `___________`\n")

    sections.append("### 4.4 Verify LangGraph is clean\n")
    sections.append("```bash")
    if scoring_mode == "cumulative":
        sections.append("git -C data/langgraph checkout . && "
                        "git -C data/langgraph clean -fd")
    sections.append("git -C data/langgraph status")
    sections.append("```\n")
    sections.append("- [ ] Working tree clean\n")

    sections.append("### 4.5 Update metadata.json\n")
    sections.append(
        f"Update `data/transcripts/treatment-{tid}/metadata.json` with "
        "actual timing and outcome data:\n"
    )
    sections.append("```json")
    sections.append("{")
    sections.append("  \"started_at\": \"2026-XX-XXTXX:XX:XXZ\",")
    sections.append("  \"completed_at\": \"2026-XX-XXTXX:XX:XXZ\",")
    sections.append("  \"wall_clock_seconds\": null,")
    sections.append("  \"session_id\": null,")
    sections.append("  \"model\": \"claude-opus-4-6\",")
    sections.append("  \"notes\": null")
    sections.append("}")
    sections.append("```\n")
    sections.append("- [ ] metadata.json updated\n")

    sections.append(_notes_template(treatment))

    sections.append("### 4.7 Save session transcript\n")
    sections.append(
        "Claude Code stores session transcripts as JSONL files at:\n"
    )
    sections.append("```")
    sections.append(transcript_hint)
    sections.append("```\n")
    sections.append(
        "Look for the most recent `.jsonl` file matching the session time.\n"
    )
    sections.append(
        "- [ ] Session transcript located or session ID noted: "
        "`___________`\n"
    )

    sections.append("---\n")

    # --- §5 Final Checklist ---
    sections.append("## 5. Final Checklist\n")
    at_check = (
        "Agent Teams env var was set"
        if at else "No Agent Teams env var was set (plain `claude`)"
    )
    sections.append(f"- [ ] {at_check}")
    sections.append("- [ ] All 8 features were attempted")
    if scoring_mode == "cumulative":
        sections.append("- [ ] Per-feature snapshots saved")
        sections.append("- [ ] cumulative.patch saved (combined result)")
    else:
        sections.append(
            "- [ ] Patches saved for each feature (even if empty)"
        )
        sections.append("- [ ] LangGraph was reset between features")
    sections.append("- [ ] LangGraph is clean after final feature")
    sections.append("- [ ] Per-feature timing recorded in monitoring table")
    sections.append("- [ ] metadata.json updated with actual data")
    sections.append("- [ ] Notes written with observations")
    sections.append("- [ ] Session transcript saved")
    sections.append("- [ ] Total wall-clock time: `___________`")
    sections.append("")

    sections.append("---\n")

    # --- Appendix ---
    sections.append(_feature_quick_reference(features))

    return "\n".join(sections)


def generate_all_runbooks(
    *, scoring_mode: str = "isolated",
) -> dict[int | str, str]:
    """Generate runbooks for all 11 treatments."""
    from ate_features.config import (
        load_communication_nudges,
        load_specialization,
    )
    from ate_features.models import Specialization

    config = load_treatments()
    features = load_features().features
    assignments = config.feature_assignments.explicit
    nudges = load_communication_nudges()

    runbooks: dict[int | str, str] = {}
    for treatment in config.treatments:
        spec_context: str | None = None
        if treatment.dimensions.specialization == Specialization.SPECIALIZED:
            parts = [load_specialization(i) for i in range(1, 5)]
            spec_context = "\n\n".join(parts)

        nudge_text: str | None = None
        comm = treatment.dimensions.communication
        if comm is not None and comm.value != "neutral" and comm.value in nudges:
            nudge_text = nudges[comm.value]["system_context"]

        runbooks[treatment.id] = generate_runbook(
            treatment,
            features,
            assignments=assignments,
            specialization_context=spec_context,
            communication_nudge=nudge_text,
            scoring_mode=scoring_mode,
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
