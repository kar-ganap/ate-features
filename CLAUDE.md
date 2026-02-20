# Agent Teams Eval — Feature Implementation (ate-features)

## Overview

Experimental comparison of Claude Code with Agent Teams vs single-agent for
feature implementation on the LangGraph Python library. 8 treatments, 8 features,
tiered acceptance tests (T1/T2/T3), spec-based prompts (no issue URLs).

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
│   └── treatments.yaml        # 8 treatments (same matrix as ate)
├── docs/
│   ├── desiderata.md          # Immutable principles
│   ├── process.md             # Phase lifecycle & validation gates
│   ├── experiment-design.md   # THE NORTH STAR
│   └── phases/                # plan + retro per phase
├── data/                      # Raw experiment data (gitignored contents)
│   ├── langgraph/             # Pinned LangGraph repo
│   ├── transcripts/           # Session transcripts per treatment
│   ├── patches/               # Implementation patches per treatment
│   ├── scores/                # Tiered scores
│   └── acceptance-tests/      # T1/T2/T3 test suites per feature
├── src/ate_features/
│   ├── models.py              # Pydantic models
│   └── config.py              # YAML loading
├── tests/
│   ├── unit/                  # Mocked tests
│   └── integration/           # Real LangGraph tests
└── scripts/                   # Utility scripts
```

## Key References

- `docs/desiderata.md` — Immutable principles (10 items)
- `docs/process.md` — Phase lifecycle (PLAN → TEST → IMPLEMENT → RETRO)
- `docs/experiment-design.md` — Full experiment protocol
- `../ate/docs/findings.md` — Prior experiment findings (bug-fixing ceiling effect)

## Current State

**Phase 0 complete.** Project scaffolded with models, config loading, and
directory structure. No features pinned, no acceptance tests written yet.

## Phases

| Phase | Branch | Status |
|-------|--------|--------|
| 0 | `phase-0-scaffold` | Complete |
| 1 | TBD | Pending — pin LangGraph, write acceptance tests |

## Known Gotchas

- pyproject.toml: `dependencies` must come before `[project.scripts]` in the
  `[project]` table, otherwise hatchling fails
