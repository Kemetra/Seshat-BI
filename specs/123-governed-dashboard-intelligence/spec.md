# Feature Specification: Governed Dashboard Intelligence and PBIR Authoring

**Feature Branch**: `123-governed-dashboard-intelligence`

**Created**: 2026-07-12

**Status**: Draft

**Input**: User description: "Governed Dashboard Intelligence and PBIR Authoring — one governed journey from a conversational report request through committed Report Intent, gap/duplication checks, pattern-assisted composition, page blueprints and visual specs, report composition, visual preview, dashboard semantic audit, named-human blueprint approval, optional bounded PBIR compilation, and PBIR-vs-design validation, stopping before publishing. Compose and strengthen existing dashboard capabilities; do not replace them."

---

## Overview

Seshat BI already ships strong, individually-governed dashboard-design components, but a user must manually connect them and can reach visual implementation without a clear, committed report purpose. This feature creates **one governed dashboard-intelligence journey** that composes the shipped components in the correct order, adds the missing "report purpose" front end and report-level audit, and — as later slices — adds a bounded blueprint-to-PBIR compiler and a PBIR-vs-design validator.

The feature is one product vision delivered as **independently useful slices**. Its MVP delivers a reviewable dashboard design (no preview, no PBIR). Later slices add preview, semantic audit, a pattern library, and staged PBIR compilation + validation. The journey always **stops before publishing to the Power BI Service**.

### Capability classification (shipped truth verified against `main` @ `0aca21d`)

Authoritative status was read from `docs/capabilities/capabilities.yaml` (`state:` field) and source paths, **not** from `spec.md` headers or `tasks.md` checkboxes, which are known-stale in this repo (specs 116/117/118/121 merged while still labeled `Draft` with unchecked tasks).

**A. Shipped capabilities this feature REUSES (must not be replaced or re-implemented):**

| Capability | Where it lives (evidence) | Role in this feature |
|---|---|---|
| Dashboard design (F011) | `.claude/skills/dashboard-design/SKILL.md`; capabilities.yaml `dashboard-design` | Authors layout plan + visual list + binding map from approved contracts; hard-gated on `semantic_model_ready: pass` |
| Visual-foundation router (F011A) | `.claude/skills/powerbi-dashboard-design/SKILL.md` | Routes design requests into the four visual surfaces (visuals / background / theme / implementation review) |
| Page-blueprint / visual-spec / report-composition templates | `templates/dashboard-page-blueprint.yaml`, `templates/visual-spec.yaml`, `templates/report-composition.yaml` | Structural design artifacts (page intent, per-visual intent, page order + navigation + cross-page filters) |
| Metric contracts (F009) | `templates/metric-contract.yaml` | Own metric meaning; upstream gate |
| Dashboard planner — new/extend/duplicate (spec 116) | `retail dashboard-planner`; `src/seshat/cli/commands/dashboard_planner.py`; `docs/tools/dashboard-planner.md` | Deterministic categorical classification of a dashboard proposal |
| Dashboard gap detector (spec 117) | `retail dashboard-gaps`; `src/seshat/cli/commands/gap_detector.py`; `docs/tools/dashboard-gap-detector.md` | Pre-design categorical inventory of covered/blocked/planned requirements |
| Visual QA anti-pattern catalog + screenshot review | `docs/powerbi/visual-qa.md`, `.claude/skills/powerbi-dashboard-design/workflows/dashboard-qa.md`, `workflows/screenshot-review.md` | Per-visual / per-page anti-pattern QA (test-enforced parity) |
| Accessibility / RTL evidence | `templates/a11y-rtl-readiness-checklist.md`; `mappings/retail_store_sales/design/a11y-rtl-readiness-checklist.md`; rule `CT1` (`src/seshat/rules/design_contrast.py`) | Contrast / colorblind / RTL review evidence |
| Mobile guidance | `.claude/skills/powerbi-dashboard-design/workflows/mobile-layout.md`; `design/grids/mobile-grid.yaml` | Mobile reflow design guidance |
| Design tokens / themes / grids / backgrounds | `design/tokens/*`, `design/grids/*`, `design/backgrounds/*`, `themes/README.md`; `retail theme-gen` / `theme-compile` | Design-system inputs |
| Driver / decomposition + narrative fields | `templates/driver-decomposition.md` (spec 087); `narrative:` block in `dashboard-page-blueprint.yaml`; driver visual types in `visual-spec.yaml` | Design-intent (define-only) fields |
| Visual-to-contract binding map | `templates/visual-contract-binding-map.md`; filled `mappings/retail_store_sales/design/visual-contract-binding-map.md` | The human design-review sign-off artifact |
| Visual Implementation Review (F034) | `.claude/skills/powerbi-dashboard-design/workflows/visual-implementation-review.md`; `templates/visual-implementation-trace.md` | Read-only trace of a built page against the approved binding map |
| PBIR authoring adapters A/B/C/D (spec 106) | `retail pbir-apply-theme` / `pbir-format-visual` / `pbir-set-page-background` / `pbir-set-geometry`; `src/seshat/pbir_*.py`; ADRs 0015/0016 | Bounded, allow-listed operations that restyle/reposition **human-authored** visuals |
| PBIR validation rules | `src/seshat/rules/pbir.py` (R1 relative model ref, R2 report-json authoring-lint) | Structural / allow-list policing of PBIR |
| Decision Store + approval model (spec 121) | `src/seshat/decision_store.py`, `decision_gate.py`, `rules/decision_store.py` (DS1–DS5); `contracts/knowledge/approval-authority.yaml` | Records approvals; enforces named-human authority, no self-grant, supersession (DS4) |
| Business-knowledge interview (spec 121) | `.claude/skills/business-knowledge-interview/SKILL.md`; `contracts/interview/business-knowledge-interview.yaml` | The reusable interview → Decision Store pattern |
| Capability inventory (spec 118) | `docs/capabilities/capabilities.yaml`; `src/seshat/capability_inventory.py`; `.claude/skills/capabilities/SKILL.md` | Read-only "what can the kit do" surface |
| Evidence pack composer | `src/seshat/evidence_pack.py`; `src/seshat/cli/commands/evidence_pack.py` | Read-only pre-publish evidence composer |
| Dashboard-blueprint gate contract | `contracts/report/dashboard-blueprint.yaml`; flow stages in `contracts/knowledge/database-to-pbip-flow.yaml` | Declares the `dashboard_blueprint` stage + `dashboard_blueprint_approval` decision |

