# Feature Specification: Shareable Seshat Proof (Showcase Bundle)

**Feature Branch**: `127-showcase-build`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Shareable Seshat Proof (seshat showcase build). Compose EXISTING Explorer, Passport, readiness, review, blocker, approval, and lineage evidence into a disclosure-safe STATIC OFFLINE bundle. This is a composition/rendering layer over shipped evidence, NOT a new engine."

## Overview

Seshat BI already renders committed readiness truth two ways: the readiness
**Explorer** (a self-contained offline HTML view of stages, evidence, blockers,
approvals, next actions, and metric lineage, generated fail-closed against the
disclosure scanner) and the portable **Passport** (a disclosure-safe snapshot of
one or more tables' readiness state plus content identities, with a non-mutating
verify). What it does not yet give is a single **shareable proof bundle** an
analyst or maintainer can hand to a reviewer, a stakeholder, or a prospective
contributor to answer "what has Seshat governed here, and can I trust it?" -- one
offline folder that shows the readiness spine, the evidence, the blockers and
findings, the approvals, and the metric lineage together, carries a truthful
badge or project card (never a fabricated score), and states in a **disclosure
manifest** exactly what was included, redacted, omitted, and unavailable.

This feature adds that bundle as a **read-only composition and rendering layer
over already-shipped surfaces**. It READS the outputs of the Explorer
projection, the Passport, the readiness classify/evidence/projection modules,
the review/blocker/approval surfaces, and the metric-lineage projection, then
renders one accessible, responsive, RTL/Arabic-safe offline bundle. It recomputes
no readiness, defines no new evidence schema, invents no meaning, and grants no
approval. Generation is local-only and fail-closed on disclosure findings;
publishing the bundle anywhere remains a separate, explicit human action.

## Reuse Map (anti-reinvent contract)

This feature is defined by its DELTA over shipped surfaces. Every capability in
the brief is either **satisfied by reuse** (the feature calls the shipped module
and MUST NOT re-implement it) or **net-new** (the feature adds it as a rendering
concern over reused data). This table is normative: an FR that restates reused
behavior is a defect.

| Brief requirement | Disposition | Shipped surface reused / where net-new lives |
|-------------------|-------------|----------------------------------------------|
| (1) Show stages, evidence, blockers, findings, approvals, metric lineage | REUSE | `src/seshat/explorer/build.py::build_explorer_projection` (stages/evidence/blockers/approvals/lineage), `readiness_projection.py`, `readiness_classify.py`, `readiness_evidence.py`, `review_integration.py`, `blocker_explainer.py`, `approval_inbox.py` |
| (2) Before/after only when valid comparable snapshots exist | NET-NEW (rendering) | Compares two Passport snapshots (`passport.py`) by shared `schema_version` + `source_revision` + `scope`; reuses Passport verdict vocabulary |
| (3) Truthful badge / project card | NET-NEW (rendering) | Derived from the reused projection (highest contiguous `pass` stage, counts); never a fabricated confidence number (Constitution readiness-spine rule) |
| (4) Disclosure manifest (included / redacted / omitted / unavailable) | NET-NEW (rendering) | Categories map to EXISTING vocabulary: evidence `state`, Passport `unavailable`, `disclosure.scan_disclosure` findings |
| (5) Produce LOCAL OFFLINE files only | REUSE | `src/seshat/cli/guards.py::resolve_local_output` (`.seshat-output/` containment), Explorer offline posture |
| (6) Never publish / upload / track / call external APIs | REUSE | Explorer CLI posture: local write only; no network in the composition path |
| (7) Remove secrets, credentials, DSNs, PII, local paths, private URLs | REUSE (+ one net-new scan term) | `src/seshat/disclosure.py::scan_disclosure` fail-closed; "private URL" handling is the one candidate scanner extension (see FR-019) |
| (8) Accessible, responsive, Arabic, RTL-safe output | NET-NEW (rendering) | Bundle renders its OWN a11y/RTL shell aligned to shipped spec-102 rules (`design_contrast`, `design_categorical_distinctness`); does not edit `explorer.css` |

## Clarifications

### Session 2026-07-14

