# Feature Specification: Decision Change Impact Map

**Feature Branch**: `132-decision-change-impact-map`

**Created**: 2026-07-15

**Status**: Draft

**Input**: Owner-directed specification input (2026-07-15): "A deterministic, read-only projection showing which analytical artifacts may be affected when an approved business decision is superseded or its evidence becomes stale, including direct/transitive dependency paths, incomplete-lineage warnings, affected readiness stages, and next human review actions. It must reuse existing authorities and never create another Decision Store, readiness engine, lineage authority, approval system, or status model."

> This is a SPECIFICATION-ONLY package. The boundary below is recorded as owner-directed
> input dated 2026-07-15; the feature is NOT ratified by their presence. No runtime code, no
> CLI command, no production artifact under `src/`, `skills/`, `.claude/skills/`, `templates/`,
> `mappings/`, `contracts/`, `docs/capabilities/`, `docs/roadmap/`, or `.specify/memory/` is
> created or edited by this package. All authored bytes live under
> `specs/132-decision-change-impact-map/`. Status-header and tasks.md checkboxes are known-stale
> in this repo; the authoritative record of shipped truth is `docs/capabilities/capabilities.yaml`
> + git log + source paths.

---

## Overview

### Feature Summary

When a named human supersedes an approved business decision, or when the evidence an approved
decision cited stops matching the committed file it points at, the **downstream analytical
artifacts derived from that decision are silently at risk**. Today nothing in Seshat BI can
answer "if this decision changed, which mappings, metric contracts, gold bindings, semantic/DAX
artifacts, dashboard/PBIP artifacts, and readiness evidence may now be wrong, and what does a
human need to re-review?" The Decision Store records the supersession pointer; the decision gate
notices a decision's *own* cited evidence went stale; but neither resolves the decision's scope to
the concrete downstream artifacts that depend on it, and no shipped code walks from a decision to
the lineage graph.

This feature specifies the **Decision Change Impact Map**: one deterministic, read-only projection
that, given a superseded or evidence-stale approved decision, resolves the decision's scope to the
downstream artifacts derived from it, walks the **existing** lineage edges to name the affected
artifacts and their **direct and transitive** dependency paths, surfaces **incomplete-lineage
warnings** where a scope tag or an edge cannot be resolved, names the **affected readiness stages**,
and states the **next human review actions**. It produces the same information as both a
human-readable view and a machine-readable projection from the same committed evidence. It computes
no numeric score, changes no state, and grants no approval.

### Problem Statement

Seshat BI already owns the Decision Store (spec 121), the decision gate that classifies a decision
into pass/warn/blocked and folds a verdict onto a readiness stage, a runtime metric-to-gold lineage
edge (the explorer), a designed multi-hop artifact chain (the cross-table-lineage skill), a single
artifact-identity scheme, a readiness spine, and a disclosure-safe export pattern. What it lacks is
the **one edge that joins them**: from a *changed decision* to the *downstream artifacts derived
from it*.

Concretely, when an approved decision is superseded or its cited evidence no longer matches:

- A reviewer cannot see, in one place, which mappings / metric contracts / gold bindings / semantic
  artifacts / dashboard artifacts / readiness evidence cite or descend from that decision.
- There is no separation of *direct* impact (artifacts that reference the decision's scope
  directly) from *transitive* impact (artifacts reachable only by following one or more further
  dependency edges).
- A scope tag that resolves to **no** artifact today reads as "nothing affected," which is a
  dangerous false negative: absence of a discovered reference is not proof of no impact.
- There is no truthful, evidence-backed statement of which readiness stages the change touches or
  what the next human action is — without fabricating a confidence, risk, or "blast-radius" number.

Without this projection, a superseded decision propagates into semantic models, dashboards, and
published reports as an unreviewed change, and the human who must re-confirm has no map of what to
look at.

### Product Goal

Give any Seshat BI reviewer a **truthful, deterministic, offline map of what a decision change may
have affected** — assembled entirely from committed evidence, reusing every existing authority —
so that a superseded or evidence-stale approved decision can be re-reviewed against a concrete list
of affected artifacts, dependency paths, incomplete-lineage warnings, affected readiness stages,
and next human actions, and so that the projection is trustworthy precisely because it never
guesses an edge, never treats "no reference found" as "unaffected," never computes a score, and
never changes any state.

### Primary Actors

- **Reviewer / approver** (agent-driven): the named human who is deciding whether a decision change
  is safe, and who reads the impact map before re-confirming or re-superseding. Owns the review
  action; the map informs it, never performs it.
- **Data owner / governance**: the authority who supersedes a critical decision and needs to see
  its downstream reach before and after doing so.
- **The agent**: the runtime. It composes the projection from committed artifacts, presents both
  the human and machine-readable forms, and STOPS at the review action. It never supersedes,
  approves, re-validates, or writes any state.
- **Seshat governance layer**: the Decision Store, decision gate, lineage authorities, readiness
  spine, and disclosure scanner that this feature reads from and never mutates.

### Relationship to Already-Shipped Capabilities (no-duplicate check)

This feature is a **new read-only projection layer** that composes existing authorities. It
introduces **no** new Decision Store, no new readiness/state engine, no new readiness spine stage,
no new lineage authority, no new approval/status model, and no new numeric score. Adversarial
verification (an independent reviewer instructed to *prove* the boundary already exists, defaulting
to "duplicate") could not sustain the duplicate argument: the decision → downstream-artifact edge
exists in no shipped code, and no capabilities-ledger entry or roadmap feature claims it.

