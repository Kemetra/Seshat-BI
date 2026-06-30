# Cross-Artifact Analysis: Idea-Bank Memory Seam (IL1)

**Feature**: 052-idea-bank-memory-seam | **Date**: 2026-06-30 | **Mode**: read-only

Scope of pass: spec.md, plan.md, tasks.md, data-model.md, contracts/shipped-ideas.schema.md,
quickstart.md. No artifact was modified (this file is the only write, per repo convention).

## A. Requirement -> Task coverage

| FR | Requirement (short) | Covered by |
|----|---------------------|------------|
| FR-001 | ledger file + keyed schema (status/pr_sha/f_row) | T002 (author), T003 (guard) |
| FR-002 | Memory stage reads ledger as known-history | T005 |
| FR-003 | evidence-only; no F-row write/promote | T007 (assert + comment); SC-002 |
| FR-004 | Memory must not re-read git; Ground single owner | T005 (git_corroborated:false) |
| FR-005 | absent/empty -> graceful fallback | T006, T003 (fixture) |
| FR-006 | malformed -> fail loud | T006, T003 (fixture) |
| FR-007 | generic identifiers only | T003 (invariant) |
| FR-008 | docs + JS read step only; no executor/DB | plan Phase 0/Constitution; (authorship marker open) |
| FR-009 | ledger authoritative on conflict; surface, no rewrite | T006 |
| FR-010 | optional rule OUT of scope | "Out of scope" section; T009 verifies absence |

Result: every in-scope FR maps to at least one task. FR-008's design constraint is satisfied
by the plan (no executor/DB introduced); its embedded authorship [NEEDS CLARIFICATION] is an
intentional Principle-V open item, not a coverage gap.

## B. User-story -> Task coverage

- US1 (engine remembers shipped, P1) -> Phase 3 (T003-T007). Independently testable via the
  guard test + manual labeling check. OK.
- US2 (readable honest ledger, P2) -> T002 (authoring) + T003 (validity guard). OK.

No orphan tasks; every task traces to a story or to setup/polish.

## C. Success-criteria verifiability

- SC-001 (shipped ids labeled) -> US1 acceptance scenarios + quickstart step 3. Verifiable.
- SC-002 (zero F-rows written) -> T007 + quickstart step 4 (grep engine output). Verifiable.
- SC-003 (absent/empty -> no error, same as today) -> T003 fixture + T006 branch. Verifiable.
- SC-004 (maintainer reads evidence+placement) -> data-model + quickstart step 1. Verifiable.
- SC-005 (no sample/domain values) -> T003 generic-only assertion. Verifiable.

All SCs are measurable and technology-agnostic at the spec level.

## D. Terminology consistency

- "idea-id" / "backlog short-code" used consistently as the key across spec/plan/data-model/
  contract. No competing term.
- status enum (shipped | settled) identical in spec FR-001, data-model, contract.
- f_row (label or none) consistent everywhere; none is a first-class value in all three.
- current_state mapping (shipped/rejected-settled) matches the actual idea-engine Memory
  schema enum verified in source -- no invented downstream shape.

## E. Constitution / principle alignment

- Idea-bank-not-roadmap + human-rules-promotion (Principle V): enforced by FR-003 + T007 +
  SC-002. No self-promotion path. PASS.
- Single-owner-of-ship-status: Memory keeps git_corroborated:false and does not re-read git
  (T005); the engine-append-vs-human-curated question is correctly left OPEN, not silently
  decided. PASS (with recorded open item).
- Add-the-seam-not-the-implementation (YAGNI): optional rule deferred (FR-010); no F016/
  F031-F033 dependency. PASS.
- Generic-only / no C086 leak: FR-007 + T003. PASS.
- Fail-loud / no fabricated confidence: FR-006 + no readiness score produced. PASS.

## F. Rule-count consistency (the grounding's flagged discrepancy)

The grounding flagged a 32-vs-33-vs-34 ambiguity. Verified against the live frozenset in
tests/unit/test_rules_wiring.py: the current EXPECTED_RULE_IDS enumerates 38 ids
(S1-S8 incl. S4a/S4b = 9; D1-D11 = 11; R1; A1,A3; B1,B3; C1,C2; G1-G6; P1,P2; PP1; SC1; DF1).
All three artifacts cite 38 and explicitly call the prior "33/34" prose stale. Because the
optional rule is out of scope, NO "N+1" claim is encoded -- the off-by-one cannot propagate.
Consistent across artifacts. No finding.

## G. Findings

| ID | Severity | Location | Finding | Disposition |
|----|----------|----------|---------|-------------|
| (none critical) | -- | -- | -- | -- |
| N1 | low | spec FR-008 | The authorship [NEEDS CLARIFICATION] is embedded in FR-008, whose prose is otherwise about "docs + JS only". The two concerns (no-executor vs authorship) are bundled in one FR. | Acceptable -- both recorded; the marker is intentional and the no-executor half is independently testable. No change required for ratification. |
| N2 | low | tasks T003 | Test placement is left as "alongside existing manifest/wiring tests" rather than a fixed path. | Acceptable -- the exact path is an implementation choice; the guard's required assertions are fully specified. |

## H. Verdict

- Critical findings: 0
- High findings: 0
- Low/informational: 2 (N1, N2) -- neither blocks ratification.

Cross-artifact state: CLEAN (0 critical, 0 high). Coverage complete, terminology consistent,
principles aligned, rule-count reconciled. Two Principle-V markers remain OPEN by design for
the human ratify gate (promotion authority is settled in the spec text as evidence-only;
ledger authorship and yaml-replaces-prose remain human calls).
