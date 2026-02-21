# Phase 1 Retrospective: LangGraph Tests & Communication Infrastructure

## What Worked

- Pinning LangGraph at a specific commit and using editable installs gave a
  stable, reproducible test target.
- Writing acceptance tests first (before any implementation) clarified what
  each feature actually needed to do.
- The tiered test methodology (T1/T2/T3) naturally created a quality gradient —
  T1 tests are simple happy-path checks, T2 tests hit edge cases, T3 tests
  cover quality/robustness concerns.
- Communication infrastructure ported cleanly from the predecessor `ate` project,
  with enhancements (pattern-quality nudges, taxonomy classification).

## Surprises

- **F5-F8 were too easy**: The original features (graph-level features) had
  9-11/11 tests already passing against the pinned commit. This would create a
  ceiling effect identical to the predecessor experiment. Had to replace F5-F8
  mid-phase with harder state/streaming features.
- **T4 tier emerged**: The replacement features needed smoke/integration tests
  (multi-node graph + checkpointer). This became the T4 tier — not planned
  initially but added natural signal for real-world usage patterns.
- **Treatment expansion to 11**: Adding a specialization dimension (vanilla vs
  specialized) grew the treatment matrix from 8 to 11, with 3 new treatments
  that pair agents with subsystem-specific domain context.
- **`from __future__ import annotations` breaks TypedDicts in acceptance tests**:
  When TypedDicts use `Annotated` fields in local scope, `get_type_hints()`
  fails because it can't resolve names from module globals. All acceptance test
  files must avoid this import. Documented as a gotcha.

## Deviations from Plan

- No formal Phase 1 plan document was written (oversight — addressed in backfill).
- F5-F8 features replaced mid-phase. The original features.yaml was overwritten.
- T4 tier was not in the original design — added organically when writing F5-F8
  replacement tests.
- Treatment count grew from 8 to 11 (specialization dimension).

## Implicit Assumptions Made Explicit

- All 8 features must have 0% pass rate against pinned commit for the experiment
  to be valid (otherwise ceiling effect repeats).
- Communication analysis only counts `SendMessage(recipient=<peer>)` with routing
  metadata — internal tool calls are not inter-agent communication.
- Acceptance tests run inside the LangGraph repo, not ate-features.

## Scope Changes for Next Phase

- F1-F4 lack T4 smoke tests (they predate the tier) — backfill deferred to Phase 3.
- Specialization definitions (what domain context each agent gets) deferred to
  Phase 2.
- Execution harness (how to actually run treatments) is Phase 2.

## Metrics

- **Tests added**: ~37 unit + 96 acceptance = ~133 total
- **Files changed**: 25
- **Commits**: 6
- **Key decision**: Replace F5-F8 to avoid ceiling effect
