# Experiment Design

The north star for the Agent Teams Eval (Feature Implementation) experiment.

## 1. Research Question

Does Claude Code with Agent Teams outperform single-agent Claude Code on feature
implementation tasks where the outcome is genuinely uncertain a priori?

Specifically: for tasks with broad solution spaces and natural decomposition
boundaries, does inter-agent collaboration (information sharing about shared
subsystems) improve solution quality beyond what parallel independent work achieves?

### Hypotheses Under Test

- **Decomposition**: Does explicit task decomposition across agents improve quality
  when features share subsystems?
- **Collaboration**: Does inter-agent communication about shared code paths lead to
  better solutions than independent parallel work?

### Prior Work

The predecessor experiment ([ate](https://github.com/kar-ganap/ate)) tested
bug-fixing in the Ruff Python linter. Key findings:
- Ceiling effect: 8/8 solve rate regardless of treatment configuration
- Zero inter-agent communication across all team treatments
- Bug-fixing in single codebases is structurally biased toward solo agents

See `../ate/docs/findings.md` for the full writeup.

## 2. OSS Target

**LangGraph** — Python graph-based agent orchestration library by LangChain.

- Repository: `https://github.com/langchain-ai/langgraph`
- Pin commit: `b0f14649e0669a6399cb790d23672591a2a52884`
- Pin date: 2026-02-20
- Build: `pip install -e libs/langgraph && pip install -e libs/checkpoint`
- Test: `cd libs/langgraph && pytest tests/`

## 3. Feature Portfolio

8 features across 4 subsystems. See `config/features.yaml` for full specs.

| ID | Title | Subsystem |
|----|-------|-----------|
| F1 | Pandas DataFrame/Series msgpack serialization | serializer |
| F2 | Generic Pydantic v2 type round-trip in checkpoint serde | serializer |
| F3 | StrEnum preservation in checkpoint serde | serializer |
| F4 | Nested Enum deserialization fix | serializer |
| F5 | Pydantic state with aliased fields | state |
| F6 | Dataclass defaults with reducer | state |
| F7 | END routing in conditional edges | graph |
| F8 | messages_key streaming filter | streaming |

## 4. Acceptance Test Design

Tiered methodology creating a quality gradient:

- **T1 (Basic)**: Does the feature work for the simple case? First approach passes.
- **T2 (Edge Cases)**: Does it handle boundary conditions? First approach may fail.
- **T3 (Quality)**: Is it robust, performant, and maintainer-acceptable? First
  approach probably fails.

Acceptance test suites written in Phase 1. Existing PR solutions (if any) should
fail T2/T3.

## 5. Prompt Design

Spec-based prompts only. No GitHub issue URLs. The agent receives:
1. A feature description (from `config/features.yaml`)
2. The acceptance test suite (T1/T2/T3)
3. The pinned codebase

No hints about existing PRs, discussions, or solution approaches.

## 6. Treatment Matrix

8 treatments. See `config/treatments.yaml` for full definitions.

| ID | Label | Decomposition | Prompt | Delegate | Team Size | Communication |
|----|-------|---------------|--------|----------|-----------|---------------|
| 0a | Control: Full Context | explicit | detailed | N/A | 1x8 | N/A |
| 0b | Control: Swim Lanes | explicit | detailed | N/A | 8x1 | N/A |
| 1 | Structured Team | explicit | detailed | on | 4x2 | neutral |
| 2a | Autonomous + Encourage | autonomous | vague | on | 4x2 | encourage |
| 2b | Autonomous + Discourage | autonomous | vague | on | 4x2 | discourage |
| 3 | Invest in Prompts | autonomous | detailed | on | 4x2 | neutral |
| 4 | Player-Coach | autonomous | vague | off | 4x2 | neutral |
| 5 | Max Parallelism | explicit | detailed | on | 8x1 | neutral |

## 7. Feature Assignments + Correlation Pairs

### Assignments (explicit treatments)

| Agent | Features | Rationale |
|-------|----------|-----------|
| 1 | F1, F5 | serializer/new + state/pydantic |
| 2 | F2, F6 | serializer/new + state/defaults |
| 3 | F3, F7 | serializer/fix + graph/routing |
| 4 | F4, F8 | serializer/fix + streaming |

### Correlation Pairs

| Pair | Features | Shared Subsystem |
|------|----------|------------------|
| serializer_new_types | F1, F2 | Both extend _msgpack_default()/_msgpack_ext_hook() |
| serializer_type_preservation | F3, F4 | Both fix EXT_CONSTRUCTOR mechanism |
| state_management | F5, F6 | Both fix Pydantic/dataclass channel init |
| graph_api | F7, F8 | Both modify graph compilation/execution |

## 8. Measurement Framework

### Tiered Scoring

For each feature x treatment:
- T1 score: `t1_passed / t1_total` (automated)
- T2 score: `t2_passed / t2_total` (automated, edge cases)
- T3 score: `t3_passed / t3_total` (quality assessment)
- Composite: weighted combination (weights TBD in Phase 3)

### Communication Analysis

Enhanced from predecessor experiment:
- Only `SendMessage(recipient=<peer>)` with routing metadata counts
- Structured transcript parser (`src/ate_features/communication.py`) extracts
  sender, recipient, content, and auto-classifies taxonomy
- Pattern-quality nudges (`config/prompts/communication_nudges.yaml`) enrich
  the encourage/discourage dimension with concrete examples of useful vs
  wasteful communication
- CLI support: `ate-features comms parse <session-id>`

## 9. Execution Protocol

TBD — detailed in Phase 2.

## 10. Change Log

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-02-20 | Initial design | Phase 0 scaffolding |
| 2026-02-20 | Phase 1: pinned LangGraph, 88 acceptance tests, communication infrastructure | Baseline for treatments |
| 2026-02-20 | Flag: F7 (END routing) all 11 tests pass on pinned commit | May need replacement feature |
