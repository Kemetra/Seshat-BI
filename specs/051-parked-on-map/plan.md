# Implementation Plan: Parked-On Map / Parked-On Dependency Map (DF1 -- F016 Bottleneck-Edge Reconciler)

**Branch**: `051-parked-on-map` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/051-parked-on-map/spec.md`

## Summary

Add a static governance rule DF1 to the `retail check` core that reconciles declared
PARKED-ON DEPENDENCY EDGES against committed evidence. A new human-curated manifest
`docs/quality/parked-on.yaml` declares each edge as `{id, blocked, parked_on, doc,
anchor, evidence, shipped_when_tracked?}`. DF1 is a pure `(RuleContext -> findings)`
function in the existing rule contract, a near-clean lift of the shipped SC1
reconciler (`src/retail/rules/status_claims.py`): lazy `import yaml`,
manifest-in-`tracked_files` guard, fail-loud on missing/malformed input, per-entry
resolution against the tracked-files set with ERROR on a contradiction. DF1 mirrors
SC1's two extra reads -- it confirms the edge's `doc` is tracked and that the `anchor`
sentence is literally present in that doc -- and applies the fail-closed-both-directions
shape to parked-on edges: an `evidence` file that is not tracked is an ERROR (a
nonexistent/unresolvable blocker), and a `shipped_when_tracked` artifact that IS tracked
is an ERROR (a parked-but-shipped contradiction, the static analog of SC1's
`planned`-but-now-tracked stale marker). The expected rule-id set moves 37 -> 38 in the
same change so the wiring drift guard stays honest, and `docs/rules/rules-manifest.json`
is regenerated via `retail manifest` (guarded by the rule-registry snapshot test). The
manifest is seeded with the v1 F016 bottleneck cluster -- edges citing already-tracked
deferred-spec / spec evidence -- so DF1 ships GREEN on the feature branch.

## Technical Context

**Language/Version**: Python 3.12+ (matches the existing `src/retail/` core; CI runs 3.13).

**Primary Dependencies**: Standard library only in the core import path. The manifest
parse uses a LAZY `import yaml` inside the rule body (the exact pattern SC1/A1 use) --
`PyYAML` is a dev/optional dependency, NOT a core import-path dependency. No new
dependency: the anchor check is a stdlib substring test against the cited roadmap doc's
text; evidence/shipped resolution is a membership test against the tracked-files set.

**Storage**: N/A -- reads tracked text files (the parked-on manifest, plus each cited
roadmap `doc`) and the tracked-files set; writes nothing at runtime.

**Testing**: pytest, `@pytest.mark.unit`. New `tests/unit/test_parked_on.py` mirrors
`test_status_claims.py`: a `_stage` helper writes a synthetic manifest + synthetic
roadmap docs + synthetic evidence/shipped artifacts under `tmp_path` and returns a real
`RuleContext`; plus one live-manifest-vs-real-repo guard (shells `git ls-files`, builds
a real `RuleContext`, asserts zero findings against the seeded manifest).

**Target Platform**: CI (Linux/Windows) under `retail check`; no DB, no network.

**Project Type**: Single project -- a governance rule submodule in `src/retail/rules/`.

**Performance Goals**: Negligible -- one small-manifest read plus, per edge, one
membership test against the tracked set (evidence + optional shipped artifact) and one
substring scan of one cited roadmap doc. No measurable impact on `retail check` runtime.

**Constraints**: stdlib-only core import path (Principle VIII); pure read-only, no
execution / no connection (Principle VIII, never-execute invariant -- B1 itself would
flag a module-scope DB/network import); fail-loud on missing/malformed input (never
vacuously green, but a present-and-empty manifest passes clean per spec Q4); strictly
categorical -- no numeric confidence/readiness value emitted (Hard rule 9); generic-only
schema + messages, no C086/pharmacy specifics in rule or seed (Principle VII). ASCII +
UTF-8-no-BOM in all authored text (Principle IX). MUST NOT add/start/wire/vendor F016 or
any F031-F033 runtime (hard rule #6, Principle II, YAGNI).

**Scale/Scope**: One new rule module (`src/retail/rules/parked_on.py`), one new manifest
(`docs/quality/parked-on.yaml`), one new test file (`tests/unit/test_parked_on.py`), the
`EXPECTED_RULE_IDS` 37->38 update, the rule-package wiring edit
(`src/retail/rules/__init__.py`), the regenerated `docs/rules/rules-manifest.json`
(37->38 entries via `retail manifest`), and a roadmap ledger row. The live set holds 37
ids today (S1-S8, D1-D11, R1, A1, A3, B1, B3, C1, C2, G1-G6, P1, P2, PP1, SC1).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS. DF1 is an enforced
  non-zero-exit static rule under `retail check`; an unresolved/contradicted parked-on
  edge fails closed (ERROR, spec Q1). It advises nothing -- the gate disposes.
- **Principle II (Depend, Never Fork) + hard rule #6**: PASS. F016 is the gated
  execution adapter at the bottom of the stack; DF1 MAPS the parked-on edges to it but
  adds zero F016/execution-adapter machinery. No `.pbix`/connection/MCP code, no
  F031-F033 runtime. The only new artifacts are the DF1 rule, its manifest, the wiring
  edits, the regenerated manifest, and a roadmap ledger row (FR-014, SC-006).
- **Principle V (Agent Stops at Judgment Calls)**: HONORED / N/A carve-out. DF1
  surfaces NO grain/uniqueness, PII publish-safety, business rollup/segment, or
  product-identity question -- it reconciles dependency edges against file existence and
  committed text. The five build-relevant ambiguities (severity, parked-but-shipped
  criterion, v1 edge inventory, empty-manifest posture, amendment/stage placement) were
  resolved by the advisor on reversible defaults in spec ## Clarifications; none is a
  Principle-V ruling. The one non-Principle-V orchestration call (IL1 roadmap F-number)
  is recorded "Open for the human" and left for ratify, not answered here.
- **Principle VII (C086 Is An Example, Not The Schema)**: PASS. The manifest schema
  and the rule are generic dependency-edge machinery; no pharmacy / C086 doc path,
  artifact, value, segment, or PII token is hardcoded in the rule or seeded as an edge.
  Test fixtures use synthetic doc/artifact paths and anchors. The seeded edges reference
  generic kit roadmap features (F016 and its named dependents) + tracked deferred-spec /
  spec files -- repo-infrastructure paths, not worked-example values.
- **Principle VIII (Static-First Governance, Live Deferred)**: PASS. DF1 is a pure
  static read of committed text + the tracked-files set. Core import path stays
  stdlib-only (lazy `import yaml`, stdlib substring anchor check, no markdown dep, no
  network, no DB). It fails loud on missing/malformed/absent-anchor/unresolved-evidence
  input. It opens no connection and executes nothing. ERROR is the defensible posture
  for a proven contradiction (spec Q1).
- **Hard rule 9 (No fake confidence)**: PASS. DF1 is strictly categorical: an edge
  reconciles against the evidence or it does not. No numeric confidence score, readiness
  percentage, or graded value is computed or emitted -- findings are yes/no statements.
- **Principle IX (Secrets and Reproducibility)**: PASS. No secrets; all authored text
  is ASCII + UTF-8-no-BOM (`--` and `->`, no glyphs); paths stay short.
- **Wiring symmetry (roadmap discipline)**: PASS. `EXPECTED_RULE_IDS` is updated
  37->38 in the SAME change as the rule, its package wiring, and the regenerated
  `rules-manifest.json`. The count is derived from `len(EXPECTED_RULE_IDS)`, never a
  hard-coded number; the wiring test + rule-registry snapshot are the guards. The known
  G6-wiring-latent-gap (40 raw `@register` occurrences vs the expected-id set) is
  pre-existing and out of scope -- this change adds exactly one new expected id and does
  not depend on the raw-occurrence count.
- **Ship-green discipline**: PASS. The seeded manifest cites only already-tracked
  evidence and parks that the repository confirms (no `shipped_when_tracked` artifact
  present for a still-parked target), so an enforced ERROR rule does not land RED on the
  feature branch (FR-013, SC-005).

**Result**: No violations. No entries in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/051-parked-on-map/
|-- plan.md              # This file
|-- spec.md              # Feature spec (stages 2-3)
|-- research.md          # Phase 0 output
|-- data-model.md        # Phase 1 output
|-- quickstart.md        # Phase 1 output
|-- contracts/
|   `-- df1-rule-contract.md  # Phase 1 output (the rule's input/output contract)
|-- checklists/
|   `-- requirements.md  # spec quality checklist
|-- analysis.md          # Stage 5 (/speckit-analyze) output
|-- plan-review.md       # Stage 6 adversarial review output
`-- tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/retail/
|-- core.py                  # Finding / Severity / RuleContext (UNCHANGED, reused)
|-- registry.py              # @register decorator + all_rules() (UNCHANGED, reused)
|-- runner.py                # build_context / git ls-files (UNCHANGED, reused)
|-- manifest.py              # render/write rules-manifest.json (UNCHANGED, reused)
`-- rules/
    |-- __init__.py          # EDIT: add parked_on to import tuple + __all__
    |-- status_claims.py     # SC1 sibling (UNCHANGED, read as the shape to mirror)
    `-- parked_on.py         # NEW: the DF1 rule

