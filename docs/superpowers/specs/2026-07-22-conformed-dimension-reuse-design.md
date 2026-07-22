# Design — #418-P1: conformed-dimension reuse across stars in `seshat dbt scaffold`

**Date:** 2026-07-22
**Issue:** #418 item 1 (P1), deferred from PR #415 (`seshat dbt scaffold`, #406).
**Scope:** `src/seshat/dbt/scaffold/` (`model_plan.py`, `orchestrator.py`); tests.

## Problem

`orchestrator._mart_files` writes each dimension to
`dbt/models/marts/<table_id>/<dim.name>.sql`. When a SECOND governed table
declares a CONFORMED dimension already built by another star (e.g.
`dim_customer` in both a sales star and a returns star), scaffold emits a second
model file with the SAME dbt model name. dbt requires globally-unique model
names, so `dbt parse` fails. Multi-star conformed dimensions are a first-class
Kimball concept; the single-table generator shipped in #406 cannot express them.

## Authority reuse — no new state file

The repo ALREADY has the authority on cross-star conformance:
`docs/quality/conformed-dimension-map.yaml`, enforced by the HR1 rule
(`src/seshat/rules/conformed_dimension.py`). Its shape:

```yaml
dimensions:
  <bare_dimension_name>:        # gold_star.dimensions[].name, schema prefix stripped
    status: conformed           # conformed | distinct (the only valid values)
    stars: [<table_id_a>, <table_id_b>]
```

HR1 already fails closed if a `conformed` dim's `surrogate_key` diverges across
its stars. Scaffold READS this same map — it never authors it, never adds a new
cross-table state file, and never decides conformance itself (a Principle-V human
judgment authored once in the map).

## The owner rule (deterministic, order-independent)

Scaffold runs one `table_id` at a time in any order. To keep the output
idempotent and order-independent, ownership of a conformed dim's `.sql` is
decided by the map, not by run order:

> **The FIRST entry in a conformed dim's `stars:` list OWNS (materializes) it.
> Every other star in the list REUSES it (references the owner's model, emits no
> dim file of its own).**

The `stars:` order is human-authored, so the human controls which star owns the
canonical model. No run-order dependence, no mutable cross-run state.

## Reuse behavior

A dimension is REUSED for the current `table_id` iff ALL hold:

1. it is declared `status: conformed` in the map, AND
2. its `stars:` list has ≥2 entries and includes the current `table_id`, AND
3. the current `table_id` is NOT the first entry in `stars:` (i.e. not the owner).

When a dim is reused, for the current (non-owner) star scaffold:

- **emits NO `dim_<name>.sql` and NO `_models.yml` contract row** for it — this is
  what avoids the duplicate-model-name `dbt parse` failure;
- **still emits the fact's FK column** (`<dim>_sk`) as a `surrogate_key`
  derivation (unchanged — never a fabricated bronze citation);
- **still emits the fact's `ref('<dim>')` join comment** — which now names the
  OWNER's model. dbt resolves the cross-model `ref()` via its DAG; scaffold is a
  skeleton generator targeting the STATIC gate, so emitting the correct `ref()`
  is sufficient (consistent with how it treats every join as a human-completed
  TODO — see the `sql_render` package docstring);
- **drops the reused dim's `dimension_member_count` parity row** — the OWNER star
  asserts that dim's member count; the reusing star's parity set covers only the
  models it materializes (its fact + the dims it owns). This keeps
  `evidence._validate_parity_set` exact (it derives the required set from the
  models actually selected for this table).

## Components changed

| Component | Change |
|---|---|
| `model_plan._conformed_reuse(map_doc, table_id) -> frozenset[str]` | NEW pure helper: the bare dim names this `table_id` REUSES (does not own), read from the conformed-dimension-map. Empty on absent/malformed map or any non-conformed dim (fail-safe → emit as today). |
| `model_plan.MapSource` | Gains an optional `conformed_map: dict \| None` (the parsed `conformed-dimension-map.yaml`, or None). Keeps the derivation a pure function of its inputs — no filesystem in `model_plan`. |
| `model_plan._dimensions` | Skips a dim whose BARE name is in the reuse set (no model/contract generated for it). |
| `model_plan._parity_rows` | Emits `dimension_member_count` only for the dims actually in `plan.dimensions` (already true — reused dims are simply absent from that tuple, so this follows for free). |
| `model_plan.ScaffoldPlan` | Gains `reused_dimensions: tuple[str, ...]` (bare names + owner), for the operator note only. Does NOT change the fact contract. |
| `model_plan.build_scaffold_plan` | Threads the reuse set: excludes reused dims from `dimensions`, records them in `reused_dimensions`. The fact's FK-per-dimension loop must still emit an FK for a REUSED dim (it is a real conformed FK), so it iterates the FULL declared dim set, not only the owned subset. |
| `orchestrator._build_plan` | Reads `docs/quality/conformed-dimension-map.yaml` from the repo root (lazy `yaml`, tolerate absent/malformed → None) and passes it into `MapSource`. |
| `orchestrator._notes` | Adds a note when `reused_dimensions` is non-empty: names each reused conformed dim + its owning star, and that its fact FK joins a cross-star `ref()`. |