**B. Existing capabilities this feature STRENGTHENS or COORDINATES (no parallel replacement):**

- **Report composition** and **driver-decomposition** templates are shipped but have **no filled worked instance** on the one real subject area (`retail_store_sales`). This feature exercises them end-to-end.
- **Chart-selection-by-question-and-grain** exists only as a one-sentence heuristic inside `dashboard-design/SKILL.md` (step 3). This feature may strengthen it into reusable pattern guidance (US3) without replacing the design skill.
- **Dashboard patterns**: only four fixed starter blueprints exist under `reports/blueprints/` (executive-summary, branch-performance, product-mix, data-quality-control-room). This feature adds a generic, named, extensible pattern **library** (US3) that adapts to committed Report Intent — it does not fork the design skill and does not define KPI meaning.
- **Coordination**: the shipped skills run individually today. This feature adds an agent-/skill-driven **coordinator** (US2) that sequences them, inspects committed state, chooses one next allowed action, and fails closed — without introducing a broad new CLI family.

**C. Genuinely NEW capabilities (absent on `main`):**

- **Report Intent artifact + interview** (US1). Today `report_intent` exists **only** as a routing-taxonomy label in `contracts/knowledge/database-to-pbip-flow.yaml` (lines 126–136) — **no template, no skill, no dedicated `decision_type`, no contract file**. The intent *interview* reuses the shipped business-knowledge-interview + Decision Store pattern; the *artifact* and its own approval record are new.
- **Dashboard coordinator** (US2) — a state-driven sequencer over the shipped capabilities.
- **Deterministic blueprint preview** (US4) — nothing in the repo renders design intent; the shipped architecture deliberately separates *author* (text/YAML) from *execute* (the deferred F016 adapter). A no-live-data preview is new.
- **Dashboard Semantic Audit** (US5) — a report-level coherence audit distinct from the shipped per-visual anti-pattern QA; absent today.
- **Blueprint-to-PBIR compiler** (US7) — the shipped PBIR adapters restyle/reposition **already-authored** visuals; **none creates a page or visual from a blueprint**. Compilation-from-approved-blueprint is new.
- **PBIR-vs-approved-design validator** (US8) — an extension of the shipped Visual Implementation Review that verifies committed PBIR conforms to the **approved blueprint** (not just structural allow-list policing).

---

## Clarifications

### Session 2026-07-12

- Q: How should the `report_owner` authority class be reconciled between `approval-authority.yaml` (requires it for `dashboard_blueprint_approval`) and RS1's shipped `_AUTHORITY_CLASSES` (which excludes it)? → A: Extend RS1 to recognize `report_owner` — a **one-class, additive** change, explicitly NOT a broad readiness-spine refactor (reconciles with FR-037), since every contract layer already requires it.
- Q: What is the ownership relationship between the new Report Intent artifact and the existing inline `business_question` field on page blueprints? → A: Report Intent is the upstream owner of report purpose and primary business questions; a page blueprint's `business_question` is retained but MUST trace to a question declared in the committed Report Intent (no duplicate truth, per FR-038) — blueprints reference intent questions rather than independently re-declaring them.

## User Scenarios & Testing *(mandatory)*

Actors: business owner, BI analyst/developer, metric owner, BI report owner, Power BI reviewer, agent operator, dashboard consumer (executive, branch manager, operations manager, analyst).

### User Story 1 - Capture Report Intent (Priority: P1 — MVP)

A user describes the report they need in plain language. The system conducts a focused interview and produces a committed, reviewable **Report Intent** artifact that records what the report is for — never inventing metric meaning.

**Why this priority**: Report purpose is the missing front end. Every downstream artifact (blueprint, composition, audit, PBIR) depends on a clear, committed intent. Without it, users reach visual implementation with an unclear purpose. It reuses the shipped `business-knowledge-interview` + Decision Store pattern, so it is achievable as the first slice and delivers standalone value (a reviewable intent even if nothing downstream runs).

**Independent Test**: Run the intent interview from a conversational request against a subject area that already has approved metric contracts; confirm a committed, machine-readable Report Intent artifact is produced capturing audience, purpose, decision, questions, outcome/driver/guardrail metrics, comparisons, dimensions/filters, expected actions/exceptions, pages/drill paths, and mobile/accessibility/language/RTL needs, with every referenced metric resolving to an approved contract. Deliver value independently: the artifact is reviewable on its own.

**Acceptance Scenarios**:

1. **Given** a subject area with approved metric contracts and a ready semantic model, **When** the user says "I need a weekly report for branch managers to spot underperforming branches," **Then** the system interviews for the missing fields and records a Report Intent artifact capturing (where applicable) audience, purpose category (executive / monitoring / diagnostic / action-oriented / analytical exploration), supported decision, review cadence, primary business questions, outcome/driver/guardrail metrics, comparisons, dimensions and filters, expected actions and exceptions, required pages and drill paths, mobile/accessibility/language/RTL needs, and exclusions/non-goals.
2. **Given** the interview references a metric that has **no** approved metric contract, **When** intent is being recorded, **Then** the system records a gap that routes upstream to metric-contract definition and does **not** define the metric itself; the intent remains blocked on that metric.
3. **Given** the agent proposes intent options (audience, purpose, question phrasing), **When** any business judgment is required, **Then** the agent records it as a proposal and a **named human** owns the decision — the agent never self-grants intent approval.
4. **Given** a vague request ("build an executive dashboard"), **When** the interview runs, **Then** the system asks focused disambiguating questions and refuses to produce a committed intent until audience, purpose, and at least one primary business question are resolved.

