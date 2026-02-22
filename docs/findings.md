# Findings: Agent Teams vs Solo on Feature Implementation

## Abstract

We compared Claude Code with Agent Teams (multi-agent) against single-agent
Claude Code on 8 LangGraph feature implementation tasks across 3 treatment
configurations: solo sequential (0a), 4-agent structured team (1), and 8-agent
max parallelism (5). Three key findings: (1) **ceiling effect**: all 3
treatments scored 104/104 on the 4-tier acceptance test suite and 14/16 on a
post-hoc T5 robustness tier — identical failures across all treatments; (2)
**zero inter-agent communication**: despite Agent Teams being active in
treatments 1 and 5, no peer-to-peer `SendMessage` events occurred — agents
coordinated implicitly by reading shared file state; (3) **time compression**:
wall-clock time compressed from 28 minutes (solo) to 12 minutes (4x2) to 8
minutes (8x1), a 3.6x speedup with no quality loss. These results replicate
the predecessor experiment's ceiling effect on a harder task domain (feature
implementation vs bug-fixing) and suggest that Agent Teams' primary value is
latency reduction, not quality improvement, for tasks within Claude Opus 4.6's
capability frontier.

---

## 1. Research Question

### Original Formulation

> Does Claude Code with Agent Teams outperform single-agent Claude Code on
> feature implementation tasks where the outcome is genuinely uncertain a priori?

The experiment varied 7 dimensions: decomposition (explicit/autonomous), prompt
specificity (detailed/vague), delegation mode (on/off), team size (1x8/4x2/8x1),
communication nudge (encourage/discourage/neutral), specialization
(vanilla/specialized), and execution mode (interactive). 11 treatments were
designed, with 8 core treatments in Wave 1 and 3 specialized variants in Wave 2
(contingent on Wave 1 variance).

### Refined Formulation

> For tasks within the capability frontier of a single Claude Opus 4.6 agent,
> does multi-agent collaboration add signal beyond parallelism?

The answer is **no** for this task portfolio. The refinement reflects two
observations: (a) all 8 features were independently solvable by a single agent
in under 30 minutes, placing them well within the capability frontier; (b) the
collaboration dimension (inter-agent communication) showed zero activity across
all team treatments, meaning there was no collaboration to measure.

---

## 2. Method

### 2.1 Codebase

