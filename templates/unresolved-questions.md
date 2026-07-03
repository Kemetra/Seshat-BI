# Unresolved questions -- `<table-id>`

> **Template.** One per table being mapped. Copy to `mappings/<table>/` (per
> [ADR 0003](../docs/decisions/0003-mapping-artifact-location.md)) and fill the
> placeholders. ASCII only.
> **Note on links:** the `../docs/...` links below are relative to `templates/`
> (one level deep). `mappings/<table>/` is **two** levels deep, so after copying,
> change `../docs/...` to `../../docs/...`.
>
> **What this file is for.** The open questions that **block** the build -- the things
> the agent (or analyst) **cannot decide alone**. It is the committed, reviewable form
> of the [medallion playbook](../docs/medallion-playbook.md)'s **Phase 2 analyst
> decision points** and its **Phase 4 review gate**. No `silver.*` SQL is written until
> every blocking question here is `answered` (the source-mapping gate --
> [architecture Sec 5](../docs/architecture/tower-bi-agent-kit.md)).
>
> **Sibling artifacts (read as a set):**
> [`source-profile.md`](./source-profile.md) (Phase 1 -- the numbers these questions
> reference), [`source-map.yaml`](./source-map.yaml) (Phase 2.0-2.5/2.7-2.8 -- the
> machine-readable decisions), [`assumptions.md`](./assumptions.md) (Phase 2+3 -- ADR
> defaults adopted vs deviated), and [`reconciliation-report.md`](./reconciliation-report.md)
> (Phase 5/6 -- the live acceptance checks). A question answered here usually becomes a
> recorded decision in `source-map.yaml` and/or a deviation in `assumptions.md`.
>
> **Rule (from the playbook's interaction protocol):** the agent **recommends, the
> analyst decides**. Never resolve a blocking question silently. If an answer
> contradicts an earlier decision or a profiled data fact, stop and reconcile.
> **Generic placeholders only** -- do not bake one table's answers (codes, segment
> names, PII columns) into this template. See a filled worked example under
> `docs/worked-examples/` for a filled instance.

---

- **Table id:** `<table-id>` (e.g. `<C0xx-source-name>`)
- **Date raised:** `<YYYY-MM-DD>`
- **Raised by:** `<agent | analyst-name>`
- **Maps to playbook phases:** Phase 2 (decision points) + Phase 4 (review gate)
- **Gate status:** `<OPEN | CLEARED>` -- the build is blocked until every row below is
  `answered` (or its proposed default is explicitly accepted by the named owner).

---

## Open questions (the build is blocked until these are `answered`)

Each row is one decision the agent could not make alone. `Who must answer` is the
authority required: **analyst** (business meaning / grain / rollups), **governance**
(PII / publish-safety sign-off), or **data-owner** (source semantics / upstream truth).
The `Proposed default` is what the agent recommends *if the question goes unanswered* --
usually the relevant ADR 0002 default (RC1-RC16); accepting it is still a decision and
must be recorded by the owner.

| ID | Question | Why it blocks | Who must answer | Proposed default (if unanswered) | Status | Resolution |
|----|----------|---------------|-----------------|----------------------------------|--------|------------|
| Q1 | `<the open question, in one sentence>` | `<what downstream artifact / decision cannot proceed without it>` | `<analyst \| governance \| data-owner>` | `<recommended default, cite ADR Dn if applicable>` | `open` | `<blank until answered; record the decision + date + who>` |
| Q2 | `<...>` | `<...>` | `<...>` | `<...>` | `open` | `<...>` |
| Q3 | `<...>` | `<...>` | `<...>` | `<...>` | `open` | `<...>` |

> Add rows as needed. Do **not** delete answered rows -- flip `Status` to `answered`
> and fill `Resolution` so review sees the audit trail.

### Categories to prompt for (do not leave a category unconsidered)

These are the recurring decision classes the agent must **raise rather than guess**.
For each, either record a question above or state in [`assumptions.md`](./assumptions.md)
that the ADR default was adopted with no ambiguity. Each cites the playbook phase that
surfaces it.

- **Grain ambiguity** (Phase 2.0; ADR **RC1/RC2**). Does one row mean what the candidate
  key implies? If row count vs business-entity count does not match the assumed grain,
  or the candidate PK is not unique on the data, raise it -- grain fixes the
  non-droppable keys, so it cannot be deferred. *Default:* lowest grain the source
  provides (RC1); verify PK on transformed data (RC2).

- **PII judgment calls** (Phase 2.2; ADR **RC4**; **governance** sign-off). Any kept
  column that *might* be personal/sensitive and would reach the BI layer (a published
  dataset is effectively irreversible). The agent does **not** decide "this is safe to
  publish" alone. *Default:* drop the column (RC4); if a need is asserted, governance
  must sign off on hash/mask/isolate -- never rely on row-level security to hide a
  *column*.

- **Business-rollup mappings** (Phase 2.7; ADR **RC11**; **analyst**-supplied). A
  higher-level grouping over source values (e.g. a segment/category rollup). **The
  playbook NEVER invents this mapping** -- it must be analyst-supplied. If a rollup is
  wanted, the analyst provides the full value->group table. *Default:* no rollup;
  if added, unmapped values fall to an explicit `UNMAPPED` bucket (RC11), and note
  whether the rollup is a merchandising axis vs a structural one.

