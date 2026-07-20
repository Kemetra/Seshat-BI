---
name: run-next-readiness
description: >-
  Compute the ONE next allowed action for a single table from its
  readiness-status.yaml -- walk the seven readiness stages in fixed order, find
  the earliest non-pass stage, and return exactly one outcome: a forward
  next_action, a stop_blocked citing blocking_reasons verbatim, an
  approval_required naming the human authority class, a terminal_pass, or an
  input_defect -- plus any caveats (pass-without-evidence, stored/computed
  next_action disagreement, warning carried forward, dual-blocked). Use when
  someone asks "what's the next allowed action for this table", "is this table
  blocked", "can I proceed to silver/gold yet", or "what is <table> waiting on".
  READ-ONLY and compute-then-STOP: it never executes the action, never writes
  readiness-status.yaml, never advances a stage, never grants or infers an
  approval, opens NO DB connection, and emits NO numeric health / confidence /
  percent-ready score (hard rule #9). It COMPUTES a fresh answer for ONE table
  (unlike readiness-viewer, which RENDERS the stored field across many); it does
  not execute (unlike retail-orchestrate); it APPLIES but does not re-implement
  RS1's approval-shape rule.
---

# run-next-readiness

`retail-orchestrate` observes disk state, decides the next phase, and then
EXECUTES it (self-healing against the gate). This skill is the extracted,
standalone, READ-ONLY decision half: given ONE table's committed
`readiness-status.yaml`, it computes the single next allowed action and STOPS.
It runs nothing, writes nothing, and grants nothing. It answers the question;
the human (or `retail-orchestrate`) acts on the answer.

## Module contract (this skill IS a filled Product Module declaration)

Per the F024 Companion Tools Architecture contract (`templates/module-contract.md`).

- **Authority category:** Product Module
- **Capability level:** `read-only`  *(exactly one)*
- **Product layer:** `4`  *(readiness spine lens; orthogonal to category)*
- **Roadmap feature:** `F080`  **On-disk spec:** `specs/080-run-next-readiness-state-machine/`
- **Owner:** `the readiness / data-quality lead`  *(a named role -- never "the agent")*
- **Status:** `Authored`

### What it does (one line)

> Reads one table's `readiness-status.yaml` (Core Authority), walks the seven
> stages in fixed order, and returns the single next allowed action (or a
> stop / approval-required / terminal / defect outcome) -- creating no truth,
> executing nothing.

### Core Authority it READS

It reads these committed truth artifacts; it never writes them.

- `mappings/<table>/readiness-status.yaml` -- `table`, `current_stage`, per-stage
  `status` (the four words), `evidence[]`, `blocking_reasons[]`, `approvals[]`,
  `next_action`. Its ABSENCE is a valid, handled case (not an error).
- the "Next allowed action" and "Required owner / approval" fields of each
  `docs/readiness/<stage>-ready.md` -- fixed reference vocabulary for phrasing
  the forward action and confirming which stages require an approval.

### What it WRITES

Nothing. Its output is an ephemeral response to the caller (an agent turn, a
human, a future `retail-orchestrate` wiring), never a file on disk. The
read-only proof is `git status --short` empty after any invocation (SC-003).

## Scope boundary (read this before every use)

- **Read-only.** Computes no truth it then persists. Reads
  `readiness-status.yaml` and the stage docs; writes nothing, ever.
- **Computes, does not execute.** It names the next allowed action; it does NOT
  run it. Running the mapping gate, writing silver SQL, invoking `retail
  validate`, publishing -- none of that is this skill's job (that is
  `retail-orchestrate` and the medallion verbs). Executing "just the next step
  for convenience" is the one temptation this skill must never yield to.
- **Grants no approval.** At a human-approval seam it reports "approval
  required" and names the authority class; it NEVER writes an `approvals[]`
  entry, infers one, or treats a missing/shape-invalid one as present
  (Principle V; hard stop "never self-grant approval").
