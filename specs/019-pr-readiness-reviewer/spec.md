# Feature Specification: PR Readiness Reviewer -- a read-only "is this PR safe to merge" verdict from PR + readiness evidence

**Feature Branch**: `019-pr-readiness-reviewer`

**Roadmap feature**: F025 (Product Module, read-only). Numbering note: the roadmap F-number is the authoritative identity; the spec-dir number (`019`) is the next free on-disk slot. This batch maps F024=018, **F025=019**, F026=020, F027=021, F028=022, F029=023, F030=024, F031=025, F032=026, F033=027. When the dir number and the F-number disagree, the roadmap F-number wins.

**Created**: 2026-06-25

**Status**: Shipped (pr-readiness-reviewer skill landed; spec authored no runtime Python by design)

**Input**: "A Product Module (read-only) that turns the manual PR review pattern into a repeatable skill. It reads one PR's state (open/draft/mergeable, CI/workflow conclusions, open review threads, unresolved Codex/GitHub review comments) and the committed readiness evidence (readiness-status.yaml, source-map approval metadata, declared-vs-run tests, no raw data / no secrets / no local paths) and emits a structured verdict: merge_ready (yes/no), blockers[], warnings[], required_human_decisions[], evidence[], next_action. It MUST distinguish blocker vs warning. It reports readiness from evidence only -- it CANNOT merge a PR, approve a PR, resolve a review thread, or move a readiness stage. Category per F024: Product Module, read-only. Generic (#7). No fake confidence (#9). Depends on F024."

## Clarifications

### Session 2026-06-25

- Q: Where does the rendered verdict go -- is it persisted as a committed/tracked repo file, or emitted ephemerally to the operator? -> A: Ephemeral -- the skill renders the verdict to the operator (chat/stdout) using the generic template as its shape; it writes NO tracked verdict file and creates no new evidence artifact. Any persistence (saving or posting the verdict) is a separate, opt-in, human-triggered action outside this read-only module, consistent with the already-deferred PR-comment write.

## Why this feature exists

The kit already merges work through a human PR review pattern that is, today, tribal
knowledge re-applied by hand on every PR: is the PR still a draft, is it mergeable, did
CI pass, are there unresolved Codex / GitHub review comments, does the PR body claim a
readiness stage the committed `readiness-status.yaml` does not back, was a publish
approval requested before Semantic Model Ready is `pass`, did someone commit raw data or
a secret or a local machine path. A reviewer reconstructs that checklist from memory each
time, and the recent history of this very repo (Codex PR review with nine findings; a
publish-approval record; a readiness-stage / date-table reconciliation) shows the pattern
is real, repeatable, and expensive to do by hand.

This feature turns that manual pattern into a **read-only Product Module**: a repeatable
skill that observes one PR plus the committed readiness evidence and renders a single
structured verdict -- `merge_ready` (yes/no) with explicit `blockers[]`, `warnings[]`,
`required_human_decisions[]`, `evidence[]`, and one `next_action`. It does not replace the
human reviewer or the gates; it assembles the evidence the human needs in one place and
states, traceably, whether anything blocks the merge.

It is a **Product Module** in the F024 sense (the Companion Tools architecture): it READS
evidence, SUMMARIZES it, and renders a verdict; it MUST NOT create truth. It cannot merge,
cannot approve, cannot resolve a thread, cannot move a stage. The verdict is a derived
reading of evidence, never an authority.

## What this feature is NOT (the scope wall)

This is the load-bearing constraint, stated up front so the spec cannot drift:

- **It is read-only and takes no merge action.** It observes and reports; every act that
  changes state (merge, approve, resolve a thread, push a commit, edit a PR body, move a
  stage) remains a named human's action (Principle V; F024 Core Authority -- a module cannot
  create truth). The full forbidden list is in "Forbidden operations".
- **`merge_ready` is a DERIVED BOOLEAN, never a score and never an approval.**
  `merge_ready: yes` means "no blocker and no open required-human-decision was found in the
  evidence" -- it is NOT a confidence number (hard rule #9) and it is NOT "I approve this
  PR." A human still approves and still merges. The module never emits a numeric
  confidence/health/merge score.
