# Cross-Artifact Analysis: 011-semantic-model-readiness

**Date**: 2026-06-24 | **Scope**: spec.md + plan.md + tasks.md vs constitution,
roadmap, the readiness spine, and the committed model. Read-only analysis; no source
edits beyond the artifacts under review.

## Method

Checked the three feature artifacts against: the constitution
(`.specify/memory/constitution.md`, v1.6.0), the roadmap + hard rules
(`docs/roadmap/roadmap.md`), the stage authority
(`docs/readiness/semantic-model-ready.md`), the spine model + pipeline, the existing
gate rules (`src/retail/rules/{dax,pbir,g6}.py`), the conductor seam
(`.claude/skills/retail-orchestrate/SKILL.md`), and the committed model
(`powerbi/Retailgold.SemanticModel/`). Looked for: scope overlap, requirement-to-task
coverage, terminology drift, constitution conflicts, and unfounded claims.

## Coverage matrix (requirement -> task -> success criterion)

| FR | Covered by tasks | Success criterion |
|----|------------------|-------------------|
| FR-001 (new skill, no Python/rule/CLI) | T004 | SC-001, SC-002 |
| FR-002 (Gold-Ready ordering gate) | T007 | SC-003 (ordering) |
| FR-003 (run `retail check`; D/C/R/G6 -> blockers) | T008 | SC-002, SC-003 |
| FR-004 (structural facts: D6/D7/D1/D2) | T008 (via gate), T003 | SC-003 |
| FR-005 (contract-binding criterion) | T011, T012, T013 | SC-003 |
| FR-006 (necessary-not-sufficient) | T010 | SC-004 |
| FR-007 (one verdict, evidence+blockers, no number) | T009 | SC-003 |
| FR-008 (read-only, author-nothing) | T015, T016 | SC-004 |
| FR-009 (fail-loud judgment stops) | T014, T017 | SC-003 |
| FR-010 (orchestration pointer) | T018 | SC-001 |
| FR-011 (cross-link stage authority) | T019 | SC-004 |

Every FR maps to >=1 task and >=1 success criterion. Every user story (US1/US2/US3)
has a dedicated task phase (3/4/5) and an independent test. No orphan tasks; no
uncovered FR. PASS.

## Consistency findings

- **F009/F010 scope boundary held.** The spec, plan, and tasks consistently place
  contract DEFINITION in F009 and contract CHECKING in this feature; the skill READS
  the store and never creates/edits/approves a contract (spec check/define boundary,
  FR-005, T013). No overlap with F009. PASS. NOTE recorded below on the roadmap's
  feature-number naming.
- **Hard-gate ordering respected.** This stage refuses to evaluate until Gold Ready is
  `pass` (FR-002, T007), matching roadmap hard rule #4 / Principle VIII and the
  pipeline transition `gold_ready --pass--> semantic_model_ready`. PASS.
- **No authoring automation.** The skill is read-only and never calls pbi-cli / PBIP
  automation (FR-008, T015); pbi-cli stays the deferred F016 adapter (hard rule #6,
  Principle II). Consistent with the conductor's row "PBIP build engine | [SEAM --
  pbi-cli deferred adapter, Principle II]". PASS.
- **No fake confidence.** The verdict is the four explicit statuses + evidence +
  blockers; no numeric score (FR-007, T009), matching hard rule #9 and
  readiness-model "No fake confidence". PASS.
- **Mechanical gate reuse is accurate.** The D1-D8 (dax.py), C1/R1 (pbir.py), G6
  (g6.py) rules cited all exist in code (verified). The skill calls them and adds no
  rule (plan Structure Decision, T002). PASS.
- **Date-table marker description matches D7.** The spec/plan describe the marker as
  the `DATE_TABLE_MARKER` annotation OR table-level `dataCategory: Time` + a key
  column -- exactly D7's detection logic in `dax.py`. PASS.
- **Terminology stable.** "Semantic Model Ready" / "Stage 5" / "metric contract" /
  "contract-binding" / "necessary-not-sufficient" are used identically across all
  three artifacts and match the stage doc. PASS.
- **Generic, no C086 leakage.** The skill procedure is generic; the RetailGold model
  is cited only as the available read-only fixture, not baked into the procedure
  (Principle VII). The artifacts name no pharmacy specifics. PASS.
- **ASCII + UTF-8 no BOM.** All three artifacts verified ASCII-clean and BOM-free
  (an initial box-drawing-character slip in plan.md's tree was corrected to ASCII).
  PASS.

## Notes / non-blocking observations (recorded, not defects)

- **N1 -- roadmap feature-number naming.** The task input cites "Roadmap F010" and
  "F009 / on-disk 010", while `docs/roadmap/roadmap.md` lists feature 010 as
  "Semantic Model Readiness" (the checking layer) and feature 011 as "Power BI
  Dashboard Design Skill". This feature is authored under branch/dir 011 per the
  orchestration assignment. The spec resolves the naming by treating "F010 / on-disk
  010" as the model-CHECKING layer that THIS feature carries, and keeps F009 as the
  contract STORE producer. The substantive boundary (define vs check) is unambiguous;
  only the integer label differs. Flagged for a human to reconcile the roadmap's
  feature numbering vs the assigned branch number if desired -- it does not change any
  requirement.
- **N2 -- the model already has measures, but no contracts.** The committed
  RetailGold model has ~12 PascalCase measures (TotalSales, NetSales, DiscountRate,
  ReturnSales, ...) and passes `retail check`, yet the F009 store does not exist. The
  spec makes this the central correctness property: the skill MUST emit `blocked`
  (nothing to bind to), not `pass`. This is the designed outcome and the primary
  acceptance test (SC-003), not a defect.
- **N3 -- contract <-> measure matching convention is F009's to settle.** The spec
  assumes a readable store and a recordable owner approval, and HARD-STOPS on an
  ambiguous measure-name-to-contract-key mapping (FR-009, T014) rather than guessing.
  The exact matching convention is deferred to F009 (recorded in spec Deferred
  decisions). No invented answer. Consistent with Principle V.

## Principle-V human-judgment seams (NOT auto-answered)

Per the clarification policy, the following are recorded for a human and were NOT
invented by this chain (Principle V -- grain, PII, business-rollup, product-identity,
and named approvals):

- **Metric owner approval** of each contract -- a named human action the skill cannot
  self-grant (spec FR-005/Acceptance 2, US2). The skill reports its absence as
  `blocked`; it never records the approval itself.
- **The contract grain + formula intent** carried by each contract -- owned by F009 /
  the metric owner; this feature reads them, it does not define them.
- These are surfaced, not answered.

## Verdict

All three artifacts are mutually consistent, fully cover the requirements, and conform
to the constitution (Principles II, V, VII, VIII, IX and the Readiness spine), the
roadmap hard rules (#4, #5, #6, #9), and the stage authority. One non-ASCII slip was
found and fixed. No blocking inconsistencies. The single open item for a human is the
roadmap feature-number reconciliation (N1) plus the standard Principle-V approval seams
-- none of which block drafting. Ready for downstream `/speckit-implement`.
