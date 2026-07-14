---
name: friendly-pr-reviewer
description: >-
  Render a PLAIN-LANGUAGE narrative summary of one PR's already-produced governance
  review -- what changed, which readiness stages are pass/warning/blocked (verbatim),
  which findings are NEW/RESOLVED/pre-existing (when a base identity set is supplied),
  who must approve, and exactly one next action. Use when someone asks "explain this PR
  in plain language", "what does this review envelope actually mean", or wants a
  non-technical summary of a PR's governance findings WITHOUT opening JSON/YAML. It is
  a NARRATIVE over already-shipped truth (`retail check --format review`, readiness
  truth), NOT a merge-safety verdict -- see the boundary note against F025
  pr-readiness-reviewer below. It renders NO merge_ready boolean and NO score; asked
  for either, it declines and cites the rule.
---

# friendly-pr-reviewer

<!--
=============================================================================
 EMBEDDED MODULE CONTRACT (F024 authority declaration -- filled in place, the
 same pattern F025 pr-readiness-reviewer uses).
 See: docs/architecture/product-modules.md (the five categories, the authority
      matrix, the two sub-vocabularies), templates/module-contract.md (the
      copy-me declaration this fills).
=============================================================================
-->

## Module Contract -- Friendly PR Reviewer

- **Authority category:** Product Module
- **Capability level:** `read-only` *(exactly one of `read-only | artifact-writing | execution-capable`)*
- **Product layer:** cross-cutting *(guards no stage, gates no promotion; a presentation companion, sibling to F025/F036/F037)*
- **Roadmap feature:** not yet assigned -- a human assigns the F-number at scheduling
  (this skill does NOT self-assign one; see spec.md status line). **On-disk spec:**
  `specs/130-pr-reviewer`
- **Owner:** the repo maintainer / PR reviewer (a named human)
- **Status:** Authored

### What it does (one line)

> Reads one PR's already-produced review envelope + committed readiness truth, and
> RENDERS a plain-language narrative of what changed and what it means -- never a
> merge-ready verdict, never a score.

### Core Authority it READS

It reads; it never writes these, and it re-derives nothing.

- The `build_review_result` review envelope (`review_integration.py`) -- `outcome`
  (`ok`/`blocked` only), `checks_run`, `changed_files`, `changed_readiness_state`,
  `affected_stages`, `findings[]`, `blocking_findings[]`, `next_actions[]`,
  `run_boundary`, `result_digest`.
- The SARIF finding identity (`sarif.finding_fingerprint` / `sarif_document`) -- the
  canonical new-vs-existing key, reused directly for the temporal diff.
- `mappings/<table>/readiness-status.yaml` -- `current_stage`, per-stage `status`,
  `approvals[]` (named owner + date), `blocking_reasons[]` -- read as an already-parsed
  mapping; this module opens no file itself.
- The `readiness_classify` refutation-first category rank (approval > grain >
  live_validation > artifact > readiness) -- reused to pick exactly one next action
  AND to route a blocked stage to its required approval surface.

### Derived evidence it WRITES

- none (`read-only`; the summary is rendered EPHEMERALLY to the operator, mirroring
  F025's own "presents / summarizes Core Authority" reading -- no tracked summary file,
  no committed evidence artifact).

### Approved step it EXECUTES

- none (`read-only`). The ONLY networked write anywhere in this feature is the
  separate, OPT-IN, off-by-default CI step (`.github/workflows/ci.yml` +
  `scripts/post_friendly_pr_summary.py`) that posts/updates the sticky PR comment --
  that step is explicit CI infrastructure outside this skill's own invocation, gated on
  a repo-level opt-in flag, and is not part of the tested deterministic core.

### Forbidden operations (the matrix says NO)

- MUST NOT create truth: no defining business meaning, no approving a metric/mapping.
- MUST NOT grant approval or move a readiness stage to `pass` (named-human / Core
  Authority only).
- MUST NOT connect to a DB or external service, and MUST NOT publish a Power BI
  artifact.