- **It introduces NO new gate and NO new validator.** It does not re-run `retail check` or
  `retail validate` as a new check, does not add a `retail check` rule (the static gate
  stays exit 0), and does not add a CI workflow. It READS the recorded
  results of the existing gates and the existing CI, and the committed readiness evidence,
  and interprets them. Reading PR / CI / git state is read-only OBSERVATION, not a gate and
  not a mutation.
- **It defines no business meaning and approves nothing.** It does not decide a grain, a
  PII publish-safety call, a sentinel-vs-null choice, a business rollup, or whether a
  metric/mapping is correct. Those are `required_human_decisions[]` it surfaces and routes
  to the named owner (Principle V). The module recommends; the human decides.
- **Generic.** No worked-example specifics (no billing codes, segments, PII column names,
  per-table grain keys). C086 / `retail_store_sales` are FILLED INSTANCES cited as
  references, never baked into the generic skill or template (Principle VII).

## Aggregates and observes, never re-derives or gates (the evidence chain)

Every line in the verdict traces back to an observed PR fact or a committed evidence file.
The verdict is an interpretation over these, never a new measurement:

| Verdict input | Source it observes / reads | Default severity |
|---------------|----------------------------|------------------|
| PR state (open / draft / closed) | the PR's own state (e.g. via `gh pr view`) | draft -> blocker; closed -> blocker |
| mergeability / conflicts | the PR's mergeable state + base divergence | conflicts -> blocker |
| CI / workflow conclusions | the recorded check-run / workflow conclusions on the head SHA | failing required check -> blocker |
| open review threads | unresolved review threads on the PR | unresolved -> warning (blocker if a reviewer marked change-requested) |
| Codex / GitHub review comments | unresolved review comments / findings | unresolved -> warning; unaddressed change-request -> blocker |
| tests declared vs run | the PR body's claimed test plan vs the recorded CI test result | declared-not-run -> blocker |
| no raw data committed | the PR diff file list vs the repo's raw-data ignore policy | raw data present -> blocker |
| no secrets / no local paths | the PR diff scanned for secret-shaped / machine-path strings | present -> blocker |
| readiness-stage consistency | the PR body's claimed stage vs `mappings/<table>/readiness-status.yaml` `current_stage` + per-stage `status` | mismatch -> blocker |
| approvals consistency | the PR body's claimed approval vs `readiness-status.yaml` `approvals[]` (named owner + date) | missing/absent -> blocker |
| source-map approval metadata | `source-map.yaml` approval / mapping-gate CLEARED metadata when the PR touches a mapping | absent when claimed -> blocker |
| PR-body drift vs readiness | any claim in the PR body unsupported by committed evidence | unsupported claim -> warning (blocker if it asserts a stage `pass`) |
| publish approval requested too early | a publish/merge-to-publish request when Semantic Model Ready / the required prior stage is not `pass` | too-early -> required_human_decision (Principle V), and a blocker until resolved |

If a source is missing, the module records `unknown` for that line with the missing
source named -- it does NOT invent a status or assume pass. A `merge_ready: yes` MUST be
backed by zero blockers AND zero open `required_human_decisions[]`, each traceable to its
source; the module cannot upgrade a verdict past its evidence.

## Relationship to shipped features (scope delta)

This module overlaps several shipped surfaces; the delta is precise:

- **vs F012 Data Quality Control Room (013).** F012 rolls up DATA-QUALITY findings +
  blockers ACROSS tables (a portfolio view of `retail check` WARNs, `retail validate`
  ERRORs, per-table issues). F025 guards ONE PR's promotion ACT: it reads PR + CI + review
  state and checks PR-body claims against committed readiness evidence. F012 answers "which
  table is broken across the portfolio"; F025 answers "is THIS pull request safe to merge,
  and what blocks it". F025 may CITE F012's recorded roll-up as evidence; it does not
  re-compute it.
