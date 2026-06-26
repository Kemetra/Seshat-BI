# Feature Specification: Approval Console -- the human-in-the-loop decision package + decision recorder

**Feature Branch**: `021-approval-console`  **Roadmap feature**: F027
(Numbering note: the roadmap F-number is the authoritative identity; the spec-dir
number is the next free on-disk slot. Here the on-disk dir is `021-approval-console`
and the roadmap feature is F027. When the dir number and the F-number disagree, the
roadmap F-number wins: this is F027.)

**Created**: 2026-06-25

**Status**: Shipped (approval-console skill landed; spec authored no runtime Python by design)

**Input**: "A Product Module for human-in-the-loop decisions. It turns an agent's
judgment-call question into a reviewable DECISION PACKAGE (a request), then RECORDS the
named human's answer back into the right committed artifacts (a decision). It is the
operational realization of Principle V (stop-and-ask) and of the `approvals[]` field in
`readiness-status.yaml` + the Open-questions table in `unresolved-questions.md`. It
TRANSCRIBES the human's decision; it never authors the decision, never self-approves,
and cannot move a stage to `pass` without the required approval AND evidence. Pure
skill + two templates + one docs page; no Python, no CLI, no new `retail check` rule.
Generic (#7); no fabricated confidence number (#9); ASCII + UTF-8 no BOM (Principle IX)."

## Clarifications

### Session 2026-06-26

- Q: When the console writes the authority class into the committed artifacts, which vocabulary does it use, and what about the fourth class (metric-owner)? -> A: Write each target's existing vocabulary verbatim -- `data_owner` (underscore) into `readiness-status.yaml` `approvals[].owner`, and `data-owner` (hyphen) into the `unresolved-questions.md` "Who must answer" cell, exactly as each template already spells it. The base `unresolved-questions.md` template carries only three classes (analyst / governance / data-owner); `metric-owner` is an ADDITIVE extension class (from F009 metric contracts) the console uses ONLY for a metric-contract question, documented in the docs page as not-yet-present in the base template -- the console never silently renames or collapses the existing three.
- Q: Where does the console report a duplicate-`question_id` defect (the same question packaged twice)? -> A: Surface it as a `remaining_blockers` line on the request side and DECLINE to create a second decidable request for that `question_id`; the one existing request is authoritative (surface the conflict, never create a second decidable copy).
- Q: If only one of the two write-back targets (`unresolved-questions.md`, `readiness-status.yaml`) is present/writable when recording a decision, what does the console do? -> A: Record the `approval-decision.md` first (the durable record), then apply both write-throughs idempotently; if a target artifact is missing, record the decision with a `remaining_blockers` entry naming the missing target and do NOT fabricate it or perform a partial stage flip. A `pass` flip happens only after BOTH write-throughs land alongside the required evidence.

## Why this feature exists

The kit already STOPS at judgment calls. Principle V requires the agent to raise -- and
never silently resolve -- business-rollup/segment mappings, PII publish-safety, grain
ambiguity, and sentinel-vs-null choices. The readiness spine already RESERVES a slot for
the answer: `readiness-status.yaml` carries `approvals[]` (stage + owner + at) and the
per-table `unresolved-questions.md` carries an Open-questions table whose `Resolution`
column is the agreed answer + date + who. The mapping gate, F008 (Grain Confidence),
and F012 (Data Quality Control Room) all SURFACE these blockers.

What the kit lacks is the operational LOOP between "a question was raised" and "the
named human's answer is recorded in the committed artifacts." Today that loop happens in
chat: the agent asks, the human replies, and unless someone manually edits
`unresolved-questions.md` and `readiness-status.yaml`, the decision evaporates. An
approval that lives only in chat is not an approval -- it cannot be reviewed, cannot
advance a gate, and cannot be audited later.

This feature is that loop, made explicit and reviewable. It does two things and only two:
(1) it packages a raised judgment call into a DECISION PACKAGE -- a request with the
question, the evidence, the options, the impact, the owner authority required, and the
exact artifacts to update once decided; and (2) once the named human answers, it RECORDS
that decision -- the selected option, the owner, the date, the rationale, the artifacts
updated, and any remaining blockers -- back into those committed artifacts. It is the
operational realization of Principle V and the write-back side of the `approvals[]` slot.

## What this feature is NOT (the scope wall)

This is the load-bearing constraint, stated up front so the spec cannot drift:

- **It does NOT decide.** The console TRANSCRIBES a decision the named human supplied; it
  never picks `selected_option`, never supplies or forges the `owner`, and never invents
  the `rationale`. The human chooses; the console records. If no human answer exists,
  there is nothing to record -- the request stays open.
- **It does NOT self-approve, and cannot self-grant a stage.** It MAY flip a readiness
  stage to `pass` ONLY mechanically -- as the executor of an already-made decision -- when
  BOTH the named human approval AND the stage's required evidence already exist. The
  forbidden line, verbatim: it MUST NOT move a readiness stage to `pass` without the
  required evidence AND a named human approval. It is an executor of an approved step, not
  a discretionary approver (Principle V; the architectural Core-Authority rule).
- **It does NOT auto-accept a recommended default.** `unresolved-questions.md` is explicit:
  accepting a proposed default "is still a decision and must be recorded by the owner."
  The console MUST NOT accept `recommended_default` on the human's behalf; an accepted
  default is recorded as an explicit decision by the named owner, exactly like any other.
- **It is NOT read-only (unlike F012).** It WRITES -- into `readiness-status.yaml`
  `approvals[]` and the `unresolved-questions.md` `Resolution` column and the enumerated
  `artifacts_to_update_after_decision`. It borrows F012's structure (pure skill +
  template, all-stages, conflict-surfacing) and F010's authoring posture, but its boundary
  is its own: it is the one module that writes the recorded human decision (never the
  decision itself).
