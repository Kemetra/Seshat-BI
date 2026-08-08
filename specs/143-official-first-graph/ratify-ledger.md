# Ratify ledger: spec 143 -- public capability graph integrity

**Branch**: `143-official-first-graph`

**Prepared**: 2026-08-07

**Status**: RATIFIED by Ahmed Shaaban, 2026-08-07 -- Phase 1 implementation permitted

## Recommendation

**READY FOR HUMAN RATIFICATION.** The phase is bounded to control-plane metadata
and fail-closed contracts. It changes no runtime, router content, executor,
integration, readiness gate, dependency, MCP, or generated bundle.

## Chain

```text
repository truth -> phase classification -> specify -> plan -> tasks ->
cross-artifact analysis -> adversarial plan review -> human ratification
```

| Artifact | State |
| --- | --- |
| `spec.md` | Draft; 13 functional requirements, 6 success criteria |
| `plan.md` | Required-phase evidence, constitution check, 5 design decisions, 4 risks |
| `tasks.md` | 16 dependency-ordered tasks; every implementation box unchecked |
| `analysis.md` | Four findings found during review and resolved; 19/19 requirement outcomes covered |
| `plan-review.md` | Default-refuted review; ready for ratification |

## Approval-time validation

| Command | Exit | Result | Classification |
| --- | ---: | --- | --- |
| `python scripts/export_agent_bundles.py --check` | 0 | Generated Claude and Codex bundles match reviewed inputs. | PASS |
| Focused baseline capability/public/bundle tests | 0 | 67 passed. | PASS |
| Active Spec Kit fence contract without temp override | nonzero | AppData pytest temp denied before collection. | ENVIRONMENTAL |
| Active Spec Kit fence contract with isolated writable temp | 0 | 6 passed. | PASS |
| `git diff --check` | 0 | No whitespace errors. | PASS |

## Decisions requiring ratification

1. `seshat-bi-public-router` is currently a `seshat-orchestrator`.
2. `powerbi-workflows-public-router` is currently a `seshat-orchestrator`, not a
   Microsoft adapter, because official delegation is not implemented yet.
3. A public capability's canonical source must be a tracked authored file and
   cannot be a generated Claude/Codex projection.
4. The integrity gate extends the existing independent capability oracle; it
   does not add a runtime checker or registry.

## Ratification record

Ratifier: Ahmed Shaaban

Date: 2026-08-07

Decision: Ratified; Phase 1 implementation authorized.

Recorded from Ahmed Shaaban's explicit instruction: "i ahmed shaaban ratify
spec 143 on 2026-08-07 and authorize Phase 1 implementation".

## What ratification permits

Implementation of Phase 1 tasks only. It does not authorize later roadmap
phases, a commit, push, PR, merge, publication, or any Power BI/dbt/Dagster
execution change.

## Local implementation closeout

**State**: Phase 1 implementation complete locally on 2026-08-07; unstaged and
not landed on `main`.

The specification remains `ratified`. Repository policy reserves
`implemented` for a capability that exists on `main`, and no commit or landing
was authorized.

| Evidence | Result |
| --- | --- |
| Public capability graph | 21 shipped public skills; 0 integrity violations |
| Capability inventory tests | 57 passed |
| Public/bundle/plugin contracts | 45 passed |
| Deterministic bundle check | PASS; generated roots have zero diff |
| Static Seshat gate | Exit 0; one unchanged pre-existing RS1 warning |
| Scope | Metadata, docs, independent oracle/tests, and Spec Kit artifacts only |

The full results and the intermediate environmental/fail-closed findings are
recorded in `evidence/validation.md`; the complete diff review is recorded in
`evidence/scope-review.md`.
