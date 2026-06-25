# Implementation Plan: Adapter Compatibility Matrix

**Branch**: `026-adapter-compatibility-matrix` | **Roadmap feature**: F032 | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

> Numbering note: roadmap F-number (F032) is authoritative; on-disk spec-dir is 026.
> When they disagree, the roadmap F-number wins.

**Input**: Feature specification from `specs/026-adapter-compatibility-matrix/spec.md`

## Summary

Plan the **adapter compatibility matrix** (Roadmap F032, Maintenance Automation
category per F024): the committed, reviewable RECORD of which version of each adapter/
dependency the kit pins is verified-compatible, the smoke test that proves it, the
last-verified date, and the attesting owner. The planned shape is **one operations doc
(`docs/operations/adapter-compatibility-matrix.md`) + one generic record template
(`templates/adapter-version-record.md`)**, with the agent as the runtime that fills the
matrix from attested evidence. This is the RECORD half of the record/policy pair: F032
stores the version-truth; F031 (Adapter Maintenance Policy) enforces against it. An
untested version is recorded `unknown`, NEVER assumed compatible (hard rule #9 /
Principle IX). Readiness stage affected: none directly.

**This slice is planning-only.** It writes the five Spec-Kit files and nothing else.
The matrix doc and the record template are FUTURE deliverables ENUMERATED here, not
created now. No runtime code, no CI, no dbt/Dagster/Power BI artifact.

## Technical Context

**Language/Version**: None -- docs/planning this slice. The planned deliverables are a
Markdown doc + a Markdown record template (text artifacts); no programming language is
introduced.

**Primary Dependencies**: None at runtime. Authoring style for the future template
borrows from the existing readiness/issue templates (header + namespace/placeholder
convention) and the four-status + no-fake-confidence vocabulary from
`docs/readiness/readiness-model.md`. The matrix's adapter list references the version
surfaces named by F029 (dbt-core, dbt-postgres), F030 (Dagster, dagster-dbt), and F016
(Power BI PBIP/TMDL assumptions, Power BI MCP status), plus the kit/Python/Postgres
baselines.

**Storage**: Committed text. Future deliverables:
`docs/operations/adapter-compatibility-matrix.md` (the matrix) and
`templates/adapter-version-record.md` (the per-adapter record template). This slice
creates only the five `specs/026-adapter-compatibility-matrix/` planning files.

**Testing**: No code, so no unit tests. Verification for the future authoring slice is:
(1) the matrix lists all nine named adapters/dependencies as rows; (2) every row carries
a version range + a named smoke test + a status + a last-verified date + an owner;
(3) every untested cell is `unknown`, never supported; (4) no numeric score appears;
(5) ASCII + UTF-8 no-BOM on every file. For THIS slice, verification is that the five
planning files exist, are ASCII/no-BOM, and enumerate both future deliverables as
planned-not-created.

**Target Platform**: Repo text artifacts consumed by an agent + reviewed by a human;
the F031 maintenance policy reads the matrix.

**Project Type**: Documentation/planning feature (no source tree change).

**Performance Goals**: N/A (static text).

**Constraints**: ASCII + UTF-8 no BOM; generic (no C086 / retail_store_sales specifics);
no secrets/DSNs/tokens/local paths; Windows path budget (keep names short); no numeric
compatibility score; no enforcement logic (PR gate / CI fail) -- that is F031; no adapter
code -- F032 tracks versions, it does not build; planning-only this slice.

