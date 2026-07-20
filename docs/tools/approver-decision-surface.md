# retail approver-view -- Approver Decision Surface

A read-only Product Module (spec 115) that re-sequences ONE table's
ALREADY-COMMITTED readiness evidence into a refutation-first reading view for
the human signer: what would make them REFUSE first, reassurance last.

## What it does

For one table, it reads the committed `mappings/<table>/readiness-status.yaml`
and `mappings/<table>/unresolved-questions.md` and composes a "refusal case"
(blocked/warning stages' blocking reasons, approval-requiring stages with no
valid recorded approval, OPEN unresolved-questions rows) ordered ABOVE a
"reassurance" list (pass stages, recorded valid approvals, `answered`
questions). It fills the gap no shipped surface covers: `approval_inbox` sorts
by (source_path, stage-index); `blocker_explainer` sorts lexically and only
surfaces `blocked` (never `warning`, never questions); `run_next` is a
single-table next-action dispatcher; `readiness-viewer` renders `approvals[]`
chronologically. None reorders for "what would make me refuse to sign,
first", and none reads `unresolved-questions.md` at all.

## Run

```
retail approver-view --table <table>                # print the view (writes nothing)
retail approver-view --table <table> --format json
```

There is no `--write` flag -- the default (and only) mode is a pure read.

## The refusal-first ordering (fixed enum rank, never a score)

Every refusal item carries a `category` drawn from the SHIPPED fixed rank in
`readiness_classify.py`: `approval > grain > live_validation > artifact >
readiness`. Items sort by `(rank, source, reason)` -- the rank is a committed
lookup, never a computed priority/urgency/confidence value (hard rule #9).
Reassurance is always listed after the full refusal case, never interleaved.

An OPEN `unresolved-questions.md` row is assigned its category from the
committed `Who must answer` owner column, NEVER by scanning the question's
free-text prose: `governance` / `data-owner` -> the `approval` bucket (rank
1, top); `analyst` (or any other owner) -> classified by the same keyword
classifier used for blocking reasons, defaulting to `readiness` if
unrecognized. An `answered` row is never shown as an open refusal item -- it
may appear only as reassurance.

On the worked example, `retail_store_sales` is at `publish_ready` with all
stages `pass`, recorded approvals, and all four `unresolved-questions.md`
rows `answered` (Gate CLEARED). The view therefore shows an EMPTY refusal
case ("nothing to refuse... was found in the committed evidence") and lists
the passed stages / recorded approvals / answered questions as reassurance,
with no score anywhere.

## The scope wall (what it will NOT do)

- **Grants NO approval and moves NO stage.** It is a reading view, not a
  decision -- F027 approval-console owns the write-back (`approvals[]`, the
  `unresolved-questions.md` `Resolution` column, stage flips).
  never_self_grant_approval (Principle V) holds absolutely.
- **WRITES NOTHING.** No file-write path exists structurally in
  `approver_view.py` -- there is no `--write` flag at all, matching the
  three shipped read-only surfaces (`approval_inbox`, `blocker_explainer`,
  `run_next`).
- **Orders by a FIXED, COMMITTED enum rank -- never a synthesized
  priority/score.** The category rank is a lookup (`rank_of()`), not a
  computation; even expressed only as list position (not a printed number)
  it must never be rolled up from other signals (hard rule #9).
- **Emits NO score, count, or percentage** anywhere -- no "N blockers", no
  readiness percentage, no confidence value. Items are ordered and shown,
  not tallied.
- **Adds NO `seshat check` rule and NO gate.** No new blocking reason, no
  stage move; its presence/absence is never a gate requirement.
- **Reads ONLY the two committed artifacts** (`readiness-status.yaml`,
  `unresolved-questions.md`); opens no DB, Power BI, or network connection.
- **Never fabricates on a missing input.** If one of the two files is
  missing or unreadable, it composes from the input that IS present and
  names the missing one explicitly -- a missing `unresolved-questions.md` is
  reported as "could NOT be read", never silently treated as "no open
  questions".
- **Generic across tables (Principle VII):** no hardcoded table names,
  column names, PII categories, or grain keys.
- **Always exits 0.** It is not a gate (FR-007); a non-empty refusal case is
  not a failure exit.

## Boundary against neighbours

- **blocker_explainer** -- surfaces only `blocked` stages, sorts lexically
  (source, stage, reason), and never reads `unresolved-questions.md`. This
  surface widens the refusal case to `blocked` AND `warning` stages plus
  unmet approvals plus open questions, and reorders by the fixed category
  rank instead of lexical order.
- **approval_inbox** -- sorts by (source_path, stage-index); a queue of
  pending approvals, not a refutation-first reading order.
- **run_next** -- a single-table next-action dispatcher, not a full
  refusal/reassurance composition.
- **readiness-viewer** -- renders `approvals[]` chronologically (by `at`),
  the opposite ordering principle from refutation-first.
- **F027 approval-console** -- the write-back. This surface is its
  read-only companion: it never grants, never records, never moves a
  stage. Its absence is never a prerequisite for any readiness stage.
