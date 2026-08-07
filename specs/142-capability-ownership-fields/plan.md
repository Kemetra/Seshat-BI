# Implementation Plan: Capability ownership fields

**Spec**: `specs/142-capability-ownership-fields/spec.md`

**Branch**: `142-capability-ownership-fields`

**Created**: 2026-08-07

**Status**: Draft -- not ratified, not started

---

## Summary

Add one optional `ownership:` mapping to entries in
`docs/capabilities/capabilities.yaml`, extend the existing manifest oracle to
validate its token sets and the adapter-delta rule, and classify all 102
entries. No new command, no new gate, no new score.

The migration is **additive and independently landable**: every existing
consumer reads named keys only, so unknown keys are inert. This was verified
empirically before planning (see Technical Context), which is why the plan can
sequence entry batches instead of a lockstep schema bump.

## Technical Context

Verified against `main` at `edfab33`. These are measured facts, not assumptions
-- each determined a planning decision.

| Finding | Location | Planning consequence |
| --- | --- | --- |
| Projection reads a fixed key list via `.get()`, drops unknowns, "degrades rather than crashes" | `src/seshat/capability_inventory.py:172-186` | New keys need no renderer change. Renderer work is optional and deferred. |
| Allowlist derivation reads only `ships`, `references.skill`, `ship_classification`, `id` | `src/seshat/allowlist_derivation.py` | Derived allowlist is byte-identical. No bundle churn. |
| Bundle hashes cover skill-file bytes, not the manifest | `scripts/export_agent_bundles.py:455-456` | `manifest_digest` / `source_sha256` / `output_sha256` unchanged; the drift gate cannot fire on this change. |
| Ship-classification contract asserts named keys only, no key-set closure | `tests/contract/test_capability_ship_classification.py` | No lockstep bump. Entries may land in batches. |
| Oracle walks **every** key and scalar at **every** depth | `tests/unit/_capability_oracle.py:441-456` | Hard naming and typing constraints -- the primary implementation risk. See Risk R1. |
| Five axis constants are dead, enforcing nothing | `src/seshat/capability_inventory.py:35-43` | Must not be incidentally revived. See Risk R3 and FR-010. |
| No JSON Schema exists for the manifest | no hits under `schemas/` | Validation extends the oracle; no schema file to author. |

## Constitution Check

| Principle | Bearing | Verdict |
| --- | --- | --- |
| **II. Depend, Never Fork** | This is the constitutional basis for the feature. The axis makes "who owns this" a declared, reviewable fact, which is how "depend, never fork" becomes auditable rather than aspirational. The `vendored-upstream` token exists to *surface a potential Principle II violation* -- notably the `speckit-*` question. | **Advances the principle.** No fork is created; a fork-detection vocabulary is added. |
| **V. Agent Stops at Judgment Calls** | Three classifications are genuine judgment (OD-1, OD-2, OD-3). The plan routes them to owner rulings and does not let implementation self-answer them. | **Respected.** OD-1/OD-2 block their specific entries, not the whole migration. |
| **VII. C086 Is An Example** | FR-008 clause 3 bans `c086` / `retail_store_sales` literals from ownership values. This is Principle VII enforced mechanically by `tests/unit/test_capability_inventory.py:513-526`. | **Respected**, and the constraint is now traced to its principle rather than to a test. |
| **VIII. Static-First Governance** | Change is static metadata plus a unit-level oracle. No live connection, no DB, no Power BI. | **Respected.** |
| **I. Agent-First, Gate-Enforced** | Deliberately adds no gate (FR-009). Gating is downstream once values exist. | **Consistent** -- see Complexity Tracking for why deferring is the correct call, not a shortcut. |

No principle violation. No amendment required.

## Approach

### Why extend the manifest instead of adding a registry

Issue #592 section C offered "a machine-readable registry (or extend
`capabilities.yaml`)". This plan takes the extend branch. A parallel registry
would need its own drift check against the manifest, recreating precisely the
duplication the issue exists to remove. The manifest is already the control
plane, already loaded by the inventory and the allowlist derivation, and already
guarded by an oracle.

### Why the oracle, not a `seshat check` rule

The oracle (`tests/unit/_capability_oracle.py`) already walks raw manifest
entries and is the manifest's existing truthfulness authority. Reusing it costs
one function per check. A static rule costs nine wiring surfaces and, more
importantly, has nothing to assert against until entries carry values -- the
evidence-gate discipline this kit applies to its own rules. Gating is downstream
of this spec by construction, not by preference.

## Phase sequence

Ordered so that the risky, cheap-to-reverse work lands before the bulk work.

### Phase 1 -- Vocabulary and validation (no data yet)

1. Extend `tests/unit/_capability_oracle.py` with `OWNERSHIP_OWNERS` and
   `OWNERSHIP_SURFACES` token sets and two new axis checks: unknown-token, and
   adapter-missing-delta.
2. Write failing tests first (TDD): an unknown `capability_owner` must be
   rejected; a `seshat-adapter` without `seshat_delta` must be rejected.
