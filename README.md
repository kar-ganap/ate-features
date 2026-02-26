# Agent Teams Eval — Feature Implementation (ate-features)

Experimental comparison of Claude Code with Agent Teams (symmetric peers) vs
single-agent paradigm for feature implementation on
[LangGraph](https://github.com/langchain-ai/langgraph).

**Key finding:** Ceiling effect — all treatments score 104/104 on tiered
acceptance tests and 14/16 on post-hoc robustness tests. Zero peer-to-peer
communication. Agent Teams provides a 3.6x wall-clock speedup (28 min solo
vs 8 min with 8 agents) with no quality improvement. Parallelism, not
collaboration.

Second in the [ate-series](https://github.com/kar-ganap/ate-series). Predecessor:
[ate](https://github.com/kar-ganap/ate) (bug-fixing in Ruff). Successor:
[ate-arch](https://github.com/kar-ganap/ate-arch) (architecture design — first
significant result).

## Results at a Glance

| Treatment | T1–T4 Score | T5 Robustness | Wall Clock | Peer Messages |
|-----------|-------------|---------------|------------|---------------|
| 0a (solo) | 104/104 | 14/16 | 28 min | N/A |
| 1 (4-agent, 2 features each) | 104/104 | 14/16 | 12 min | 0 |
| 5 (8-agent, 1 feature each) | 104/104 | 14/16 | 8 min | 0 |

See [findings](docs/findings.md) for full analysis and
[experiment-design.md](docs/experiment-design.md) for the protocol.

## Quick Start

```bash
uv sync --group dev
uv run ate-features exec status
uv run ate-features score show
```

## Built On

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) — agentic coding tool
- [Agent Teams & Subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents) — the multi-agent infrastructure under study

## Validation Gates

```bash
make test            # Unit tests (238)
make test-acceptance # Acceptance tests (104, requires LangGraph setup)
make lint            # Ruff linter
make typecheck       # mypy strict
```
