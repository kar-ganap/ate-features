# Agent Teams Eval — Feature Implementation (ate-features)

## Overview

Experimental comparison of Claude Code with Agent Teams vs single-agent for
feature implementation on the LangGraph Python library. 8 treatments, 8 features,
tiered acceptance tests (T1/T2/T3/T4), spec-based prompts (no issue URLs).

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
│   ├── treatments.yaml        # 8 treatments (same matrix as ate)
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
│   ├── models.py              # Pydantic models
│   ├── config.py              # YAML loading + communication nudges
│   ├── communication.py       # Transcript parsing + communication models
│   └── cli.py                 # CLI with comms subcommand
├── tests/
│   ├── unit/                  # Mocked tests (40 tests)
│   └── acceptance/            # LangGraph acceptance tests (96 tests)
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

**Phase 1 complete.** LangGraph pinned (b0f14649), 96 acceptance tests across
8 features (all failing), communication infrastructure (transcript parser,
pattern-quality nudges, CLI).

40 unit tests + 96 acceptance tests = 136 total.

## Phases

| Phase | Branch | Status |
|-------|--------|--------|
| 0 | `phase-0-scaffold` | Complete |
| 1 | `phase-1-langgraph-tests` | Complete |
| 2 | TBD | Pending — execution infrastructure, treatment runner |

## Acceptance Test Results (against pinned LangGraph)

| Feature | T1 | T2 | T3 | T4 | Fails | Notes |
|---------|----|----|-----|-----|-------|-------|
| F1 Pandas serde | 3F | 5F | 3F | — | 11/11 | No pandas handler |
| F2 Pydantic round-trip | 3F | 5F | 3F | — | 11/11 | No `.dumps` method |
| F3 StrEnum preservation | 3F | 5F | 3F | — | 11/11 | StrEnum not preserved |
| F4 Nested Enum | 3F | 5F | 3F | — | 11/11 | Enums in containers lost |
| F5 Reducer metadata | 3F | 5F | 3F | 2F | 13/13 | `meta[-1]` only checks last |
| F6 Default factory | 3F | 5F | 3F | 2F | 13/13 | `typ()` ignores factory |
| F7 Nested emission | 3F | 5F | 3F | 2F | 13/13 | 2-level scan only |
| F8 Nested dedup | 3F | 5F | 3F | 2F | 13/13 | Input msgs not tracked |

All 96 tests fail against pinned commit. 0 passing.

## Communication Infrastructure

- `src/ate_features/communication.py` — models, transcript parser, summary
- `config/prompts/communication_nudges.yaml` — pattern-quality nudges
- CLI: `ate-features comms parse <session-id>`, `ate-features comms summary <session-id> <treatment-id>`
- Nudge dimension stays `encourage|discourage|neutral` but text enriched with examples

## Known Gotchas

- pyproject.toml: `dependencies` must come before `[project.scripts]` in the
  `[project]` table, otherwise hatchling fails
- `from __future__ import annotations` + `get_type_hints()`: TypedDicts/dataclasses
  with `Annotated` fields defined in local scope fail because names must be in
  module-level globals. Acceptance tests MUST NOT use `from __future__ import
  annotations` — all annotation features work natively in Python 3.11
- `data/langgraph/.gitkeep` must be removed before `git clone` into the directory
- `make test-acceptance` requires `make setup-langgraph` first
