# Runbook: Treatment 2b — Autonomous + Discourage

| Dimension | Value |
|-----------|-------|
| Decomposition | autonomous |
| Prompt specificity | vague |
| Delegate mode | True |
| Team size | 4x2 |
| Communication | discourage |
| Specialization | vanilla |

**Agent Teams:** ON

## Pre-session Setup

```bash
# 1. Run preflight (records CC version)
ate-features exec preflight

# 2. Scaffold session directories
ate-features exec scaffold 2b

# 3. Create patches directory
mkdir -p data/patches/treatment-2b

# 4. Record start time
echo "Started: $(date -Iseconds)" >> data/transcripts/treatment-2b/notes.md
```

## Start Session

```bash
cd data/langgraph
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude
```

### Opening Prompt

```
# Feature Implementation Task

Implement the following features in the LangGraph repository. Acceptance tests are in the `tests/acceptance/` directory.

- **Pandas DataFrame/Series msgpack serialization** (serializer)
- **Generic Pydantic v2 type round-trip in checkpoint serde** (serializer)
- **StrEnum preservation in checkpoint serde** (serializer)
- **Nested Enum deserialization fix** (serializer)
- **Reducer metadata ordering dependency** (state)
- **BinaryOperatorAggregate ignores default_factory** (state)
- **Nested message detection in stream_mode=messages** (streaming)
- **Input message dedup for nested structures** (streaming)

## Patch Instructions

After implementing each feature, save the patch and reset:
```
git diff > data/patches/treatment-2b/<FN>.patch
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
ate-features exec verify-patches 2b

# 3. Record end time
echo "Ended: $(date -Iseconds)" >> data/transcripts/treatment-2b/notes.md

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