- **No fake confidence.** The response carries no numeric score, percentage, or
  health/confidence/percent-ready field (hard rule #9). Outcomes and authority
  classes are enums (strings), never numbers.
- **Generic.** No C086 / `retail_store_sales` / client specifics baked into the
  logic. Any table name in an example is a cited filled instance, never part of
  the procedure.
- **One table, fresh, every time.** No memory of prior invocations, no cache, no
  persisted run-state, no daemon. Same file in -> same response out
  (determinism).
- **ASCII + UTF-8 no BOM.** No non-ASCII glyphs in this skill or its output.

## Relationship to retail-orchestrate / readiness-viewer / RS1

This is the fourth reader of `readiness-status.yaml`. It exists as a distinct
surface because each of the three neighbors does something this one deliberately
does not:

1. **vs. `retail-orchestrate`.** Orchestrate contains an inline "observe disk
   state -> current phase/action" decision that it uses internally and then
   EXECUTES via its self-heal loop. This skill extracts the READ-ONLY decision
   half into a standalone, independently invocable surface. It does not change
   orchestrate's execution / self-heal behavior. (A future wiring change --
   orchestrate calling this skill instead of recomputing inline -- is out of
   scope here.)
2. **vs. `readiness-viewer` (F026) / `retail-control-room` (F012).** Both surface
   a `next_action` value, but they RENDER the file's STORED `next_action` string
   verbatim, across many tables (a rendering lens). This skill COMPUTES a fresh
   next action from the seven stage statuses for ONE table, and when the computed
   value disagrees with the stored string it reports BOTH and flags the
   disagreement (a `next_action_disagreement` caveat) rather than silently
   picking one. Cross-table aggregation stays F012/F026 territory.
3. **vs. RS1 (`src/seshat/rules/readiness_status.py`).** RS1 is the static
   consistency LINTER wired into `seshat check` (invalid status values, `pass`
   without evidence, `blocked` without reasons, invalid approval-owner shape,
   `current_stage` skipping a blocker). This skill applies the SAME
   approval-owner shape rule -- so its notion of "approved" agrees with the
   gate's -- but it does NOT call RS1's code, does NOT add a rule ID, and does
   NOT assume its input has already passed RS1. On RS1-dirty input it degrades
   gracefully (reports the defect as an `input_defect` or an approval failure)
   rather than requiring RS1-clean input first.

**Merge-fallback (honesty discipline).** If the "fresh computation" delta ever
collapses -- e.g. the computed action turns out to always agree trivially with
the stored `next_action` and the disagreement path never fires on real data --
the documented fallback is to fold this computation into `retail-orchestrate`'s
existing decision table as a named, independently-callable sub-step rather than
keep a fourth overlapping surface. This mirrors `readiness-viewer`'s own
merge-fallback discipline.

## The stage-order walk (the procedure)

