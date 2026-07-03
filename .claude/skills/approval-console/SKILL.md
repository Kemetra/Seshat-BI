---
name: approval-console
description: >-
  Package a raised judgment call into a reviewable DECISION PACKAGE (a request),
  then RECORD the named human's answer back into the committed artifacts (a
  decision) for the Seshat BI repo. Use when someone asks to "package this open
  question for sign-off", "record the analyst's decision", "write the approval
  into the readiness file", or "close this blocker now that the owner answered".
  Product Module / artifact-writing: it WRITES the recorded human decision into
  unresolved-questions.md (Resolution + answered status) and readiness-status.yaml
  (an approvals[] entry) -- but it only TRANSCRIBES a decision a named human
  supplied. It NEVER picks the option, supplies/forges the owner, invents the
  rationale, auto-accepts a recommended default, or moves a stage to `pass` without
  the stage's required evidence AND a named human approval. It emits NO numeric
  confidence/health score (hard rule #9), runs NO validator, opens NO DB connection,
  and adds NO `retail check` rule. F027 is the first concrete Product Module under F024.
---

# approval-console

- **Roadmap feature:** F027.  **On-disk spec:** `specs/021-approval-console/`. When the
  spec-dir number (021) and the roadmap F-number (F027) disagree, the roadmap F-number
  wins: this is F027.

The kit STOPS at judgment calls (Principle V) and the readiness spine RESERVES the slot
for the answer (`readiness-status.yaml` `approvals[]`; the `unresolved-questions.md`
Open-questions `Resolution` column). What it lacks is the LOOP between "a question was
raised" and "the named human's answer is recorded in the committed artifacts". This skill
is that loop, and only that loop. It does two things: (1) packages a raised judgment call
into a reviewable DECISION PACKAGE (a request), and (2) once a named human answers,
RECORDS that decision back into the committed artifacts. An approval that lives only in
chat is not an approval -- it cannot be reviewed, advance a gate, or be audited.

## Authority declaration (F024 module contract -- filled)

- **Authority category:** Product Module
- **Capability level:** `artifact-writing`  *(exactly one)*
- **Product layer:** 1-6  *(all stages -- the functional axis; orthogonal to category)*
- **Roadmap feature:** F027  **On-disk spec:** `specs/021-approval-console/`
- **Owner:** the named human who decides each judgment call (the console transcribes; it is never the owner)
- **Status:** Authored (skill + two templates + one docs page; no runtime code)

### What it does (one line)

> Consumes a raised judgment call + a named human's answer, and WRITES the transcribed
> decision through to the committed `unresolved-questions.md` Resolution + the
> `readiness-status.yaml` `approvals[]` slot -- it never authors the decision itself.

### Core Authority it READS

- `mappings/<table>/unresolved-questions.md` -- the Open-questions row a request packages
  (the question, why it blocks, the "Who must answer" authority class, the proposed default).
- `mappings/<table>/readiness-status.yaml` -- per-stage `status`, the stage's recorded
  `evidence[]`, the existing `approvals[]` entries (to detect a contradicting prior approval).
- the surfacing features' evidence: a grain-confidence stop (F008), an open blocker the
  control room lists (F012), a metric contract's open question (F009) -- the inputs to a request.

### Derived evidence it WRITES

- `templates/approval-request.md` (filled) -- the decision package; poses a decision, never answers it.
- `templates/approval-decision.md` (filled) -- the transcribed human answer (written FIRST, the durable record).
- `mappings/<table>/unresolved-questions.md` -- the matching row's `Resolution` cell + `Status` flipped `open` -> `answered`.
- `mappings/<table>/readiness-status.yaml` -- an `approvals[]` entry (`stage` + `owner` + `at`); and,
  ONLY when gated (see below), a stage `status` flipped to `pass`.

Every written cell is a TRANSCRIPTION of the human's answer or a copy of a committed
source path -- it is DERIVED evidence, never a new approval the console authored and never
a new metric/mapping definition.

### Approved step it EXECUTES

- **none.** This is an `artifact-writing` module, not `execution-capable`. The `pass`-flip
  is a GATED WRITE of transcribed evidence (the `approvals[]` entry + the stage `status`
  field), not an execution-capable local step. The console opens no DB connection, runs no
  validator, and publishes nothing.

### Forbidden operations (the matrix says NO)

- MUST NOT pick `selected_option`, supply/forge `owner`, or invent `rationale` (no deciding).
- MUST NOT auto-accept `recommended_default` -- an accepted default is an explicit named-owner decision.
- MUST NOT move a readiness stage to `pass` without the stage's required evidence AND a named human approval.
- MUST NOT record a decision under an authority class that does not match the question class.
- MUST NOT silently overwrite a prior recorded approval -- it surfaces the conflict.
- MUST NOT create truth: no defining business meaning, no approving a metric/mapping (Core Authority / named human only).
- MUST NOT connect to a DB / external service, and MUST NOT publish a Power BI artifact (that is an Execution Adapter).
- MUST NOT emit a numeric / maturity / confidence score (hard rule #9).
- MUST NOT add a `retail check` rule, a CLI verb, or Python.

### How it handles a missing input

When a required Core Authority input is absent (no human answer, a missing write-back
target, missing stage evidence, a phantom `question_id`, a duplicate `question_id`), the
console SURFACES it as a blocker and stops -- it never fabricates the input, self-approves,
or proceeds past the missing gate (Principle V; stop-and-ask). See the procedure below.

## The transcribe-never-author boundary (read first)

> The console TRANSCRIBES a human decision and WRITES it into the committed artifacts; it
> does NOT pick the option, supply or forge the owner, invent the rationale, auto-accept a
> recommended default, or move a readiness stage to `pass` without the stage's required
> evidence AND a named human approval. The named human decides; the console records. If no
> human answer exists, there is nothing to record and the request stays open.

This is the single load-bearing rule. A module that WRITES into Core-Authority artifacts is
exactly where an agent is tempted to self-approve or upgrade a stage; both are forbidden and
hard-stop. The console is the EXECUTOR of an already-made decision, not a discretionary
approver (the architectural Core-Authority rule; `docs/architecture/product-modules.md`).

## Readiness vocabulary (fixed; no score)

The four statuses ONLY: `not_started` | `blocked` | `warning` | `pass`, plus `evidence[]`
+ `blocking_reasons[]`. There is NO numeric / health / confidence score field anywhere
(hard rule #9). A `pass` is the named-owner approval recorded as evidence (owner + date),
never a number. A stage flips to `pass` ONLY when BOTH a named human approval AND the
stage's required evidence already exist (the `pass`-flip rule).

## The four authority classes (the decider must match the question)

- **analyst** -- business meaning / grain / rollups
- **governance** -- PII / publish-safety sign-off
- **data-owner** -- source semantics / upstream truth
- **metric-owner** -- metric contracts (an ADDITIVE extension class from F009 metric
  contracts; NOT present in the base `unresolved-questions.md` template -- used ONLY for a
  metric-contract question; documented as not-yet-present in `docs/tools/approval-console.md`)

**Serialization (verbatim per target).** When the decision is written back, the console
records the DECIDER, not just the authority class, so the named-human guarantee is
auditable from committed evidence (audit C4): `readiness-status.yaml` `approvals[].owner`
holds the person's NAME followed by the authority class in parentheses --
`"<Person Name> (<analyst | governance | data_owner | metric_owner>)"` (e.g.
`"Ahmed Shaaban (data_owner)"`). The `unresolved-questions.md` "Who must answer" cell keeps
the role token in that artifact's existing spelling (`analyst` / `governance` / `data-owner`),
and the matching `Resolution` records the person + date. A bare role token with no person in
`approvals[].owner` is a defect -- an approval must trace to a named human, never a role alone.

## The procedure

### 1. Package a raised judgment call into a request (US1)

Render `templates/approval-request.md` from ONE open judgment call. Fill `question_id`
(matching the source row), `stage`, `subject`, `decision_needed` (one sentence), `evidence`
(measured numbers + the committed source path each was read from), `options`, `impact` (per
option), `recommended_default` (only if the source carries one traceable to a committed
source -- else omit; mark it NOT auto-accepted), `owner_required` (the question's authority
class), and `artifacts_to_update_after_decision`. Record NO `selected_option` -- a request
never answers itself. If a required number is not yet measured, record
`evidence incomplete: <source>` and do NOT invent it.

**Duplicate guard.** A `question_id` resolves to exactly ONE request. If the same
`question_id` is packaged twice, surface the duplicate as a `remaining_blockers` line on the
request side and DECLINE to create a second decidable request -- the one existing request is
authoritative (never create a second decidable copy).

### 2. Transcribe the named human's answer + write it through (US2)

On a named human's answer, render `templates/approval-decision.md` FIRST (the durable
record): `selected_option`, `owner`, `date`, `rationale` -- each TRANSCRIBED from the human,
none fabricated; a field the human did not supply is left unfilled. Then apply BOTH
write-throughs idempotently:

- `unresolved-questions.md`: fill the matching row's `Resolution` (decision + date + owner)
  and flip `Status` `open` -> `answered`.
- `readiness-status.yaml`: append an `approvals[]` entry -- `stage` + `owner` (the
  DECIDER by name + authority class, e.g. `Ahmed Shaaban (data_owner)`; never a bare
  role token) + `at` (populated from the decision's `date`).

If a target artifact is MISSING or unwritable, record the decision with a
`remaining_blockers` entry naming the missing target and do NOT fabricate it or perform a
partial stage flip. A `pass` flip occurs ONLY after BOTH write-throughs land alongside the
stage's required evidence.

**The `pass`-flip rule.** Flip the stage `status` to `pass` ONLY when BOTH already exist: the
named human approval (this decision) AND the stage's own required evidence (e.g. the live
`retail validate` result for Gold Ready). Otherwise record the decision and leave the stage
unchanged, with the gap in `remaining_blockers`. The flip is mechanical -- the console
executes an already-made decision; it never grants one.

### 3. Refuse to decide; surface conflicts (US3)

- **Asked to "just approve it" / pick the option / supply the owner / flip a stage to `pass`
  without a named human answer AND the required evidence:** DECLINE, cite Principle V
  (stop-and-ask) and the Core-Authority rule, and return the open request unchanged (no
  artifact altered).
- **A decision recorded under the WRONG authority class** (e.g. a PII publish-safety call
  recorded by an analyst, not governance): refuse to record it and NAME the required
  authority class.
- **A new decision that CONTRADICTS a prior recorded `approvals[]` entry:** SURFACE the
  conflict as a finding; do NOT silently overwrite the prior approval.
- **An owner left blank:** record owner `UNASSIGNED` and refuse to treat the decision as a
  valid approval; never self-assign the owner.
- **A decision for a question never packaged:** require a matching request `question_id`; do
  not record against a phantom question.
- **A stage already `pass`:** record a new decision as an AMENDMENT with its own
  `approvals[]` entry and surface it for review -- never a silent re-pass.

## No fake confidence (the guardrail)

If asked to "score this decision's confidence" or "give a readiness number", DECLINE: cite
the readiness-model "No fake confidence" rule (hard rule #9) and return the four explicit
statuses + the recorded evidence + blockers with their source paths instead. A numeric score
is OPTIONAL and DEFERRED; the console MUST NOT emit one.

## Honest-state rules (never invent, never silently re-run)

| Situation | What the console does |
|-----------|------------------------|
| Answer lives only in chat | treats the approval as NOT recorded; the request stays open until the write-back lands |
| A write-back target is missing/unwritable | records the decision, names the missing target in `remaining_blockers`, performs NO partial `pass` flip |
| Stage evidence absent (approval present) | refuses the `pass` flip, lists the missing evidence as a remaining blocker |
| Same `question_id` packaged twice | surfaces the duplicate as a `remaining_blockers` line, declines a second decidable request |
| Decision under the wrong authority class | refuses to record it, names the required class |
| New decision contradicts a prior approval | surfaces the conflict as a finding; does NOT overwrite |
| Owner left blank | records `UNASSIGNED`, not a valid approval; never self-assigns |
| recommended_default with no traceable source | omits the default rather than inventing one |

## See also

- The output shapes: `templates/approval-request.md`, `templates/approval-decision.md`.
- The operator guide + the boundary: `docs/tools/approval-console.md`.
- The slot this fills: `templates/readiness-status.yaml` (`approvals[]`: stage / owner / at)
  and `templates/unresolved-questions.md` (Open-questions table + Resolution column).
- The model + no-fake-confidence rule: `docs/readiness/readiness-model.md`; the stage
  sequence: `docs/readiness/readiness-pipeline.md`.
- The features that produce request inputs: F006 (onboarding), F008 (grain confidence),
  F012 (control room), F009 (metric contracts).
- The category it realizes: `docs/architecture/product-modules.md` (F024; Product Module /
  `artifact-writing`) and the Core-vs-Module authority boundary
  (`docs/architecture/core-vs-modules-and-adapters.md`); the copy-me declaration:
  `templates/module-contract.md`. A filled instance is cited under
  `docs/worked-examples/`.
- The constitution: Principle V (stop-and-ask), VII (generic), VIII (static-first), IX
  (ASCII / no BOM).

## Orchestration

When tables are driven end-to-end, the `retail-orchestrate` conductor may invoke the console
when a raised judgment call BLOCKS the next stage: the console packages the request, and --
once a named human answers -- records the decision and reports. It does NOT advance any stage
beyond the mechanical `pass` flip of an already-approved, already-evidenced step (the
`pass`-flip rule). The decision itself stays a named-human action; the conductor routes to
the console, the console transcribes, and the named human decides -- never the conductor and
never the console (`.claude/skills/retail-orchestrate/SKILL.md`).
