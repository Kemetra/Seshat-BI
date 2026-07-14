# Implementation Plan: Friendly PR Reviewer (Plain-Language PR Summary)

**Branch**: `130-pr-reviewer` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/130-pr-reviewer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command.

## Summary

Add a plain-language PRESENTATION LAYER over the already-shipped, authoritative
review results. The primary requirement: render a non-technical-owner-readable
summary of one PR -- affected artifact kinds, per-stage `pass`/`warning`/`blocked`
status (verbatim), NEW vs RESOLVED vs pre-existing blockers, required approval
authority, and exactly one next action -- as a single sticky comment that updates
in place, without re-running analysis, without exposing secrets/PII, and without
taking any action on the PR.

Technical approach: a docs-first **Product Module** (a SKILL) backed by ONE pure,
stdlib, deterministic renderer/differ over the `build_review_result` envelope +
the `finding_fingerprint` identity + the readiness truth. The renderer masks the
`_mask`-detected PII/secret shapes before any egress (DSN-URL detection is a
documented v1 non-coverage, FR-009). The changed-vs-pre-existing distinction is a
temporal fingerprint diff (base set vs head set). The networked sticky-comment
post is a thin, opt-in step added to the EXISTING `ci.yml` -- off by default, no
new workflow file, not part of the tested deterministic core. No new
`retail check` rule; no change to any consumed output shape.

## Technical Context

**Language/Version**: Python 3.13 (repo standard); stdlib-only for the
deterministic renderer/differ core (Principle VIII; B1/B3 import-boundary guards
keep DB/network imports out of the static path).

**Primary Dependencies**: NONE new in the tested core -- consumes shipped
in-repo modules only (`review_integration`, `sarif`, `readiness_classify`,
`readiness_evidence`, `interview_review` masking, optionally
`review_pack_export`). The opt-in CI comment wrapper uses the GitHub Actions
runner's own `gh` / GitHub token already available in `ci.yml`; it adds no new
Python dependency to the package.

**Storage**: N/A. Reads committed artifacts (review envelope produced by
`retail check --format review`, `readiness-status.yaml`); writes no tracked file.
The only optional output is an ephemeral PR comment via the opt-in step.

**Testing**: pytest (`-m unit`); fixture-driven. The renderer, differ, masking,
next-action selection, and sticky-comment-body composition are all pure functions
tested against fixtures. No network, no DB, no live GitHub in the unit suite.

**Target Platform**: CI (Linux/Windows GitHub Actions runners) for the opt-in
comment step; the core is platform-independent (pure Python).

**Project Type**: Single project (agent-first kit; a skill + a small pure module).

**Performance Goals**: N/A (a summary render over one PR's already-computed
envelope; deterministic and fast). No large-data path.

**Constraints**: Deterministic, byte-stable, NO wall-clock read (FR-012);
stdlib-only tested core; ASCII / UTF-8-no-BOM; masks the `_mask`-detected
PII/secret shapes before egress, DSN-URL a documented v1 non-coverage (FR-009);
no numeric score (FR-011); no PR-mutating action (FR-010); opt-in and additive to
`ci.yml` (FR-015). Windows `MAX_PATH`: repo-relative paths stay short.

**Scale/Scope**: Per-PR, v1 (no portfolio/multi-PR roll-up). Three user stories;
MVP = US1 (the renderer). US2 (the differ) and US3 (the opt-in sticky comment)
build on US1.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Agent-First, Gate-Enforced**: PASS. The skill is the interface; the
  `retail check` review envelope it reads is the gate it consumes, not a new
  authority. It adds no rule and cannot flip the gate's exit code.
- **II. Depend, Never Fork**: PASS. Reuses shipped in-repo surfaces; forks/vendors
  nothing; the GitHub Action is reused, not re-implemented.
- **III. Medallion / Gold-Only**: N/A (no warehouse or Power BI read). No DB.
- **IV. Source Mapping Before Silver**: N/A (writes no silver/gold; presentation
  only).
- **V. Agent Stops at Judgment Calls**: PASS. The summary surfaces required
  human decisions (approval authority, PII publish-safety, grain, conflicts) and
  routes them to a named owner; it approves/merges/dismisses nothing (FR-007,
  FR-010, FR-019). It never self-grants.