| Already on main (do NOT rebuild) | Where it lives (evidence) | This feature's relationship |
| --- | --- | --- |
| **Decision Store** — decision records, the 9-status lifecycle, `supersedes` / `superseded_by` pointer fields, scope tags, cited evidence + `evidence_identity`, approval metadata, fail-closed loader, static rules DS1–DS5 (incl. DS4 supersession referential integrity) | `src/seshat/decision_store.py`, `src/seshat/rules/decision_store.py`, spec 121 (capability `business-knowledge-interview`) | REUSE as the ONLY decision store and the source of the supersession pointer chain and scope tags this feature reads. It records nothing new here. |
| **Decision gate** — pass/warn/blocked classification, superseded→settled handling, cited-evidence staleness detection, and the flow-stage→spine-stage projection (`project_to_spine`), never a write | `src/seshat/decision_gate.py`, spec 121 | REUSE as the source of the evidence-staleness signal and the affected-readiness-stage mapping. This feature reads the same signals; it adds no second gate and computes no second verdict. |
| **Artifact identity** — the single `kind:path` + content-hash identity scheme and sandbox-safe path resolution | `src/seshat/artifact_identity.py` | REUSE as the ONLY artifact-identity scheme for every resolved downstream artifact. This feature invents no new identity scheme. |
| **Readiness spine** — the seven ordered stages, the four status words, evidence/blocking-reasons shape, and the read-only disclosure-safe projection over them | `src/seshat/readiness_projection.py`, `src/seshat/rules/readiness_status.py`, readiness model docs | REUSE as the ONLY readiness engine and stage/status vocabulary. This feature names affected stages by reading this projection; it defines no stage, writes no `readiness-status.yaml`, and adds no status word. |
| **Blocker category / next-surface authority** — the fixed blocker-category rank and category→explanation→next-surface mapping shared by the blocker explainer and approver view | `src/seshat/readiness_classify.py` (capabilities `retail-blockers`, `retail-approver-view`) | REUSE as the ONLY source of "next human review action" phrasing and category ranking. This feature re-derives no category rules. |
| **Runtime metric→gold lineage edge** — the single-hop `metric_contract → warehouse_table` (`binds_to`) edge and its node/edge vocabulary | `src/seshat/explorer/build.py` (capability `seshat-readiness-explorer`, roadmap F026) | REUSE as the runtime lineage edge and the canonical lineage-node vocabulary. This feature adopts that vocabulary; it does not invent a competing one. |
| **Cross-table lineage** — the designed multi-hop artifact chain (source-map → migration SQL → metric contract → TMDL measure → dashboard visual) with proven/unresolved/gap tiering | `.claude/skills/cross-table-lineage/SKILL.md` (capability `cross-table-lineage`, roadmap F036) | REUSE its hop definitions and its proven/unresolved/gap tiering vocabulary for the transitive-path and incomplete-lineage portions. This feature does not re-adjudicate lineage or ship a second traversal that disagrees with it. |
| **Disclosure scanner + contained output + human/machine output pattern** — the fail-closed recursive secret/PII/path scanner, the contained output-root guard, and the "build a dict → render/print the same dict, scan before writing" pattern | `src/seshat/disclosure.py`, `src/seshat/cli/guards.py`, `src/seshat/passport.py`, `src/seshat/explorer/build.py` (capabilities `seshat-passport`, `seshat-readiness-explorer`) | REUSE as the disclosure-safety, containment, and dual-output mechanism. This feature adds no new disclosure rule and no new output surface convention. |
| **HR9 rename-impact orphaned-reference guard** — a static, single-hop, name-resolution check over committed TMDL that never touches decisions, supersession, or readiness | `src/seshat/rules/rename_impact_guard.py` | NOT this feature. HR9 answers "does this cited NAME still resolve in the current TMDL?"; it has no decision graph, no supersession trigger, and no readiness interaction. It shares only the coincidental word "impact." No reuse required; distinctness recorded to close the no-duplicate gate. |
| **HR-family / semantic drift / grain-confidence-diff / portfolio-watch** — contract-drift, mapping-version-diff, and cross-signal roll-up capabilities | `retail-semantic-check`, `retail-drift`, `grain-confidence-reviewer`, `portfolio-watch` | REFERENCE only. None is triggered by a decision supersession, and none projects a decision → downstream-artifact dependency path. Their diff/baseline patterns are adjacent prior art, not the affected-artifact traversal. |

Genuinely NEW in this feature: **(1)** the resolution of a changed decision's scope to the concrete
downstream artifacts derived from it; **(2)** the deterministic walk of the existing lineage edges
producing separated direct and transitive dependency paths; **(3)** the incomplete-lineage warning
whenever a scope tag or an edge cannot be resolved (so "no reference found" is never reported as
"unaffected"); **(4)** the assembly of affected readiness stages and next human review actions for
the change; **(5)** the single read-only projection dict and its human/machine renderings. Every
underlying store, gate, identity, lineage edge, readiness engine, and disclosure mechanism is
reused.

---

## Clarifications

### Session 2026-07-15 (owner-directed boundary decisions D1–D8)

