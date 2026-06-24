# Implementation Plan: Metric Contract Store + Retail KPI Packs

**Branch**: `010-metric-contract-store` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-metric-contract-store/spec.md`

## Summary

Build the metric-DEFINITION layer of Layer 5 (Roadmap F009): a generic, copy-me
**metric-contract template**, a generic **KPI-pack template** with one example generic
pack, and a **store layout + authoring guide** doc -- then resolve the "metric contracts
PLANNED, not yet built" note in the Semantic Model Ready stage doc to point at the new
template. This is **docs/templates only** (Principle VIII; roadmap rule #8): no Python,
no CLI verb, no `retail check` rule, no PBIP read. The contract is INTENT + binding +
explicit readiness status (four words, evidence, blockers -- never a score). CHECKING a
PBIP model against these contracts is the separate later feature F010 / on-disk 011 and
is out of scope here.

## Technical Context

**Language/Version**: None (docs/templates only -- Markdown + YAML text artifacts).

**Primary Dependencies**: None at runtime. Authoring style borrows from
`templates/source-map.yaml` (header + namespace/placeholder convention) and the readiness
vocabulary from `templates/readiness-status.yaml` / `docs/readiness/readiness-model.md`.

**Storage**: Committed text files in the repo: `templates/`, `docs/metrics/`, and a doc
pointer edit in `docs/readiness/semantic-model-ready.md`. Filled contracts (a later,
per-table activity) live under `mappings/<table>/metrics/`; the reusable pack store under
a top-level `metrics/` dir (see Structure Decision + open question O-1).

**Testing**: No code, so no unit tests. Verification is: (1) `retail check` exit 0 with
rule count unchanged, (2) YAML templates parse as valid YAML, (3) a manual generic
fill-in proves every required field is present and no C086 specifics leak, (4) ASCII +
UTF-8 no-BOM check on every new file.

**Target Platform**: Repo text artifacts consumed by an agent + reviewed by a human; the
Semantic Model Ready stage reads them later.

**Project Type**: Documentation/templates feature (no source tree change).

**Performance Goals**: N/A (static text).

**Constraints**: ASCII + UTF-8 no BOM; generic (no C086/pharmacy values); Windows path
budget (`<= 200` chars repo-relative -- keep names short); no numeric confidence score
anywhere; no PBIP read; no checker/CLI/rule.

**Scale/Scope**: 3 new files + 1 small doc-pointer edit. One example generic KPI pack.

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | Adds no gate and no agent authority over pass/fail. The contract template is something the agent FILLS (like `source-map.yaml`); approval authority is the named human owner, not the agent. `retail check` stays the gate; this feature does not touch it. |
| II. Depend, Never Fork | No engine, no pbi-cli, no fork. Pure local opinion in templates/docs. |
| III. Medallion, Gold-Only | FR-012: `binds_to` references `gold` only; a contract binding to silver/bronze is a defect. |
| IV. Source Mapping Before Silver | Not triggered (no silver SQL). The contract sits at Layer 5, downstream of an approved map + built gold; the plan records that ordering but writes no SQL. |
| V. Agent Stops at Judgment Calls | FR-009: business rollup/segment, grain ambiguity, and PII publish-safety are stop-and-ask `blocking_reasons`, never auto-filled. Recorded in spec edge cases and carried into the template's authoring notes. These are exactly the items the orchestrator routes to a human. |
| VI. Defaults Then Deviations | The template starts from the existing conventions (PascalCase names, gold-only binding) as defaults; deviations are recorded, not silent. |
| VII. C086 Is An Example | FR-006/SC-002: all artifacts generic; C086 cited as the filled instance, never inlined. Obvious placeholders. |
| VIII. Static-First, Live Deferred | FR-007/SC-003: NO Python, NO rule, NO CLI, NO PBIP read; `retail check` rule count unchanged, exit 0. Docs/templates only (rule #8). |
| IX. Secrets & Reproducibility | No secrets. ASCII + UTF-8 no BOM; short paths; templates are reproducible copy-me text. |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Boundary gate (feature-specific, load-bearing)

The single biggest design risk is scope-bleed into F010 (the CHECKING half). The plan
holds the boundary explicitly:

- This feature DEFINES (authors contract/pack text + the store rules). It does NOT CHECK.
- No artifact here reads `powerbi/<Model>.SemanticModel/`, asserts a measure/relationship/
  date-table, or adds a `retail check` rule.
- The doc-pointer edit to `semantic-model-ready.md` only resolves the "artifact missing"
  note; it MUST NOT change that stage's gates or add a PBIP check.

## Project Structure

### Documentation (this feature)

```text
specs/010-metric-contract-store/
├── spec.md              # /speckit-specify output (done)
├── plan.md              # This file (/speckit-plan output)
├── tasks.md             # /speckit-tasks output
├── analysis.md          # /speckit-analyze findings (recorded here)
└── checklists/
    └── requirements.md  # spec quality checklist (done)
