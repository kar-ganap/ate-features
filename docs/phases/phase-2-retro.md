# Phase 2 Retrospective: Execution Harness

## What Worked

- Building the harness incrementally (directories → prompts → scaffolding →
  patches) made each step testable in isolation.
- Naming specialization files by content (`serde_types_and_state_channels.md`)
  instead of agent number (`agent_1.md`) — user feedback that descriptive names
  help the spawned agent follow instructions. Good insight.
- The `is_per_feature_treatment()` / `uses_agent_teams()` introspection helpers
  made conditional logic clean throughout prompt generation and scaffolding.
- Session guide generation (markdown document with treatment config, features,
  assignments, opening prompt, and data collection checklist) gives a
  self-contained reference for each experiment run.

## Surprises

- **`datetime.UTC` import gotcha**: Python 3.11 has `datetime.UTC` as a
  module-level alias, but accessing it as `datetime.datetime.UTC` fails.
  Correct: `from datetime import UTC, datetime`. Ruff UP017 enforces this.
- **Prompt complexity**: The opening prompt is a product of 3 dimensions
  (detailed/vague × specialization × communication nudge) — testing all
  combinations required 17 tests in `test_harness_prompts.py`.
- **Per-feature treatments need special handling everywhere**: Treatments 0b and 6
  are 8×1 without Agent Teams, meaning 8 independent sessions per treatment.
  This affected directory structure, scaffolding, and will affect scoring.

## Deviations from Plan

- Plan mentioned `ScoringReport` model — deferred to Phase 3 where it belongs.
- Specialization files were initially named `agent_N.md`, renamed to descriptive
  names based on user feedback before committing.
- `load_communication_nudges()` was added to config.py (not originally in the
  Phase 2 plan, carried over from Phase 1 communication infrastructure).

## Implicit Assumptions Made Explicit

- `apply_patch()` runs `--check` before `apply` — fail-fast if patch won't apply
  cleanly.
- `revert_langgraph()` does both `git checkout .` and `git clean -fd` — the
  latter catches untracked test fixtures not cleaned by checkout alone.
- Specialization context is only injected for `Specialization.SPECIALIZED`
  treatments (4, 5, 6) — vanilla treatments get no domain context even if the
  files exist.

## Scope Changes for Next Phase

- Phase 3: Scoring framework. T4 backfill for F1-F4, composite weights,
  JUnit XML parsing, Wave 2 decision gate.

## Metrics

- **Tests added**: 67 unit tests (from 50 → 117)
- **Files changed**: 17
- **Commits**: 9 (including plan + docs)
- **New modules**: `harness.py` (359 lines), 4 specialization files
