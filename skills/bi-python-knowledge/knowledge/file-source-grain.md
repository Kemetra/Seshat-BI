# File-Source Grain (CSV / Excel)

Reading a standalone file -- CSV or Excel -- as a raw source, without misreading its
grain, its types, or its text. A file is not a table: it has no declared schema, no
enforced types, and no single-connection contract. Every one of those absences is a way
to silently corrupt the profile before a single cleaning decision is made. This file owns
the file-specific reasoning; once the file has landed as a bronze frame, the normal
profiling / cleaning / grain routes take over.

Schema: `references/retail-dataframe-schema.md`. Meaning of a KPI lives upstream in
`skills/retail-kpi-knowledge/` -- do not infer meaning from a file's column names.

> **Boundary -- reason, do not ingest.** This layer *reasons about* how a file must be
> read and what to record; it is single-node source-prep knowledge, not an ingestion
> runner. The governed core never opens a file at import time (never-execute). A file's
> mechanical numbers are recorded through a read-only profiling pass, exactly as a DB
> source's numbers come from `profile.py` -- the file profiler is `file_profile.py`
> (`make_csv_reader` on the stdlib; `make_excel_reader` via the optional `files` extra).
> A CSV/Excel source reaches `source_ready: pass` after profiling PLUS an owner
> encoding-confirmation (RS1 enforces it -- see `docs/readiness/source-ready.md`). Only
> when no reader is available (Excel without the `files` extra) does the deferred-boundary
> fallback (`[PENDING LIVE PROFILE]`, `source_ready: warning`) apply.

---

## PY-CN-081 -- A file has no declared type; every dtype is inferred

A DB column arrives with a type the source enforced. A file column arrives as text that a
reader *guesses* a type for. That guess is not the truth. `read_csv`/`read_excel` will
read a leading-zero product code (`"007412"`) as the integer `7412` -- dropping the zeros
that make it a valid key (RC7) -- and read a mixed column as `object`. Treat every inferred
type as **landed-as-TEXT** for the profile; the target type is a `source-map.yaml` decision,
identical to a DB source. Read with all columns as string first, profile, THEN decide types.

**Retail illustration:** a `material` code column of leading-zero SKUs read with default
inference becomes an int column; `000` prefixes vanish and two distinct SKUs (`00412`,
`0412`) collapse to one. Read as string -> the distinct count is correct -> the collapse is
caught as a finding, not shipped as clean.

## PY-CN-082 -- Encoding is a decoding decision, not a fact

Bytes are not text until an encoding decodes them. A file gives you bytes; the encoding is
an *inference* until confirmed. A wrong guess mojibakes non-ASCII labels: Arabic or
accented category names read as garbage, and the corruption is invisible in a numeric
summary. Detect and record the encoding (`utf-8`, `utf-8-sig`, `cp1256`, `latin-1`); mark
it `[PROPOSED]` in the profile until a data owner confirms. A UTF-8 **BOM** is a common
trap: undetected, it prepends a zero-width `U+FEFF` byte to the first header name, so
`id` reads as `<BOM>id` -- a name that looks identical but is not, and every keyed lookup
on that column silently misses. Read with `utf-8-sig` (or strip the BOM) to remove it.

**Retail illustration:** a POS export in `cp1256` (Windows Arabic) read as `utf-8` turns
`billing_type` Arabic labels into replacement characters; the distinct-label count looks
plausible but no label matches the mapping table -- a decode finding, not a mapping gap.

## PY-CN-083 -- The delimiter and quoting decide the column boundaries

For CSV/TSV, the delimiter is what splits a row into columns. `;` is common in
comma-decimal locales; a file assumed comma-delimited but actually `;`-delimited reads the
entire row as one column, and the profile reports column count `1`. The quote/escape char
decides whether an embedded delimiter inside a quoted field (`"Cairo, EG"`) splits or
stays. Record both, from the read, not the extension -- a `.csv` may be tab- or
semicolon-delimited.

## PY-CN-084 -- The header row is a decision; exports lie above it

