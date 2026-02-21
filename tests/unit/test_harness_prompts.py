"""Tests for opening prompt generation and session guides."""

from pathlib import Path

from ate_features.config import load_features, load_treatments
from ate_features.harness import (
    get_opening_prompt,
    is_per_feature_treatment,
    render_session_guide,
)


def _get_treatment(treatment_id):
    config = load_treatments()
    return next(t for t in config.treatments if t.id == treatment_id)


def _get_features():
    return load_features().features


class TestGetOpeningPromptDetailed:
    """Detailed prompts: 0a, 0b, 1, 3, 5, 6, 7."""

    def test_contains_feature_spec(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(treatment, features)
        # Should contain at least one feature's spec text
        assert features[0].spec in prompt

    def test_contains_acceptance_test_path(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(treatment, features)
        assert "tests/acceptance/" in prompt

    def test_contains_feature_titles(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        prompt = get_opening_prompt(treatment, features)
        for f in features:
            assert f.title in prompt

    def test_contains_assignments_for_team_treatment(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, assignments=config.feature_assignments.explicit,
        )
        assert "Agent 1" in prompt
        assert "F1" in prompt

    def test_contains_instructions(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(treatment, features)
        assert "implement" in prompt.lower() or "test" in prompt.lower()


class TestGetOpeningPromptVague:
    """Vague prompts: 2a, 2b, 4, 8."""

    def test_contains_feature_titles(self) -> None:
        treatment = _get_treatment("2a")
        features = _get_features()
        prompt = get_opening_prompt(treatment, features)
        for f in features:
            assert f.title in prompt

    def test_does_not_contain_spec_text(self) -> None:
        treatment = _get_treatment("2a")
        features = _get_features()
        prompt = get_opening_prompt(treatment, features)
        # Vague should not include the detailed spec text
        for f in features:
            assert f.spec not in prompt

    def test_contains_subsystem(self) -> None:
        treatment = _get_treatment("2a")
        features = _get_features()
        prompt = get_opening_prompt(treatment, features)
        assert "serializer" in prompt.lower() or "state" in prompt.lower()


class TestSpecializationInjection:
    def test_specialization_preamble_included(self) -> None:
        treatment = _get_treatment(7)
        features = _get_features()
        context = "## Serializer Subsystem\nThe checkpoint serializer lives in..."
        prompt = get_opening_prompt(
            treatment, features, specialization_context=context,
        )
        assert "Serializer Subsystem" in prompt

    def test_no_specialization_for_vanilla(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        context = "## Serializer Subsystem\nThe checkpoint serializer lives in..."
        prompt = get_opening_prompt(
            treatment, features, specialization_context=context,
        )
        # Vanilla treatments should not include specialization context
        assert "checkpoint serializer lives in" not in prompt


class TestCommunicationNudge:
    def test_nudge_included_when_provided(self) -> None:
        treatment = _get_treatment("2a")
        features = _get_features()
        nudge = "Actively coordinate with your teammates."
        prompt = get_opening_prompt(
            treatment, features, communication_nudge=nudge,
        )
        assert "Actively coordinate" in prompt

    def test_no_nudge_when_not_provided(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        prompt = get_opening_prompt(treatment, features)
        assert "coordinate" not in prompt.lower()


class TestRenderSessionGuide:
    def test_contains_treatment_config(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        run_dir = Path("/tmp/treatment-1")
        guide = render_session_guide(treatment, features, run_dir)
        assert "Treatment 1" in guide or "treatment-1" in guide
        assert "Structured Team" in guide

    def test_contains_feature_details(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        run_dir = Path("/tmp/treatment-0a")
        guide = render_session_guide(treatment, features, run_dir)
        for f in features:
            assert f.id in guide

    def test_contains_opening_prompt(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        run_dir = Path("/tmp/treatment-0a")
        guide = render_session_guide(treatment, features, run_dir)
        assert "Opening Prompt" in guide

    def test_contains_data_collection_checklist(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        run_dir = Path("/tmp/treatment-0a")
        guide = render_session_guide(treatment, features, run_dir)
        assert "checklist" in guide.lower() or "Checklist" in guide

    def test_includes_specialization_for_specialized_treatment(self) -> None:
        treatment = _get_treatment(7)
        features = _get_features()
        run_dir = Path("/tmp/treatment-7")
        context = "## Serializer Subsystem domain context"
        guide = render_session_guide(
            treatment, features, run_dir, specialization_context=context,
        )
        assert "Serializer Subsystem domain context" in guide


class TestPatchInstructions:
    def test_single_session_treatment_has_patch_instructions(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(treatment, features)
        assert "git diff" in prompt
        assert "git checkout" in prompt
        assert "git clean" in prompt

    def test_per_feature_treatment_has_single_feature_instructions(self) -> None:
        treatment = _get_treatment("0b")
        assert is_per_feature_treatment(treatment)
        features = _get_features()[:1]  # Single feature for per-feature
        prompt = get_opening_prompt(treatment, features)
        assert "git diff" in prompt
        # Per-feature patch section should say "this feature", not "EACH feature"
        patch_section = prompt[prompt.index("## Patch Instructions"):]
        assert "this feature" in patch_section.lower()
        assert "each feature" not in patch_section.lower()

    def test_opt_out_patch_instructions(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(
            treatment, features, include_patch_instructions=False,
        )
        assert "git diff" not in prompt

    def test_patch_instructions_contain_treatment_id(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        prompt = get_opening_prompt(treatment, features)
        assert "treatment-1" in prompt


class TestCumulativePatchInstructions:
    def test_cumulative_has_git_add(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
        )
        assert "git add -A" in prompt

    def test_cumulative_no_reset(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
        )
        assert "git checkout" not in prompt
        assert "git clean" not in prompt

    def test_cumulative_has_combined_patch(self) -> None:
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
        )
        assert "cumulative.patch" in prompt

    def test_cumulative_has_treatment_id(self) -> None:
        treatment = _get_treatment(1)
        features = _get_features()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
        )
        assert "treatment-1" in prompt

    def test_cumulative_at_no_same_tree_constraint(self) -> None:
        """AT treatments should NOT say 'same working tree'."""
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
            assignments=config.feature_assignments.explicit,
        )
        assert "same working tree" not in prompt

    def test_cumulative_at_has_combined_patch(self) -> None:
        """AT treatments should still request a combined patch."""
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
            assignments=config.feature_assignments.explicit,
        )
        assert "cumulative.patch" in prompt

    def test_cumulative_at_no_git_add(self) -> None:
        """AT treatments should NOT tell agents to git add -A between features."""
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
            assignments=config.feature_assignments.explicit,
        )
        assert "git add -A" not in prompt

    def test_cumulative_at_has_team_creation_instruction(self) -> None:
        """AT treatments should explicitly instruct team creation."""
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
            assignments=config.feature_assignments.explicit,
        )
        assert "agent team" in prompt.lower() or "create a team" in prompt.lower()

    def test_cumulative_at_has_teammate_spawning(self) -> None:
        """AT treatments should tell the lead to spawn teammates."""
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
            assignments=config.feature_assignments.explicit,
        )
        assert "teammate" in prompt.lower() or "spawn" in prompt.lower()

    def test_cumulative_solo_no_team_instruction(self) -> None:
        """Solo treatments should NOT mention team creation."""
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
        )
        assert "agent team" not in prompt.lower()
        assert "spawn" not in prompt.lower()

    def test_cumulative_solo_has_same_tree_constraint(self) -> None:
        """Solo treatments (0a) should still say 'same working tree'."""
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
        )
        assert "same working tree" in prompt

    def test_cumulative_vague_at_no_feature_assignments_reference(self) -> None:
        """Vague AT treatments must NOT reference 'Feature Assignments section'."""
        treatment = _get_treatment("2a")  # vague + AT
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
            assignments=config.feature_assignments.explicit,
        )
        assert "Feature Assignments section" not in prompt

    def test_cumulative_vague_at_lets_lead_decide(self) -> None:
        """Vague AT treatments should tell lead to decide assignments."""
        treatment = _get_treatment("2a")  # vague + autonomous
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
            assignments=config.feature_assignments.explicit,
        )
        assert "as you see fit" in prompt.lower()

    def test_cumulative_detailed_at_references_assignments_section(self) -> None:
        """Detailed AT treatments SHOULD reference 'Feature Assignments section'."""
        treatment = _get_treatment(1)  # detailed + AT
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
            assignments=config.feature_assignments.explicit,
        )
        assert "Feature Assignments section" in prompt

    def test_cumulative_per_feature_no_same_tree(self) -> None:
        """Per-feature treatments should NOT say 'same working tree'."""
        treatment = _get_treatment("0b")
        features = _get_features()[:1]
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
        )
        assert "same working tree" not in prompt

    def test_cumulative_per_feature_no_cumulative_patch(self) -> None:
        """Per-feature treatments should NOT reference cumulative.patch."""
        treatment = _get_treatment("0b")
        features = _get_features()[:1]
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
        )
        assert "cumulative.patch" not in prompt

    def test_cumulative_per_feature_has_feature_patch(self) -> None:
        """Per-feature treatments should reference the single feature's patch."""
        treatment = _get_treatment("0b")
        features = _get_features()[:1]
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
        )
        assert "F1.patch" in prompt

    def test_cumulative_at_mandatory_delegation(self) -> None:
        """AT treatments should mandate delegation — lead must NOT implement."""
        treatment = _get_treatment(1)
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
            assignments=config.feature_assignments.explicit,
        )
        assert "must" in prompt.lower() or "do not implement" in prompt.lower()

    def test_cumulative_8x1_mandatory_delegation(self) -> None:
        """8x1 AT treatment should mandate delegation."""
        treatment = _get_treatment(5)
        features = _get_features()
        config = load_treatments()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
            assignments=config.feature_assignments.explicit,
        )
        assert "do not implement" in prompt.lower()

    def test_cumulative_solo_no_delegation_language(self) -> None:
        """Solo treatments should NOT have delegation mandate."""
        treatment = _get_treatment("0a")
        features = _get_features()
        prompt = get_opening_prompt(
            treatment, features, scoring_mode="cumulative",
        )
        assert "do not implement" not in prompt.lower()