- Q: Should the bundle be surfaced as a new `seshat showcase build` CLI verb (as the brief's wording implies) or as a read-only skill/composer? -> A: **Skill/composer, honoring the ratified Option B decision** (`docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`, owner-ratified 2026-07-07: the CLI stays a narrow gate; new capabilities ship as skills over a reusable library function). The composition logic lives as a library function under `src/seshat/`, reused by a skill; no new top-level CLI verb is added.
- Q: When a live disclosure finding (secret, DSN, PII, absolute path) is detected, is the offending content "redacted" into the bundle or does generation block? -> A: **Fail-closed block**, inheriting the Explorer posture (no partial/redacted page is written). "Redacted" in the manifest names by-design portability normalizations (absolute paths reduced to repo-relative, private URLs stripped), NOT the suppression of a disclosure finding.
- Q: Does producing the bundle constitute PII publish sign-off? -> A: **No.** The bundle is a local file; sharing it is a separate explicit human action after disclosure review. Generation never grants publish approval.
- Q: What does "valid comparable snapshots" mean for before/after (requirement 2)? -> A: Two Passport snapshots are comparable only when they share `schema_version` and `scope` and differ in `source_revision`; otherwise the before/after section is **omitted gracefully** (no fabricated delta).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Render a Shareable Proof Bundle from Committed Evidence (Priority: P1)

A Seshat maintainer or analyst asks for a shareable proof of the current
workspace. The feature reads the shipped readiness projection (stages, evidence
states, blockers, approvals, next actions, metric lineage) and renders one
self-contained offline bundle: a landing page with a truthful badge/project
card, per-table readiness detail, and a disclosure manifest. Nothing is inferred;
a missing artifact shows as missing, a deferred live check as unavailable, and no
stage is shown as `pass` without evidence.

**Why this priority**: This is the MVP. Without the composed offline bundle and
its truthful badge, there is no shareable proof at all; every other story
enriches this one.

**Independent Test**: Point the feature at the worked example, open the generated
bundle offline, and confirm it displays every table's stages, evidence, blockers,
approvals, next action, and metric lineage; that the badge reflects the actual
highest contiguous passed stage; and that the source readiness artifacts are
unchanged.

**Acceptance Scenarios**:

1. **Given** a workspace with one or more valid readiness records, **When** the bundle is generated, **Then** it contains per-table stage/evidence/blocker/approval/next-action detail and the available metric lineage, all sourced from the shipped projection.
2. **Given** an evidence reference that is a bracketed live sentinel or prose, **When** the bundle is generated, **Then** that evidence is shown as unavailable (deferred), never as a passing file.
3. **Given** an artifact is missing or malformed, **When** the bundle is generated, **Then** the affected item is shown as missing / an input defect and never substituted with an inferred pass.
4. **Given** a user browses the generated bundle, **When** they navigate or filter it, **Then** no source artifact, readiness status, database, or Power BI model is modified.

---

### User Story 2 - Truthful Badge / Project Card (Priority: P2)

The bundle carries a badge (and a richer project card) summarizing readiness at a
glance. The badge is derived only from committed evidence -- for example the
highest contiguous stage that is `pass` and the count of passed stages -- and is
rendered as an offline inline image/markup. It never states a percentage
confidence, a grade, or any claim not backed by the projection.

**Why this priority**: A badge is the single most shareable artifact (README,
issue, chat), so its truthfulness is load-bearing; but it is meaningless without
US1's bundle, so it is P2.

**Independent Test**: Generate a bundle for a workspace where stages 1-3 pass and
stage 4 is blocked; confirm the badge reads a contiguous-passed summary (e.g.
"Gold: blocked" / "3/7 stages ready"), never a fabricated score, and renders
offline with no external image fetch.

**Acceptance Scenarios**:

1. **Given** a workspace whose highest contiguous passed stage is Silver, **When** the badge is generated, **Then** it names that stage and the passed-stage count and contains no percentage or grade.
2. **Given** a badge is embedded in the bundle, **When** the bundle is opened offline, **Then** the badge renders from inline markup/data URI with no network request.
3. **Given** no stage has passed for any table, **When** the badge is generated, **Then** it states the truthful onboarding/earliest-stage status rather than an empty or celebratory claim.

---

### User Story 3 - Disclosure Manifest (Priority: P2)

The bundle includes a disclosure manifest that transparently lists, in four
categories: **included** content (evidence that is `available`), **unavailable**
content (deferred live checks and prose evidence the Passport marks unavailable),
**omitted** content (missing artifacts, input defects, and any out-of-scope
tables/stages), and **redacted** content (the by-design portability
normalizations the composer applied -- absolute paths reduced to repo-relative,
private URLs stripped). The manifest is a truth ledger of what the bundle does and
does not show.

**Why this priority**: The manifest is what makes the bundle safe to share and
what distinguishes a truthful proof from a marketing page; it is P2 because it
requires US1's composed content to describe.

**Independent Test**: Generate a bundle for a workspace mixing available evidence,
a deferred live check, a missing artifact, and a machine-local absolute path;
confirm each appears under exactly one of the four manifest categories with a
locator, and nothing is silently dropped.

**Acceptance Scenarios**:

1. **Given** evidence in states available / deferred / missing, **When** the manifest is built, **Then** each is listed under included / unavailable / omitted respectively, each with its reference.
2. **Given** the composer normalizes an absolute path to repo-relative for portability, **When** the manifest is built, **Then** that normalization is listed under redacted with a locator, not silently applied.
3. **Given** a table is outside the requested bundle scope, **When** the manifest is built, **Then** it is listed under omitted, so the reader knows the bundle is partial.

---

### User Story 4 - Before/After Only When Comparable (Priority: P3)

When the user supplies two Passport snapshots of the same scope taken at
different source revisions, the bundle shows a before/after section (which stages
advanced, which evidence changed, per the Passport verify vocabulary). When the
snapshots are not comparable -- different scope, different schema version, or only
one snapshot -- the section is omitted gracefully with a short truthful note,
never a fabricated delta.

**Why this priority**: Before/after is a powerful proof of progress but strictly
optional and dependent on the user having two snapshots; the bundle is fully
valuable without it, so P3.

**Independent Test**: Generate a bundle with two comparable snapshots and confirm
the diff section shows the real stage/evidence changes; then generate with
mismatched-scope snapshots and confirm the section is omitted with a note and no
invented delta.

**Acceptance Scenarios**:

1. **Given** two Passport snapshots with the same schema version and scope and different source revisions, **When** the bundle is generated, **Then** a before/after section reports the stage and evidence changes using the Passport verdict vocabulary.
2. **Given** two snapshots of different scope, **When** the bundle is generated, **Then** the before/after section is omitted with a note stating the snapshots are not comparable.
3. **Given** only one snapshot (or none), **When** the bundle is generated, **Then** no before/after section is rendered and no delta is fabricated.

---

### User Story 5 - Accessible, Responsive, RTL/Arabic-Safe Output (Priority: P3)

The bundle's rendered shell is accessible (color contrast and colorblind-safe
palette aligned to the shipped spec-102 gate rules), responsive (readable on a
narrow screen with no horizontal body scroll), and RTL/Arabic-safe (correct
`dir`/`lang`, mirrored layout, Arabic labels supported). The showcase renders its
OWN shell over the reused projection data; it does not modify the shipped Explorer
assets.

