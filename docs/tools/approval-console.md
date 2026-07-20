# Approval Console -- operator guide

- **Roadmap feature:** F027.  **On-disk spec:** `specs/021-approval-console/`. When the
  spec-dir number (021) and the roadmap F-number (F027) disagree, the roadmap F-number
  wins: this is F027.
- **Authority category:** Product Module / `artifact-writing` (the first concrete Product
  Module realized under F024; see `docs/architecture/product-modules.md`).
- **Status:** Runtime slice shipped for the read-only inbox: `retail approvals`
  lists missing/invalid approval seams. Decision packaging/write-back remains the
  agent-led artifact-writing workflow described below.

## Purpose

The kit STOPS at judgment calls (Principle V) and the readiness spine RESERVES the slot
for the answer: `readiness-status.yaml` carries `approvals[]` (stage + owner + at) and the
per-table `unresolved-questions.md` carries the Open-questions table whose `Resolution`
column is the agreed answer + date + who. What the kit lacked is the LOOP between "a
question was raised" and "the named human's answer is recorded in the committed artifacts".
The Approval Console is that loop, made explicit and reviewable. An approval that lives only
in chat is not an approval -- it cannot be reviewed, advance a gate, or be audited later.

It does two things and only two:

1. **Package** a raised judgment call into a reviewable DECISION PACKAGE -- a filled
   `templates/approval-request.md`.
2. **Record** the named human's answer back into the committed artifacts -- a filled
   `templates/approval-decision.md` plus the write-through into `unresolved-questions.md`
   and `readiness-status.yaml`.

## Read-only inbox

```bash
retail approvals
retail approvals --format json
```

The inbox scans committed `mappings/*/readiness-status.yaml` files and reports
approval seams that are blocked on review, missing a shape-valid named-human
approval, or carrying an invalid owner such as a bare role token. It writes
nothing and does not record a decision; use the request -> decision workflow
below when a named human has actually answered.

## The transcribe-never-author boundary (the load-bearing rule)

> The console TRANSCRIBES a human decision and WRITES it into the committed artifacts; it
> does NOT pick the option, supply or forge the owner, invent the rationale, auto-accept a
> recommended default, or move a readiness stage to `pass` without the stage's required
> evidence AND a named human approval. The named human decides; the console records. If no
> human answer exists, there is nothing to record and the request stays open.

The console WRITES into Core-Authority artifacts, which is exactly where an agent is tempted
to self-approve or upgrade a stage. It stays a Product Module precisely because it only
TRANSCRIBES a human decision and only writes that already-made grant through -- it is the
EXECUTOR of an approved step, not a discretionary approver. Creating truth (defining a
metric/mapping, approving a stage) belongs to the named human via Core Authority alone
(`docs/architecture/core-vs-modules-and-adapters.md`).

## The request -> decision loop

```text
raised judgment call            named human answers              committed artifacts
(unresolved-questions.md row, ->  approval-request.md      ->     approval-decision.md  ->  unresolved-questions.md (Resolution + answered)
 F008 grain stop, F012 blocker)   (the decision package)         (recorded FIRST)          readiness-status.yaml  (approvals[] entry; pass only if gated)
```

1. A judgment call is raised (an open `unresolved-questions.md` row, a grain-confidence
   stop from F008, an open blocker the F012 control room lists, or a metric-contract open
   question from F009).
2. The console packages it into a filled `approval-request.md`: `question_id`, `stage`,
   `subject`, `decision_needed`, `evidence` (measured numbers + committed source paths),
   `options`, `impact`, `recommended_default` (optional), `owner_required`, and
   `artifacts_to_update_after_decision`. No `selected_option` -- a request never answers
   itself.
3. A NAMED HUMAN of the matching authority class answers.
4. The console records `approval-decision.md` FIRST (the durable record), then applies both
   write-throughs idempotently (see "Write order + missing targets").

## The four authority classes (the decider must match the question)