- **vs `retail check` / `retail validate` (the gates).** F025 READS the recorded results
  of these gates (exit code, WARNs, ERRORs) as evidence; it does NOT re-run them as a new
  check and adds no rule. The gates remain the authority on rule-pass; F025 only reports
  whether the PR is consistent with their recorded results.
- **vs any existing Codex / cross-model review gate.** F025 does not replace the human or
  the Codex review; it observes whether their threads/comments are RESOLVED and surfaces
  unresolved ones as warnings/blockers. It never resolves a thread or speaks for a
  reviewer.
- **The novel surface F025 owns:** PR-body drift vs `readiness-status.yaml`,
  readiness-stage consistency, approvals consistency, source-map approval-metadata
  consistency, and the "publish approval requested too early" guard -- the cross-check
  between what a PR CLAIMS and what the committed readiness evidence SUPPORTS.

## Architecture (planning posture: a pure skill + one template + one doc; no code, no new CLI)

Consistent with F012 (013): the reviewer is **agent-procedure text**; the agent is the
runtime. Planned shape: **a pure skill plus one generic report template plus one tool doc;
NO new Python, NO new `retail` subcommand, NO codegen, NO new CI workflow.**

Deciding reason: the work is a read-fan-out over a handful of PR facts (observable through
read-only `gh` / git reads the agent already performs) plus reading committed
`readiness-status.yaml` / `source-map.yaml` and interpreting existing CI and gate results
-- exactly the read-and-interpret posture `retail-validate` ("invoke-and-interpret only")
and the control room ("aggregates, never re-derives") already use. A `retail pr-review`
subcommand would add a CLI that parses PR JSON and tracks the readiness schema in code --
maintenance for ~zero gain at this volume (YAGNI, hard rule #8). The template gives the
verdict a stable, reviewable shape; the skill gives the agent the procedure to fill it from
observed PR state + committed evidence; the doc explains when to run it and what each line
means. (The actual SKILL.md / template / doc are FUTURE deliverables enumerated in plan.md
and tasks.md, not created in this spec-only slice.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One structured "is this PR safe to merge" verdict (Priority: P1)

A human (or the agent) asks "is this PR ready to merge?" for a given PR. The skill observes
the PR's state (open/draft, mergeable, CI/workflow conclusions, open review threads,
unresolved review comments) and reads the committed readiness evidence the PR touches, then
emits ONE structured verdict: `merge_ready` (yes/no), `blockers[]`, `warnings[]`,
`required_human_decisions[]`, `evidence[]`, and a single `next_action` -- every line
traceable to an observed fact or a committed source.

**Why this priority**: this is the feature -- the one structured verdict that replaces the
hand-reconstructed merge checklist. Without it, the module does not exist.

**Independent Test**: given a PR with one failing required CI check and one unresolved
review thread, the skill emits a verdict where the failing check is a `blocker` (with the
check name + conclusion as evidence), the unresolved thread is a `warning` (with the thread
reference), `merge_ready` is `no`, and `next_action` names the single highest-value step --
and the skill takes no action on the PR (no merge, no approve, no thread resolution).

**Acceptance Scenarios**:

1. **Given** a PR with passing CI, no draft flag, no unresolved threads, a PR body whose
   claims match the committed `readiness-status.yaml`, and no raw-data/secret/path
   findings, **When** the skill runs, **Then** it emits `merge_ready: yes` with an empty
   `blockers[]` and empty `required_human_decisions[]`, and every `evidence[]` line names
   its source.
2. **Given** a PR that is still a draft, **When** the skill runs, **Then** `draft` is a
   `blocker`, `merge_ready` is `no`, and `next_action` is "mark ready for review" -- the
   skill does not un-draft or merge.
3. **Given** any verdict line, **When** a reviewer asks "where does this come from",
   **Then** the skill can name the exact observed fact (PR number, check-run conclusion,
   thread id) or committed source (path + field/line) it read.

---

### User Story 2 - Blocker vs warning, made operational (Priority: P1)

The verdict MUST distinguish a BLOCKER (a finding that, while present, makes
`merge_ready` `no`) from a WARNING (a finding surfaced for the reviewer that does not, by
itself, flip the verdict). The gating rule is explicit: `merge_ready` is `no` while ANY
`blockers[]` entry OR ANY open `required_human_decisions[]` entry exists; `warnings[]`
surface but do not alone flip the verdict.

**Why this priority**: a verdict that does not separate "this must be fixed before merge"
from "the reviewer should be aware of this" is just an undifferentiated list. The
blocker/warning split is what makes the verdict actionable and what the task requires.

**Independent Test**: construct a PR with (a) one failing required check [blocker], (b) one
unresolved non-blocking review thread [warning], and (c) no open required-human-decision;
assert `merge_ready` is `no` because of (a); then remove (a) and assert that with only the
warning remaining, `merge_ready` is `yes` and the warning is still listed. A pure-warning
PR is `merge_ready: yes` with a non-empty `warnings[]`.

**Acceptance Scenarios**:

1. **Given** a PR whose only findings are warnings (e.g. an unresolved informational review
   comment, a benign PR-body imprecision), **When** the skill runs, **Then** `merge_ready`
   is `yes`, `blockers[]` is empty, and the warnings are listed for the reviewer.
2. **Given** a PR with a failing required CI check, **When** the skill runs, **Then** the
   check is a `blocker`, `merge_ready` is `no`, and the verdict states which check and its
   recorded conclusion.
3. **Given** a finding whose severity is ambiguous (e.g. an unresolved review thread with no
   explicit change-request), **When** the skill classifies it, **Then** it uses the
   default in the evidence-chain table (unresolved thread -> warning; change-requested ->
   blocker) and records why -- it never silently promotes or demotes a severity.

---

### User Story 3 - PR-body drift, readiness-stage / approvals consistency, and too-early publish (Priority: P1)

The skill cross-checks what the PR CLAIMS against what the committed readiness evidence
SUPPORTS: a PR body claiming a stage the `readiness-status.yaml` does not back is drift; a
claimed approval absent from `approvals[]` is a blocker; a publish approval requested before
the required prior stage is `pass` is surfaced as a `required_human_decision` (Principle V)
and blocks until a named human resolves it. The module flags and routes; it never moves the
stage, grants the approval, or rules on the judgment call.

**Why this priority**: this is the novel surface F025 owns and the constitutional guardrail.
A PR is exactly where an over-eager promotion (a claimed `pass`, a too-early publish
request) tries to slip past, and where a module would be tempted to "just approve it". Both
must hard-stop at the human.

**Independent Test**: given a PR body asserting "Publish Ready" while the table's
`readiness-status.yaml` shows Semantic Model Ready is not `pass`, assert the skill records a
`required_human_decision` ("publish approval requested before <prior stage> is pass --
named owner must decide"), sets `merge_ready: no`, cites the exact `readiness-status.yaml`
field, and does NOT mark any stage `pass` or approve anything. Given a PR body claiming an
approval absent from `approvals[]`, assert that is a `blocker` with the missing approval
named.

**Acceptance Scenarios**:

1. **Given** a PR body claiming a readiness stage that `readiness-status.yaml`
   `current_stage` / per-stage `status` does not support, **When** the skill runs,
   **Then** it records the drift (warning for a general unsupported claim; blocker when the
   claim asserts a stage `pass`) and cites the conflicting field -- it does not edit either.
2. **Given** a publish/merge-to-publish request while the required prior stage is not
   `pass`, **When** the skill runs, **Then** it records a `required_human_decision` routing
   to the named owner, sets `merge_ready: no`, and takes no approving action (Principle V).
3. **Given** a PR claiming a mapping is approved while the touched `source-map.yaml` carries
   no CLEARED approval metadata, **When** the skill runs, **Then** the missing approval is a
   `blocker` naming the absent metadata -- the skill never self-clears the mapping gate.
4. **Given** any request to "approve and merge this PR" or "mark this stage pass", **When**
   the skill is asked, **Then** it declines, states it is read-only and cannot create truth
   (F024 / Principle V), and returns the verdict for a human to act on.

### Edge Cases

- **Missing evidence**: the PR touches no readiness artifact, or a referenced
  `readiness-status.yaml` is absent -- the skill records the relevant lines as `unknown`
  with the missing source named, and does NOT assume `pass` or fabricate a verdict.
- **CI not yet run / pending**: a required check is queued/in-progress -- the skill reports
  the check as `pending` (a blocker for `merge_ready: yes`, since not-yet-green is
  not-green) with its recorded state, and does NOT re-trigger or wait on CI itself.
- **A no-fake-confidence request**: asked for "a merge-readiness score 0-100" or "how
  confident are you", the skill DECLINES, cites no-fake-confidence (rule #9), and returns
  the boolean `merge_ready` + the explicit blockers/warnings/required-decisions with their
  sources.
- **Conflicting evidence** (e.g. PR body says a stage is `pass` but `readiness-status.yaml`
  shows a `blocked` with an open blocking reason): the skill SURFACES the conflict as a
  finding and does NOT resolve it by choosing one (surface conflicts, never bury them --
  Principle V posture).
- **A secret-shaped string in the diff**: flagged as a blocker AND the skill recommends the
  STOP-rotate-sweep posture (security rule); it reports the location but does not edit or
  remove it (read-only).
- **An unassigned required decision**: a `required_human_decision` whose owner is not named
  is shown with owner "UNASSIGNED" and flagged -- the skill never self-assigns or
  self-resolves it.
- **The skill is run on its own PR**: it reviews the PR like any other; it has no special
  authority over its own promotion and cannot self-approve.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Plan a `.claude/skills/pr-readiness-reviewer/SKILL.md` (ASCII, UTF-8 no BOM,
  valid frontmatter) as a FUTURE deliverable -- a read-only Product Module skill. NO new
  Python, NO new `retail` subcommand, NO codegen, NO new CI workflow. (Enumerated in
  plan.md/tasks.md; not created in this spec-only slice.)
- **FR-002**: Plan ONE generic verdict template (`templates/pr-readiness-report.md`) -- the
  stable output shape carrying `merge_ready`, `blockers[]`, `warnings[]`,
  `required_human_decisions[]`, `evidence[]`, `next_action`. ASCII, UTF-8 no BOM,
  placeholders only, no worked-example specifics (Principle VII).
- **FR-003**: Plan a tool doc (`docs/tools/pr-readiness-reviewer.md`) explaining when to run
  the reviewer, what each verdict field means, the blocker-vs-warning rule, and the
  read-only / no-merge / no-approve / no-stage-move boundary. (Future deliverable.)
- **FR-004**: The skill MUST emit a verdict with EXACTLY these fields: `merge_ready`
  (yes/no boolean), `blockers[]`, `warnings[]`, `required_human_decisions[]`, `evidence[]`,
  and one `next_action`. It MUST distinguish a blocker (flips `merge_ready` to `no`) from a
  warning (surfaced, does not alone flip the verdict).
- **FR-005**: The gating rule MUST be explicit: `merge_ready` is `no` while ANY `blockers[]`
  entry OR ANY open `required_human_decisions[]` entry exists; `warnings[]` do NOT alone
  flip `merge_ready`. `required_human_decisions[]` is a SEPARATE gating class from
  `blockers[]` (a human-judgment item, not a defect), and BOTH gate `merge_ready: yes`.
- **FR-006**: The skill MUST observe and report, each at the default severity in the
  evidence-chain table above, the PR facts: PR state (draft/open/closed), mergeability /
  conflicts, CI / workflow conclusions, open review threads, unresolved Codex / GitHub
  review comments, tests-declared-vs-tests-run, no-raw-data-committed, and
  no-secrets / no-local-paths.
- **FR-007**: The skill MUST cross-check PR-body claims against committed readiness evidence,
  at the evidence-chain-table severities: readiness-stage consistency vs
  `mappings/<table>/readiness-status.yaml`, approvals consistency vs `approvals[]`,
  source-map approval metadata vs `source-map.yaml` (mapping-gate CLEARED), and general
  PR-body drift. A claim asserting a stage `pass` unsupported by evidence is a blocker; a
  lesser unsupported claim is a warning.
- **FR-008**: The "publish approval requested too early" guard: if the PR requests a
  publish / merge-to-publish while the required prior readiness stage (e.g. Semantic Model
  Ready) is not `pass`, the skill MUST record a `required_human_decision` routing to the
  named owner (Principle V) and set `merge_ready: no` until resolved -- never approving the
  publish or moving the stage.
- **FR-009**: The skill MUST be READ-ONLY: it MUST NOT merge a PR, approve a PR (submit a
  review, grant a required approval), resolve or reply to a review thread, push or amend a
  commit, edit a PR body, or move/upgrade a readiness stage. It performs read-only
  observation only (F024 Core Authority; Principle V). The verdict is EMITTED EPHEMERALLY --
  rendered to the operator (chat/stdout) in the shape of the generic template; the skill
  writes NO tracked verdict file and creates no new committed evidence artifact. Persisting or
  posting the verdict is a separate, opt-in, human-triggered action outside this module (the
  PR-comment write stays deferred under "Deferred decisions").
- **FR-010**: No-fake-confidence guard: `merge_ready` is a derived boolean, never a numeric
  score. The skill MUST refuse to emit a numeric merge/confidence/health score; if asked, it
  declines, cites no-fake-confidence (rule #9), and returns the boolean + explicit
  blockers/warnings/required-decisions.
- **FR-011**: Evidence traceability: EVERY entry in `blockers[]`, `warnings[]`,
  `required_human_decisions[]` MUST carry a cited source -- a PR fact (PR number, check-run
  conclusion, thread/comment id) or a committed source (path + field/line). A finding with
  no traceable source is a defect.
- **FR-012**: Missing / pending / conflicting evidence handling: a missing source yields an
  `unknown` line naming the missing source (never an assumed `pass`); a pending CI check is
  reported as `pending` (a blocker for `merge_ready: yes`); conflicting evidence is surfaced
  as a finding and NOT silently resolved (Principle V posture).
- **FR-013**: No new gate / no new validator: the skill MUST run NO new `retail check`
  /`retail validate` of its own as a new gate, add NO `retail check` rule (verified by the
  diff), and add NO CI workflow. It READS recorded gate/CI results as evidence only.
- **FR-014**: All planned artifacts MUST be GENERIC: a reader finds ZERO C086 /
  `retail_store_sales` / pharmacy specifics in the skill, template, or doc. The worked
  examples may be CITED as filled instances, never inlined (Principle VII).

### Key Entities

- **PR readiness verdict**: the structured output -- `merge_ready` (derived boolean),
  `blockers[]`, `warnings[]`, `required_human_decisions[]`, `evidence[]`, one `next_action`.
  A READING of evidence, never an approval or a score.
- **Blocker**: a finding that, while present, makes `merge_ready` `no` (e.g. failing
  required CI, draft state, conflicts, a claimed-but-absent approval, a secret in the diff).
  Each carries a cited source.
- **Warning**: a finding surfaced for the reviewer that does not, by itself, flip the
  verdict (e.g. an unresolved informational review thread, a benign PR-body imprecision).
  Each carries a cited source.
- **Required human decision**: a Principle-V judgment item the module surfaces and routes to
  a named owner (e.g. publish-too-early, a PII publish-safety question, a grain/sentinel
  call) -- a SEPARATE gating class from blockers; an open one also makes `merge_ready` `no`.
  The module recommends; the human decides.
- **Observed PR facts (inputs, read-only)**: PR state, mergeability, CI/workflow
  conclusions, review threads, review comments -- read via read-only `gh` / git observation.
- **Committed readiness evidence (inputs, unchanged)**: `mappings/<table>/readiness-status.yaml`
  (`current_stage`, per-stage `status`, `approvals[]`, `blocking_reasons[]`),
  `source-map.yaml` approval metadata, declared test plan, the recorded `retail check`
  /`retail validate` and CI results. INPUTS; the module creates no new evidence file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The planned `.claude/skills/pr-readiness-reviewer/SKILL.md`,
  `templates/pr-readiness-report.md`, and `docs/tools/pr-readiness-reviewer.md` are
  enumerated as future deliverables with their shapes specified; when later built they will
  be ASCII + UTF-8 no BOM, frontmatter valid, and generic (no worked-example specifics).
- **SC-002**: The verdict separates blocker from warning operationally: given a PR with one
  blocker and one warning, `merge_ready` is `no` due to the blocker; with the blocker
  removed and only the warning remaining, `merge_ready` is `yes` and the warning is still
  listed -- demonstrating warnings do not alone gate.
- **SC-003**: Every verdict line is traceable: a reviewer can name, for each blocker /
  warning / required-decision, the exact observed PR fact or committed source it was read
  from. A line with no traceable source is a defect (FR-011).
- **SC-004**: No-fake-confidence holds: a request for a numeric merge-readiness score is
  DECLINED with the rule-#9 rationale, and the only verdict value is the boolean
  `merge_ready` plus the explicit lists -- no number reads as confidence anywhere.
- **SC-005**: Read-only holds: across all scenarios, the module performs no merge, no
  approval, no thread resolution, no commit/PR-body edit, and no stage move -- a reviewer
  can confirm it only observed and reported (F024 Core Authority; Principle V).
- **SC-006**: Adding this feature adds no new `retail check` rule, runs no new
  gate, and adds no CI workflow -- it reads recorded gate/CI results as evidence only
  (FR-013).

## Human approval boundary

The module NEVER grants or substitutes for human approval. `merge_ready: yes` is a derived
reading ("no blocker and no open required-human-decision found in evidence"), explicitly NOT
an approval and NOT a merge. The named human reviewer still approves the PR and still
performs the merge. Every `required_human_decision[]` routes to a NAMED owner; the module
recommends and STOPS (Principle V). No tool self-approves, self-merges, or self-clears.

## Allowed operations

- Read-only observation of a PR's state, mergeability, CI / workflow conclusions, review
  threads, and review comments (read-only `gh` / git reads).
- Reading committed readiness evidence (`readiness-status.yaml`, `source-map.yaml`,
  declared test plan, recorded gate/CI results) and the PR diff/file list.
- Interpreting the observed facts + committed evidence into a structured verdict.
- Emitting the verdict (`merge_ready`, `blockers[]`, `warnings[]`,
  `required_human_decisions[]`, `evidence[]`, `next_action`) and recommending a next action.
- Declining out-of-scope requests (approve/merge/score) with the governing rule cited.

## Forbidden operations

- Merging a PR; approving a PR (submitting a review, granting a required approval).
- Resolving, replying to, or editing a review thread or review comment.
- Pushing, amending, or reverting a commit; editing a PR body or title.
- Moving, upgrading, or marking `pass` any readiness stage; clearing a blocker; granting an
  approval; clearing the mapping gate.
- Defining business meaning, a metric, a mapping, a grain, a PII call, or a sentinel choice
  (those are `required_human_decisions[]`).
- Re-running `retail check` / `retail validate` as a new gate, adding a `retail check` rule,
  or adding a CI workflow.
- Emitting a numeric merge / confidence / health score (rule #9).
- Inventing a status / approval / source for a missing or pending input.

## Evidence required

- For `merge_ready: yes`: zero `blockers[]` and zero open `required_human_decisions[]`,
  each observed line traceable to its source; pending/unknown lines are not treated as pass.
- For each blocker: a cited observed PR fact (PR number, check-run conclusion, thread id) or
  committed source (path + field/line).
- For each `required_human_decision`: the judgment call, the named owner who must decide, and
  the evidence prompting it (Principle V).
- For a claimed readiness stage / approval / mapping clearance: the supporting
  `readiness-status.yaml` / `approvals[]` / `source-map.yaml` field, or a blocker naming its
  absence.

## Readiness stage affected

Cross-cutting -- the module guards promotions at EVERY stage (it is run on the PR that would
advance any stage). It does not itself enter, gate, or advance any single stage; it reports
whether the PR is consistent with the committed readiness evidence for whatever stage the PR
claims to advance.

## Dependencies

- **Upstream**: F024 (the Companion Tools architecture -- defines the Product Module,
  read-only category and the Core Authority boundary this module obeys); the readiness
  spine (F005: `docs/readiness/`, `templates/readiness-status.yaml`,
  `mappings/<table>/readiness-status.yaml` per ADR 0004); the constitution (Principles V,
  VII, VIII, IX). All cited by roadmap identity; F024's own artifacts are authored in this
  same batch.
- **Reads (does not depend on for its own gate)**: the recorded results of `retail check`
  / `retail validate` and CI, the per-table readiness evidence, and (optionally) the F012
  control-room roll-up -- all as evidence.

## Non-goals

(The read-only / no-act boundary is enumerated under "Forbidden operations"; not repeated
here.)

- Any new `retail check` rule, Python module, CLI verb, or CI workflow (hard rule #8;
  Principle VIII).
- Defining or approving a metric, mapping, grain, PII call, business rollup, or sentinel
  choice (Principle V).
- A numeric merge / confidence / health score (rule #9; deferred until scoring rules exist).
- Filling the skill/template/doc with C086 / `retail_store_sales` specifics (Principle VII).
- Reviewing more than one PR at a time (a portfolio PR roll-up is deferred; this module is
  per-PR).

## Assumptions

- Pure skill + one generic template + one doc; the agent is the runtime (same posture as
  F012/013). No new Python, no `retail pr-review` CLI, no codegen, no CI workflow (YAGNI).
- PR facts are observable through read-only reads the agent already performs (e.g.
  `gh pr view`, `gh pr checks`, the PR diff); the module reads, never writes, GitHub state.
- The per-table readiness evidence (`mappings/<table>/readiness-status.yaml`,
  `source-map.yaml`) already exists as the F005 / ADR 0004 templates and is the
  authoritative input; this module consumes it, never redefines it.
- "Cross-cutting" means the reviewer applies to any PR regardless of which stage it
  advances; it does not itself gate or advance a stage.
- The verdict is delivered EPHEMERALLY (rendered to the operator using the generic template
  as its shape); the module persists nothing and creates no new committed evidence file.
  Saving or posting the verdict is a deliberate, human-triggered action outside this read-only
  module (auto-posting as a PR comment is enumerated under "Deferred decisions").

## Deferred decisions (future specs / issues -- recorded, not built)

- **A `retail pr-review` CLI / programmatic verdict** (machine-readable JSON output): DEFERRED
  until PR volume justifies a code surface (still read-only, still no new gate).
- **A numeric merge-readiness score**: DEFERRED until readiness scoring rules are defined
  (rule #9). Until then the verdict is the boolean `merge_ready` + explicit lists only.
- **A portfolio PR roll-up** (many PRs at once): DEFERRED; this module is per-PR. A future
  multi-PR view could read each PR's verdict.
- **Auto-posting the verdict as a PR comment**: DEFERRED and treated as a WRITE action
  outside read-only scope; if ever built it would be an opt-in, human-triggered post, never
  an approval.

## See also

- The architecture parent: F024 (Companion Tools architecture -- Product Module, read-only
  category; Core Authority boundary), `specs/018-companion-tools-architecture/`.
- The closest sibling read-only aggregator: F012 Data Quality Control Room,
  `specs/013-data-quality-control-room/spec.md`; the per-table evidence it reads:
  `templates/readiness-status.yaml`, `templates/source-map.yaml`.
- The readiness spine + no-fake-confidence rule: `docs/readiness/readiness-model.md`;
  the stage sequence: `docs/readiness/readiness-pipeline.md`.
- The gates it reads (never re-runs as a new check): the `retail-govern` / `retail check`
  static surface and the `retail-validate` / `retail validate` live surface.
- The roadmap: `docs/roadmap/roadmap.md`, to be extended by this batch with the F025 row
  (Product Module, read-only, cross-cutting); hard rules 7, 8, 9. Constitution Principles V,
  VII, VIII, IX.
