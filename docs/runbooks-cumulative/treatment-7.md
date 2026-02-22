# Runbook: Treatment 7 — Specialized Structured Team

**Treatment**: 7 (Specialized Structured Team)
**Description**: 1 interactive Claude Code session with Agent Teams. Team size: 4x2. Delegate mode ON. Detailed prompts with full specs. Communication: neutral.
**Expected Duration**: 2-6 hours
**Agent Teams**: ON (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude`)

| Dimension | Value |
|-----------|-------|
| Decomposition | **Explicit** |
| Prompt specificity | detailed |
| Delegate mode | True |
| Team size | 4x2 |
| Communication | neutral |
| Specialization | specialized |

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
ate-features exec scaffold 7
```

- [ ] `data/transcripts/treatment-7/` created
- [ ] `session_guide.md`, `metadata.json`, `notes.md` present

### 1.3 Create patches directory

```bash
mkdir -p data/patches/treatment-7
```

- [ ] `data/patches/treatment-7/` exists

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
# Domain Context

# Agent 1 Specialization: Serializer + State

## Serializer Subsystem

### Architecture
The checkpoint serializer lives in `libs/checkpoint/langgraph/checkpoint/serde/`.
The primary class is `JsonPlusSerializer` in `jsonplus.py`.

### Key Files
- `jsonplus.py` — Core serializer with msgpack extension handling
- `base.py` — `SerializerProtocol` (defines `dumps_typed`/`loads_typed`)
- `types.py` — `SendProtocol`, `ChannelProtocol` type definitions

### Extension Mechanism
Custom types are handled via msgpack ext codes defined at module level:
- `EXT_CONSTRUCTOR_SINGLE_ARG = 0` — constructor with 1 arg
- `EXT_CONSTRUCTOR_POS_ARGS = 1` — constructor with *args
- `EXT_CONSTRUCTOR_KW_ARGS = 2` — constructor with **kwargs
- `EXT_METHOD_SINGLE_ARG = 3` — class method with 1 arg
- `EXT_PYDANTIC_V1 = 4`, `EXT_PYDANTIC_V2 = 5`, `EXT_NUMPY_ARRAY = 6`

### Adding New Types
`_msgpack_default(obj)` uses cascading `isinstance`/`hasattr` checks. Each
handler wraps data in a tuple `(module_path, class_name, serialized_data)`
and packs it with `ormsgpack.Ext(code, encoded_bytes)`.

`_msgpack_ext_hook(code, data)` reverses the process: unpacks the tuple,
imports the class via `importlib.import_module`, and reconstructs the object.

### Passthrough Options
The serializer uses `OPT_PASSTHROUGH_DATACLASS | OPT_PASSTHROUGH_DATETIME |
OPT_PASSTHROUGH_ENUM | OPT_PASSTHROUGH_UUID` to route these types through
`_msgpack_default()` instead of ormsgpack's built-in handling.

## State Subsystem

### Architecture
State management lives in `libs/langgraph/langgraph/graph/state.py` and
the `channels/` package.

### Key Files
- `graph/state.py` — Channel selection from type annotations
- `channels/binop.py` — `BinaryOperatorAggregate` (reducer channels)
- `channels/last_value.py` — `LastValue` (default non-reducer channel)
- `_internal/_fields.py` — `get_field_default()`, field introspection utilities

### Channel Creation Pipeline
1. `_get_channels(schema)` extracts type hints via `get_type_hints(schema, include_extras=True)`
2. For each field, `_get_channel(name, typ)` decides the channel type:
   - `_is_field_managed_value()` → managed value
   - `_is_field_channel()` → explicit channel annotation
   - `_is_field_binop()` → `BinaryOperatorAggregate` (has a reducer)
   - Default → `LastValue`
3. `_is_field_binop(typ)` inspects `Annotated` metadata for a callable with
   a 2-parameter signature to use as the binary reduction operator

### Cross-subsystem Boundaries
- Serializer checkpoints state values that include channel contents
- `BinaryOperatorAggregate` stores accumulated values that the serializer
  must handle (lists, dicts, custom types)
- Agent 2 also works on state channels — the channel construction pipeline
  is shared between your work and theirs


# Agent 2 Specialization: Serializer + State

## Serializer Subsystem

### Architecture
The checkpoint serializer lives in `libs/checkpoint/langgraph/checkpoint/serde/`.
The primary class is `JsonPlusSerializer` in `jsonplus.py`.

### Key Files
- `jsonplus.py` — Core serializer with msgpack extension handling
- `base.py` — `SerializerProtocol` (defines `dumps_typed`/`loads_typed`)
- `types.py` — `SendProtocol`, `ChannelProtocol` type definitions

### Pydantic Handling
Pydantic models have dedicated ext codes:
- `EXT_PYDANTIC_V1 = 4` — Pydantic V1 `BaseModel` instances
- `EXT_PYDANTIC_V2 = 5` — Pydantic V2 `BaseModel` instances

In `_msgpack_default(obj)`, a Pydantic V2 model is detected via
`hasattr(obj, "model_dump")` and serialized as
`(module, class_name, model_dump_dict)`. The ext hook reconstructs via
`cls(**data)`.

### Round-trip Pattern
`dumps_typed(obj)` → ormsgpack with passthrough options → `_msgpack_default`
for unhandled types → ext bytes.
`loads_typed((type_tag, bytes))` → ormsgpack unpack → `_msgpack_ext_hook`
for ext codes → reconstructed object.

The `type_tag` is a string (`"msgpack"` or `"json"`) that selects the codec.

## State Subsystem

### Architecture
State management lives in `libs/langgraph/langgraph/graph/state.py` and
the `channels/` package.

### Key Files
- `graph/state.py` — Channel selection from type annotations
- `channels/binop.py` — `BinaryOperatorAggregate` (reducer channels)
- `channels/last_value.py` — `LastValue` (default non-reducer channel)
- `_internal/_fields.py` — `get_field_default()`, field introspection utilities

### BinaryOperatorAggregate Internals
`__init__(self, typ, operator, default=...)` stores the reduction function
and initializes `self.value = default if default is not EMPTY else typ()`.

`update(values)` folds: `self.value = reduce(operator, values, self.value)`.

`get()` returns the current accumulated value.

The `typ()` call for default initialization means the type must be
callable with zero arguments (e.g., `list`, `dict`, `int`). Custom types
that require constructor arguments need an explicit `default` parameter.

### Cross-subsystem Boundaries
- Serializer checkpoints state values that include channel contents
- `BinaryOperatorAggregate` stores accumulated values that the serializer
  must handle (lists, dicts, custom types)
- Agent 1 also works on state channels — the channel construction pipeline
  is shared between your work and theirs


# Agent 3 Specialization: Serializer + Streaming

## Serializer Subsystem

### Architecture
The checkpoint serializer lives in `libs/checkpoint/langgraph/checkpoint/serde/`.
The primary class is `JsonPlusSerializer` in `jsonplus.py`.

### Key Files
- `jsonplus.py` — Core serializer with msgpack extension handling
- `base.py` — `SerializerProtocol` (defines `dumps_typed`/`loads_typed`)
- `types.py` — `SendProtocol`, `ChannelProtocol` type definitions

### Enum Handling
Standard `Enum` and `StrEnum` instances are routed through `_msgpack_default()`
via the `OPT_PASSTHROUGH_ENUM` option. They are serialized with
`EXT_CONSTRUCTOR_SINGLE_ARG = 0`: the ext payload is
`(module, class_name, member_value)`.

Reconstruction in `_msgpack_ext_hook()` imports the class and calls
`cls(value)` to get the enum member back.

The passthrough option is critical — without it, ormsgpack serializes enums
as their raw value (string/int) and type identity is lost on deserialization.

### Passthrough Options
The serializer uses `OPT_PASSTHROUGH_DATACLASS | OPT_PASSTHROUGH_DATETIME |
OPT_PASSTHROUGH_ENUM | OPT_PASSTHROUGH_UUID` to route these types through
`_msgpack_default()` instead of ormsgpack's built-in handling.

## Streaming Subsystem

### Architecture
Stream message handling lives in
`libs/langgraph/langgraph/pregel/_messages.py`.

### Key Files
- `pregel/_messages.py` — `StreamMessagesHandler` callback handler
- `pregel/loop.py` — Pregel execution loop (invokes handlers)
- `types.py` — `StreamMode` enum and message type definitions

### Message Emission Pipeline
`StreamMessagesHandler` implements LangChain's `BaseCallbackHandler`.

`_find_and_emit_messages(values)` is the core scanning method:
1. Iterates over values in a state dict
2. For each value that is a sequence (list/tuple), checks items
3. Items that are `BaseMessage` instances get emitted via the `stream` callback
4. Scanning depth is limited — only top-level state keys and their
   immediate sequence contents are checked

The `on_chain_end(outputs)` callback triggers `_find_and_emit_messages`
after each node completes, extracting messages from the node's output state.

### Cross-subsystem Boundaries
- Serialized checkpoints include streaming state (which messages have been
  emitted) for resume scenarios
- Agent 4 also works on streaming — message deduplication depends on the
  emission scanning logic you work on


# Agent 4 Specialization: Serializer + Streaming

## Serializer Subsystem

### Architecture
The checkpoint serializer lives in `libs/checkpoint/langgraph/checkpoint/serde/`.
The primary class is `JsonPlusSerializer` in `jsonplus.py`.

### Key Files
- `jsonplus.py` — Core serializer with msgpack extension handling
- `base.py` — `SerializerProtocol` (defines `dumps_typed`/`loads_typed`)
- `types.py` — `SendProtocol`, `ChannelProtocol` type definitions

### Nested Type Reconstruction
`_msgpack_ext_hook(code, data)` handles reconstruction for all ext codes:
- `EXT_CONSTRUCTOR_SINGLE_ARG = 0` — `cls(arg)`
- `EXT_CONSTRUCTOR_POS_ARGS = 1` — `cls(*args)`
- `EXT_CONSTRUCTOR_KW_ARGS = 2` — `cls(**kwargs)`
- `EXT_METHOD_SINGLE_ARG = 3` — `getattr(cls, method)(arg)`

When types are nested (e.g., an Enum inside a dataclass inside a list),
ormsgpack processes ext codes bottom-up. Inner objects are deserialized
first, then the containing structure's ext hook receives already-
reconstructed inner values.

### Extension Mechanism
`_msgpack_default(obj)` uses cascading `isinstance`/`hasattr` checks. Each
handler wraps data in a tuple `(module_path, class_name, serialized_data)`
and packs it with `ormsgpack.Ext(code, encoded_bytes)`.

The tuple structure is consistent across all ext codes — the ext hook
always unpacks `(module, name, data)` and uses `importlib.import_module`
to locate the class.

## Streaming Subsystem

### Architecture
Stream message handling lives in
`libs/langgraph/langgraph/pregel/_messages.py`.

### Key Files
- `pregel/_messages.py` — `StreamMessagesHandler` callback handler
- `pregel/loop.py` — Pregel execution loop (invokes handlers)
- `types.py` — `StreamMode` enum and message type definitions

### Deduplication via Seen Set
`StreamMessagesHandler.__init__()` initializes `self.seen: set[str]` to
track message IDs that have already been emitted.

`on_chain_start(inputs)` populates the seen set from input state via
`_state_values(inputs)`: it scans input values for `BaseMessage` instances
and adds their `id` to `self.seen`.

When `_find_and_emit_messages()` encounters a message, it checks
`msg.id in self.seen` before emitting. This prevents re-emitting messages
that were already in the state when the node started.

The seen set is populated from **inputs** (start of node) and checked
during **outputs** (end of node), creating a before/after diff.

### Cross-subsystem Boundaries
- Serialized checkpoints include streaming state for resume scenarios
- Agent 3 also works on streaming — the emission logic that Agent 3
  modifies feeds into the deduplication logic you work on


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

- **Agent 1:** F1, F5
- **Agent 2:** F2, F6
- **Agent 3:** F3, F7
- **Agent 4:** F4, F8

## Team Setup

**Create an agent team** to implement these features in parallel. Spawn one teammate per agent assignment above (4x2). Each teammate should work on their assigned features independently.

Assign each teammate their features from the Feature Assignments section. Teammates can communicate with each other if they need to coordinate on shared files.

**IMPORTANT:** You MUST delegate all feature implementation to your teammates. Do NOT implement any features yourself. Your role is to coordinate: spawn the team, assign work, monitor progress, and save the final combined patch.

Wait for all teammates to complete their tasks before creating the final combined patch.

## Patch Instructions

**CRITICAL:** Implement all assigned features. After each agent completes its feature, have it save a snapshot:
`git diff > data/patches/treatment-7/<FN>.patch`

When **all** features are complete, save the combined patch:
`git diff > data/patches/treatment-7/cumulative.patch`


Remember: after each agent finishes, save its snapshot with `git diff > data/patches/treatment-7/<FN>.patch`. When all features are done, save the combined patch with `git diff > data/patches/treatment-7/cumulative.patch`. Start with F1.
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
| Agent stuck on unrelated build/test errors | Nudge toward a different approach |
| No output for >2 minutes | Check if waiting for input |
| Agent completed all features but not yet saved final patch | Remind to save cumulative.patch |
| Lead forming team and delegating | Note the confirmation |

### 3.3 Escape time thresholds

Wall-clock time limit per feature: **~45 minutes**. If the agent has not produced a patch (or acknowledged it cannot) within the threshold, intervene.

### 3.4 Nudge examples

Use these as templates. Adapt to the situation.

**If stuck on a feature past the threshold:**
```
Let's move on to the next feature. You'll save a final combined patch at the end.
```

**If agent completed all features but forgot patch:**
```
Great! Now save your combined patch with:
git diff --staged > data/patches/treatment-7/cumulative.patch
```

**If agent is going in circles:**
```
You seem to be revisiting the same approach. Can you try a different angle?
If you're stuck, it's OK to move on to the next feature.
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

If the agent did not save the final combined patch, save it now:

```bash
git -C data/langgraph diff > data/patches/treatment-7/cumulative.patch
```

### 4.3 Verify patches

```bash
ate-features exec verify-patches 7
ls -la data/patches/treatment-7/
```

Expected: `cumulative.patch` (combined result from all agents).

- [ ] Verified patch files present
- [ ] Non-empty patches: `___________`

### 4.4 Verify LangGraph is clean

```bash
git -C data/langgraph checkout . && git -C data/langgraph clean -fd
git -C data/langgraph status
```

- [ ] Working tree clean

### 4.5 Update metadata.json

Update `data/transcripts/treatment-7/metadata.json` with actual timing and outcome data:

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

Record observations in `data/transcripts/treatment-7/notes.md`. Use this format:

```markdown
# Notes: Treatment 7 — Specialized Structured Team

## Assignment Confirmation
- Agent 1: F1, F5 (confirmed by lead)
- Agent 2: F2, F6 (confirmed by lead)
- Agent 3: F3, F7 (confirmed by lead)
- Agent 4: F4, F8 (confirmed by lead)

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
- [ ] Per-feature snapshots saved
- [ ] cumulative.patch saved (combined result)
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
