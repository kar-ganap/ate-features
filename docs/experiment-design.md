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
- **Specialization**: Does giving agents subsystem domain context (via spawn prompt
  enrichment) improve outcomes — and does it interact with team collaboration?

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
| F5 | Reducer metadata ordering dependency | state |
| F6 | BinaryOperatorAggregate ignores default_factory | state |
| F7 | Nested message detection in stream_mode=messages | streaming |
| F8 | Input message dedup for nested structures | streaming |

## 4. Acceptance Test Design

Tiered methodology creating a quality gradient:

- **T1 (Basic)**: Does the feature work for the simple case? First approach passes.
- **T2 (Edge Cases)**: Does it handle boundary conditions? First approach may fail.
- **T3 (Quality)**: Is it robust, performant, and maintainer-acceptable? First
  approach probably fails.
- **T4 (Smoke/Integration)**: End-to-end realistic multi-node workflows with
  checkpointer. Tests behavioral correctness in production-like scenarios.

Per feature: 3 T1 + 5 T2 + 3 T3 + 2 T4 = 13 tests. 8 features × 13 = 104 total.
All tests FAIL against pinned commit.

## 5. Prompt Design

Spec-based prompts only. No GitHub issue URLs. The agent receives:
1. A feature description (from `config/features.yaml`)
2. The acceptance test suite (T1/T2/T3)
3. The pinned codebase

No hints about existing PRs, discussions, or solution approaches.

## 6. Treatment Matrix

11 treatments across 7 dimensions. See `config/treatments.yaml` for full definitions.

### Wave 1: Core Treatments (8)

| ID | Label | Decomposition | Prompt | Delegate | Team Size | Communication | Specialization |
|----|-------|---------------|--------|----------|-----------|---------------|----------------|
| 0a | Control: Full Context | explicit | detailed | N/A | 1x8 | N/A | vanilla |
| 0b | Control: Swim Lanes | explicit | detailed | N/A | 8x1 | N/A | vanilla |
| 1 | Structured Team | explicit | detailed | on | 4x2 | neutral | vanilla |
| 2a | Autonomous + Encourage | autonomous | vague | on | 4x2 | encourage | vanilla |
| 2b | Autonomous + Discourage | autonomous | vague | on | 4x2 | discourage | vanilla |
| 3 | Invest in Prompts | autonomous | detailed | on | 4x2 | neutral | vanilla |
| 4 | Player-Coach | autonomous | vague | off | 4x2 | neutral | vanilla |
| 5 | Max Parallelism | explicit | detailed | on | 8x1 | neutral | vanilla |

### Wave 2: Specialized Variants (3)

Run after Wave 1, contingent on Wave 1 producing score variance across treatments.

| ID | Label | Paired With | Decomposition | Prompt | Delegate | Team Size | Communication | Specialization |
|----|-------|-------------|---------------|--------|----------|-----------|---------------|----------------|
| 6 | Specialized Swim Lanes | 0b | explicit | detailed | N/A | 8x1 | N/A | specialized |
| 7 | Specialized Structured Team | 1 | explicit | detailed | on | 4x2 | neutral | specialized |
| 8 | Specialized + Encourage | 2a | autonomous | vague | on | 4x2 | encourage | specialized |

### Specialization Dimension

Specialized treatments enrich each agent's spawn prompt with subsystem domain
context: key files, architecture descriptions, and cross-subsystem boundaries.
This is delivered via Agent Teams spawn prompts (the only per-agent customization
mechanism currently supported).

Specialization content includes subsystem architecture and key entry points but
explicitly excludes feature-specific hints, solution approaches, or knowledge of
other agents' features.

Specialization definitions are authored in Phase 2 as part of execution
infrastructure. See `config/specializations/` (Phase 2).

### Paired Comparisons

| Pair | Treatments | Tests |
|------|-----------|-------|
| 0b vs 6 | Solo vanilla vs solo specialized | Does domain context help individual agents? |
| 1 vs 7 | Team vanilla vs team specialized | Does domain context enable team collaboration? |
| 2a vs 8 | Encourage vanilla vs encourage specialized | Can domain context compensate for vague prompts? |

Each pair yields 8 paired observations (one per feature). Across 3 pairs: 24
paired observations, sufficient for Wilcoxon signed-rank test on specialization
effect.

## 7. Feature Assignments + Correlation Pairs

### Assignments (explicit treatments)

| Agent | Features | Rationale |
|-------|----------|-----------|
| 1 | F1, F5 | serializer/new + state/metadata |
| 2 | F2, F6 | serializer/new + state/defaults |
| 3 | F3, F7 | serializer/fix + streaming/emission |
| 4 | F4, F8 | serializer/fix + streaming/dedup |

### Correlation Pairs

| Pair | Features | Shared Subsystem |
|------|----------|------------------|
| serializer_new_types | F1, F2 | Both extend _msgpack_default()/_msgpack_ext_hook() |
| serializer_type_preservation | F3, F4 | Both fix EXT_CONSTRUCTOR mechanism |
| state_management | F5, F6 | Both fix channel creation pipeline (state.py -> binop.py) |
| streaming_messages | F7, F8 | Both fix _messages.py (emission + dedup) |

## 8. Measurement Framework

### Tiered Scoring

For each feature x treatment:
- T1 score: `t1_passed / t1_total` (automated)
- T2 score: `t2_passed / t2_total` (automated, edge cases)
- T3 score: `t3_passed / t3_total` (quality assessment)
- T4 score: `t4_passed / t4_total` (smoke/integration)
- Composite: `0.15*T1 + 0.35*T2 + 0.30*T3 + 0.20*T4`

### Composite Weights