**Scale/Scope**: This slice = 5 planning files. The planned record = one matrix doc
(nine adapter rows) + one record template (one-adapter shape). One generic example
adapter row demonstrates the shape; no C086 values.

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | Adds no gate and no agent authority over a row's status. The matrix is something the agent FILLS from attested evidence; promoting a row to supported requires a named owner attesting a passed smoke test. `retail check` stays the gate; this feature does not touch it. |
| II. Depend, Never Fork | No engine fork, no `pbi-cli` reliance (the official Power BI MCP / connection is the preferred future adapter; F032 only records its STATUS). Pure local opinion in a doc + template. |
| III. Medallion, Gold-Only | Not triggered -- the matrix records tool versions, not data flow. No silver/gold/Power BI data path is defined or altered. |
| IV. Source Mapping Before Silver | Not triggered (no silver SQL, no mapping). The matrix is orthogonal to the data pipeline. |
| V. Agent Stops at Judgment Calls | The judgment call here is "is this version supported?" -- the agent records `unknown` and stops when untested; a named owner attests a passed smoke test to promote a row. The agent never self-attests or self-promotes. Classic data judgment calls (grain/PII/rollup) are N/A and stated so explicitly, not fake-fitted. |
| VI. Defaults Then Deviations | The record/policy split (F032 record, F031 policy) is the recommended default, recorded in both specs; a deviation (merging them) would be recorded, not silent. |
| VII. C086 Is An Example | FR-013/SC-007: all artifacts generic; C086 / retail_store_sales cited as an example, never inlined. Concrete version strings in a future filled matrix are environment facts, not pharmacy specifics; this slice carries placeholders only. |
| VIII. Static-First, Live Deferred | FR-015/SC-008: NO runtime code, NO CLI, NO `retail check` rule, NO CI job, NO adapter artifact this slice; the planned first form is a human-readable doc + template (rule #8 -- automate enforcement later, if ever; that is F031's call). `retail check` exit 0 + no new rule added. |
| IX. Secrets & Reproducibility | No secrets, DSNs, tokens, or local paths. ASCII + UTF-8 no BOM; short paths. The no-fake-confidence rule is instantiated as "UNKNOWN is never compatible" (FR-007/FR-008); no numeric score. |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Boundary gates (feature-specific, load-bearing)

The two biggest design risks are scope-bleed from the RECORD into the POLICY, and from
the RECORD into the ADAPTERS. The plan holds both boundaries explicitly:

- **Record vs policy (F032 vs F031).** F032 stores supported ranges + smoke-test status
  + last-verified dates + owners. It adds NO PR gate, NO CI fail condition, NO merge
  block, NO enforcement logic. What a dependency-update PR must DO about a violation is
  F031. The planned matrix doc states this boundary at the top.
- **Record vs build (F032 vs F029/F030/F016).** F032 records the supported versions of
  those adapters; it MUST NOT author, modify, or execute any adapter's runtime code,
  connection logic, or transformations. It names them and pins their boundaries only.
- **Record vs smoke-test authoring/running.** F032 NAMES each required smoke test and
  records its last result + date; it does NOT author or run the smoke test, nor wire it
  into CI.

## Project Structure

### Documentation (this feature)

```text
specs/026-adapter-compatibility-matrix/
|-- spec.md              # /speckit-specify output (this slice)
|-- plan.md              # This file (/speckit-plan output)
|-- tasks.md             # /speckit-tasks output
`-- checklists/
    |-- acceptance.md    # spec quality checklist (this slice)
    `-- governance.md    # Core-vs-Module authority + no-self-approval gate (this slice)
```

No `research.md` / `data-model.md` / `contracts/` directory is generated: there is no
code to research, no DB model to design, and no API contracts. The "contract" this
feature produces is the record TEMPLATE itself, which is a FUTURE deliverable under
`templates/`, not a speckit `contracts/` dir.

### Repository artifacts this feature PLANS (not created this slice)

```text
docs/operations/
`-- adapter-compatibility-matrix.md   # PLANNED -- the single committed matrix (nine adapter rows)

templates/
`-- adapter-version-record.md         # PLANNED -- generic one-adapter record shape (copy-me)
```

These two files are FUTURE outputs. This planning slice does NOT create them; it
enumerates them so a later authoring slice (and the F031 policy that reads them) has a
specified target.

**Structure Decision**: documentation/planning feature -- no `src/` or `tests/` change.
The future matrix lives under a new `docs/operations/` dir (a home for kit-durability /
maintenance docs, parallel to `docs/readiness/`), keeping the matrix discoverable as an
operations record rather than a readiness-stage artifact. The future record template
lives in the existing `templates/` dir alongside the other copy-me artifacts. Both are
planned here, created later.

## Phase 0 -- Research (no external research needed)

No unknowns requiring external research. The reference shapes are already in-repo: the
readiness/issue templates (authoring header + namespace/placeholder convention) and
`docs/readiness/readiness-model.md` (the four-status vocabulary + no-fake-confidence
rule, which this feature extends with `unknown` for the compatibility sense). The
adapter list is fixed by the spec (the nine named adapters/dependencies). The one
organizing decision -- record (F032) vs policy (F031) as separate features -- is
resolved as the recommended default, not deferred research.

## Phase 1 -- Design (the planned artifact shapes)

**docs/operations/adapter-compatibility-matrix.md** (the matrix). Header block in the
house style: what it is (the version-truth record), which principles it instantiates
(VII generic, VIII static-first, IX no-BOM + no-fake-confidence as "UNKNOWN is not
compatible"), and the record/policy + record/build boundaries. Body: a single table with
one row per adapter/dependency -- Tower BI Kit, Python, Postgres, dbt-core, dbt-postgres,
Dagster, dagster-dbt, Power BI PBIP/TMDL assumptions, Power BI MCP adapter status -- and
columns: supported version range, required smoke test (named), smoke-test status,
last-verified date, owner. Plus the rules section: UNKNOWN-is-not-compatible,
range-required, smoke-test-required, no-numeric-score, owner-attests-to-promote, how
F031 reads the matrix, and "readiness stage affected: none directly".

**templates/adapter-version-record.md** (the per-adapter record template). Generic,
copy-me shape of ONE adapter's entry: `adapter` name, supported `range` (floor + tested
ceiling; untested bound = `unknown`), `smoke_test` (named), `status` (one of the explicit
statuses or `unknown`), `last_verified` date, `owner` (named attester), `evidence[]`,
`blocking_reasons[]`, plus authoring notes embedding the no-fake-confidence rule and the
"agent never self-attests / never self-promotes" rule. One generic example adapter
(e.g. "the transformation adapter against `<tool> >=X,<Y`") demonstrates the shape with
placeholders only -- zero C086 values.

These two are DESIGNED here and AUTHORED in a later slice. This slice produces only the
five planning files describing them.

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design adds only generic text artifacts (and
only PLANS them this slice), introduces no enforcement logic (that stays F031), touches
no adapter implementation (those stay F029/F030/F016), keeps the four-status + `unknown`
vocabulary with no numeric score, and advances no readiness stage. Both boundary gates
(record/policy, record/build) hold.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
