# Agent Teams Eval — Feature Implementation (ate-features)

## Overview

Experimental comparison of Claude Code with Agent Teams vs single-agent for
feature implementation on the LangGraph Python library. 11 treatments (8 core +
3 specialized variants), 8 features, tiered acceptance tests (T1/T2/T3/T4),
spec-based prompts (no issue URLs). Two-wave execution: Wave 1 (core), Wave 2
(specialized, contingent on Wave 1 variance).

Successor to [ate](https://github.com/kar-ganap/ate) which tested bug-fixing in
Ruff and found a ceiling effect (8/8 solve rate regardless of treatment, zero
inter-agent communication). This experiment targets the decomposition and
collaboration hypotheses with broader solution spaces.

## Tech Stack

- Python 3.11+ with uv
- Pydantic for data models
- Typer for CLI
- PyYAML for config
- pytest + ruff + mypy (strict)
- hatchling build backend

## Conventions

- TDD: tests before code, validation gates (`make test`, `make lint`, `make typecheck`)
- No Co-Authored-By in commits
- Phase branches off main, user merges manually
- `docs/experiment-design.md` is the north star
- Raw data in `data/` (gitignored contents), config in `config/` (committed)
- Dependency groups: core (always), dev (always), scoring (Phase 3+), analysis (Phase 5+)

## Project Structure

```
ate-features/
├── CLAUDE.md                  # This file (living state)
├── Makefile                   # test, lint, typecheck shortcuts
├── pyproject.toml             # uv + hatchling + ruff + mypy + pytest
├── config/
│   ├── features.yaml          # 8 LangGraph features with specs
│   ├── treatments.yaml        # 11 treatments (8 core + 3 specialized)
│   ├── scoring.yaml           # Composite weights + Wave 2 threshold
│   ├── execution.yaml         # Escape threshold, transcript path hint
│   ├── specializations/        # 4 agent domain context files
│   └── prompts/
│       └── communication_nudges.yaml  # Pattern-quality nudges
├── docs/
│   ├── desiderata.md          # Immutable principles
│   ├── process.md             # Phase lifecycle & validation gates
│   ├── experiment-design.md   # THE NORTH STAR
│   └── phases/                # plan + retro per phase
├── data/                      # Raw experiment data (gitignored contents)
│   ├── langgraph/             # Pinned LangGraph repo (commit b0f14649)
│   ├── transcripts/           # Session transcripts per treatment
│   ├── patches/               # Implementation patches per treatment
│   ├── scores/                # Tiered scores
│   └── acceptance-tests/      # T1/T2/T3 test suites per feature
├── src/ate_features/
│   ├── models.py              # Pydantic models (incl. PatchStatus, PreflightResult, TieredScore)
│   ├── config.py              # YAML loading + specialization + scoring + execution config
│   ├── harness.py             # Execution harness (scaffold, prompts, patches, preflight, verify)
│   ├── scoring.py             # Scoring: XML parsing, collection, aggregation, Wave 2
│   ├── runbook.py             # Per-treatment runbook generation
│   ├── communication.py       # Transcript parsing + communication models
│   └── cli.py                 # CLI with comms + exec + score subcommands
├── tests/
│   ├── unit/                  # Unit tests (204 tests)
│   └── acceptance/            # LangGraph acceptance tests (104 tests)
├── scripts/
│   ├── pin_langgraph.sh       # Clone pinned LangGraph
│   └── setup_langgraph.sh     # Editable install of LangGraph libs
└── scripts/                   # Utility scripts
```

## Key References

- `docs/desiderata.md` — Immutable principles (10 items)
- `docs/process.md` — Phase lifecycle (PLAN → TEST → IMPLEMENT → RETRO)
- `docs/experiment-design.md` — Full experiment protocol
- `../ate/docs/findings.md` — Prior experiment findings (bug-fixing ceiling effect)

## Current State

**Phase 4 complete.** Execution runner: preflight checks (records CC
version), patch instructions in opening prompts, patch verification
(`PatchStatus` model), runbook generation (11 per-treatment runbooks
in `docs/runbooks/`), execution config (`config/execution.yaml`).

204 unit tests + 104 acceptance tests = 308 total.

## Phases

| Phase | Branch | Status |
|-------|--------|--------|
| 0 | `phase-0-scaffold` | Complete |
| 1 | `phase-1-langgraph-tests` | Complete |
| 2 | `phase-2-execution-harness` | Complete |
| 3 | `phase-3-scoring-framework` | Complete |
| 4 | `phase-4-execution-runner` | Complete |

## Acceptance Test Results (against pinned LangGraph)

| Feature | T1 | T2 | T3 | T4 | Fails | Notes |
|---------|----|----|-----|-----|-------|-------|
| F1 Pandas serde | 3F | 5F | 3F | 2F | 13/13 | No pandas handler |
| F2 Pydantic round-trip | 3F | 5F | 3F | 2F | 13/13 | No `.dumps` method |
| F3 StrEnum preservation | 3F | 5F | 3F | 2F | 13/13 | StrEnum not preserved |
| F4 Nested Enum | 3F | 5F | 3F | 2F | 13/13 | Enums in containers lost |
| F5 Reducer metadata | 3F | 5F | 3F | 2F | 13/13 | `meta[-1]` only checks last |
| F6 Default factory | 3F | 5F | 3F | 2F | 13/13 | `typ()` ignores factory |
| F7 Nested emission | 3F | 5F | 3F | 2F | 13/13 | 2-level scan only |
| F8 Nested dedup | 3F | 5F | 3F | 2F | 13/13 | Input msgs not tracked |

All 104 tests fail against pinned commit. 0 passing. Uniform structure:
3 T1 + 5 T2 + 3 T3 + 2 T4 = 13 per feature.

## Communication Infrastructure

- `src/ate_features/communication.py` — models, transcript parser, summary
- `config/prompts/communication_nudges.yaml` — pattern-quality nudges
- CLI: `ate-features comms parse <session-id>`, `ate-features comms summary <session-id> <treatment-id>`
- Nudge dimension stays `encourage|discourage|neutral` but text enriched with examples

## Execution Harness

- `src/ate_features/harness.py` — directory mgmt, prompts, scaffolding, patches, preflight, verify
- `config/specializations/serde_*.md` — 4 domain context files named by content
- `config/execution.yaml` — escape threshold (45 min), transcript path hint
- CLI: `ate-features exec scaffold <tid>`, `ate-features exec status`,
  `ate-features exec preflight`, `ate-features exec verify-patches <tid>`,
  `ate-features exec runbook <tid>`, `ate-features exec runbooks`
- `preflight_check()` verifies LangGraph pin + clean tree, records CC version
- `verify_patches()` checks F1-F8 patches: exist → non-empty → applies cleanly
- Opening prompts include git diff/checkout/clean patch instructions by default
- `src/ate_features/runbook.py` — per-treatment markdown runbooks with shell commands,
  monitoring, checklists. 11 runbooks committed in `docs/runbooks/`
- Specialization files mapped by agent number: `load_specialization(1-4)`
- Per-feature treatments (0b, 6): 8×1 without Agent Teams → 8 sub-directories
- `apply_patch()` does `--check` before `apply`; `revert_langgraph()` does `checkout . && clean -fd`

## Scoring Infrastructure

- `src/ate_features/scoring.py` — JUnit XML parsing, score collection/persistence, aggregation, Wave 2 decision
- `config/scoring.yaml` — composite weights (T1=0.15, T2=0.35, T3=0.30, T4=0.20) + CV threshold (0.10)
- `TieredScore.composite(weights)` — weighted combination on the model
- Collection pipeline: apply patch → pytest --junitxml → parse XML → revert → persist to `data/scores/`
- Wave 2 decision: CV of mean composites across treatments; CV > threshold → recommend Wave 2
- CLI: `ate-features score collect <tid>`, `ate-features score show [tid]`, `ate-features score decide-wave2`

## Known Gotchas

- pyproject.toml: `dependencies` must come before `[project.scripts]` in the
  `[project]` table, otherwise hatchling fails
- `from __future__ import annotations` + `get_type_hints()`: TypedDicts/dataclasses
  with `Annotated` fields defined in local scope fail because names must be in
  module-level globals. Acceptance tests MUST NOT use `from __future__ import
  annotations` — all annotation features work natively in Python 3.11
- `data/langgraph/.gitkeep` must be removed before `git clone` into the directory
- `make test-acceptance` requires `make setup-langgraph` first
