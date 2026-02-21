# Phase 0 Retrospective: Scaffold

## What Worked

- Carrying over patterns from the predecessor `ate` project (Pydantic models,
  YAML config, Typer CLI, TDD workflow) made scaffolding fast.
- Establishing `docs/process.md` and `docs/desiderata.md` upfront gave clear
  guardrails for all subsequent phases.
- The `experiment-design.md` skeleton served as a living north-star document.

## Surprises

- hatchling requires `dependencies` before `[project.scripts]` in pyproject.toml —
  discovered when CLI entry point failed to resolve. Added as a known gotcha.

## Deviations from Plan

- None significant. Phase 0 was straightforward scaffolding.

## Implicit Assumptions Made Explicit

- Python 3.11+ assumed (for StrEnum, native type unions, etc.).
- uv as the only package manager (no pip).
- Each phase gets its own git branch; user merges to main manually.

## Scope Changes for Next Phase

- Phase 1 needs LangGraph pinned at a specific commit before acceptance tests
  can be written.
- Communication infrastructure (from predecessor ate) needs to be ported.

## Metrics

- **Tests added**: 13 unit tests
- **Files created**: 27
- **Commits**: 1