| Class | Decides | Question examples |
|-------|---------|-------------------|
| **analyst** | business meaning / grain / rollups | a business-rollup mapping, a grain ambiguity |
| **governance** | PII / publish-safety sign-off | whether a PII-derived column is safe to publish |
| **data-owner** | source semantics / upstream truth | which source column authoritatively marks a return |
| **metric-owner** | metric contracts | the intent/binding of one metric (F009) |

The decider's class MUST match the question class (FR-009). A decision recorded under the
wrong class -- e.g. a PII publish-safety call signed by an analyst rather than governance --
is REFUSED, and the console names the required authority class.

### metric-owner is an additive extension (not yet in the base template)

The base `unresolved-questions.md` template carries only THREE classes -- analyst,
governance, data-owner. `metric-owner` is an ADDITIVE extension class drawn from F009 metric
contracts. The console uses it ONLY for a metric-contract question and treats it as
not-yet-present in the base `unresolved-questions.md` template. The console never silently
renames or collapses the existing three classes.

### Serialization: each target's own spelling (verbatim, asymmetric)

When the recorded decision is written back, the console uses each TARGET artifact's existing
spelling verbatim:

| Target artifact | Field | Spelling used |
|-----------------|-------|---------------|
| `readiness-status.yaml` | `approvals[].owner` | `data_owner` (underscore) |
| `unresolved-questions.md` | "Who must answer" cell | `data-owner` (hyphen) |

analyst and governance are spelled identically in both targets; only the data-owner class
differs by target. `metric-owner` has no base `readiness-status.yaml` spelling to copy (it
is additive, from F009), so it serializes as-written -- `metric-owner` -- in both targets.
The console never renames or collapses the three classes the base `unresolved-questions.md`
template already carries.

## How a recorded decision maps to the committed artifacts

A recorded `approval-decision.md` is written through to the artifacts named in the request's
`artifacts_to_update_after_decision`. At minimum:

- **`unresolved-questions.md`** -- the matching row's `Resolution` cell is filled (the
  decision + date + owner) and its `Status` is flipped `open` -> `answered`. Answered rows
  are never deleted (the audit trail).
- **`readiness-status.yaml`** -- an `approvals[]` entry is appended: `stage`, `owner`
  (serialized `data_owner` where applicable), and `at` (populated from the decision's
  `date`).

No approval may live only in chat: until the write-back lands in a committed artifact, the
approval is treated as NOT recorded.

## The `pass`-needs-approval-AND-evidence rule

A readiness stage flips to `pass` ONLY when BOTH already exist:

1. a NAMED HUMAN approval (the recorded decision -- owner + date), AND
2. the stage's OWN required evidence (e.g. the live `retail validate` result for Gold Ready;
   the PBIP model + metric contracts for Semantic Model Ready).

The flip is MECHANICAL -- the console executes an already-made, already-evidenced decision;
it never grants the approval. If either is absent, the decision is recorded and the stage
stays as it was, with the gap listed in the decision's `remaining_blockers`. The console MUST
NOT move a stage to `pass` without the required evidence AND a named human approval.

`remaining_blockers` is EXACTLY why a recorded decision does NOT always mean the stage is
`pass`.

## Write order + missing targets (idempotent, never partial)

The console records `approval-decision.md` FIRST (the durable record), then applies BOTH
write-throughs idempotently. If a target artifact is MISSING or unwritable, the console
records the decision with a `remaining_blockers` entry NAMING the missing target and does NOT
fabricate it or perform a partial stage flip. A `pass` flip occurs ONLY after BOTH
write-throughs land alongside the stage's required evidence.

## The guards (what the console refuses)

- **No self-approval / no self-grant.** Asked to "just approve it", to pick the option, to
  supply the owner, or to flip a stage to `pass` without a named human answer AND the
  required evidence, the console DECLINES, cites Principle V + the Core-Authority rule, and
  returns the open request unchanged (no artifact altered).