tests/
`-- unit/
    |-- test_rules_wiring.py     # EDIT: add "DF1" to EXPECTED_RULE_IDS (37 -> 38)
    |-- test_status_claims.py    # SC1 tests (UNCHANGED, read as the shape to mirror)
    `-- test_parked_on.py        # NEW: TDD for DF1 incl. live manifest-vs-real-repo guard

docs/
|-- quality/parked-on.yaml                 # NEW: the human-curated parked-on edge manifest (seeded)
|-- rules/rules-manifest.json              # EDIT (regenerated via `retail manifest`): 37 -> 38 entries
`-- roadmap/roadmap.md                     # EDIT: ledger row recording DF1 + 37->38 note (read-only for anchors)
```

**Structure Decision**: Single project; DF1 ships as a NEW submodule
`src/retail/rules/parked_on.py` (rather than folding into `status_claims.py`) to keep
each rule module focused and because DF1 reads a different manifest with
parked-on-edge semantics. The new submodule MUST be added to
`src/retail/rules/__init__.py` (import tuple + `__all__`) to be discovered --
`test_all_submodules_importable` derives the list via `pkgutil`, so an unimported new
module is caught; `__init__.py` is the single wiring step for discovery. The
`rules-manifest.json` regeneration is a mechanical `retail manifest` run after the rule
is wired, guarded by the rule-registry snapshot test.

## Phase 0 -- Research

See [research.md](./research.md). No open unknowns: the SC1 sibling is an exact
template, the rule-context/registry/manifest seams are confirmed, the 37-id baseline is
verified, and the v1 edge inventory's evidence files are confirmed tracked. The only
deliberate divergence from SC1 (the optional `shipped_when_tracked` field for the
parked-but-shipped branch) is documented there.

## Phase 1 -- Design

See [data-model.md](./data-model.md) (the parked-on edge / manifest schema and the
finding shapes), [contracts/df1-rule-contract.md](./contracts/df1-rule-contract.md)
(DF1's input/output contract and every fail-loud branch), and
[quickstart.md](./quickstart.md) (how to run DF1 locally + regenerate the manifest).

## Complexity Tracking

> No Constitution Check violations. This section is intentionally empty.
