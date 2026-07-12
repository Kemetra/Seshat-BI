# Phase 0 Research: Governed Dashboard Intelligence and PBIR Authoring

**Feature**: 123-governed-dashboard-intelligence
**Date**: 2026-07-12
**Method**: Read-only inspection of `main` (@ `0aca21d`) + grounding each open technical decision in an existing shipped pattern. Line numbers are from files as read on this date; re-verify before relying on them (hand-authored YAML/MD drifts).

This document resolves the technical unknowns the spec deferred to plan-time. Each decision is grounded in an existing repo pattern so the feature composes rather than replaces.

---

## Cross-cutting principle

**Determinism is the *product* for the preview and compiler; it is *inherited* for the audit and validator.** FR-015 (preview byte-identical) and FR-026 (compiler byte-identical) force pure functions with sorted inputs + fixed serialization. The audit/validator inherit determinism from the shipped tools they re-read (`dashboard-planner`, `dashboard-gaps`, CT1, the binding map, the implementation trace); their own job is evidence-citation + coherence reasoning, which is a **skill** responsibility, not a computed value.

**Delivery default (ratified Option-B):** new capabilities ship as **skills**, not new `retail` CLI verbs (`docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`, ratified 2026-07-07; reinforced by spec FR-011). A deterministic renderer/validator may have a small pure library function in `src/seshat/`, but the discovery/invocation surface is a skill. A read-only CLI verb is the deliberate, rare exception, used only where a scripting/CI need is stated (none is, for these).

---

## D1 — Report Intent artifact: location & format (US1)

- **Decision**: New template `templates/report-intent.yaml`; filled instance at `mappings/<subject-area>/design/report-intent.yaml` (sibling of the existing `dashboard-layout.md`, `visual-contract-binding-map.md`, `a11y-rtl-readiness-checklist.md`). Format **YAML** (machine-read by the coordinator, audit, and a new shape rule).
- **Rationale**: Every filled per-subject-area artifact follows "one blank under `templates/`, one filled instance under `mappings/<table>/…`" (ADR 0003 cohesive per-table working set). Report Intent is upstream of the design artifacts, so `design/` is the correct sibling. YAML (not Markdown) because it is structurally parsed for metric-name resolution (FR-003) and coordinator state inspection (FR-007).
- **Alternatives rejected**: new top-level dir (breaks the per-table convention); Markdown (needs fragile regex re-parse); embedding intent fields into the page blueprint (violates FR-002a/FR-038 single-owner).
- **Open (cheaply reversible)**: if a subject area supports multiple reports, path may widen to `…/design/<report_id>/report-intent.yaml`. MVP assumes one report per subject area.

## D2 — Report Intent field schema (US1)

- **Decision**: A YAML shape transcribing FR-002 fields verbatim, with metric references using the shipped `name` + `store_ref` + `status_required: pass` triple from `dashboard-page-blueprint.yaml` (no formula/DAX field, by design), the `"Name (class)"` owner shape (`decision_store.owner_shape_ok`), the four-status `readiness` block (no numeric score, FR-035), and an `open_questions` ambiguity ledger mirroring `metric-contract.yaml`'s `ambiguities:` block. `business_questions[]` carry stable `question_id`s so blueprint `business_question` can trace to one (FR-002a). Full shape in `data-model.md`.
- **Rationale**: Reusing established shapes keeps one reference convention across intent + blueprint and satisfies FR-003 the same way the page blueprint already does.
- **Alternatives rejected**: free-text metric blob; any numeric `confidence`/`fit_score` (FR-035); inlined DAX (FR-003 define/check boundary).

## D3 — Report Intent approval mechanism (US1/US6)

- **Decision**: Add a new critical decision type `report_intent_approval` to `CRITICAL_DECISION_TYPES` (`src/seshat/decision_store.py`), an eligibility row `report_intent_approval: [report_owner]` in `contracts/knowledge/approval-authority.yaml`, and wire it into `blocking_decision_categories` of the `report_intent` **and** `dashboard_blueprint` flow stages (so blueprint cannot proceed without approved intent — realizing FR-032 through the existing gate). Add a companion stage contract `contracts/report/report-intent.yaml` mirroring `contracts/report/dashboard-blueprint.yaml`.
- **Important scope correction**: This needs **no RS1 change**. `decision_store.py`'s `_ROLE_TOKENS` already includes `report_owner`, and `report_intent_approval` validity rides on `approval_is_valid()` (owner shape + authority map). The separate RS1 gap (FR-022a) is scoped only to `dashboard_blueprint`'s spine sign-off — do not conflate the two.
- **Rationale**: Directly operationalizes the spec's Conflict #1 default and mirrors the `dashboard_blueprint_approval` precedent. Cost is additive (one frozenset member + one eligibility row + two blocking-category entries), honoring FR-037.
- **Alternatives rejected**: reuse `kpi_definition` (FR-003 — intent must not define metric meaning; corrupts DS4 scope-conflict detection); reuse `pii_handling` (orthogonal, already inherited separately); no approval record (FR-005 needs a checkable `approval_is_valid` record).
- **Test-maintenance note (plan)**: adding a blocking category to `report_intent` requires a fixture update in `tests/unit/test_decision_gate.py` so existing downstream pass/warn assertions still hold.

