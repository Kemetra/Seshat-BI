# Evidence Pack -- Index -- `<schema>.<table>`

> **GENERIC template -- copy this file to `mappings/<table>/evidence-pack-index.md`**,
> fill every `<placeholder>` and section row, commit it.
> **Roadmap feature: F028  On-disk spec: `specs/022-evidence-pack-generator/`**
> (dir 022 == F028; the roadmap F-number is authoritative when the two disagree).
> **Authority category: Product Module / `artifact-writing`** (F024 --
> `../docs/architecture/product-modules.md`).
>
> The ordered 10-section index for a table/report at the late readiness stages
> (Semantic Model Ready -> Dashboard Ready -> Publish Ready). It COMPOSES existing
> committed evidence -- every section points at an artifact that already exists from
> an earlier stage -- and invents nothing. It is the DERIVED output a Product Module
> writes; it owns no truth.
>
> **Composes, never invents.** Every present section resolves to an existing committed
> artifact path. A section whose source is missing / unfilled / a blank template is
> recorded `blocked` with a blocker naming the missing source -- never fabricated.
>
> **Surfaces, never asserts.** The publish-ready state lives in the summary
> (`evidence-pack-summary.md`); it is READ from `readiness-status.yaml`, never written
> here. This index records nothing back into any source artifact.
>
> **Consumes F013, never redefines it.** Section 08 references the table's FILLED
> `templates/handoff/bi-handoff-pack.md` instance and links to it; it never re-authors
> or edits that handoff. If the handoff is missing/incomplete, section 08 is a blocker.
>
> **No fake confidence, no count.** Each section's status is one of the four explicit
> statuses + `evidence[]` + `blocking_reasons[]`. NO numeric confidence/health number
> and NO "N of 10 sections present" tally anywhere (hard rule #9; Clarifications
> 2026-06-25).
>
> **Generic, not C086.** Placeholders only; the worked example is cited by reference,
> never inlined (Principle VII). ASCII only, UTF-8 no BOM; keep paths short (Windows
> MAX_PATH).

---

## Header

| Field | Value |
|-------|-------|
| Table / report | `<schema>.<table>` |
| Source family | `<source_family>` |
| Current stage | `<current_stage from readiness-status.yaml>` |
| Composed on | `<YYYY-MM-DD>` |
| Composed by | `<analyst / agent>` |
| In-progress? | `<yes -- composed before Publish Ready / no -- at Publish Ready>` |

When composed before Publish Ready, mark `In-progress? yes`: present sections render
and link; absent downstream sections are blockers; the summary states the CURRENT
stage and claims no stage the table has not reached.

## The 10-section index (fixed order; each row points at a committed source)

Status is one of `not_started` / `blocked` / `warning` / `pass`. The source column is
the repo-relative path the section summarizes; for a missing/unfilled source, record
`MISSING` and set status `blocked` with a blocking reason below. A `warning` carried
from upstream stays `warning` -- it does NOT auto-promote to `pass`.

| # | Section | Status | Source artifact (committed) | One-line summary or blocker |
|---|---------|--------|-----------------------------|------------------------------|
| 01 | source-profile | `<status>` | `mappings/<table>/source-profile.md` | `<summary / MISSING -> blocker>` |
| 02 | source-map-summary | `<status>` | `mappings/<table>/source-map.yaml` | `<summary / MISSING -> blocker>` |
| 03 | assumptions-and-decisions | `<status>` | `mappings/<table>/assumptions.md` + `unresolved-questions.md` (+ ADRs) | `<summary / MISSING -> blocker>` |
| 04 | metric-contracts | `<status>` | `mappings/<table>/metrics/` (filled F009/F010 contracts) | `<summary / MISSING -> blocker>` |
| 05 | validation-summary | `<status>` | recorded `retail check` + `retail validate` results + F012 roll-up | `<summary / MISSING -> blocker>` |
| 06 | semantic-model-summary | `<status>` | F010 / `retail semantic check` recorded output | `<summary / MISSING -> blocker>` |
| 07 | dashboard-summary | `<status>` | F011 dashboard design + F011A visual foundation | `<summary / MISSING -> blocker>` |
| 08 | handoff-pack | `<status>` | `mappings/<table>/handoff/bi-handoff-pack.md` (FILLED F013 instance -- EMBED) | `<summary / MISSING / incomplete -> blocker>` |
| 09 | known-limitations | `<status>` | `mappings/<table>/data-issues.md` + recorded caveats | `<summary / MISSING -> blocker>` |
| 10 | release-notes | `<status>` | F015 reconciliation ledger (+ F014 drift + `readiness-status.yaml` `approvals[]`) | `<summary / MISSING -> blocker>` |

