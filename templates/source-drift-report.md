# Source Drift Report -- `<table-id>`

> **GENERIC template -- copy this file to `mappings/<table>/source-drift-report.md`**
> (co-located with the baseline it compares, per ADR 0003), fill every `<placeholder>`
> and measured cell, commit it.
> The blank a (future) drift run fills: it compares a BASELINE `source-profile.md` (the
> committed profile that earned Source Ready `pass`) against an OBSERVED re-profile of
> the same `<schema>.<table>` taken later, classifies each difference, and sets the
> resulting Source Ready status. See `docs/readiness/source-drift.md` (the taxonomy).
>
> **Cite numbers, not adjectives.** Every finding carries before/after MEASURED cells
> (counts, %, type strings) -- "missingness 3.1% -> 11.7%", never "missingness rose".
>
> **No fake confidence.** Per-class measured magnitudes are required; a rolled-up single
> drift "score" is FORBIDDEN (roadmap rule #9). Readiness is the four spine statuses.
>
> **Principle-V seams hard-stop.** grain/PK, returns-rule, PII-surface, and
> identity-bearing semantic-pair drift are `blocked` + raised to
> `unresolved-questions.md`; the report NEVER re-decides grain/returns/PII/identity.
>
> **DESIGN-ONLY today.** No drift runtime exists yet; absent a live re-profile, mark the
> findings `[PENDING LIVE RE-PROFILE]` and record `warning` -- never a fabricated diff.
>
> **Generic, not C086.** Placeholders only; C086 is a cited filled baseline. ASCII only,
> UTF-8 no BOM; secrets only in the git-ignored `.env`.

---

## Header

| Field | Value |
|-------|-------|
| Table | `<schema>.<table>` |
| Baseline profile | `mappings/<table>/source-profile.md` @ `<commit / date>` (the `pass` baseline) |
| Observed re-profile | `<YYYY-MM-DD>` by `<analyst / agent / runtime>` (read-only connection; secrets in `.env`) |
| Re-profile available? | `<yes / NO -> [PENDING LIVE RE-PROFILE], warning>` |

## Per-class findings (before -> after, measured)

One row per drift class observed. Severity is the class default (see the taxonomy),
escalated where noted. Leave a class out if it did not fire.

| Class | Column / field | Before (baseline) | After (observed) | Severity | Principle-V? |
|-------|----------------|-------------------|------------------|----------|--------------|
| `column added` | `<col>` | absent | present (`<type>`, `<cardinality>`) | `warning` | no -- "not yet mapped; review for adoption" |
| `column removed` | `<col>` | present | absent | `blocked` | no -- any mapping/silver reference is now broken |
| `column retyped` | `<col>` | `<TEXT>` | `<numeric>` | `warning` / `blocked` if key/measure | no |
| `missingness shift` | `<col>` | `<3.1%>` | `<11.7%>` | `warning` | no |
| `cardinality shift` | `<col>` | `<N distinct>` | `<M distinct>` | `warning` | no |
| `grain/PK drift` | `<pk cols>` | `is_unique=true` | `COUNT(*) != COUNT(DISTINCT pk)` | `blocked` | **YES** -> raise grain question |
| `returns-rule drift` | `<returns col>` | `<pop / meaning>` | `<changed / absent>` | `blocked` | **YES** -> raise returns question |
| `semantic-pair drift` | `<code -> label>` | 1:1 | `<not 1:1: N labels for 1 code>` | `warning` / `blocked` if identity | maybe -> identity is a seam |
| `PII surface drift` | `<col>` | dropped (RC4) / absent | reappeared / new PII-looking | `blocked` | **YES** -> raise PII question (default stays drop) |

## Resulting Source Ready status

- Status: `<pass | warning | blocked>` (no material drift -> `pass`; only non-fatal
  classes -> `warning`; any fatal class -> `blocked`). NO drift score.
- `blocking_reasons[]`: `<enumerate each fatal class with the column + measured fact>`.
- `evidence[]`: this report + the baseline profile + the observed re-profile.
- Downstream-suspect note: `<which downstream pass stages (Mapping/Silver/Gold/...) are
  now SUSPECT and must be re-confirmed against the new shape -- flagged, never auto-demoted>`.

## Principle-V handoff (open questions for a human)

One row per HARD-STOP class. The report raises; the named owner decides -- never
auto-resolved here.

| Open question | Class | Measured fact | Owner |
|---------------|-------|---------------|-------|
| `<e.g. is the new grain acceptable, or is dedup a defect?>` | grain/PK drift | `<dup count>` | analyst |
| `<e.g. which column is now authoritative for returns?>` | returns-rule drift | `<pop change>` | analyst |
| `<e.g. is the reappeared column publish-safe?>` | PII surface drift | `<col name>` | governance |

## Edge-case notes

- **No baseline** -> the detector does not run; the table is `not_started` (stage 1), not
  "drifted".
- **Tolerances not set on the baseline** -> any movement is recorded as an observation at
  `warning`; raise a follow-up to record tolerances (never silently treated as zero-drift).
- **Cosmetic-only diff** (provable rename, same semantics + measures) -> recorded as an
  observation, flagged for mapping review; the detector does NOT auto-equate two names.
- **Profile schema-version skew** -> compare only the fields both profiles carry; record
  which fields were uncomparable rather than reporting false drift.

## See also

- The taxonomy + status mapping: `../docs/readiness/source-drift.md`.
- The baseline it compares: `source-profile.md`; the Principle-V handoff:
  `unresolved-questions.md`; the spine: `../docs/readiness/readiness-model.md`.
- A cited filled baseline is not the schema: see a filled worked example under `../docs/worked-examples/`.
