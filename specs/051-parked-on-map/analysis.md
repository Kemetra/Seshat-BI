# Cross-Artifact Analysis: DF1 Parked-On Map (Stage 5 /speckit-analyze)

**Scope**: read-only consistency + quality pass over `spec.md`, `plan.md`, `tasks.md`
(with `research.md`, `data-model.md`, `contracts/df1-rule-contract.md` as design
inputs). No artifact was modified by this stage.

**Verdict**: CLEAN -- 0 critical, 0 high. Three low/informational notes recorded below;
none blocks ratify.

## Coverage matrix

### User stories -> tasks

| Story | Priority | Tasks | Covered |
|---|---|---|---|
| US1 parked-but-shipped contradiction | P1 | T004, T005, T006 | yes |
| US2 nonexistent/unresolvable blocker + absent anchor | P1 | T004, T005, T006 | yes |
| US3 missing/malformed manifest (+ empty-clean) | P2 | T007, T008 | yes |
| US4 wired + counted | P2 | T009, T010, T011 | yes |

### Functional requirements -> tasks

| FR | Where implemented | Note |
|---|---|---|
| FR-001 register DF1 | T005 (@register), T009 (discovery) | implicit (not FR-tagged) |
| FR-002 lazy import yaml, fixed manifest path | T005 | implicit |
| FR-003 edge fields | T002 (seed), T005/T006 (validation) | implicit |
| FR-004 missing/malformed fail-loud | T005, T007, T008 | tagged in T008 phase |
| FR-005 untracked doc / absent anchor | T004, T006 | tagged |
| FR-006 unresolved evidence | T004, T006 | tagged |
| FR-007 parked-but-shipped | T004, T006 | tagged |
| FR-008 no score | T004 (asserts), T005 | tagged |
| FR-009 only listed edges | T005/T006 (no free-scan), T012 | tagged |
| FR-010 static read-only | T005 (no module-scope conn import) | implicit; B1 also guards |
| FR-011 +1 expected id, len-derived | T010, T011 | tagged in scope guard |
| FR-012 generic, no C086 | T002, scope guard | tagged |
| FR-013 ships green (live guard) | T012 | tagged |
| FR-014 no F016/F031-F033 runtime | scope guard | tagged |
| FR-015 ERROR severity | T004 (asserts), T005 | tagged |

### Success criteria -> evidence

| SC | Verified by |
|---|---|
| SC-001 stale park caught, named | T004 (US1), T006 |
| SC-002 nonexistent blocker caught | T004 (US2), T006 |
| SC-003 no vacuous green on missing/malformed | T007, T008 |
| SC-004 +1 id, fail-closed if uncounted | T010, T011 |
| SC-005 manifest reconciles clean | T002, T003, T012 |
| SC-006 no F016 runtime | scope guard, inspection |

## Consistency checks

- **Counts**: 37 -> 38 expected-id move is stated identically across spec assumptions,
  plan, research, quickstart, and tasks (T010/T011). Verified against the live repo:
  `len(EXPECTED_RULE_IDS) == 37` and `rules-manifest.json` has 37 entries today.
  Consistent. The "40 raw @register vs expected set" G6 gap is explicitly named as
  pre-existing and out of scope in spec Assumptions, plan Constitution Check, research,
  and the contract -- no artifact relies on a hard-coded count.
- **Manifest path + key**: `docs/quality/parked-on.yaml` with top-level `edges:` is
  consistent across plan, data-model, contract, quickstart, tasks. No drift vs SC1's
  `status-claims.yaml`/`claims:` (correctly a different file/key).
- **Rule id / module**: `DF1` in `src/retail/rules/parked_on.py`, test
  `tests/unit/test_parked_on.py`, register title consistent between contract and tasks.
- **Severity**: ERROR everywhere (spec Q1/FR-015, plan, data-model finding shape,
  contract). No WARNING residue after clarify resolved the marker.
- **Parked-but-shipped criterion**: optional `shipped_when_tracked` field is described
  identically in FR-007, data-model field table, contract branch 10, and tasks T006.
  Consistent.
- **Empty-manifest posture**: clean pass (spec Q4 / Edge Cases / FR-004 wording /
  contract branch 4 / tasks T007-T008). Consistent.
- **No [NEEDS CLARIFICATION] markers** remain in spec.md (verified: 0 occurrences).

## Constitution / invariant alignment

- Principle I (gate-enforced, non-zero exit): satisfied (FR-001, contract).
- Principle II + hard rule #6 (no F016 start/fork): satisfied (FR-014, SC-006, scope
  guard). No deferred-capability assumption: DF1 reads only tracked text; it does NOT
  assume F016 / F031-F033 runtimes exist -- it records that they do NOT (parked).
- Principle V: no grain/PII/rollup/identity question; carve-out correctly empty; the
  one orchestration call (IL1 F-number) is left open for the human, not answered.
- Principle VII (generic): manifest + rule generic; seeds cite kit features + tracked
  infra specs, no C086 facts.
- Principle VIII (static-first, stdlib core, lazy yaml, fail-loud): satisfied.
- Hard rule 9 (no fake confidence): satisfied (FR-008, categorical).
- Principle IX (ASCII/UTF-8-no-BOM): authored artifacts use -- / ->, no glyphs.

## Findings

| ID | Severity | Finding | Recommendation |
|---|---|---|---|
| A1 | low | FR-001/002/003/010 implemented but not FR-tagged in tasks (covered by T005/T009 implicitly). | Optional: add FR tags to T005/T009 at build time. Non-blocking. |
| A2 | low | The anchor sentences for the five seed edges are not yet pinned to exact roadmap text in the spec (deferred to T002/T003 at build). | Acceptable: anchors copied byte-literal at build; T003 verifies presence before the rule lands. |
| A3 | info | DF1 reuses SC1's Finding/Severity/RuleContext; no new core type. | No action -- minimizes surface, matches sibling. |

**Critical**: 0. **High**: 0.
