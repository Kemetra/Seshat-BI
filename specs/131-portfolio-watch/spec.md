# Feature Specification: Portfolio Watch

**Feature Branch**: `131-portfolio-watch`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Portfolio Watch (seshat watch build). Produce a RECURRING, READ-ONLY portfolio summary for teams WITHOUT creating another governance engine. Aggregation/summary layer over existing evidence + drift surfaces, covering source drift; contract and semantic drift; stale or missing approvals; changed readiness; dashboard-intent divergence; tables requiring human attention; new, resolved, and unchanged blockers; ONE prioritized next action per governed scope."

---

## Overview

Seshat BI already ships strong per-scope evidence surfaces (source drift, contract/semantic drift, readiness state, dashboard-intent audit, approval inbox, review integration) and one shipped worst-first cross-table roll-up (the `retail-control-room` skill, F012). What a team lacks is a **recurring, read-only portfolio summary** that answers a single question over the whole portfolio at once and again next week: *since we last looked, what changed, what still needs a human, and what is the one next thing to do per scope?*

Portfolio Watch is that summary. It is an **aggregation/summary layer**, not a new governance engine: it **derives** its result entirely from evidence the shipped surfaces already produce, adds **no new gate**, adds **no new `retail check` rule**, and creates **no new approval mechanism**. Its genuinely new contribution over the existing control-room roll-up is a **baseline diff** -- it persists a local snapshot each run so the next run can distinguish a *new* condition from an *unchanged* one and can report *resolved* conditions -- plus coverage of the drift, semantic-drift, and dashboard-intent-divergence dimensions the control room does not fold in today.

The feature is delivered as **independently useful slices**. Its MVP is a single, re-runnable read-only summary with the baseline diff. Later slices broaden dimension coverage and reporting formats. Scheduling and hosted monitoring are explicitly **out of the MVP**: "recurring" here means *re-runnable + baseline-diffable*, not a scheduler.

### Capability classification (shipped truth verified against `main`)

