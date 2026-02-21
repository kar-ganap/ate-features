# Phase 3: Scoring Framework

## Goal

Build scoring infrastructure to collect test results, compute composite scores,
and evaluate the Wave 2 decision gate. Also backfill T4 smoke tests for F1-F4
so all 8 features have uniform tier structure (13 tests each, 104 total).

## Deliverables

1. **T4 backfill**: 2 T4 smoke tests per F1-F4 (8 new acceptance tests)
2. **Scoring config** (`config/scoring.yaml`): tier weights + Wave 2 threshold
3. **Composite model**: `TieredScore.composite(weights)` + `ScoringReport`
4. **Scoring module** (`src/ate_features/scoring.py`): JUnit XML parsing,
   score collection/persistence, aggregation, Wave 2 decision gate
5. **CLI extensions**: `score collect`, `score show`, `score decide-wave2`

## Acceptance Criteria

- `make test` passes (~142 unit tests + 104 acceptance tests)
- `make lint` is clean
- `make typecheck` is clean
- All 104 acceptance tests fail against pinned LangGraph
- `ate-features score show` displays rich table (with mock data)
