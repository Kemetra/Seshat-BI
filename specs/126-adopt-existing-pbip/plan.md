# Implementation Plan: Governed Existing PBIP Adoption

**Branch**: `126-adopt-existing-pbip` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/126-adopt-existing-pbip/spec.md`

## Summary

Add a thin, offline `seshat adopt-pbip` composition surface for analysts who
already have a PBIP project. `assess` inventories supported PBIP/TMDL/PBIR text,
reuses shipped governance findings and canonical readiness/next-action
projections, redacts unsafe values, and emits equivalent text and JSON without
writing. `scaffold` recomputes that assessment and requires the user to accept
its exact digest before atomically creating one new
`.seshat/adoption/pbip-adoption.yaml` evidence manifest. The manifest records a
baseline and unresolved proposals; it owns no readiness state and grants no
approval. The existing PBIP workflow skill and shared public Seshat router expose
the same entry path to repository agents and generated Claude/Codex bundles.

## Technical Context

**Language/Version**: Python >=3.13

**Primary Dependencies**: Python standard library, existing runtime PyYAML, and
existing Seshat parsers, rule registry, disclosure scanner, readiness status,
blocker, and run-next services; no new dependency

**Storage**: Local PBIP/TMDL/PBIR and Seshat YAML/JSON files; assessment is
stdout-only, while accepted scaffolding writes one YAML manifest

**Testing**: pytest unit and contract suites, CLI tests, fixture byte snapshots,
`seshat check`, Ruff, and the documented quickstart

**Target Platform**: Windows as the primary supported environment, with
macOS/Linux filesystem behavior covered where the existing package supports it

**Project Type**: Python library and CLI package

**Performance Goals**: Complete a typical assessment (up to five reports, five
semantic models, 500 measures, and 100 pages) in under five minutes; never
silently truncate larger supported inventories

**Constraints**: Offline and read-only assessment; no Desktop, Service, database,
DAX execution, network, or feature-016 adapter; deterministic substantive output;
UTF-8 without BOM; project-relative paths only; no secret/raw-value disclosure;
no score; no implicit Git initialization; no existing-file overwrite

**Scale/Scope**: One bounded local PBIP project per invocation, including
multi-report/multi-model projects that are reported as ambiguous when their
relationships are not explicit

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

### Pre-research gate

- **I — Agent-first, gate-enforced**: PASS. The CLI is a deterministic helper an
  agent composes through the PBIP workflow/router surfaces; existing static
  findings and live-validation boundaries retain authority.
- **II — Depend, never fork**: PASS. Existing TMDL/PBIR readers, governance rules,
  status projection, blocker explanation, and run-next logic are composed. The
  Power BI execution adapter is not invoked.
- **III/IV — Medallion order and mapping gate**: PASS. PBIP structure is candidate
  evidence only; it cannot skip Source/Mapping or authorize silver/gold work.
- **V — Human judgment stops**: PASS. Proposals name required human authority,
  `approvals` remains empty, and no categorical status is upgraded.
- **VI/VII — Defaults and generic design**: PASS. The command uses deterministic
  safe defaults and generic PBIP fixtures; no C086 domain assumptions are used.
- **VIII — Static first, live deferred**: PASS. The feature is fully offline and
  never claims semantic correctness or a live-validation pass.
- **IX — Secrets and reproducibility**: PASS. All locations are project-relative,
  disclosure scanning fails closed, writes are UTF-8/LF, and paths are contained.
- **Readiness spine**: PASS. The adoption manifest is a fingerprinted evidence
  snapshot, not a readiness file, gate, score, or second run-state engine.

### Post-design gate

PASS with no exceptions. The data model has exactly one `next_step`, preserves
the five required classifications, carries concrete blockers/evidence, and
contains no numeric readiness field. The CLI contract makes assessment
write-free and makes scaffold acceptance, Git presence, containment, collision
preflight, and staged publication mandatory. No complexity waiver is required.

## Project Structure

### Documentation (this feature)

```text
specs/126-adopt-existing-pbip/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── adopt-pbip-cli.md
│   ├── pbip-adoption-assessment.schema.json
│   └── pbip-adoption-scaffold-result.schema.json
└── tasks.md
```

### Source Code (repository root)

```text
src/seshat/
├── pbip_adoption.py                    # normalized assessment + scaffold service
└── cli/
    ├── parser.py                       # imports/assembles the adoption parser
    ├── parser_adoption.py              # argparse-only command contract
    ├── __init__.py                     # one lazy dispatch row
    └── commands/adopt_pbip.py          # text/JSON rendering and exit policy

schemas/
├── pbip-adoption-assessment.schema.json
└── pbip-adoption-scaffold-result.schema.json

tests/
├── fixtures/pbip_adoption/             # supported, unsafe, ambiguous, PBIX cases
├── contract/test_pbip_adoption_schema.py
└── unit/
    ├── test_pbip_adoption.py
    ├── test_pbip_adoption_scaffold.py
    └── test_cli_pbip_adoption.py

docs/tools/
└── pbip-adoption.md

.claude/skills/pbip-workflow/
└── SKILL.md                           # existing-PBIP adoption route

distribution/bundle-templates/shared/skills/seshat-bi/
└── SKILL.md                           # shared Claude/Codex route

integrations/
├── claude-code/seshat-bi/             # deterministically regenerated bundle
└── codex/seshat-bi/                   # deterministically regenerated bundle

docs/capabilities/
└── capabilities.yaml                  # shipped CLI/agent capability claim
```

**Structure Decision**: Keep the feature inside the existing single Python
package. One domain module owns normalized facts, fingerprints, and safe
scaffolding; a small parser module avoids worsening the parser hotspot; a lazy
command handler preserves the static-check import boundary. The public schema is
copied from the design contract and validated by a focused contract test. Agent
discovery extends the existing PBIP skill and shared generated-bundle router;
generated integration trees remain outputs of the reviewed export inputs, never
hand-edited copies.

## Complexity Tracking

No constitution violations or justified complexity exceptions.