**Why this priority**: Accessibility and RTL are the credibility and inclusivity
layer for a shareable proof (Arabic retail is a first-class audience), but the
bundle conveys its truth even before the shell is polished, so P3.

**Independent Test**: Generate a bundle and confirm the shell passes the
spec-102-aligned contrast/colorblind checks, lays out without horizontal body
scroll at a narrow width, and renders correctly with `dir="rtl"` and Arabic
labels; confirm the shipped `explorer.css`/`explorer.js` files are byte-unchanged.

**Acceptance Scenarios**:

1. **Given** the bundle shell, **When** its palette and text are checked, **Then** they satisfy the spec-102 contrast and categorical-distinctness thresholds.
2. **Given** an Arabic/RTL rendering mode, **When** the bundle is opened, **Then** the document declares `dir="rtl"` with correct `lang`, mirrors layout, and shows Arabic labels without breakage.
3. **Given** a narrow viewport, **When** the bundle is opened, **Then** content reflows without horizontal body scroll and wide content scrolls within its own container.

---

### Edge Cases

- A workspace contains no onboarded tables: the bundle shows the truthful earliest-stage (Source Ready onboarding) status and a truthful badge, never an empty success or a celebratory claim.
- A readiness file is malformed: it is surfaced as an input defect in both the bundle and the disclosure manifest (omitted category), never rendered as a pass.
- A live disclosure finding (secret / DSN / PII / absolute path) is present in the composed data: generation blocks fail-closed with the findings listed; no partial or redacted bundle is written.
- A metric contract is unreadable: it appears as an input-defect lineage node (reusing the Explorer lineage behavior), not as a valid metric.
- Two before/after snapshots share scope but one is malformed / wrong schema: treated as not comparable; the section is omitted with a note.
- The output path escapes the contained output root: generation refuses with an uncontained-output error (reusing the guard), writing nothing.

