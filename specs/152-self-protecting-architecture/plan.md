# Implementation Plan: Self-Protecting Official-First Architecture

**Branch**: `152-self-protecting-architecture`

**Status**: ratified -- Ahmed Shaaban, 2026-08-10. Implementation is authorized
only for the approved tasks in this plan.

**Implementation**: all approved tasks complete and locally validated on
2026-08-10; Final Architecture Audit remains the next state.

## Phase classification

**REQUIRED, NARROW SLICE.** Phase 11 is not already satisfied because two
constructed regressions pass the current protection set. All other audited
invariants are already protected and are excluded from implementation.

## Smallest stable design

1. Extend `ownership_violations()` in the existing independent capability
   oracle so every upstream-backed Seshat-owned entry requires a concrete delta.
   Preserve the stricter existing adapter rule.
2. Add the five missing normalized hashes to the existing Claude Spec Kit
   integration manifest.
3. Add one focused contract test that derives the fourteen-skill closure from
   the capability manifest, reconciles it with the Claude manifest, checks
   normalized hashes and version agreement, and exposes constructible failure
   cases.
4. Update only the two canonical documentary claims that currently say KF-2 is
   open.

No production module is needed. The ownership oracle already lives in tests as
an intentionally independent verifier, and the provenance concern is a
repository vendoring contract enforced by CI-run tests.

## Authority map

| Fact | Existing authority | Change |
| --- | --- | --- |
| Capability owner and Seshat delta | `capabilities.yaml` + independent ownership oracle | strengthen one detector; no new manifest field |
| Spec Kit skill scope | `speckit-workflow-skills.references.skill` | read directly; do not copy the list |
| Vendored bytes | `.specify/integrations/claude.manifest.json` | extend from 9 to 14 skill hashes |
| Spec Kit version | `init-options.json` and the two existing manifests | require agreement; no new version source |
| Generated public bundles | `export_agent_bundles.py` | unchanged; git skills are development-only and not bundle inputs |

## Files expected to change after ratification

| File | Reason |
| --- | --- |
| `tests/unit/_capability_public_ownership.py` | extend the existing delta detector |
| `tests/unit/test_capability_ownership_delta.py` | negative and non-regression tests for the stronger delta contract, in their own module so the O1-O8 inventory suite is unchanged |
| `.specify/integrations/claude.manifest.json` | add the five missing normalized hashes |
| `tests/contract/test_speckit_provenance.py` | full-closure, hash, path, and version contract |
| `docs/capabilities/capabilities.yaml` | replace the KF-2-open update-policy claim with the verified closed contract |
| `docs/capabilities/ownership-audit.md` | append a dated Phase 11 closure note without rewriting history |

Explicitly unchanged: vendored Spec Kit skill bodies, the Spec Kit core
manifest's file list, routes, bundle exporter, integration catalog, runtime
code, readiness, approvals, evidence schemas, dependencies, CI, and feature
fence.

## Implementation sequence

1. Baseline all focused guards on a clean tree.
2. Add failing ownership-oracle tests for upstream-backed non-adapter Seshat
   owners with missing/blank deltas.
3. Strengthen the existing detector and prove official/vendored/internal
   non-wrapper cases remain clean.
4. Add failing provenance tests for current five-file coverage absence, a
   missing entry, drifted content, malformed paths, and version disagreement.
5. Extend the existing Claude manifest with normalized hashes for the five
   files; make the clean contract pass.
6. Run negative proof in a temporary fixture: clean -> pass; seed one missing
   entry and one byte drift -> intended contract fails; restore -> pass.
7. Update the two KF-2 claims only after enforcement passes.
8. Run the focused and repository-level validation named below.

## Error posture

- A missing or malformed owner mapping remains a named ownership violation.
- A blank delta is absent, never a valid declaration.
- A missing/malformed manifest or capability scope fails, never skips.
- An invalid path is rejected before filesystem resolution.
- A content mismatch names the affected file and expected/actual hash.
- Version disagreement names all three claims.
- Line-ending-only changes normalize to LF and do not fail.

## Validation after ratification

```text
python -m pytest tests/unit/test_capability_ownership_delta.py tests/unit/test_capability_inventory.py tests/contract/test_speckit_provenance.py -q --no-cov
python -m pytest tests/contract/test_dbt_ownership_routing.py tests/contract/test_dagster_ownership_routing.py tests/contract/test_powerbi_ownership_routing.py tests/unit/test_dbt_execution_state.py tests/unit/test_readiness_status.py tests/unit/test_spec_status_policy.py tests/unit/test_spec_status_grammar_agreement.py -q --no-cov
python -m seshat.cli check
python scripts/export_agent_bundles.py --check
ruff format --check tests
ruff check tests
```

Broader tests are required only if the ratified implementation expands beyond
the six expected files; such expansion first requires a spec amendment.

## Stop point

Named-human ratification was recorded from Ahmed Shaaban on 2026-08-10.
Implementation may now execute only this plan's approved tasks. The feature
fence remains unchanged, and work stops before the Final Architecture Audit.