- **VI. Defaults Then Deviations**: PASS. Severity/status read verbatim from the
  envelope; the next-action pick uses the shipped `readiness_classify` rank
  (a committed default), and any deviation would be stated with its reason.
- **VII. C086 Is An Example**: PASS. Generic; worked-example names cited only
  (FR-020).
- **VIII. Static-First Governance, Live Deferred**: PASS. Tested core is
  stdlib-only with no DB/network import (B1/B3 preserved); the networked comment
  post is a thin opt-in wrapper outside the tested core. No new live validator.
- **IX. Secrets and Reproducibility**: PASS -- and load-bearing here. FR-009
  masks the `_mask`-detected PII/secret shapes before egress (the comment is a
  public surface), with a bare DSN-URL in a finding message a documented v1
  non-coverage (residual risk stated, not hidden); deterministic, byte-stable, no
  clock (FR-012); ASCII/UTF-8-no-BOM (FR-020).

**Hard-rule check**: adds no `retail check` rule (SC-006); does not approve/merge/
publish/score (FR-010/FR-011, hard rule #9); reuses the Action, mints no workflow
(FR-015, hard rule #8: docs/skill first); no self-assigned F-number (FR-021); no
readiness stage moved (FR-013). No violation -> Complexity Tracking is empty.

**Post-design re-check**: still PASS -- the design keeps the network out of the
tested core and adds no dependency to the package's import path.

## Project Structure

### Documentation (this feature)

```text
specs/130-pr-reviewer/
|-- plan.md              # This file
|-- spec.md              # Feature spec (committed)
|-- research.md          # Phase 0 output (reuse-surface confirmation)
|-- data-model.md        # Phase 1 output (the summary + classification shapes)
|-- quickstart.md        # Phase 1 output (how to render a summary from an envelope)
|-- contracts/           # Phase 1 output (renderer/differ input-output contract)
`-- tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/seshat/
|-- review_integration.py     # REUSED (input: build_review_result envelope)
|-- sarif.py                  # REUSED (input: finding_fingerprint identity)
|-- readiness_classify.py     # REUSED (input: refutation-first next-action rank)
|-- readiness_evidence.py     # PATTERN REF ONLY (_redact_dsn re-impl style; its
|                             #   _scrub needs a literal DSN, so NOT a masker here)
|-- interview_review.py       # REUSED (input: _mask PII-shape contract -- the masker)
|-- review_pack_export.py     # REUSED (optional: pack shape reference)
`-- pr_summary.py             # NEW: pure, stdlib renderer + differ + comment-body
                              #      composition (deterministic, no clock, no network)

tests/unit/
`-- test_pr_summary.py        # NEW: fixture-driven tests for renderer / differ /
                              #      masking / next-action pick / sticky-marker body

.claude/skills/
`-- friendly-pr-reviewer/
    `-- SKILL.md              # NEW: the Product Module skill (agent runtime); embeds
                              #      the F024 Module Contract; when-to-run + boundary

templates/
`-- friendly-pr-summary.md    # NEW: the plain-language summary/sticky-comment shape

docs/tools/
`-- friendly-pr-reviewer.md   # NEW: tool doc (inputs, the temporal diff, opt-in step)

.github/workflows/
`-- ci.yml                    # EDITED: ONE additive, OPT-IN, off-by-default step
                              #         that renders + posts the sticky comment
```

**Structure Decision**: Single-project layout. The tested deterministic core is
one new pure module (`src/seshat/pr_summary.py`) plus its unit test; everything
else is docs-first (skill + template + tool doc) per hard rule #8. The only
network-touching change is one additive opt-in step in the existing `ci.yml`
(FR-015). Reused modules are consumed by field/function, not modified.

## Phase 0 -- Research (reuse-surface confirmation)

Confirm (already verified during specify) the consumed seams are stable and
sufficient, and record any residual unknown in `research.md`:

1. **Review envelope**: `review_integration.build_review_result` yields
   `outcome`, `checks_run`, `changed_files`, `changed_readiness_state`,
   `affected_stages`, `findings[]`, `blocking_findings[]`, `next_actions[]`,
   `run_boundary`, `result_digest`. Exposed via `retail check --format review`
   (`runner.run_review`). CONFIRMED sufficient for FR-004/005/008.
2. **Finding identity**: `sarif.finding_fingerprint` = sha256(rule_id + severity
   + locator + message); also the SARIF `partialFingerprints`
   (`seshatFinding/v1`). This IS the temporal new-vs-existing key. CONFIRMED for
   FR-006/018.
3. **Masking contract**: `interview_review._mask` (email / SSN / long-digit /
   secret-assignment shapes) is the reusable, self-contained pattern for FR-009 --
   it matches by shape and needs no external input. CONFIRMED reusable. NOTE on
   `readiness_evidence._scrub`: it is NOT usable here for DSN masking -- `_scrub`
   only redacts a DSN when the caller passes the literal DSN string
   (`out.replace(dsn, ...)`), which a DB-less PR summarizer does not have; it does
   NOT shape-detect a DSN URL embedded in arbitrary text. Therefore v1 masks only
   the `_mask` shapes; a bare DSN/connection-URL in a finding message is a
   documented v1 non-coverage (FR-009), not a masking guarantee, and NO new
   DSN/URL detector is added (reuse-only, hard rule #1). Open item: import the
   private helper or lift its patterns into the new module's own small masker --
   decided in Phase 1 (lift the pattern with a citation, keeping the tested core
   self-contained and stdlib-only, mirroring how `readiness_evidence` re-implements
   `_redact_dsn` rather than importing `cli`).
4. **Next-action rank**: `readiness_classify.classify` / `rank_of` /
   `CATEGORY_RANK` gives the refutation-first order (approval > grain >
   live_validation > artifact > readiness). CONFIRMED for FR-008's single-pick.
5. **Base identity source**: a base review/SARIF run or a supplied base
   fingerprint list. CONFIRMED that GitHub SARIF upload uses `partialFingerprints`
   for new-vs-existing; v1 accepts a base fingerprint set as an explicit input and
   reports undeterminable when absent (FR-018). Deferred: auto-fetching the base
   run inside the pure core (that is the opt-in wrapper's job, outside the core).
6. **CI reuse**: `ci.yml` already runs `retail check` on pull_request; the opt-in
   step hangs off the same workflow (FR-015). CONFIRMED no new workflow needed.

## Phase 1 -- Design (data-model, contracts, quickstart)

- **data-model.md**: the `FriendlySummary` output shape (affected-artifact
  narrative, per-stage status list of {stage, status-verbatim, source}, the three
  blocker groups {new, resolved, carried_over} each a list of masked finding
  lines, required-approval-authority list, exactly-one next_action, an explicit
  `undetermined[]` for missing-input lines); the `ChangeClassification` (three
  disjoint fingerprint sets); the `StickyComment` (marker + body). All frozen /
  additive-versioned; no score field anywhere.
- **contracts/**: the pure-function contract for `render_summary(envelope,
  readiness, base_fingerprints=None) -> FriendlySummary`, `classify_changes(
  base_fingerprints, head_findings) -> ChangeClassification`, `mask(text) -> str`,
  `pick_next_action(next_actions) -> str | None`, and `compose_comment(summary) ->
  StickyComment` -- each deterministic, no clock, no network, no mutation.
- **quickstart.md**: `retail check --format review > review.json`, then render the
  friendly summary from `review.json` + `readiness-status.yaml` (+ optional base
  fingerprints); shows the masked output and the single next action.

**Re-run Constitution Check after Phase 1**: expected PASS (network stays out of
the core; no dependency added; no rule; no score).

## Phase 2 -- Tasks

`/speckit-tasks` generates `tasks.md` grouped by user story: US1 (renderer +
masking + next-action pick + honesty-on-missing), US2 (temporal differ), US3
(sticky-comment body composition + opt-in `ci.yml` step + tool doc), plus the
skill/template/docs and the F024 Module Contract. Tests are requested (fixture
unit tests for every pure function; the networked post is documented, not
unit-tested against a live API).

## Complexity Tracking

> No Constitution Check violation -- this table is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | --         | --                                   |
