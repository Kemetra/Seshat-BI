# Implementation Plan: 5-Place Wiring Meta-Gate / Registry Lockstep Self-Check

**Branch**: `061-wiring-meta-gate` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/061-wiring-meta-gate/spec.md`

## Summary

Add a single test-only, standard-library-only meta-gate that proves the five
rule-registry wiring places stay in mutual lockstep and closes the one
currently-un-guarded seam (package import list == public export list == on-disk
submodule set). The meta-gate treats the deterministically re-loaded live
registry as ground truth and cross-checks it against the four other places
(package symmetry, expected-rule-id set, golden manifest, golden posture record),
failing closed with a message that names the disagreeing place and offending
symbol/id. It adds NO runtime rule, NO expected-rule-id, and NO new persisted
golden file; it reads committed text plus the in-process registry object and
executes nothing (no database/network/Power BI/DAX/agent).

## Technical Context

**Language/Version**: Python 3.11+ (repo runs 3.12 locally, 3.13 in CI); the
test uses only the standard library.

**Primary Dependencies**: None new. Standard library only (`importlib`,
`pkgutil`, `json`, `pathlib`). Reuses existing in-repo modules:
`retail.registry`, `retail.rules` (package), `retail.manifest`,
`retail.severity_posture`, and the existing `EXPECTED_RULE_IDS` test constant.

**Storage**: None. Reads two already-committed golden files
(`docs/rules/rules-manifest.json`, `docs/rules/severity-posture.json`) statically.
Writes no new file.

**Testing**: pytest, `@pytest.mark.unit`, in the existing `tests/unit/` lane.

**Target Platform**: Cross-platform CI (Linux) + Windows local; path handling
must be MAX_PATH-safe.

**Project Type**: Single project (governance/linter kit). New artifact is one
unit-test module.

**Performance Goals**: Same order of magnitude as the existing wiring/snapshot
tests (sub-second); it does one deterministic registry reload plus a few set
comparisons and two small JSON reads.

**Constraints**: stdlib-only; no DB/network/Power BI/DAX/agent execution
(Principle VIII); fail-closed non-zero on any divergence (Principle I); UTF-8 no
BOM, `\n`, deterministic ordering, MAX_PATH-safe (Principle IX); zero
example-domain identifiers (Principle VII).

**Scale/Scope**: 40 registered rule ids today; 16 on-disk rule submodules; one
non-registered governance surface (ADR-0007). One new test module, no source
changes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Agent-First, Gate-Enforced** -- PASS. The contract is a failing test /
  non-zero exit, not prose; FR-007 mandates fail-closed, no advisory-only mode.
- **II. Depend, Never Fork** -- PASS. No new third-party dependency (FR-011);
  reuses existing in-repo seams.
- **III. Medallion, Postgres-First** -- N/A. No data-tier work; governance
  infrastructure only.
- **IV. Source Mapping Before Silver** -- N/A. No silver/gold artifacts touched.
- **V. Agent Stops at Judgment Calls** -- PASS. No business-data judgment calls
  (grain/PII/rollup/identity) exist for this governance-internal feature; the one
  deferred decision (roadmap-row assignment) is recorded for the human and is not
  build-blocking.
- **VI. Defaults Then Deviations** -- N/A. No cleaning defaults involved.
- **VII. C086 Is An Example** -- PASS. FR-014: zero example-domain identifiers;
  the meta-gate references only generic registry infrastructure and does not plant
  domain fixtures.
- **VIII. Static-First Governance, Live Deferred** -- PASS. FR-012: reads
  committed text + in-process registry; no query/DAX/agent/DB/network. The
  posture cross-check reads the committed golden file statically rather than
  re-observing (which would inherit a subprocess dependency) -- resolved in
  Clarifications.
- **IX. Secrets and Reproducibility** -- PASS. FR-013: deterministic ordering,
  UTF-8 no BOM, `\n`, MAX_PATH-safe; no secrets read or written.

No violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/061-wiring-meta-gate/
+-- plan.md              # This file
+-- research.md          # Phase 0 output
+-- data-model.md        # Phase 1 output
+-- quickstart.md        # Phase 1 output
+-- contracts/
|   `-- meta-gate-contract.md   # the check contract (assertions + failure shape)
+-- checklists/
|   `-- requirements.md  # spec quality checklist (from specify)
+-- spec.md
`-- tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/retail/
+-- registry.py          # (existing) all_rules() -> ground truth; unchanged
+-- rules/
|   `-- __init__.py      # (existing) import list + __all__; the un-guarded seam; unchanged
+-- manifest.py          # (existing) build_manifest(); read for cross-check; unchanged
`-- severity_posture.py  # (existing) posture generator; golden read statically; unchanged

docs/rules/
+-- rules-manifest.json      # (existing golden) read statically; unchanged
`-- severity-posture.json    # (existing golden) read statically; unchanged

tests/unit/
+-- test_rules_wiring.py         # (existing) EXPECTED_RULE_IDS lives here; unchanged
+-- test_rules_manifest_snapshot.py  # (existing) unchanged
+-- test_severity_posture.py     # (existing) unchanged
`-- test_wiring_meta_gate.py     # NEW: the single lockstep meta-gate test module
```

**Structure Decision**: Single-project layout. The ONLY new artifact is
`tests/unit/test_wiring_meta_gate.py`. No `src/` change, no new golden file, no
package/`__init__` edit. The meta-gate imports the existing seams read-only. This
mirrors how the manifest and posture guards were added as test-only assertions.

## Phase 0: Research

See [research.md](./research.md). Key decisions:
- Deterministic registry reload reusing the same clear-and-reload technique the
  existing `test_registered_rule_ids_match_expected_set` uses (avoids depending
  on global registry state left by sibling tests).
- Static read of the two golden JSON files (not re-generation, not re-observation)
  -- keeps the check purely static and avoids the posture subprocess dependency.
- Explicit ADR-0007 exemption list (constant in the test) rather than an implicit
  "ignore anything without a rule id".
- ADD (not REPLACE): existing per-place tests stay; the meta-gate is a fourth
  cross-referencing check.

## Phase 1: Design & Contracts

- [data-model.md](./data-model.md): the conceptual entities (live-registry
  snapshot, wiring place, exemption list, lockstep report) -- no persisted schema.
- [contracts/meta-gate-contract.md](./contracts/meta-gate-contract.md): the exact
  assertions the meta-gate makes, the fail-closed conditions, and the failure
  message shape.
- [quickstart.md](./quickstart.md): how to run the meta-gate and how to reproduce
  each fail-closed case.

## Complexity Tracking

No constitution violations; table intentionally omitted.