- **No fabricated confidence number.** A request and a decision carry explicit status +
  evidence + blockers, never an invented health/confidence score (hard rule #9). Any
  numeric score is OPTIONAL and DEFERRED.
- **Generic.** No worked-example specifics (no billing codes, segments, PII column names,
  per-table grain keys). C086 is a filled instance cited as a reference, never baked in
  (Principle VII).

## Relationship to shipped features (scope delta)

F027 is the missing write-back loop. It adds no gate and duplicates none of these:

| Shipped feature | What it does with judgment calls / approvals | What F027 adds |
|-----------------|----------------------------------------------|----------------|
| F005 Retail Readiness Model | DEFINES the `approvals[]` slot (stage/owner/at) and the four statuses; states a `pass` needs evidence | F027 is the mechanism that FILLS `approvals[]` from a named human decision |
| F006 Table Onboarding Wizard | RAISES open questions into `unresolved-questions.md` during onboarding | F027 packages one of those rows into a request and records the answer back |
| F008 Grain Confidence + Mapping Diff Reviewer | SURFACES a grain-ambiguity judgment call as evidence; STOPS for the human | F027 turns that stop into a decision package and records the human's resolution |
| F012 Data Quality Control Room | READ-ONLY roll-up that LISTS open blockers + the owner who can clear them | F027 is the action the control room points at: it records the clearing decision |
| F013 BI Handoff Pack / F010 Semantic Model | depend on stages being `pass` with named approval evidence | F027 produces exactly that approval evidence, recorded, not chatted |

None of the shipped features RECORD the human's answer back into the committed artifacts.
F005 defines the slot; the surfacing features fill the request side's inputs; F027 is the
write-back loop that closes it. It introduces no new validator and no new gate.

## Relationship to F024 (dependency)

F027 is the FIRST concrete Product Module realized under F024's companion-tools / module
category. Per the architectural Core-Authority rule that binds all features in this
batch: a module may READ evidence, SUMMARIZE it, VISUALIZE it, write DERIVED evidence, or
EXECUTE an approved step -- it MUST NOT create truth. F027 is the cleanest test of that
rule because it writes INTO Core-Authority artifacts: it stays a module precisely because
it only transcribes a human decision and only executes an already-approved step. (F024's
internal artifact shapes are not assumed here; F027 cites F024 only for the module
category and the Core-vs-Module authority boundary.)

## Architecture (planning posture: pure skill + two templates + one docs page; no code)

Consistent with features 010/012/013: the console is **agent-procedure text**; the agent
is the runtime. Decision: **a pure skill plus two generic templates (a request and a
decision) plus one docs page; NO new Python, NO new `retail` subcommand, NO codegen, NO
new `retail check` rule** (Principle VIII; roadmap rule #8 -- docs/templates first).

Deciding reason: packaging a raised question and recording a human answer is read-and-
write over a handful of committed Markdown/YAML files -- exactly the authoring work the
agent already does for `source-map.yaml` and `unresolved-questions.md`. A `retail
approve` CLI would add the repo's first decision-writing command, would have to parse and
re-emit the readiness schema, and would risk becoming a self-approving surface -- the one
thing this feature must NOT be. The templates give the skill a stable, reviewable shape
for the request and the decision; the skill gives the agent the procedure to fill them
from a raised question and a named human's answer.

The four future deliverables this feature ENUMERATES (and does NOT create now):
`.claude/skills/approval-console/SKILL.md` (the verb), `docs/tools/approval-console.md`
(the operator guide + the transcribe-never-author boundary),
`templates/approval-request.md` (the decision-package shape), and
`templates/approval-decision.md` (the recorded-decision shape).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Package a raised judgment call into a decision request (Priority: P1)

The agent has raised a judgment call (e.g. a row in a table's `unresolved-questions.md`,
or a grain-confidence stop from F008, or an open blocker from F012). A human (or the
agent on their behalf) asks the console to package it. The console produces ONE decision
package -- a filled `approval-request.md` -- carrying: `question_id`, the affected
`stage`, the `subject` (source/table/report), the `decision_needed` in one sentence, the
`evidence` (measured numbers + source paths), the `options`, the `impact` of each, the
`recommended_default` (if the source carries one), the `owner_required` (the authority
class), and the `artifacts_to_update_after_decision`. No answer is chosen.

**Why this priority**: a reviewable request is the atomic unit of the whole loop -- without
it, a judgment call has no committed, decidable form. This is the MVP.

**Independent Test**: take a single open `unresolved-questions.md` row for a GENERIC table
and produce a filled `approval-request.md` whose every field is present, whose `evidence`
cites the committed source path it was read from, whose `owner_required` matches the
question class, and which records NO `selected_option` (the request never answers itself).

**Acceptance Scenarios**:

1. **Given** an open judgment-call row, **When** the console packages it, **Then** the
   resulting request carries question_id, stage, subject, decision_needed, evidence,
   options, impact, owner_required, and artifacts_to_update -- and no selected option.
2. **Given** a question whose source carries a proposed default, **When** the request is
   built, **Then** `recommended_default` records that default AND the request states the
   default is NOT auto-accepted -- accepting it is a decision the owner must record.
3. **Given** a judgment call with no measured evidence yet, **When** the console tries to
   package it, **Then** it records "evidence incomplete: <source>" and does NOT invent a
   number or an option (no fabricated confidence).

---

### User Story 2 - Record the named human's decision into the committed artifacts (Priority: P1)

A named human has answered a packaged request. The console records that answer as a
filled `approval-decision.md` carrying `selected_option`, `owner`, `date`, `rationale`,
`artifacts_updated`, and `remaining_blockers`; it then writes the decision through to the
committed artifacts named in the request: the `Resolution` column + `answered` status of
the `unresolved-questions.md` row, and an `approvals[]` entry (stage + owner + at) in
`readiness-status.yaml`. A stage status flips to `pass` ONLY when the approval AND the
stage's required evidence both already exist; otherwise the decision is recorded but the
stage stays as it was, with `remaining_blockers` listing why.

**Why this priority**: recording the answer is the point of the feature -- a packaged
request with no committed write-back is just a question that evaporates in chat.

**Independent Test**: given a packaged request and a human's answer (option + owner +
rationale), produce a filled `approval-decision.md` and the exact edits to
`unresolved-questions.md` (Resolution + status) and `readiness-status.yaml` (`approvals[]`
entry). Assert: the selected option equals the human's (never the console's), the owner is
the named human (never self-assigned), and the stage flips to `pass` ONLY if the required
evidence is present -- otherwise it stays put with `remaining_blockers` populated.