---

### User Story 2 - Coordinate Existing Dashboard Capabilities (Priority: P1 — MVP)

Given an approved Report Intent, approved metric contracts, and a ready semantic model, the system coordinates the **shipped** dashboard capabilities in the correct order to produce a reviewable dashboard design — reusing `retail dashboard-gaps`, `retail dashboard-planner`, `dashboard-design`, the blueprint/visual-spec/composition templates, visual-to-contract binding, dashboard QA, and the human blueprint review; then handing off to implementation.

**Why this priority**: This is the "one governed journey" the feature exists to create. It turns a set of individually-usable skills into a coherent, fail-closed sequence. It is P1/MVP because the reviewable dashboard design is the MVP deliverable.

**Independent Test**: Provide a **hand-authored** approved Report Intent fixture (so this story is testable without running US1), approved metric contracts, and a ready semantic model; run the coordinator; confirm it (a) inspects committed state, (b) selects exactly one next allowed action, (c) invokes the shipped capability responsible for that action, (d) re-evaluates state, and (e) stops with a named blocker on the first unmet precondition — without bypassing `semantic_model_ready: pass` or self-granting `dashboard_ready: pass`.

**Acceptance Scenarios**:

1. **Given** approved intent + contracts + ready model, **When** the coordinator runs, **Then** it inspects committed state, identifies one next allowed action, invokes the responsible shipped capability (e.g. `retail dashboard-gaps` before `dashboard-design`), re-evaluates, and repeats — producing page blueprints, visual specs, and a report composition, each visual traceable to an approved contract and mapped field.
2. **Given** `semantic_model_ready` is not `pass`, **When** the coordinator runs, **Then** it stops with a blocked result naming the missing semantic-model readiness and does **not** proceed to design.
3. **Given** a required metric has no approved contract, **When** the coordinator reaches the gap check, **Then** it stops with a blocked result naming the missing contract and the responsible owner, and routes upstream.
4. **Given** all design artifacts are authored but the blueprint has no valid approval, **When** the coordinator reaches the readiness gate, **Then** it does **not** self-grant `dashboard_ready: pass`; it stops at the human blueprint review seam.
5. **Given** a proposed page, **When** the coordinator classifies it, **Then** it uses `retail dashboard-planner` to obtain a deterministic `new` / `extends <page>` / `duplicate of <page>` verdict (no score) and acts accordingly (e.g. surfaces a duplicate for human decision).

---

### User Story 3 - Use Dashboard Patterns Safely (Priority: P2)

Based on the approved Report Intent, the system may recommend a reusable, generic dashboard **pattern** (design guidance only). Initial families may include Executive Performance, Sales Diagnosis, Branch Performance, Inventory Health, Product Performance, Promotion Effectiveness, Returns and Refunds, Customer Behavior, Data Quality Control Room, Action and Exceptions.

**Why this priority**: Patterns accelerate composition and encode good structure, but they are guidance and must never define KPI meaning or fabricate metrics. The MVP does not require them, so P2.

**Independent Test**: Given an approved intent whose purpose is "diagnostic," confirm the system proposes a matching pattern (e.g. Sales Diagnosis), that the pattern provides only generic guidance (suitable audiences, intended purpose, common question families, outcome/driver/guardrail roles, common page structure, recommended visual roles, expected action paths, common design risks), and that the human may accept, adapt, or reject it. Confirm a requirement the pattern assumes but the subject area cannot satisfy is surfaced as a gap, not fabricated.

**Acceptance Scenarios**:

1. **Given** an approved intent, **When** a pattern is recommended, **Then** it is generic (no KPI meaning, no tenant-specific business logic), adapts to the committed intent, and lists suitable audiences, purpose, question families, metric roles, page structure, visual roles, action paths, and design risks.
2. **Given** a pattern assumes a metric or dimension the subject area lacks, **When** the pattern is applied, **Then** the unavailable requirement is surfaced as a gap (reusing `retail dashboard-gaps`), never fabricated.
3. **Given** two suitable patterns match the intent, **When** recommending, **Then** the system presents the candidates for human choice and does not silently pick one; if a pattern only partially fits, the misfitting parts are flagged for human adaptation.

---

### User Story 4 - Preview the Dashboard Blueprint (Priority: P2)

Given approved design artifacts, the system produces a **deterministic** visual preview before any PBIR implementation, so reviewers can see the design.

**Why this priority**: Preview improves review quality but is not required to produce a reviewable design (the artifacts themselves are reviewable). Post-MVP.

**Independent Test**: From a set of approved design artifacts, generate a preview; confirm it represents pages/order, sections, visual positions/sizes/types, titles + business questions, referenced metric contracts, filters/slicers, narrative regions, navigation, freshness/DQ areas, and theme/typography/grid/accessibility/mobile/RTL intent; confirm it uses no live database, contains no fabricated business result, creates no DAX/semantic model/PBIR, clearly marks placeholders vs real data, and is reviewable across revisions.

**Acceptance Scenarios**:

1. **Given** approved design artifacts, **When** a preview is generated, **Then** it deterministically represents the listed structural and design-intent elements with placeholders clearly distinguished from any real data.
2. **Given** a request for "realistic preview values," **When** no approved data source exists for those values, **Then** the preview shows labeled placeholders and refuses to fabricate business results.
3. **Given** the same approved artifacts, **When** the preview is regenerated, **Then** the output is deterministic (identical inputs → identical preview) and diffable across revisions.

---

### User Story 5 - Audit the Report Against Its Intent (Priority: P2)

The system performs a **Dashboard Semantic Audit** over the whole report as a decision-support product — distinct from the shipped per-visual anti-pattern QA. It emits categorical findings only (no score).

**Why this priority**: Report-level coherence catches gaps that per-visual QA cannot (e.g. an intent question no page answers). Valuable but not MVP-blocking; P2.