## D4 — Report Intent interview (US1)

- **Decision**: A **new skill** `report-intent-interview` + contract `contracts/interview/report-intent-interview.yaml`, structurally **mirroring** (not extending) `business-knowledge-interview`.
- **Rationale**: The two interviews have mutually-exclusive `required_inputs` (discovery profile vs. approved contracts + ready model) and different `focus`, which the contract schema makes structurally distinct. Reused verbatim: load-existing-first, batch-low-risk / ask-critical-individually (`critical_types_forbidden`), PII mask-by-default (SEC-003), record-in-Decision-Store + STOP, never self-grant / never emit confidence. Mirrors how `dashboard-blueprint.yaml` was added as a new stage contract beside the interview contract.
- **Alternatives rejected**: extend the existing interview contract (contradictory per-stage `required_inputs`); a CLI verb (Option-B / FR-011); fold into the coordinator (coordinator sequences capabilities, it is not one).

## D5 — Report Intent well-formedness rule (US1)

- **Decision**: One new `DL`-series shape rule (e.g. `DL5`, confirm next free slot at build) mirroring **DL4** (`design_review_evidence.py`): scans `**/design/report-intent.yaml` filled instances (excluding templates + test paths), checks presence of FR-002 required fields (purpose in enum, ≥1 business question, valid owner shape, `readiness.status: pass` never with empty `evidence[]`). Presence-only, never content-judged, grants no approval. `<no-finding>` on `main` today (no instance exists yet), so it ships with the template.
- **Do NOT** add a static rule for FR-002a blueprint→intent traceability (that is US5's categorical audit, not a pass/fail gate) or for metric-name resolution (that is the coordinator's runtime state check, FR-003/FR-007).
- **Alternatives rejected**: no rule (every other filled artifact has a shape gate); one giant rule mixing shape + traceability + resolution (three verification layers, FR-038).

## D6 — Preview medium (US4)

