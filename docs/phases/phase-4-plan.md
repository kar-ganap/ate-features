# Phase 4: Execution Runner

## Goal

Build operational infrastructure for running Wave 1 experiments reliably.
Phases 0-3 built the *what* (scaffolding, tests, scoring); Phase 4 builds
the *how* (preflight checks, patch instructions, patch verification,
per-treatment runbooks).

## Deliverables

1. **Execution config** (`config/execution.yaml`): escape threshold,
   transcript path hint
2. **Preflight checks** (`harness.py`): verify LangGraph pin + clean tree,
   record Claude Code version (informational, not enforced)
3. **Patch instructions** in opening prompts: git diff/checkout/clean
   commands appended to `get_opening_prompt()` output
4. **Patch verification** (`harness.py`): `PatchStatus` enum + `verify_patches()`
   to check F1-F8 patch files exist and apply cleanly
5. **Runbook generation** (`runbook.py`): per-treatment markdown runbooks
   with shell commands, monitoring guidance, checklists
6. **CLI extensions**: `exec preflight`, `exec verify-patches`, `exec runbook`,
   `exec runbooks`

## Acceptance Criteria

- `make test` passes (~203 unit tests + 104 acceptance tests)
- `make lint` is clean
- `make typecheck` is clean
- `ate-features exec preflight` reports LangGraph state + CC version
- `ate-features exec runbook 0a` generates a complete runbook
- `ate-features exec runbooks` generates 11 runbook files to `docs/runbooks/`
- `ate-features exec verify-patches 0a` reports all missing (no data yet)
