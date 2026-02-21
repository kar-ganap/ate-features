# Phase 5: Cumulative Scoring Mode

## Context

Treatment 0a (control) scored 97.5% in 30 minutes — ceiling effect, same as
ate Round 1. Root cause: **patch-and-reset protocol eliminates collaboration
signal**. Each feature starts from clean tree, so agents on shared files
(F1/F2 both touch `_msgpack_default()`) never see each other's changes.
There is nothing to coordinate about.

Redesign: agents work cumulatively on the same tree. No resets between features.
One combined result scored against all 104 acceptance tests. This creates real
coordination opportunities — parallel agents editing the same file must
coordinate or their changes conflict.

Keep all existing isolated-mode code. Add cumulative as a parallel mode.

## Protocol: Cumulative Mode

**Agent workflow:**
1. Implement F1
2. `git diff > data/patches/treatment-{tid}/F1.patch` (snapshot)
3. `git add -A` (stage F1 changes)
4. Implement F2
5. `git diff > data/patches/treatment-{tid}/F2.patch` (incremental snapshot)
6. `git add -A` (stage F2 changes)
7. ... repeat for F3-F8 ...
8. `git diff --staged > data/patches/treatment-{tid}/cumulative.patch` (combined)

**Scoring:**
1. Apply `cumulative.patch` to clean langgraph
2. Run all 104 acceptance tests with `--junitxml`
3. Parse XML, group testcases by feature ID (from classname)
4. Compute per-feature TieredScores
5. Revert langgraph

**Treatments to run (3 total):**
- 0a: Control — single agent, sequential, no AT
- 1: Structured Team — AT, explicit decomposition, 4x2
- 5: Max Parallelism — AT, explicit decomposition, 8x1

## Deliverables

1. Cumulative scoring functions in `scoring.py`
2. Cumulative prompt instructions in `harness.py`
3. Cumulative runbook sections in `runbook.py`
4. CLI `--mode` flag on scoring and runbook commands
5. Documentation updates

## Implementation Order

TDD throughout. ~18 new unit tests. No files deleted, no config changes.