- **Sentinel-vs-null choices** (Phase 2.4; ADR **RC5/RC6**). For each column with missing
  values: NULL (genuinely unknown) or a grouping sentinel (`UNKNOWN`/`UNCLASSIFIED`)?
  A sentinel is justified only for a **dimension attribute that must group cleanly**,
  and only after verifying it collides with no real value. *Default:* `''`->NULL on all
  columns first (RC5); NULL unless a grouping need is stated (RC6).

- **Returns identification** (Phase 2.6; ADR **RC8**; **data-owner** confirms the
  authoritative column). Which source column authoritatively marks a return (billing /
  transaction type)? Returns must be flagged from that column, **never** from the
  measure sign alone (the sign misses zero-value and edge-case returns). *Default:*
  keep returns + derive `is_return` from the authoritative type column (RC8); if the
  authoritative column is unknown, this is a blocking data-owner question.

- **Hierarchy multi-parent handling** (Phase 2.8; ADR **RC12**). Is the category
  hierarchy a clean tree, or does a child appear under multiple parents (verify on the
  data)? If not a tree, forcing a single parent destroys real overlap. *Default:* flat
  denormalized levels, one path per row so totals do not double-count (RC12); a snowflake
  is not the default.

> **Namespace note (flagged, not resolved here).** The `Dn` ids above refer to **ADR
> 0002 cleaning/modeling defaults (RC1-RC16)** in
> `docs/decisions/0002-retail-cleaning-defaults.md`. These are a **different namespace**
> from the `retail check` governance checker's TMDL/DAX rules (`D1-D8`). Distinct prefixes,
> distinct namespaces -- no collision (disambiguated in feature 002). A cleaning default
> reads `RC<n>`; a checker rule reads `D<n>`.

---

## Kit-level open decisions (inherited)

These are **not** per-table questions -- they are the architecture's own open decisions,
inherited by every table that passes through the kit. They are restated here so a
reviewer reading one table's gate also sees what is unsettled kit-wide. Authoritative
source: [`docs/architecture/tower-bi-agent-kit.md` Sec 9](../docs/architecture/tower-bi-agent-kit.md).
Marked in Spec-Kit `[NEEDS CLARIFICATION]` style; do **not** resolve them in a per-table
file.

- **[RESOLVED -- feature 002] D-namespace disambiguation.** ADR 0002 cleaning defaults are
  now **RC1-RC16** ("retail cleaning"); the `retail check` governance checker keeps its
  separate **D1-D8** TMDL/DAX rules. Distinct prefixes, no collision -- this was the
  disambiguation required before any ADR default is wired into `retail check`.

- **[NEEDS CLARIFICATION: per-table mapping artifact location]** Where the five mapping
  artifacts (`source-profile.md`, `source-map.yaml`, `assumptions.md`,
  `unresolved-questions.md`, `reconciliation-report.md`) live **per table** is undecided:
  a `mappings/<table-id>/` directory, alongside the silver migration, or under `docs/`.
  Until decided, keep a table's five artifacts together in one place and link them
  relative to each other (as this template's header does).

- **[NEEDS CLARIFICATION: agent orchestration shape]** Which agent / skill drives the
  playbook conversationally (Layer D), and how it self-heals against the `retail check`
  gate, is **designed as a seam, not a runtime** in this slice. The mechanism that
  reads this file, asks the analyst the `open` questions, and writes back `Resolution`
  is a later slice.

- **[NEEDS CLARIFICATION: deferred `retail validate` live surface]** The live-validator
  categories ([architecture Sec 7](../docs/architecture/tower-bi-agent-kit.md): PK
  uniqueness on materialized rows, date-dim coverage, 0 orphan FKs, cross-layer measure
  reconciliation) are **documented only** -- no validator logic exists. They need their
  own spec before implementation. Until then, the [`reconciliation-report.md`](./reconciliation-report.md)
  artifact is filled **manually** from a live DB run, not by an automated validator.

---

## See also

- **Method:** [`docs/medallion-playbook.md`](../docs/medallion-playbook.md) -- Phase 2
  (analyst decision points) and Phase 4 (review gate) are what this file commits.
- **Defaults:** [`docs/decisions/0002-retail-cleaning-defaults.md`](../docs/decisions/0002-retail-cleaning-defaults.md)
  -- the RC1-RC16 defaults referenced as proposed answers above.
- **Architecture:** [`docs/architecture/tower-bi-agent-kit.md`](../docs/architecture/tower-bi-agent-kit.md)
  -- Sec 5 (source-mapping gate), Sec 9 (open decisions inherited above).
- **Sibling templates:** [`source-profile.md`](./source-profile.md),
  [`source-map.yaml`](./source-map.yaml), [`assumptions.md`](./assumptions.md),
  [`reconciliation-report.md`](./reconciliation-report.md).
- **Filled instance:** a filled worked example under `docs/worked-examples/` (an
  example, never the universal schema).