3. Confirm O6 stays green with the new *names* present in the oracle's own
   constants -- `capability_owner`, `upstream_project`, `upstream_surface`,
   `upstream_reference`, `seshat_delta`, `canonical_source`,
   `generated_targets`, `overlap_note`, `update_policy`. None contains a
   `NUMERIC_FIELD_HINTS` substring; this is asserted, not assumed.

Phase 1 lands with **zero manifest entries changed**, so it is provably inert.

### Phase 2 -- Pilot on the four known wrappers

Classify only `dbt-transformation-adapter`, `dagster-orchestration-adapter`,
`pbi-mcp-doctor`, `pbir-authoring-adapter` as `seshat-adapter` with upstream
projects and deltas drawn from `ownership-audit.md` section 4 and cross-checked
against `src/seshat/integrations/catalog.py` per FR-007.

Gate: run `export_agent_bundles.py --check` and the full capability test set
here. This is the empirical proof of FR-004 (SC-004) on real data, at four
entries rather than 102.

### Phase 3 -- The six knowledge roots and the governance set

Mechanical, low-judgment: the six `skills/` roots are
`seshat-domain-knowledge`; the readiness/evidence/approval set is
`seshat-governance`. Taken from the audit's KEEP sections.

### Phase 4 -- The remainder, in reviewable batches

Remaining entries in batches small enough to review, each batch a commit. Any
entry whose class is genuinely unclear is left unclassified and listed with a
reason (SC-001) rather than guessed.

### Phase 5 -- Deliberately unclassified list and closeout

Record the unclassified entries and their reasons. Re-run the full gate set.

**OD-1 and OD-2 block only their own entries.** The `speckit-*` aggregate and the
INSPECT-flagged dev-workflow skills stay unclassified pending owner rulings;
they do not block Phases 1-4.

## Risks

### R1 -- The oracle's depth-walking constraints (primary risk)

`_axis_numeric_field_names` fails on any key at any depth containing `score`,
`maturity`, `confidence`, `completeness`, or `health`.
`_axis_numeric_scalars` fails on any bare `int`/`float` at any depth.

This axis is exactly the kind of metadata that invites an "ownership maturity"
or "confidence level" field, and a version or year value is naturally written
unquoted.

**Mitigation**: the field vocabulary is fixed by FR-001 and contains no
offending substring; FR-008 requires every version/year/count to be a quoted
string. Phase 1 asserts this before any data lands.

### R2 -- Silent divergence from `catalog.py`

`upstream_reference` could drift from the coordinate in `catalog.py:61-67`.

**Mitigation**: FR-007 makes the catalog authoritative. Phase 2 cross-checks all
four wrappers by hand. A future automated check is possible but is section-D
work, out of scope.

### R3 -- Incidentally reviving the dead constants

Adding ownership tokens near `capability_inventory.py:35-43` invites "tidying"
the five dead constants into live enforcement, which would change behavior for
`state`/`authority`/`surface`/`requirements`/`provenance` -- and would fail
immediately on the live `surface: product-module` value.

**Mitigation**: FR-010 forbids it. Ownership tokens live in the oracle, not
alongside the dead constants. Recorded as OD-3 for a separate spec.

### R4 -- Scope creep into section D

The overlap gate is adjacent and tempting.

**Mitigation**: an explicit Non-goal with a stated reason (no filled target
exists yet). Any task proposing a `seshat check` rule is out of scope by
definition.

## Complexity Tracking

| Deferred item | Why deferring is correct |
| --- | --- |
| Section D overlap gate | No filled target exists until this spec produces values. Building the rule first would mean writing assertions against data that does not exist. |
| Rendering ownership in `capability_inventory` output | The projection drops unknown keys harmlessly. Surfacing the axis is a separate, additive UX change with its own closed-schema contract (`DECLARED_RECORD_FIELDS`) to extend. |
| Making the five dead constants live | A behavior change to five unrelated axes. Belongs in its own spec (OD-3); would fail today on a live value. |
| Automated `catalog.py` cross-check | Section-D shaped. Manual for four entries now. |

## Verification

Run at the end of every phase, not only at the end:

```
seshat check
ruff format --check src tests scripts && ruff check src tests scripts
python scripts/export_agent_bundles.py --check
python -m pytest tests/unit/test_capability_inventory.py \
  tests/contract/test_capability_ship_classification.py \
  tests/contract/test_generated_agent_bundles.py -q --no-cov
```

Expected: `seshat check` exit 0 with the pre-existing RS1 warning and no new
finding; bundle drift PASS; all tests green.

## What this plan will not do

- Not merge to `main`, not push to `main`, not self-ratify.
- Not promote this spec into the `<!-- SPECKIT -->` fence
  (`.specify/feature.json` points at `specs/138-agent-driven-bundle`; the fence
  carries exactly one plan path by contract).
- Not delete, merge, or consolidate any capability.
- Not answer OD-1, OD-2, or OD-3.
