# Implementation Plan: Portfolio Watch

**Branch**: `131-portfolio-watch` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/131-portfolio-watch/spec.md`

**Note**: This plan is spec-driven. It STOPS after Phase 1 design + `/speckit.analyze`. It does NOT implement code, does NOT ratify any ADR/approval (those are named-human seams per Constitution Principle V), and does NOT merge.

## Summary

Deliver a **recurring, read-only portfolio summary** that DERIVES its result entirely from evidence the shipped Seshat surfaces already produce (source drift, contract/metric drift, dashboard-intent audit, readiness projection, approval inbox, review integration) and adds one genuinely-new mechanic: a **persisted prior-run snapshot** so the next run can diff current categorical state into `new` / `resolved` / `unchanged` and suppress duplicate alerts. The technical approach is **skill-driven** (ratified Option-B): the summary is composed by a new agent skill (`portfolio-watch`), with a small read-only **pure library** in `src/seshat/` (the deterministic aggregator + change classifier) so the diff and the "one prioritized next action per scope" are byte-deterministic and unit-testable. The one deliberate CLI addition is a narrow read-only summary/status surface mirroring the ratified `status --format json` precedent -- NOT a broad new verb family. No new gate, no new `retail check` rule, no new approval mechanism, no numeric score, no live DB, no write-back beyond the local summary + snapshot.

## Technical Context

**Language/Version**: Python 3.13 (matches shipped `src/seshat/`; `pyproject.toml`).

**Primary Dependencies**: **stdlib only** for new code (`json`, `pathlib`, `dataclasses`, `hashlib` for stable snapshot keys, `subprocess` only to read `git rev-parse HEAD` as the shipped `readiness_projection._source_revision` already does). Reuses shipped modules as READERS: `readiness_projection.py`, `readiness_classify.py`, `status_surface.py`, `agent_next.py`, `drift.py`, `metric_drift.py`, `semantic_audit.py`, `report_intent.py`, `approval_inbox.py`, `review_integration.py`. YAML/PyYAML (already a dev/optional dep) only where a reused reader already imports it lazily; the aggregator core stays stdlib-only so it never trips the B3 import-boundary guard.

**Storage**: Committed on-disk artifacts only. The summary + the prior-run snapshot are LOCAL artifacts (proposed location `.seshat/watch/` -- see research D2). Inputs are the committed evidence the shipped surfaces read/emit (`readiness-status.yaml`, committed source-drift-findings artifacts, metric contracts + TMDL, semantic-audit inputs, `.seshat/*` approval state). **No database** in the MVP (SEC-001); live-only dimensions degrade to `[PENDING LIVE]`.

**Testing**: pytest with `unit` / `integration` markers (`pyproject.toml [tool.pytest.ini_options]`); TDD RED->GREEN. Determinism is asserted directly (identical inputs -> byte-identical summary + change labels). No new static rule is wired (this feature adds none), so the "rule emits-on-main" discipline does not apply.

**Target Platform**: Cross-platform CLI + agent skill (Windows-first dev; POSIX CI). All produced text UTF-8 without BOM, `core.autocrlf=true`, short repo-relative paths (CLAUDE.md hard rules).

**Project Type**: Analytics tooling kit -- Python library + `retail`/`seshat` CLI + Claude skills. Portfolio Watch is a Tier-5 read/summarize/derive companion (roadmap binding rule: may READ/SUMMARIZE/derive evidence, MUST NOT create truth).

**Performance Goals**: N/A as latency/throughput. Binding constraints are **determinism** (byte-identical summary + change labels for identical inputs + snapshot), **truthful degradation** (never fabricate coverage/comparison), and **linear-in-scope** cost (mirror `readiness_projection`'s deliberate per-table linearity; no quadratic cross-table join).

**Constraints**: Read-only; local artifacts only; no numeric health/confidence/priority/quality score (FR-020); no new gate/rule/approval (FR-019); no originated Principle-V ruling (FR-021); no live DB in MVP (SEC-001); no scheduler in MVP (FR-024); at most one narrow CLI addition (FR-023); generic core (Principle VII); redaction preserved (SEC-002).

**Scale/Scope**: 4 user stories; MVP = US1 + US2 + US3 (all P1). Scope count = the governed scopes the readiness spine already tracks. One worked example is a filled instance cited as reference, never the schema (Principle VII).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Gates derived from `.specify/memory/constitution.md` (v1.7.0):

| Principle | Gate | Status |
|---|---|---|
| I -- Agent-First, Gate-Enforced | Enforcement lives in checkers, not prose; the agent is never the pass-authority | **PASS** -- Watch adds NO gate; it READS existing gate/evidence outputs and never asserts a `pass`. The `retail check` exit contract is unchanged (SC-009). |
| II -- Depend, Never Fork | Reuse shipped/external surfaces; do not fork | **PASS** -- reuses the shipped readers verbatim as inputs; forks/replaces none (esp. not `retail-control-room`). |
| III -- Medallion, Gold-Only | Power BI reads gold only | **N/A** -- Watch touches no schema and no Power BI read path; it summarizes committed governance evidence. |
| IV -- Source Mapping Before Silver | Map before build | **N/A** -- Watch writes no silver/gold; it observes readiness, never advances a stage. |
| V -- Agent Stops at Judgment Calls / No Self-Grant | Business/PII/grain/returns/approval judgments are named-human, never self-granted | **PASS** -- FR-021/SC-010: no Principle-V ruling ORIGINATES in Watch; it RELAYS upstream grain/returns/PII/approval conditions and names the owner, deciding none. `open_for_human` is empty for this feature. |
| VI -- Defaults Then Deviations | Deviations need a cited data fact | **PASS** -- every plan-time decision (research D1-D8) cites a shipped pattern; conflicts resolved to documented defaults. |
| VII -- Example, Not Schema | Worked example never becomes the generic schema | **PASS** -- FR-025; the aggregator is generic; any filled instance is cited, never baked in. |
| VIII -- Static-First, Live Deferred | Static now; live deferred | **PASS** -- SEC-001/FR-013: MVP reads committed artifacts + pure readers only; live-only dimensions -> `[PENDING LIVE]`, mirroring `docs/readiness/source-drift.md`. |
| IX -- Secrets & Reproducibility | Secrets only in `.env`; deterministic artifacts | **PASS** -- SEC-002: shipped redaction preserved; no DSN/secret in summary/snapshot; the summary + change classifier are deterministic (SC-006). |
| Readiness System | `pass` carries evidence; NO fabricated confidence number | **PASS** -- FR-020: four spine statuses + shipped categorical enums + measured magnitudes only; the "one next action" uses the shipped `readiness_classify` fixed rank, never a computed priority. |
| Hard rule #1 (agent-first CLI) | CLI stays a narrow gate; agent+skills are the interface | **PASS** -- FR-023: delivered as a skill; at most one narrow read-only summary/status surface (the ratified `status --format json` precedent), no broad verb family. |
| Hard rule #9 (no fake confidence) | No rolled-up score | **PASS** -- FR-020/SC-003; measured magnitudes are allowed, a rolled-up score is forbidden. |

**Complexity Tracking**: no unjustified violations. The one net-new persisted artifact (the prior-run snapshot) is REQUIRED to satisfy new/resolved/unchanged + duplicate-suppression (FR-007..FR-010); it is a local, read-only-in-effect baseline modeled on `drift.py`'s baseline/observed, not a new source of truth or a gate. No Complexity Tracking table needed.

## Project Structure

### Documentation (this feature)

```text
specs/131-portfolio-watch/
|-- plan.md              # This file
|-- research.md          # Phase 0 -- technical decisions D1-D8
|-- data-model.md        # Phase 1 -- entities, summary/snapshot shapes, dimension->source map, degradation states
|-- quickstart.md        # Phase 1 -- how to run the MVP twice and read the baseline diff
|-- contracts/           # Phase 1 -- the summary + snapshot artifact contracts (read-only, no gate)
|   |-- portfolio-watch-summary.md
|   `-- portfolio-watch-snapshot.md
|-- checklists/
|   `-- requirements.md  # from /speckit.specify
`-- tasks.md             # Phase 2 -- from /speckit.tasks
```

### Source Code (repository root) -- anticipated touch points (NOT created by this plan)

```text
src/seshat/
|-- portfolio_watch.py                    # NEW (US1/US2/US3) -- pure, stdlib-only aggregator + change classifier.
|                                         #   Composes the shipped readers (like agent_next.py composes run_next +
|                                         #   status_surface); NO DB, NO write-back, deterministic, no score.
`-- cli/commands/watch.py (if a verb)     # NEW, OPTIONAL (US1) -- the ONE narrow read-only summary surface
                                          #   (e.g. `retail watch --format json`), mirroring the shipped
                                          #   read-only projection verbs. No broad family (FR-023).

.claude/skills/
`-- portfolio-watch/SKILL.md              # NEW (US1/US2/US3) -- the agent-facing recurring-summary skill,
                                          #   sibling to retail-control-room; invoke-and-present, read-only.

.seshat/watch/                            # NEW runtime dir (local artifacts only) -- created at run time, NOT by this
|-- portfolio-watch-summary.json|md       #   plan. The summary + the prior-run snapshot. Gitignore vs commit is a
`-- snapshot.json                         #   research decision (D2). No per-scope artifact is ever written here.

docs/tools/portfolio-watch.md             # NEW (US1) -- read-only tool doc, sibling to dashboard-planner.md /
                                          #   dashboard-gap-detector.md.

docs/capabilities/capabilities.yaml       # EDIT (US1) -- add one `portfolio-watch` entry (state/authority/surface/
                                          #   requirements), consistent with retail-control-room's shape.
```

**Structure Decision**: Single-project layout (the shipped `src/seshat/` + `.claude/skills/` + `docs/tools/` structure). The composition logic is a small pure library module (`portfolio_watch.py`) exactly as `agent_next.py` composes `run_next` + `status_surface` into a portfolio-level document; the agent-facing surface is a skill (`portfolio-watch/`), the sibling of `retail-control-room`. This matches the shipped read-only-projection architecture and keeps the generic core free of tenant logic (Principle VII).

## Phase 0 -- complete

See `research.md` (D1-D8). All plan-time unknowns the spec deferred are resolved with cited grounding. No NEEDS CLARIFICATION remain.

## Phase 1 -- complete

- `data-model.md`: the Portfolio Watch Summary shape, the Prior-Run Snapshot shape, the Condition-Change classification, the dimension->shipped-source map, and the truthful-degradation state set.
- `contracts/`: the summary artifact contract + the snapshot artifact contract (both read-only; neither is a gate).
- `quickstart.md`: run the MVP twice on a generic multi-scope fixture and read `new`/`resolved`/`unchanged`.
- Agent context: `CLAUDE.md` SPECKIT pointer updated to this plan.

**Post-design Constitution re-check**: still PASS on all gates. No new violation introduced by the design; no gate/rule/approval is added; the one new artifact is a local baseline, not a source of truth.

## Explicit STOPs (human seams -- NOT cleared by this chain)

- **Ratification of this spec** is a named-human action (Principle V). This chain drafts specify -> plan -> tasks -> analyze and STOPS; it does not mark the spec Ratified and does not implement.
- **No Principle-V ruling** originates here to clear; Watch relays upstream grain/returns/PII/approval conditions only (FR-021). There is therefore no per-feature judgment seam for this feature beyond spec ratification itself.
- **The one CLI addition** (if taken) is a narrow read-only surface; growing it into a verb family would need the owner to revisit the ratified Option-B decision -- out of scope for this chain.
