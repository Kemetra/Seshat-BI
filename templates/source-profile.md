# Source Profile -- `<table-id>`

> **Template -- copy this file to `mappings/<table>/source-profile.md`** (per
> [ADR 0003](../docs/decisions/0003-mapping-artifact-location.md)), fill every
> `<placeholder>` and blank cell, commit it.
> This is the **first artifact of the source-mapping gate** (see
> `docs/architecture/tower-bi-agent-kit.md` Sec 5). It formalizes **Phase 1
> (Connect & profile)** of `docs/medallion-playbook.md` into a committed, reviewable
> record. Fill it from a read-only profiling pass over the *landed* source -- before
> any cleaning decision and before any `silver.*` SQL exists.
>
> **The rule the gate enforces:** you do not write silver until this profile is filled,
> the source is mapped (`source-map.yaml`), and the mapping is reviewed.
>
> **ASCII only.** Use `->` for arrows, `<->` for pairs, `>=`/`<=` for inequalities,
> `[OK]`/`[x]` for status. No unicode.
>
> **Cite numbers, not adjectives.** Every claim below must carry a measured count.
> "Mostly populated" is not a profile; "`8,431 / 249,106` missing" is.

---

## Header

| Field | Value |
|-------|-------|
| Table id | `<table-id>` (e.g. `C091`) |
| Source kind | `<db-table / csv / excel>` (a DB `<schema>.<table>`, or a standalone file -- fill the File-source addendum below when csv/excel) |
| Source system | `<source-system>` (e.g. ERP / POS export / SAP extract; for a file: the system that produced the export) |
| Landed location | `<bronze.schema.table>` (faithful all-TEXT landing) |
| Connection | read-only; credentials from the gitignored `.env` at runtime -- **never inline a connection string or secret here**. For a file source: the read-only path/glob the file was profiled from -- **never inline a share credential or absolute user path** |
| Profiled on | `<YYYY-MM-DD>` |
| Profiled by | `<analyst / agent>` |
| Source files folded in | `<N>` files / `<single export>` (relevant to the cross-file drift check below) |

---

## Shape

| Metric | Value |
|--------|-------|
| Row count (landed) | `<N>` |
| Column count (landed) | `<N>` |
| Schema(s) present | `<schema names>` |

> Record the **landed (bronze, raw) row count** here -- the source as it arrived, before
> any filter. The post-clean silver count is recorded later in `reconciliation-report.md`,
> not in this file.

---

## File-source addendum (csv / excel only)

Fill this section **only when `Source kind` is `csv` or `excel`**; delete it for a
`db-table` source. A standalone file has structural facts a DB table does not -- how it
was decoded, where the header row is, which sheets exist -- and getting them wrong
silently misreads every column below. **These are the file equivalent of "the connection";
record them from the read-only open, do not assume from the file name or extension.**

> **PROPOSED, not asserted.** Encoding, delimiter, and header-row detection are
> *inferences* unless a data owner has confirmed them. Record the detected value AND mark
> it `[PROPOSED]` until confirmed -- exactly as the semantic rows below are proposed, never
> invented (Principle V / RC-semantics). A guessed encoding stated as fact is the file
> analogue of inventing a business rollup.

| Field | Value |
|-------|-------|
| Format | `<csv / tsv / xlsx / xlsm>` (the profiler reads OOXML Excel via openpyxl; legacy `.xls` (BIFF) is NOT supported -- convert to `.xlsx` first, or mark it unsupported/deferred) |
| Encoding | `<utf-8 / utf-8-sig / cp1256 / latin-1>` `[PROPOSED]` -- how bytes decode to text; a wrong guess mojibakes Arabic/accented labels (see Encoding corruption in Semantics) |
| Byte-order mark (BOM) | `<present / absent>` -- a UTF-8 BOM leaks into the first header name if not stripped |
| Delimiter | `<, / ; / tab / pipe>` `[PROPOSED]` (csv/tsv only) -- `;` is common in cp1256 locales; a wrong delimiter reads the whole row as one column |
| Quote / escape char | `<" / ' / none>` (csv/tsv only) -- embedded delimiters inside quoted fields |
| Header row | `<row index, 0-based / none>` `[PROPOSED]` -- the row carrying column names; a report title or blank line above it shifts every column if misread |
| Skipped pre-header rows | `<N>` -- banner/title/blank rows above the header (Excel exports often carry these) |
| Line terminator | `<LF / CRLF>` (csv/tsv only) |

**Excel workbooks -- one row per sheet that is in scope.** Enumerate sheets; do NOT assume
the first sheet is the data. State which sheet(s) this profile covers and why the others are
out of scope (empty, a pivot, a legend).

