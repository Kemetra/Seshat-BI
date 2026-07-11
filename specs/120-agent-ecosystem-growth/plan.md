# Implementation Plan: Agent Ecosystem Growth

**Branch**: `120-agent-ecosystem-growth` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/120-agent-ecosystem-growth/spec.md`

## Summary

Turn Seshat BI's existing governance depth into a visible and composable ecosystem:
an offline five-minute proof, reusable change-review integration, a read-only MCP
governor, portable readiness passports, governed local extension packs, bounded
contribution lanes, a categorical BI-agent safety benchmark, and a disclosure-safe
static readiness explorer. Delivery is phased in user-story priority order; each phase
is independently releasable and User Story 1 is the MVP. All new surfaces reuse the
existing readiness/status/findings/evidence contracts and remain projections or
formatters rather than new authorities.

## Technical Context

**Language/Version**: Python 3.13, matching the current package contract. Generated
explorer assets use standards-based HTML, CSS, and small dependency-free JavaScript.

**Primary Dependencies**: Existing `pyyaml>=6`; optional MCP extra pinned to stable
`mcp>=1.28,<2`; no dependency is added to the static check core. GitHub integration is
a composite action that installs the released `seshat-bi` package. Static rendering
uses the Python standard library and committed brand assets.

**Storage**: Local files only. Authoritative state remains under
`mappings/<table>/readiness-status.yaml` plus its cited committed artifacts. Derived
output defaults to gitignored `.seshat-output/`; no service database or registry.

**Testing**: pytest unit, contract, and integration tests; existing `retail check`,
`retail semantic-check`, and `retail kit-lint`; clean-environment action smoke test;
MCP in-memory/stdio contract test; static-page DOM, accessibility, screenshot, and
disclosure checks at desktop and mobile viewports.

**Target Platform**: Windows release gate; macOS/Linux supported best effort per spec
119. GitHub-hosted review workflow on Linux. MCP v1 stdio clients. Static explorer in
current evergreen desktop/mobile browsers and offline after generation.

**Project Type**: Single Python CLI/agent toolkit with optional local MCP adapter,
generated static web output, and distribution integrations. No hosted backend.

**Performance Goals**: Five-minute first success; review summary for a 2,000-file repo
within 60 seconds excluding package installation; read-only tool response within two
seconds for a 100-table local workspace; passport/explorer generation within 10 seconds
for 100 tables and 2,000 evidence references; static explorer first render under two
seconds for the reference portfolio.

**Constraints**: Offline-first; local workspace boundary; deterministic same-input
outputs except explicitly recorded generation time; no score; no self-approval; no
remote pack registry; no database or Power BI execution; no hidden telemetry; no secret,
PII, raw-value, DSN, or absolute-path disclosure; Windows-safe relative paths; MCP
dependency remains optional and absent from the static core import graph.

**Scale/Scope**: Eight independently releasable phases. Initial conformance targets 100
tables, 2,000 evidence references, 50 locally selected packs, and 100 benchmark
scenarios. This is not an enterprise hosted control plane, remote registry, agent
leaderboard, Power BI publisher, or replacement state engine.

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.7.0 before research and
re-checked after design.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| I. Agent-First, Gate-Enforced | PASS / reinforced | The agent governor and review integration expose existing gates and refuse premature work; the CLI remains a helper surface. |
| II. Depend, Never Fork | PASS | MCP, GitHub Actions, and browser standards are adapters. Any marketplace wrapper is generated one-way from this canonical repo. F016 is untouched. |
| III. Medallion, Postgres-First, Gold-Only | PASS / untouched | No warehouse authoring, source-of-truth change, or Power BI read-path change. |
| IV. Source Mapping Before Silver | PASS / enforced | Review and governor contracts explicitly block silver while Mapping Ready is uncleared. |
| V. Agent Stops at Judgment Calls | PASS / reinforced | Approval tools prepare requests and carry receipts; they cannot grant approval. |
| VI. Defaults Then Deviations | PASS | Packs declare deviations and owners; they cannot silently override defaults. |
| VII. C086 Is an Example | PASS | Reference data and packs are synthetic/generic; C086 is not used as a schema. |
| VIII. Static-First, Live Deferred | PASS | MVP, action, MCP, passports, packs, benchmark reference runner, and explorer work without a DB. Live absence remains visible. |
| IX. Secrets and Reproducibility | PASS / reinforced | Local output, canonical relative paths, disclosure scanning, stable schemas, deterministic fixtures, and no hidden telemetry. |

**Result: PASS. No constitutional violation requires Complexity Tracking.**

## Project Structure

### Documentation (this feature)

```text
specs/120-agent-ecosystem-growth/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── implementation-graph.md # Task DAG, serialized hotspots, safe parallel waves
├── contracts/
│   ├── agent-governor-tools.md
│   ├── benchmark-run.schema.json
│   ├── extension-pack.schema.json
│   ├── readiness-passport.schema.json
│   ├── review-integration.md
│   └── static-projection.schema.json
├── checklists/requirements.md
├── spec.md
└── tasks.md
```

### Source Code (repository root)

```text
src/seshat/
├── readiness_projection.py          # shared status/evidence/blocker projection
├── artifact_identity.py             # canonical paths + content identities
├── disclosure.py                    # shared public-output safety boundary
├── demo/
│   ├── report.py                 # extend text/json with safe HTML projection
│   └── html_report.py            # deterministic MVP renderer
├── sarif.py                      # Finding -> SARIF 2.1.0 formatter
├── review_integration.py         # changed-state digest + review summary
├── governor/
│   ├── service.py                # transport-neutral read-only operations
│   └── mcp_server.py             # optional stable MCP v1 stdio adapter
├── passport.py                   # export + verify artifact identities
├── packs/
│   ├── model.py
│   ├── loader.py
│   ├── validator.py
│   └── scaffold.py
├── benchmark/
│   ├── model.py
│   ├── reference.py
│   ├── runner.py
│   └── render.py
└── explorer/
    ├── build.py
    └── assets/                   # accessible CSS/JS; brand assets referenced

