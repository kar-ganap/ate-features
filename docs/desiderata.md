# Desiderata

Immutable principles for the Agent Teams Eval (Feature Implementation) project.
Frozen after Phase 0.

## 1. Python + uv

Python 3.11+ only. uv as package manager. No pip.

## 2. TDD

Tests first, validation gates (unit mocks + integration real). No code merged
without passing `make test`, `make lint`, `make typecheck`.

## 3. Experiment Design is Law

`docs/experiment-design.md` is the north star. All experimental choices (features,
treatments, scoring rubrics, execution protocol) live there. Changes require a
Change Log entry with date, what changed, and rationale.

## 4. Reproducibility Where Possible

Pin LangGraph to a specific commit. Version-control all prompts and agent
definitions. Document what can't be pinned (interactive sessions, model
non-determinism). Pin model and Claude Code version across all treatments.

## 5. Objective Before Subjective

Tiered acceptance tests (T1 automated) are always scored before T2/T3 quality
assessment. Subjective judgment never overrides objective results. If a patch
fails T1, it fails — regardless of how good the approach looks.

## 6. Separation of Concerns

Harness code (`src/`) does not make experimental choices. The experiment protocol
(`docs/` + `config/`) drives all decisions. The harness is a tool, not a
decision-maker.

## 7. Raw Data Preservation

Never modify raw transcripts or patches. Derived data (scores, analysis) can be
regenerated from raw data at any time. If in doubt, keep the original.

## 8. Git Workflow

Phase branches off main. User merges manually. No force pushes. No
Co-Authored-By lines in commits.

## 9. Documentation as Code

CLAUDE.md updated at the end of each phase. Phase plans written before
implementation. Phase retros written after. Everything in the repo.

## 10. Spec-Based Prompts

No issue URLs, no anchoring to existing solutions. The agent receives a feature
description and acceptance tests only. This prevents solution-space collapse from
finding existing PRs or discussions.
