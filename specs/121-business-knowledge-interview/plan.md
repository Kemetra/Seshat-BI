# Implementation Plan: Business Knowledge Interview, Decision Store, and Knowledge Contracts

**Branch**: `121-business-knowledge-interview` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/121-business-knowledge-interview/spec.md`

## Summary

Add the decision-capture and contract layer beneath the future Database-to-PBIP flow:
a discovery-grounded Business Knowledge Interview (agent-conducted, contract-governed),
a machine-readable project Decision Store with a nine-status lifecycle and named-human
approval metadata, a regenerable human-readable review artifact, per-stage Knowledge
Contracts that pin allowed routes and stop rules, and pass/warn/blocked gate verdicts
that feed the existing readiness spine. Delivery follows the repo's established shape
for governance slices: templates + product contracts + a kit-router verb + a new
fail-closed static rule family in `retail check` + fixture tests. No PBIP compiler,
no publish, no database connector, no interview runtime engine -- the agent conducts
the interview conversationally; the contracts and gates make it governable.

## Technical Context

**Language/Version**: Python 3.13 for the static rule family and verdict projection
(matching the existing package contract). Product artifacts are YAML and Markdown.

**Primary Dependencies**: Existing `pyyaml>=6` only. The static check core stays
stdlib-only on its import path; no new dependency is added anywhere in this feature.

**Storage**: Local committed files only. Decision store under the project workspace
(`.seshat/semantic-decisions.yaml`, `.seshat/kpi-contracts.yaml`,
`.seshat/cleaning-rules.yaml`), product contracts under a new top-level `contracts/`
directory, blank shapes under `templates/`, generated review artifact in the workspace
evidence location. No database, no service state.

**Testing**: pytest unit + contract fixtures (valid store, each invalid-record class,
each seeded gate scenario from SC-003); `retail check` self-run stays exit 0 on the
repo; rule-registry snapshot test and `retail manifest` regeneration for the new rule
family; determinism test for review-artifact regeneration (NFR-002).

**Target Platform**: Windows-first (release gate), macOS/Linux best effort; CI on
Linux. Everything works offline (NFR-006); live samples are optional input.

**Project Type**: Single Python CLI/agent toolkit -- a governance slice (docs +
templates + contracts + kit verb + static rules), consistent with how the readiness
spine and capability inventory shipped.

**Performance Goals**: Static validation of a 500-decision store completes within the
existing `retail check` run budget (< 2 s added); review-artifact generation is
deterministic and < 1 s for 500 decisions; verdict recomputation is pure projection
over committed text (no I/O beyond reading the store and cited evidence paths).

**Constraints**: Fail-closed everywhere (malformed record => blocked, never pass); no
numeric confidence anywhere (only `low|medium|high` proposal confidence, never
surfaced as readiness); no self-granted approval; no secrets or raw suspected-PII
values in committed artifacts; UTF-8 without BOM; repo-relative paths <= 200 chars
(Windows MAX_PATH); no PBIP/publish/DB-execution surface.

**Scale/Scope**: Decision stores up to ~500 decisions spanning ~50 tables and ~30
KPIs; 11 flow-stage contract entries; 1 new static rule family (working name DS1-DS5);
1 new kit-router verb; 3 store templates + 1 review-artifact template. Not in scope:
an interview UI/runtime, a PBIP compiler, KPI catalog expansion, or any rewrite of the
five knowledge layers.

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.7.0 before research and
re-checked after Phase 1 design.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| I. Agent-First, Gate-Enforced | PASS / reinforced | Decision-store validity, approval metadata, and gate verdicts are enforced by a new fail-closed static rule family inside `retail check` (non-zero exit), not by prose. The agent conducts the interview; the gate disposes. |
| II. Depend, Never Fork | PASS / untouched | No execution adapter is touched. F016 stays deferred and gated; the publish/export decision type only records the human decision that will one day gate it. |
| III. Medallion, Postgres-First, Gold-Only | PASS / untouched | No warehouse authoring, no read-path change, no engine work. Decisions *about* grain/keys feed the existing medallion method; they do not alter it. |
| IV. Source Mapping Before Silver | PASS / reinforced | Pending grain/PK/relationship decisions produce blocked verdicts for Silver/Gold modeling (FR-032), which is Principle IV expressed as decision-level gates. The five mapping artifacts remain authoritative; the decision store records rulings, it does not replace `mappings/<table>/`. |
| V. Agent Stops at Judgment Calls | PASS / reinforced | The interview formalizes the stop-and-ask floor: critical decisions require explicit named-human approval with per-type authority eligibility; confidence never equals approval; batch sets exclude critical types by construction. |
| VI. Defaults Then Deviations | PASS | `cleaning-rules.yaml` records missing-value and cleaning *rulings* that start from RC1-RC16 and cite the triggering data fact on deviation; it does not fork or restate the ADR 0002 defaults. |
| VII. C086 Is An Example, Not The Schema | PASS | All templates and contracts are generic with placeholders; fixtures use synthetic data; no worked-example specifics are baked in. |
| VIII. Static-First Governance, Live Deferred | PASS | Everything ships as static checks over committed text. `needs_sample` truthfully marks the live boundary; no live runs are required or claimed. |
| IX. Secrets and Reproducibility | PASS / reinforced | Masked-samples-by-default, no raw suspected-PII in committed artifacts (FR-005), deterministic regeneration (NFR-002), UTF-8 no BOM, short paths. |

**Result: PASS. No constitutional violation requires Complexity Tracking.**

## Project Structure

### Documentation (this feature)

```text
specs/121-business-knowledge-interview/
├── plan.md                       # This file
├── research.md                   # Phase 0 output
├── data-model.md                 # Phase 1 output
├── quickstart.md                 # Phase 1 output
├── implementation-graph.md       # Task DAG, serialized hotspots, parallel waves
├── contracts/                    # Phase 1 output
│   ├── decision-record.schema.json
│   ├── knowledge-contract.schema.json
│   ├── gate-verdicts.md
│   └── interview-protocol.md
├── checklists/requirements.md
├── spec.md
└── tasks.md                      # Phase 2 output (/speckit-tasks -- NOT created here)
```

### Source Code (repository root)

```text
contracts/                                  # NEW top-level product-contract dir
├── README.md                               # what lives here; contracts vs templates
├── knowledge/database-to-pbip-flow.yaml    # 11 stage entries (FR-027)
├── knowledge/approval-authority.yaml       # decision_type -> eligible authority classes (FR-021)
├── interview/business-knowledge-interview.yaml
└── report/dashboard-blueprint.yaml