| Sheet name | In scope? | Row count | Col count | Header row | Notes |
|------------|-----------|-----------|-----------|------------|-------|
| `<sheet>` | `<yes / no>` | `<N>` | `<N>` | `<row index>` | `<why in/out of scope; merged cells; multi-row header>` |
| `<sheet>` | | | | | |

**File-source traps (each silently corrupts the per-column profile below):**
- **Merged / multi-row headers** (Excel) -- a two-row header reads as a phantom first data
  row and NULLs a real column name. Report merged-header rows: `<N>`.
- **Type inference is a guess, not the type.** A reader that auto-infers dtypes may read a
  leading-zero product code as an integer (dropping the zeros, RC7) or a mixed column as
  `object`. Treat every inferred type as *landed-as-TEXT* for this profile; the target type
  is a `source-map.yaml` decision, exactly as for a DB source.
- **Cross-file / cross-sheet drift** -- if `>1` file or sheet is folded into one header, a
  column-order or header-rename change in one silently misaligns values. This is the file
  form of the Cross-file schema drift check in Semantics below -- profile categoricals
  grouped by source file/sheet.

---

## Per-column profile

Fill one row per landed column. Leave the value cells blank in the template; fill them
from the profiling pass.

> **Missingness trap (load-bearing -- read before filling the column below).**
> Measure missingness as **`trim(col) = '' OR col IS NULL`**, *never* `IS NULL` alone.
> A faithful landing loader that writes `'' if value is None` makes
> `COUNT(*) WHERE col IS NULL` return `0` for every column -- a false "no missing data."
> The `Missingness` cell must report the `'' OR NULL` count (and `%`). This is ADR 0002
> **RC5** and playbook Appendix A trap #1.

| Column | Type as landed | Missingness (`'' OR NULL`, count / %) | Distinct cardinality | Candidate key? | Notes |
|--------|----------------|----------------------------------------|----------------------|----------------|-------|
| `<column>` | `<TEXT / as-landed>` | `<N>` / `<%>` | `<N>` | `<yes / no / part-of-composite>` | `<redundancy, derivability, leading-zeros, parse issues>` |
| `<column>` | | | | | |
| `<column>` | | | | | |

**Column-table legend**
- *Type as landed* -- the type the source actually arrived as (a faithful bronze landing
  is typically all-`TEXT`). The *target* type is a Phase 2.5 decision recorded in
  `source-map.yaml`, not here.
- *Missingness* -- always the `'' OR NULL` measure (see trap above), with both count and `%`.
- *Distinct cardinality* -- `COUNT(DISTINCT trim(col))`; flags single-value columns
  (drop candidates, ADR 0002 **RC3**) and code/label fan-out.
- *Candidate key?* -- whether this column (alone or in a composite) is a candidate for the
  grain PK; the verification numbers go in the **Candidate grain & PK** section below.
- *Notes* -- redundancy / derivability vs another column, leading zeros (forces `TEXT`,
  **RC7**), parse failures, anything a keep/drop/rename/type decision will hinge on.

---

## Semantics

Profiling pass B -- derive these **from the data, not from field names**. Two columns
whose source names look related can still disagree on thousands of rows; compute the
row-level rate, do not assume.

- **Code <-> label pairs.** `<column-code>` <-> `<column-label>`: is it 1:1 on the data?
  Measured rate: `<N>` / `<N>` rows consistent (`<%>`). *(If 1:1, the code half is a drop
  candidate per RC3 unless it is a stable join key.)*
- **Dimension fan-out (`id -> name` 1:1?).** `<id-column>` -> `<name-column>`: one name
  per id? Violations: `<N>` ids map to `>1` name. *(A fan-out > 1:1 changes how the
  dimension is built.)*
- **Hierarchy nesting.** `<parent>` / `<child>` levels: clean tree, or does a child
  appear under multiple parents? Multi-parent rows measured: `<N>`. *(Not a clean tree
  -> flat denormalized levels later, ADR 0002 RC12 -- a Phase 2.8 decision, recorded in
  `source-map.yaml`.)*
- **Returns population & how it is identified.** Identified from the **authoritative
  column** `<column>` (a billing / transaction-type code), **not** the sign of a measure.
  Returns rows: `<N>` / `<N>` (`<%>`). *(Playbook 2.6 / ADR 0002 RC8: the measure sign
  alone misses zero-value and edge-case returns.)*
- **Encoding corruption.** Display columns with garbage / mixed-encoding characters:
  `<column(s)>`, affected rows `<N>`. *(Driver for the encoding-fix step in the silver
  build order.)*
- **Outliers.** `<measure-column>`: range `<min>` .. `<max>`; suspicious extremes `<N>`.
  Report violation **counts**, not averages -- two columns can share a mean yet disagree
  on thousands of rows.