- Q: Does this feature add a Decision Store, readiness engine, lineage authority, approval system, or status model? → A: No. It is a read-only projection that composes existing authorities. It reads the Decision Store, the decision gate's staleness/stage signals, the existing lineage edges, the readiness projection, and the disclosure scanner; it creates none of them and mutates none of them. (D1; FR-001, FR-002, FR-024, FR-025)
- Q: What does "preserve supersession history" mean, given the store holds only `supersedes` / `superseded_by` scalar pointers and no version log? → A: "History" is the **existing supersession pointer chain** read from the store and presented in order — never a new history model, version log, or diff structure (that would be a second store or a mutation). Where the chain is partial or a pointer does not resolve, that surfaces as an incomplete-lineage warning, never fabricated history. (D2; FR-006, FR-016, EDGE, Assumptions)
- Q: What triggers an impact map? → A: One of exactly two committed, decision-provenance conditions on an **approved** decision: (a) the decision is superseded (its `status` is `superseded`, or it is the target of another record's `supersedes`), or (b) its cited evidence is stale (a cited evidence file's current content identity no longer matches the identity recorded at approval). Both may be previewed for a not-yet-superseded decision ("what would be affected if I superseded this"). No live database or Power BI connection is a trigger or an input. (D3; FR-003, FR-004, FR-005)
- Q: Direct vs transitive impact — how separated? → A: The projection MUST label each affected artifact as **direct** (it references the changed decision's scope directly) or **transitive** (it is reachable only by following one or more further dependency edges from a direct artifact), and MUST record the evidence path for every edge it traversed. (D4; FR-009, FR-010, FR-011)
- Q: How is "no reference found" handled? → A: Never as proof of "unaffected." A scope tag that resolves to zero artifacts, or a lineage edge that cannot be followed, MUST produce an explicit **incomplete-lineage warning** naming the unresolved tag/edge; the projection MUST NOT silently drop it and MUST NOT infer an edge to fill the gap. (D5; FR-012, FR-013, SC-004)
- Q: What about cycles in the dependency graph? → A: The walk MUST detect a cycle, record it as a named condition, and terminate without re-traversing — it MUST NOT loop indefinitely and MUST NOT report a cycle as a completed transitive path. (D6; FR-014, SC-006)
- Q: Any numeric confidence / risk / trust / completeness / blast-radius score? → A: None, anywhere. Affected/at-risk state is expressed as named artifacts + evidence paths + reused readiness statuses + reused blocker categories only. No percentage, count-as-score, ranking, or synthesized number is emitted. (D7; FR-023, SC-005)
- Q: CLI, UI, or agent surface, and how much? → A: No new broad CLI family, no new web UI, no new readiness stage. The durable outputs are the committed projection artifact(s) and their human/machine renderings, produced by the agent reusing the existing disclosure-safe, contained-output pattern; the exact single surface (skill vs one narrow verb) is a plan-time decision constrained to the smallest addition. (D8; FR-021, FR-022, Non-Goals)

### Session 2026-07-15 (`/speckit.clarify` ambiguity scan)

A structured ambiguity & coverage scan across the full taxonomy (functional scope, domain/data model,
interaction/UX, non-functional attributes, integration/dependencies, edge cases, constraints/tradeoffs,
terminology, completion signals, placeholders) found **no critical ambiguity that would block planning**.
The load-bearing interpretive gap ("preserve supersession history" against a pointer-only substrate) was
resolved during `/speckit.specify` as decision D2 (FR-006). All other taxonomy categories are Clear or
not applicable to a read-only, offline, committed-artifacts projection (no live integration, no new UI,
no scale/latency target, no new persistence).

- Q: Which wire format (YAML vs JSON) should the machine-readable projection use? → A: Deferred to `/speckit.plan`. This is a plan-level execution detail that does not block correctness — every FR/NFR/SC is satisfiable in either format (the disclosure scan, determinism, and dual-rendering requirements are format-independent). Recorded in Assumptions; not a spec-level decision.

No spec requirements were changed by this scan (no answer materially altered scope, data model, test design, or acceptance criteria beyond what D1–D8 already fixed).

---

## User Scenarios & Testing *(mandatory)*

Actors: reviewer/approver (agent-driven), data owner/governance, the agent, the Seshat governance layer.

### User Story 1 - Map the direct impact of a changed decision (Priority: P1 — MVP)

A reviewer selects an approved decision that has been superseded (or whose cited evidence is stale)
and asks what it may have affected. The agent produces an impact map naming every **direct**
downstream artifact — the mappings, metric contracts, gold bindings, semantic/DAX artifacts,
dashboard/PBIP artifacts, and readiness evidence that reference the changed decision's scope
directly — with the evidence path that establishes each reference, the affected readiness stage(s),
and the next human review action. Every result carries its evidence path; nothing is asserted
without one.

**Why this priority**: Direct impact is the smallest truthful, independently valuable slice — it
answers "what points straight at this decision?" without any transitive walk. Every other story
builds on the same resolution and evidence-path discipline. This is the MVP core.

**Independent Test**: Provide a fixture Decision Store containing one approved-then-superseded
decision and fixture downstream artifacts, some of which cite the decision's scope. Request the
impact map; confirm each directly-citing artifact appears exactly once, labeled `direct`, with a
resolvable evidence path; confirm the affected readiness stage is read from the existing readiness
projection (not invented); confirm the next action is drawn from the existing blocker-category
authority; confirm no numeric score appears and no state file is written.

**Acceptance Scenarios**:

1. **Given** an approved decision with `status: superseded` and a metric contract whose scope tag matches the decision's scope, **When** the impact map is produced, **Then** the metric contract appears labeled `direct`, with the evidence path to the citing artifact and the affected readiness stage named from the readiness projection.
2. **Given** an approved decision whose cited evidence file's current content identity no longer matches the identity recorded at approval, **When** the impact map is produced, **Then** the decision is included as evidence-stale (via the existing staleness signal), and its directly-derived artifacts are listed with evidence paths.
3. **Given** the same run, **When** the human view and the machine view are produced, **Then** both present the identical set of affected artifacts, labels, evidence paths, stages, and next actions from the same committed evidence.
4. **Given** any produced impact map, **When** it is inspected, **Then** it contains no numeric confidence/risk/trust/completeness/blast-radius value and no readiness-status file, decision record, or approval was written or changed.

---

### User Story 2 - Separate transitive impact and warn on incomplete lineage (Priority: P1 — MVP)

Building on the direct set, the agent follows the **existing** dependency edges to name the
**transitive** artifacts reachable only through one or more further hops, labeling them distinctly
from direct impact and recording the evidence path for every edge traversed. Wherever a scope tag
resolves to no artifact, or a lineage edge cannot be followed, the agent emits an explicit
**incomplete-lineage warning** naming the unresolved tag or edge — it never treats an unresolved
reference as "unaffected" and never fabricates an edge to close the gap.

**Why this priority**: Transitive reach and honest incompleteness are what make the map trustworthy
rather than a false-negative generator. This is the counterintuitive core of the feature and is
co-equal with US1 in the MVP: a direct-only map that silently drops unresolved tags would be
actively misleading.

**Independent Test**: Provide fixtures where (a) a direct artifact is itself referenced by a further
artifact (a transitive hop), (b) a decision scope tag resolves to zero artifacts, and (c) a lineage
edge points at a missing target. Request the impact map; confirm the transitive artifact is labeled
`transitive` with the full evidence-path chain of edges; confirm the zero-resolution scope tag and
the missing-target edge each produce a named incomplete-lineage warning; confirm neither is silently
dropped and no edge was inferred to fill either gap.

**Acceptance Scenarios**:

1. **Given** a direct metric contract that a dashboard artifact depends on through an existing lineage edge, **When** the transitive walk runs, **Then** the dashboard artifact appears labeled `transitive` with the ordered evidence paths of every edge from the decision to it.
2. **Given** a decision scope tag that resolves to no committed artifact, **When** the map is produced, **Then** an incomplete-lineage warning names the unresolved scope tag and the map does NOT record "no impact" for it.
3. **Given** a lineage edge whose target artifact is missing from the committed tree, **When** the walk reaches it, **Then** an incomplete-lineage warning names the unresolvable edge and the walk continues without inferring a substitute target.
4. **Given** a mix of resolvable and unresolvable references in one run, **When** the map is produced, **Then** resolvable artifacts are listed with direct/transitive labels AND every unresolvable reference is listed as an incomplete-lineage warning — the two sets are both present and never conflated.

---

### User Story 3 - Preview impact before superseding, and read the supersession chain (Priority: P2)

A data owner considering whether to supersede an approved decision asks for the impact map **before**
making the change, to see the reach first. The same projection runs against the not-yet-superseded
decision as a preview. When a decision is (or would be) superseded, the map presents the **existing
supersession pointer chain** (`supersedes` / `superseded_by`) in order, so a reviewer can read what
this decision replaced and what replaced it — reading the pointers already in the store, never
constructing a new history model. A pointer that does not resolve surfaces as an incomplete-lineage
warning, not fabricated history.

**Why this priority**: Preview and chain-reading are high-value for safe change management but sit on
top of the US1/US2 resolution machinery, so P2. Each is independently testable against fixture
decisions.

**Independent Test**: Provide a fixture chain of decisions linked by `supersedes` / `superseded_by`,
including one dangling pointer. Request a preview impact map for a decision not yet superseded and a
map for a superseded decision; confirm the preview produces the same affected-artifact structure
without any state change; confirm the supersession chain is presented in pointer order; confirm the
dangling pointer yields an incomplete-lineage warning and no invented history entry.

**Acceptance Scenarios**:

1. **Given** an approved decision that has not been superseded, **When** a preview impact map is requested, **Then** the projection lists the artifacts that would be affected if it were superseded, and no decision record, supersession pointer, or approval is written.
2. **Given** a superseded decision with a resolvable `supersedes` pointer to a prior record, **When** the map is produced, **Then** the supersession chain is presented in order using the store's existing pointer fields.
3. **Given** a `superseded_by` (or `supersedes`) pointer that does not resolve to a real decision id, **When** the map is produced, **Then** an incomplete-lineage warning names the dangling pointer and no history entry is fabricated for it.

---

### User Story 4 - Fail closed on malformed, absent, or incomplete evidence (Priority: P2)

When the Decision Store is absent, malformed, or internally conflicting; when the flow/lineage
inputs are unreadable; or when required evidence is missing, the impact map fails closed. It does
not crash, does not emit a live-DB traceback, does not fabricate an empty "nothing affected" result,
and does not report a resolvable-looking answer built on unreadable inputs. It names the blocking
condition and, where partial resolution is possible, marks the unresolved portions as
incomplete-lineage warnings rather than dropping them.

**Why this priority**: Fail-closed behavior is what keeps the projection safe to trust under the
exact conditions (drift, missing files, malformed store) that motivate running it, so it is a
first-class P2 rather than an afterthought. It is independently testable by degrading each input.

**Independent Test**: Independently (a) remove the Decision Store, (b) corrupt it into a load
problem, (c) introduce a conflicting active-scope pair, (d) make a lineage input unreadable, and (e)
remove a cited evidence file; for each, confirm the projection reports the blocking condition
without crashing, without a numeric score, without writing state, and without reporting a clean
"no impact" that hides the failure.

**Acceptance Scenarios**:

1. **Given** no Decision Store present, **When** an impact map is requested, **Then** the projection reports the absent-store condition (reusing the store's fail-closed load behavior) and does not report "no artifacts affected."
2. **Given** a Decision Store that fails to load (malformed YAML / load problem), **When** an impact map is requested, **Then** the projection fails closed and names the store problem, writing nothing.
3. **Given** two active in-scope decisions of the same type conflicting on the same scope key, **When** an impact map is requested, **Then** the projection surfaces the conflict (reusing the existing active-scope-conflict signal) and does not silently pick one.
4. **Given** a cited evidence file that has been removed, **When** the map is produced, **Then** the missing evidence is named as an incomplete-lineage warning and the map does not report a resolvable path through it.

---

### User Story 5 - Produce reviewable human and machine-readable projections (Priority: P3)

The agent produces the impact map in two forms from the same committed evidence: a machine-readable
projection (deterministically ordered, disclosure-scanned, containing artifact identities, direct/
transitive labels, evidence paths, incomplete-lineage warnings, affected stages, next actions, and
the supersession chain) and a human-readable rendering of the identical content. Both are scanned by
the existing disclosure scanner before being written, and both are contained to the existing output
root. Neither contains raw PII, a connection string, or a credential.

**Why this priority**: Dual reviewable output completes the deliverable but sits atop the resolution
and fail-closed machinery, so P3. Independently testable by producing both forms and diffing their
content.

**Independent Test**: Produce both forms for a fixture with a known affected set; confirm the human
and machine forms carry the identical affected artifacts, labels, evidence paths, warnings, stages,
and next actions; confirm deterministic ordering (a re-run yields byte-identical machine output for
identical committed inputs, modulo an explicit generated-at field); confirm the disclosure scan runs
before any write and blocks on any secret/PII/connection-string finding; confirm both forms are
written only under the contained output root.

**Acceptance Scenarios**:

1. **Given** a fixture affected set, **When** both forms are produced, **Then** the human-readable and machine-readable forms present the identical affected artifacts, labels, evidence paths, warnings, stages, and next actions.
2. **Given** identical committed inputs, **When** the machine-readable projection is produced twice, **Then** the two outputs are byte-identical except for an explicit generated-at field.
3. **Given** a document that would contain a secret/PII/connection-string value, **When** the projection is produced, **Then** the existing disclosure scanner blocks the write and the failure is reported.
4. **Given** any produced form, **When** the write target is inspected, **Then** it lies under the existing contained output root and nowhere else.

---

### Edge Cases

- **Scope tag resolves to nothing**: emit an incomplete-lineage warning naming the tag; never record "unaffected" (D5, FR-012).
- **Lineage edge target missing**: incomplete-lineage warning naming the edge; continue without inferring a substitute (D5, FR-013).
- **Cycle in the dependency graph**: detect, record as a named condition, terminate; never loop, never report the cycle as a completed transitive path (D6, FR-014).
- **Dangling supersession pointer** (`supersedes` / `superseded_by` does not resolve): incomplete-lineage warning; no fabricated history entry (D2, FR-016).
- **Decision never approved** (still `proposed`/`pending`, or the id resolves to no approved decision): the map applies only to *approved* decisions. A non-approved subject yields a `blocking_condition` of kind `invalid_subject` (with `subject: null`), reported as *not a valid impact-map subject* — never a `subject` carrying a made-up trigger and never "no impact" (FR-003).
- **Superseded decision whose replacement is itself superseded**: present the full pointer chain in order; each unresolved link is its own incomplete-lineage warning.
- **Evidence-stale but not superseded**: a valid trigger (D3); the map runs on the staleness signal alone.
- **Conflicting active in-scope decisions**: surface the conflict (reuse the existing signal); do not silently choose one (US4).
- **Absent / malformed Decision Store**: fail closed with the condition named; never a clean "no impact" (US4).
- **Same artifact reached by more than one path from the subject**: the map is single-subject (one changed decision per run), so an artifact is listed **once**; if multiple dependency paths from that subject reach it, the additional paths are recorded within its ordered `evidence_paths` chain — never duplicated as separate affected entries.
- **Same artifact reachable both directly and transitively**: labeled `direct` (the stronger relation) with the transitive path(s) also recorded as evidence; never double-counted as two affected artifacts.
- **Decision scope names a gold-only object vs a silver/bronze object**: resolution follows the existing gold-only lineage edges; a reference into `silver`/`bronze` is out of the readable lineage surface and, if cited, is an incomplete-lineage warning, not an inferred edge.
- **No lineage edges exist yet for a table** (e.g. metric contracts but no model): direct references are still listed; the absent transitive edges are incomplete-lineage warnings, never "no transitive impact."
- **PII-bearing evidence path**: only repo-relative paths/identities are recorded; the disclosure scanner blocks any raw PII/secret/connection-string leak before write (SEC-001..SEC-003).
- **Live DB / Power BI unavailable**: never a trigger or input; the projection is computed only from committed artifacts, so unavailability changes nothing (D3, NFR-004).

---

## Requirements *(mandatory)*

### Functional Requirements — Boundary and reuse (D1)

- **FR-001**: The feature MUST be a read-only projection that composes existing authorities and MUST NOT introduce a second Decision Store, a second readiness/state engine, a second lineage authority, a second approval system, or a second status model.
- **FR-002**: The feature MUST read the changed-decision signals and downstream references only from committed artifacts (the Decision Store, cited evidence identities, the existing lineage edges/definitions, the readiness projection, and the flow/lineage inputs those authorities already consume); it MUST NOT require or use a live database or a Power BI connection.

### Functional Requirements — Trigger (US1, US3; D3)

- **FR-003**: The impact map MUST apply to an **approved** decision and MUST support exactly three trigger modes: (a) **superseded** — the decision is superseded; (b) **evidence_stale** — its cited evidence is stale (a cited evidence file's current content identity no longer matches the identity recorded at approval); and (c) **preview** — an explicit reviewer-initiated request against a not-yet-superseded, non-stale approved decision (FR-004), which projects "what would be affected if this were superseded" and is marked `is_preview: true`. Modes (a) and (b) are the two *committed* conditions detected from state; mode (c) is an explicit request and requires no committed change condition. The map MUST NOT run on an unapproved decision (it is reported as not a valid subject, not as "no impact").
- **FR-004**: The feature MUST support producing the map as a **preview** for a not-yet-superseded approved decision (what would be affected if it were superseded) without changing any state.
- **FR-005**: The feature MUST detect the evidence-stale condition using the existing cited-evidence staleness signal and the existing artifact-identity scheme; it MUST NOT define a second staleness or identity mechanism.

### Functional Requirements — Supersession chain / history (US3; D2)

- **FR-006**: Where a decision is (or would be) superseded, the map MUST present the **existing** supersession pointer chain read from the store's `supersedes` / `superseded_by` fields, in order; it MUST NOT construct a new history model, version log, or diff structure, and MUST NOT write any supersession pointer.

### Functional Requirements — Downstream resolution and dependency paths (US1, US2; D4)

- **FR-007**: Given a changed decision, the feature MUST resolve the decision's scope to the concrete downstream artifacts derived from it across the artifact chain: mappings/model plans → metric contracts → gold bindings → semantic/DAX artifacts → dashboard/PBIP artifacts → readiness evidence.
- **FR-008**: Every affected artifact and every traversed edge in the map MUST carry a resolvable **evidence path** (a repo-relative reference to the committed artifact that establishes the reference/edge); no affected artifact may be asserted without one.
- **FR-009**: The map MUST label each affected artifact as **direct** (it references the changed decision's scope directly) or **transitive** (reachable only by following one or more further dependency edges).
- **FR-010**: The map MUST separate the direct-impact set from the transitive-impact set so a reviewer can read each independently.
- **FR-011**: The transitive walk MUST follow only the **existing** lineage edges/definitions (the runtime metric→gold edge and the designed cross-table hops), reusing their hop definitions and node/edge vocabulary; it MUST NOT invent a new lineage vocabulary or a divergent traversal that disagrees with the shipped lineage on which hops are resolvable.

### Functional Requirements — Incomplete lineage and "no reference ≠ unaffected" (US2; D5)

- **FR-012**: A decision scope tag that resolves to **no** committed artifact MUST produce an explicit **incomplete-lineage warning** naming the unresolved tag; the feature MUST NOT record it as "unaffected" and MUST NOT drop it silently.
- **FR-013**: A lineage edge that cannot be followed (missing or unreadable target) MUST produce an explicit incomplete-lineage warning naming the unresolvable edge; the feature MUST NOT infer or substitute an edge to fill the gap.
- **FR-015**: The map MUST present resolvable affected artifacts and incomplete-lineage warnings as two distinct, both-present result sets; it MUST NOT conflate an unresolved reference with a resolved one or vice versa.

### Functional Requirements — Cycles (US2; D6)

- **FR-014**: The dependency walk MUST detect a cycle, record it as a named condition, and terminate without re-traversing; it MUST NOT loop indefinitely and MUST NOT report a cycle as a completed transitive path.

### Functional Requirements — Dangling supersession pointer (US3; D2)

- **FR-016**: A `supersedes` / `superseded_by` pointer that does not resolve to a real decision id MUST produce an incomplete-lineage warning; no history entry may be fabricated for it.

### Functional Requirements — Affected readiness stages and next actions (US1; D1)

- **FR-017**: The map MUST name the affected readiness stage(s) for the change by reading the existing read-only readiness projection and the existing flow-stage→spine-stage mapping; it MUST NOT define a new readiness stage, write `readiness-status.yaml`, or otherwise change readiness state.
- **FR-018**: The map MUST state the next human review action(s) for the change using the existing blocker-category / next-surface authority; it MUST NOT re-derive category rules or invent a new next-action vocabulary.

### Functional Requirements — Fail-closed behavior (US4)

- **FR-019**: When the Decision Store is absent, malformed, or reports a load problem, the feature MUST fail closed — report the condition and write nothing — and MUST NOT report a clean "no artifacts affected" that hides the failure.
- **FR-020**: When active in-scope decisions conflict on the same scope key, the feature MUST surface the conflict using the existing active-scope-conflict signal and MUST NOT silently select one.

### Functional Requirements — Output surface and dual rendering (US5; D8)

- **FR-021**: The feature MUST produce the map as both a machine-readable projection and a human-readable rendering of the **identical** content from the same committed evidence.
- **FR-022**: The feature MUST reuse the existing disclosure-safe, contained-output pattern: the machine-readable projection MUST be scanned by the existing disclosure scanner before any write, and every written form MUST be contained to the existing output root. The feature MUST NOT add a new broad CLI command family, a new web UI, or a new readiness stage.

### Functional Requirements — No score (all stories; D7)

- **FR-023**: No artifact or rendering the feature produces MAY contain a numeric confidence, risk, trust, completeness, or blast-radius score, a percentage, a ranking, or any synthesized number expressing "how affected" something is; affected/at-risk state MUST be expressed only as named artifacts, evidence paths, reused readiness statuses, and reused blocker categories.

### Functional Requirements — No mutation, execution, or approval (all stories; D1)

- **FR-024**: The feature MUST NOT execute a transformation, repair, rewrite, approve, invalidate, publish, supersede, re-validate, or change readiness state; it reads and projects only.
- **FR-025**: The feature MUST NOT be the authority on whether a decision or stage passed; it reads existing verdicts/statuses and never grants, advances, or fabricates one (Constitution Principles I and V).

### Non-Functional Requirements

- **NFR-001** (Determinism): For identical committed inputs, the machine-readable projection MUST be byte-identical across runs except for an explicit generated-at field; all collections (affected artifacts, edges, warnings, chain entries) MUST use an explicit, stable ordering (e.g. sorted by artifact identity/path/id), mirroring the passport/explorer determinism guarantees.
- **NFR-002** (Offline-capable): The projection MUST be computable with no network, no live database, and no Power BI/desktop process — committed text only.
- **NFR-003** (Disclosure-safe): The machine-readable projection MUST pass the existing fail-closed disclosure scan before being written; a secret/PII/connection-string/absolute-path/raw-value finding MUST block the write.
- **NFR-004** (Fail-closed): Malformed, absent, or unreadable inputs MUST degrade to a reported blocking condition or a named incomplete-lineage warning — never a crash, a live-DB traceback, or a false clean result.
- **NFR-005** (Generic): The projection MUST remain generic across any retail workspace and MUST NOT embed a worked example's table names, column names, policies, numbers, client names, or named humans as defaults.
- **NFR-006** (Single-vocabulary lineage): The feature MUST adopt one existing lineage-node identifier vocabulary and MUST NOT introduce a further, unreconciled metric/artifact-identity scheme.

### Security / PII Requirements

- **SEC-001**: No artifact or rendering the feature produces MAY contain raw PII; only repo-relative paths and identities may be recorded.
- **SEC-002**: No artifact MAY contain a connection string, credential, or DSN; connection details remain parameters per Constitution Principle IX.
- **SEC-003**: Evidence references MUST be repo-relative paths/ids matching the existing artifact-identity scheme, never embedded secret or raw-PII values, and the disclosure scan MUST be the enforced gate on this.

### Key Entities

- **ChangedDecision**: an existing Decision Store record of an approved decision that is superseded or evidence-stale, read (never written) as the impact-map subject. *(Reused; spec 121.)*
- **SupersessionChainView**: the ordered presentation of the store's existing `supersedes` / `superseded_by` pointers for the subject decision. *(Reused pointers; new read-only view.)*
- **AffectedArtifact**: one downstream artifact resolved from the changed decision, carrying its existing artifact identity, a direct/transitive label, and the evidence path(s) establishing its dependency. *(New projection entry over reused identities/edges.)*
- **DependencyEdge**: one traversed lineage edge from the existing lineage authorities. It is **not** a separate top-level collection in the projection; each traversed edge is represented by its evidence path within the reached artifact's `evidence_paths` chain (a transitive artifact carries the full ordered chain of the edges from the decision to it). *(Reused edge vocabulary; represented as evidence paths, not a distinct `edges[]` array.)*
- **IncompleteLineageWarning**: one named unresolved scope tag, unfollowable edge, or dangling supersession pointer. *(New.)*
- **AffectedReadinessStage**: an affected stage named from the existing readiness projection and flow→spine mapping. *(Reused.)*
- **NextReviewAction**: a next human action drawn from the existing blocker-category / next-surface authority. *(Reused.)*
- **ImpactMapProjection**: the single deterministic, disclosure-scanned dict composing all of the above, with a human-readable rendering of the identical content. *(New.)*

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a fixture superseded (or evidence-stale) approved decision and directly-citing fixture artifacts, the impact map lists every directly-citing artifact exactly once, labeled `direct`, each with a resolvable evidence path. *(Verify: fixture run + structural scan.)*
- **SC-002**: Given a transitive dependency chain in fixtures, the map lists the transitively-reachable artifact labeled `transitive` with the ordered evidence paths of every edge traversed, and never labels a transitive-only artifact `direct`. *(Verify: fixture run.)*
- **SC-003**: Given a decision scope tag resolving to zero artifacts and a lineage edge with a missing target, the map emits a named incomplete-lineage warning for each and records neither as "unaffected"; a diff of "resolvable artifacts" vs "incomplete-lineage warnings" shows both non-empty and disjoint. *(Verify: fixture run.)*
- **SC-004**: There is no run in which an unresolved scope tag or unfollowable edge is silently absent from the output — every unresolved reference is present as an incomplete-lineage warning. *(Verify: fixture matrix over the unresolved cases.)*
- **SC-005**: No artifact or rendering the feature produces contains a numeric confidence/risk/trust/completeness/blast-radius value — verified by the absence of any digit-immediately-followed-by-`%` token and the absence of any of the forbidden keys `score`/`confidence`/`risk`/`risk_score`/`trust`/`completeness`/`blast_radius`/`weight` in the machine-readable projection. *(Verify: SL1-style structural scan, mirroring spec 124 SC-003.)*
- **SC-006**: Given a cyclic fixture dependency graph, the walk terminates, records the cycle as a named condition, and produces a bounded output (no infinite loop, no cycle reported as a completed transitive path). *(Verify: fixture run with a bounded-time assertion.)*
- **SC-007**: Given a fixture supersession pointer chain including a dangling pointer, the map presents the resolvable chain in pointer order and emits an incomplete-lineage warning for the dangling pointer with no fabricated history entry. *(Verify: fixture run.)*
- **SC-008**: Under each degraded input independently (absent store, malformed store, active-scope conflict, unreadable lineage input, removed cited evidence), the map reports the blocking condition or a named incomplete-lineage warning, writes no state file, emits no numeric score, and never reports a clean "no impact". *(Verify: fixture matrix, degrading one input at a time.)*
- **SC-009**: The human-readable and machine-readable forms of the same run carry the identical set of affected artifacts, labels, evidence paths, warnings, affected stages, and next actions. *(Verify: content diff of the two forms.)*
- **SC-010**: For identical committed inputs, the machine-readable projection is byte-identical across two runs except for an explicit generated-at field. *(Verify: double-run byte diff.)*
- **SC-011**: No artifact the feature produces contains raw PII, a connection string, or a credential; a document that would contain one is blocked by the existing disclosure scan before write. *(Verify: disclosure-scan fixture, reusing the existing C2/SEC posture.)*
- **SC-012**: No worked-example table name, column name, policy, number, client name, or named human appears in any generic artifact the feature produces (fixtures may carry example values but they never become defaults). *(Verify: no-leak scan against the enumerated worked-example token list.)*
- **SC-013**: The no-duplicate boundary holds — no second Decision Store, readiness engine, lineage authority, approval system, status model, readiness stage, numeric score, broad CLI family, or web UI is introduced; every underlying authority is reused. *(Verify: a no-duplicate check task enumerating the reused authorities and asserting no new authority module is created.)*

---

## MVP Boundary and Delivery Slices

**MVP = US1 + US2** (both P1): the direct-impact map with evidence paths, affected readiness stages,
and next actions, plus the transitive walk with distinct labeling and honest incomplete-lineage
warnings. This pair is independently valuable (a truthful "what did this decision change touch"
map that never reports a false "unaffected") and independently testable without US3–US5.

Later slices: **US3** (preview + supersession-chain reading, P2), **US4** (fail-closed on
malformed/absent/incomplete evidence, P2), **US5** (dual human/machine reviewable output, P3).

---

## Non-Goals

This feature MUST NOT:

- Introduce a second Decision Store, a second readiness/state engine, a second lineage authority, a second approval system, or a second status model.
- Add a new readiness spine stage.
- Execute, repair, rewrite, approve, invalidate, publish, supersede, or re-validate anything.
- Change readiness state or write `readiness-status.yaml`, a decision record, an approval, or a supersession pointer.
- Emit a numeric confidence, risk, trust, completeness, or blast-radius score, a percentage, or a ranking.
- Use a graph database or any new persistent graph engine.
- Add a new web UI.
- Add a new broad CLI command family.
- Require or use a live database or a Power BI connection.
- Generate or modify DAX, SQL, TMDL, PBIR, or any transformation.
- Construct a new supersession history/version-log model (only the existing pointer chain is read).
- Introduce a fourth metric/artifact-identity vocabulary or a lineage traversal that disagrees with the shipped lineage on which hops are resolvable.
- Perform an unrelated refactor of the Decision Store, decision gate, readiness spine, lineage, or disclosure code.
- Treat any worked example as a product default.

---

## Repository Conflicts and Drift Found *(documented, not blocking)*

- **Supersession is a pointer pair, not a history log**: `src/seshat/decision_store.py` models supersession as two scalar fields (`supersedes` / `superseded_by`) with referential-integrity checking (DS4) only — there is no version list, timestamped chain, or diff. The task's phrase "preserve supersession history" is therefore satisfied by *reading and presenting the existing pointer chain* (D2/FR-006), not by building a history model. Recorded so the plan does not assume a richer substrate than exists.
- **Staleness signal is module-private**: the cited-evidence staleness comparison lives inside `src/seshat/decision_gate.py` as a private helper. Reuse (not re-implementation) of that signal is required (FR-005); whether to promote it to a shared helper is a plan-time decision, flagged so a second staleness authority is not created.
- **Three coexisting metric/artifact-identity vocabularies**: the `artifact_identity` `kind:path` scheme, the explorer's `metric:<table>:<name>` node id, and the additivity rule's prose-derived metric-name strings coexist unreconciled in shipped code. This feature MUST adopt one (NFR-006) and must not add a fourth; recorded as a real constraint the plan must honor.
- **Runtime lineage is single-hop; multi-hop lineage is a skill, not code**: the only shipped *runtime* lineage edge is the explorer's single-hop metric→gold `binds_to`; the full multi-hop chain exists only as the `cross-table-lineage` skill (prose/agent-executed), not as a queryable library. The transitive walk must reuse the skill's hop definitions and tiering vocabulary (FR-011), not silently assume a richer runtime graph exists.
- **Status-header/checkbox staleness**: repo-wide, spec Status headers and tasks.md checkboxes are known-unreliable; capability truth is `docs/capabilities/capabilities.yaml` + git log + source paths.

---

## Assumptions

- "Preserve supersession history" means reading and presenting the store's existing `supersedes` / `superseded_by` pointer chain; no new history/version model is built (D2/FR-006). This is the one boundary point that required an explicit interpretation against the real substrate; recorded here rather than left ambiguous.
- The exact output surface (a skill vs a single narrow read-only verb), the projection file format/path, and the precise field names of the projection dict are plan-time decisions (see plan.md); the spec fixes only that there is one deterministic machine-readable projection plus a human rendering of identical content, reusing the disclosure-safe contained-output pattern (FR-021, FR-022).
- The Decision Store (spec 121), the decision gate's staleness and flow→spine signals (spec 121), the artifact-identity scheme, the readiness projection, the blocker-category/next-surface authority, the explorer's runtime lineage edge, the `cross-table-lineage` skill's hop definitions, and the disclosure scanner + contained-output guard are all reused as-is; this feature adds no logic to any of them.
- The projection is computed from committed artifacts only; a live database or Power BI connection is never a trigger or input (D3/NFR-002), so their absence changes nothing.
- Whether the private staleness helper in the decision gate should be promoted to a shared helper (to avoid a forked staleness authority) is a plan-time decision, not a spec decision; the spec fixes only that the existing signal is reused, not duplicated (FR-005).
- Worked examples remain references; their specifics never enter generic artifacts and may only appear in fixtures (NFR-005, SC-012).