**Acceptance Scenarios**:

1. **Given** a human's answer to a packaged request, **When** the console records it,
   **Then** the `Resolution` cell and `answered` status of the matching
   `unresolved-questions.md` row are filled, and an `approvals[]` entry (stage + owner +
   `at`, where `at` is the decision date) is added to `readiness-status.yaml` -- transcribed
   from the human, nothing invented.
2. **Given** a decision whose stage still has open required evidence, **When** it is
   recorded, **Then** the decision is recorded with `remaining_blockers` listing the
   missing evidence and the stage is NOT moved to `pass`.
3. **Given** a decision that ACCEPTS the recommended default, **When** it is recorded,
   **Then** it is recorded as an explicit named-owner decision (owner + date + rationale),
   never as a silent auto-accept.
4. **Given** a recorded decision, **When** a reviewer reads it, **Then** every written cell
   traces to the human's answer or to a committed source path -- no field is fabricated.

---

### User Story 3 - The no-self-approval guard (Priority: P1)

The console refuses to be the decider. If asked to "just approve it", to pick the option,
to supply the owner, or to flip a stage to `pass` without a named human approval AND the
required evidence, it declines, cites Principle V (stop-and-ask) and the Core-Authority
rule, and returns the open request unchanged. It also refuses a decision recorded under
the WRONG authority class (e.g. a PII publish-safety call recorded by an analyst rather
than governance), and surfaces -- never silently overwrites -- a decision that contradicts
a prior recorded approval.

