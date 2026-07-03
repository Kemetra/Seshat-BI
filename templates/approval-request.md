<!--
=============================================================================
 approval-request.md  --  the copy-me DECISION PACKAGE for one raised judgment call
=============================================================================
 Tower BI Agent Kit  -  Layer 1-6 (all stages), feature F027 (Approval Console).
 On-disk spec: specs/021-approval-console/ . When the spec-dir number (021) and
 the roadmap F-number (F027) disagree, the roadmap F-number wins: this is F027.
 See: docs/tools/approval-console.md (the operator guide + the boundary),
      templates/approval-decision.md (the recorded answer this request is decided into),
      templates/unresolved-questions.md (the Open-questions row a request packages),
      templates/readiness-status.yaml (the approvals[] slot a decision appends to).

 WHAT THIS IS
   A GENERIC, copy-me template. One filled copy turns ONE raised judgment call --
   a row in a table's unresolved-questions.md, a grain-confidence stop (F008), or
   an open blocker the control room lists (F012) -- into a reviewable DECISION
   PACKAGE: the question, the evidence, the options, the impact, the authority
   class required to decide, and the exact committed artifacts to update once a
   named human answers. A request POSES a decision; it NEVER answers it. There is
   NO selected_option field here -- the answer lives in approval-decision.md.

 THE TRANSCRIBE-NEVER-AUTHOR BOUNDARY  (verbatim across all F027 artifacts -- do not drift)
   The console TRANSCRIBES a human decision and WRITES it into the committed
   artifacts; it does NOT pick the option, supply or forge the owner, invent the
   rationale, auto-accept a recommended default, or move a readiness stage to
   `pass` without the stage's required evidence AND a named human approval. The
   named human decides; the console records. If no human answer exists, there is
   nothing to record and the request stays open.

 WHICH PRINCIPLES THIS INSTANTIATES  (cite, do not re-decide)
   .specify/memory/constitution.md
     V    Agent Stops at Judgment Calls  this template IS the committed, decidable
                                         form of a stop-and-ask -- the agent raises
                                         it and never resolves it alone.
     VII  C086 Is An Example ........... every value below is an obvious placeholder;
                                         C086 is CITED as the filled instance, never
                                         inlined (FR-013).
     IX   Secrets & Reproducibility .... ASCII + UTF-8 no BOM; short repo-relative
                                         paths (Windows 260-char budget); no secrets.

 NO FAKE CONFIDENCE  (hard rule #9 / readiness-model.md)
   A request carries explicit status + evidence + blockers ONLY. There is NO
   numeric / health / confidence score field anywhere, and a filled copy MUST NOT
   add one. Evidence is a MEASURED number traceable to a committed source path,
   never an adjective and never an invented figure.

 HOW TO USE
   Copy this file, delete this comment banner, and fill every <ANGLE-BRACKET>
   field for the one judgment call being packaged. Where the filled copy lives is a
   path choice recorded in the operator guide (the authoritative write-back is into
   the per-table unresolved-questions.md + readiness-status.yaml; an optional
   standalone copy may live under the per-table working set). Generic only -- no
   C086 / retail_store_sales values.
=============================================================================
-->

# Approval Request -- `<question_id>`

- **question_id:** `<stable short id; MUST match the unresolved-questions.md row id, e.g. Q3>`
- **stage:** `<one of: source_ready | mapping_ready | silver_ready | gold_ready | semantic_model_ready | dashboard_ready | publish_ready>`
- **subject:** `<the source / table / report this decision is about, e.g. silver.<table_id>>`
- **owner_required:** `<analyst | governance | data-owner | metric-owner>`  *(the authority class -- see below)*
- **status:** `open`  *(a request is `open` until a named human answers it via approval-decision.md; it never answers itself)*

## Decision needed (one sentence)

> `<the single judgment call, stated in one sentence the named owner can answer yes/no or pick-an-option to>`

## Evidence (measured numbers + committed source paths)

Each line is a MEASURED number or fact, with the committed source path (and row/line
where applicable) it was read from. A value with no traceable origin is a defect
(FR-012). Never invent a number; if the evidence is not yet measured, see below.

- `<e.g. row count = <n>  (source: mappings/<table>/source-profile.md, line <n>)>`
- `<e.g. candidate PK not unique: <n> duplicate keys  (source: mappings/<table>/source-profile.md)>`
- `<... add one line per measured fact this decision turns on>`

> **Evidence incomplete:** if a required number has not yet been measured, record
> `evidence incomplete: <source>` here and do NOT invent the number or an option
> (no fabricated confidence). The request is not decidable until the evidence lands.

## Options

The discrete choices the owner picks among. List them; do NOT mark one chosen (that
is the decision, recorded in approval-decision.md `selected_option`).

- **A.** `<option A, stated concretely>`
- **B.** `<option B>`
- `<... add one per real option>`

## Impact (per option)

For EACH option above, the concrete downstream consequence -- what it changes in the
build, what it commits the table to. This is what the owner weighs.

- **A ->** `<what choosing A means downstream, e.g. which silver column / grain / rollup it fixes>`
- **B ->** `<what choosing B means downstream>`
- `<...>`

## recommended_default (optional)

The default the SOURCE carries (e.g. the relevant ADR 0002 RC default) IF it has one
traceable to a committed source. If the console cannot trace a default to a committed
source, OMIT this section rather than inventing one (edge case: a default with no source).

- **default:** `<the recommended default, cite ADR RC<n> if applicable; or omit this section>`
- **NOT auto-accepted:** accepting this default is STILL a decision and MUST be recorded
  by the named owner as an explicit approval-decision.md (owner + date + rationale). The
  console NEVER accepts a recommended default on the human's behalf (FR-006).

## artifacts_to_update_after_decision

The exact committed artifacts the decision is written through to once a named human
answers. At minimum, both write-back targets below; add any the request specifically
names. The decision (approval-decision.md) records WHICH of these were updated and any
that were missing/unwritable as `remaining_blockers`.

- `mappings/<table>/unresolved-questions.md` -- the matching row's `Resolution` cell + `Status` flipped `open` -> `answered`
- `mappings/<table>/readiness-status.yaml` -- an `approvals[]` entry (stage + owner + `at`)
- `<... any further artifact this specific decision updates, e.g. mappings/<table>/source-map.yaml a recorded mapping>`

## Authority class (who may decide)

The decider's authority class MUST match the question class (FR-009); a decision under
the wrong class is refused by the console:

- **analyst** -- business meaning / grain / rollups
- **governance** -- PII / publish-safety sign-off
- **data-owner** -- source semantics / upstream truth
- **metric-owner** -- metric contracts (an ADDITIVE extension class from F009 metric
  contracts; NOT present in the base unresolved-questions.md template -- used only for a
  metric-contract question; see docs/tools/approval-console.md)

> **Serialization note.** When the decision is written back, the console uses each
> TARGET artifact's existing spelling verbatim. In `readiness-status.yaml`
> `approvals[].owner` it writes the FULL named-decider shape
> `"Person Name (authority_class)"` with the class in underscore spelling
> (e.g. `"Ahmed Shaaban (data_owner)"`) -- RS1 rejects a role-only owner and it
> does not satisfy the stage approval (audit C4). In the `unresolved-questions.md`
> "Who must answer" cell the bare class keeps its hyphen spelling (`data-owner`).
> It never renames or collapses the three classes the base unresolved-questions.md
> template carries (analyst / governance / data-owner).

## Duplicate guard

A given `question_id` MUST resolve to exactly ONE request. If the same `question_id` is
packaged twice, the console surfaces the duplicate as a `remaining_blockers` line and
DECLINES to create a second decidable request -- the one existing request is
authoritative. Never create a second decidable copy of the same question.

## See also

- The operator guide + the boundary: `docs/tools/approval-console.md`.
- The recorded answer this is decided into: `templates/approval-decision.md`.
- The Open-questions row this packages: `templates/unresolved-questions.md`.
- The `approvals[]` slot the decision appends to: `templates/readiness-status.yaml`.
- The console verb: `.claude/skills/approval-console/SKILL.md`.
- The model + no-fake-confidence rule: `docs/readiness/readiness-model.md`.
- The category it realizes: `docs/architecture/product-modules.md` (F024; Product Module
  / `artifact-writing`). C086 is a cited filled instance: a filled worked example under
  `docs/worked-examples/`.
