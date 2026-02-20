# Process

Each phase follows a strict 4-step lifecycle: **PLAN -> TEST -> IMPLEMENT -> RETRO**.

## Phase Lifecycle

### PLAN

1. Write `docs/phases/phase-N-plan.md` with implementation details, test plan,
   and acceptance criteria.
2. Create branch: `phase-N-description`.

### TEST

1. Write unit tests with mocks — all FAIL (red).
2. Write integration stubs where applicable.
3. Commit failing tests.

### IMPLEMENT

1. Implement to make tests GREEN.
2. Run lint and typecheck.

### RETRO

1. User observations first.
2. Claude drafts retro doc at `docs/phases/phase-N-retro.md`.
3. Update CLAUDE.md with current state and any new gotchas.
4. Commit + push.
5. User merges to main.

## Validation Gates

| Tier | Scope | Command | When |
|------|-------|---------|------|
| Mock | Unit tests with mocked deps | `make test` | Every phase |
| Real | Integration against built LangGraph | `make test-int` | Phases 1+ (requires pinned LangGraph) |
| Lint | Code quality | `make lint` | Every phase |
| Types | Type checking | `make typecheck` | Every phase |

## Git Workflow

- `main` <- `phase-N-description` (user-merged, no force push)
- No Co-Authored-By lines in commits

## Retro Format

- What Worked
- Surprises
- Deviations from Plan
- Implicit Assumptions Made Explicit
- Scope Changes for Next Phase
- Metrics (tests added, files changed)
