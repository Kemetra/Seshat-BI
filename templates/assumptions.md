# Assumptions -- `<table-id>`

> **Template.** A generic, per-table record of which ADR 0002 cleaning/modeling
> defaults (`RC1`-`RC16`) this table **adopted as-is** versus **deviated from**. It is
> the engineering expression of the constitution principle **"Defaults Then
> Deviations"** (`.specify/memory/constitution.md`): start from the shared rulings,
> document only what changed and why.
>
> This file is **not** the per-table ADR. It is the at-a-glance checklist that points
> to the full rationale. Each deviation's reasoning lives in the table's own ADR (see
> the ADR 0002 Consequence: deviations are recorded "in its own ADR"). Replace every
> `<placeholder>` and delete this blockquote when filling it in.

| Field | Value |
|-------|-------|
| Table id | `<table-id>` (e.g. `silver.<source>`) |
| Date | `<YYYY-MM-DD>` |
| Author | `<name>` |
| Source profile | `templates/source-profile.md` -> `<filled path>` (the profiled **evidence**) |
| Source map | `templates/source-map.yaml` -> `<filled path>` (the keep/drop/type/grain/star **decisions**) |
| Per-table ADR | `<this table's own ADR for deviations, e.g. docs/decisions/00NN-<table>-deviations.md>` |

**Where this sits in the data flow:** `source-profile.md` (evidence) +
`source-map.yaml` (decisions) `->` **`assumptions.md`** (which ADR defaults held, which
were overridden). The 16 rows below are exactly the ADR 0002 defaults `RC1`-`RC16`.

---

## Defaults adopted as-is

Confirm each ADR 0002 default. `[OK]` = adopted unchanged; `[x]` = deviated (record it
in **Deviations** below). The "Default summary" column states the **generic ruling
only** -- no per-table specifics; the triggering data lives in `source-profile.md`.

| ADR id | Default summary (generic ruling) | Adopted? | Note |
|--------|----------------------------------|----------|------|
| RC1  | Model at the lowest grain the source provides; decide grain first. | `[OK]` | |
| RC2  | Verify the PK on the data, and re-verify on the transformed output. | `[OK]` | |
| RC3  | Drop no-signal columns (100%-empty, single-value, verified dup, code half of a 1:1 code/label pair). | `[OK]` | |
| RC4  | Remove PII/sensitive data before the BI layer, decided early (not at review). | `[OK]` | |
| RC5  | Treat the empty string as missing: `''` `->` NULL first; measure missingness as `'' OR NULL`. | `[OK]` | |
| RC6  | Fill policy: NULL for unknown facts; sentinel only on grouping dims, after a no-collision check. | `[OK]` | |
| RC7  | Money/qty `->` exact `NUMERIC`; dates `->` `DATE`; leading-zero IDs/codes stay `TEXT`. | `[OK]` | |
| RC8  | Keep returns; derive `is_return` from the authoritative type column, never the measure sign. | `[OK]` | |
| RC9  | Keep the independent money measures (gross/net/tax/discount); drop only true duplicates. | `[OK]` | |
| RC10 | Unify categorical encodings to one standard; keep the original code if it is a stable join key. | `[OK]` | |
| RC11 | Add business rollups only from an analyst-supplied mapping; never invent the mapping. | `[OK]` | |
| RC12 | Model a non-tree hierarchy as flat denormalized levels, not a snowflake. | `[OK]` | |
| RC13 | Materialize silver as a TABLE via an idempotent numbered migration; transform order is load-bearing. | `[OK]` | |
| RC14 | Gold is a Kimball star: surrogate `_sk` keys, `-1` unknown member + FK `COALESCE`, degenerate dims. | `[OK]` | |
| RC15 | Date dimension is a contiguous generated calendar over the full span (never `SELECT DISTINCT date`). | `[OK]` | |
| RC16 | Reconcile measure totals at every layer and assert 0 orphan FKs before declaring the build done. | `[OK]` | |

**Integrity invariant (the rule a reviewer checks):** every row marked `[x]` above
**must** have a matching entry in **Deviations** below, and every adopted row stays
`[OK]`. The two sections are two views of the same set of 16 rulings; if a row is `[x]`
with no deviation entry (or vice versa), the document is inconsistent and the review
gate should reject it.

