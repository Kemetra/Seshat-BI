# Implementation Plan: Governed Dashboard Intelligence and PBIR Authoring

**Branch**: `123-governed-dashboard-intelligence` | **Date**: 2026-07-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/123-governed-dashboard-intelligence/spec.md`

**Note**: This plan is spec-driven. It STOPS after Phase 1 design + `/speckit.analyze`. It does NOT implement code, does NOT ratify any ADR/approval (those are named-human seams per Constitution Principle V), and does NOT merge.

## Summary

Deliver one governed dashboard-intelligence journey that **composes and strengthens** shipped Seshat dashboard capabilities and adds the missing front end (Report Intent), report-level audit, deterministic preview, and — as later, sample-gated slices — a bounded blueprint→PBIR compiler and a PBIR-vs-design validator. The technical approach is **skill-driven** (ratified Option-B): new capabilities ship as skills, with small read-only pure library functions in `src/seshat/` only where byte-determinism must be guaranteed (preview renderer). Approvals reuse the shipped Decision Store; PBIR work reuses the four shipped adapters and their stage→validate→commit discipline. Nothing publishes to the Power BI Service.

## Technical Context

**Language/Version**: Python 3.13 (matches shipped `src/seshat/`; `pyproject.toml`)

**Primary Dependencies**: **stdlib only** for new code (`json`, `pathlib`, `html`, `base64`, `hashlib`, `yaml` via the already-vendored PyYAML the Decision Store uses). No new graphics/templating/PBIR libraries. Reuses shipped modules: `decision_store.py`, `decision_gate.py`, `pbir_theme_apply.py`, `pbir_visual_format.py`, `pbir_page_background.py`, `pbir_geometry.py`, `rules/*`.

**Storage**: Committed on-disk artifacts only — YAML templates under `templates/`, filled instances under `mappings/<subject-area>/design/…`, Decision Store `.seshat/*.yaml`, PBIR under `powerbi/<Report>.Report/`. No database (SEC-001). No live connection at any stage.

**Testing**: pytest with `unit` / `integration` markers (`pyproject.toml [tool.pytest.ini_options]`); TDD RED→GREEN. New static rules verified `<no-finding>` on `main` before wiring (memory: rule emits-on-main).

**Target Platform**: Cross-platform CLI + agent skills (Windows-first dev; POSIX CI). PBIR text must be UTF-8 without BOM, `core.autocrlf=true`, short paths (CLAUDE.md hard rules).

**Project Type**: Analytics tooling kit — Python library + `retail`/`seshat` CLI + Claude skills; Power BI PBIP/PBIR is the report target (gold-only reads).

**Performance Goals**: N/A as latency/throughput. The binding constraints are **determinism** (byte-identical preview/compiler output for identical inputs), **fail-closed correctness**, and **reversibility** — not speed.

**Constraints**: No live DB; no fabricated data (labeled placeholders only); no numeric readiness/design/confidence/quality score (FR-035); no self-grant of approval; no PBIR JSON guessing (verified samples only); no partial PBIR write; no Power BI Service publish/refresh/export/schedule; no broad readiness-spine or Decision Store refactor; no tenant logic in the generic core; not all visual types in the first compiler release.

**Scale/Scope**: 8 user stories across independently-useful slices. MVP = US1 + US2. Worked subject area = `retail_store_sales` (an example, not the schema — Principle VII). One report per subject area in MVP (path may widen later).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Gates derived from `.specify/memory/constitution.md` (v1.7.0):

| Principle | Gate | Status |
|---|---|---|
| I — Agent-First, Gate-Enforced | Enforcement lives in checkers, not prose; agent is never the pass-authority | **PASS** — new DL5 shape rule + reused DS/RS/R/CT rules carry enforcement; coordinator reads gate verdicts, never grants |
| II — Depend, Never Fork | Reuse external/shipped surfaces; Power BI execution stays external/deferred | **PASS** — reuses 4 PBIR adapters, Decision Store, interview machinery; F016 live-publish remains deferred; no fork |
| III — Medallion, Gold-Only | Power BI reads gold only | **PASS** — feature touches report/design layer only; no schema change |
| IV — Source Mapping Before Silver | N/A (report-side feature, upstream mapping assumed ready) | **N/A** |
| V — Agent Stops at Judgment Calls / No Self-Grant | Business judgments + approvals are named-human, recorded, never self-granted | **PASS** — intent approval, blueprint approval, and the new compiler ADR are explicit human seams; chain stops at analyze |
| VI — Defaults Then Deviations | Deviations need a cited data fact | **PASS** — every design decision in research.md cites an existing pattern; conflicts resolved to documented defaults |
| VII — Example, Not Schema | Worked example never becomes the generic schema | **PASS** — `retail_store_sales` exercises templates; nothing tenant-specific in core |
| VIII — Static-First, Live Deferred | Static `retail check` (WARN/suspect); live deferred | **PASS** — preview/audit/compiler all static/committed-artifact; live remains `retail validate`/F016 |
| IX — Secrets & Reproducibility | Secrets only in `.env`; no baked connection strings | **PASS** — SEC-004; PBIR uses parameters + relative refs (R1/R2) |
| Readiness System | `pass` carries evidence; no fabricated confidence number | **PASS** — FR-035; four-status vocab reused; audit is categorical, no score |

**Complexity Tracking**: no unjustified violations. The one net-new *authorization* surface (the PBIR-creation ADR, D11) is required precisely because the constitution/ADRs forbid the agent self-granting it — that is the constitution working as designed, not a violation.

## Project Structure

### Documentation (this feature)

```text
specs/123-governed-dashboard-intelligence/
├── plan.md              # This file
├── research.md          # Phase 0 — technical decisions D1–D13
├── data-model.md        # Phase 1 — entities, schema shapes, check→artifact map
├── quickstart.md        # Phase 1 — how to exercise the MVP journey
├── contracts/           # Phase 1 — report-intent stage contract + interview contract sketches
│   ├── report-intent-stage.md
│   └── report-intent-interview.md
├── checklists/
│   └── requirements.md  # from /speckit.specify
└── tasks.md             # Phase 2 — from /speckit.tasks
```

### Source Code (repository root) — anticipated touch points (NOT created by this plan)

```text
templates/
├── report-intent.yaml                    # NEW (US1) — the intent artifact template

contracts/
├── report/report-intent.yaml             # NEW (US1) — report_intent stage contract (mirrors dashboard-blueprint.yaml)
├── knowledge/approval-authority.yaml     # EDIT (US1) — add report_intent_approval: [report_owner]
└── interview/report-intent-interview.yaml# NEW (US1) — interview behavior contract (mirrors business-knowledge-interview.yaml)

src/seshat/
├── decision_store.py                     # EDIT (US1) — add report_intent_approval to CRITICAL_DECISION_TYPES
├── rules/report_intent.py                # NEW (US1) — DL5 shape rule (mirrors design_review_evidence.py / DL4)
├── rules/readiness_status.py             # EDIT (US6) — add report_owner to _AUTHORITY_CLASSES (FR-022a, one-class)
├── blueprint_preview.py                  # NEW (US4) — deterministic SVG renderer (pure, stdlib)
├── pbir_compile.py (+ submodules)        # NEW (US7, gated) — orchestration over the 4 adapters + create primitive
└── cli/…                                 # EDIT (US8 only) — read-only retail pbir-validate-blueprint verb

.claude/skills/
├── report-intent-interview/SKILL.md      # NEW (US1)
├── dashboard-intelligence/SKILL.md       # NEW (US2) — the coordinator skill
├── powerbi-dashboard-design/workflows/
│   ├── blueprint-preview.md              # NEW (US4)
│   ├── dashboard-semantic-audit.md       # NEW (US5)
│   └── visual-implementation-review.md   # EDIT (US8) — reconcile boundary text: human OR compiler build
└── dashboard-patterns/…                  # NEW (US3) — generic pattern library

docs/patterns/dashboard/                   # NEW (US3) — generic dashboard pattern docs (distinct from data-modeling docs/patterns/)
docs/decisions/00NN-pbir-creation-*.md     # NEW (US7) — DRAFTED here, RATIFIED by owner (human seam, not by this chain)
```

**Structure Decision**: Single-project layout (the shipped `src/seshat/` + `.claude/skills/` + `templates/` + `contracts/` structure). Every new capability is a skill; deterministic renderers are small read-only library modules under `src/seshat/`. This matches the shipped dashboard/planner/interview architecture exactly and keeps the generic core free of tenant logic (Principle VII).

## Phase 0 — complete

See `research.md` (D1–D13). All plan-time unknowns the spec deferred are resolved with cited grounding. No NEEDS CLARIFICATION remain.

## Phase 1 — complete

- `data-model.md`: Report Intent schema, Dashboard Pattern shape, Semantic Audit finding record + check→artifact map, PBIR-creation primitive contract, ID-minting rule.
- `contracts/`: report-intent stage contract + interview contract sketches (mirroring shipped precedents).
- `quickstart.md`: how to walk the MVP journey (US1→US2) on `retail_store_sales`.
- Agent context: `CLAUDE.md` SPECKIT pointer updated to this plan.

**Post-design Constitution re-check**: still PASS on all gates. No new violation introduced by the design; the PBIR-creation ADR remains the single human-seam gate (by design, not a shortcut).

## Explicit STOPs (human seams — NOT cleared by this chain)

1. **Spec ratification** — Principle V human seam; not cleared by planning.
2. **PBIR-creation ADR** (D11) — must be owner-ratified by name before any US7 creation writer is built.
3. **`report_intent_approval` / `dashboard_blueprint_approval`** — named-human approvals recorded in the Decision Store; the agent proposes and records, never self-grants.
4. **Owner-supplied PBIR reference samples** — increments 2/4/5 (and column/bar in 3) are BLOCKED until the owner supplies real Desktop-authored samples (D10).

## Delivery sequencing (feeds /speckit.tasks)

MVP (P1): US1 (Report Intent template + interview skill + decision type + DL5 rule) → US2 (coordinator skill). Then P2: US6 approval+versioning (incl. FR-022a RS1 one-class fix) → US4 preview → US5 audit → US3 patterns. Then P3 (sample-gated): US7 page-shell (unblocked) → US7 lineChart → [BLOCKED increments await samples] → US8 validator + boundary reconcile.
