# Runbook: Treatment 5 — Max Parallelism

**Treatment**: 5 (Max Parallelism)
**Description**: 1 interactive Claude Code session with Agent Teams. Team size: 8x1. Delegate mode ON. Detailed prompts with full specs. Communication: neutral.
**Expected Duration**: 2-6 hours
**Agent Teams**: ON (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude`)

| Dimension | Value |
|-----------|-------|
| Decomposition | **Explicit** |
| Prompt specificity | detailed |
| Delegate mode | True |
| Team size | 8x1 |
| Communication | neutral |
| Specialization | vanilla |

---

## 1. Pre-Session Setup

Run these commands from the ate-features repo root.

### 1.1 Run preflight checks

```bash
ate-features exec preflight
```

- [ ] Preflight passed (LangGraph at correct pin, clean working tree)
- [ ] CC version recorded: `___________`

### 1.2 Scaffold session directories

```bash
ate-features exec scaffold 5
```

- [ ] `data/transcripts/treatment-5/` created
- [ ] `session_guide.md`, `metadata.json`, `notes.md` present

### 1.3 Create patches directory

```bash
mkdir -p data/patches/treatment-5
```

- [ ] `data/patches/treatment-5/` exists

### 1.4 Verify LangGraph is clean

```bash
git -C data/langgraph status
git -C data/langgraph diff --stat
```

- [ ] Working tree clean (no modifications, no untracked files)

### 1.5 Record session start

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
```

- [ ] Start time: `___________`

---

## 2. Opening Prompt

Launch Claude Code:

```bash
cd data/langgraph
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude
```

- [ ] Confirmed: launched with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude`

### 2.1 Paste the opening prompt

Copy and paste the **entire block below** as a single message:

---

````
# Feature Implementation Task

Implement the following features in the pinned LangGraph repository. For each feature: explore the codebase, implement the fix, run the acceptance tests, and create a patch file.

## F1: Pandas DataFrame/Series msgpack serialization
**Subsystem:** serializer
**Spec:** Add first-class pandas DataFrame and Series serialization to
JsonPlusSerializer in libs/checkpoint/. Currently these types
only work with pickle_fallback=True. Implement custom msgpack
ext type handlers in _msgpack_default() and _msgpack_ext_hook()
that serialize/deserialize DataFrame and Series without relying
on pickle. Must preserve dtypes, index, column names, and
multi-index structures.

**Tests:** `tests/acceptance/test_f1_*.py`

## F2: Generic Pydantic v2 type round-trip in checkpoint serde
**Subsystem:** serializer
**Spec:** Extend JsonPlusSerializer to support round-tripping arbitrary
Pydantic v2 BaseModel subclasses through checkpoint
serialization/deserialization. Currently only specific known
types are handled. The serializer should detect BaseModel
instances, serialize them via model_dump(mode="json"), and
reconstruct them using model_validate() on deserialization,
preserving the original type information.

**Tests:** `tests/acceptance/test_f2_*.py`

## F3: StrEnum preservation in checkpoint serde
**Subsystem:** serializer
**Spec:** Fix JsonPlusSerializer so that Python StrEnum values survive
a serialize/deserialize round-trip. Currently StrEnum values
are downcast to plain strings during serialization. The fix
should preserve the enum type through the EXT_CONSTRUCTOR
mechanism so that isinstance() checks and .name/.value
attributes work correctly after deserialization.

**Tests:** `tests/acceptance/test_f3_*.py`

## F4: Nested Enum deserialization fix
**Subsystem:** serializer
**Spec:** Fix deserialization of Enum values that are nested inside
containers (lists, dicts, dataclass fields) in
JsonPlusSerializer. Currently top-level Enum values round-trip
correctly, but when an Enum is a field inside a dataclass or
nested in a dict/list, it deserializes as a plain string/int.
The fix should recursively apply enum reconstruction through
the EXT_CONSTRUCTOR mechanism.

**Tests:** `tests/acceptance/test_f4_*.py`

## F5: Reducer metadata ordering dependency
**Subsystem:** state
**Spec:** Fix _is_field_binop() in graph/state.py so that Annotated type
reducers work regardless of metadata ordering. Currently the
function only checks meta[-1] for a callable reducer. When the
reducer is not the last Annotated metadata item (e.g.,
Annotated[list, operator.add, "description"]), it is silently
dropped and the field becomes LastValue instead of
BinaryOperatorAggregate. The fix should scan ALL metadata items
for a callable with a 2-parameter signature.

**Tests:** `tests/acceptance/test_f5_*.py`

## F6: BinaryOperatorAggregate ignores default_factory
**Subsystem:** state
**Spec:** Fix BinaryOperatorAggregate.__init__() in channels/binop.py so
that dataclass field default_factory values are used as the
channel's initial value. Currently __init__() always calls
typ() (e.g., list() = []), ignoring any default or
default_factory on the dataclass field. The fix should wire
dataclass defaults through the channel construction pipeline
so that initial state matches the dataclass definition.

**Tests:** `tests/acceptance/test_f6_*.py`

## F7: Nested message detection in stream_mode=messages
**Subsystem:** streaming
**Spec:** Fix _find_and_emit_messages() in pregel/_messages.py so that
messages nested inside Pydantic models, dataclasses, or
dict-within-state objects are found and emitted during
stream_mode="messages" streaming. Currently the function only
scans two levels: top-level state field values, then one level
of Sequence. Messages in nested objects are silently dropped.
The fix should recursively traverse nested structures.

**Tests:** `tests/acceptance/test_f7_*.py`

## F8: Input message dedup for nested structures
**Subsystem:** streaming
**Spec:** Fix on_chain_start() in pregel/_messages.py so that messages
nested in Pydantic models, dataclasses, or dicts within the
input state are added to the `seen` set for deduplication.
Currently only top-level and one-level-deep sequence messages
are tracked. When a node receives nested messages in input and
returns them flattened in output, they are incorrectly emitted
as "new" duplicates. The fix should recursively scan input
structures for message IDs.

**Tests:** `tests/acceptance/test_f8_*.py`

## Feature Assignments

- **Agent 1:** F1
- **Agent 2:** F2
- **Agent 3:** F3
- **Agent 4:** F4
- **Agent 5:** F5
- **Agent 6:** F6
- **Agent 7:** F7
- **Agent 8:** F8

## Patch Instructions

**CRITICAL:** After implementing **each** feature, save your patch by running `git diff > data/patches/treatment-5/<FN>.patch` (replacing `<FN>` with the feature ID, e.g., `F1`, `F2`, etc.), then reset with `git checkout . && git clean -fd` before moving to the next feature. If you cannot produce a fix for a feature, save an empty patch and move on.


Remember: save each patch with `git diff > data/patches/treatment-5/<FN>.patch` and reset with `git checkout . && git clean -fd` before starting the next feature. Start with F1.
````

---

- [ ] Pasted the full opening prompt
- [ ] Agent acknowledged the features and began working

---

## 3. Monitoring Guidelines

### 3.1 Cadence

Glance at the session every **2-3 minutes**. You do not need to watch continuously, but check progress regularly to catch stalls early.

### 3.2 What to watch for

| Signal | Action |
|--------|--------|
| Agent making steady progress (reading, coding, testing) | No action needed |
| Agent going in circles (re-reading same files, same approach) | Note time; prepare to nudge at threshold |
| Agent asks a clarifying question | Answer promptly |
| Agent forgot to save patch before next feature | Intervene immediately (see nudge examples) |
| Agent forgot to reset (`git checkout . && git clean -fd`) | Intervene immediately |
| Agent stuck on unrelated build/test errors | Nudge toward a different approach |
| No output for >2 minutes | Check if waiting for input |
| Lead forming team and delegating | Note the confirmation |

### 3.3 Escape time thresholds

Wall-clock time limit per feature: **~45 minutes**. If the agent has not produced a patch (or acknowledged it cannot) within the threshold, intervene.

### 3.4 Nudge examples

Use these as templates. Adapt to the situation.

**If stuck on a feature past the threshold:**
```
Let's move on. Save whatever patch you have (even if incomplete) with:
git diff > data/patches/treatment-5/<feature-id>.patch
Then reset with: git checkout . && git clean -fd
And proceed to the next feature.
```

**If agent forgot to save a patch:**
```
Before moving on, please save the patch for the feature you just finished:
git diff > data/patches/treatment-5/<feature-id>.patch
Then reset: git checkout . && git clean -fd
```

**If agent forgot to reset LangGraph:**
```
Please reset the LangGraph source before starting the next feature:
git checkout . && git clean -fd
Verify with: git diff --stat
```

**If agent is going in circles:**
```
You seem to be revisiting the same approach. Can you try a different angle?
If you're stuck, it's OK to save what you have and move on to the next feature.
```

**If a specific agent is stuck (team treatments):**
```
Agent [N] seems stuck on [feature]. Can it try a different approach?
```

### 3.5 Per-feature tracking

Use this table to track progress in real time (fill in as you go):

| # | Feature | Subsystem | Started | Finished | Patch Saved | Reset Done | Notes |
|---|---------|-----------|---------|----------|-------------|------------|-------|
| 1 | F1 | serializer | ___:___ | ___:___ | [ ] | [ ] | |
| 2 | F2 | serializer | ___:___ | ___:___ | [ ] | [ ] | |
| 3 | F3 | serializer | ___:___ | ___:___ | [ ] | [ ] | |
| 4 | F4 | serializer | ___:___ | ___:___ | [ ] | [ ] | |
| 5 | F5 | state | ___:___ | ___:___ | [ ] | [ ] | |
| 6 | F6 | state | ___:___ | ___:___ | [ ] | [ ] | |
| 7 | F7 | streaming | ___:___ | ___:___ | [ ] | [ ] | |
| 8 | F8 | streaming | ___:___ | ___:___ | [ ] | [ ] | |


---

## 4. After-Session Steps

### 4.1 Record end timestamp

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
```

- [ ] End time: `___________`

### 4.2 Check for unsaved work

```bash
git -C data/langgraph diff --stat
```

If there are uncommitted changes, save them as a remaining patch:

```bash
git -C data/langgraph diff > data/patches/treatment-5/remaining.patch
git -C data/langgraph checkout . && git -C data/langgraph clean -fd
```

### 4.3 Verify patches

```bash
ate-features exec verify-patches 5
ls -la data/patches/treatment-5/
```

Expected: up to 8 files (`F1.patch` through `F8.patch`). Some may be empty (0 bytes) if the agent could not implement that feature.

- [ ] Verified patch files present
- [ ] Non-empty patches: `___________`

### 4.4 Verify LangGraph is clean

```bash
git -C data/langgraph status
```

- [ ] Working tree clean

### 4.5 Update metadata.json

Update `data/transcripts/treatment-5/metadata.json` with actual timing and outcome data:

```json
{
  "started_at": "2026-XX-XXTXX:XX:XXZ",
  "completed_at": "2026-XX-XXTXX:XX:XXZ",
  "wall_clock_seconds": null,
  "session_id": null,
  "model": "claude-opus-4-6",
  "notes": null
}
```

- [ ] metadata.json updated

### 4.6 Write session notes

Record observations in `data/transcripts/treatment-5/notes.md`. Use this format:

```markdown
# Notes: Treatment 5 — Max Parallelism

## Assignment Confirmation
- Agent 1: F1 (confirmed by lead)
- Agent 2: F2 (confirmed by lead)
- Agent 3: F3 (confirmed by lead)
- Agent 4: F4 (confirmed by lead)
- Agent 5: F5 (confirmed by lead)
- Agent 6: F6 (confirmed by lead)
- Agent 7: F7 (confirmed by lead)
- Agent 8: F8 (confirmed by lead)

## Timeline
- HH:MM Session started
- HH:MM Agent began Feature F1
- ...

## Per-Feature Outcomes
| Feature | Outcome | Time |
|---------|---------|------|
| F1 | fix/partial/stuck | ~X min |
| ... | ... | ... |

## Interventions
- (timestamp): (what you said)

## Inter-Agent Communication
- (any SendMessage events between agents)

## Observations
- Notable behavior: (anything interesting)
- Approximate tool calls: ~N
```

- [ ] Notes written

### 4.7 Save session transcript

Claude Code stores session transcripts as JSONL files at:

```
~/.claude/projects/-Users-kartikganapathi-Documents-Personal-random_projects-others-projects-checkout-ate-features/
```

Look for the most recent `.jsonl` file matching the session time.

- [ ] Session transcript located or session ID noted: `___________`

---

## 5. Final Checklist

- [ ] Agent Teams env var was set
- [ ] All 8 features were attempted
- [ ] Patches saved for each feature (even if empty)
- [ ] LangGraph was reset between features
- [ ] LangGraph is clean after final feature
- [ ] Per-feature timing recorded in monitoring table
- [ ] metadata.json updated with actual data
- [ ] Notes written with observations
- [ ] Session transcript saved
- [ ] Total wall-clock time: `___________`

---

## Appendix: Feature Quick Reference

| # | ID | Title | Subsystem |
|---|----|-------|-----------|
| 1 | F1 | Pandas DataFrame/Series msgpack serialization | serializer |
| 2 | F2 | Generic Pydantic v2 type round-trip in checkpoint serde | serializer |
| 3 | F3 | StrEnum preservation in checkpoint serde | serializer |
| 4 | F4 | Nested Enum deserialization fix | serializer |
| 5 | F5 | Reducer metadata ordering dependency | state |
| 6 | F6 | BinaryOperatorAggregate ignores default_factory | state |
| 7 | F7 | Nested message detection in stream_mode=messages | streaming |
| 8 | F8 | Input message dedup for nested structures | streaming |