- **Decision**: Deterministic **SVG** (HTML twin acceptable) generated by a **pure Python stdlib function** from committed blueprint/visual-spec/composition/grid YAML. Every value is structural (position/size/section/title/contract-name/question-text) or an explicit labeled `PLACEHOLDER`. Output at `mappings/<subject-area>/design/preview/<page_id>-preview.svg`. No live data, no PBIR, no DAX.
- **Rationale**: The repo already renders deterministic HTML with stdlib only (`src/seshat/demo/html_report.py`, imports `base64/html/pathlib`), so "least dependency" = stdlib-generated, not ASCII. SVG is text (diffable), renders as an actual image (satisfies FR-038 "visual representation"), and maps 1:1 onto `visual-spec.position` + `16x9-grid.yaml` coordinates. Determinism via `sorted(...)` inputs (SL1's pattern) + fixed serialization. Not F016 territory (not a Power BI artifact, imports nothing, creates no PBIR).
- **Alternatives rejected**: ASCII/markdown (not a *visual* representation per FR-038 — kept as fallback); data-free PBIR-shaped preview (PBIR is F016/US7 territory, would need a verified sample and collapse two differently-gated capabilities).

## D7 — Preview delivery (US4)

- **Decision**: Pure library function `src/seshat/blueprint_preview.py` (read-only, mirrors `dashboard_planner.py`/`gap_detector.py` as library modules) + a new skill/workflow (`workflows/blueprint-preview.md`) that invokes it and narrates the result. **No new CLI verb.**
- **Rationale**: Determinism (FR-015/SC-006) forces the pure-function half (an agent free-handing SVG cannot guarantee byte-identical output). Option-B forces the skill half for discovery/invocation. `dashboard_planner`/`gap_detector` are grandfathered pre-Option-B CLI verbs listed as *reused* capabilities, not a template for new verbs.
- **Alternatives rejected**: new CLI verb (Option-B/FR-011); skill-only (fails determinism); function-only (no discovery/routing).

## D8 — Dashboard Semantic Audit (US5)

- **Decision**: A **skill** (new workflow `workflows/dashboard-semantic-audit.md`) that reads and cites the *committed output* of already-shipped tools and emits the spec-fixed closed enum verbatim: `covered / incomplete / missing / conflicting / warning / blocked / not_applicable_with_reason`. Each finding is `{check, category, cited evidence path(s), named owner/correction}`. **No numeric score** (FR-020/FR-035). **Not** a `retail check` gate (it is non-gating decision support, like the gap-detector which "adds no `retail check` rule").
- **Rationale**: Borrow SL1/DL4's emission discipline (closed enum, no-percent regex, evidence-anchored locator, named owner) but not their gating delivery — the audit's checks require cross-artifact coherence *judgment* (does page X answer intent question Y?), which is a skill's job, not a static regex rule. FR-020 requires reusing tool *outputs*, not recomputing.
- **Check→artifact map**: in `data-model.md`. Each FR-018 check reads a specific committed artifact (intent questions vs blueprint `business_question`; `dashboard-planner` recorded verdict for page dup; filled `a11y-rtl-readiness-checklist.md` cited not re-derived; etc.).
- **Alternatives rejected**: a `retail check` rule (judgment ≠ regex; would silently make human calls, violating Principle V); CLI verb (Option-B); remap onto readiness's 4-status or SL1's 5-status enum (loses `conflicting`/`incomplete`; misuses owned vocabularies).

## D9 — PBIR compiler architecture (US7)

- **Decision**: A **new orchestration layer** `src/seshat/pbir_compile.py` (+ per-increment submodules), **not a fifth peer adapter**. It calls the four shipped adapters' public functions for theme/format/background/geometry, and adds exactly **one new primitive** the adapters structurally refuse: `create_page()` / `create_visual_container()`. Reuses their discipline verbatim (allow-list, stage→validate→commit-or-raise, byte-identical `json.dumps(sort_keys=True, indent=2)+"\n"`, refuse-overwrite-without-force, path-traversal guard, FR-003 query/visualType snapshot). Gets its own skill documenting the increment-gating table.
- **Rationale**: Spec Overview §A lists the adapters as "must not be replaced or re-implemented"; a second engine duplicates FR-003/allow-list logic. Isolating *creation* to one primitive matches the ADR-authorization boundary (D11).
- **Alternatives rejected**: monolith reimplementing formatting/geometry; extending an existing adapter file (ADR 0016 forbids creation in that scope); putting it in the static core (ADR 0015 decision 1 forbids the core writing PBIR).

## D10 — Staged increments vs reference-sample coverage (US7) — the key gating fact

Each increment needs a **verified Desktop-authored sample** before it can ship (FR-029; the shipped Increment-C "hold until real sample" precedent). Verified status today:

| # | Increment | Sample status | Verdict |
|---|---|---|---|
| 1 | Page shells | `powerbi/RetailStoreSales.Report/…/page.json` is a real Desktop save (Desktop-only fingerprints in `report.json`), zero visuals | **UNBLOCKED** — ships immediately |
| 2 | KPI cards | only self-invented `geometry.Report` `card` placeholder (schema 1.0.0, `Entity: placeholder`) | **BLOCKED** — owner sample required |
| 3 | Core bar/column/line | `lineChart` verified (data-goblin sample in `visual_fmt.Report`); `columnChart`/`bar` only placeholder | **PARTIAL** — lineChart ships; column/bar blocked |
| 4 | Slicers + navigation | no slicer/bookmark fixture anywhere | **BLOCKED** — owner sample required |
| 5 | Supported interactions | no interaction-wiring fixture | **BLOCKED** — owner sample required |
| 6 | Full validation (US8) | not sample-gated; needs increment 1+ shipped + the review-workflow reconciliation (D12) | not sample-blocked |

- **Rationale**: Increment C was held for exactly this reason and "the hold was vindicated — guessing would have produced the wrong structure." The `geometry.Report` placeholders were never held to this bar because increment D only needed *position* fields plausible; the compiler needs the *body*.
- **Alternatives rejected**: extrapolate card/bar from lineChart (C-precedent rejects adjacent-substitute); use placeholders as samples (not Desktop-authored); block increment 1 too (its real sample already exists).

## D11 — Authorization: new ADR required (US7)

- **Decision**: A **new ADR is required** before any *creation* writer ships, gating strictly at the creation primitive. Reuse of the four existing adapter calls stays under ADR 0015/0016. Creating a page/visual is explicitly outside both ADRs' scope and must be owner-ratified by name (Principle V).
- **Rationale**: ADR 0016 §2 explicitly excludes "create a visual, delete a visual, or add/remove a page — creation is authoring truth." Reading 0015/0016 as covering creation would be the agent self-granting authority. The new ADR must cover: which element types may be created per increment (docs-first, ships no writer); binding only to approved-binding-map fields; deterministic ID minting rules (D13); verified-sample-per-type requirement.
- **Alternatives rejected**: read 0015/0016 as already covering creation (they explicitly exclude it); treat `dashboard_blueprint_approval` as sufficient (that authorizes a blueprint's *content*, not the kit's *standing authority* to write PBIR structure).
- **This is a human ratify seam** — the plan/tasks may draft the ADR, but ratification is the named owner's action; the chain STOPS at analyze regardless.

## D12 — Validator: extend Visual Implementation Review (US8)

- **Decision**: Extend the existing `visual-implementation-review.md` workflow + `visual-implementation-trace.md` template (not a second reviewer). Add a blueprint-conformance dimension (pages/visuals/types/geometry/theme/background/nav/interactions per FR-030) beside the existing binding-map trace; keep the four-status vocabulary and "grants no approval." **Reconcile the boundary text**: the workflow currently asserts "the ONLY PBIR change is the human's Desktop save" — FR-030 requires validating compiler-**or**-human PBIR, so that sentence must be edited to name both paths (F016 remains the owner of the still-forbidden live publish). Delivered as a read-only CLI verb (`retail pbir-validate-blueprint`) alongside the manual workflow, the way `retail check` polices writers without writing.
- **Rationale**: FR-031 mandates reuse+extend, not a second reviewer. The existing workflow already owns the right evidence model. The boundary text becomes false once increment 1 ships and must be corrected, not left stale.
- **Alternatives rejected**: standalone new validator (FR-031); leave boundary text untouched (self-contradiction); fold into R1/R2 (those are structural lint, not blueprint-conformance comparison).
- **Note**: this is the one place a read-only CLI verb is proposed; justify against Option-B in the plan (R1/R2 precedent: the check surface is CLI, distinct from authoring skills).

## D13 — Determinism / no-partial-write / reversibility (US7)

- **Inherited from adapters** (sufficient for single-file edits): `json.dumps(sort_keys=True, indent=2)+"\n"` serialization; stage-in-memory → validate → write-only-after-all-checks; refuse-overwrite-without-force; `_within()` path guard; git-diff as the rollback mechanism (ADR 0016 §5).
- **Compiler must ADD**:
  1. **Multi-file atomicity** — even shipped Increment C writes 3 files sequentially with no rollback if file 3 fails. The compiler writes a page shell + N visuals + `pages.json` + maybe `report.json`. It must stage the complete tree (e.g. temp dir), validate the whole batch, then move into place only after all writes confirm — or document `git checkout -- <report-dir>` as the explicit recovery net (matching ADR 0016's git framing) rather than assuming inherited atomicity. Temp-dir approach adopted by increment 3/4 (many files/run).
  2. **Deterministic ID minting** — no shipped adapter mints IDs (they edit existing named entities). The compiler must invent page/visual `name` values derived deterministically from the blueprint's stable ids (e.g. truncated hash), never random/time-based (FR-027/US7#4 byte-determinism).
- **Alternatives rejected**: assume single-file pattern scales (partial-write surface multiplies); random UUIDs like Desktop (breaks determinism); full temp-dir transaction in increment 1 (over-engineered for a single-page write — sizing decision).

---

## Constitution alignment (informs the Constitution Check)

- **Principle I (agent-first, gate-enforced)**: new gate rule DL5 (shape) + reused DS/RS/R/CT rules carry enforcement; the agent is never the authority on pass.
- **Principle II (depend, never fork)**: reuses the four PBIR adapters + Decision Store + interview machinery; forks nothing. F016 remains the deferred external execution adapter (no live publish).
- **Principle V (agent stops at judgment calls / no self-grant)**: intent approval, blueprint approval, and the new compiler ADR are all named-human seams; the agent proposes, records, and STOPS.
- **Principle VII (C086/retail_store_sales is an example, not the schema)**: worked instances exercise the templates; nothing tenant-specific enters the generic core.
- **Readiness System (no fabricated confidence)**: no numeric readiness/design/confidence/quality score anywhere (FR-035).
