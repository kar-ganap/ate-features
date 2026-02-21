# Phase 4 Retrospective: Execution Runner

## What Worked

- TDD cycle stayed consistent: every module followed red → green → gates →
  commit. Zero regressions across 7 commits.
- Modeling ate's detailed runbooks (250-380 lines each) as the template.
  Generating runbooks from config ensures consistency across all 11 treatments.
- `PreflightResult` model cleanly separates issues (blocking) from CC version
  (informational). Recording version rather than pinning avoids unnecessary
  friction while maintaining audit trail.
- Patch instructions appended to `get_opening_prompt()` with opt-out flag
  keeps the prompt self-contained — the agent has everything it needs.
- `PatchStatus` enum (MISSING/EMPTY/VALID/INVALID) gives a clear vocabulary
  for post-session verification.

## Surprises

- **ruff F541 (f-string without placeholders)**: Caught twice in different
  files. Easy fix but worth noting as a recurring lint trip.
- **mypy strict + `dict[str, object]`**: Same pattern as Phase 3 — config
  loaders return `dict[str, object]` from YAML, and downstream `int()`/`float()`
  calls fail. Solved with `int(str(...))` cast. Should consider typed config
  models in a future phase.
- **Test assertion too broad**: `assert "each feature" not in prompt.lower()`
  failed because the phrase appears in the detailed prompt template itself
  (not just the patch instructions section). Fixed by scoping the assertion
  to the patch instructions section only.

## Deviations from Plan

- Plan estimated ~40 new unit tests. Actual: 41 new unit tests (4 config +
  8 preflight + 4 patch instructions + 7 verify + 18 runbook).
- Plan mentioned `_monitoring_section()` and `_shell_command()` as helpers in
  runbook.py — both implemented as planned, no surprises.
- CC version is recorded but not checked in preflight (user preference), not
  pinned in `execution.yaml` as originally planned.

## Implicit Assumptions Made Explicit

- `FEATURE_IDS` is hardcoded as `["F1"..."F8"]` in harness.py for
  `verify_patches()`. If features are added/removed, this needs updating.
- Runbooks are generated from config data and committed to `docs/runbooks/`.
  They should be regenerated if treatments.yaml or features.yaml change.
- `_patch_instructions()` uses `is_per_feature_treatment()` to decide
  single-feature vs multi-feature instructions. This is the same function
  used by scaffolding, keeping the logic consistent.

## Scope Changes for Next Phase

- All infrastructure phases (0-4) are complete. Next step is running
  Wave 1 experiments interactively using the runbooks.

## Metrics

- **Tests added**: 41 unit tests (from 163 → 204)
- **Total tests**: 204 unit + 104 acceptance = 308
- **Files changed**: 18
- **Commits**: 9 (plan, config, preflight, patch instructions, patch verify,
  runbook, generate runbooks, docs, retro)
- **New modules**: `runbook.py` (205 lines), `config/execution.yaml`
- **Generated artifacts**: 11 runbook files in `docs/runbooks/`