A file's header is wherever the column names are -- not necessarily row 0. Exports from BI
tools and ERPs routinely carry banner/title/blank rows above the header. Read the wrong row
as the header and every column name is wrong and one real data row is lost. Record the
0-based header-row index and the count of skipped pre-header rows. A header that is a report
title (`"Sales Report Q2"`) rather than field names is a definite finding, not a rename.

## PY-CN-085 -- Excel is a workbook, not a table; enumerate sheets

An Excel file holds many sheets; the first is not necessarily the data. Enumerate every
sheet, state which one(s) this profile covers, and say why the rest are out of scope (empty,
a pivot cache, a legend, a parameters tab). Never assume `sheet 0`. Two further Excel-only
traps:
- **Merged cells / multi-row headers.** A visually merged two-row header reads as a phantom
  first data row and NULLs a real column name. Count merged-header rows; flatten to a single
  header before profiling.
- **Per-sheet grain differs.** Two sheets in one workbook can be at different grains (a
  detail sheet and a summary sheet). Do not union them without proving the grain matches --
  that is the file form of a fan-out (PY-PB, grain).

## PY-BP-007 -- Read as text, enumerate, then profile -- in that order

The safe default for any file source, before a single cleaning or type decision:

1. Enumerate structure -- for Excel, list sheets and pick the in-scope one(s); for CSV,
   detect delimiter, quote char, encoding, and the header-row index.
2. Read every column as **string** (no type inference) using the detected structure.
3. Profile the string frame with the normal routes (missingness as `'' OR NULL`, distinct
   cardinality, candidate PK) -- now the numbers are trustworthy.
4. Record the File-source addendum in `mappings/<table>/source-profile.md` with the
   detected encoding/delimiter/header marked `[PROPOSED]`.
5. Only then propose target types and cleaning -- as `source-map.yaml` decisions.

Skipping step 1 or 2 means every later number is measured on a misread frame.

## PY-PB-011 -- Playbook: a file column looks wrong / count is off

| Symptom | Likely cause | Check |
|---------|--------------|-------|
| Whole row in one column; column count is `1` | wrong delimiter (PY-CN-083) | re-detect the delimiter; a `.csv` may be `;`/tab |
| Non-ASCII labels are garbage; no label matches the domain | wrong encoding (PY-CN-082) | try the locale encoding (`cp1256`, `latin-1`); confirm with the owner |
| First column name has a stray leading character | UTF-8 BOM (PY-CN-082) | read with `utf-8-sig` / strip the BOM |
| Leading-zero codes lost; two keys collapsed to one | type inference (PY-CN-081) | re-read as string; re-check distinct count |
| Column names look like a title / are `Unnamed: N` | header row misread (PY-CN-084) | find the real header row; count skipped rows |
| Excel row count includes a phantom blank/summary row | merged/multi-row header or wrong sheet (PY-CN-085) | enumerate sheets; flatten the header |

Each row is a **finding to record**, not a silent auto-fix -- the same discipline as the
cleaning routes: profile -> flag -> decide with the owner -> re-profile.

---

## Stop rule

This file ends when the file's structure is recorded (format, encoding, delimiter/quote,
header row, in-scope sheets) and every column is read as string for profiling. It does NOT
decide target types, business meaning, or grain rollups -- those are `source-map.yaml`
decisions and (for meaning) `skills/retail-kpi-knowledge/`. It never opens a file inside the
governed core.

## See also

- `docs/readiness/source-ready.md` -- Stage 1; where a file source is profiled (via
  `file_profile.py`) and reaches pass after owner encoding-confirmation.
- `src/retail/file_profile.py` -- the read-only file profiler (CSV on the stdlib; Excel
  via the `files` extra) that produces the mechanical numbers this reasoning guides.
- `templates/source-profile.md` -- the File-source addendum this reasoning fills.
- `knowledge/cleaning-and-standardization.md` -- what to do once the file has landed as a
  frame (PY-CN-031..036).
- `skills/bi-sql-knowledge/INDEX.md` -- Future extension: file sources are explicitly routed
  here, not to the SQL layer.
- A DB-landed worked example is not a file source -- a filled instance, never the universal
  schema: see a filled worked example under `docs/worked-examples/`.