**Why this priority**: this is the constitutional guardrail. A console that WRITES into
Core-Authority artifacts is exactly where an agent is tempted to self-approve or to
upgrade a stage; both are forbidden and must hard-stop.

**Independent Test**: ask the console to approve a request with no named human answer;
assert it declines, cites Principle V + no-self-approval, and changes no artifact. Then
record a PII decision under an analyst owner; assert it refuses (governance authority
required). Then record a decision that contradicts a prior `approvals[]` entry; assert it
surfaces the conflict and does not overwrite.

**Acceptance Scenarios**:

1. **Given** a request with no human answer, **When** asked to approve it, **Then** the
   console declines, cites Principle V, and leaves the request open and every artifact
   unchanged (no self-approval).
2. **Given** a decision recorded under an authority class that does not match the question
   (e.g. PII signed by analyst, not governance), **When** the console validates it, **Then**
   it refuses to record it and names the required authority class.
3. **Given** a new decision contradicting a prior recorded approval, **When** the console
   processes it, **Then** it surfaces the conflict as a finding and does NOT silently
   overwrite the prior approval (surface conflicts, never bury them).
4. **Given** a request to flip a stage to `pass` with the approval present but required
   evidence absent, **When** the console processes it, **Then** it refuses the flip and
   lists the missing evidence as a remaining blocker.

### Edge Cases

- **An answer that lives only in chat**: until the decision is written into a committed
  artifact, the console treats the approval as NOT recorded; "the human said yes in chat"
  is not an approval. The request stays open until the write-back lands.
- **A question packaged twice**: the same `question_id` MUST resolve to one request; a
  duplicate is a defect the console flags -- it surfaces the duplicate as a
  `remaining_blockers` line on the request side and DECLINES to create a second decidable
  request, treating the one existing request as authoritative (it never creates a second
  decidable copy).
- **A decision for a question that was never packaged**: the console requires a matching
  request `question_id`; it does not record a decision against a phantom question.
- **A recommended_default with no source**: if the console cannot trace the default to a
  committed source, it omits the default rather than inventing one.
- **An owner left blank**: the console records owner "UNASSIGNED" and refuses to treat the
  decision as a valid approval; it never self-assigns the owner.
- **A stage already `pass`**: a new decision on a passed stage is recorded as an amendment
  with its own approval entry; the console surfaces it for review rather than silently
  re-passing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Plan (do NOT create) `.claude/skills/approval-console/SKILL.md` -- the
  console verb, ASCII + UTF-8 no BOM, valid frontmatter; NO new Python, NO new `retail`
  subcommand, NO codegen, NO new `retail check` rule.