> **Namespace note (disambiguated).** The `RC1`-`RC16` ids in this table are **ADR 0002
> cleaning/modeling defaults** ("retail cleaning"). The `seshat check` governance checker
> uses a separate `D1`-`D8` for its TMDL/DAX rules -- **distinct prefixes, distinct
> namespaces**, no collision. (Historically the ADR also used `D`; it was renamed to `RC*`
> in feature 002 because the checker ids live in code.) When this file says `RC7`, it
> means the ADR cleaning default; a checker rule would read `D7`. The two are unambiguous.

---

## Deviations

Record **only** the defaults this table overrode. If a table adopts all 16, this section
is empty (state that explicitly). Each deviation needs the **triggering data fact** --
the profiled evidence from `source-profile.md` that forced the override -- so the review
sees *why*, not just *what*. ADR 0002's "override when" clauses make a legitimate fork
visible; an override without a triggering fact is a red flag.

**Status for this table:** `<none -- adopted 16/16>` **OR** `<N deviations, listed below>`.

Fill one block per deviation (delete the placeholder block if there are none):

| Field | Value |
|-------|-------|
| ADR id | `<Dn -- the ADR 0002 default being overridden>` |
| What we did instead | `<the alternative ruling applied to this table>` |
| Triggering data fact | `<the profiled evidence that forced it -- cite the figure/finding in source-profile.md>` |
| Recorded in | `<the table's own ADR + section, e.g. docs/decisions/00NN-<table>-deviations.md>` |

> **No fabricated examples.** Do not invent a deviation to fill the shape. The first
> worked example, **C086**, adopted **16/16 defaults with 0 deviations** after live DB
> validation, so its `assumptions.md` Deviations section is empty -- a filled instance of
> "all defaults held." See a filled worked example under `docs/worked-examples/` and
> `docs/c086-adr0002-compliance.md`. A non-zero Deviations section looks like the block
> above, with real `Dn` ids and a real triggering fact from that table's profile.

---

## Kit-level assumptions

Inherited from the architecture and constitution; true for every table unless a future
slice changes them. They are *not* per-table decisions -- they frame the whole kit:

- **Gold-only for Power BI.** The semantic model reads the `gold` schema only; `bronze`
  and `silver` are upstream substrate, not query surfaces. (Governance design decision
  #3; architecture doc Sec. 4.)
- **Postgres-first medallion.** Storage is the DigitalOcean Postgres medallion
  (`bronze` `->` `silver` `->` `gold`). There is **no DuckDB/Parquet-first** copy in the
  MVP: Power BI Import caches columnar at refresh (VertiPaq), so a gold-as-Parquet copy
  would be a redundant second source of truth. (Architecture doc correction #5.)
- **Mapping before silver.** No `silver.*` SQL is written until the source is profiled
  and mapped into committed artifacts and that mapping is reviewed -- the **source-mapping
  gate**. This file is one of those gate artifacts. (Architecture doc Sec. 5;
  formalizes the playbook's Phase 1 + Phase 2.0-2.5 + Phase 4 review gate.)
- **`pbi-cli` is a later adapter, not the core.** The Power BI semantic-model engine is
  `pbi-cli` (depend-not-fork, installed via `pipx`), invoked at the build step -- it is
  not the center of the kit. (Governance design decision #1; architecture doc Sec. 4.)
- **Validators are categories only at this stage.** Static (`seshat check`, 23 rules,
  already on `main`) versus live (`retail validate`, deferred) are *documented
  categories*; no validator logic is implemented in this slice. The
  `reconciliation-report.md` template is the blank a future live run fills. (Architecture
  doc Sec. 7.)

---

## See also

A reviewer reads all of the kit's templates and docs as one set:

- **Sibling templates** (the source-mapping gate artifacts): `templates/source-profile.md`
  (Phase 1 evidence), `templates/source-map.yaml` (Phase 2.0-2.5/2.7-2.8 decisions),
  `templates/unresolved-questions.md` (Phase 2 decision points + Phase 4 gate),
  `templates/reconciliation-report.md` (Phase 5/6 live acceptance).
- **Defaults this file checks against:** `docs/decisions/0002-retail-cleaning-defaults.md`
  (`RC1`-`RC16`).
- **Constitution principle realized:** "Defaults Then Deviations" in
  `.specify/memory/constitution.md`.
- **Architecture:** `docs/architecture/tower-bi-agent-kit.md`.
- **Method:** `docs/medallion-playbook.md` (Phases 2 and 3 surface these adopt/deviate
  decisions).
- **Governance design:** `docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md`.
- **First worked example (filled instance, never the universal schema):**
  a filled worked example under `docs/worked-examples/` + `docs/c086-adr0002-compliance.md` -- 16/16
  defaults adopted, 0 deviations, validated live.
