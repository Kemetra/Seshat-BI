# Fixture descriptors: Decision Change Impact Map

**Feature**: `132-decision-change-impact-map` | **Date**: 2026-07-15

Descriptors for the fixture families the tasks require. Each is a small committed-tree shape (a
fixture Decision Store + fixture downstream artifacts) materialized under `tests/` at implement time.
No fixture carries a worked-example's real table/column/policy/number/client/human values as a default
(SC-012); example-shaped values, if any, stay inside the fixture and never become product defaults.

| Fixture | Shape | Exercises | Expected result |
| --- | --- | --- | --- |
| `direct/` | one approved-then-superseded decision + a metric contract whose scope tag matches | US1, FR-007/008/009 | contract in `affected[]`, `relation:"direct"`, resolvable `evidence_paths`, affected stage from readiness projection |
| `transitive/` | direct metric contract + a dashboard artifact depending on it via an existing lineage edge | US2, FR-009/010/011, SC-002 | dashboard in `affected[]`, `relation:"transitive"`, full ordered edge evidence chain |
| `cycle/` | a dependency graph with a cycle among artifacts | US2, FR-014, SC-006 | walk terminates; `cycles[]` records the cycle; no cycle reported as a completed transitive path |
| `stale_evidence/` | approved decision whose cited evidence file's current identity ≠ recorded identity | US1, FR-003(b)/005 | subject `trigger` includes `evidence_stale`; directly-derived artifacts listed |
| `missing_ref/` | a decision scope tag resolving to zero artifacts + a lineage edge with a missing target | US2, FR-012/013, SC-003/004 | two `incomplete_lineage[]` warnings (`unresolved_scope_tag`, `unfollowable_edge`); nothing recorded "unaffected"; no inferred edge |
| `conflict/` | two active in-scope decisions of the same type on the same scope key | US4, FR-020 | `blocking_condition.kind = active_scope_conflict`; not silently resolved |
| `incomplete_lineage/` | mix of resolvable and unresolvable references in one run | US2, FR-015, INV-1 | `affected[]` and `incomplete_lineage[]` both non-empty and disjoint |
| `dangling_pointer/` | a supersession chain including a `supersedes`/`superseded_by` that does not resolve | US3, FR-016, SC-007 | resolvable chain in order + one `incomplete_lineage[]` warning (`dangling_supersession_pointer`); no fabricated history |
| `absent_store/` | no Decision Store present | US4, FR-019 | `blocking_condition.kind = absent_store`; no empty-clean "no impact" |
| `malformed_store/` | Decision Store that fails to load | US4, FR-019, SC-008 | `blocking_condition.kind = malformed_store`; write refused |
| `preview/` | approved decision NOT yet superseded | US3, FR-004 | preview `affected[]` produced; `is_preview:true`; zero state writes |
| `no_leak/` | a document that would carry a secret/PII/connection string | SC-011, NFR-003 | `scan_disclosure` blocks the write |
| `non_approved_subject/` | a decision that is still `proposed`/`pending` (never approved) | US1, FR-003 (approved-only), spec Edge Case "Decision never approved" | `blocking_condition.kind == "invalid_subject"`, `subject == null`; reported as *not a valid impact-map subject*, NOT as "no impact" |

## Cross-cutting assertions (apply to every fixture)

- No numeric score anywhere (INV-4 / SC-005).
- No state file written; no decision/approval/supersession pointer/`readiness-status.yaml` mutated
  (FR-024/025, SC-001 clause).
- Machine and human forms carry identical content (SC-009).
- Byte-determinism modulo `generated_at` (SC-010) on any fixture with a stable resolvable result.
