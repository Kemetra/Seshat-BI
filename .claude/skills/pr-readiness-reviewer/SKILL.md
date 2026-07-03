---
name: pr-readiness-reviewer
description: >-
  Render ONE structured "is this PR safe to merge" verdict for a single pull request in
  the Seshat_BI repo -- merge_ready (yes/no) + blockers[] + warnings[] +
  required_human_decisions[] + evidence[] + one next_action. Use when someone asks "is
  this PR ready to merge?", "what blocks this PR?", or "review this PR for promotion". It
  OBSERVES the PR's state (open/draft, mergeable, CI/workflow conclusions, open review
  threads, unresolved Codex/GitHub review comments) and READS the committed readiness
  evidence the PR touches (readiness-status.yaml, source-map.yaml approval metadata,
  declared-vs-run tests, no raw data / no secrets / no local paths), then cross-checks the
  PR body's CLAIMS against that evidence. READ-ONLY: it CANNOT merge a PR, approve a PR,
  resolve a review thread, push/amend a commit, edit a PR body, or move/upgrade a
  readiness stage -- it observes and reports only. merge_ready is a DERIVED BOOLEAN, never
  a numeric merge/confidence/health score (rule #9); a score request is declined.
---

# pr-readiness-reviewer

<!--
=============================================================================
 EMBEDDED MODULE CONTRACT (F024 authority declaration -- filled in place)
 This skill fills templates/module-contract.md HERE rather than as a separate
 file (this feature ships exactly three artifacts: this skill, the verdict
 template, and the tool doc). The category is declared verbatim below.
 See: docs/architecture/product-modules.md (the five categories, the authority
      matrix, the two sub-vocabularies), templates/module-contract.md (the
      copy-me declaration this fills).
=============================================================================
-->

## Module Contract -- PR Readiness Reviewer

- **Authority category:** Product Module
- **Capability level:** `read-only`  *(exactly one of `read-only | artifact-writing | execution-capable`)*
- **Product layer:** cross-cutting *(the functional axis -- see docs/roadmap/roadmap.md; orthogonal to category; this module guards promotions at every stage and enters none)*
- **Roadmap feature:** F025  **On-disk spec:** `specs/019-pr-readiness-reviewer`
- **Owner:** the repo maintainer / PR reviewer (a named human)
- **Status:** Authored

### What it does (one line)

> Reads one PR's observed state and the committed readiness evidence it touches, and
> RENDERS a structured `merge_ready` verdict -- a reading of evidence, never an authority.

### Core Authority it READS

It reads; it never writes these. Inputs, unchanged.

- `mappings/<table>/readiness-status.yaml` -- `current_stage`, per-stage `status`,
  `approvals[]` (named owner + date), `blocking_reasons[]`.
- `source-map.yaml` -- approval / mapping-gate CLEARED metadata (when the PR touches a mapping).
- The PR's declared test plan, the recorded `retail check` / `retail validate` and CI
  results, and the PR diff / file list (for the raw-data / secret / path scan).

### Derived evidence it WRITES

- none (`read-only`; the verdict is rendered EPHEMERALLY to the operator -- "presents /
  summarizes Core Authority", NOT "writes derived evidence". No tracked verdict file is
  written and no committed evidence artifact is created).

### Approved step it EXECUTES

- none (`read-only`).

### Forbidden operations (the matrix says NO)

- MUST NOT create truth: no defining business meaning, no approving a metric / mapping.
- MUST NOT grant approval or move a readiness stage to `pass` (named-human / Core Authority only).
- MUST NOT connect to a DB or external service, and MUST NOT publish a Power BI artifact.
- MUST NOT emit a numeric / maturity / confidence score (rule #9).
- As a `read-only` module it additionally MUST NOT write any derived evidence or execute any step.
- MUST NOT (this module's concrete read-only boundary): merge a PR, approve a PR (submit a
  review, grant a required approval), resolve / reply to / edit a review thread or comment,
  push / amend / revert a commit, edit a PR body or title, or move / upgrade / mark `pass`
  a readiness stage or clear the mapping gate. It performs read-only observation only.

### How it handles a missing input

When a required Core Authority input is absent or a stage is not yet `pass`, the module
records that verdict line `unknown` (naming the missing source), surfaces it, and STOPS --
it never fabricates the input, assumes `pass`, self-approves, or proceeds past the missing
gate (Principle V; stop-and-ask).

---

The kit merges work through a human PR review pattern that is, today, re-applied by hand on
every PR: is the PR still a draft, is it mergeable, did CI pass, are there unresolved
Codex / GitHub review comments, does the PR body claim a readiness stage the committed
`readiness-status.yaml` does not back, was a publish approval requested before the required
prior stage is `pass`, did someone commit raw data or a secret or a local machine path.
This skill turns that pattern into a repeatable read: it OBSERVES one PR plus the committed
readiness evidence and RENDERS one structured verdict. It is the per-PR sibling of the
F012 portfolio control room: F012 answers "which table is broken across the portfolio";
this answers "is THIS pull request safe to merge, and what blocks it". It adds no new gate,
no new validator, no `retail check` rule, no CLI verb, and no CI workflow (Principle VIII;
hard rule #8): the agent is the runtime.

## Scope boundary (read first)

- **Aggregates and observes, never re-derives or gates.** Every verdict line traces back
  to an observed PR fact or a committed evidence file. It READS the recorded results of the
  existing gates (`retail check` / `retail validate`) and the existing CI; it does NOT
  re-run them as a new check and adds no rule. Reading PR / CI / git state is read-only
  OBSERVATION, not a gate and not a mutation.
- **Read-only (the boundary, verbatim).** The module cannot merge a PR, approve a PR
  (submit a review, grant a required approval), resolve / reply to a review thread,
  push / amend a commit, edit a PR body, or move / upgrade a readiness stage -- it observes
  and reports only (F024 Core Authority; Principle V).
- **The gating rule (verbatim).** `merge_ready` is `no` while ANY `blockers[]` entry OR ANY
  open `required_human_decisions[]` entry exists; `warnings[]` do NOT alone flip
  `merge_ready`; `required_human_decisions[]` is a SEPARATE gating class from `blockers[]`
  and BOTH gate `merge_ready: yes`.
- **No fake confidence.** `merge_ready` is a DERIVED BOOLEAN ("no blocker and no open
  required-human-decision found in evidence"), never a numeric merge / confidence / health
  score and never an approval (rule #9). The module emits NO number that reads as
  confidence; asked for one, it declines and cites rule #9.
- **Every line traces to a source.** EVERY entry in `blockers[]`, `warnings[]`,
  `required_human_decisions[]` carries a cited source -- a PR fact (PR number, check-run
  conclusion, thread / comment id) or a committed source (path + field / line). A finding
  with no traceable source is a defect.
- **Defines no business meaning and approves nothing.** A grain, a PII publish-safety call,
  a sentinel-vs-null choice, a business rollup, or whether a metric / mapping is correct are
  `required_human_decisions[]` it routes to a named owner (Principle V) -- never decided here.
- **Generic.** No worked-example specifics (billing codes, segments, PII column names,
  per-table grain keys). C086 / `retail_store_sales` are filled instances cited as
  references, never baked in (Principle VII).
- ASCII only, UTF-8 no BOM; `--` and `->` only.

## Aggregates and observes, never re-derives (the evidence chain)

Every verdict input is interpreted from one observed PR fact or one committed source, at
the default severity below. This is the reproducibility backbone of the rendered verdict.

| Verdict input | Source it observes / reads | Default severity |
|---------------|----------------------------|------------------|
| PR state (open / draft / closed) | the PR's own state (e.g. `gh pr view`) | draft -> blocker; closed -> blocker |
| mergeability / conflicts | the PR's mergeable state + base divergence | conflicts -> blocker |
| CI / workflow conclusions | recorded check-run / workflow conclusions on the head SHA | failing required check -> blocker; pending -> blocker for `yes` |
| open review threads | unresolved review threads on the PR | unresolved -> warning (blocker if change-requested) |
| Codex / GitHub review comments | unresolved review comments / findings | unresolved -> warning; unaddressed change-request -> blocker |
| tests declared vs run | the PR body's claimed test plan vs the recorded CI test result | declared-not-run -> blocker |
| no raw data committed | the PR diff file list vs the repo's raw-data ignore policy | raw data present -> blocker |
| no secrets / no local paths | the PR diff scanned for secret-shaped / machine-path strings | present -> blocker |
| readiness-stage consistency | PR-body claimed stage vs `mappings/<table>/readiness-status.yaml` `current_stage` + per-stage `status` | mismatch -> blocker |
| approvals consistency | PR-body claimed approval vs `readiness-status.yaml` `approvals[]` (named owner + date) | missing / absent -> blocker |
| source-map approval metadata | `source-map.yaml` approval / mapping-gate CLEARED metadata (PR touches a mapping) | absent when claimed -> blocker |
| PR-body drift vs readiness | any PR-body claim unsupported by committed evidence | unsupported claim -> warning (blocker if it asserts a stage `pass`) |
| publish approval requested too early | a publish / merge-to-publish request while the required prior stage is not `pass` | too-early -> required_human_decision, and a blocker until resolved |

If a source is missing, record that line `unknown` with the missing source NAMED -- do NOT
invent a status or assume `pass`. The module cannot UPGRADE a verdict past its evidence.

## Run it -- render the verdict

Render `templates/pr-readiness-report.md` filled from the observed PR facts + committed
evidence. Eight steps, then STOP:

### 1. Identify the target PR
Name the single PR under review (number / ref) and its head SHA. This module is per-PR
(a portfolio PR roll-up is deferred).

### 2. OBSERVE the PR facts (read-only)
Read the PR's state (open / draft / closed), mergeable state + base divergence, recorded
CI / workflow conclusions on the head SHA, open review threads, and unresolved
Codex / GitHub review comments -- via read-only `gh` / git reads the agent already
performs (`gh pr view`, `gh pr checks`, the PR diff). Read, never write, GitHub state.

### 3. READ the committed readiness evidence the PR touches
Read `mappings/<table>/readiness-status.yaml` (`current_stage`, per-stage `status`,
`approvals[]`, `blocking_reasons[]`), `source-map.yaml` approval metadata (if the PR
touches a mapping), the declared test plan, the recorded `retail check` / `retail validate`
and CI results, and the PR diff for the raw-data / secret / local-path scan. These are
INPUTS; the module creates no new evidence file.

### 4. CROSS-CHECK the PR-body claims against that evidence
The novel surface this module owns: compare what the PR CLAIMS to what the committed
evidence SUPPORTS -- readiness-stage consistency, approvals consistency, source-map
approval metadata, and general PR-body drift. A claim asserting a stage `pass` unsupported
by evidence is a blocker; a lesser unsupported claim is a warning. Cite the conflicting
field; edit nothing.

### 5. CLASSIFY each finding (blocker / warning / required-decision)
Apply the evidence-chain severity defaults above (Principle VI). A deviation from a default
(e.g. an unresolved thread promoted to a blocker because a reviewer marked change-requested)
is recorded WITH ITS REASON -- never silently promoted or demoted. A Principle-V judgment
item (see the trigger list below) is a `required_human_decision`, routed to a named owner.

### 6. APPLY the gating rule to derive merge_ready
`merge_ready` is `no` while ANY `blockers[]` entry OR ANY open `required_human_decisions[]`
entry exists; `warnings[]` do NOT alone flip it. A `pending` or `unknown` line is NOT
treated as `pass`. `merge_ready: yes` requires zero blockers AND zero open
required-human-decisions, each line traceable to its source.

### 7. FILL the template
Render `templates/pr-readiness-report.md` with the six fields -- `merge_ready`,
`blockers[]`, `warnings[]`, `required_human_decisions[]`, `evidence[]`, one `next_action`
-- each finding carrying its cited source. Add no seventh field, no summary, no score.

### 8. STOP -- report and recommend, take no action
Emit the verdict EPHEMERALLY to the operator and recommend the single `next_action` a
HUMAN should take. Take no action on the PR: no merge, no approve, no thread resolution,
no commit / PR-body edit, no stage move. The verdict is rendered, never committed.

## Principle-V required_human_decisions[] (surface, never resolve)

Each is a HUMAN judgment call. The module RECOMMENDS; the named owner DECIDES. Each routes
to a named owner; an item with no named owner is shown `UNASSIGNED` and flagged. An open
required-decision gates `merge_ready: yes`. The module never rules, self-resolves, or
self-assigns.

| Trigger | Action | Owner |
|---------|--------|-------|
| Publish / merge-to-publish requested before the required prior stage is `pass` | record a `required_human_decision`, set `merge_ready: no`; never approve the publish or move the stage | named publish owner |
| A PII publish-safety question | route to governance sign-off; never declare a column publish-safe | governance |
| A grain ambiguity / sentinel-vs-null choice | surface; never auto-pick a grain or a sentinel | analyst |
| A business rollup / segment mapping the analyst has not supplied | surface; never invent the mapping | analyst |
| Any request to "approve and merge this PR" or "mark this stage `pass`" | DECLINE; state it is read-only and cannot create truth (F024 / Principle V); return the verdict for a human to act on | human |

## No fake confidence (the guardrail)

If asked for "a merge-readiness score 0-100", "how confident are you", or "one health
number", DECLINE: cite no-fake-confidence (rule #9) and return the boolean `merge_ready`
plus the explicit `blockers[]` / `warnings[]` / `required_human_decisions[]` with their
cited sources. A PR verdict is exactly where a tidy invented score is tempting; it is
forbidden.

## Decline-to-act (read-only proof)

Asked to merge, approve, submit a review, resolve / reply to a thread, edit the PR body,
push a commit, or mark a stage `pass`, the skill DECLINES, states it is read-only and
cannot create truth (F024 Core Authority; Principle V), and returns the verdict for a human
to act on. After a run, GitHub state is unchanged (no merge, no review, no resolved thread,
no edited body) and `git status` shows no modified `mappings/<table>/` evidence -- the skill
observed and reported only. Run on its own PR, it reviews it like any other and cannot
self-approve.

## Honest-state rules (never invent, never silently re-run)

| Situation | What the reviewer does |
|-----------|------------------------|
| The PR touches no readiness artifact | record the readiness lines `unknown` / "not applicable"; do NOT fabricate a stage or a verdict |
| A referenced `readiness-status.yaml` / `source-map.yaml` is absent | record the line `unknown` naming the missing source; do NOT assume `pass` |
| A required CI check is queued / in-progress | report `pending` (a blocker for `merge_ready: yes`); do NOT re-trigger or wait on CI itself |
| Two sources disagree (PR body says stage `pass`; `readiness-status.yaml` shows `blocked` with an open reason) | SURFACE the conflict as a finding; do NOT resolve it by choosing one (Principle V) |
| A secret-shaped string in the diff | flag as a blocker AND recommend the STOP-rotate-sweep posture; report the location but do NOT edit or remove it (read-only) |
| A `required_human_decision` whose owner is not named | show owner `UNASSIGNED` and flag it; never self-assign or self-resolve |

## See also

- The output shape: `../../../templates/pr-readiness-report.md`; the tool doc (when to
  run, field meanings, the gating rule): `../../../docs/tools/pr-readiness-reviewer.md`.
- The authority category it declares: `../../../docs/architecture/product-modules.md`
  (Product Module / `read-only`; the matrix, the two sub-vocabularies); the copy-me
  declaration it fills: `../../../templates/module-contract.md`; the seam (Module vs
  Adapter): `../../../docs/architecture/core-vs-modules-and-adapters.md`.
- The committed evidence it reads (inputs, unchanged): `../../../templates/readiness-status.yaml`
  (`current_stage`, per-stage `status`, `approvals[]`, `blocking_reasons[]`),
  `../../../templates/source-map.yaml` approval metadata.
- The closest read-only sibling: `.claude/skills/retail-control-room/SKILL.md` (F012, the
  portfolio roll-up); the invoke-and-interpret sibling: `.claude/skills/retail-validate/SKILL.md`.
- The model + no-fake-confidence rule: `../../../docs/readiness/readiness-model.md`; the
  stage sequence: `../../../docs/readiness/readiness-pipeline.md`.
- The gates it reads (never re-runs as a new check): the `retail-govern` / `retail check`
  static surface, the `retail-validate` / `retail validate` live surface.
- The roadmap row + hard rules: `../../../docs/roadmap/roadmap.md` (F025, cross-cutting;
  #7 / #8 / #9); Principles V, VII, VIII, IX. A filled worked example lives under
  `../../../docs/worked-examples/`.

## Orchestration

When a table is driven end-to-end, the `retail-orchestrate` conductor may invoke this
reviewer as the pre-merge READ on the PR that would advance a stage -- to assemble the
merge checklist in one place before a human approves and merges. This skill reads state and
reports; it advances no stage, clears no blocker, grants no approval, and merges nothing.
The merge and the approval stay the named human's action; the self-heal loop and any
per-table fix live in `retail-orchestrate` / the per-table owner, never here.