- **Repository**: LangGraph (Python graph-based agent orchestration by LangChain)
- **Pin**: `b0f14649e0669a6399cb790d23672591a2a52884` (2026-02-20)
- **Build**: `pip install -e libs/langgraph && pip install -e libs/checkpoint`
- **Test**: Custom acceptance tests in `tests/acceptance/` (not LangGraph's own tests)

### 2.2 Treatments Executed

Of 11 designed treatments, 3 were executed before the ceiling effect made
further runs uninformative.

| ID | Label | Agent Teams | Team Size | Communication |
|----|-------|-------------|-----------|---------------|
| 0a | Control: Full Context | No | 1x8 (solo) | N/A |
| 1 | Structured Team | Yes | 4x2 | neutral |
| 5 | Max Parallelism | Yes | 8x1 | neutral |

All treatments used:
- **Model**: Claude Opus 4.6 (`claude-opus-4-6`)
- **Prompt**: Detailed spec-based (from `config/features.yaml`)
- **Scoring**: Cumulative mode (shared working tree, no resets)
- **Decomposition**: Explicit feature assignments

### 2.3 Feature Portfolio

8 features across 4 subsystems, designed with natural decomposition boundaries
and shared code paths to create collaboration opportunities.

| ID | Title | Subsystem | Shared Code |
|----|-------|-----------|-------------|
| F1 | Pandas DataFrame/Series serde | serializer | `_msgpack_default()` / `_msgpack_ext_hook()` |
| F2 | Pydantic v2 type round-trip | serializer | `_msgpack_default()` / `_msgpack_ext_hook()` |
| F3 | StrEnum preservation | serializer | `EXT_CONSTRUCTOR` mechanism |
| F4 | Nested Enum deserialization | serializer | `EXT_CONSTRUCTOR` mechanism |
| F5 | Reducer metadata ordering | state | `_is_field_binop()` in `graph/state.py` |
| F6 | default_factory wiring | state | `BinaryOperatorAggregate.__init__()` |
| F7 | Nested message detection | streaming | `_find_and_emit_messages()` |
| F8 | Input message dedup | streaming | `on_chain_start()` in `_messages.py` |

F1-F4 share `libs/checkpoint/langgraph/checkpoint/serde/jsonplus.py`.
F5-F6 share the channel creation pipeline (`state.py` -> `binop.py`).
F7-F8 share `libs/langgraph/langgraph/pregel/_messages.py`.

### 2.4 Acceptance Test Design

5-tier methodology creating a quality gradient:

| Tier | Name | Tests/Feature | Intent |
|------|------|---------------|--------|
| T1 | Basic | 3 | Happy path — any first attempt passes |
| T2 | Edge Cases | 5 | Boundary conditions — naive attempt may miss |
| T3 | Quality | 3 | Robustness, performance — first approach fails |
| T4 | Smoke | 2 | End-to-end multi-node graph workflows |
| T5 | Robustness | 2 | Spec-derived edge cases (added post-hoc) |

- **T1-T4**: 13 tests/feature x 8 features = **104 tests** (designed pre-experiment)
- **T5**: 2 tests/feature x 8 features = **16 tests** (added post-hoc to break ceiling)
- **Total**: 120 acceptance tests, all failing against pinned commit

Composite weights: T1=0.15, T2=0.35, T3=0.30, T4=0.20, T5=0.00 (T5 scored
separately, not contributing to composite).

### 2.5 Communication Verification Protocol

Same as predecessor experiment:
- Only `SendMessage(recipient=<peer>)` with routing metadata counts as
  inter-agent communication
- Messages to `team-lead` are coordination overhead, not peer collaboration
- `shutdown_request` messages are infrastructure, not communication

### 2.6 Scoring Protocol

**Cumulative mode**: Agents work on the same working tree without resets between
features. After all features are implemented, `git diff > cumulative.patch` is
saved. Scoring applies the cumulative patch to a clean tree, runs all acceptance
tests, and groups results by feature ID.

This protocol was chosen over isolated mode (patch-per-feature with resets)
because isolated mode eliminates the collaboration signal — agents working on
correlated features never see each other's changes.

---

## 3. Results

### 3.1 Primary Outcome: Ceiling Effect

All 3 treatments achieved perfect scores on the 4-tier acceptance suite.

| Treatment | T1 (24) | T2 (40) | T3 (24) | T4 (16) | Total (104) | Composite |
|-----------|---------|---------|---------|---------|-------------|-----------|
| 0a (solo) | 24/24 | 40/40 | 24/24 | 16/16 | **104/104** | **1.0000** |
| 1 (4x2 AT) | 24/24 | 40/40 | 24/24 | 16/16 | **104/104** | **1.0000** |
| 5 (8x1 AT) | 24/24 | 40/40 | 24/24 | 16/16 | **104/104** | **1.0000** |

CV = 0.0000. Wave 2 decision gate: **DO NOT recommend Wave 2**.

### 3.2 T5 Robustness Tier: Still No Differentiation

The T5 tier was added post-hoc to test whether spec-derived edge cases could
break the ceiling. Result: the ceiling breaks (not all tests pass), but there
is still zero differentiation between treatments.

| Feature | Test | 0a | 1 | 5 |
|---------|------|----|---|---|
| F3 | StrEnum as dict key | FAIL | FAIL | FAIL |
| F6 | Plain default (not factory) | FAIL | FAIL | FAIL |
| All other 14 tests | — | PASS | PASS | PASS |

**Totals**: All 3 treatments = **14/16 T5** (87.5%)

The 2 T5 failures are systematic spec gaps that all 3 implementations
independently missed:
1. **F3 `strenum_as_dict_key`**: All implementations handle StrEnum values but
   not StrEnum keys — dict keys are downcast to plain `str` during serialization.
2. **F6 `plain_default_value_with_reducer`**: All implementations fixed
   `default_factory` but not plain `default=` on dataclass fields with reducers.

### 3.3 Wall-Clock Time: The Only Differentiator

| Treatment | Structure | Wall Clock | Speedup | Impl Window | Setup |
|-----------|-----------|------------|---------|-------------|-------|
| 0a | 1 agent, sequential | 1672s (28m) | 1.0x | ~28m | — |
| 1 | 4 agents x 2 features | 721s (12m) | 2.3x | ~8m | ~4m |
| 5 | 8 agents x 1 feature | 468s (8m) | 3.6x | ~5.5m | ~1.2m |

- **0a**: Sequential implementation. F1 (Pandas) took 8 min; F5/F7/F8 took ~1 min each.
- **1**: 4 agents on shared tree. ~4 min setup (lead read tests, created team,
  spawned agents). ~8 min implementation. Agent 1 "stole" F6 from the queue.
  Agent 4 fixed Agent 2's import bug.
- **5**: 8 agents, 1 feature each. ~71s setup. All 8 Task calls issued in a
  single message. Agent spawn serialization: ~12s gap per agent despite parallel
  intent. Implementation window: 5m 28s (first spawn to last completion).

### 3.4 Communication: Zero Peer-to-Peer

| Treatment | Total Messages | Lead→Agent | Agent→Lead | Agent→Agent |
|-----------|----------------|------------|------------|-------------|
| 0a | 0 | — | — | — |
| 1 | 9 | 4 spawn + 1 fix | 4 completion reports | **0** |
| 5 | 16 | 8 shutdown | 8 completion reports | **0** |

No agent ever sent a `SendMessage` to a peer agent. All communication was
vertical (lead ↔ agent). This is identical to the predecessor experiment's
finding on bug-fixing tasks.

### 3.5 Emergent Implicit Coordination (Treatment 5)

Despite zero explicit messaging, agents on the shared working tree demonstrated
implicit coordination through file state:

- **F3** (StrEnum) noticed F2's Pydantic v2 handler changes already present in
  `jsonplus.py` and adapted. Created `_CLASS_REGISTRY`, `_register_class()`,
  `_resolve_class()` as shared infrastructure.
- **F4** (Nested Enum) discovered and reused F3's `_resolve_class()` and F2's
  `_find_pydantic_v2_class()`.
- **F8** explicitly checked "Let me also check if Agent 7 has already made
  changes" and adapted its implementation.

This implicit coordination through shared file state is a qualitatively new
finding not observed in the predecessor experiment (where bugs were fully
independent files). It suggests agents can coordinate without messaging when
they share a working tree — but this coordination doesn't improve quality
(scores are identical to the solo agent).

### 3.6 Adversarial Patch Quality Analysis

A manual adversarial review of the 3 cumulative patches (456, 504, and 653
lines respectively) found real architectural differences invisible to T1-T4:

| Aspect | 0a (Solo) | 1 (4x2 AT) | 5 (8x1 AT) |
|--------|-----------|-------------|-------------|
| Class registry | Separate (`_pydantic_v2_classes`, `_ext_classes`) | Unified `_CLASS_REGISTRY` with `_resolve_class()` | Unified with `_register_class()`/`_resolve_class()` |
| Pandas JSON hook | Missing `_msgpack_ext_hook_to_json` | Has it | Has it with RangeIndex/NaN/datetime64 |
| `dumps()`/`loads()` | Length-prefixed binary format | Hardcodes msgpack (loses type info) | Correct format-preserving |
| Pydantic handling | No generic model support | Generic models handled | Generic + `fields_set` preservation |
| Depth guard | None | None | Has recursion depth guard |
| Latent bug | Missing JSON conversion path | `dumps()` loses format info | References undefined `_find_pydantic_v2_class()` |

**Each implementation has at least one latent bug**, but the T1-T4 suite is
insufficient to detect them. The T5 suite catches 2 of these (the same 2 in
all treatments), but the deeper architectural differences remain invisible
to any automated test suite.

Despite these differences, **all 3 patches produce functionally equivalent
behavior** on all 120 tests. The architectural differences are latent —
they would matter in production (maintainability, edge cases beyond the spec)
but don't affect measured outcomes.

---

## 4. Analysis

### 4.1 Why the Ceiling Effect?

1. **Tasks within capability frontier**: Each feature is independently solvable
   by a single Claude Opus 4.6 agent in 1-8 minutes. The solution space, while
   broad, has clear spec-driven convergence points.

2. **Strong test suite drives convergence**: The 104-test acceptance suite
   provides enough signal for any agent to iteratively fix its implementation.
   Agents use test feedback as their primary guidance mechanism.

3. **No inter-feature dependency required**: While features share subsystems
   (e.g., F1-F4 all modify `jsonplus.py`), each feature's tests are
   independently satisfiable. No feature requires another feature to be
   implemented first.

4. **Cumulative mode doesn't help**: Despite sharing a working tree, agents
   don't need to coordinate — they can each make independent changes that
   happen to coexist. The Edit tool's atomic string-replacement mechanism
   avoids merge conflicts naturally.

### 4.2 Why Zero Communication?

The communication finding is now replicated across 2 experiments (5 treatments
total: 3 in ate, 2 in ate-features) on 2 different codebases:

- **No information advantage**: Each agent has the full codebase and its feature
  spec. There is nothing a peer agent knows that it doesn't already have access
  to.
- **No coordination need**: Features are independently satisfiable. No agent
  needs to wait for or adapt to another agent's work.
- **Communication overhead**: Sending a message takes a tool call that could be
  spent on implementation. The expected value of a message is zero when there's
  nothing to communicate.
- **Implicit coordination suffices**: When agents DO need to adapt (treatment 5
  on shared files), reading the file state is cheaper and more reliable than
  messaging. The file IS the shared state — no need to describe it in a message.

### 4.3 The Parallelism-Quality Decomposition

Agent Teams provide two potential benefits:
1. **Parallelism**: Multiple agents working simultaneously → faster wall-clock
2. **Collaboration**: Agents sharing information → better quality

Our results show that (1) is real and substantial (3.6x speedup) while (2) is
zero. This suggests a structural property:

> For tasks where P(single_agent_solves) ≈ 1.0, multi-agent collaboration
> cannot improve quality (there's no room above 100%). Parallelism can still
> improve latency.

The interesting regime for collaboration would be tasks where
P(single_agent_solves) << 1.0 — tasks beyond the capability frontier. Our
feature portfolio falls outside this regime.

### 4.4 Comparison with Predecessor Experiment

| Dimension | ate (Bug-Fixing) | ate-features (Feature Implementation) |
|-----------|------------------|--------------------------------------|
| Codebase | Ruff (Python linter) | LangGraph (agent framework) |
| Task type | Bug fixes (8 bugs) | Feature implementation (8 features) |
| Treatments run | 3 (0b, 2a, 5) | 3 (0a, 1, 5) |
| Score | 8/8 all treatments | 104/104 all treatments |
| Communication | Zero peer-to-peer | Zero peer-to-peer |
| Time compression | Not measured | 3.6x (solo → 8x1) |
| Implicit coordination | None (independent files) | Yes (shared file state) |
| T5 ceiling break | N/A | 14/16 (same failures all treatments) |

The ceiling effect is now confirmed across 2 task domains, 2 codebases, and 6
treatment configurations. The zero-communication finding is confirmed across 5
team treatments.

### 4.5 Task Difficulty Assessment

Per-feature implementation time (treatment 0a, solo) reveals a difficulty
gradient:

| Difficulty | Features | Time | Characteristics |
|------------|----------|------|-----------------|
| Hard | F1 (Pandas), F6 (default_factory) | 4-8 min | Multi-step debugging, false starts |
| Medium | F2 (Pydantic), F3 (StrEnum) | 3 min | Straightforward but multi-file |
| Easy | F4, F5, F7, F8 | 1-2 min | Near-trivial, single-function changes |

Despite this gradient, all features score 13/13 (T1-T4) regardless of
difficulty. The "hard" features take longer but still achieve perfect scores.
Task difficulty affects latency, not quality — the same pattern as the
predecessor experiment.

---

## 5. Conclusions

### 5.1 Answer to the Core Question

> Does Claude Code with Agent Teams outperform single-agent Claude Code on
> feature implementation tasks?

**No** — not on quality. All 3 treatments produce functionally equivalent
implementations that pass all 104 acceptance tests and fail the same 2 of 16
T5 robustness tests.

**Yes** — on speed. Agent Teams compress wall-clock time by 3.6x (8x1) or
2.3x (4x2) with no quality loss.

### 5.2 Secondary Findings

1. **Zero inter-agent communication is structural, not incidental.** Replicated
   across 2 experiments, 5 team treatments, 2 codebases. Agents don't message
   peers because there is no information advantage to sharing.

2. **Implicit coordination through shared file state works.** Treatment 5
   showed agents reading and adapting to each other's changes without messaging.
   This is functionally equivalent to explicit coordination for these tasks.

3. **Adversarial review reveals quality differences invisible to tests.** Each
   treatment produced architecturally distinct implementations with unique
   latent bugs. But these differences don't affect any measured outcome —
   all implementations are functionally equivalent within the test suite's
   coverage.

4. **The ceiling effect is robust to test suite expansion.** Adding a 5th
   tier of spec-derived robustness tests breaks the ceiling (14/16 instead of
   16/16) but does not differentiate between treatments — all 3 fail the same
   2 tests.

5. **Spawn serialization limits parallelism.** In treatment 5, the 8 Task
   calls were issued in a single message (parallel intent), but agents spawned
   sequentially with ~12s gaps. True parallel execution would further compress
   wall-clock time.

### 5.3 What Would Change This Answer?

- **Harder tasks**: Features beyond the capability frontier of a single agent
  (P(solve) < 0.5) would create room for collaboration to add value.
- **Multi-round iteration**: Tasks requiring back-and-forth refinement where
  one agent's output is another's input.
- **Adversarial evaluation**: If scoring included code review metrics
  (maintainability, no latent bugs, test coverage), the architectural
  differences might produce score variance.
- **Shared mutable state**: Tasks where agents must coordinate writes to the
  same data structure (not just the same file) would force explicit
  communication.
- **Non-deterministic environments**: Tasks with external dependencies (APIs,
  databases) where coordination reduces redundant work.

---

## 6. Implications

### For Practitioners

- **Use Agent Teams for speed, not quality.** If a single agent can solve the
  task, Agent Teams will solve it faster (up to ~4x) but not better.
- **Don't invest in communication nudges for solvable tasks.** Encouraging or
  discouraging communication has zero effect when agents have no information
  advantage to share.
- **8x1 > 4x2 for independent tasks.** When features don't require inter-agent
  coordination, maximum parallelism (one agent per feature) outperforms
  structured teams with shared assignments.

### For Future Research

- **Identify tasks beyond the frontier.** The interesting regime for
  collaboration is P(single_agent_solves) << 1.0. Candidates: multi-service
  architecture changes, security audits requiring cross-codebase reasoning,
  large-scale refactoring with dependency chains.
- **Measure implicit coordination quality.** Treatment 5 showed agents reading
  shared file state. Is this coordination optimal? Do agents make worse
  decisions when adapting to concurrent changes vs. building on sequential ones?
- **Test with communication-dependent tasks.** Design tasks where agent A
  physically cannot proceed without information from agent B (e.g., A
  implements the API, B implements the client, neither has the other's spec).

---

## 7. Data Summary

### Wave 1 Cumulative Round (LangGraph, 3 treatments x 8 features)

| Metric | 0a (Solo) | 1 (4x2 AT) | 5 (8x1 AT) |
|--------|-----------|-------------|-------------|
| Wall clock | 1672s (28m) | 721s (12m) | 468s (8m) |
| T1-T4 score | 104/104 | 104/104 | 104/104 |
| T5 score | 14/16 | 14/16 | 14/16 |
| Composite (T1-T4) | 1.0000 | 1.0000 | 1.0000 |
| Peer-to-peer messages | 0 | 0 | 0 |
| Total tool calls | — | — | 263 |
| Interventions | 0 | 0 | 4 ("keep going") |
| Patch size (lines) | 456 | 504 | 653 |

### Per-Feature T5 Results (all 3 treatments identical)

| Feature | T5 Test 1 | T5 Test 2 |
|---------|-----------|-----------|
| F1 Pandas serde | categorical dtype: PASS | series multiindex: PASS |
| F2 Pydantic round-trip | multiple models: PASS | aliased fields: PASS |
| F3 StrEnum | **dict key: FAIL** | overlapping values: PASS |
| F4 Nested Enum | 4-level nesting: PASS | pydantic model list: PASS |
| F5 Reducer metadata | 4 metadata items: PASS | int reducer: PASS |
| F6 Default factory | nested factory: PASS | **plain default: FAIL** |
| F7 Message emission | dict-of-dicts: PASS | mixed msg types: PASS |
| F8 Message dedup | flat+nested: PASS | 10 nested msgs: PASS |

### Tooling

- **Model**: Claude Opus 4.6 (`claude-opus-4-6`)
- **Claude Code**: Interactive mode with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- **Scoring**: `ate-features score collect <tid> --mode cumulative`
- **Infrastructure**: macOS, Python 3.11, uv, LangGraph installed as editable
- **Total experiment time**: ~48 min across 3 treatments (not counting
  infrastructure development)

---

## Appendix A: Implicit Coordination Examples (Treatment 5)

### Example 1: F3 Builds Shared Infrastructure

Agent 3 (F3: StrEnum) was the longest-running agent (5m 6s, 42 tool calls).
While implementing StrEnum preservation, it noticed that Agent 2 (F2: Pydantic)
had already modified the `_msgpack_ext_hook()` function. Rather than conflicting
with those changes, Agent 3 created a generalized `_CLASS_REGISTRY` with
`_register_class()` and `_resolve_class()` helper functions that worked for
both StrEnum and Pydantic types. This shared infrastructure was then reused by
Agent 4 (F4: Nested Enum).

### Example 2: F4 Reuses F3's and F2's Code

Agent 4 (F4: Nested Enum) started after Agents 2 and 3 had already modified
`jsonplus.py`. It discovered `_resolve_class()` (from F3) and
`_find_pydantic_v2_class()` (from F2) and reused both in its recursive enum
reconstruction logic. No messaging was needed — the code was self-documenting.

### Example 3: F8 Checks F7's Changes

Agent 8 (F8: Input message dedup) explicitly read the file to check "if Agent 7
has already made changes" to `_messages.py`. Finding that Agent 7 had added
recursive traversal for message emission, Agent 8 adapted its dedup logic to
use the same traversal pattern. Again, no messaging — file state was sufficient.

## Appendix B: Communication Transcript Evidence

### Treatment 1 — All 9 Messages

```
Lead → Agent 1: spawn (F1, F5)
Lead → Agent 2: spawn (F2, F6)
Lead → Agent 3: spawn (F3, F7)
Lead → Agent 4: spawn (F4, F8)
Agent 1 → Lead: completion report
Agent 2 → Lead: completion report
Agent 3 → Lead: completion report
Agent 4 → Lead: completion report (+ import fix for Agent 2's bug)
Lead → Agent 2: import fix notification
```

Zero peer-to-peer messages. All communication is vertical (lead ↔ agent).

### Treatment 5 — All 16 Messages

```
Agent 1-8 → Lead: 8 completion reports (one each)
Lead → Agent 1-8: 8 shutdown_request messages
```

Zero peer-to-peer messages. Agents never communicated with each other despite
working on the same files concurrently.

## Appendix C: Remaining Treatments Not Executed

8 of 11 designed treatments were not executed due to the ceiling effect:

| ID | Label | Why Not Run |
|----|-------|-------------|
| 0b | Control: Swim Lanes | Per-feature solo — expected to match 0a |
| 2a | Autonomous + Encourage | Ceiling effect makes communication nudge irrelevant |
| 2b | Autonomous + Discourage | Paired with 2a — both moot |
| 3 | Invest in Prompts | Autonomous + detailed — no quality gap to close |
| 4 | Player-Coach | Autonomous + vague + no delegation — ceiling makes it irrelevant |
| 6 | Specialized Swim Lanes | Wave 2 — gated on Wave 1 variance (CV=0) |
| 7 | Specialized Structured Team | Wave 2 — gated on Wave 1 variance (CV=0) |
| 8 | Specialized + Encourage | Wave 2 — gated on Wave 1 variance (CV=0) |

The Wave 2 decision gate (CV > 0.10) was not met. Specialization, communication
nudges, and prompt specificity dimensions remain untested — but the ceiling
effect on the remaining dimensions makes it unlikely they would produce
differentiation on this task portfolio.
