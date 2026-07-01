---
description: "Task list for 053-per-contract-ambiguity-decision-ledger"
---

# Tasks: Per-Contract Ambiguity Decision Ledger

**Input**: Design documents from `specs/053-per-contract-ambiguity-decision-ledger/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/ambiguity-ledger.schema.md, quickstart.md

**Tests**: No runtime function is added (DEFINE-only authoring). "Tests" are the reviewer
invariant checks in quickstart.md + the schema contract; there is no automated test suite and
NO retail-check rule (spec FR-010). YAML validity of the extended template is the one
mechanical check.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- Scope is the DEFINE seam only; the enforcing static CHECK rule is OUT OF SCOPE (spec FR-010)
  and has NO task here.

## Phase 1: Setup

- [ ] T001 Confirm the spec dir + design artifacts are present (spec.md, plan.md,
  data-model.md, contracts/ambiguity-ledger.schema.md, quickstart.md, checklists/requirements.md)
  and the branch is `053-per-contract-ambiguity-decision-ledger`. No tooling/dependency setup
  is required (no code, no new library).

- [ ] T002 Re-read the read-only seams to author against exact text (do NOT edit them):
  `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` (A1..A11 ids; confirm A10 =
  inventory snapshot, A11 = same-store), the four-status vocabulary + evidence/blocking_reasons
  in `docs/metrics/metric-contract-store.md`, the readiness block + verbatim Principle-V
  stop-and-ask list in `templates/metric-contract.yaml`, and the rollup sentence in
  `templates/kpi-pack.yaml` / the store guide.

---

## Phase 2: Foundational (the template seam)

**Purpose**: the `ambiguities` block must exist on the template before the store guide can
document its lifecycle.

- [ ] T003 [US1][US2] Add the net-new top-level `ambiguities` block to
  `templates/metric-contract.yaml` per contracts/ambiguity-ledger.schema.md and data-model.md.
  Author it as a SIBLING of `readiness` (NOT nested; Q3/FR-017). Each entry has `id` (A1..A11
  only), `decision_status` (comment naming the two existing candidate vocabularies -- four
  readiness statuses recommended, needs-business-definition flag alternative -- and forbidding
  a fifth word; FR-006), `ruling` (plain-language INTENT; reject DAX/SQL/model path; FR-003),
  `evidence` (owner+date when decided; FR-001). Include the generic discounted-transaction-rate
  example comment (A7/A4; FR-012). State: applicable-only recording (FR-015), omission =
  not-applicable (FR-016), no numeric confidence (FR-005), A1..A11 range with the A10/A11
  correction called out (FR-002). Keep the verbatim readiness-block text and the verbatim
  define/check boundary UNCHANGED (must not drift). ASCII + UTF-8 no BOM (FR-011).

- [ ] T004 [US2] In the SAME edit pass on `templates/metric-contract.yaml`, add an authoring
  note tying an undecided MATERIAL ambiguity to a readiness `blocking_reason` + `status:
  blocked`, and stating the agent records-not-invents rule (FR-004). Do not duplicate or
  reshape the existing readiness block -- reference it. (Same file as T003; author T003+T004
  together to minimize edit rounds.)

---

## Phase 3: Store-guide documentation (the lifecycle + boundary)

- [ ] T005 [US1][US2] Add a "Per-contract ambiguity ledger" section to
  `docs/metrics/metric-contract-store.md` documenting: the block's purpose, the lifecycle
  (applicable -> undecided/blocked -> owner rules -> decided/evidence), the non-pass blocker
  rule (FR-004), the A1..A11 keying with the A10 = inventory-snapshot / A11 = same-store
  correction (FR-002), applicability + not-applicable-by-omission (FR-015/FR-016), and the
  no-fake-confidence rule (FR-005). Generic-retail only; motivating example is the generic
  discounted-transaction-rate case (FR-012); cite `docs/worked-examples/c086-pharmacy.md` for
  a real filled instance rather than inlining one (FR-007).

- [ ] T006 [US1] In `docs/metrics/metric-contract-store.md`, RESTATE the define/check boundary
  VERBATIM for the ledger (this feature DEFINES; reads no model; adds no check rule; does not
  implement the deferred enforcing half; FR-008, FR-010). Ensure the wording matches the
  existing boundary paragraph so it does not drift. (Same file as T005.)

- [ ] T007 [US3] In `docs/metrics/metric-contract-store.md`, add a one-paragraph CONFIRMATION
  that the existing pack rollup ("a pack is no more ready than its least-ready contract")
  already propagates a contract blocked by an undecided ambiguity to its packs -- explicitly
  stating that NO new rollup logic is added (FR-009). (Same file as T005/T006; author T005-T007
  together.)

---

## Phase 4: Consistency + invariant pass (the reviewer checks stand in for tests)

- [ ] T008 [P] Verify the A1..A11 range invariant across ALL authored artifacts (template
  block + store-guide section): every reference uses A1..A11, none narrows to A1..A10, and the
  A10/A11 identities are stated correctly (FR-002, SC-005).

- [ ] T009 [P] Verify the no-fake-confidence invariant: grep the authored artifacts for any
  numeric confidence / score / weight field and confirm none exists (FR-005, SC-003).

- [ ] T010 [P] Verify the generic-only invariant: no domain-specific (pharmacy/C086) ambiguity
  ruling is inlined in the template or store guide; the only inlined case is the generic
  discounted-transaction-rate example; the worked example is CITED not copied (FR-007, SC-004).

- [ ] T011 [P] Verify the define/check-boundary + no-check invariant: no `retail check` rule,
  registered rule id, `powerbi/` model read, or executable code was added; the boundary text
  did not drift (FR-008, FR-010, SC-006).

- [ ] T012 Verify encoding + YAML validity: the extended `templates/metric-contract.yaml` is
  valid YAML (parseable as a set), and all authored files are ASCII + UTF-8 no BOM with `--`
  and `->` (no glyphs) and short repo-relative paths (FR-011).

- [ ] T013 Walk the quickstart.md scenarios (US1 fill-and-read-back, US2 undecided-blocks,
  US3 pack-propagation) against the authored artifacts to confirm each acceptance scenario is
  satisfiable by a reviewer, and that the two Principle-V carve-outs (headline-moving criterion
  FR-013, roadmap placement FR-014) plus the two other carve-outs (per-ruling correctness,
  decision-status vocabulary pick) remain recorded-not-answered in spec ## Clarifications.

---

## Dependencies

- T001, T002 (setup) before all.
- T003 + T004 (template block) before T005-T007 (store guide documents what the block is).
- T005-T007 (authoring) before T008-T013 (verification).
- T008-T011 are parallel [P] (independent read-only invariant checks over the same authored
  files -- run as separate checks, no write contention).
- T012, T013 after T008-T011.

## Out of scope (no task exists for these)

- The enforcing static CHECK rule / any new registered rule (spec FR-010).
- Any Power BI model read, execution adapter, or live data.
- Editing the read-only A1..A11 catalogue.
- Answering the four Principle-V carve-outs (they are recorded for a human owner).