**Independent Test**: Given an approved intent and a composed report, run the audit; confirm it emits categorical findings (`covered`, `incomplete`, `missing`, `conflicting`, `warning`, `blocked`, `not_applicable_with_reason`) for each of: every intent question covered; each page has one coherent purpose; primary outcomes visible; diagnostic reports include drivers; guardrails/comparisons represented; action/exception paths exist; pages don't duplicate; composition matches declared purpose; navigation/drill coherent; cross-page filters consistent; narrative claims supported by referenced contracts + visuals; accessibility/mobile/RTL/freshness addressed — each finding citing committed evidence and naming the responsible correction or owner. Confirm **no numeric score** is produced.

**Acceptance Scenarios**:

1. **Given** an intent question that no page answers, **When** the audit runs, **Then** it emits `missing` for that question, cites the intent + composition evidence, and names the owner/correction.
2. **Given** a diagnostic-purpose report with no driver metrics represented, **When** the audit runs, **Then** it emits `incomplete` (or `missing`) for drivers with cited evidence.
3. **Given** monitoring intent mixed with diagnostic intent on one page, **When** the audit runs, **Then** it emits `conflicting` and names the coherence problem.
4. **Given** the audit runs, **When** producing findings, **Then** it reuses the shipped dashboard QA, planner, gap detector, accessibility evidence, binding maps, and implementation traces rather than recomputing their checks, and produces **no** numeric score or ranking.

---

### User Story 6 - Approve and Version the Blueprint (Priority: P2)

Before any PBIR compilation, an eligible **named human** reviews the intent, page blueprints, visual specs, report composition, preview, semantic-audit findings, and unresolved warnings, then approves, rejects, or requests revision — recorded in the shipped Decision Store via the existing `dashboard_blueprint_approval` decision.

**Why this priority**: Approval is the hard human seam that gates compilation. It is P2 because the MVP stops at *human review* (US2); this story formalizes recording that approval and its versioning for the compilation slices.

**Independent Test**: With design artifacts + preview + audit findings present, record an approval decision using the shipped Decision Store; confirm the approval is valid only when authored by a named human of the eligible authority class per `contracts/knowledge/approval-authority.yaml`; confirm an agent identity can never satisfy it (no self-grant); confirm that changing an approved blueprint marks the prior decision superseded (preserving history via DS4) and requires renewed approval before compilation.

**Acceptance Scenarios**:

1. **Given** the review bundle, **When** an eligible named human approves, **Then** a `dashboard_blueprint_approval` decision is recorded via the shipped Decision Store and passes the shared `approval_is_valid` predicate.
2. **Given** an agent attempts to approve, **When** the decision is checked, **Then** it is rejected (an agent identity never satisfies `approved_by`).
3. **Given** an approved blueprint is later changed, **When** the change is committed, **Then** the prior approval is marked `superseded` (with `superseded_by` referencing the new record per DS4), history is preserved, and compilation is blocked until renewed approval.
4. **Given** an approved blueprint has **not** changed, **When** re-reviewed, **Then** the existing approval remains valid (no forced re-approval).

---

### User Story 7 - Compile an Approved Blueprint into PBIR (Priority: P3 — Post-MVP)

Given a ready semantic model, approved contracts, mapped fields, an approved blueprint, and verified PBIR reference samples, the system may compile **supported** dashboard elements into committed PBIR — bounded, allow-listed, deterministic, reversible, and validated before preserving changes.

**Why this priority**: Compilation is the most technically constrained slice and depends on all upstream approval. It must be broken into independent increments. Post-MVP (P3).

**Independent Test** (per increment): Given an approved blueprint and a verified reference sample for the target element (e.g. a page shell), run the compiler for that increment only; confirm it writes committed PBIR for that element, never guesses PBIR JSON, never creates unsupported/unapproved visuals, never binds unmapped fields, never touches DAX/semantic model, leaves no partial write on failure, and does not publish. Confirm a rerun on identical inputs is byte-deterministic.

Independent delivery increments (each its own slice): (1) page shells; (2) KPI cards; (3) core bar/column/line charts; (4) slicers and navigation; (5) supported interactions; (6) full blueprint-to-PBIR validation (US8 close-out).

**Acceptance Scenarios**:

1. **Given** an approved blueprint + a verified reference sample for a supported element, **When** the compiler runs that increment, **Then** it emits committed, Git-reviewable PBIR grounded in the real sample, reversible, and validated before the change is preserved.
2. **Given** the blueprint requests a visual type with **no** verified reference sample, **When** compilation is attempted, **Then** it stops with a blocked result naming the missing sample and writes nothing.
3. **Given** the compiler encounters an unsupported structure mid-run, **When** it fails, **Then** no partial PBIR survives (all-or-nothing per element) and the failure names the unsupported structure.
4. **Given** the same approved blueprint + samples, **When** the compiler is rerun, **Then** the output is deterministic (identical inputs → identical PBIR).
5. **Given** no valid `dashboard_blueprint_approval`, **When** compilation is attempted, **Then** it is blocked, naming the missing/invalid approval.

---

### User Story 8 - Validate PBIR Against the Approved Design (Priority: P3)

After a compiler run **or** a human Power BI Desktop build, the system verifies that committed PBIR matches the approved design — extending the shipped Visual Implementation Review. It records evidence and deviations but grants no approval.

**Why this priority**: Validation closes the loop and is the only way to prove conformity, but it depends on committed PBIR existing. P3.

**Independent Test**: Given committed PBIR (compiler- or human-produced) and an approved blueprint, run the validator; confirm it reports expected vs actual for pages, visuals, visual types, contract bindings, semantic fields, titles/formats, geometry, theme/background, navigation, statically-inspectable interactions, relative model references, and the implementation trace — flagging unapproved additions and missing elements — while granting no approval.

**Acceptance Scenarios**:

1. **Given** committed PBIR + approved blueprint, **When** the validator runs, **Then** it reports conformity per checked dimension and cites the implementation trace, extending (not duplicating) the shipped Visual Implementation Review.
2. **Given** a manually-added visual with no approved contract, **When** the validator runs, **Then** it flags the unapproved addition and does not pass it.
3. **Given** the compiler wrote PBIR but the preview and PBIR diverge, **When** the validator runs, **Then** it flags the divergence with cited evidence.
4. **Given** the validator finishes, **When** results are recorded, **Then** it records evidence/deviations only and grants **no** approval (no self-grant of `dashboard_ready: pass`).