Authoritative status was read from `docs/capabilities/capabilities.yaml` (`state:` field) plus the source path and `git log`, **not** from `spec.md` headers or `tasks.md` checkboxes (known-stale in this repo). Verified: spec 123 (governed dashboard intelligence) is **merged and implemented** (commit `88daf50`, PR #261), so its intent-audit surfaces are shipped runtime, not paper.

**A. Shipped surfaces this feature AGGREGATES (must not be replaced, re-implemented, or re-derived):**

| Dimension it feeds | Where it lives (evidence) | What it emits today | Live leg? |
|---|---|---|---|
| Source drift | `src/seshat/drift.py`, `src/seshat/drift_semantics.py`; `retail-drift` (`state: shipped`) | A drift-findings dict (nine classes, four statuses, Principle-V handoff) from a pure comparator; `drift_semantics` supplies returns/PII roles | **Yes** -- the comparison needs a re-profile (`observed`); absent a DSN it is `[PENDING LIVE RE-PROFILE]` |
| Contract / metric drift | `src/seshat/metric_drift.py`; `retail-semantic-check` (`state: shipped`) | A per-measure `Verdict` comparing a DAX denominator's filter-set to the approved contract; ESCALATE is the default branch | Reads committed contracts + TMDL; no DB for the static compare |
| Semantic / dashboard-intent divergence | `src/seshat/semantic_audit.py`, `src/seshat/report_intent.py`, `src/seshat/rules/report_intent.py` | Report-level categorical audit findings (closed enum `covered`/`incomplete`/`missing`/`conflicting`/`warning`/`blocked`/`not_applicable_with_reason`) + metric-reference resolution against approved contracts | No DB (committed artifacts only) |
| Readiness state + changed readiness | `src/seshat/readiness_projection.py`, `readiness_classify.py`, `readiness_evidence.py` | A disclosure-safe per-table projection (`current_stage`, four-status `stages[]`, `evidence`, `blocking_reasons`, `next_action`); the fixed category rank | No DB (committed `readiness-status.yaml`); `readiness_evidence` records a proposed `gold_ready` block from a live `validate` run |
| Governed-scope enumeration | `src/seshat/portfolio_enumerate.py` | The reachable table set OR one redacted boundary error (DSN-safe) | **Yes** -- enumeration reads DB metadata; the read-only summary uses the committed per-scope artifacts, not this live path (see Assumptions) |
| Stale / missing approvals | `src/seshat/approval_inbox.py`; `retail-approvals` (`state: shipped`) | A read-only inbox of open/invalid approval seams across committed readiness statuses; never records a decision | No DB |
| Review surfaces (tables requiring human attention) | `src/seshat/review_integration.py`, `src/seshat/review_pack_export.py` | A stable change-review result derived from governance findings, mapped to a stage; a review-pack export | No DB |
| Closest shipped sibling (roll-up precedent) | `.claude/skills/retail-control-room/SKILL.md` (F012, `state: shipped`) | A worst-first, read-only, cross-table roll-up of stage/status/WARNs/live findings/blockers/next-action -- every cell traces to a committed source; emits no score | No DB |

**B. What this feature STRENGTHENS or COORDINATES (no parallel replacement):**

- **The control-room roll-up** is point-in-time: it shows *current* state worst-first but does not persist a baseline, so it cannot say what is *new* versus *unchanged*, cannot report *resolved* conditions, and does not fold in drift / semantic-drift / dashboard-intent-divergence. Portfolio Watch **extends** the same read-only, aggregate-never-re-derive posture with a persisted baseline diff and those extra dimensions. It does not fork or replace the control-room skill.
- **The per-surface readers** each answer one dimension for one scope. Portfolio Watch **joins** their existing outputs across the portfolio into one summary; it never re-computes a surface's own check.

**C. Genuinely NEW in this feature (absent on `main`):**

- **The Portfolio Watch summary artifact** -- one local, committed, machine-readable + human-readable summary spanning the whole portfolio and all covered dimensions. *(New artifact type.)*
- **The persisted prior-run snapshot (baseline)** -- a local artifact each run writes so the next run can diff current categorical state against it. This is the one entity that makes *new / resolved / unchanged* and duplicate-suppression possible. *(New entity.)*
- **The change classifier** -- the pure diff of the current summary against the prior snapshot into `new` / `resolved` / `unchanged` per condition. *(New; modeled on `drift.py`'s baseline-vs-observed comparator, including its `observed=None` honesty for the first run.)*

---

## Clarifications

### Session 2026-07-14

- Q: Should "seshat watch build" be a broad new CLI verb family? -> A: **No.** The ratified product-direction decision (`docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`, Option B, Ahmed Shaaban 2026-07-07) and hard rule #1 keep the kit agent-/skill-driven and the CLI a narrow gate. Portfolio Watch is delivered agent-/skill-driven like its sibling `retail-control-room`, with the **one deliberate allowed CLI addition** being a narrow, read-only, machine-readable summary/status surface mirroring the ratified `status --format json` precedent -- NOT a broad new verb family. (Auto-answered per the drafting clarification policy; reversibility: easy -- packaging is additive.)
- Q: What is a "governed scope"? -> A: The **existing per-table / per-report unit** the readiness spine and `portfolio_enumerate` already track -- Portfolio Watch introduces **no new scope unit**. A scope is identified by its committed readiness-status path, exactly as the control room and the readiness projection already identify tables.
- Q: How is the "one prioritized next action per scope" ranked without a score? -> A: By the **shipped fixed categorical rank** in `readiness_classify` (`approval` > `grain` > `live_validation` > `artifact` > `readiness`) -- a committed lookup, never a computed priority. The summary relays the highest-ranked scope's own `next_action`; it does not invent one.

## User Scenarios & Testing *(mandatory)*

Actors: BI analyst / data engineer, data owner, governance reviewer, metric owner, report owner, agent operator, team lead (the recurring-summary consumer).

### User Story 1 - Read a recurring portfolio summary (Priority: P1 -- MVP)

A team lead (or the agent on their behalf) runs Portfolio Watch over the repo and gets one read-only summary: for every governed scope, its current readiness stage/status, any open blockers, the covered evidence dimensions (source drift, contract/semantic drift, stale/missing approvals, dashboard-intent divergence), whether it needs human attention, and one prioritized next action -- with every line traceable to a committed source and no numeric score anywhere.

**Why this priority**: The read-only summary is the product. Even with no baseline yet (first run), it delivers standalone value: a single truthful cross-portfolio picture that today only exists piecemeal across separate surfaces.

**Independent Test**: Point Portfolio Watch at a repo that has several tables at mixed readiness stages plus committed drift / approval / intent evidence; confirm it produces one summary that (a) lists every governed scope the readiness spine tracks, (b) for each covered dimension cites the committed evidence it summarized, (c) marks any dimension with no shipped producer or no available evidence truthfully (`not_applicable_with_reason` / `[PENDING LIVE]` / `stale` / `unreadable`) rather than fabricating coverage, (d) names one prioritized next action per scope drawn from that scope's own recorded `next_action`, and (e) contains no numeric health/confidence score. Deliverable is reviewable on its own.

**Acceptance Scenarios**:

1. **Given** a repo with tables at Source/Mapping/Gold-ready and committed drift + approval + intent evidence, **When** Portfolio Watch runs, **Then** it emits one summary enumerating every governed scope with its stage, status, open blockers, covered-dimension findings, human-attention flag, and one prioritized next action -- each finding citing a committed evidence path.
2. **Given** a scope whose highest-ranked open condition is a missing named approval, **When** the next action is chosen, **Then** the summary relays that scope's recorded `next_action` and marks the scope as requiring human attention (approval outranks grain/live/artifact/readiness by the shipped fixed rank), never self-granting the approval.
3. **Given** the summary is produced, **When** any field would need a rolled-up number, **Then** the summary uses the four spine statuses + categorical findings + measured magnitudes only, and emits no numeric health/confidence/priority score.
4. **Given** a scope has no open condition at all (all covered dimensions clean, no blockers), **Then** its next action is the scope's own terminal/next-stage `next_action`, and it is NOT flagged for human attention.

---

### User Story 2 - Distinguish changes from existing conditions across runs (Priority: P1 -- MVP)

The team runs Portfolio Watch again a week later. This time each condition is labeled `new`, `resolved`, or `unchanged` relative to the prior run, so the team reads only what moved instead of re-reading a wall of standing conditions -- and the same standing condition is never re-alerted as if it were new.

**Why this priority**: Without a baseline, a recurring summary re-alerts every standing condition every run (alert fatigue) and cannot show that something was fixed. The baseline diff is the core value that separates Portfolio Watch from the point-in-time control-room roll-up. It is P1/MVP alongside US1 because "recurring" is meaningless without it.

**Independent Test**: Run Portfolio Watch twice against two committed repo states. Confirm: (1) the **first** run writes a local baseline snapshot and -- because there is no prior snapshot -- labels every condition a **current condition, explicitly NOT `new`** (the `observed=None` honesty pattern); (2) the **second** run diffs against the first snapshot and labels each condition `new` (present now, absent before), `resolved` (absent now, present before), or `unchanged` (present in both); (3) a condition present in both runs is reported once as `unchanged`, never re-alerted as `new` (duplicate suppression); (4) the snapshot is a local artifact only -- nothing is published or sent anywhere.

**Acceptance Scenarios**:

1. **Given** no prior snapshot exists, **When** the first run completes, **Then** it writes a local baseline snapshot and marks every condition a current condition (not `new`), stating explicitly that no baseline was available to diff against.
2. **Given** a prior snapshot exists, **When** a later run completes, **Then** each condition is labeled `new` / `resolved` / `unchanged` by diffing the current categorical state against the snapshot, and the run writes a fresh snapshot for the next run.
3. **Given** the same standing blocker is present in two consecutive runs, **When** the later run classifies it, **Then** it is `unchanged` and is not re-raised as a new alert.
4. **Given** a blocker present last run is absent this run, **When** the later run classifies it, **Then** it is reported as `resolved`, citing that it no longer appears in the current evidence.
5. **Given** the covered scope set changed between runs (a scope added or removed), **When** the diff runs, **Then** added/removed scopes are reported truthfully as scope-level changes, not misattributed as condition changes within a missing scope.

---

### User Story 3 - Handle unavailable, stale, partial, and incompatible evidence truthfully (Priority: P1 -- MVP)

Because Portfolio Watch is read-only and runs with no live database in the MVP, some evidence is unavailable, some is old, some scopes have none yet, and some may be in a format this version cannot read. The summary must say so precisely and never guess.

**Why this priority**: Truthful degradation is a hard constitutional requirement (Principle VIII static-first / live-deferred; hard rule #9 no fake confidence; the `source-drift.md` `[PENDING LIVE]` precedent). A summary that silently fabricates coverage for an absent producer or reads a stale file as current is worse than no summary. P1/MVP -- it is inseparable from US1's correctness.

**Independent Test**: Construct a repo where: (a) a covered dimension has evidence that requires a live re-profile but no DSN is configured; (b) a scope's committed evidence predates the current `source_revision`/HEAD; (c) several scopes have no evidence yet for a dimension; (d) one evidence file declares a schema version this feature does not understand. Confirm the summary marks (a) `[PENDING LIVE]`, (b) `stale` (with the revision it was captured at vs current), (c) `not_applicable_with_reason` / no-evidence-yet, and (d) `unreadable` (naming the unknown schema version) -- and fabricates none of them.

**Acceptance Scenarios**:

1. **Given** a dimension whose evidence needs a live re-profile and no DSN/`db` extra is present, **When** the summary runs, **Then** that dimension is `[PENDING LIVE]` (never a fabricated comparison), consistent with `docs/readiness/source-drift.md`.
2. **Given** a scope's committed evidence was captured at a revision older than the current HEAD/`source_revision`, **When** it is summarized, **Then** it is marked `stale`, citing captured-at vs current, and is not presented as a current condition.
3. **Given** a dimension has no shipped producer for a scope (or no evidence has been produced yet), **When** it is summarized, **Then** it is `not_applicable_with_reason` (naming why: "source not yet implemented" / "no evidence produced yet"), never counted as covered/clean.
4. **Given** an evidence artifact declares a schema version this feature cannot parse, **When** it is read, **Then** it is marked `unreadable` (naming the unknown version) and excluded from any pass/clean claim, never guessed.
5. **Given** a partial portfolio (some scopes fully evidenced, some empty), **When** the summary runs, **Then** it reports the covered scopes truthfully and lists the un-evidenced scopes as such -- it does not block or fail the whole run on partial coverage.

---

### User Story 4 - Broaden dimension coverage and reporting formats (Priority: P2)

Later slices widen the summary to fold in additional shipped dimensions not in the MVP core and add human-friendly reporting formats (e.g. a rendered digest) over the same machine-readable summary -- without changing the read-only, aggregate-only, no-score posture.

**Why this priority**: The MVP delivers value with the core dimensions and a machine-readable + basic human-readable summary. Additional dimensions and richer rendering improve consumption but are not required for the recurring summary to be useful. P2.

**Independent Test**: Given the MVP summary artifact, add coverage for an additional shipped dimension and a rendered digest format; confirm the added dimension is sourced from a shipped surface (cited), the digest is a pure rendering of the same machine-readable summary (identical inputs -> identical digest), and neither addition introduces a score, a write-back, a live DB requirement, or a new gate.

**Acceptance Scenarios**:

1. **Given** a shipped surface not yet folded into the MVP, **When** it is added as a dimension, **Then** its findings cite that surface's committed output and follow the same truthful-degradation rules, adding no new gate.
2. **Given** the machine-readable summary, **When** a human-readable digest is produced, **Then** it is a deterministic rendering of the same summary (no new data, no score) and is reviewable across revisions.

---

### Edge Cases

- **First run, no baseline**: every condition is a current condition, explicitly NOT `new`; a baseline snapshot is written for next time (US2 #1).
- **Duplicate/standing condition**: reported once as `unchanged`; never re-alerted as new (US2 #3).
- **Resolved condition**: reported as `resolved` when it disappears from current evidence (US2 #4).
- **Scope added/removed between runs**: reported as a scope-level change, not misattributed to conditions (US2 #5).
- **Live-only evidence, no DSN**: `[PENDING LIVE]`, never a fabricated comparison (US3 #1).
- **Stale evidence (predates HEAD/`source_revision`)**: marked `stale`, not current (US3 #2).
- **No producer / no evidence yet for a dimension**: `not_applicable_with_reason`, not counted clean (US3 #3).
- **Unreadable/incompatible schema version**: marked `unreadable`, naming the version; never guessed (US3 #4).
- **Partial portfolio**: covered scopes summarized; empty scopes listed; run does not fail (US3 #5).
- **Empty portfolio (no governed scopes yet)**: the summary states there are no governed scopes yet and writes an empty baseline; it does not error.
- **A Principle-V blocker upstream** (grain / returns / PII drift, unmet approval): Portfolio Watch **relays** the blocker and names the responsible owner; it decides none of them and originates no Principle-V ruling.
- **Snapshot corruption / unreadable prior snapshot**: the run treats it as "no usable baseline" (degrade to first-run behavior, marked as such), never a fabricated diff.
- **Two scopes tie on the highest-ranked category**: both surface their own next action; the rank is a fixed committed lookup, so the tie is reported, not broken by a synthesized number.
- **Contract/metric drift that ESCALATEs** (unknown predicate / non-ratio measure): relayed as an escalation-to-human condition, never resolved to pass or drift by the summary.

---

## Requirements *(mandatory)*

### Functional Requirements -- Summary (US1)

- **FR-001**: The system MUST produce ONE read-only portfolio summary covering, per governed scope: source drift; contract/semantic drift; stale or missing approvals; changed readiness; dashboard-intent divergence; tables/scopes requiring human attention; new/resolved/unchanged blockers; and ONE prioritized next action per governed scope.
- **FR-002**: A "governed scope" MUST be the existing per-table/per-report unit the readiness spine and `portfolio_enumerate` already track; the feature MUST NOT introduce a new scope unit.
- **FR-003**: The summary MUST DERIVE every finding from evidence the shipped surfaces already produce (source-drift findings, metric-drift verdicts, readiness projection, dashboard semantic-audit findings, approval-inbox items, review-integration results); it MUST NOT re-run or re-derive any shipped surface's own check.
- **FR-004**: Every summarized finding MUST cite the committed evidence (path, and row/line where applicable) it was derived from; a finding with no traceable committed source is a defect.
- **FR-005**: The "one prioritized next action per scope" MUST be selected using the SHIPPED fixed categorical rank in `readiness_classify` (`approval` > `grain` > `live_validation` > `artifact` > `readiness`) -- a committed lookup -- and MUST relay that scope's own recorded `next_action`; the system MUST NOT compute or synthesize a priority.
- **FR-006**: The summary MUST flag a scope as requiring human attention when its highest-ranked open condition is a named-human seam it cannot clear (an unmet/invalid approval, or a relayed Principle-V drift blocker), naming the responsible owner.

### Functional Requirements -- Change detection & baseline (US2)

- **FR-007**: Each run MUST persist a local prior-run snapshot (the baseline) recording the categorical state summarized that run; the snapshot MUST be a local artifact only.
- **FR-008**: A run with a usable prior snapshot MUST classify each condition as `new` (present now, absent before), `resolved` (absent now, present before), or `unchanged` (present in both), by diffing current categorical state against the snapshot.
- **FR-009**: The FIRST run (no prior snapshot), or a run whose prior snapshot is missing/unreadable, MUST mark every condition a current condition -- explicitly NOT `new` -- and state that no baseline was available to diff (the `observed=None` honesty pattern); it MUST NOT fabricate a diff.
- **FR-010**: A standing condition present across consecutive runs MUST be reported once as `unchanged` and MUST NOT be re-alerted as new (duplicate suppression).
- **FR-011**: A change in the covered scope set between runs (scope added/removed) MUST be reported as a scope-level change, not misattributed as a condition change inside a missing scope.
- **FR-012**: The change classification MUST be deterministic: identical current evidence + identical prior snapshot MUST yield identical `new`/`resolved`/`unchanged` labels.

### Functional Requirements -- Truthful degradation (US3)

- **FR-013**: A covered dimension whose evidence requires a live re-profile/DB leg that is unavailable (no DSN / no `db` extra) MUST be marked `[PENDING LIVE]`, never a fabricated comparison (consistent with `docs/readiness/source-drift.md`).
- **FR-014**: Evidence captured at a revision older than the current HEAD/`source_revision` MUST be marked `stale` (citing captured-at vs current) and MUST NOT be presented as a current condition.
- **FR-015**: A dimension with no shipped producer for a scope, or no evidence produced yet, MUST be marked `not_applicable_with_reason` (naming the reason) and MUST NOT be counted as covered or clean.
- **FR-016**: An evidence artifact declaring a schema version the feature cannot parse MUST be marked `unreadable` (naming the unknown version) and excluded from any pass/clean claim; the feature MUST NOT guess its contents.
- **FR-017**: A partial portfolio (some scopes evidenced, some empty) MUST be summarized for the covered scopes with the empty scopes listed as such; a partial state MUST NOT fail or block the whole run.

### Functional Requirements -- Governance, boundaries & fail-closed (cross-cutting)

- **FR-018**: The feature MUST be READ-ONLY and produce LOCAL ARTIFACTS ONLY in the initial version: it MUST NOT modify any project, refresh or write to any database, record/grant any approval, move any readiness stage to `pass`, run any new validator, or publish/send anywhere automatically.
- **FR-019**: The feature MUST NOT introduce a new gate, a new `retail check` rule, or a new approval mechanism -- it aggregates and summarizes, then stops (it is NOT another governance engine).
- **FR-020**: The feature MUST NOT emit any numeric health, confidence, priority, or quality score; it MUST express state only as the four readiness spine statuses (`not_started` / `blocked` / `warning` / `pass`), the shipped categorical finding enums, and measured magnitudes (counts, rates, deltas) traceable to a committed source.
- **FR-021**: No Principle-V ruling (grain, PII publish-safety, business-rollup/segment mapping, returns identity, product identity, approval sign-off) may ORIGINATE in this feature; it MUST relay such upstream conditions and name the responsible owner, deciding none of them.
- **FR-022**: The feature MUST fail closed on the run mechanics (e.g. unreadable prior snapshot -> treat as no baseline; a per-scope read error -> mark that scope's dimension `unreadable`) -- it MUST NOT convert a read/degradation failure into a fabricated pass/clean/diff.
- **FR-023**: The feature MUST be delivered agent-/skill-driven (consistent with the ratified Option-B decision and hard rule #1), with at most ONE deliberate narrow read-only machine-readable summary/status surface as a CLI addition (mirroring the `status --format json` precedent); it MUST NOT introduce a broad new CLI verb family.
- **FR-024**: Scheduling and hosted/continuous monitoring MUST be OUT of the MVP; "recurring" in the MVP MUST mean re-runnable + baseline-diffable only. Any future scheduling is a separate, later, explicitly-scoped concern.
- **FR-025**: The feature MUST stay generic (Principle VII): no worked-example specifics (billing codes, segments, PII column names, per-table grain keys) baked into the summary logic or artifacts; a worked example is a filled instance cited as a reference.

### Security & Data-Exposure Requirements

- **SEC-001**: The feature MUST NOT require or use a live database connection for the MVP summary; it operates on committed artifacts + pure-function readers only (live checks remain the deferred `retail validate` / drift-live boundary).
- **SEC-002**: No secrets, connection strings, DSNs, or real host/parameter values may appear in any produced summary or snapshot artifact; where a shipped surface would surface a boundary error, its existing redaction (e.g. `portfolio_enumerate` / dialect redaction) MUST be preserved and the summary MUST NOT reproduce an un-redacted error (consistent with the shipped `C2` / `G6` posture).
- **SEC-003**: The summary MUST NOT embed real business result values; it carries only categorical statuses, measured magnitudes already committed as evidence, and citations -- never fabricated data.
- **SEC-004**: A relayed PII-related condition (e.g. a `pii_surface_drift` blocker) MUST be relayed as an upstream blocker for the named owner; the feature MUST NOT make or record a PII publish-safety ruling.

### Key Entities

- **Portfolio Watch Summary**: the read-only, local, machine-readable + human-readable record spanning all governed scopes and covered dimensions -- per scope: stage, four-status readiness, open blockers, per-dimension categorical findings with evidence citations, human-attention flag, and one prioritized next action. Carries no score. *(New artifact type.)*
- **Prior-Run Snapshot (Baseline)**: a local artifact each run writes, recording the categorical state summarized that run, so the next run can diff against it. The one entity enabling `new`/`resolved`/`unchanged` and duplicate suppression. *(New entity; modeled on `drift.py` baseline/observed.)*
- **Condition Change Classification**: the per-condition `new` / `resolved` / `unchanged` (or first-run "current condition, no baseline") label from diffing the current summary against the snapshot. *(New; deterministic.)*
- **Governed Scope**: the existing per-table/per-report unit the readiness spine + `portfolio_enumerate` track (identified by its committed readiness-status path). *(Reused -- no new scope unit.)*
- **Covered Dimension Findings**: per-scope categorical findings for source drift / contract-semantic drift / dashboard-intent divergence / readiness / approvals / review, each sourced from the shipped surface named in the capability classification. *(Reused surface outputs, joined.)*
- **Fixed Category Rank**: the shipped `readiness_classify` rank (`approval` > `grain` > `live_validation` > `artifact` > `readiness`) used to pick the one prioritized next action per scope. *(Reused -- a committed lookup, never a computed score.)*

---

## Repository Conflicts & Drift Found *(documented, not blocking)*

Facts discovered inspecting `main`; each has a defensible default for `/speckit.plan`; none is a blocking clarification.

1. **`retail-control-room` (F012) already does a read-only cross-table roll-up** but is point-in-time (no baseline, no drift/semantic/intent dimensions). *Recommended default*: Portfolio Watch **extends** the same posture (read-only, aggregate-never-re-derive, no score) with a baseline diff + the extra dimensions; it does not fork or replace the control-room skill. Whether Watch's summary reuses the control room's roll-up as an input or composes the readers directly is a plan-time decision.
2. **Two evidence "shapes" for readiness state.** The disclosure-safe `readiness_projection` and the raw per-table `readiness-status.yaml` both exist. *Recommended default*: consume the shipped projection/readers as the summary's inputs (they already enforce disclosure + the four-status invariant); do not read raw YAML in a second, divergent way.
3. **Drift and enumeration have live legs; the summary is no-DB.** `drift.py`'s comparison needs an observed re-profile and `portfolio_enumerate` reads DB metadata. *Recommended default*: in the MVP the summary reads the **committed** drift-findings artifacts / per-scope readiness paths, and marks live-only dimensions `[PENDING LIVE]` -- it does not open a connection (SEC-001).
4. **Spec-123 intent surfaces are shipped, not paper** (verified `88daf50`/PR #261), contrary to some stale memory notes. *Recommended default*: treat `semantic_audit.py` / `report_intent.py` as shipped producers of the dashboard-intent-divergence dimension.
5. **Stale status signals.** `Status: Draft` headers and `tasks.md` checkboxes are known-unreliable in this repo. *Recommended default*: treat `docs/capabilities/capabilities.yaml` `state:` + `git log` + source paths as authoritative (as this spec did).

---

## Success Criteria *(mandatory)*

All criteria are behavioral and traceability-based -- **no numeric health/confidence/priority/quality score** is produced (per FR-020). "Measurable" here means categorically verifiable pass/fail against committed artifacts and reproducible runs.

### Measurable Outcomes

- **SC-001**: A single run produces ONE read-only summary covering every governed scope the readiness spine tracks, with each covered-dimension finding citing a committed evidence path. *(Verify: scope count in summary = scope count the spine tracks; 0 findings without a citation.)*
- **SC-002**: Zero fabricated coverage -- every dimension is either sourced from a shipped surface's committed output OR truthfully marked `[PENDING LIVE]` / `stale` / `not_applicable_with_reason` / `unreadable`. *(Verify: 0 dimensions marked covered/clean without a cited shipped source.)*
- **SC-003**: Each scope has exactly ONE prioritized next action, selected by the shipped fixed category rank and relaying that scope's own `next_action`; no synthesized priority appears. *(Verify: the chosen category = the highest-ranked open category for that scope; 0 computed priority values.)*
- **SC-004**: The first run writes a baseline and labels every condition a current condition (not `new`); a later run labels each condition `new`/`resolved`/`unchanged` by diffing the baseline. *(Verify: run-1 has 0 `new`; run-2 labels are the exact set difference/intersection against run-1's snapshot.)*
- **SC-005**: A standing condition present in two consecutive runs is reported once as `unchanged` and never re-alerted as new. *(Verify: duplicate-suppression -- 0 standing conditions labeled `new` on run-2.)*
- **SC-006**: The change classification is deterministic -- identical current evidence + identical prior snapshot yield identical labels. *(Verify: two runs on the same two states -> byte-identical change labels.)*
- **SC-007**: Every truthful-degradation case is handled per FR-013...FR-017 -- no live comparison fabricated without a DSN, no stale evidence shown as current, no unreadable schema guessed, partial portfolios summarized without failing. *(Verify: each degradation fixture yields the specified marker.)*
- **SC-008**: The feature performs no write-back -- no project modified, no DB refreshed, no approval recorded, no readiness stage moved to `pass`, nothing published. *(Verify: after a run, the only new/changed files are the summary + the local snapshot; no per-scope artifact changed.)*
- **SC-009**: No new gate, `retail check` rule, or approval mechanism is introduced; `retail check` exit behavior is unchanged. *(Verify: rule inventory unchanged; `retail check` still exits as before on the repo.)*
- **SC-010**: Every Principle-V condition (grain/returns/PII drift, unmet approval) is relayed with a named owner and decided by none; no Principle-V ruling originates in the feature. *(Verify: 0 originated rulings; each relayed condition names an owner.)*
- **SC-011**: The MVP (US1 + US2 + US3) is useful with no scheduler and no live DB -- a re-runnable, baseline-diffable, truthfully-degrading read-only summary. *(Verify: MVP slice runs end-to-end offline and produces summary + snapshot + change labels.)*
- **SC-012**: No secret, DSN, connection string, or real host/parameter value appears in any produced artifact; redaction from the shipped surfaces is preserved. *(Verify: secret-scan of the summary + snapshot is clean.)*

---

## MVP Boundary & Delivery Slices

**MVP (P1)** -- a re-runnable, baseline-diffable, truthfully-degrading read-only summary:

```
Enumerate governed scopes (spine + committed readiness paths)
 -> Join shipped-surface evidence per scope (drift / metric-drift / readiness / semantic-audit / approvals / review)
 -> Mark each dimension truthfully (covered w/ citation | [PENDING LIVE] | stale | not_applicable_with_reason | unreadable)
 -> Pick ONE next action per scope by the shipped fixed category rank
 -> Diff against the prior-run snapshot -> new / resolved / unchanged (first run: current condition, no baseline)
 -> Write the summary + a fresh local snapshot
 -> STOP (read-only; nothing published)
```

The MVP delivers standalone value with **no scheduler** and **no live DB**. It is delivered as three independently-testable P1 slices: US1 (the summary), US2 (the baseline diff), US3 (truthful degradation).

**Recommended later slices** (each independently useful; do **not** ship as one PR):

1. Broaden dimension coverage to additional shipped surfaces (US4).
2. Human-friendly rendered digest over the same machine-readable summary (US4).
3. (Separately scoped, explicitly deferred) any scheduling / continuous-monitoring surface -- a distinct future spec, not part of this feature.

---

## Non-Goals

- No new governance engine: no new gate, no new `retail check` rule, no new approval mechanism.
- No numeric health / confidence / priority / quality score.
- No write-back: no project modification, no DB refresh, no approval grant, no readiness-stage promotion, no automatic publish/send.
- No live database connection or ingestion in the MVP (live-only dimensions degrade to `[PENDING LIVE]`).
- No scheduler or hosted/continuous monitoring in the MVP.
- No originated Principle-V ruling (grain / PII / returns / rollup / identity / approval) -- relay only.
- No replacement or fork of the `retail-control-room` skill or any shipped surface; no re-derivation of a surface's own check.
- No broad new CLI verb family (agent-/skill-driven per the ratified Option-B decision; at most one narrow read-only summary/status surface).
- No worked-example specifics baked into the generic core (Principle VII).
- No implementation architecture, storage format, snapshot wire-format, or file-location decisions -- those belong to `/speckit.plan`.

---

## Assumptions

- **The readiness spine + `portfolio_enumerate` define the governed-scope set**; Portfolio Watch enumerates scopes from the committed readiness paths those already track and introduces no new scope unit (Clarifications).
- **The MVP is no-DB**: the summary reads committed evidence artifacts + pure-function readers only; live-only dimensions (drift's re-profile, any live validate leg) degrade to `[PENDING LIVE]` (SEC-001, FR-013). Whether a later slice adds an opt-in live leg is a separate concern.
- **The shipped surfaces' outputs are the inputs**: source-drift findings (`drift.py`/`drift_semantics.py`), metric-drift verdicts (`metric_drift.py`), readiness projection (`readiness_projection.py` + `readiness_classify.py`), dashboard semantic-audit + intent resolution (`semantic_audit.py` / `report_intent.py`), approval inbox (`approval_inbox.py`), review integration (`review_integration.py`). Verified shipped against `main` (capability classification).
- **The prior-run snapshot is a local artifact**; its exact storage format and location are plan-time decisions (the spec fixes only that it is local, machine-readable, per-run, and diffable, mirroring the `drift.py` baseline/observed pattern and the `observed=None` first-run honesty).
- **The next-action rank is the shipped `readiness_classify` rank** (`approval` > `grain` > `live_validation` > `artifact` > `readiness`); the spec fixes only that the priority is this committed lookup and the relayed `next_action`, never a computed score.
- **The interface is agent-/skill-driven** per the ratified Option-B decision (`docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`) and hard rule #1; the at-most-one narrow CLI addition mirrors the `status --format json` precedent (FR-023).
- **A worked example remains an example, not the schema** (Principle VII); any filled instance exercises the summary without generalizing tenant specifics into the core.
