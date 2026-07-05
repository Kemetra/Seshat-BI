<!--
=============================================================================
 consumer-data-dictionary.md  --  the generic copy-me consumer data dictionary
=============================================================================
 Seshat BI -- Product Module F040 (proposed; ledger row deferred to
 integration -- see research.md section 1.4). Spec:
 specs/101-consumer-data-dictionary/.
 Composer skill: .claude/skills/consumer-data-dictionary/SKILL.md.

 WHAT THIS IS
   A GENERIC, copy-me shape for ONE table's plain-language CONSUMER data
   dictionary. An analyst who has access to a published table/report reads
   one ordered document: every deployed gold column and every metric
   contract, each entry citing the committed artifact it came from. The
   module COMPOSES; it never invents. A column or metric with no committed
   consumer-legible meaning gets an explicit GAP marker, never invented
   prose. NO numeric score, NO completeness count, anywhere.

 THE F024 MODULE CONTRACT (banner -- reused by the skill; see SKILL.md for
   the fully-filled declaration)
   - Authority category: Product Module
   - Capability level: `artifact-writing` (exactly one; per docs/architecture/
     product-modules.md -- reads Core Authority, writes one derived artifact,
     executes nothing).
   - READS (never writes): warehouse/migrations/*_create_gold_<table>*.sql,
     mappings/<table>/source-map.yaml, mappings/<table>/metrics/*.yaml.
   - WRITES: this one derived dictionary at
     mappings/<table>/consumer-data-dictionary.md.
   - EXECUTES: none.
   - FORBIDDEN (the matrix says NO): no defining/approving/paraphrasing
     business meaning, no resolving an open mapping question, no writing
     back to any upstream source artifact, no numeric confidence/health/
     maturity score, no completeness/"N of M" count, no DB / Power BI / PBIP
     read, no deferred adapter (F016) or spec-only runtime (F031-F033).

 HOW TO USE
   The skill FILLS one copy of this shape as
   mappings/<table>/consumer-data-dictionary.md. Fill every <ANGLE-BRACKET>
   placeholder from a committed source; a column or metric with no committed
   consumer-facing meaning becomes an explicit GAP marker (never invented,
   never paraphrased -- see the OPEN FR-008/Q1 owner ruling in SKILL.md).
   ASCII only, UTF-8 no BOM (use `--` and `->`, no glyphs); short
   repo-relative paths (Windows 260-char budget). Delete this comment banner
   in a filled copy. GENERIC -- no worked-example (C086 / retail_store_sales)
   column name, grain key, or metric name anywhere in a fixed label.
=============================================================================
-->

# Consumer Data Dictionary -- <table>

> A plain-language reference for every deployed gold column and every metric
> contract of ONE table, composed only from already-committed artifacts. Every
> entry below cites the committed source it came from. This document writes
> NOTHING back to any upstream artifact -- it is an OPTIONAL companion, never a
> readiness-stage gate. No score, no count: gaps are named `GAP:` markers only.

## (H) Header

- **Table:** `<table_id>`  *(the mapping-folder name / table identifier)*
- **Generated on:** "<YYYY-MM-DD>"  *(quoted; authoring time; ASCII)*
- **Sources read (every claim below traces to one of these):**
  - `<gold_source path>`  *(committed gold migration SQL, or "-- not found
    (see Document-Level Gaps)" if the table has not reached Gold Ready)*
  - `mappings/<table>/source-map.yaml`  *(committed column mapping rationale)*
  - `mappings/<table>/metrics/`  *(committed metric-contract folder)*

## (1) Gold Column Entries

One row per column actually declared in the committed gold migration SQL's
`CREATE TABLE` statement(s), in that file's own column definition order
(never reordered by relevance). A column marked `pii: true` and dropped in
`source-map.yaml`, or otherwise never materialized to gold, does NOT appear
here at all -- this section describes the DEPLOYED gold star only.

### `<gold_table_1>`

- **Column:** `<column_name>`
  - **Meaning:** <one of the two forms below -- choose per column>
    - **Cited:** "<the source-map `reason` text, quoted VERBATIM -- never
      paraphrased or simplified>" -- source: `mappings/<table>/source-map.yaml`
      (`columns[].source_name == "<matched source_name>"`)
    - **Gap:** `GAP: <column_name> -- no_source_map_entry` -- checked:
      `mappings/<table>/source-map.yaml` (no matching `source_name`/`gold_star`
      attribute entry found for this column)
  - **Drift note (only if present):** `<drift_note text, or omit this line
    entirely when there is no disagreement>` -- checked:
    `<gold_source path>`, `mappings/<table>/source-map.yaml`

- **Column:** `<column_name_2>`
  - **Meaning:** <cited or gap, as above>

<!-- repeat one "### <gold_table>" block per gold table/dim/fact the
     migration SQL declares; repeat one "- **Column:**" entry per column in
     that table's own CREATE TABLE definition order -->

## (2) Metric Entries

One row per metric contract file found under `mappings/<table>/metrics/`, in
the lexical (alphabetical) order of the folder's filenames. Every contract
found is listed -- approved and pending alike -- each clearly marked with its
own recorded status; a non-`pass` contract is never presented as approved.

- **Metric:** `<metric_name>`
  - **What it means:** "<the contract's `formula_intent` text, carried
    forward VERBATIM>"
  - **Status:** `<readiness.status value, verbatim>` -- <"approved" if
    `pass`, else "NOT YET APPROVED">
  - **Source:** `mappings/<table>/metrics/<metric_name>.yaml`

<!-- OR, when a referenced contract file is missing/unreadable: -->

- **Metric:** `<metric_name>`
  - **Meaning:** `GAP: <metric_name> -- contract_missing_or_unreadable` --
    checked: `mappings/<table>/metrics/<metric_name>.yaml`

<!-- repeat one "- **Metric:**" entry per file found under
     mappings/<table>/metrics/*.yaml, in lexical filename order -->

## (3) Document-Level Gaps

Table-wide gaps that are not specific to one column or metric. If none apply,
say so explicitly rather than leaving the section silently empty.

- `GAP: document -- no_gold_migration_found` -- checked:
  `warehouse/migrations/*_create_gold_<table>*.sql` *(only when the table has
  not yet reached Gold Ready; no column list is fabricated in this case)*
- `GAP: document -- source_disagreement` -- checked: `<gold_source path>`,
  `mappings/<table>/source-map.yaml` *(only when the two committed sources
  disagree at the table level; a per-column disagreement is recorded as that
  column's `drift_note` in section 1 instead)*
- <... or, if none: "No document-level gap recorded for this table.">

---

<!-- END OF DICTIONARY. No numeric confidence/health/maturity score anywhere;
     no completeness / "N of M" count (hard rule #9, FR-013). Every entry
     above cites a committed source path; a missing meaning is always a named
     `GAP:` marker, never invented or paraphrased prose (FR-005, FR-008,
     pending the OPEN FR-008/Q1 owner ruling -- see SKILL.md). The module
     wrote only this one file; it edited no upstream source artifact. -->
