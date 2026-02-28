# Findings: Agent Teams vs Single Agent for Feature Implementation

## Abstract

We designed an experiment to compare Claude Code's Agent Teams (multi-agent
coordination) against single-agent Claude Code for feature implementation on
the LangGraph Python library. After executing 3 of 11 planned treatments on
8 features (104 tiered acceptance tests), we report three findings: (1) a
pervasive ceiling effect where all treatments achieve 104/104 on acceptance
tests regardless of team configuration, (2) zero inter-agent communication
across all team treatments despite explicit encouragement, and (3) a 3.6x
wall-clock speedup from parallelism with no quality improvement. We conclude
that feature implementation on a shared codebase — like bug-fixing — is
structurally biased toward independent parallel work because each feature is
solvable without knowledge of other agents' changes.

---

## 1. Research Question

### Original Formulation

> Does Claude Code with Agent Teams outperform single-agent Claude Code on
> feature implementation tasks where the outcome is genuinely uncertain a priori?

The experiment tested three hypotheses:
- **Decomposition**: Does explicit task decomposition across agents improve
  quality when features share subsystems?
- **Collaboration**: Does inter-agent communication about shared code paths
  lead to better solutions than independent parallel work?
- **Specialization**: Does giving agents subsystem domain context improve
  outcomes?

### Prior Work

