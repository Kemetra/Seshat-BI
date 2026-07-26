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
- The value is a **digest of a server-echoed identity** -- not an env-derived
  string. Server-echoed is the whole point: the database asserts its own
  identity, so the claimant cannot type it. This is what makes A2 trustworthy
  where A1 was not. **See the two amendments below for what that identity must
  contain and how it must be obtained** -- the first draft of this ruling was
  wrong on both counts.

#### R7 amendment 1 -- the digest MUST include the SERVER, not just the database

Raised in review of this record (P1) and **verified**. The first draft said "a
digest of the server-echoed `select current_database()`", which is
**insufficient**: staging and production commonly share a database *name* on
different hosts, so a name-only digest **matches for both** and `next`/`status`
could not detect that validation ran against the wrong live system. That defeats
A2's entire stated purpose -- proving *which* system earned the evidence.

It also silently narrowed the parent design note, which already specified
`sha256("<host>/<dbname>")` (`2026-07-25-live-db-provenance-design.md:163`).

**Ruled:** derive the digest from a **server-confirmed endpoint plus the echoed
database name** -- both server-asserted, so neither is typed by the claimant --
while continuing to persist **neither raw value**. If a server-confirmable
endpoint cannot be obtained for a given engine, say so and record the limitation
rather than silently falling back to a name-only digest that cannot distinguish
two systems.

#### R7 amendment 3 -- the identity must be COMPARABLE OFFLINE, or it is not usable

Raised in review (P1) and **verified as a real hole in amendment 1**. Amendment 1
said the endpoint "must come from the connection the server confirms, not from
`.env`". Taken literally that breaks the comparison, because the **reader is
configuration-only and never connects** (a hard constraint of R7):

- with a DNS alias, proxy, PgBouncer, or load balancer in front of the database,
  the server-confirmed endpoint commonly reports a **backend address or instance**
  rather than the configured hostname;
- the writer would then hash a different value than the config-only reader derives
  for the *same* database, and A2's present-but-mismatching path would
  **downgrade valid evidence with a blocker** -- a false positive on the exact
  signal A2 exists to provide.

A provenance check that cries wolf gets disabled, so this must be settled before
implementation, not after.

**Ruled:** A2 requires a **canonical identity that BOTH sides can derive
independently** -- the writer at connect time and the reader from configuration
alone -- and the digest is computed over that canonical form. Concretely, the
implementation must:

1. define the canonicalization explicitly (normalized host as configured, port,
   database name), and document which components are included;
2. use the server-echoed values to **confirm and correct** the *database name*
   (which the server reports reliably and the claimant would otherwise be free to
   type), rather than to source a backend address the reader can never see;
3. where the server-reported endpoint and the configured endpoint disagree,
   treat that as **outside the digest** -- do not silently fold an unreachable
   value into a hash the reader must reproduce;
4. if no canonical form can be derived that both sides reproduce for a given
   deployment shape, record **no field** (the safe legacy absent path) rather than
   one that mismatches for a correct setup.

The governing principle: **the digest's job is to make a wrong database
detectable without making a right one look wrong.** Prefer a false *negative*
(no field, caveat persists) over a false *positive* (valid evidence blocked).

#### R7 amendment 2 -- the identity query MUST be dialect-provided

Raised in review (P2) and **verified**: `src/seshat/dialect.py` implements
**four** engines (`postgres`, `sqlserver` at `:219`, `mysql` at `:452`,
`snowflake`), and `validate`'s body selects among them. Mandating
`select current_database()` would **fail** on SQL Server (`DB_NAME()`) and MySQL
(`DATABASE()`).

**Ruled:** the identity expression is **dialect-provided**, resolved through the
existing dialect layer alongside every other engine-specific query -- never a
Postgres literal hardcoded into the provenance path. Follow the precedent already
set by `_db_extra_hint(engine)` (`cli/__init__.py:291`), which selects the right
driver per engine rather than assuming Postgres. If an engine cannot supply an
identity expression, that engine records no provenance field (the legacy
absent path) rather than a wrong one.
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
`mappings/demo_sample_orders/source-map.yaml` is a **real gate artifact** --
`source_ready`, `mapping_ready`, and `silver_ready` are all `pass` (`gold_ready`
is `blocked`; the remaining three stages are `not_started`) -- with `meta` absent
**and** a bare
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
  **ADR-0001 deliberately excluded** from the static core to keep this toolchain
  headless. The shipped narrow lint is complete for its scope; there is no
  further *headless* increment. It stays open.

  **Correction (raised in review of this record, verified):** an earlier draft
  routed this through "unratified ADR-0018", which is **wrong**. ADR-0018
  (`docs/decisions/0018-unpark-f016-power-bi-mcp-execution-adapter.md`) is the
  gate for F016's **execution-only** slices -- approval-gated *mutations* (slice
  5) and the remote server (slice 6) via Microsoft's Power BI MCP. It neither
  authorizes nor provides a TOM **validation** path, so ratifying it would leave
  #494's gap exactly where it is.

  What #494 actually needs is a **separate optional-validator decision** against
  ADR-0001 -- i.e. whether a TOM-dependent validator may ship as an *optional
  extra* outside the static core, which is a different question from unparking an
  execution adapter. That decision is not made here, and #494 must not be
  described as blocked on #469 or on ADR-0018.
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
