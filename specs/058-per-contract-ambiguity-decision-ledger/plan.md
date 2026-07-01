# Implementation Plan: Per-Contract Ambiguity Decision Ledger

**Branch**: `058-per-contract-ambiguity-decision-ledger` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/058-per-contract-ambiguity-decision-ledger/spec.md`

## Summary

Add a per-contract ambiguity ledger to the DEFINE layer: a new top-level
`ambiguities` block on `templates/metric-contract.yaml` where a filled contract records,
per applicable catalogued ambiguity (A1..A11), a recorded owner ruling
-- `{ id, decision_status, ruling, evidence }`. An undecided material ambiguity records a
blocking reason and forces the contract's `readiness.status: blocked`; the agent records
the human owner's ruling and never self-grants a decided status. Document the ledger
lifecycle, the non-pass blocker rule, and the (verbatim, must-not-drift) define/check
boundary in `docs/metrics/metric-contract-store.md`, and CONFIRM the existing KPI pack
rollup already propagates a blocked contract (no new rollup logic).

Scope is pure DEFINE-layer authoring over committed text: template + store guide, plus a
one-line confirmation touch to the pack template's prose if needed. No retail-check rule,
no Power BI model read, no live data, no new module. This is the same category as
authoring the F009 contract template.

## Technical Context

**Language/Version**: None (data/documentation authoring only). Artifacts are YAML template
text and Markdown docs. No Python, no JavaScript, no executable code is added or changed.

**Primary Dependencies**: None new. The ledger keys to the existing A1..A11 catalogue in
`skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` (read-only reference, never
edited) and reuses the existing four-status readiness vocabulary
(`not_started | blocked | warning | pass`) already defined for contracts.

**Storage**: No new data file created by this feature. It EXTENDS the existing template
`templates/metric-contract.yaml` (adds one block) and the existing store guide
`docs/metrics/metric-contract-store.md` (adds lifecycle + boundary prose). Filled contracts
are NOT authored by this feature.

**Testing**: There is no runtime function to unit-test in the DEFINE-only scope. Validation
is (a) YAML validity of the extended template (it is parsed/reviewed as a set), and (b)
static-invariant checks a reviewer applies: A1..A11 range present (not A1..A10), no numeric
confidence field, no DAX/SQL/model-path in the ledger, generic-retail only, ASCII/UTF-8
no BOM. The acceptance scenarios are verified by the quickstart walkthrough (fill an entry;
read it back), since the "blocker" is a human-honored authoring convention, not a program.

**Target Platform**: Repo tooling / docs (Windows + CI Linux). No deployment target.

**Project Type**: Governance/authoring artifact for the metric-contract DEFINE layer (F009).
Template + docs edit.

**Performance Goals**: N/A.

**Constraints**: ASCII + UTF-8 no BOM (rule IX: `--` and `->`, no glyphs). Generic-only
(rule 7: no C086/pharmacy specifics inlined). No numeric confidence/score (rule 9). No
executor, no live DB, no model read, no new check rule. The verbatim define/check boundary
text and readiness-block shape MUST NOT drift. Windows 260-char path budget (names short).

**Scale/Scope**: One block added to one template; one lifecycle section + boundary restatement
added to one store guide; one confirmation sentence about pack rollup. Zero new files strictly
required, though this spec dir holds design artifacts (plan/data-model/quickstart/contracts).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS by construction. The agent RECORDS the
  owner's ruling as `decision_status` + `evidence`; it never self-grants a decided status.
  An undecided material ambiguity is a blocking reason it structurally cannot clear
  (FR-004).
- **Principle V (Agent Stops at Judgment Calls)**: PASS. Every A1..A11 ambiguity that moves a
  number is a human ruling. The headline-moving criterion (which ambiguities block) and the
  per-ruling correctness are reserved for the owner and recorded as carve-outs in the spec's
  ## Clarifications -- the plan does not resolve them.
- **Principle VII (C086 Is An Example, Not The Schema)**: PASS. The ledger block and A-ids
  stay generic-retail; the only motivating example inlined is the generic retail-store-sales
  discounted-transaction-rate case (FR-012). Any real filled ruling is CITED via the worked
  example, never inlined (FR-007).
- **Roadmap rule #9 / No Fake Confidence**: PASS. Certainty is recorded only via the four
  statuses + evidence + blocking reasons. No numeric confidence field is added (FR-005).
- **F009 DEFINE/CHECK boundary (verbatim, must not drift)**: PASS. This feature DEFINES; it
  reads no `powerbi/` model, adds no `retail check` rule, and does not implement the deferred
  enforcing half (FR-008, FR-010). The boundary text is restated verbatim.
- **Principle IX (Secrets & Reproducibility)**: PASS. ASCII + UTF-8 no BOM; short
  repo-relative paths (FR-011).

Re-check after Phase 1: no violation introduced. The one structural decision (ledger as a
sibling top-level block, not nested in readiness -- Q3) is specifically chosen to AVOID
drifting the verbatim readiness-block shape.

## Project Structure

### Documentation (this feature)

```
specs/058-per-contract-ambiguity-decision-ledger/
  spec.md                         # the feature specification (done)
  plan.md                         # this file
  data-model.md                   # the ambiguity-ledger entry schema (conceptual)
  quickstart.md                   # fill-and-read-back walkthrough + reviewer checks
  contracts/
    ambiguity-ledger.schema.md    # the ledger block field contract + invariants
  checklists/
    requirements.md               # spec quality checklist (done)
  analysis.md                     # produced by /speckit-analyze (stage 5)
  plan-review.md                  # produced by the adversarial review (stage 6)
