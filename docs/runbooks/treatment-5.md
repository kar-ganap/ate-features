# Runbook: Treatment 5 — Max Parallelism

| Dimension | Value |
|-----------|-------|
| Decomposition | explicit |
| Prompt specificity | detailed |
| Delegate mode | True |
| Team size | 8x1 |
| Communication | neutral |
| Specialization | vanilla |

**Agent Teams:** ON

## Pre-session Setup

```bash
# 1. Run preflight (records CC version)
ate-features exec preflight

# 2. Scaffold session directories
ate-features exec scaffold 5

# 3. Create patches directory
mkdir -p data/patches/treatment-5

# 4. Record start time
echo "Started: $(date -Iseconds)" >> data/transcripts/treatment-5/notes.md
```

## Start Session

```bash
cd data/langgraph
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude
```

### Opening Prompt

```
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

## Patch Instructions

After implementing each feature, save the patch and reset:
```
git diff > data/patches/treatment-5/<FN>.patch
git checkout . && git clean -fd
```
Save a separate patch for EACH feature before resetting.

```

## Monitoring

**Escape threshold:** ~45 min per feature. If the agent is stuck for >10 min on a single approach, consider nudging.

**Nudge templates:**
- **Stuck:** "Have you considered looking at the test file for hints about the expected behavior?"
- **Forgot patch:** "Please save a patch before moving on: `git diff > data/patches/treatment-{tid}/{FN}.patch`"
- **Forgot reset:** "Please reset before the next feature: `git checkout . && git clean -fd`"

## Post-session

```bash
# 1. Check for unsaved work
cd data/langgraph && git diff --stat

# 2. Verify patches
ate-features exec verify-patches 5

# 3. Record end time
echo "Ended: $(date -Iseconds)" >> data/transcripts/treatment-5/notes.md

# 4. Revert LangGraph to clean state
cd data/langgraph && git checkout . && git clean -fd
```

**Transcript location:** `~/.claude/projects/-Users-kartikganapathi-Documents-Personal-random_projects-others-projects-checkout-ate-features/`
Look for the most recent `.jsonl` file matching the session time.

## Final Checklist

- [ ] Preflight passed
- [ ] Session scaffolded
- [ ] Start time recorded
- [ ] Opening prompt pasted
- [ ] All features implemented
- [ ] Patches saved (one per feature)
- [ ] Patches verified
- [ ] End time recorded
- [ ] Transcript located
- [ ] LangGraph reverted to clean state
- [ ] Notes finalized
