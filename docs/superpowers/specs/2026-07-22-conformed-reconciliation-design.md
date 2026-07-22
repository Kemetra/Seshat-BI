# Design — #418 remainder: cross-star conformed-dimension reconciliation

**Date:** 2026-07-22
**Issue:** #418 remainder (the three cross-table items deferred from PR #419).
**Scope:** a new shared star-discovery module; `src/seshat/dbt/scaffold/`
(`model_plan.py`, `orchestrator.py`); `src/seshat/rules/conformed_dimension.py`
(refactor to consume the shared module — no behavior change); tests.

## Problem

PR #419 shipped conformed-dimension reuse: a non-owner star `ref()`s a conformed
dim owned by another star (owner = `stars[0]` in
`docs/quality/conformed-dimension-map.yaml`) instead of re-emitting a colliding
model. It runs with only the reuser's map + the conformed-map (status/stars). Three
gaps remain, all needing ONE capability — a **cross-table view of the owner star's
dimension** (its declared attributes + surrogate key):

1. **All-dims-reused refused.** A star whose dims are *all* owned elsewhere
   currently raises `ScaffoldError` (it would own no dim model). The textbook
   fully-conformed reuser (a returns star sharing only `dim_customer` + `dim_date`).
2. **Owner not validated.** `stars[0]` is trusted; a mistyped/absent owner, or one
   that does not actually declare the dim, yields a dangling `ref()` caught only at
   `dbt parse`, not a clean scaffold-time refusal.
3. **Reuser-only attributes silently lost.** HR1 permits divergent attribute *sets*
   across a conformed dim's stars. A reuser attribute the owner's dim lacks vanishes
   (the reuser emits no dim model; the owner's does not carry it).

All three are **latent today** — no conformed-dimension name collision exists in the
committed tree (`test_hr1_clean_on_real_committed_tree`).

## The shared capability — one authority on "what a star is"

The reconciliation needs exactly what HR1 already computes: discover every
`mappings/*/source-map.yaml`, resolve each to its governed star id
(`meta.table_id` → `source_id` → directory), and extract each star's dimensions
(bare name → raw dim dict with `attributes` + `surrogate_key`). HR1 has these as
private helpers (`_discover_stars`, `_star_dimensions`, `_star_id`, `_bare`,
`_is_star`, `_add_dim`).

**Decision: extract them into a small shared module** — `src/seshat/dbt/stars.py`
(pure, stdlib + lazy-`yaml`, no DB, no rules-package import). Both HR1 and scaffold
import it, so the governance gate and the generator can never disagree on star
identity or dimension discovery. HR1 is refactored to delegate to the module
(behavior-preserving — its existing tests are the regression guard). This also
retires the `_governed_star_id` DUPLICATE scaffold added in #419 (which mirrored
`_star_id` by hand) in favor of the shared function — closing the drift risk #419
only papered over.

Public surface of `seshat.dbt.stars`:
- `star_id(document: dict, table_dir: str) -> str`
- `is_star(document: dict) -> bool`
- `star_dimensions(document: dict) -> dict[str, dict]`  (bare name → raw dim)
- `discover_stars(root: Path, *, committed: bool) -> dict[str, dict]`
  (governed star id → parsed source-map document)

