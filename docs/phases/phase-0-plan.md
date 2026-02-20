# Phase 0: Scaffold ate-features Project

## Goal

Create the project skeleton for the feature implementation experiment, carrying
over reusable patterns from the predecessor `ate` project while building fresh
infrastructure for tiered acceptance tests, spec-based prompts, and LangGraph
features.

## Deliverables

1. Project root: pyproject.toml, Makefile, .gitignore, CLAUDE.md, README.md
2. Config: features.yaml (8 LangGraph features), treatments.yaml (8 treatments)
3. Docs: desiderata.md (10 principles), process.md, experiment-design.md skeleton
4. Source: Pydantic models, YAML config loading
5. Directory structure: data/, tests/, scripts/

## Acceptance Criteria

- `uv sync --group dev` succeeds
- `make test` passes (0 tests collected OK)
- `make lint` is clean
- `make typecheck` is clean
- Git initialized with initial commit