Every present section MUST resolve to a real committed artifact path; every absent one
MUST resolve to a recorded blocker below. There is no section the pack originates from
nothing.

## Per-section evidence and blockers

For each section, record the committed evidence it cites and any blocking reason for a
gap. A blank-template source counts as MISSING (a blocker), never as evidence.

### 01 source-profile

- **evidence:** `<committed path(s) the summary cites>`
- **blocking_reasons:** `<empty / "source-profile.md missing or unfilled">`

### 02 source-map-summary

- **evidence:** `<committed path(s)>`
- **blocking_reasons:** `<empty / "source-map.yaml missing or unfilled">`

### 03 assumptions-and-decisions

- **evidence:** `<committed path(s)>`
- **blocking_reasons:** `<empty / naming the missing source>`

### 04 metric-contracts

- **evidence:** `<committed contract path(s) under mappings/<table>/metrics/>`
- **blocking_reasons:** `<empty / "no filled, approved metric contracts">`

### 05 validation-summary

- **evidence:** `<recorded retail check / retail validate result + F012 roll-up>`
- **blocking_reasons:** `<empty / naming the missing recorded result>`

### 06 semantic-model-summary

- **evidence:** `<recorded F010 / retail semantic check output>`
- **blocking_reasons:** `<empty / "semantic-model summary not yet produced">`

### 07 dashboard-summary

- **evidence:** `<committed F011 design + F011A foundation path(s)>`
- **blocking_reasons:** `<empty / "dashboard design not yet produced">`

### 08 handoff-pack (F013 -- consume, never redefine)

- **evidence:** `<link to the FILLED mappings/<table>/handoff/bi-handoff-pack.md>`
- **blocking_reasons:** `<empty / "F013 handoff missing or incomplete -- not synthesized">`
- **note:** this section REFERENCES the filled F013 instance; it never edits or
  re-authors it (scope delta: F028 consumes F013).

### 09 known-limitations

- **evidence:** `<committed data-issues.md + caveat path(s)>`
- **blocking_reasons:** `<empty / naming the missing source>`

### 10 release-notes

- **evidence:** `<F015 ledger (+ F014 drift + approvals[]) path(s)>`
- **blocking_reasons:** `<empty / naming the missing source>`

## Source disagreement (surface both, never reconcile silently)

If two upstream sources disagree (e.g. a contract count differs between the metric
store and the semantic-model summary), record BOTH with their source links here and
mark the affected section `warning` for human resolution (Principle V). Do NOT pick a
winner or reconcile silently.

- `<source A path + value> vs <source B path + value> -- recorded as a warning for <named human>`

## See also

- The one-page readiness summary (publish-ready state surfaced there):
  `evidence-pack-summary.md`.
- The skill that composes this: `../.claude/skills/evidence-pack-generator/SKILL.md`;
  the tool doc: `../docs/tools/evidence-pack-generator.md`.
- The F013 handoff embedded as section 08: `handoff/bi-handoff-pack.md` (in the filled
  per-table copy: `mappings/<table>/handoff/bi-handoff-pack.md`).
- The four-status / no-fake-confidence model: `../docs/readiness/readiness-model.md`.
- The authority contract: `../docs/architecture/product-modules.md`;
  `../templates/module-contract.md`. A filled worked example is cited as an
  instance under `../docs/worked-examples/`.
