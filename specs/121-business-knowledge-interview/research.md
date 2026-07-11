# Research: Business Knowledge Interview, Decision Store, and Knowledge Contracts

**Feature**: `specs/121-business-knowledge-interview` | **Date**: 2026-07-11

All plan-time unknowns from the spec's Assumptions section and the clarify session's
deferred items are resolved below. No NEEDS CLARIFICATION markers remain.

## R-1: Enforcement mechanism

**Decision**: Add a new fail-closed static rule family (working name **DS1-DS5**) to
the existing `retail check` surface, registered in the rule registry and the generated
manifest: DS1 store schema/status validity, DS2 approval-metadata completeness +
authority-class eligibility, DS3 batch integrity (no critical types in batches;
exclusions recorded), DS4 supersession/immutability integrity (approved records only
change by supersession; references resolve), DS5 verdict consistency (no pass without
evidence; recorded blocking reasons match the store).

**Rationale**: Constitution Principle I -- "the governance contract is a non-zero
process exit, not a paragraph of prose". A decision store whose validity is only
described in docs would drift the first time it is inconvenient. The repo's precedent
(spec 118's fail-closed truthfulness oracle; RS1 for approval shape) is exactly this
shape. Severity per class, respecting Principle VIII's suspect->WARN / proven->ERROR
asymmetry: defects **provable from committed text** (malformed record, missing
approval metadata, ineligible authority class, critical type in a batch, unresolved
supersession reference, in-place edit of an approved record) are ERROR; **heuristic
guards** (the PII-value-shape guard) are WARNING. Confirm the classification against
the RS1 precedent at implementation (T011). Enforcement never depends on severity
alone: an invalid approval never satisfies a gate -- the dependent verdict is blocked
regardless of the checker's exit class.

**Alternatives considered**: Docs/templates-only slice (rejected: unenforced, violates
Principle I's posture and the spec's fail-closed FRs); a separate new CLI gate command
(rejected: creates a second gate surface next to `retail check`; the spine's rule is
one static gate the agent calls).

## R-2: Decision-record identity

**Decision**: Every record carries a required stable `id`: a kebab-case slug
`<decision_type>.<scope-slug>[.<n>]` (e.g. `grain.fct-sales`,
`kpi-definition.net-sales`, `missing-value.fct-sales.unit-price`), unique within the
project store. Supersession references use these ids (`supersedes:` /
`superseded_by:`).

**Rationale**: Human-readable ids keep diffs and review-artifact references legible
(NFR-001) and survive merges better than sequence numbers; supersession lineage
(FR-017) needs stable references.

**Alternatives considered**: Content hashes (rejected: opaque in diffs and review);
global sequence numbers (rejected: merge-conflict magnet across branches).

## R-3: Decision store layout

**Decision**: Three project-level YAML files in the workspace `.seshat/` directory,
exactly as the spec proposed: `semantic-decisions.yaml` (grain, PK, relationships,
PII, exclusions, blueprint/publish decisions), `kpi-contracts.yaml` (KPI-meaning
decisions and policy rulings: VAT/returns/discount/cost), `cleaning-rules.yaml`
(missing-value and cleaning rulings). Each record declares `scope` (tables / columns /
KPIs / artifacts), satisfying FR-019.

**Rationale**: `.seshat/` is already the workspace's machine-readable state home.
Splitting by concern keeps each file small and review-focused (many small files rule)
and mirrors the three downstream consumers (modeling, KPI/DAX, cleaning).

**Alternatives considered**: Per-table files under `mappings/<table>/` (rejected:
KPI-meaning and policy decisions are cross-table; ADR 0003 scopes `mappings/<table>/`
to the five gate artifacts, and the store records rulings that *feed* those artifacts
rather than duplicating them); one monolithic decisions file (rejected: merge and
review noise).

## R-4: Product-contract location

**Decision**: New top-level `contracts/` directory holding the product-level knowledge
contracts: `contracts/knowledge/database-to-pbip-flow.yaml` (all 11 stage entries in
one file), `contracts/knowledge/approval-authority.yaml` (decision_type -> eligible
authority classes), `contracts/interview/business-knowledge-interview.yaml`, and
`contracts/report/dashboard-blueprint.yaml`, plus a README distinguishing contracts
(normative product data) from templates (blanks users fill).

**Rationale**: No conflicting convention exists (verified: no root `contracts/` dir).
The spec's working proposal stands. `templates/` is wrong for normative data users
never fill in; `docs/` is wrong for machine-readable YAML the checker reads.

**Alternatives considered**: `docs/contracts/` (rejected: docs are narrative);
embedding in `.seshat/kit-source.yaml` (rejected: that file generates the router
block; contracts are consumed by rules and agents, not the router generator).

## R-5: Review-artifact location and generation

**Decision**: Blank shape at `templates/business-interview-review.md`; generated
instance lives in the workspace evidence location as
`evidence/business-interview-review.md`. Generation is a deterministic projection of
the decision store (same store => byte-identical artifact), implemented alongside the
verdict projection.

**Rationale**: Matches the existing template->filled-instance pattern (the five
mapping artifacts) and the evidence-pack surfaces. Determinism satisfies NFR-002 and
keeps SC-008 testable.

**Alternatives considered**: Hand-maintained markdown (rejected: becomes a second
source of truth, violating FR-024); embedding in readiness-status.yaml (rejected:
that file is per-table and recomputed; the review is project-level and human-facing).

## R-6: Gate-verdict integration with the readiness spine

**Decision**: Verdicts are a pure projection: `decision_gate` recomputes
pass/warn/blocked for a requested stage from the store + cited evidence, and
contributes entries to the affected stage's existing `blocking_reasons[]` /
`warning` surface in `readiness-status.yaml`. Stage mapping: interview decisions land
on Source Ready / Mapping Ready; KPI-meaning on Semantic Model Ready prerequisites;
blueprint approval on Dashboard Ready; publish/export on Publish Ready. `warn` maps to
the spine's `warning`; the spine remains the only stage-state authority.

**Rationale**: FR-001 (no second state engine) and the kit's "state lives in
readiness-status.yaml, recomputed; this file stores none" posture. The spine already
has exactly the pass/warning/blocked semantics needed.

**Alternatives considered**: A parallel verdict file (rejected: second state engine);
writing verdicts into the decision store (rejected: mixes rulings with derived state,
breaking determinism of R-5).

## R-7: Authority-class vocabulary

**Decision**: Reuse the readiness spine's existing named-human-plus-authority-class
convention and its class vocabulary, normalized to snake_case tokens (`data_owner`,
`analyst`, `governance`, `metric_owner`, `report_owner` -- the token forms the RS1
shape check parses). `contracts/knowledge/approval-authority.yaml`
maps each of the ten critical decision types to its eligible class(es): PII handling,
data exclusion, publish/export -> `data_owner`/`governance`; KPI definition,
missing-value rules on KPI/financial fields, policy rulings (`policy_ruling`) ->
`metric_owner`; grain, primary key,
relationship/cardinality -> `data_owner` or `analyst` with `data_owner` confirmation
where the stage docs require it; dashboard blueprint -> `report_owner`. Exact per-type rows are
finalized against `docs/glossary.md` and the stage docs during implementation -- the
contract file is the single place they live.

**Rationale**: The clarify session ruled per-type eligibility mapping; RS1 already
enforces the name+class shape, so DS2 only adds the eligibility check on top rather
than inventing a new convention.

**Alternatives considered**: Hard-coding eligibility in rule code (rejected: contracts
are data; owners may legitimately amend the mapping); free-form classes (rejected:
unknown class is already a defect under RS1).

## R-8: Interview execution shape

**Decision**: No interview runtime engine. The interview is conducted conversationally
by the agent (agent-first, Principle I) under a gated kit verb
(`.claude/skills/business-knowledge-interview/`, registered in `.seshat/kit-source.yaml`)
whose behavior contract is `contracts/interview/business-knowledge-interview.yaml`:
question grouping (batch vs critical), masking defaults, pause/resume, re-run
confirmation semantics, and the requirement that every outcome lands in the store.
Static rules then verify the *recorded result*, not the conversation.

**Rationale**: The kit's product is governed agent behavior, not chat UI. Verifying
committed outcomes is what static-first governance can actually enforce (Principle
VIII); the conversation itself is unverifiable text.

**Alternatives considered**: A CLI questionnaire runtime (rejected: terminal-first,
contradicts North-Star correction #1; large scope for no governance gain); an
interactive TUI (rejected: same, plus platform risk).

## R-9: Masking approach for samples

**Decision**: Masking is a display obligation defined in the interview contract:
suspected-PII values shown as shape-preserving masks (e.g. `a***@***.com`,
`+20-1**-***-**45` -> class + length hints only), with the suspicion source cited
(profile heuristic or owner statement). Committed artifacts never contain raw
suspected-PII values (FR-005); DS1 includes a value-shape guard for the store files,
and the existing C2 secret-scan posture extends to the new artifact paths.

**Rationale**: The PII-touch-notice work (spec 114) and R4 credential-leak classes
already establish redaction as a governance concern; this reuses that posture instead
of inventing a parallel one.

**Alternatives considered**: Hash-only display (rejected: useless to a human deciding
whether a column is PII); full suppression (rejected: the owner sometimes needs shape
evidence to rule correctly).

## R-10: Stale-evidence detection mechanism

**Decision**: Every approval captures `evidence_identity` -- a map from each cited
evidence ref to its content identity (hash or revision ref) at approval time.
Staleness (clarify Q1) is detected by comparing an artifact's current identity to the
recorded one; a missing `evidence_identity` invalidates the approval outright (DS2).
Implementation reuses the spec-120 artifact-identity approach
(`src/seshat/artifact_identity.py`: canonical paths + content identities) rather than
inventing a second identity scheme.

**Rationale**: The clarified staleness rule (critical => blocked, non-critical =>
warn) is unenforceable without a recorded point-of-approval identity -- nothing else
distinguishes "evidence changed" from "evidence always looked like this". Capturing
identity at approval keeps verdict recomputation deterministic from committed text
(FR-034).

**Alternatives considered**: Git-history inspection at verdict time (rejected:
non-deterministic across shallow clones and rebases; violates
projection-from-committed-text); timestamps (rejected: mtime is not content identity
and does not survive checkout).
