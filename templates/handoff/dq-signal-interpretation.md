# DQ-Signal Interpretation Note

> **Generic template -- clone this per table.** Fill one note per table that has a recorded
> data-quality signal worth interpreting for a business reader. This template carries NO
> table specifics; a concrete filled instance lives only in the worked example
> (`../../docs/worked-examples/c086-pharmacy.md`, `../../docs/c086-adr0002-compliance.md`),
> never inlined here.
>
> **Composes, never invents.** Every count is **sourced by reference from
> `../data-issues.md`** (the single source of truth for the number). This note interprets a
> recorded signal; it computes and invents no number.
>
> **No fake confidence.** ASCII / UTF-8 without BOM (`--` and `->`, no glyphs). This note
> emits **no numeric confidence / health / readiness score** -- only a plain-language caveat
> plus explicit owner-gated cells (hard rule #9).

**Table**: `<schema>.<table>`  **Assembled on**: `<YYYY-MM-DD>`  **by**: `<analyst>`
**Stage of record**: Stage 7 (Publish Ready) -- the caveat/stakeholder surface that CONSUMES
the signal. The `-1` count is NOT produced by the Stage-4 `retail validate` run -- that run
only flags HARD orphan FKs (a FK with no matching dim row); rows coalesced to the `-1`
unknown member DO have a matching dim row and pass validate silently. The count comes from a
separate analyst query and is recorded in `../data-issues.md`. This note is authored
generically now, filled once that count is recorded, and read as a Stage-7 caveat.

## Per-signal interpretation

One row per recorded `-1` unknown-member signal (from `../data-issues.md`). Every judgment
cell is an unfilled `<placeholder>` the named analyst fills; the template pre-decides nothing.

| Signal (dim) | Count (by reference) | Affected KPI (analyst fill) | Direction (understate \| overstate \| none) | Plain-language caveat | Owner (named) | PII review |
|--------------|----------------------|-----------------------------|----------------------------------------------|-----------------------|---------------|------------|
| `<N rows on the -1 unknown member of dim_<x>>` | see `../data-issues.md` (do not re-type the number) | `<KPI, analyst fill>` | `<understate \| overstate \| none, analyst fill>` | `<plain-language caveat, analyst fill>` | `<named owner>` | `<governance sign-off if a person/customer dim -- else n/a>` |

## Direction-of-distortion semantics (FR-011 -- the analyst states this precisely)

The `-1` unknown member has a known, categorical effect that the caveat must state precisely
(no magnitude, no forecast):

- **Measure TOTALS are preserved.** The row is absorbed into the `-1` bucket, so a grand
  total (e.g. total sales) still reconciles -- the value is not lost, only its dimension key
  is unknown.
- **Any view SLICED / grouped by the affected dimension is distorted.** The `-1` bucket
  steals share from the real members: real members are understated and an "unknown" bucket
  is overstated.

Which specific business KPI a given signal distorts, and in which direction for that KPI, is
an analyst business-meaning ruling (Principle V) -- the analyst fills the row; the template
asserts only the total-vs-sliced claim above. See spec **FR-011** (the recorded human ruling).

## When there is no recorded signal

If `../data-issues.md` records **no** `-1` unknown-member signal for this table, write exactly:

> **No recorded `-1` signal for this table -- nothing to interpret; zero caveats.**

An empty note is the honest state. Never fabricate a caveat for a table with no recorded
signal (and none until the analyst has recorded a `-1` count in `../data-issues.md` -- a
clean `retail validate` run does NOT record it, since `-1` rows pass validate silently).

## Feeds the handoff pack -- does not duplicate it

A confirmed caveat is carried **verbatim** into the Stage-7 handoff pack "Known data issues /
caveats" section (`bi-handoff-pack.md`, the Known-gaps rows). This note is the interpretive
*source*; it does not restate the pack. **`../data-issues.md` remains the single source of
truth for the number** -- if this note and `data-issues.md` ever disagree, reconcile to
`data-issues.md`; this note never overrides it.

## The `-1` member is a ratified default, not a defect

The `-1` unknown member + `COALESCE(<fk>, -1)` is a **ratified default** (Constitution
Principle VI; ADR-0002 RC14). This note **interprets the consequence** of that accepted
default for a business reader; it does not re-litigate the default and invents no number.

## PII publish-safety gate

If the affected dimension is a **person / customer** dimension, a governance publish-safety
sign-off is required before the caveat is published. Default: **defer to governance**
(Principle V) -- the analyst does not self-clear a PII-adjacent gap.

## See also

- The count's single source of truth: `../data-issues.md`
- Stage-7 consumer (Known-gaps section): `bi-handoff-pack.md`
- Stage-7 stage doc: `../../docs/readiness/publish-ready.md`
- Where the count is recorded (an analyst query, NOT the validate run): `../data-issues.md`; Stage-4 gate context: `../../docs/readiness/gold-ready.md`
- The ratified `-1` default: `../../.specify/memory/constitution.md` (Principle V, Principle VI / RC14)
- Filled concrete instance (worked example): `../../docs/worked-examples/c086-pharmacy.md`, `../../docs/c086-adr0002-compliance.md`
