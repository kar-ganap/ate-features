"""Tests for runbook generation."""

from pathlib import Path

from ate_features.config import load_features, load_treatments
from ate_features.runbook import (
    generate_all_runbooks,
    generate_runbook,
    save_runbooks,
)


def _get_treatment(treatment_id):
    config = load_treatments()
    return next(t for t in config.treatments if t.id == treatment_id)


def _get_features():
    return load_features().features


class TestShellCommand:
    def test_no_agent_teams(self) -> None:
        """Treatment 0a has no Agent Teams — plain `claude`."""
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        # Header should say Agent Teams OFF
        assert "**Agent Teams**: OFF" in runbook
        # Shell command should be plain claude
        assert "cd data/langgraph\nclaude" in runbook

    def test_agent_teams_enabled(self) -> None:
        """Treatment 1 has Agent Teams — needs env var."""
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        runbook = generate_runbook(
            treatment, features,
            assignments=config.feature_assignments.explicit,
        )
        assert "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1" in runbook


class TestHeader:
    def test_has_description(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "Description" in runbook or "description" in runbook

    def test_has_expected_duration(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "Duration" in runbook or "duration" in runbook

    def test_has_agent_teams_status(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "Agent Teams" in runbook


class TestPreSessionSetup:
    def test_has_numbered_subsections(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "### 1.1" in runbook
        assert "### 1.2" in runbook

    def test_has_per_step_checkboxes(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        # Pre-session should have checkboxes after each step
        pre_section = runbook.split("## 2.")[0]
        assert "- [ ]" in pre_section

    def test_preflight_command(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "ate-features exec preflight" in runbook

    def test_scaffold_command(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "ate-features exec scaffold" in runbook


class TestMonitoringSection:
    def test_has_signal_action_table(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "Signal" in runbook and "Action" in runbook

    def test_has_escape_threshold(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "45" in runbook

    def test_has_nudge_templates(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "stuck" in runbook.lower()

    def test_has_per_feature_tracking_table(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        # Should have a tracking table with all 8 features
        assert "F1" in runbook and "F8" in runbook
        assert "Started" in runbook and "Finished" in runbook
        assert "Patch Saved" in runbook

    def test_team_treatment_has_agent_nudge(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        runbook = generate_runbook(
            treatment, features,
            assignments=config.feature_assignments.explicit,
        )
        assert "Agent" in runbook


class TestPostSession:
    def test_has_numbered_subsections(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        post_section = runbook[runbook.index("After-Session"):]
        assert "### 4.1" in post_section or "### 4.1" in runbook

    def test_has_metadata_json_guidance(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "metadata.json" in runbook

    def test_has_notes_template(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "## Timeline" in runbook or "Timeline" in runbook
        assert "Observations" in runbook or "observations" in runbook

    def test_has_transcript_path(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "transcript" in runbook.lower()

    def test_team_treatment_has_communication_notes(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        runbook = generate_runbook(
            treatment, features,
            assignments=config.feature_assignments.explicit,
        )
        assert "Inter-Agent" in runbook or "Communication" in runbook


class TestRunbookStructure:
    def test_single_session_treatment(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "# Runbook:" in runbook
        assert "Treatment 0a" in runbook
        assert "Pre-Session" in runbook
        assert "After-Session" in runbook or "Post-Session" in runbook
        assert "Checklist" in runbook

    def test_per_feature_treatment_has_sub_sections(self) -> None:
        treatment = _get_treatment("0b")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        for f in features:
            assert f.id in runbook

    def test_opening_prompt_included(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "Opening Prompt" in runbook

    def test_verify_patches_command_included(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "verify-patches" in runbook

    def test_dimensions_table(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "Decomposition" in runbook

    def test_checklist_has_checkboxes(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "- [ ]" in runbook

    def test_has_feature_quick_reference(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "Quick Reference" in runbook or "Appendix" in runbook


class TestGenerateAllRunbooks:
    def test_generates_all_11(self) -> None:
        runbooks = generate_all_runbooks()
        assert len(runbooks) == 11

    def test_all_have_content(self) -> None:
        runbooks = generate_all_runbooks()
        for tid, content in runbooks.items():
            assert len(content) > 200, f"Treatment {tid} runbook too short"

    def test_treatment_ids_match(self) -> None:
        config = load_treatments()
        expected_ids = {t.id for t in config.treatments}
        runbooks = generate_all_runbooks()
        assert set(runbooks.keys()) == expected_ids


class TestSaveRunbooks:
    def test_saves_files(self, tmp_path: Path) -> None:
        runbooks = {"0a": "# Test content", 1: "# More content"}
        paths = save_runbooks(runbooks, tmp_path)
        assert len(paths) == 2
        assert all(p.exists() for p in paths)

    def test_file_names(self, tmp_path: Path) -> None:
        runbooks = {"0a": "# Test", "0b": "# Test", 1: "# Test"}
        paths = save_runbooks(runbooks, tmp_path)
        names = {p.name for p in paths}
        assert "treatment-0a.md" in names
        assert "treatment-0b.md" in names
        assert "treatment-1.md" in names

    def test_file_content(self, tmp_path: Path) -> None:
        runbooks = {"0a": "# Hello World"}
        paths = save_runbooks(runbooks, tmp_path)
        assert paths[0].read_text() == "# Hello World"


class TestCumulativeRunbook:
    def test_cumulative_has_no_reset_nudges(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(
            treatment, features, scoring_mode="cumulative",
        )
        assert "git checkout" not in runbook
        assert "git clean" not in runbook

    def test_cumulative_has_git_add_in_prompt(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(
            treatment, features, scoring_mode="cumulative",
        )
        assert "git add -A" in runbook

    def test_cumulative_has_cumulative_patch_in_post_session(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(
            treatment, features, scoring_mode="cumulative",
        )
        assert "cumulative.patch" in runbook

    def test_cumulative_no_per_feature_reset_signals(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(
            treatment, features, scoring_mode="cumulative",
        )
        assert "forgot to reset" not in runbook

    def test_8x1_notes_template_has_8_agents(self) -> None:
        """Treatment 5 (8x1) notes template should list 8 agents."""
        treatment = _get_treatment(5)
        features = _get_features()
        config = load_treatments()
        runbook = generate_runbook(
            treatment, features,
            assignments=config.feature_assignments.explicit,
            scoring_mode="cumulative",
        )
        # Notes section should have 8 agent lines
        notes_section = runbook[runbook.index("Write session notes"):]
        assert "Agent 8: F8" in notes_section
        # Each agent should have exactly one feature (no comma-separated)
        assert "Agent 1: F1 (" in notes_section

    def test_4x2_notes_template_has_4_agents(self) -> None:
        """Treatment 1 (4x2) notes template should list 4 agents with 2 each."""
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        runbook = generate_runbook(
            treatment, features,
            assignments=config.feature_assignments.explicit,
            scoring_mode="cumulative",
        )
        notes_section = runbook[runbook.index("Write session notes"):]
        assert "Agent 1: F1, F5" in notes_section
        # Should NOT have Agent 5 in notes
        assert "Agent 5" not in notes_section

    def test_specialized_runbook_has_domain_context(self) -> None:
        """Specialized treatments should include domain context in the prompt."""
        from ate_features.config import load_specialization
        context = load_specialization(1)
        treatment = _get_treatment(7)
        features = _get_features()
        config = load_treatments()
        runbook = generate_runbook(
            treatment, features,
            assignments=config.feature_assignments.explicit,
            specialization_context=context,
            scoring_mode="cumulative",
        )
        assert "Domain Context" in runbook

    def test_encourage_runbook_has_nudge(self) -> None:
        """Encourage treatments should include communication nudge."""
        from ate_features.config import load_communication_nudges
        nudges = load_communication_nudges()
        nudge_text = nudges["encourage"]["system_context"]
        treatment = _get_treatment("2a")
        features = _get_features()
        config = load_treatments()
        runbook = generate_runbook(
            treatment, features,
            assignments=config.feature_assignments.explicit,
            communication_nudge=nudge_text,
            scoring_mode="cumulative",
        )
        assert "Communication guidance" in runbook

    def test_generate_all_runbooks_wires_specialization(self) -> None:
        """generate_all_runbooks should inject specialization for treatments 6,7,8."""
        runbooks = generate_all_runbooks(scoring_mode="cumulative")
        # Treatment 7 is specialized
        assert "Domain Context" in runbooks[7]
        # Treatment 0a is vanilla
        assert "Domain Context" not in runbooks["0a"]

    def test_generate_all_runbooks_wires_communication_nudge(self) -> None:
        """generate_all_runbooks should inject nudge for encourage/discourage."""
        runbooks = generate_all_runbooks(scoring_mode="cumulative")
        # Treatment 2a is encourage
        assert "Communication guidance" in runbooks["2a"]
        # Treatment 1 is neutral (no nudge text)
        assert "Communication guidance" not in runbooks[1]