## Requirements *(mandatory)*

### Functional Requirements

**Composition over shipped surfaces (reuse; MUST NOT re-implement)**

- **FR-001**: The feature MUST obtain readiness stages, evidence states, blockers, approvals, next actions, and metric lineage by reading the shipped readiness/Explorer projection, and MUST NOT recompute readiness or re-derive evidence states.
- **FR-002**: The feature MUST NOT define a new evidence schema, a new readiness engine, a new Explorer, or a new Passport; it composes and renders the existing ones.
- **FR-003**: The feature MUST surface a missing artifact as missing, a malformed artifact as an input defect, and a deferred live check as unavailable, exactly as the shipped projection classifies them; it MUST NOT show any stage as `pass` without inspectable evidence.
- **FR-004**: The composition path MUST be read-only with respect to every source artifact, readiness status, database, and Power BI model; generating or browsing the bundle MUST NOT modify them.

**Delivery shape and offline safety (reuse)**

- **FR-005**: The feature MUST be surfaced as a read-only skill/composer over a reusable library function, honoring the ratified Option B decision; it MUST NOT add a new top-level CLI verb.
- **FR-006**: The feature MUST write only local files under the contained output root (`.seshat-output/`), refusing any output path that escapes it, and MUST write nothing on refusal.
- **FR-007**: The feature MUST NOT publish, upload, track users/telemetry, or call any external network or publishing API in the generation path; the bundle MUST be fully functional offline.
- **FR-008**: Every asset the bundle needs (styles, scripts, badge image, brand mark) MUST be inlined or embedded as a data URI; the bundle MUST make no external request when opened.

**Disclosure safety (reuse scanner; fail-closed)**

- **FR-009**: Before writing the bundle, the feature MUST run the shipped disclosure scan over the composed content and MUST fail closed (write nothing, list the findings) if any blocking finding is present.
- **FR-010**: Secrets, credentials, DSNs / connection strings, PII values, and machine-local absolute paths MUST NOT appear in the bundle; their presence is a blocking disclosure finding (fail-closed), not a redaction.
- **FR-011**: Generating the bundle MUST NOT constitute or grant any approval or publish sign-off; sharing the bundle remains a separate, explicit human action recorded outside this feature.

**Badge / project card (net-new rendering)**

- **FR-012**: The feature MUST generate a truthful badge and a richer project card derived only from committed evidence (e.g. the highest contiguous passed stage and the count of passed stages).
- **FR-013**: The badge and card MUST NOT express a fabricated confidence number, percentage, grade, or any claim not backed by the projection.
- **FR-014**: The badge MUST render offline from inline markup or a data URI, with no external image fetch.
- **FR-015**: When no stage has passed, the badge MUST state the truthful earliest-stage / onboarding status, never an empty or celebratory claim.

**Disclosure manifest (net-new rendering over existing vocabulary)**

- **FR-016**: The bundle MUST include a disclosure manifest listing content in four categories -- included, redacted, omitted, and unavailable -- each entry carrying a locator/reference.
- **FR-017**: The manifest categories MUST map to existing vocabulary: included = evidence state `available`; unavailable = deferred live sentinels and prose evidence (Passport `unavailable`); omitted = missing artifacts, input defects, and out-of-scope tables/stages; redacted = the composer's by-design portability normalizations.
- **FR-018**: The manifest MUST NOT silently drop any composed item; every item shown, normalized, omitted, or unavailable MUST appear under exactly one category.
- **FR-019**: The feature MUST reduce machine-local absolute paths to repo-relative form and strip private/internal URLs before rendering, and MUST list each such normalization under the manifest's redacted category. [Scanner extension: "private URL" detection is a candidate addition to the shipped disclosure scanner; see plan.]

**Before/after (net-new rendering, optional)**

- **FR-020**: The feature MUST render a before/after section ONLY when two supplied Passport snapshots are comparable -- same schema version and same scope, differing source revision -- and MUST omit the section gracefully otherwise.
- **FR-021**: The before/after section MUST express changes using the Passport verify/verdict vocabulary and MUST NOT fabricate a delta when snapshots are absent, single, or non-comparable.

**Accessibility, responsiveness, RTL/Arabic (net-new rendering)**