- **Cross-file schema drift.** If the landing folded `>1` source file into one header, a
  column-order change in one file silently misaligns values. Profiled low-cardinality
  categoricals **grouped by source file**: drift found `<yes / no>`, evidence `<...>`.
  *(Playbook Phase 1 trap; Appendix A trap #4.)*
- **Money-relationship checks (derive, never assume).** If the source carries multiple
  money columns (e.g. a gross / net / tax / discount set), compute the row-level identity
  rate rather than trusting the names. `<column> == <column> + <column>` holds on `<N>` /
  `<N>` rows (`<%>`). *(Keep independent measures per ADR 0002 RC9; do not collapse them on
  a name-based assumption.)*

---

## Candidate grain & candidate PK

State the grain **first** (playbook Phase 2.0 / ADR 0002 **RC1**: model at the lowest grain
the source provides -- you can roll up later, never down) and verify the candidate PK is
unique **on the data**.

- **Candidate grain:** one row = `<one ... >` (e.g. one invoice line item).
- **Grain ratio:** `<N>` rows vs `<N>` of the candidate business entity = `<ratio>`
  (e.g. `2.42` lines per invoice).
- **Candidate PK:** `( <key-col-a>, <key-col-b> )`.
- **Uniqueness proof (on the landed data):**
  - `COUNT(*)            = <N>`
  - `COUNT(DISTINCT pk)  = <N>`   *(must equal `COUNT(*)` for the PK to hold)*
  - `NULLs in PK columns = <N>`   *(must be `0`)*

> **Forward seam to the silver build (ADR 0002 RC2).** What is recorded here is the
> candidate PK on the **landed** data. RC2 requires the PK to be **re-verified on the
> TRANSFORMED output** during the silver build (Phase 5) -- `TRIM`/cast can collapse two
> raw-distinct keys or null a key. This profile establishes the candidate; the silver
> migration must re-prove it. Do not treat landed uniqueness as final.

---

## Top data-quality issues

Rank the issues this profile surfaced that a downstream decision must address (each with
its number). These feed `assumptions.md` (defaults vs deviations) and
`unresolved-questions.md` (the open decisions that block the build).

1. `<issue + count>`
2. `<issue + count>`
3. `<issue + count>`

---

## Exit gate

This profile is complete when **you can state -- with numbers -- the grain, the candidate
keys, the returns rule, and the top data-quality issues.** Until then, the source-mapping
gate stays shut and no `silver.*` SQL may be written.

- [ ] Grain stated, with the row-vs-entity ratio.
- [ ] Candidate PK stated and proven unique on the landed data (`COUNT(*)` =
      `COUNT(DISTINCT pk)`, `0` NULL PK).
- [ ] Returns rule stated, from the authoritative column (not a measure sign).
- [ ] Top data-quality issues listed, each with a measured count.
- [ ] Missingness measured as `'' OR NULL` for every column (not `IS NULL` alone).
- [ ] **File source (`Source kind` csv/excel) only:** the File-source addendum is filled
      -- format, encoding (`[PROPOSED]`), delimiter/quote (csv), header row, and the
      enumerated in-scope sheet list (Excel). A file profile is NOT complete without it:
      the mechanical numbers above are unreadable-to-trust until the encoding/delimiter/
      header that produced them is recorded (and the encoding is owner-confirmed at the
      Source Ready gate). Do not proceed to `source-map.yaml` on a misread file.

---

## Next artifact

Once this exit gate passes, proceed to **`source-map.yaml`** -- the machine-readable
spine that records the per-column keep / drop / rename / type decisions, the grain + PK
decided first, the target silver column, and the gold star placement (fact measure / dim
attribute / degenerate dim). This profile is its evidence base.

## See also

- **Method:** `docs/medallion-playbook.md` -- Phase 1 (Connect & profile) and Appendix A
  (the reusable trap-checklist: missingness `'' OR NULL`, derive from data not names,
  candidate keys verified on data, cross-file drift, returns from the authoritative column).
- **Defaults:** `docs/decisions/0002-retail-cleaning-defaults.md` -- **RC1** (lowest grain),
  **RC2** (verify PK on transformed data), **RC5** (`'' -> NULL`; missingness as `'' OR NULL`).
  *(Namespace note: these are ADR 0002 cleaning defaults `RC*`; distinct from the
  governance checker's own `D1-D8` TMDL/DAX rules. Distinct prefixes, no collision --
  disambiguated in feature 002.)*
- **Architecture:** `docs/architecture/tower-bi-agent-kit.md` Sec 5 -- the source-mapping
  gate and how the five templates map to playbook phases.
- **Worked example (a filled instance):** a filled worked example under
  `docs/worked-examples/` shows a table profiled through this gate. A worked
  example is an example, never the universal schema; its source-specific columns
  and codes belong to its own artifacts, not to this template.
