<!--
=============================================================================
 approval-decision.md  --  the copy-me RECORD of a named human's answer to a request
=============================================================================
 Tower BI Agent Kit  -  Layer 1-6 (all stages), feature F027 (Approval Console).
 On-disk spec: specs/021-approval-console/ . When the spec-dir number (021) and
 the roadmap F-number (F027) disagree, the roadmap F-number wins: this is F027.
 See: docs/tools/approval-console.md (the operator guide + the boundary),
      templates/approval-request.md (the decision package this answers),
      templates/unresolved-questions.md (the Resolution + Status this writes through to),
      templates/readiness-status.yaml (the approvals[] entry this appends).

 WHAT THIS IS
   A GENERIC, copy-me template. One filled copy RECORDS the named human's answer to
   one approval-request.md: the option they selected, the named owner who decided,
   the date, their rationale, the committed artifacts the answer was written through
   to, and any remaining blockers. It is the durable form of an approval -- an answer
   that lives only in chat is NOT recorded. The console writes this record FIRST,
   then writes the answer through to the committed artifacts named in the request.

 THE TRANSCRIBE-NEVER-AUTHOR BOUNDARY  (verbatim across all F027 artifacts -- do not drift)
   The console TRANSCRIBES a human decision and WRITES it into the committed
   artifacts; it does NOT pick the option, supply or forge the owner, invent the
   rationale, auto-accept a recommended default, or move a readiness stage to
   `pass` without the stage's required evidence AND a named human approval. The
   named human decides; the console records. If no human answer exists, there is
   nothing to record and the request stays open.

 WHICH PRINCIPLES THIS INSTANTIATES  (cite, do not re-decide)
   .specify/memory/constitution.md
     V    Agent Stops at Judgment Calls  every field below is the human's answer or a
                                         committed source path -- the console fills none
                                         of them on the human's behalf.
     VII  C086 Is An Example ........... every value below is an obvious placeholder;
                                         C086 is CITED, never inlined (FR-013).
     IX   Secrets & Reproducibility .... ASCII + UTF-8 no BOM; short repo-relative
                                         paths; no secrets.

 NO FAKE CONFIDENCE  (hard rule #9 / readiness-model.md)
   A decision carries explicit status + evidence + blockers ONLY. There is NO
   numeric / health / confidence score field, and a filled copy MUST NOT add one. A
   `pass` is the named-owner approval recorded as evidence (owner + date), never a
   number.

 HOW TO USE
   Copy this file, delete this comment banner, and fill every <ANGLE-BRACKET> field
   from the NAMED HUMAN's answer. A field the human did not supply is left UNFILLED,
   never fabricated (FR-005). Generic only -- no C086 / retail_store_sales values.
=============================================================================
-->

# Approval Decision -- `<question_id>`

- **question_id:** `<MUST match an existing approval-request.md question_id; a decision against a phantom question is refused>`
- **selected_option:** `<the option the NAMED HUMAN chose, e.g. A; transcribed from the human, never picked by the console>`
- **owner:** `<the NAMED human who decided -- a person/role of the required authority class; never "the agent", never self-assigned. Left "UNASSIGNED" if blank, and then NOT a valid approval>`
- **date:** `<YYYY-MM-DD>`  *(the decision date; becomes `at` in the readiness-status.yaml approvals[] entry)*
- **rationale:** `<the human's stated reason; never invented by the console>`

## artifacts_updated

The committed artifacts this decision was written THROUGH to, with the cell/entry that
changed. The console records THIS file FIRST (the durable record), then applies each
write-through idempotently. List only artifacts actually updated; targets that were
missing/unwritable go under `remaining_blockers` (FR-008).

- `mappings/<table>/unresolved-questions.md` -- row `<question_id>`: `Status` flipped `open` -> `answered`; `Resolution` filled with the decision + date + owner
- `mappings/<table>/readiness-status.yaml` -- `approvals[]` entry appended: `stage: <stage>`, `owner: "<Person Name> (<analyst | governance | data_owner | metric_owner>)"` (the NAMED decider + authority class -- RS1 rejects a role-only owner and it does NOT satisfy the stage approval), `at: <date>`
- `<... any further artifact the request named, e.g. mappings/<table>/source-map.yaml a recorded mapping>`

> **Serialization (verbatim per target).** In `readiness-status.yaml`
> `approvals[].owner` the console writes the FULL named-decider shape
> `"Person Name (authority_class)"` with the class in underscore spelling
> (e.g. `"Ahmed Shaaban (data_owner)"`) -- RS1 flags a role-only owner as invalid
> and it does not count toward the stage approval (audit C4). In the
> `unresolved-questions.md` "Who must answer" cell the bare class keeps its
> hyphen spelling (`data-owner`). The console never renames or collapses the
> three base classes (analyst / governance / data-owner). `metric-owner`
> (additive, F009) appears only for a metric-contract question (see the docs page).

## remaining_blockers

This is EXACTLY why a recorded decision does NOT always mean the stage is `pass`. List
each reason the stage cannot yet flip -- a missing write-back target, an authority-class
mismatch surfaced, missing required stage evidence, or a duplicate-question defect. An
empty list means nothing is left blocking THIS decision (the stage still flips only per
the rule below).

- `<e.g. missing target: mappings/<table>/readiness-status.yaml not writable -- approvals[] entry not yet applied>`
- `<e.g. stage evidence absent: <stage> requires <the stage's own evidence, e.g. live retail validate result> before pass>`
- `<... or: none>`

## The `pass`-flip rule (mechanical, gated -- never discretionary)

A readiness stage flips to `pass` ONLY when BOTH already exist: a NAMED HUMAN approval
(this decision, recorded) AND the stage's own required evidence (e.g. the live
`retail validate` result for Gold Ready). The console flips the stage as the executor
of an already-made decision; it is NOT a discretionary approver. If either is absent,
the decision is recorded and the stage stays as it was, with the gap listed in
`remaining_blockers` above. A `pass` flip happens only after BOTH write-throughs land
alongside the stage's required evidence (FR-007, FR-008).

## Conflict + amendment posture

- **Contradicts a prior approval:** if this decision contradicts a prior recorded
  `approvals[]` entry, the console SURFACES the conflict as a finding and does NOT
  silently overwrite the prior approval (FR-010; surface, never bury).
- **Stage already `pass`:** a new decision on an already-passed stage is recorded as an
  AMENDMENT with its own `approvals[]` entry and surfaced for review -- never a silent
  re-pass.

## See also

- The operator guide + the boundary: `docs/tools/approval-console.md`.
- The decision package this answers: `templates/approval-request.md`.
- The Resolution + Status this writes through to: `templates/unresolved-questions.md`.
- The `approvals[]` slot this appends to: `templates/readiness-status.yaml`.
- The console verb: `.claude/skills/approval-console/SKILL.md`.
- The model + no-fake-confidence rule: `docs/readiness/readiness-model.md`.
- The category it realizes: `docs/architecture/product-modules.md` (F024; Product Module
  / `artifact-writing`). C086 is a cited filled instance: a filled worked example under
  `docs/worked-examples/`.