- MUST NOT emit a numeric / maturity / confidence / merge-ready / completeness score
  or percentage (hard rule #9).
- As a `read-only` module it additionally MUST NOT write any derived evidence or
  execute any step (the opt-in CI comment post is separate infrastructure, not this
  skill's own action).

### How it handles a missing input

When the review envelope is absent/unproducible, or `next_actions[]` is empty, or the
readiness file is absent, or a source conflicts with another, the module records that
line `unknown` / "could not determine" (naming the missing source), surfaces it, and
STOPS that line -- it never fabricates the input, assumes `pass`, or invents a change
story (Principle V; FR-017/018/019).

---

## Boundary against F025 pr-readiness-reviewer (read first)

The kit already ships `pr-readiness-reviewer` (F025): a per-PR read-only
**merge-safety VERDICT** -- `merge_ready` (yes/no) + `blockers[]` +
`required_human_decisions[]`. That skill answers "is this PR safe to merge?" -- a
judgment reading of PR + evidence state, and it is the authority for that question.

This skill (Friendly PR Reviewer) is DISTINCT and complementary: it answers "in plain
language, what CHANGED in this PR and what does it mean?" -- a presentation NARRATIVE
over the governance review envelope. It renders no `merge_ready` boolean, adopts no
verdict authority, and does not replace or re-derive F025. Where both could run on the
same PR: F025 owns the merge gate/verdict; this skill owns the plain-language change
story. Asked to decide whether a PR is safe to merge, this skill DECLINES and points to
`pr-readiness-reviewer` instead.

## Scope boundary (read first)

- **Presentation over shipped truth, never a second analysis engine.** Every summary
  line traces to a field of the review envelope, the readiness truth, or a
  fingerprint. It re-runs no rule, opens no DB, and adds no `retail check` rule.
- **No fake confidence, no verdict.** No numeric score/percentage/tally anywhere
  (rule #9); no `merge_ready` boolean anywhere (that stays F025's surface).
- **Read-only; takes no action on the PR.** It cannot approve, merge, dismiss a
  finding, edit the PR body, resolve a thread, or move a readiness stage. It renders
  words only.
- **Masked before egress.** The four `_mask`-detected shapes (email, SSN/national-ID-
  like number, long digit run, `key: value` secret assignment) are masked before any
  finding text enters the summary -- with extra force in the sticky comment (a public
  surface). A bare DSN/connection-string URL in a finding message is a documented v1
  non-coverage (see `docs/tools/friendly-pr-reviewer.md`), not a masking guarantee.
- **Deterministic.** Same envelope + same readiness (+ same base set) -> byte-identical
  summary. No wall-clock read; a timestamp is always an explicit argument.
- **Honest on missing/conflicting inputs.** An absent envelope, empty `next_actions[]`,
  absent readiness, a non-file locator, or two disagreeing sources are all surfaced
  honestly, never silently resolved or assumed `pass`.
- **Generic.** No worked-example specifics baked in; `retail_store_sales` is a filled
  instance cited as a reference only (Principle VII). ASCII only, UTF-8 no BOM; `--`
  and `->` only.

## Run it -- render the summary

The deterministic core is `seshat.pr_summary` (`render_summary`, `classify_changes`,
`mask`, `pick_next_action`, `compose_comment`, `find_existing`). To render a summary by
hand over an already-produced review:

1. **Produce the review envelope**: `retail check --format review [--commit-range
   BASE..HEAD] > review.json` (an already-shipped surface; no new analysis).
2. **Load readiness truth** (optional but recommended): parse the relevant
   `mappings/<table>/readiness-status.yaml` into a plain mapping.
3. **(Optional, US2) Gather a base fingerprint set**: a prior run's finding
   fingerprints (via `sarif.finding_fingerprint`) or a base SARIF run's
   `partialFingerprints`. Omitting this is honest and supported -- the summary then
   states the new-vs-pre-existing distinction could not be determined.
4. **Render**: call `render_summary(envelope, readiness, base_fingerprints=...,
   timestamp=...)` -- it returns a `FriendlySummary` with a `.text` plain-language
   document, per-stage statuses, blocker groups, required authority, and exactly one
   next action.
5. **(Optional, US3) Compose the sticky comment**: `compose_comment(summary)` for the
   marker + masked body; `find_existing(comment_bodies)` to decide update-vs-create.
6. **STOP -- present, take no action.** Emit the summary text to the operator (or let
   the opt-in CI step post/update the sticky comment). No PR action is taken.

See `templates/friendly-pr-summary.md` for the rendered shape and
`docs/tools/friendly-pr-reviewer.md` for the full field reference, the temporal
fingerprint-diff limitation, and the opt-in CI step.

## No fake confidence (the guardrail)

Asked for "a PR health score", "a confidence percentage", or "a merge-readiness
number", DECLINE: cite no-fake-confidence (rule #9) and return the plain-language
summary instead -- verbatim statuses, named blockers, one next action, nothing
numeric.

## Decline-to-act (read-only proof)

Asked to merge, approve, submit a review, resolve a thread, edit the PR body, push a
commit, or mark a stage `pass`, this skill DECLINES, states it is read-only and cannot
create truth (F024 Core Authority; Principle V), and returns the summary for a human to
act on. It never self-grants an approval and never names itself as the required
authority.

## Honest-state rules (never invent, never silently resolve)

| Situation | What the skill does |
|-----------|----------------------|
| The review envelope is absent/unproducible (e.g. a bad commit range) | states so and stops; renders no change story |
| `next_actions[]` is empty | states "no next action was produced by the review" |
| A referenced `readiness-status.yaml` (or a stage entry in it) is absent | stage reported `unknown`, source named; never assumed `pass` |
| A finding locator is not a file path (e.g. a git-metadata rule) | described in words, never presented as a file:line pointer |
| No base fingerprint set is supplied | states the new-vs-pre-existing distinction could not be determined; findings listed as "present", never defaulted to "new" |
| Two sources disagree (e.g. readiness shows a stage `pass` while the envelope reports it blocked) | surfaced as a conflict; never resolved here (a human judgment / F025 territory) |
| A very large finding set | grouped by classification, capped at a stable documented count per group, with the omission count always stated -- never a silent truncation that hides a blocker |

## See also

- The output shape: `../../../templates/friendly-pr-summary.md`; the tool doc (inputs,
  the temporal fingerprint diff, the opt-in CI step, the F025 boundary):
  `../../../docs/tools/friendly-pr-reviewer.md`.
- The authority category it declares: `../../../docs/architecture/product-modules.md`;
  the copy-me declaration it fills: `../../../templates/module-contract.md`.
- The merge-safety verdict sibling (the F025 boundary): `../pr-readiness-reviewer/SKILL.md`.
- The reused seams (read by field, never modified): `../../../src/seshat/review_integration.py`,
  `../../../src/seshat/sarif.py`, `../../../src/seshat/readiness_classify.py`,
  `../../../src/seshat/readiness_evidence.py` (pattern reference only),
  `../../../src/seshat/interview_review.py` (mask shapes reproduced, not imported).
- The deterministic core + tests: `../../../src/seshat/pr_summary.py`,
  `../../../tests/unit/test_pr_summary.py`.
- The opt-in CI wrapper: `../../../.github/workflows/ci.yml` (the "Friendly PR summary"
  step) + `../../../scripts/post_friendly_pr_summary.py`.
