# Phase 1: LangGraph Pinning, Acceptance Tests & Communication Infrastructure

## Goal

Pin LangGraph at a specific commit, write tiered acceptance tests for all 8
features, set up communication infrastructure for transcript analysis, and
establish the test baseline — all tests must FAIL against the pinned commit.

## Deliverables

1. **LangGraph pin**: Clone at commit `b0f14649`, editable install scripts
2. **Acceptance tests**: T1/T2/T3 suites for F1-F8 (88 tests initially)
3. **Communication module** (`src/ate_features/communication.py`): transcript
   parser, event models, summary generation
4. **Communication nudges** (`config/prompts/communication_nudges.yaml`):
   pattern-quality nudges for encourage/discourage dimension
5. **CLI extensions**: `comms parse`, `comms summary` commands
6. **Config updates**: `load_communication_nudges()` loader

## Mid-Phase Scope Changes

- **F5-F8 replaced**: Original features were too easy (9-11/11 passing against
  pinned commit). Replaced with harder features in state and streaming subsystems.
- **T4 tier added**: Smoke/integration tests (2 per feature) for F5-F8. F1-F4
  deferred to Phase 3 backfill.
- **Treatment expansion**: Specialization dimension added (vanilla vs specialized),
  growing from 8 to 11 treatments (8 core + 3 specialized variants).

## Acceptance Criteria

- `make test` passes (~50 unit tests)
- `make lint` is clean
- `make typecheck` is clean
- All 96 acceptance tests fail against pinned LangGraph
- `ate-features comms parse <session-id>` works with mock transcripts