templates/                                  # blank shapes (existing dir)
├── semantic-decisions.yaml                 # decision-store blank
├── kpi-contracts.yaml                      # KPI-meaning decision blank
├── cleaning-rules.yaml                     # cleaning/missing-value ruling blank
└── business-interview-review.md            # review-artifact blank (FR-024/025)

src/retail/
├── decision_store.py                       # load/validate store records (fail-closed)
├── decision_gate.py                        # pass/warn/blocked verdict projection (FR-033/034)
├── interview_review.py                     # deterministic review-artifact generator (R-5)
└── rules/decision_store.py                 # DS1-DS5 static rule family (registered)

.claude/skills/business-knowledge-interview/  # the gated interview verb (agent-conducted)
.seshat/kit-source.yaml                     # router entry for the new verb (regenerated block)

docs/knowledge-map.md                       # + routes: interview / decision store / decision gate
docs/glossary.md                            # + decision statuses, verdicts, DS rule family

tests/unit/
├── test_decision_store.py                  # schema, statuses, immutability, supersession
├── test_decision_gate.py                   # SC-003 seeded gate scenarios, fail-closed
└── test_decision_store_rules.py            # DS1-DS5 rule fixtures + manifest snapshot
```

**Structure Decision**: single-project layout on the existing `src/retail/` package;
new product contracts get the top-level `contracts/` directory the spec proposed
(research.md R-4 confirms no conflicting convention exists); blank shapes join the
existing `templates/` set exactly as the five mapping-gate artifacts did; the
interview verb follows the established `.claude/skills/` + kit-router pattern.

## Complexity Tracking

No constitutional violations; table intentionally empty.