- **No auto-accepted default.** Accepting a `recommended_default` is STILL a decision and is
  recorded as an explicit named-owner decision (owner + date + rationale) -- never a silent
  auto-accept on the human's behalf.
- **No fabricated confidence.** A request and a decision carry explicit status + evidence +
  blockers ONLY -- never a numeric health/confidence score (hard rule #9). Asked to score a
  decision's confidence, the console declines and cites the no-fake-confidence rule.
- **Conflicts surfaced, never buried.** A new decision that contradicts a prior recorded
  approval is SURFACED as a finding; the prior approval is never silently overwritten. A new
  decision on an already-`pass` stage is recorded as an AMENDMENT and surfaced for review.
- **Owner left blank** -> recorded `UNASSIGNED` and NOT a valid approval; never self-assigned.
- **Phantom question** -> a decision requires a matching request `question_id`; the console
  does not record against a question never packaged.
- **Duplicate `question_id`** -> surfaced as a `remaining_blockers` line on the request side;
  the console DECLINES to create a second decidable request, treating the one existing
  request as authoritative.

## Relationship to shipped features

| Feature | What it does with judgment calls | What the console adds |
|---------|----------------------------------|-----------------------|
| F005 Retail Readiness Model | DEFINES the `approvals[]` slot + four statuses | FILLS `approvals[]` from a named human decision |
| F006 Table Onboarding Wizard | RAISES open questions into `unresolved-questions.md` | packages a row into a request, records the answer back |
| F008 Grain Confidence Reviewer | SURFACES a grain-ambiguity stop | turns the stop into a decision package + records the resolution |
| F012 Data Quality Control Room | READ-ONLY roll-up listing open blockers + owners | the action the control room points at: records the clearing decision |
| F009 Metric Contracts | DEFINES a metric (intent + binding) | packages a metric-contract open question; uses the `metric-owner` class |

The console adds no new validator and no new gate. It is the missing write-back loop.

## What this tool does NOT do (the scope wall)

- It does NOT decide, self-approve, or self-grant a stage.
- It does NOT auto-accept a recommended default.
- It does NOT emit a numeric confidence/health score (hard rule #9).
- It adds NO `seshat check` rule, NO CLI verb, NO Python, NO DB connection, NO Power BI
  execution (that is F016, parked). The agent is the runtime.
- It inlines NO C086 / pharmacy specifics; C086 is cited as a filled instance only
  (Principle VII).

## Deferred

- A machine-readable request/decision queue (an `approvals/<question_id>.yaml` store + an
  index) -- deferred until request volume warrants it.
- A `retail approve` CLI / programmatic recorder -- deferred (still no deciding, no new gate).
- Notification / routing of a request to its owner -- the request names the owner authority,
  but delivery to a specific person is out of scope (no runtime).
- A numeric decision-confidence score -- deferred (hard rule #9).

## See also

- The verb: `.claude/skills/approval-console/SKILL.md`.
- The output shapes: `templates/approval-request.md`, `templates/approval-decision.md`.
- The slot this fills: `templates/readiness-status.yaml` (`approvals[]`),
  `templates/unresolved-questions.md` (Open-questions + Resolution).
- The model + no-fake-confidence rule: `docs/readiness/readiness-model.md`; the stage
  sequence: `docs/readiness/readiness-pipeline.md`.
- The category it realizes: `docs/architecture/product-modules.md` (F024),
  `docs/architecture/core-vs-modules-and-adapters.md` (the Core-vs-Module boundary), and the
  copy-me declaration `templates/module-contract.md`.
- The conductor it plugs into: `.claude/skills/retail-orchestrate/SKILL.md`.
- The constitution: Principle V (stop-and-ask), VII (generic), VIII (static-first), IX
  (ASCII / no BOM).
- A filled worked example (cited, never inlined): a worked example under `docs/worked-examples/`.
