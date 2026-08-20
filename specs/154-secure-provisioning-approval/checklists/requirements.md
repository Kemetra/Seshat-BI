# Specification Quality Checklist: Secure integration provisioning approval

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-20
**Feature**: [spec.md](../spec.md) — issue #671

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Security-delta specific checks

- [x] The defect is reproduced with observed output, not merely asserted
- [x] Intent, authority, execution, verification, and readiness are distinguished as separate concepts (FR-007/008 vs FR-001, FR-016)
- [x] No second approval vocabulary or shape validator introduced (FR-003)
- [x] No third approval-writing path introduced (FR-017)
- [x] Authority is committed + HEAD-only (FR-001, FR-002)
- [x] Every caller-controlled signal is explicitly denied authority (FR-005, FR-006, FR-008)
- [x] Fail-closed on every malformed/missing/mismatched case (FR-013)
- [x] The exact amended sentence of spec 144 FR-010 is quoted verbatim
- [x] The five FR-010 clauses NOT amended are enumerated
- [x] Spec 153 implementation-blocked status restated and its FR-018 marked permanent
- [x] Every required scenario from the issue brief maps to an acceptance scenario

## Required-scenario coverage map

| Required scenario | Where |
|---|---|
| `--apply --yes`, no committed approval → refused | US1 AS1 |
| Approval only in worktree → refused | US1 AS4 |
| Committed but invalid shape → refused | US2 AS3 |
| Wrong capability/scope → refused | US2 AS2 |
| Correct committed approval → may proceed | US2 AS1 |
| Non-interactive + valid approval → no authority from flag | US2 AS4 |
| Verification fails after valid approval → not ready | US2 AS5 |
| Re-run / consumed approval semantics | US2 AS8/AS9 + FR-012a..e (ruled: standing-until-scope-change) |
| Per-table readiness approval → not provisioning authority | US2 AS6, FR-001a |
| Non-`governance` authority class → refused | US2 AS7, FR-004a |
| Material scope change → new approval required | US2 AS10, FR-012c |
| Revoked/removed/replaced approval → ceases to authorize | US2 AS11, FR-012d |
| Old approval, unchanged scope → no time-based expiry | US2 AS12, FR-012e |

## Notes

- **28 FRs, 15 SCs, 3 user stories.** FR groups: authority source (incl. the
  per-project location ruling), intent-vs-authority, scope binding, approval
  lifetime, fail-closed/reporting, reuse, and the amendment requirement. No FR
  restates spec 144 or 153 content.
- **ZERO unresolved owner decisions.** Both were ruled by the owner on 2026-08-20
  and propagated into FRs, scenarios, edge cases, entities, assumptions,
  dependencies, and success criteria:
  1. **Location/authority** — a dedicated per-project committed approval artifact;
     explicitly NOT a per-table `mappings/<table>/readiness-status.yaml` path;
     canonical shape and validator reused; existing `governance` class; no sixth
     authority class; `governance` here means the named human project-governance
     authority for external environment/tool changes and is never inferred,
     synthesized, or self-granted. (FR-001, FR-001a, FR-004a, FR-004b, SC-012,
     SC-013)
  2. **Lifetime** — `standing-until-scope-change`: reusable for retries and repeat
     runs while scope is materially identical; a partial failure never forces a new
     approval; material scope change (added capability, changed provider, expanded
     component set, security-relevant target/environment change, or materially
     changed plan) requires new approval; revocation/removal/replacement ends
     authority; no time-based expiry. (FR-012a–FR-012e, SC-014, SC-015)
- **Everything else was settled from evidence**, not left open: the defect
  reproduction, the two-model comparison, the FR-010 conflict and its exact
  sentence, and the fact that spec 144 FR-009 already says compatibility apply must
  "never infer approval" (which shows FR-010's prompt preservation was compatibility
  intent, not a trust-model endorsement).
- **Zero implementation.** No source or test file was modified.
- **Base**: this spec was authored in worktree 55 at `51cab7c0`, one commit behind
  `origin/main` (`b024443e`). That commit was verified to touch none of the #671
  evidence set, spec 144, or the constitution — diff across all of them is empty.