---

### Edge Cases

- **Vague request** ("build an executive dashboard"): interview refuses to commit intent until audience, purpose, and ≥1 primary question are resolved (US1 #4).
- **Incompatible audiences** in one intent: surfaced as a `conflicting` audit finding / intent-review question; human resolves.
- **Multiple unrelated questions on one page**: audit emits `conflicting` (page lacks one coherent purpose).
- **Monitoring intent mixed with diagnostic intent**: audit emits `conflicting`; pattern recommendation flags partial fit.
- **Missing or unapproved metric contracts**: gap recorded, routed upstream; never invented (US1 #2, US2 #3).
- **Unavailable dimensions**: gap detector marks `Blocked — missing field`; design blocked for the affected visual.
- **Multiple suitable dashboard patterns**: presented for human choice, none auto-selected (US3 #3).
- **Partial pattern fit**: misfitting parts flagged for human adaptation.
- **Duplicate or extending proposals**: `retail dashboard-planner` returns `duplicate of <page>` / `extends <page>`; surfaced for human decision.
- **Multiple fact grains**: intent/composition must resolve which grain each page/visual uses; ambiguity surfaced, not guessed.
- **Missing drivers or guardrails**: audit emits `incomplete`/`missing` for diagnostic reports lacking drivers or reports lacking guardrails/comparisons.
- **Changed contracts or renamed fields after approval**: prior approval becomes stale; renewed approval required before compilation; validator flags binding drift.
- **Changed blueprint after approval**: prior approval superseded (DS4), renewed approval required (US6 #3).
- **Unavailable PBIR reference samples**: compilation blocked, naming the missing sample; nothing written (US7 #2) — mirrors the shipped Increment-C "hold until real sample" precedent.
- **Unsupported visual types**: compiler refuses; validator flags as out of the supported allow-list.
- **Preview and PBIR divergence**: validator flags with cited evidence (US8 #3).
- **Partial compiler failure**: all-or-nothing per element; no partial PBIR survives (US7 #3).
- **Non-deterministic compiler reruns**: forbidden; identical inputs must yield identical PBIR (US7 #4).
- **Manually added unapproved visuals**: validator flags as unapproved addition (US8 #2).
- **Missing action paths / orphan navigation**: audit emits `missing`/`incomplete`; navigation coherence checked.
- **RTL/LTR conflicts, mobile/desktop conflicts**: surfaced via accessibility/RTL + mobile evidence; audit reports if unaddressed.
- **Requests for realistic preview values without approved data**: labeled placeholders only; no fabrication (US4 #2).
- **Requests to publish immediately after compilation**: refused — the journey stops before Power BI Service publishing (the deferred F016 boundary).

---

## Requirements *(mandatory)*

### Functional Requirements — Report Intent (US1)

- **FR-001**: The system MUST conduct a focused interview from a conversational report request and produce a committed, machine-readable, reviewable **Report Intent** artifact.
- **FR-002**: The Report Intent MUST capture, where applicable: audience; report purpose (executive / monitoring / diagnostic / action-oriented / analytical exploration); supported decision; review cadence; primary business questions; primary outcome metrics; driver metrics; guardrail metrics; comparisons; dimensions and filters; expected actions and exceptions; required pages and drill paths; mobile / accessibility / language / RTL needs; exclusions and non-goals.
- **FR-002a**: The Report Intent is the upstream owner of report purpose and primary business questions. A page blueprint's existing inline `business_question` field is retained but MUST trace to a question declared in the committed Report Intent; blueprints reference intent questions rather than independently re-declaring them (no duplicate truth, per FR-038). A blueprint `business_question` with no matching intent question MUST be surfaced as a coherence finding by the semantic audit (US5).
- **FR-003**: Every metric referenced in a Report Intent MUST resolve to an **approved** metric contract; the system MUST NOT define metric meaning.
- **FR-004**: When a required metric has no approved contract, the system MUST record a gap that routes upstream to metric-contract definition and leave the intent blocked on that metric.
- **FR-005**: The intent interview MUST reuse the shipped business-knowledge-interview + Decision Store pattern (load existing decisions first, never overwrite; batch low-risk items; ask critical items individually; mask PII by default); a **named human** MUST own all business judgments and the agent MUST NOT self-grant intent approval.

### Functional Requirements — Coordination (US2)

- **FR-006**: The system MUST provide an agent-/skill-driven coordinator that, given approved intent + approved contracts + a ready semantic model, sequences the shipped dashboard capabilities in the correct order.
- **FR-007**: The coordinator MUST, on each step, inspect committed state, identify exactly one next allowed action, invoke the **existing** capability responsible for that action, then re-evaluate state.
- **FR-008**: The coordinator MUST reuse (not replace): `retail dashboard-gaps` (gap detection), `retail dashboard-planner` (new/extend/duplicate classification), the page-blueprint / visual-spec / report-composition templates, visual-to-contract binding, dashboard QA, and the human blueprint review; then hand off to implementation.
- **FR-009**: The coordinator MUST stop with a named blocker on: unresolved intent, missing/unapproved contracts, missing required fields, a visual with no approved contract, or missing/invalid blueprint approval.
- **FR-010**: The coordinator MUST NOT bypass `semantic_model_ready: pass` and MUST NOT self-grant `dashboard_ready: pass`.
- **FR-011**: The coordinator MUST NOT introduce a broad new CLI family merely to wrap existing skills (it composes existing capabilities).

### Functional Requirements — Patterns (US3)

- **FR-012**: The system MAY recommend a reusable, generic dashboard pattern based on the approved Report Intent; a pattern MUST provide only design guidance (suitable audiences, intended purpose, common question families, outcome/driver/guardrail roles, common page structure, recommended visual roles, expected action paths, common design risks).
- **FR-013**: Patterns MUST remain generic (no KPI meaning, no tenant-specific business logic), MUST NOT fabricate missing metrics, MUST adapt to the committed Report Intent, MUST surface unavailable requirements as gaps, and MUST allow human acceptance / adaptation / rejection.
- **FR-014**: When multiple patterns fit, the system MUST present candidates for human choice; when a pattern only partially fits, misfitting parts MUST be flagged for human adaptation.

### Functional Requirements — Preview (US4)

- **FR-015**: Given approved design artifacts, the system MUST produce a **deterministic** visual preview (identical inputs → identical output) representing pages/order, sections, visual positions/sizes/types, titles + business questions, referenced metric contracts, filters/slicers, narrative regions, navigation, freshness/DQ areas, and theme/typography/grid/accessibility/mobile/RTL intent.
- **FR-016**: The preview MUST use no live database, contain no fabricated business result, create no DAX/semantic model/PBIR, clearly distinguish placeholders from real data, and be reviewable across revisions.

### Functional Requirements — Semantic Audit (US5)

- **FR-017**: The system MUST perform a report-level Dashboard Semantic Audit distinct from the per-visual anti-pattern QA, emitting only categorical findings from the closed set: `covered`, `incomplete`, `missing`, `conflicting`, `warning`, `blocked`, `not_applicable_with_reason`.
- **FR-018**: The audit MUST determine (categorically): every intent question covered; each page has one coherent purpose; primary outcomes visible; diagnostic reports include drivers; guardrails/comparisons represented; action/exception paths exist; pages don't duplicate; composition matches declared purpose; navigation/drill coherent; cross-page filters consistent; narrative claims supported by referenced contracts + visuals; accessibility/mobile/RTL/freshness addressed.
- **FR-019**: Every audit finding MUST cite committed evidence and name the responsible correction or owner decision.
- **FR-020**: The audit MUST reuse the shipped dashboard QA, planner, gap detector, accessibility evidence, binding maps, and implementation traces rather than recomputing their checks, and MUST NOT produce any numeric score or ranking.

### Functional Requirements — Approval & Versioning (US6)

- **FR-021**: Blueprint approval MUST be recorded via the shipped Decision Store using the existing `dashboard_blueprint_approval` decision; the system MUST NOT create a second approval system.
- **FR-022**: An approval MUST be valid only when authored by a named human of the eligible authority class per `contracts/knowledge/approval-authority.yaml`; an agent identity MUST never satisfy `approved_by` (no self-grant), enforced via the shared `approval_is_valid` predicate.
- **FR-022a**: The readiness-status consistency rule RS1 MUST recognize `report_owner` as an eligible authority class so that a valid `dashboard_blueprint_approval` (which requires `report_owner`) is accepted consistently across the flow gate and the readiness spine. This is a **single-class, additive** reconciliation of an existing gap — it does NOT constitute a broad readiness-spine refactor (see FR-037).
- **FR-023**: An approved blueprint MUST NOT be silently mutated; a post-approval change MUST mark the prior approval `superseded` (with `superseded_by` per DS4), preserve history, and require renewed approval before compilation.
- **FR-024**: An unchanged approved blueprint MUST NOT require forced re-approval.

### Functional Requirements — PBIR Compilation (US7)

- **FR-025**: The compiler MAY run only when a ready semantic model, approved contracts, mapped fields, an approved blueprint, **and** verified PBIR reference samples are all present.
- **FR-026**: Compilation MUST be incremental, allow-list constrained, deterministic, Git-reviewable, reversible, validated before changes are preserved, and grounded in real Power BI Desktop-authored samples.
- **FR-027**: The compiler MUST NOT guess PBIR JSON, create unsupported visuals, add unapproved visuals, bind unmapped fields, redefine a metric, modify DAX or the semantic model, leave partial writes after failure, or publish to the Power BI Service.
- **FR-028**: Compilation MUST be delivered as independent product increments: (1) page shells; (2) KPI cards; (3) core bar/column/line charts; (4) slicers and navigation; (5) supported interactions; (6) full blueprint-to-PBIR validation.
- **FR-029**: A requested PBIR shape with no verified reference sample MUST block compilation, naming the missing sample, writing nothing.

### Functional Requirements — PBIR Validation (US8)

- **FR-030**: The system MUST verify committed PBIR (compiler- or human-produced) against the approved design, reporting expected vs actual for: pages, visuals, visual types, contract bindings, semantic fields, titles/formats, geometry, theme/background, navigation, statically-inspectable interactions, relative model references, and the implementation trace; flagging unapproved additions and missing elements.
- **FR-031**: PBIR validation MUST reuse and extend the shipped Visual Implementation Review rather than creating a second reviewer, and MUST record evidence/deviations only — granting no approval.

### Functional Requirements — Governance, Fail-Closed & Boundaries (cross-cutting)

- **FR-032**: The feature MUST preserve the existing report-side flow order: `report_intent → dashboard_blueprint → pbip_prototype_readiness → evidence_pack`.
- **FR-033**: The feature MUST fail closed (produce a `blocked` result, never `pass`) when: Report Intent is unresolved; approved contracts are missing; the semantic model is not ready; required fields are unavailable; a visual has no approved contract; blueprint approval is missing or invalid; an approved blueprint is stale; a requested PBIR shape has no verified sample; compilation encounters an unsupported structure; or validation cannot prove conformity.
- **FR-034**: Every blocked result MUST name: what is missing/invalid; the evidence checked; the responsible owner; and the action that would unblock progress.
- **FR-035**: The feature MUST NOT produce any numeric readiness, design, confidence, or quality score.
- **FR-036**: The feature MUST NOT publish, refresh, export, or schedule against the Power BI Service; the journey stops at committed on-disk artifacts (the F016 execution adapter remains the deferred boundary).
- **FR-037**: The feature MUST NOT perform a broad readiness-spine or Decision Store refactor, and MUST NOT place tenant-specific business logic in the generic core.
- **FR-038**: Each artifact type MUST have a single owner (no duplicate truth): Report Intent owns audience/purpose/decisions/questions (page blueprints reference intent questions, per FR-002a, and do not independently own them); Metric Contracts own metric meaning; the Semantic Model owns available measures/fields/relationships; Patterns own reusable design guidance; Page Blueprints own page-level intent; Visual Specs own per-visual intent; Report Composition owns page order + navigation; Preview owns a visual representation of design intent; Semantic Audit owns report-level findings; the Decision Store owns approval decisions; PBIR owns the implemented report definition; the Implementation Trace owns evidence that PBIR matches the approved design.

### Security & Data-Exposure Requirements

- **SEC-001**: The system MUST NOT require or use a live database connection for intent capture, design, preview, audit, or compilation; all of these operate on committed artifacts only (live checks remain the deferred `retail validate` / F016 boundary).
- **SEC-002**: The preview and any generated artifact MUST NOT embed real business result values unless those values come from an approved data source; absent that, placeholders MUST be clearly labeled (no fabricated data).
- **SEC-003**: PII referenced in intent MUST be masked by default; unmasking MUST itself be a recorded `pii_handling` decision by a named human (reusing the shipped Decision Store behavior).
- **SEC-004**: No secrets, connection strings, or real host/parameter values may appear in any committed artifact produced by this feature (consistent with the shipped `C2` / `G6` gate rules); Power BI uses parameters, not baked-in connection strings.
- **SEC-005**: PBIR produced or validated by this feature MUST use relative model references (consistent with the shipped `R1` rule) and MUST NOT contain business-logic-defining keys in a report file (consistent with `R2`).

### Key Entities

- **Report Intent**: committed, machine-readable record of *what the report is for* — audience, purpose, decision, questions, metric roles (outcome/driver/guardrail, all referencing approved contracts by name), comparisons, dimensions/filters, actions/exceptions, pages/drill paths, mobile/a11y/language/RTL needs, exclusions. *(New artifact type.)*
- **Dashboard Pattern**: generic, reusable design-guidance record (audiences, purpose, question families, metric roles, page structure, visual roles, action paths, design risks). Defines no KPI meaning. *(New; strengthens the 4 fixed starter blueprints.)*
- **Page Blueprint / Visual Spec / Report Composition**: shipped structural design artifacts (reused).
- **Blueprint Preview**: deterministic visual representation of approved design intent, placeholder-marked, no live data. *(New.)*
- **Semantic Audit Findings**: report-level categorical findings with cited evidence and named owner. *(New.)*
- **Blueprint Approval Decision**: a `dashboard_blueprint_approval` record in the shipped Decision Store (named-human, supersession-aware). *(Reused.)*
- **PBIR Artifacts**: committed on-disk report definition produced by the compiler or a human Desktop build. *(Extends shipped PBIR adapters.)*
- **Implementation Trace**: evidence that committed PBIR conforms to the approved design. *(Extends the shipped visual-implementation-trace.)*

---

## Repository Conflicts & Drift Found *(documented, not blocking)*

These are facts discovered while inspecting `main`. Each has a defensible default reconciliation for `/speckit.plan`; none is a blocking clarification.

1. **`report_intent` is a paper stage.** It exists only as a routing-taxonomy label in `contracts/knowledge/database-to-pbip-flow.yaml` (lines 126–136) — no template, no skill, and **no dedicated `decision_type`** (it is not among the ten `CRITICAL_DECISION_TYPES` in `src/seshat/decision_store.py`; it is blocked only by the pre-existing `kpi_definition` / `pii_handling` categories). *Recommended default*: the Report Intent interview records its own approval either by reusing existing decision types or by adding a new `report_intent_approval` decision type + a `contracts/report/report-intent.yaml` contract, mirroring the precedent already set by `dashboard_blueprint_approval` + `contracts/report/dashboard-blueprint.yaml`. Final choice is a plan-time decision.

2. **RS1 vs `approval-authority.yaml` authority-class gap (live code).** `contracts/knowledge/approval-authority.yaml` requires class `report_owner` for `dashboard_blueprint_approval`, but the shipped rule RS1 (`src/seshat/rules/readiness_status.py`, `_AUTHORITY_CLASSES`) recognizes only `{analyst, governance, data_owner, metric_owner}` — `report_owner` is excluded. The yaml's own comment flags this as a "FUTURE-stage class pending reconciliation." **Resolved (Clarifications 2026-07-12):** RS1 will be extended to recognize `report_owner` — a single-class, additive reconciliation of an existing gap, not a spine refactor (see FR-022a and FR-037). Every contract layer already requires it.

3. **Two unreconciled readiness layers.** The ratified 7-stage spine (`docs/readiness/readiness-model.md`, Constitution "Readiness System") and the spec-121 11-stage flow contract are bridged only by the non-authoritative `_FLOW_TO_SPINE` projection in `decision_gate.py`. *Recommended default*: preserve both as-is and consume the flow contract's stage order (FR-032); do not refactor the spine (FR-037).

4. **Stale status signals.** `Status: Draft` headers and `tasks.md` checkboxes are unreliable (116/117/118/121 merged while labeled Draft / unchecked). The stale `pbir-authoring-adapter/SKILL.md` omits shipped Increment D (geometry). *Recommended default*: treat `docs/capabilities/capabilities.yaml` `state:` + git log + source paths as authoritative; note the SKILL.md drift for a later doc fix (out of scope here).

5. **Shipped-but-unexercised templates.** `report-composition.yaml` and `driver-decomposition.md` are shipped but have no filled worked instance on `retail_store_sales`. *Recommended default*: this feature exercises them; the one real subject area remains an *example*, not the schema (Constitution Principle VII).

---

## Success Criteria *(mandatory)*

All criteria are behavioral and traceability-based — **no numeric readiness/design/confidence/quality score** is produced (per FR-035). "Measurable" here means categorically verifiable pass/fail against committed artifacts.

### Measurable Outcomes

- **SC-001**: A conversational dashboard request is turned into a committed, reviewable Report Intent artifact that records audience, purpose, decision, questions, outcome/driver/guardrail metrics, comparisons, filters, and actions. *(Verify: artifact exists and each field is present or explicitly marked N/A with reason.)*
- **SC-002**: Zero fabricated metric definitions — every metric referenced anywhere in intent, blueprint, or preview resolves to an approved metric contract; any missing definition is surfaced as a gap, not invented. *(Verify: 0 orphan metric references.)*
- **SC-003**: Zero orphan visuals — every visual in a produced/approved blueprint traces to an approved contract and a mapped semantic field. *(Verify: binding-map coverage = complete.)*
- **SC-004**: Dashboard proposals receive a deterministic `new` / `extends` / `duplicate` classification with no score (via the shipped planner). *(Verify: identical inputs → identical verdict.)*
- **SC-005**: The coordinator, on every unmet precondition, stops with a `blocked` result that names what is missing, the evidence checked, the responsible owner, and the unblocking action — and never self-grants `dashboard_ready: pass` nor bypasses `semantic_model_ready: pass`. *(Verify: each fail-closed trigger in FR-033 yields a conforming blocked result.)*
- **SC-006**: A preview can be reviewed before any PBIR work, uses no live data, fabricates no business result, and is deterministic across reruns. *(Verify: identical inputs → identical preview; placeholders labeled.)*
- **SC-007**: The semantic audit reports report-level coverage and actionability categorically (from the closed finding set) with cited evidence, and produces no numeric score. *(Verify: every finding has a category + evidence citation + named owner.)*
- **SC-008**: Blueprint approval is performed only by a named eligible human; an agent identity is always rejected; a post-approval change supersedes the prior approval and forces renewed approval before compilation. *(Verify against the shipped `approval_is_valid` predicate + DS4.)*
- **SC-009**: No PBIR compilation occurs before a valid `dashboard_blueprint_approval`; compiler output is bounded, deterministic, reversible, validated, and leaves no partial output on failure. *(Verify: compile-without-approval → blocked; failed run → no partial PBIR; rerun → byte-identical.)*
- **SC-010**: Implementation review can prove committed PBIR matches the approved blueprint (or flags the specific deviation) and grants no approval. *(Verify: validator reports expected vs actual per dimension; unapproved additions flagged.)*
- **SC-011**: The process always stops before Power BI Service publishing (no publish/refresh/export/schedule path exists). *(Verify: no Service-publishing action is reachable.)*
- **SC-012**: The MVP (US1 + US2) delivers a reviewable dashboard design and is useful with neither preview (US4) nor compilation (US7) present. *(Verify: MVP slice produces intent + blueprints + visual specs + composition + human-review handoff, standalone.)*

---

## MVP Boundary & Delivery Slices

**MVP (P1)** — ends after producing a reviewable dashboard design:

```
Report Intent Interview  (US1)
 -> Report Intent Artifact
 -> retail dashboard-gaps        (shipped)
 -> retail dashboard-planner     (shipped)
 -> dashboard-design             (shipped)
 -> Page Blueprints + Visual Specs
 -> Report Composition
 -> Human Blueprint Review
 -> STOP
```

The MVP delivers standalone value **without** preview rendering or PBIR creation. It is delivered as two independently-testable P1 slices: US1 (Report Intent) and US2 (Coordinator over shipped capabilities).

**Recommended later slices** (each independently useful; do **not** ship the feature as one PR):

1. Blueprint Preview (US4)
2. Dashboard Semantic Audit (US5)
3. Pattern Library (US3)
4. PBIR Page Shell (US7.1)
5. PBIR KPI Cards (US7.2)
6. PBIR Core Charts (US7.3)
7. PBIR Slicers and Navigation (US7.4)
8. Full PBIR Validation (US8 + US7.6)

Blueprint Approval & Versioning (US6) is a P2 that gates the PBIR slices; it is delivered before slice 4.

---

## Non-Goals

- No invented KPI/metric meaning; no unapproved metric in a visual; no unmapped semantic field.
- No self-approval; no numeric readiness/design/confidence/quality score.
- No replacement of any existing dashboard capability; no freehand dashboard generation outside approved artifacts.
- No guessed PBIR structures; no unrestricted PBIR mutation; no support for every Power BI visual type in the first compiler release.
- No Power BI Service publishing, refresh, export, or scheduling.
- No broad readiness-spine or Decision Store refactor; no tenant-specific business logic in the generic core.
- No live database provisioning or ingestion (repo YAGNI rule).
- No implementation architecture, library, wire-format, or file-location decisions — those belong to `/speckit.plan`.

---

## Assumptions

- **Approved metric contracts and a ready semantic model exist** for the target subject area before intent-driven design begins; where they do not, the feature routes upstream and blocks (per FR-004 / FR-033) rather than proceeding.
- **The Report Intent schema, storage format, and repository location are plan-time decisions** (the description explicitly defers them); the spec only requires the artifact be committed, machine-readable, and reviewable.
- **The Report Intent approval-recording mechanism** reuses the shipped Decision Store; whether it adds a new `report_intent_approval` decision type + contract or reuses existing types is deferred to plan-time (Conflict #1).
- **RS1 will be extended to recognize `report_owner`** for `dashboard_blueprint_approval` (Conflict #2, resolved in Clarifications), since all contract layers already require it; this is a single-class additive change (FR-022a), not a spine refactor (FR-037).
- **The preview rendering format is a plan-time choice** (the description explicitly defers it); the spec fixes only that it is deterministic, data-free, and placeholder-marked.
- **Compiler wire formats and the supported-visual allow-list are plan-time decisions**; the spec fixes only the boundaries (grounded in verified real samples, allow-listed, deterministic, reversible, no partial writes, no publish).
- **`retail_store_sales` remains an example, not the schema** (Constitution Principle VII); worked instances exercise the shipped templates without generalizing tenant specifics into the core.
- **The journey is agent-/skill-driven** (per the description); it does not add a broad new CLI family to wrap existing skills.