```

No `research.md` / `data-model.md` / `contracts/` directory is generated: there is no
code to research, no DB model to design, and no API contracts -- the "contracts" this
feature produces are the metric-contract TEMPLATES themselves, which live under
`templates/` (the deliverable), not under a speckit `contracts/` dir.

### Repository artifacts this feature adds/edits (the deliverable)

```text
templates/
├── metric-contract.yaml          # NEW -- generic one-metric definition template
└── kpi-pack.yaml                 # NEW -- generic KPI-pack template + 1 example generic pack

docs/metrics/
└── metric-contract-store.md      # NEW -- store layout + authoring guide + lifecycle + boundary

docs/readiness/
└── semantic-model-ready.md       # EDIT -- resolve "artifacts PLANNED" note -> point at template
```

Filled instances (NOT created by this feature; their LOCATION is defined by the guide):

```text
mappings/<table>/metrics/<MetricName>.yaml   # per-table filled contracts (parallel to the 5 gate artifacts)
metrics/packs/<pack_name>.yaml               # reusable KPI packs (top-level store)
```

**Structure Decision**: docs/templates feature -- no `src/` or `tests/` change. New
templates live in the existing `templates/` dir (alongside the five mapping-gate
templates) so all copy-me artifacts share one home; the narrative guide lives in a new
`docs/metrics/` dir (parallel to `docs/readiness/`), keeping `docs/` narrative-only.
Filled-contract placement (`mappings/<table>/metrics/` + top-level `metrics/packs/`)
follows ADR 0003's "cohesive per-table working set" rationale; recorded as a default in
the guide and flagged as open question O-1 (cheaply reversible -- a path move).

## Phase 0 -- Research (no external research needed)

No unknowns requiring external research. The two reference shapes are already in-repo:
`templates/source-map.yaml` (authoring header + namespace/placeholder convention) and
`templates/readiness-status.yaml` + `docs/readiness/readiness-model.md` (the four-status
vocabulary + no-score rule). The one open decision (O-1, filled-contract path) is resolved
with a recommended default, not deferred research.

## Phase 1 -- Design (the artifact shapes)

**metric-contract.yaml** (generic template). Header block in the `source-map.yaml` style:
what it is, which principles it instantiates (III gold-only, V stop-and-ask, VII generic,
IX no-BOM), the no-score rule (#9), and a generic-placeholder note. Fields:
`name` (PascalCase), `grain`, `formula_intent` (plain language; explicit "NOT DAX" note +
a generic intent-vs-implementation example), `owner`, `binds_to` (gold table + columns),
`status` (one of the four words), `evidence[]`, `blocking_reasons[]`, plus authoring notes
that enumerate the Principle-V stop-and-ask triggers.

**kpi-pack.yaml** (generic template + one example pack). Fields: `pack_name`, `purpose`,
`owner`, `contracts[]` (stable names referencing metric contracts). The example pack uses
generic retail KPI names only (e.g. a generic "sales overview" set) -- zero C086 values.

**docs/metrics/metric-contract-store.md** (guide). Sections: purpose; where filled
contracts + packs live; the draft -> reviewed -> approved lifecycle mapped to the four
statuses; the owner-approval-as-evidence rule (a `pass` needs owner + date); the no-score
rule; the Principle-V stop-and-ask list; the define/check boundary (this feature defines;
F010/on-disk-011 checks); and how Semantic Model Ready reads contracts.

**semantic-model-ready.md edit**: change the "Metric contracts | feature 009/010 artifact
| ..." required-artifact row's note from "PLANNED, not yet built" to "template now exists:
`templates/metric-contract.yaml` (filled per table under `mappings/<table>/metrics/`)",
leaving every gate, status, and the F010 PBIP-check responsibility unchanged.

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design adds only generic text artifacts, reads
no PBIP, adds no rule, and keeps gold-only binding + the four-status/no-score vocabulary.
Boundary gate holds (no `powerbi/` read; the doc edit changes no gate).

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