`discover_stars` reads **committed HEAD** state when `committed=True` (scaffold's
posture — the map is an ownership authority, #419) by resolving each tracked
`mappings/*/source-map.yaml` via `git show HEAD:<path>`; HR1 keeps its worktree
read (`committed=False`) via the `RuleContext` it already holds. Git/read failures
fail SAFE to "star not found" (→ owner-existence refusal below), never a traceback.

## Component changes

| Component | Change |
|---|---|
| `seshat/dbt/stars.py` (NEW) | The extracted discovery primitives above. Pure; lazy `yaml`. |
| `rules/conformed_dimension.py` | Delete the local `_star_id`/`_star_dimensions`/`_is_star`/`_add_dim`/`_bare`/`_discover_stars`; import from `seshat.dbt.stars`. No behavior change (existing HR1 tests unchanged and green). |
| `scaffold/model_plan.py` | Replace `_governed_star_id` with `stars.star_id`. `_partition_dimensions` gains the reconciliation (below). |
| `scaffold/orchestrator.py` | `_build_plan` resolves + passes an `owner_lookup` (owner star id → its `star_dimensions`) built from `stars.discover_stars(root, committed=True)`. |

## Reconciliation logic (in `_partition_dimensions` / a new `_reconcile_reuse`)

For each dim the reuser REUSES (owner = `stars[0]`), before dropping its model:

1. **Owner existence (#418-2).** Look up the owner star id in the discovered set.
   - Owner star not found (no mapping resolves to it), OR the owner star does not
     declare a dim of this bare name → **`ScaffoldError`**: name the dim, the
     declared owner, and that no governed owner star materializes it. (Fail closed
     at scaffold time, not a dangling `dbt parse` ref.)
2. **Attribute divergence (#418-3).** Compare the reuser's declared attributes for
   the dim against the owner's.
   - Any attribute the reuser declares that the owner's dim does NOT carry →
     **`ScaffoldError`**: name the missing attribute(s) and both stars, and state
     the resolution (add the attribute to the owner star, or declare the dim
     `distinct`). A conformed dimension is ONE shared entity; scaffold never
     silently drops a governed field and never mutates the owner's model to merge.
   - The reverse (owner has attributes the reuser omits) is fine — the reuser
     simply uses the shared canonical dim.
3. **Only if both pass** is the dim reused (dropped from `owned`, kept as a fact FK
   + `ref()`), exactly as #419.

## Item #1 — allow the zero-owned-dim plan

Remove the "at least one owned dimension is required" refusal. A star whose dims are
all validly reused emits its fact + staging + audit and NO dim models; its fact FKs
`ref()` the owners' dims. `evidence._validate_parity_set` requires
`dim_subjects == built dim_* models` exactly, which holds for the empty set (the
audit emits zero `dimension_member_count` rows — verified: the factless-fact path
already exercises an explicit empty required-subject set). The staging model still
requires ≥1 kept column (unchanged). This is gated behind items #2/#3 passing, so a
zero-owned plan only ships when every reused dim is validated against a real,
attribute-compatible owner.

## Error handling

Every new failure is a fail-closed `ScaffoldError` with an actionable message
(missing owner / missing attribute + the fix), consistent with the existing
scaffold governance codes. Discovery I/O (git, YAML) failing → the star is treated
as not-found → the owner-existence refusal fires (never a traceback, never a
silent pass). No self-granted merges, no cross-table writes.

## Testing (TDD, driver-free)

Shared module (`test_stars.py`): `star_id` resolution order; `star_dimensions`
(explicit + date, degenerate excluded); `discover_stars` committed vs worktree;
git/read failure → empty. HR1 regression: its full existing suite stays green after
the delegation refactor (the behavior-preserving proof).

Reconciliation (`test_scaffold_conformed_reuse.py`, extending #419's):
- owner star present + attribute-compatible → reuse works as #419 (regression).
- owner star id resolves to NO mapping → `ScaffoldError` names the owner.
- owner mapping exists but does not declare the dim → `ScaffoldError`.
- reuser declares an attribute the owner lacks → `ScaffoldError` names it + both
  stars; owner-superset (reuser omits some) → OK.
- all dims reused (validated owners) → zero-owned plan builds; fact + staging +
  audit present; `_model_contract` zero blockers; `_validate_parity_set` exact.
- committed-vs-worktree: an uncommitted owner map edit is not seen (reads HEAD).

## Out of scope (YAGNI)

- No MERGE of divergent attributes / no rewriting the owner's emitted model.
- No change to the conformed-map SHAPE or to HR1's rule semantics (only its
  internals are relocated).
- No `dbt run`/`parse` execution (scaffold targets the static gate).
- No auto-reconciliation of stale generated files on re-scaffold (separate #418
  note; still a documented manual step).