- **FR-022**: The bundle's rendered shell MUST satisfy the shipped spec-102 accessibility criteria it aligns to (color contrast, colorblind-safe categorical distinctness); it MUST NOT invent new a11y criteria.
- **FR-023**: The bundle MUST be responsive: readable at a narrow viewport with no horizontal body scroll; wide content (tables, lineage) MUST scroll within its own container.
- **FR-024**: The bundle MUST support RTL/Arabic output with correct `dir` and `lang`, mirrored layout, and Arabic labels rendered without breakage.
- **FR-025**: The feature MUST render its own shell over the reused projection data and MUST NOT modify the shipped Explorer assets (`explorer.css` / `explorer.js`) or the Explorer's output contract.

**Truthfulness invariants (cross-cutting)**

- **FR-026**: The bundle MUST NOT present any fabricated score, claim, delta, approval, or pass; every displayed fact MUST trace to committed evidence or be labeled unavailable/omitted.
- **FR-027**: The bundle MUST state that it is a local offline snapshot generated from committed evidence only, and that publication is a separate explicit human action.

### Key Entities *(include if feature involves data)*

- **Showcase bundle**: The generated offline folder/set of files -- landing page, per-table detail, badge/card, disclosure manifest, optional before/after. A rendering of the reused projection; owns no readiness state.
- **Showcase projection (reused)**: The Explorer/readiness projection document (stages, evidence states, blockers, approvals, next actions, lineage) the bundle reads. Not redefined here.
- **Truthful badge / project card**: A derived, evidence-only summary (highest contiguous passed stage, passed-stage count); never a fabricated score.
- **Disclosure manifest**: The four-category ledger (included / redacted / omitted / unavailable) describing exactly what the bundle shows, normalizes, omits, and cannot show.
- **Comparison pair (optional)**: Two Passport snapshots deemed comparable (same schema + scope, differing revision) that drive the before/after section.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a workspace with valid readiness records, a reviewer can open the generated bundle fully offline (no network) and read every table's stages, evidence, blockers, approvals, next action, and metric lineage.
- **SC-002**: 100% of displayed readiness facts trace to a committed-evidence reference or are labeled unavailable/omitted; zero stages are shown as `pass` without evidence, verified over the worked example and an all-missing fixture.
- **SC-003**: The badge/card contains zero fabricated confidence numbers, percentages, or grades across all fixtures; when no stage passes, it shows the truthful earliest-stage status.
- **SC-004**: Every composed item appears under exactly one disclosure-manifest category (included / redacted / omitted / unavailable), with no silent drops, verified on a mixed-state fixture.
- **SC-005**: When composed content contains a secret / DSN / PII / absolute path, generation blocks fail-closed and writes no bundle file; the findings are reported.
- **SC-006**: The before/after section appears only for comparable snapshot pairs and is omitted with a note otherwise; no delta is fabricated for absent/single/non-comparable snapshots.
- **SC-007**: The rendered shell passes the spec-102-aligned contrast/colorblind checks, reflows at a narrow viewport without horizontal body scroll, and renders correctly under `dir="rtl"` with Arabic labels.
- **SC-008**: The shipped Explorer assets (`explorer.css`, `explorer.js`) and every source readiness artifact are byte-unchanged after generation.

## Assumptions

- The bundle is surfaced as a read-only skill over a reusable library function (Option B, ratified 2026-07-07); no new top-level CLI verb is added. Reversible-but-costly if the owner later wants a verb.
- Generation is local-only and fail-closed; publishing the bundle is a separate explicit human action outside this feature's scope.
- The feature reuses the shipped Explorer projection, Passport, readiness classify/evidence/projection modules, review/blocker/approval surfaces, metric-lineage projection, the disclosure scanner, and the contained-output guard; it recomputes none of them.
- Accessibility/RTL requirements align to the shipped spec-102 gate rules; no new a11y criteria are invented.
- "Private URL" stripping may require a small, additive extension to the shipped disclosure scanner (which today covers connection strings, absolute paths, secret keys, PII, and raw arrays); whether to extend the scanner or scope it out is a plan-phase decision, and either way absolute-path and secret handling remain fail-closed.
- The worked example under `docs/worked-examples/` plus synthetic fixtures (all-missing, mixed-state, comparable/non-comparable snapshot pairs) are sufficient to test the feature; no live database and no Power BI Desktop are required.
- This is a Layer-6 delivery/handoff rendering surface: it reads across all readiness stages and advances none; it gates nothing.