- **FR-002**: Plan (do NOT create) `templates/approval-request.md` -- the generic
  decision-package shape carrying `question_id`, `stage`, `subject` (source/table/report),
  `decision_needed`, `evidence`, `options`, `impact`, `recommended_default` (optional),
  `owner_required` (authority class), and `artifacts_to_update_after_decision`.
- **FR-003**: Plan (do NOT create) `templates/approval-decision.md` -- the generic
  recorded-decision shape carrying `selected_option`, `owner`, `date`, `rationale`,
  `artifacts_updated`, and `remaining_blockers`.
- **FR-004**: Plan (do NOT create) `docs/tools/approval-console.md` -- the operator guide:
  the request->decision loop, the transcribe-never-author boundary, the four authority
  classes (analyst / governance / data-owner / metric-owner), the `pass`-needs-approval-
  AND-evidence rule, and how a recorded decision maps to `approvals[]` +
  `unresolved-questions.md` Resolution.
- **FR-005**: The console MUST TRANSCRIBE the human's decision only: it MUST NOT pick
  `selected_option`, MUST NOT supply or forge `owner`, and MUST NOT invent `rationale`. A
  field the human did not supply is left unfilled, never fabricated.
- **FR-006**: The console MUST NOT auto-accept `recommended_default`. Accepting a default
  is recorded as an explicit named-owner decision (owner + date + rationale), identical in
  rigor to any other recorded decision.
- **FR-007**: The console MAY flip a readiness stage to `pass` ONLY when BOTH a named human
  approval AND the stage's required evidence already exist. It MUST NOT move a stage to
  `pass` without the required evidence AND a named human approval (Core-Authority rule;
  Principle V).