| Tier | Weight | Rationale |
|------|--------|-----------|
| T1 (basic) | 0.15 | Low discriminating power — expected to mostly pass |
| T2 (edge cases) | 0.35 | Highest test count (5/feature), best signal |
| T3 (quality) | 0.30 | Robustness/performance, meaningful differentiation |
| T4 (smoke) | 0.20 | Integration tests, checkpoint round-trips |

Weights stored in `config/scoring.yaml` (committed, not hardcoded).

### Wave 2 Decision Gate

Coefficient of variation (CV) of mean composite scores across treatments.
If CV > 0.10 → recommend Wave 2 (specialized treatments add signal).
CLI: `ate-features score decide-wave2`.

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

### Harness

The execution harness (`src/ate_features/harness.py`) automates session setup:

1. **Scaffold**: `ate-features exec scaffold <treatment_id>` creates session
   directories with `session_guide.md`, `metadata.json`, and `notes.md`.
   Per-feature treatments (0b, 6) create 8 sub-directories.
2. **Prompt**: `get_opening_prompt()` generates detailed or vague prompts based
   on the treatment's `prompt_specificity` dimension. Specialized treatments
   receive domain context preambles; encourage/discourage treatments get
   communication nudges.
3. **Patch**: After implementation, extract patches per feature. `apply_patch()`
   validates with `--check` before applying. `revert_langgraph()` resets to
   pinned state between treatments.
4. **Status**: `ate-features exec status` shows the 11×8 completion matrix.

### Specialization Files

4 domain context files in `config/specializations/`, named by content:
- `serde_types_and_state_channels.md` (Agent 1: F1, F5)
- `serde_pydantic_and_state_reducers.md` (Agent 2: F2, F6)
- `serde_enums_and_stream_emission.md` (Agent 3: F3, F7)
- `serde_nested_and_stream_dedup.md` (Agent 4: F4, F8)

### Session Workflow

1. Scaffold the treatment session
2. Review the session guide
3. Start Claude Code in the pinned LangGraph directory
4. Paste the opening prompt (from the guide)
5. Let the agent(s) work; record the session transcript
6. Extract patches, run acceptance tests, record scores
7. Update metadata.json with timestamps and notes
8. Revert LangGraph to clean state before next treatment

### Wave Structure

- **Wave 1**: Run treatments 0a–5 (8 core treatments). Decision gate: do scores
  vary enough across treatments to justify Wave 2?
- **Wave 2**: Run treatments 6–8 (3 specialized variants). Only if Wave 1 shows
  meaningful variance.

## 10. Cumulative Scoring Mode

### Motivation

Treatment 0a (control) scored 97.5% in 30 minutes — a ceiling effect identical
to the predecessor experiment. Root cause: the **isolated patch-and-reset
protocol eliminates the collaboration signal**. Each feature starts from a clean
working tree, so agents working on correlated features (e.g., F1/F2 both
modifying `_msgpack_default()`) never see each other's changes. The collaboration
hypothesis requires concurrent work on shared files, but isolated measurement
resets the tree between features — making these goals mutually exclusive.

### Protocol

In cumulative mode, agents work on the **same working tree** without resets:

1. Implement F1
2. `git diff > data/patches/treatment-{tid}/F1.patch` (snapshot)
3. `git add -A` (stage changes, keep working)
4. Implement F2
5. `git diff > data/patches/treatment-{tid}/F2.patch` (incremental snapshot)
6. `git add -A`
7. ... repeat for F3–F8 ...
8. `git diff --staged > data/patches/treatment-{tid}/cumulative.patch` (combined)

Scoring applies `cumulative.patch` to a clean tree, runs all 104 acceptance
tests, and groups results by feature ID (extracted from test classnames).

### Treatments (Cumulative Round)

Three treatments to compare:

| ID | Label | Why |
|----|-------|-----|
| 0a | Control | Single agent, sequential — natural coordination |
| 1 | Structured Team | AT, explicit decomposition, 4×2 — structured coordination |
| 5 | Max Parallelism | AT, explicit decomposition, 8×1 — maximum parallelism |

### CLI Usage

```bash
# Score with cumulative mode
ate-features score collect 0a --mode cumulative

# Generate runbooks with cumulative instructions
ate-features exec runbook 0a --mode cumulative
ate-features exec runbooks --mode cumulative
```

Existing isolated mode remains the default (`--mode isolated`).

## 11. Change Log

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-02-20 | Initial design | Phase 0 scaffolding |
| 2026-02-20 | Phase 1: pinned LangGraph, 88 acceptance tests, communication infrastructure | Baseline for treatments |
| 2026-02-20 | Flag: F7 (END routing) all 11 tests pass on pinned commit | May need replacement feature |
| 2026-02-20 | Replace F5-F8: harder features, add T4 smoke tier, 96 total tests (all fail) | F5-F8 too easy (9-11/11 passing) |
| 2026-02-20 | Add specialization dimension + 3 treatments (6, 7, 8), 2-wave execution | Test whether spawn-prompt domain context improves outcomes |
| 2026-02-20 | Phase 2: execution harness, specialization files, CLI exec commands | Scaffold/prompt/patch/status infrastructure for running treatments |
| 2026-02-20 | Phase 3: T4 backfill F1-F4 (104 total), scoring framework, Wave 2 gate | Composite weights, JUnit XML parsing, score collection, CLI score commands |
| 2026-02-20 | Phase 4: execution runner — preflight, patch instructions, verify, runbooks | Operational infrastructure for running Wave 1 treatments reliably |
| 2026-02-20 | Phase 5: cumulative scoring mode — parallel to isolated, no resets, cumulative.patch | Isolated protocol eliminates collaboration signal; cumulative creates coordination opportunities |