schemas/
├── readiness-passport.schema.json
├── seshat-extension-pack.schema.json
├── benchmark-run.schema.json
└── static-readiness-projection.schema.json

integrations/github-action/
├── action.yml
├── README.md
└── entrypoint.ps1

benchmark/scenarios/              # synthetic scenario manifests + fixtures
packs/reference/                  # generic reference packs from 3 categories
.github/
├── ISSUE_TEMPLATE/               # defect, capability, pack, compatibility, starter
└── pull_request_template.md
docs/
├── ecosystem/
├── contributing/first-contribution.md
└── demo/

tests/
├── contract/                     # JSON schema, MCP tool, action output contracts
├── integration/                  # clean workspace, action, browser/static flows
└── unit/                         # formatters, validators, disclosure, conflict tests
```

**Structure Decision**: Keep one canonical Python project. Each new capability has a
transport-neutral pure core and a thin CLI/integration adapter. The MCP dependency is an
optional extra. The GitHub action lives in this repository for source authority; if a
Marketplace-only repository is later approved, it is generated and verified from this
directory rather than maintained independently. Explorer output is generated data and
is never committed by default.

## Phase 0 - Research

See [research.md](./research.md). Key decisions:

1. Extend spec 119's installed first-success path; do not rebuild packaging.
2. Use stable MCP v1 (`mcp>=1.28,<2`) and local stdio only.
3. Emit SARIF 2.1.0 optionally, with JSON/job-summary fallback where upload is unavailable.
4. Load declarative local pack manifests; do not execute pack Python or discover remotely.
5. Use artifact content hashes plus canonical relative paths for passport verification.
6. Keep the benchmark categorical and disclose stochastic run conditions.
7. Generate a self-contained static explorer from a disclosure-filtered projection.

No `NEEDS CLARIFICATION` remains.

## Phase 1 - Design and Contracts

- [data-model.md](./data-model.md) defines the shared projection, passport, pack,
  benchmark, and contribution entities and their state rules.
- `contracts/` defines the observable boundaries for MCP tools, review integration,
  passport, packs, benchmark runs, and static projections.
- [quickstart.md](./quickstart.md) is the acceptance walkthrough for planning and later
  implementation verification.
- The SPECKIT pointer in `CLAUDE.md` references this plan.

## Delivery Phases

| Phase | Story | Independently releasable result |
|------:|-------|---------------------------------|
| 1 | US1 | Installed offline demo emits a professional, disclosure-safe static readiness proof. |
| 2 | US2 | Reusable change-review action emits job summary, JSON, and optional SARIF without duplicate noise. |
| 3 | US3 | Stable local stdio MCP governor exposes six read-only tools over existing services. |
| 4 | US4 | Passport export/verify detects stale, missing, incompatible, and unavailable evidence. |
| 5 | US5 | Local declarative pack scaffold/validate/load with conflicts and three reference packs. |
| 6 | US6 | Structured issue/PR paths and bounded starter contribution lanes. |
| 7 | US7 | Synthetic categorical safety benchmark with reference participant and disclosed run metadata. |
| 8 | US8 | Offline static portfolio explorer over the shared disclosure-safe projection. |

## Post-Design Constitution Re-check

**PASS unchanged.** The data model carries status/evidence/blockers without a score;
approvals remain receipts tied to named human sources; all integrations are read-only by
default; packs are declarative and local; the explorer and passport are derived; F016,
live DB execution, semantic definitions, and publishing authority remain outside scope.

## Complexity Tracking

No violations to justify.