```

### Source artifacts touched (repo)

```
templates/metric-contract.yaml            # ADD one top-level `ambiguities` block (net-new)
docs/metrics/metric-contract-store.md     # ADD ledger lifecycle + non-pass blocker rule
                                          #   + restate define/check boundary verbatim
                                          #   + CONFIRM existing pack rollup propagates a block
templates/kpi-pack.yaml                   # (read/confirm only; no rollup logic change)
skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md   # READ-ONLY reference (A1..A11); never edited
```

**Structure Decision**: No new source tree. This feature extends two existing DEFINE-layer
artifacts in place and adds design docs under the spec dir. The ledger block is authored as a
SIBLING top-level block on the contract (adjacent to `readiness`), never nested inside it, so
the verbatim readiness-block shape does not drift (Q3, FR-017).

## Phase 0: Research / Outline

No unknowns require external research. The load-bearing seams are all confirmed present in
the repo:

1. **A1..A11 catalogue** exists and is the id vocabulary (A10 = inventory snapshot date,
   A11 = same-store definition). The idea title's "A1-A10" ceiling is CORRECTED to A1..A11 by
   this spec so A11 is not dropped (FR-002, SC-005).
2. **Four-status readiness vocabulary** + evidence[] + blocking_reasons[] with no numeric
   confidence is the existing recording mechanism the ledger reuses (FR-005, FR-006).
3. **Template readiness block** + the verbatim Principle-V stop-and-ask list already exist;
   the ledger is net-new and must NOT drift the readiness shape or the boundary text.
4. **Pack rollup** ("no more ready than its least-ready contract") already propagates a
   contract block; this feature confirms it and adds no rollup rule (FR-009).
5. **DiscountedTransactionRate stakes case** (about 33.55 percent all txns vs about 50.37
   percent known-status only) is the documented, generic motivating example (FR-012).

Deferred / not assumed to exist: the enforcing static CHECK rule (separate unbuilt idea), any
Power BI execution adapter, any model read, any live data. Nothing in this plan depends on
any of these.

## Phase 1: Design

### The ledger block (net-new on the contract)

A new top-level `ambiguities` list. Each element is one entry:

- `id` -- a catalogued identifier in the A1..A11 range only (an out-of-range id is a defect).
- `decision_status` -- reuses an existing recorded vocabulary. RECOMMENDED (pending the
  human carve-out in ## Clarifications): reuse the four readiness statuses so the ledger
  status idiom matches the host readiness block. Alternative candidate: the catalogue's
  needs-business-definition flag. The pick is deferred to the owner; the schema is written to
  accept whichever the owner confirms, and the template comment names both candidates without
  inventing a fifth word (FR-006).
- `ruling` -- plain-language business INTENT of the decision; never DAX/SQL/visual/model path
  (FR-003), consistent with the contract's define/check boundary.
- `evidence` -- the owner-and-date (and any committed support) that backs a decided ruling;
  a decided status with no evidence is a defect, mirroring the readiness `pass` rule.

Applicability (Q1/FR-015): only APPLICABLE ambiguities are recorded; a non-applicable
ambiguity may be omitted. Omission of an APPLICABLE MATERIAL ambiguity is a review defect
(treated as undecided). Not-applicable is expressed by omission (Q2/FR-016), never by a
decided status; undecided is an explicit status carrying a blocking reason.

Blocking behavior (FR-004): an undecided MATERIAL ambiguity records a `blocking_reason` on
the contract's readiness AND names the ambiguity, and forces `readiness.status: blocked`.
Only a recorded owner ruling clears it. Whether a given ambiguity is material
(number-moving/blocking) vs cosmetic is the human carve-out (FR-013).

### Store-guide additions

- A "Per-contract ambiguity ledger" section documenting: what the block is, the lifecycle
  (applicable -> undecided/blocked -> owner rules -> decided/evidence), the non-pass blocker
  rule, and the A1..A11 keying (with the A10/A11 correction called out).
- A restatement of the define/check boundary VERBATIM (must not drift): this feature DEFINES;
  it reads no model, adds no check rule, does not implement the deferred enforcing half.
- A CONFIRMATION (not new logic) that the existing pack rollup already propagates a blocked
  contract to its packs.

### Design gate re-check

Constitution re-check passes (see above). No deferred capability is assumed. The verbatim
boundary + readiness shape are preserved by choosing a sibling block.

## Complexity Tracking

No constitution deviations. No entries.