- **FR-008**: A recorded decision MUST be written through to the committed artifacts named
  in `artifacts_to_update_after_decision`: at minimum the `Resolution` column + `answered`
  status of the matching `unresolved-questions.md` row, and an `approvals[]` entry (stage +
  owner + `at`, where `at` is populated from the decision's `date`) in
  `readiness-status.yaml`. No approval may live only in chat. The console records the
  `approval-decision.md` FIRST (the durable record), then applies both write-throughs
  idempotently; if a target artifact is missing or unwritable, it records the decision with
  a `remaining_blockers` entry naming the missing target and does NOT fabricate it or
  perform a partial stage flip -- a `pass` flip occurs only after BOTH write-throughs land
  alongside the stage's required evidence (FR-007).
- **FR-009**: The console MUST validate that the recording `owner` matches the question's
  authority class (analyst = business/grain/rollups; governance = PII/publish-safety;
  data-owner = source semantics; metric-owner = metric contracts). A decision recorded
  under the wrong authority is refused. When SERIALIZING the class into a committed
  artifact the console MUST use that target's existing vocabulary verbatim: `data_owner`
  (underscore) in `readiness-status.yaml` `approvals[].owner`, and `data-owner` (hyphen)
  in the `unresolved-questions.md` "Who must answer" cell -- it never silently renames or
  collapses the three classes the base `unresolved-questions.md` template already carries
  (analyst / governance / data-owner). `metric-owner` is an ADDITIVE extension class (from
  F009 metric contracts), used ONLY for a metric-contract question and documented in the
  docs page as not-yet-present in the base `unresolved-questions.md` template.
- **FR-010**: The console MUST surface -- never silently overwrite -- a decision that
  contradicts a prior recorded approval (conflict-surfacing, Principle V posture).
- **FR-011**: No fabricated confidence: a request and a decision carry explicit status +
  evidence + blockers, never a numeric health/confidence score (hard rule #9). If asked to
  score a decision's confidence, the console declines and cites the no-fake-confidence rule.
- **FR-012**: Evidence traceability: every `evidence` line in a request and every written
  cell in a decision MUST be attributable either to the named human's answer or to a
  committed source path. A value with no traceable origin is a defect.
- **FR-013**: All planned artifacts MUST be GENERIC -- no C086 / pharmacy specifics. C086
  may be CITED as the filled instance, never inlined (Principle VII).
- **FR-014**: Append an `## Orchestration` pointer so `retail-orchestrate` can invoke the
  console when a raised judgment call blocks the next stage; the console records the
  decision and reports, it does not advance any stage beyond the mechanical `pass` flip of
  FR-007.

### Key Entities

- **Approval request (decision package)**: the atomic decidable unit. Fields:
  `question_id`, `stage`, `subject` (source/table/report), `decision_needed`, `evidence`,
  `options`, `impact`, `recommended_default` (optional), `owner_required` (authority
  class), `artifacts_to_update_after_decision`. It poses a decision; it never answers it.
- **Approval decision (recorded answer)**: the transcribed human answer. Fields:
  `selected_option`, `owner`, `date`, `rationale`, `artifacts_updated`,
  `remaining_blockers`. `remaining_blockers` is exactly why a recorded decision does NOT
  always mean the stage is `pass`.
- **Authority class**: who may decide -- analyst (business meaning / grain / rollups),
  governance (PII / publish-safety), data-owner (source semantics / upstream truth), or
  metric-owner (metric contracts). The console matches the decider to the question class.
  The base `unresolved-questions.md` template carries the first three; `metric-owner` is an
  additive extension (F009) used only for metric-contract questions. The console serializes
  each class in the target artifact's own spelling (`data_owner` in `readiness-status.yaml`;
  `data-owner` in `unresolved-questions.md`); it never renames or collapses an existing class.
- **The console skill**: the read-and-write verb; the agent is the runtime. It packages
  requests and transcribes decisions; it never decides, never self-approves, never flips a
  stage to `pass` without approval AND evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A raised judgment call can be packaged into one `approval-request.md` with
  every required field present, `owner_required` matching the question class, and NO
  selected option -- verifiable by reading one filled generic request.
- **SC-002**: A named human's answer is recorded into a `approval-decision.md` AND written
  through to the matching `unresolved-questions.md` Resolution row and a
  `readiness-status.yaml` `approvals[]` entry -- with the selected option, owner, and
  rationale all transcribed from the human, none fabricated.
- **SC-003**: A request to self-approve (no named human answer) or to flip a stage to
  `pass` without the required evidence is DECLINED with the Principle V / Core-Authority
  rationale, and no artifact is changed -- demonstrating no-self-approval and no-self-grant.
- **SC-004**: 100% of planned artifacts are generic: a reader finds ZERO C086 / pharmacy
  specifics in any template, skill, or doc this feature plans (Principle VII).
- **SC-005**: Adding this feature adds no new `retail check` rule and keeps its
  exit code at 0 -- it ships no checker and no rule (Principle VIII).
- **SC-006**: Every cell of a request and a decision is traceable: a reviewer asking "where
  did this come from" gets either the human's answer or a committed source path, and finds
  no numeric confidence score anywhere (hard rule #9).

## Human approval boundary

The named human is the sole decider for every judgment call the console packages. The
console packages the request and TRANSCRIBES the human's answer; it never chooses the
option, supplies the owner, invents the rationale, accepts a default on the human's
behalf, or flips a stage to `pass` absent the required evidence AND a named approval. The
authority class (analyst / governance / data-owner / metric-owner) must match the question
class. This is the operational realization of Principle V.

## Allowed operations

- Package a raised judgment call into a filled `approval-request.md` (request side).
- Transcribe a named human's answer into a filled `approval-decision.md` (decision side).
- Write a recorded decision through to the committed artifacts named in the request: the
  `unresolved-questions.md` Resolution + `answered` status, and a `readiness-status.yaml`
  `approvals[]` entry.
- Flip a stage to `pass` mechanically ONLY when a named approval AND the required evidence
  both already exist (executor of an approved step).
- Surface conflicts (contradicting a prior approval; wrong authority class) for review.

## Forbidden operations

- Pick `selected_option`, supply/forge `owner`, or invent `rationale` (no deciding).
- Auto-accept `recommended_default` without a named-owner decision.
- Move a stage to `pass` without the required evidence AND a named human approval.
- Record a decision under an authority class that does not match the question.
- Silently overwrite a prior recorded approval.
- Emit a numeric health/confidence score (hard rule #9).
- Add a `retail check` rule, a CLI verb, Python, or any DB/Power BI execution.
- Inline C086 / pharmacy specifics into any generic artifact (Principle VII).

## Evidence required

- A request's `evidence` lines each cite a committed source path (and where applicable the
  row/line) for the measured numbers they carry.
- A decision's `owner` + `date` are the named human approval -- this IS the evidence that a
  stage may be `pass`. A `pass` with no `approvals[]` entry is a defect.
- A stage flip to `pass` requires, in addition, the stage's own required evidence already
  recorded (e.g. the live `retail validate` result for Gold Ready).

## Readiness stage affected

ALL stages. The console is the approval mechanism for every gate -- it packages and
records the human decision wherever a stage's gate requires a named approval (Source ->
Mapping -> Silver -> Gold -> Semantic Model -> Dashboard -> Publish). It advances no stage
on its own beyond the mechanical `pass` flip of an already-approved, already-evidenced step.

## Dependencies

- **Upstream**: F024 (the companion-tools / Product-Module category and the Core-vs-Module
  authority boundary F027 is the first concrete realization of); F005 (the readiness model:
  the `approvals[]` slot + four statuses this feature fills); the mapping-gate templates
  (`unresolved-questions.md`, `readiness-status.yaml`) it writes into.
- **Relates to**: F006 (raises questions), F008 (surfaces grain stops), F012 (lists open
  blockers + owners) -- all produce the inputs to a request; none records the answer back.
- **Downstream**: every stage's gate that requires a named approval consumes the
  `approvals[]` evidence this feature records; F013 (BI Handoff Pack) bundles it.

## Non-goals

- Any `retail check` rule, Python module, or CLI verb (Principle VIII; rule #8).
- Deciding any judgment call, picking an option, or self-approving (Principle V).
- Defining the business meaning of a metric/mapping/rollup (that is the human's decision;
  F007/F009 own the definition artifacts).
- Publishing Power BI or any execution (that is F016, parked).
- A numeric confidence/health score (DEFERRED; hard rule #9).
- Filling any artifact with C086 / pharmacy values (Principle VII).

## Assumptions

- Pure skill + two templates + one docs page; the agent is the runtime (same posture as
  features 010/012/013). No new Python, no `retail approve` CLI, no codegen (YAGNI).
- The artifacts the console writes into already exist as templates
  (`readiness-status.yaml` with `approvals[]`; `unresolved-questions.md` with the
  Open-questions table) and are the authoritative write targets; this feature consumes and
  appends to them, never redefines them.
- "Recorded" means written into a committed artifact; an answer in chat is not recorded.
- The four authority classes (analyst / governance / data-owner / metric-owner) match the
  existing `unresolved-questions.md` "Who must answer" classes plus the metric-owner from
  F009. Auto-adopted from the existing templates.
- C086 is cited as the filled instance, never inlined (Principle VII).

## Deferred decisions

- **A machine-readable request/decision queue** (e.g. an `approvals/<question_id>.yaml`
  store and an index): DEFERRED until request volume warrants it; until then requests and
  decisions are human-readable Markdown copied per question.
- **A numeric decision-confidence score**: DEFERRED (hard rule #9); the console emits
  explicit status + evidence + blockers only.
- **A `retail approve` CLI / programmatic recorder**: DEFERRED. If volume grows past hand-
  recording, a write-back recorder (still no deciding, still no new gate) could parse and
  append; a code surface change for a later slice.
- **Notification / routing of a request to its owner**: DEFERRED; the request names the
  owner authority, but delivery to a specific person is out of scope (no runtime).

## See also

- The slot this fills: `templates/readiness-status.yaml` (`approvals[]`: stage / owner /
  at) and `templates/unresolved-questions.md` (Open-questions table + Resolution column).
- The model + no-fake-confidence rule: `docs/readiness/readiness-model.md`; the stage
  sequence: `docs/readiness/readiness-pipeline.md`.
- The features that produce request inputs: F006 (onboarding), F008 (grain confidence),
  F012 (control room).
- The conductor it plugs into: `.claude/skills/retail-orchestrate/SKILL.md`.
- The constitution: Principle V (stop-and-ask), Principle VII (generic), Principle VIII
  (static-first), Principle IX (ASCII / no BOM); the Readiness System spine section.
- The category it realizes: F024 (companion tools / Product Module) and the Core-vs-Module
  authority boundary; `docs/roadmap/roadmap.md`.
