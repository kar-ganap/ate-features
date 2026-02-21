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
        # Should NOT have CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
        assert "CLAUDE_CODE_EXPERIMENTAL" not in runbook
        assert "claude" in runbook.lower()

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


class TestMonitoringSection:
    def test_has_escape_threshold(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "45" in runbook or "escape" in runbook.lower()

    def test_has_nudge_templates(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "stuck" in runbook.lower() or "nudge" in runbook.lower()


class TestRunbookStructure:
    def test_single_session_treatment(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "# Runbook:" in runbook or "Treatment 0a" in runbook
        assert "Pre-session" in runbook or "Setup" in runbook
        assert "Post-session" in runbook or "Cleanup" in runbook
        assert "Checklist" in runbook

    def test_per_feature_treatment_has_sub_sections(self) -> None:
        treatment = _get_treatment("0b")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        # Per-feature treatment should have sections for each feature
        for f in features:
            assert f.id in runbook

    def test_opening_prompt_included(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "Opening Prompt" in runbook or "opening prompt" in runbook.lower()

    def test_preflight_command_included(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "preflight" in runbook.lower()

    def test_verify_patches_command_included(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "verify-patches" in runbook

    def test_transcript_path_noted(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "transcript" in runbook.lower()

    def test_dimensions_table(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "decomposition" in runbook.lower() or "Decomposition" in runbook

    def test_checklist_has_checkboxes(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        runbook = generate_runbook(treatment, features)
        assert "- [ ]" in runbook


class TestGenerateAllRunbooks:
    def test_generates_all_11(self) -> None:
        runbooks = generate_all_runbooks()
        assert len(runbooks) == 11

    def test_all_have_content(self) -> None:
        runbooks = generate_all_runbooks()
        for tid, content in runbooks.items():
            assert len(content) > 100, f"Treatment {tid} runbook too short"

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
