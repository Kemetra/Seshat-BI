# Owner rulings for the remaining issues -- decision record

- **Date:** 2026-07-26
- **Status:** **RULINGS RECORDED.** Two decisions were put to the repository
  owner and both were ruled. Recorded before implementation, for the same reason
  as [the nine-issue record](2026-07-26-nine-issue-rulings.md): a delegated
  ruling that is written down is legitimate governance; the same ruling encoded
  silently in a patch is not.
- **Scope:** issues #474, #485, #488, #494, #507, #508. Issue #469 (F016 slices
  5-6) is excluded by the owner, as before.

## Triage first: only two of six were mechanically buildable

Every issue was checked for a *buildable increment* before any agent was
assigned -- because assigning work to an issue whose remaining scope is a
blocked ADR or an already-rejected rule produces a no-op PR.

| Issue | Remaining scope | Verdict |
|---|---|---|
| #507 | 2 real single-lane emissions | **buildable** |
| #508 | encoding mismatch + dead fallback | **buildable** |
| #485 | A2's write path | **buildable once ruled** (ruled: yes) |
| #488 | only the census-blocked rule | **ruled closed** |
| #494 | only the ADR-0001-blocked TOM path | **not buildable** |
| #474 | authoring a brief that does not exist | **not delegable** |

## R7 -- #485: `seshat validate` MAY write a committed provenance artifact

The A2 spec named exactly one blocking question: *"May `seshat validate` write a
committed artifact at all?"* -- today it connects, prints findings, sets an exit
code, and deliberately persists nothing.

**Ruled: yes.** Build A2.

Scope of the authorization, stated narrowly so it cannot be read as a general
licence to write:

- `validate` may persist **one** committed provenance record, via the
  already-built-but-unwired `readiness_evidence.py` (EMIT-only per FR-013).
- The value is a **digest of the server-echoed** `select current_database()` --
  not an env-derived string. Server-echoed is the whole point: the database
  asserts its own identity, so the claimant cannot type it. This is what makes
  A2 trustworthy where A1 was not.
- **Never a raw host or dbname.** `ANALYTICS_DB_NAME` is on this repo's own
  secret/redaction lists (`dagster_adapter/redaction.py:53`,
  `rules/git_meta.py:506,513`, `severity_posture.py:375`); committing one would
  trade a correctness bug for a secret-hygiene bug.
- The reader (`next`/`status`) compares **configuration only** and never opens a
  connection -- the documented no-DB/no-network contracts of `agent_next.py`,
  `status_surface.py`, and `run_next.py` stay intact.
- Use the `source_kind` precedent (commit `64e3f88`, #120): optional field, gate
  fires **only when present**, zero migration. Absence keeps today's behavior
  plus the shipped B caveat.
- **A1 stays rejected.** No hand-authored provenance field, ever -- a digest a
  claimant can type is worse than honest silence.

Not authorized by R7: any other write from `validate`, any numeric score,
projecting the field into the output JSON contract (severable, and not needed to
close #485), and any change to what `validate` reports.

## R8 -- #488: closed; the signposting WAS the fix

The Mapping-Ready fail-closed shape rule stays rejected, and the issue closes.

Rationale. The issue's own second suggested direction -- *"have `seshat next`'s
guidance ... explicitly point at the canonical shape"* -- is fully delivered by
PR #506: `CANONICAL_SOURCE_MAP_SHAPE_HINT` names all eight required **nested**
fields (`meta.table_id`, `meta.primary_key`, `gold_star.fact.name`,
`gold_star.fact.measures`, `gold_star.dimensions[].name`,
`gold_star.dimensions[].surrogate_key`, `gold_star.date_dimension.name`,
`gold_star.date_dimension.surrogate_key`), states that `columns` is *not*
required there but is read by the drift/PII/currency surfaces, and warns that
editing a map whose gate has already passed means re-entering that gate for a
fresh named-human approval. The reader now learns the shape **before** Gold
Ready, which was the defect.

The rule remains blocked by evidence, not by preference:
`mappings/demo_sample_orders/source-map.yaml` is a **real gate artifact** (six
`pass` entries in its `readiness-status.yaml`) with `meta` absent **and** a bare
`str` at `gold_star.fact` where canonical is a `dict` -- so even a *present-only*
structural rule fires on main's own artifact, and a new rule must be no-finding
on main to land.

**The demo artifact is explicitly NOT to be edited** to make a future rule pass.
That would be editing evidence to fit a rule. The census is pinned by tests, so
this is revisitable if the ground truth ever changes -- which is why closing
loses nothing.

## Not ruled, because these are not rulings to make

Recorded so the boundary is visible rather than implied:

- **#494's full TMDL validation** needs the `TmdlSerializer`/TOM path that
  **ADR-0001 deliberately excluded** to keep this toolchain headless, routing to
  F016 under **unratified ADR-0018**. Ratifying an ADR is owner work, and #469
  (the F016 slice) is out of scope by the owner's own instruction. The shipped
  narrow lint is complete for its scope; there is no further headless increment.
  Status recorded on the issue; it stays open.
- **#474's remaining criterion** is authoring
  `mappings/retail_store_sales/narrative-brief.md`, which **does not exist** --
  so it is not "migrate a map" but *write a decision-questions document from
  scratch* for a signed artifact, "under named-owner review" per the acceptance
  criteria. That is content authorship, not design. Delegation of design rulings
  does not extend to it. Stays open, correctly scoped.

## Governance

Both rulings above were made by the repository owner in this session and are
recorded here before implementation. Neither grants a readiness stage, ratifies
an ADR, self-approves a gate, emits a confidence score, or edits a signed
artifact. R7 authorizes exactly one new write and constrains its content.