## Fact FK subtlety (load-bearing)

`_fact_columns` emits one FK per dimension using `dimensions[0].name`. If reused
dims are dropped from `dimensions`, their FK would vanish — WRONG: a conformed dim
the fact points at is still a real FK. So the fact FK loop must iterate the FULL
declared dimension set (owned + reused), while only the OWNED subset produces dim
MODELS. Concretely: keep a `declared_dimensions` list (all, for FK generation) and
an `owned_dimensions` subset (`plan.dimensions`, for model/contract/parity). The
FK name for a reused dim is derived from its declared `surrogate_key` (which HR1
guarantees matches the owner's).

## Fail-closed / backward compatibility

- **No map / empty `dimensions: {}`** (the current committed state) → reuse set is
  empty → EVERY dim is owned → output byte-identical to today. The shipped
  single-table worked example is unaffected.
- **Malformed map** → treated as no map (None) → no reuse. Never crashes scaffold.
- **`status: distinct`** → never reused (deliberately separate dims).
- Reuse requires the current table to be a declared, non-first member of a
  `conformed` dim's `stars:` — a narrow, explicit trigger.

## Testing (TDD, driver-free — mirrors `test_dbt_scaffold.py`)

1. **owner star owns the dim**: table is `stars[0]` → dim IS in `plan.dimensions`,
   its model/contract/parity are emitted (unchanged).
2. **non-owner star reuses**: table is `stars[1]` → dim is NOT in
   `plan.dimensions` (no model file), NO `dimension_member_count` parity row for
   it, BUT the fact still carries its `<dim>_sk` FK (derivation `surrogate_key`)
   and the fact SQL emits `ref('<dim>')` at the owner's name.
3. **generated non-owner plan passes the real gate** (`_model_contract` zero
   blockers; `_validate_parity_set` exact) — the end-to-end proof.
4. **no map → byte-identical**: the existing `_plan()` (no conformed map) still
   owns every dim; all existing scaffold tests stay green.
5. **`status: distinct` → no reuse**.
6. **malformed map → no reuse, no crash**.
7. **owner-rule determinism**: reversing which table is passed flips owner/reuser
   deterministically from the SAME map.

## Known limitation — a star must OWN at least one dimension

If EVERY dimension a star declares is a conformed dimension owned by another
star, `build_scaffold_plan` fails closed (`ScaffoldError`, actionable message):
the star would materialize no dimension model of its own. The textbook fully-
conformed reuser (a returns star whose only dims are the shared `dim_customer` +
`dim_date`, both owned by the sales star) must therefore either own one of them
or have a per-star dimension to scaffold end-to-end; otherwise the fact +
staging models are authored, but the reuser owns no dim model. This is a
deliberate, documented bound (the fail-closed message names it), not a silent
refusal. Lifting it (allowing a zero-owned-dim plan — `_validate_parity_set`
tolerates the empty dim-subject set) is a possible future enhancement, out of
scope here.

## Known limitation — reuser-only attributes are not merged

HR1 permits a conformed dimension whose stars declare DIFFERENT attribute sets
(it compares `silver_type` only for attributes present in ≥2 stars). When a
reuser declares an attribute the OWNER's dim does not carry, dropping the
reuser's dim spec here means that reuser-only attribute appears in neither the
owner's model nor the reuser's (which emits no dim model) — a silently-lost
governed field. Reuse does **not** currently merge or reconcile divergent
attribute sets, and it does **not** refuse such a configuration (a cheap refusal
would also reject the legitimate common case where the reuser re-declares the
shared natural key). Correct handling needs the cross-table governed-star view
(load the owner's `source-map.yaml` to compare/merge attributes) — the same
capability the owner-existence and all-reused items below need. Tracked as the
#418 follow-up; latent today (no conformed-dimension name collision exists in the
committed tree — `test_hr1_clean_on_real_committed_tree`).

## Owner-rule robustness

The owner is `stars[0]`, compared directly (`table_id == stars[0]`), NOT
"membership in `stars[1:]`". `stars` is an authority field HR1 does not validate
beyond `status`, so a human may accidentally repeat the owner later in the list
(`[owner, reuser, owner]`); comparing against `stars[0]` keeps the owner the
owner (it never reuses its own dim, which would leave the dim materialized by
nobody).

## Out of scope (YAGNI)

- No change to HR1 or the conformed-dimension-map SHAPE.
- No `dbt run`/`parse` execution (scaffold targets the static gate).
- No cross-run filesystem coupling / owner-existence validation (the owner rule is
  map-derived and order-independent; dbt's DAG resolves physical existence).
- Namespace+alias per-star reuse is explicitly rejected: it would create N physical
  copies of a "conformed" dim, contradicting conformance and HR1's one-shared-dim
  model.
