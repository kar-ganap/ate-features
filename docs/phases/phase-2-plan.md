# Phase 2: Execution Infrastructure & Treatment Runner

## Goal

Build the harness to scaffold, prompt, and manage treatment sessions so
experiments can run. Includes specialization definitions for Wave 2 treatments,
opening prompt generation (detailed/vague × specialization), session guides,
directory management, and patch utilities.

## Deliverables

1. **Harness module** (`src/ate_features/harness.py`): directory management,
   treatment introspection, prompt generation, session guides, scaffolding,
   patch management
2. **Specialization definitions** (`config/specializations/serde_*.md`):
   subsystem domain context for specialized treatments, named by content
3. **Model updates**: T4 acceptance tier, RunMetadata
4. **Config extension**: `load_specialization()` loader
5. **CLI extensions**: `exec scaffold`, `exec status` commands

## Acceptance Criteria

- `make test` passes (~106 unit tests)
- `make lint` is clean
- `make typecheck` is clean
- `ate-features exec scaffold 1` creates session directory with guide
- `ate-features exec scaffold 0b` creates 8 per-feature directories
- `ate-features exec status` shows 11×8 completion matrix