The predecessor experiment ([ate](https://github.com/kar-ganap/ate)) tested
bug-fixing in the Ruff Python linter (Rust codebase). Key findings: 8/8 solve
rate regardless of treatment, zero inter-agent communication, and a structural
argument that bug-fixing in single codebases is biased toward solo agents. See
[ate findings](https://github.com/kar-ganap/ate/blob/main/docs/findings.md).

This experiment aimed to break the ceiling by targeting feature implementation
— tasks with broader solution spaces and natural decomposition boundaries.

---

## 2. Method

### Target Codebase

LangGraph — Python graph-based agent orchestration library by LangChain.
Pinned at commit `b0f14649` (2026-02-20).

### Feature Portfolio

8 features across 4 subsystems, chosen so that pairs share code paths:

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

Correlation pairs: F1/F2 (both extend `_msgpack_default()`), F3/F4 (both fix
`EXT_CONSTRUCTOR`), F5/F6 (both fix channel creation pipeline), F7/F8 (both
fix `_messages.py`).

### Acceptance Tests

104 tiered tests (13 per feature):
- **T1 (Basic)**: 3 per feature — happy-path functionality
- **T2 (Edge Cases)**: 5 per feature — boundary conditions
- **T3 (Quality)**: 3 per feature — robustness, performance
- **T4 (Smoke/Integration)**: 2 per feature — end-to-end with checkpointer

Composite weights: T1=0.15, T2=0.35, T3=0.30, T4=0.20. All 104 tests fail
against pinned commit.

### Feature Selection Iteration

Original F5-F8 had 9-11/11 tests passing against the pinned commit — a ceiling
effect before the experiment even started. Replaced mid-Phase-1 with harder
state/streaming features. The T4 tier emerged during this replacement to test
real-world usage patterns (multi-node StateGraph + InMemorySaver).

### Treatment Matrix

11 treatments across 7 dimensions (decomposition strategy, prompt specificity,
delegate mode, team size, communication guidance, specialization). See
`docs/experiment-design.md` for the full matrix.

3 treatments executed:

| ID | Label | Team Size | Agent Teams | Key Dimension |
|----|-------|-----------|-------------|---------------|
| 0a | Control: Full Context | 1×8 | No | Solo baseline |
| 1 | Structured Team | 4×2 | Yes | Structured decomposition |
| 5 | Max Parallelism | 8×1 | Yes | Maximum parallelism |

### Execution Protocol

1. Scaffold session directories with `session_guide.md` and `metadata.json`
2. Start Claude Code in the pinned LangGraph directory
3. Paste spec-based opening prompt (no issue URLs, no solution hints)
4. Let agent(s) work; record session transcript
5. Extract patches, run acceptance tests, record scores
6. Revert LangGraph to clean state before next treatment

---

## 3. Results

### Acceptance Test Scores

| Treatment | T1–T4 Score | T5 (Post-hoc Robustness) | Wall Clock | Peer Messages |
|-----------|-------------|--------------------------|------------|---------------|
| 0a (solo) | 104/104 | 14/16 | 28 min | N/A |
| 1 (4-agent, 2 features each) | 104/104 | 14/16 | 12 min | 0 |
| 5 (8-agent, 1 feature each) | 104/104 | 14/16 | 8 min | 0 |

All three treatments achieved identical scores: 104/104 acceptance tests
passing, 14/16 on post-hoc robustness tests. The two failures are identical
across all treatments.

### Wall-Clock Speedup

| Treatment | Wall Clock | Speedup vs Solo |
|-----------|------------|-----------------|
| 0a (solo) | 28 min | 1.0x |
| 1 (4×2 team) | 12 min | 2.3x |
| 5 (8×1 team) | 8 min | 3.5x |

Speedup scales sub-linearly with agent count (8 agents → 3.5x, not 8x),
consistent with the ate experiment's finding that per-agent overhead
(context loading, tool setup) limits parallelism gains.

### Communication Analysis

Zero `SendMessage(recipient=<peer>)` calls across all team treatments.
Agents never initiated lateral messages to peers despite the `SendMessage`
primitive being available. All coordination flowed through the lead agent
(coordinator → agent dispatch).

### Wave 2 Decision

With CV = 0.0 across treatment mean composites, the Wave 2 decision gate
recommended against running specialized treatments. Zero variance means
specialization has nothing to improve.

---

## 4. Analysis

### Finding 1: Ceiling Effect

Claude Opus 4.6 achieves perfect scores (104/104) on all 8 features regardless
of treatment configuration. This is identical to the predecessor experiment's
8/8 bug-fix rate. The features were specifically designed to avoid this —
F5-F8 were replaced mid-development because the originals were too easy — yet
the ceiling persists.

The 14/16 post-hoc robustness score provides the only signal: 2 tests fail
consistently, suggesting they probe genuine edge cases beyond the model's
capability. But these failures are treatment-invariant — they don't
differentiate between team configurations.

### Finding 2: Zero Communication

Despite Agent Teams enabling `SendMessage` and the structured team treatment
(Treatment 1) pairing agents on correlated features (F1/F2 both modify
`_msgpack_default()`), no peer-to-peer communication occurred. This replicates
the predecessor experiment exactly.

The collaboration hypothesis required agents working on shared subsystems to
benefit from communicating about their changes. In practice, agents solve
features independently and never discover that coordination would help.

### Finding 3: Structural Bias

Feature implementation, like bug-fixing, is structurally biased toward
independent parallel work:

1. **Each feature is independently solvable**: An agent implementing F1 does
   not need to know about F2's changes to succeed on its acceptance tests.
2. **The patch-and-reset protocol eliminates coordination signal**: Each
   feature starts from a clean working tree, so agents modifying shared files
   never see each other's changes.
3. **No information asymmetry**: Every agent has full codebase access. There is
   nothing Agent A knows that Agent B cannot discover independently.

The cumulative scoring mode (Phase 5) was designed to address point 2 by having
agents work on the same tree without resets. However, the ceiling effect on
acceptance tests meant that even concurrent modifications to shared files
didn't produce conflicts — the model reliably writes compatible changes.

### Why This Differs from Architecture Design

The successor experiment ([ate-arch](https://github.com/kar-ganap/ate-arch))
succeeded by *constructing* information asymmetry: each agent interviews only
its assigned stakeholders, and cross-partition conflicts require cross-agent
information to resolve optimally. This structural condition — information that
Agent A has but Agent B cannot independently discover — is absent in
feature implementation.

---

## 5. Conclusions

1. **Agent Teams provides parallelism, not collaboration**, for feature
   implementation tasks within the model's capability frontier. The 3.5x
   wall-clock speedup is real and valuable; the quality improvement is zero.

2. **The ceiling effect is the model, not the experiment design**. We
   replaced easy features, added harder tiers (T3, T4), and designed
   subsystem-crossing correlation pairs. The model solves them all.

3. **Zero communication is a robust finding** across two experiments (ate and
   ate-features), 6 treatments, and two different task domains (Rust bug-fixing,
   Python feature implementation). Agents do not spontaneously communicate
   regardless of encouragement, team structure, or task design.

4. **Information asymmetry is necessary** for team coordination to improve
   quality. When every agent can independently solve its task with full
   codebase access, there is no reason to communicate.

---

## 6. Implications

### For the ate-series

This experiment eliminates a confound: the ate ceiling effect was not specific
to bug-fixing or Rust codebases. Feature implementation in Python shows the
same pattern. The research question must shift from "do teams outperform solo?"
to "under what structural conditions does the outcome become genuinely
uncertain?"

The successor experiment (ate-arch) addresses this by constructing information
asymmetry through stakeholder partitioning — the first design in the series
where agents hold non-overlapping information.

### For Practitioners

- Use Agent Teams for wall-clock speedup on tasks within the model's capability
  frontier. The parallelism is real (3.5x with 8 agents).
- Do not expect collaboration or communication between agents on feature
  implementation tasks. If you need coordination, you must structure the task
  to require it.
- The `SendMessage` primitive exists but agents never spontaneously use it.
  Communication requires structured protocols, not just available channels.

---

## 7. Data Summary

| Metric | Value |
|--------|-------|
| Features | 8 (across 4 subsystems) |
| Acceptance tests | 104 (13 per feature, 4 tiers) |
| Treatments designed | 11 (8 core + 3 specialized) |
| Treatments executed | 3 (0a, 1, 5) |
| Total runs | 3 |
| Agent model | Claude Opus 4.6 |
| Target codebase | LangGraph (Python) |
| Pinned commit | `b0f14649` |
| Pass rate (all treatments) | 104/104 (100%) |
| Post-hoc robustness | 14/16 (87.5%) |
| Peer-to-peer messages | 0 |
| Wall-clock range | 8–28 min |
| Max speedup | 3.5x (8 agents vs solo) |
| Wave 2 recommended | No (CV = 0.0) |
