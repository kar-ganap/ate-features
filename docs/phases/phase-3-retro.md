# Phase 3 Retrospective: Scoring Framework

## What Worked

- TDD workflow stayed disciplined: every module was red → green → gates → commit.
  Zero regressions across 10 commits.
- T4 backfill for F1-F4 went smoothly — pattern established by F5-F8's
  `TestT4Smoke` classes (multi-node StateGraph + InMemorySaver) replicated
  cleanly. All 8 new tests fail against pinned commit as expected.
- Composite scoring with configurable weights in YAML (not hardcoded) keeps the
  experiment flexible. Weights can be tuned without code changes.
- The `collect_scores` pipeline (apply → pytest → parse → revert) reuses
  existing `harness.py` patterns, and subprocess mocking in tests keeps them
  fast and deterministic.
- Backfilling plan/retro docs for Phases 0-2 caught a process gap before it
  became a habit. All phases now have both documents.

## Surprises

- **mypy strict vs `dict[str, object]`**: `load_scoring_config()` returns
  `dict[str, object]` (YAML is untyped). Downstream code that sums/compares
  values from this dict hits mypy errors because `object` doesn't support
  arithmetic. Solved with explicit `float()` casts and `isinstance` guards.
- **JUnit XML `--junitxml=path` is a single arg**: Tests initially looked for
  `--junitxml` and `path` as separate args, but pytest uses `=`-joined format.
  Required fixing the mock's argument parsing.
- **ruff import sorting (I001)**: Still trips up occasionally on blank lines
  between import groups. `ruff check --fix` handles it but worth noting as
  a recurring friction point.

## Deviations from Plan

- Plan mentioned `ScoringReport` model — not needed. `summarize_treatment()`
  returns a plain dict which is sufficient for CLI display and Wave 2 evaluation.
  If richer reporting is needed later, can be added then.
- Plan estimated ~25 new unit tests. Actual: 46 new unit tests (6 parse +
  12 persistence + 6 collect + 7 aggregate + 5 wave2 + 6 composite + 4 config).
- Documentation backfill (Phase 0-2 retros + Phase 1 plan) was not in the
  original Phase 3 plan but done as a process improvement.

## Implicit Assumptions Made Explicit

- Score persistence format is a flat JSON array of TieredScore dicts. One file
  per treatment at `data/scores/treatment-{id}.json`. Simple and grep-friendly.
- `load_all_scores()` identifies treatment files by `treatment-*.json` glob
  pattern and extracts treatment ID from filename via regex.
- Wave 2 decision uses population CV (not sample CV) — `variance = Σ(x-μ)²/N`
  not `/(N-1)`. With 8-11 treatments this is a minor difference but worth noting.
- `collect_scores` skips features without patch files rather than failing.

## Scope Changes for Next Phase

- Phase 3 infrastructure is ready. Next step is running Wave 1 experiments
  (core treatments) and collecting actual scores.
- Phase 3 retro is the last infrastructure phase — subsequent phases focus
  on experiment execution and analysis.

## Metrics

- **Tests added**: 46 unit + 8 acceptance = 54 new tests
- **Total tests**: 163 unit + 104 acceptance = 267
- **Files changed**: 23
- **Commits**: 10 (including plan, backfill docs, and documentation update)
- **New modules**: `scoring.py` (302 lines), `config/scoring.yaml`