The "state machine" this skill's name refers to is a PURE FUNCTION from one
`readiness-status.yaml` snapshot to one response -- re-evaluated fresh every
time, with no memory of prior runs. Walk the seven stages in this FIXED order
(matching `docs/readiness/readiness-pipeline.md` and RS1's `_STAGE_ORDER`):

```
1. source_ready
2. mapping_ready
3. silver_ready
4. gold_ready
5. semantic_model_ready
6. dashboard_ready
7. publish_ready
```

For each stage, front-to-back, apply these checks and RETURN on the first one
that fires (the earliest non-cleared stage in walk order wins -- position alone
decides the outcome; the outcome TYPE never overrides walk position):

```
for stage in the seven stages, in the fixed order above:

    # (a) invalid / unrecognized status blocks determining order past here
    if stage.status is not one of {not_started, blocked, warning, pass}:
        return input_defect(stage)          # name the first defective stage

    # (b) a blocked stage is the first wall
    if stage.status == "blocked":
        return stop_blocked(stage, stage.blocking_reasons)   # verbatim, non-empty

    # (c) a not_started / warning stage is the forward frontier
    if stage.status in {not_started, warning}:
        # before advancing INTO this stage, the PRIOR stage's approval
        # (if the prior stage is approval-required) must be present + shape-valid
        if prior_stage is approval-required
           and prior_stage has no shape-valid approvals[] entry:
            return approval_required(prior_stage)
        caveats += [warning_carried_forward(stage)] if stage.status == "warning"
        return next_action(stage, action_text from that stage's doc)

    # (d) a pass stage: record evidence gap, check its own approval, then continue
    if stage.status == "pass":
        if stage.evidence is empty:
            caveats += [pass_without_evidence(stage)]
        if stage is approval-required
           and stage has no shape-valid approvals[] entry:
            return approval_required(stage)
        continue        # cleared -- move to the next stage

# every stage was pass with all required approvals shape-valid
return terminal_pass(caveats accumulated along the way)
```

**Approval-required stages** (matching RS1's `_APPROVAL_REQUIRED` plus the
file-source special case):

- `mapping_ready` -- always
- `semantic_model_ready` -- always
- `dashboard_ready` -- always
- `publish_ready` -- always
- `source_ready` -- ONLY when that stage's block declares a file `source_kind`
  in `{csv, tsv, excel}` (RS1's `_FILE_SOURCE_KINDS`; `xlsx`/`xlsm` alias to
  `excel`). A DB `source_kind` (`db-table`, `table`, `db`) does NOT require the
  Source Ready approval.

**Approval-shape check (cite, do not re-derive).** An `approvals[]` entry counts
as "shape-valid" only if it satisfies the SAME rule RS1 enforces --
`src/seshat/rules/readiness_status.py::_owner_is_valid`. Restating its shape
(verify against the live source at build time, since RS1 may change):

- `owner` must match `Person Name (authority_class)` -- a non-empty name part,
  then exactly one parenthesized class.
- the name part must NOT itself be a role token (not `owner`, and not one of the
  authority classes).
- the class must be one of `_AUTHORITY_CLASSES = {analyst, governance,
  data_owner, metric_owner}` (case / whitespace / hyphen insensitive).
- the entry's `stage` must match the stage whose approval is being checked.

A bare role (`"data_owner"`), a name with no class (`"Ada Lovelace"`), a role as
the name (`"owner (data_owner)"`), or an unknown class (`"Ada (wizard)"`) all
FAIL -- and a failing entry does NOT satisfy the stage's approval requirement.

The `required_authority` returned on an `approval_required` outcome is the
authority class that stage expects (from `docs/readiness/<stage>-ready.md`
"Required owner / approval"); it names WHO must sign, never grants it.

## The response (the five outcomes)

Return exactly ONE `outcome`, plus zero or more `caveats`. Full field-by-field
shape and worked examples: `specs/080-run-next-readiness-state-machine/contracts/run-next-response.md`.

### `next_action` -- the forward frontier
Fires when the earliest non-`pass` stage is `not_started` or `warning` and every
prior approval-required stage's approval is present and shape-valid. Populate
`stage` and `action_text` (drawn verbatim from that stage's
`docs/readiness/<stage>-ready.md` "Next allowed action"). A `warning` frontier
adds a `warning_carried_forward` caveat.

### `stop_blocked` -- the first wall
Fires when the earliest non-`pass` stage is `blocked`. Populate `stage` and
`blocking_reasons` copied VERBATIM from the file (never paraphrased). If a later
stage is ALSO blocked, add a `dual_blocked` caveat naming it -- but the outcome
`stage` is still the earliest.

### `approval_required` -- a human seam
Fires when a stage recorded `pass` (or the file-source `source_ready` special
case) lacks a shape-valid `approvals[]` entry, OR when a forward action would
step past a prior approval-required stage whose approval is missing/invalid.
Populate `stage` and `required_authority` (the authority class expected).
NEVER write, infer, or grant the approval -- report it and stop.

### `terminal_pass` -- the chain is complete
Fires when all seven stages are `pass` with every required approval shape-valid.
`stage` is `null`. `caveats[]` may still carry `pass_without_evidence` entries
accumulated along the walk.

### `input_defect` -- the file cannot be trusted
Fires when the file is missing, unparseable, missing its `stages` key, or a stage
carries an unrecognized status value. `stage` names the first defective stage, or
`null` for a file-level defect. NEVER guess a default on a defective input.

**Missing file is NOT a defect.** When `mappings/<table>/readiness-status.yaml`
does not exist, return `next_action` @ `source_ready` ("No readiness file found;
start onboarding at Source Ready") -- a new table legitimately has no file yet.

## Caveats (never hidden, attached to any outcome)

| `kind` | Fires when |
|--------|------------|
| `pass_without_evidence` | a stage recorded `pass` has empty `evidence[]` |
| `next_action_disagreement` | the file's stored `next_action` names a materially different stage/action than the computed one -- report BOTH |
| `warning_carried_forward` | the forward frontier stage is `warning` (advanced, non-fatal) |
| `dual_blocked` | more than one stage is `blocked`; the caveat names the later one(s) |

Each caveat is `{kind, detail}` where `detail` cites the specific stage/field
(e.g. "stage 'gold_ready' is pass but evidence[] is empty").

## Verified fixtures (trace: fixture -> expected outcome)

Each fixture under `tests/fixtures/readiness/run_next/` exercises one row of
`quickstart.md`'s 15-case table. Walking each by the procedure above yields:

| Fixture file | Case | Expected outcome |
|--------------|------|------------------|
| `us1_forward_action.yaml` | #1 | `next_action` @ `mapping_ready` |
| `us1_blocked.yaml` | #2 | `stop_blocked` @ `mapping_ready` (reasons verbatim) |
| `us1_publish_next.yaml` | #3 | `next_action` @ `publish_ready` (approval gates the transition TO pass, not entry) |
| `us2_approval_invalid_owner.yaml` | #4 | `approval_required` @ `semantic_model_ready` (bare-role owner fails RS1 shape) |
| `us2_approved_chain.yaml` | #5 | `next_action` @ `publish_ready` (all approvals valid) |
| `us2_file_source_approval.yaml` | #15 | `approval_required` @ `source_ready` (csv file source, no approval) |
| `us3_pass_without_evidence.yaml` | #6 | `next_action` @ `semantic_model_ready` + `pass_without_evidence`(gold_ready) |
| `us3_next_action_disagreement.yaml` | #7 | `next_action` @ `mapping_ready` + `next_action_disagreement` |
| `us3_input_defects.yaml` | #9/#10/#12 | `input_defect` (missing stages / current_stage skip / invalid status) |
| `us3_terminal_and_dual_blocked.yaml` | #11/#14 | `terminal_pass`; `stop_blocked` @ `mapping_ready` + `dual_blocked`(gold_ready) |
| `us3_warning_forward.yaml` | #13 | `next_action` @ `silver_ready` + `warning_carried_forward` |
| (no file) | #8 | `next_action` @ `source_ready` ("no readiness file found") |

A reviewer (or a future Python helper's parametrized test) can confirm each row
by applying the walk to the fixture; the read-only proof is `git status --short`
empty after any such walk.

## What this skill must NOT do (forbidden operations)

- MUST NOT write, create, or modify `readiness-status.yaml` or any file.
- MUST NOT execute the next action (no mapping gate, no SQL, no `retail
  validate`, no publish).
- MUST NOT write, infer, back-fill, or grant an `approvals[]` entry.
- MUST NOT advance a stage or set any `status` to `pass`.
- MUST NOT emit a numeric score / confidence / percent-ready (hard rule #9).
- MUST NOT open a DB connection or require the `db` extra.
- MUST NOT register a `seshat check` rule (`@register`) -- it is not a gate.

## See also

- The response contract: `specs/080-run-next-readiness-state-machine/contracts/run-next-response.md`.
- The walk + entities: that spec's `data-model.md`; the 15 cases: its `quickstart.md`.
- The approval-shape rule it cites: `src/seshat/rules/readiness_status.py::_owner_is_valid`.
- Neighbors: `.claude/skills/retail-orchestrate/SKILL.md` (executes),
  `.claude/skills/readiness-viewer/SKILL.md` (renders many), RS1 (lints).
- Usage + boundary doc: `docs/tools/run-next-readiness.md`.
