# Live-drift semantics loader — Design

**Date:** 2026-07-08
**Feature:** F014 live-leg completion — feed `DriftSemantics` from `source-map.yaml`
**Depends on:** the shipped `retail.drift.DriftSemantics` / `classify_drift` (PR #231),
the `retail drift` CLI (PR #230), the sibling-parser pattern in `validate_targets.py`.

## Problem

`retail drift --dsn` runs the live comparator, but `classify_drift`'s
`returns_rule_drift` / `pii_surface_drift` classes only fire when a `DriftSemantics`
is supplied — and nothing supplies one today. The semantic rulings they need (the
authoritative returns *source* column; the columns dropped as PII) live in the
sibling `mappings/<table>/source-map.yaml`, which `source-profile.md` (the drift
baseline) does not carry. This design adds the loader that extracts those rulings
and wires it into the CLI, completing the live leg.

## Architecture

A NEW module `src/retail/drift_semantics.py`, mirroring `validate_targets.py`:

- Parses `source-map.yaml` with **lazily-imported pyyaml** (an optional/dev dep), so
  it is NEVER on `retail.drift`'s import path — `drift.py` stays pure + stdlib-only,
  and `retail check` / CI (no pyyaml required for the static core) never import it.
- Exposes `load_drift_semantics(source_map_path: str | Path) -> DriftSemantics`,
  returning a `retail.drift.DriftSemantics` (the loader depends on `drift`, never the
  reverse — the pure core has no new dependency).

Data flow (unchanged classifier + reader; only the CLI grows a wiring step):

```
run_drift (live leg, after the driver gate)
  -> resolve source-map path:
       --source-map PATH if given, else baseline.parent / "source-map.yaml"
  -> if that path exists: semantics = load_drift_semantics(path)
       else:               semantics = None   (returns/PII classes stay silent)
  -> observed = run_profile(runner, parsed.landed_table, parsed.pk_columns)
  -> to_findings_dict(baseline, observed, ReportContext(...), semantics=semantics)
```

## Extraction rules (from the source-map.yaml shape)

- **dropped_pii_columns** = `{ c.source_name for c in columns
  if c.pii is True and c.decision == "drop" }`.
  Rationale: a column dropped as PII can *reappear*; a `pii:true` + `keep` column
  (e.g. `customer_id` in the retail_store_sales map) never left the mapped output, so
  it is NOT a reappearance candidate. Matches the taxonomy's "a DROPPED-PII column
  reappeared" wording exactly.
- **returns_column** = the AUTHORITATIVE SOURCE column the returns rule keys on:
  `derived_columns[] where name == "is_return"` -> its `derived_from` field.
  Rationale: `classify_drift._returns_rule_findings` looks the returns column up in
  the profiled BRONZE SOURCE columns. The derived `is_return` never exists in bronze;
  the `derived_from` field (template: `derived_from: "<authoritative_type_col>"`) names
  the real source column a mechanical re-profile can watch. If `derived_columns` is
  empty (RC8 deviation), the `is_return` entry is absent, or `derived_from` is a
  placeholder (`<...>`), returns_column = None -> `returns_rule_drift` stays silent.

## Error handling

- Missing source-map path (auto-discover found nothing): NOT an error — `semantics =
  None`, drift proceeds exactly as it does today (returns/PII silent). Absence of a
  mapping is a normal state (a table profiled but not yet mapped).
- `--source-map PATH` given but unreadable/not-found: a clean stderr error + rc 1
  (an explicit path the user named should exist), NOT a silent None — mirrors the
  reader's missing-`--baseline` handling.
- Malformed yaml / missing `columns` key: raise a `ValueError` with an actionable
  message (mirrors `validate_targets._require`), surfaced by the CLI as a clean line.
- A column entry missing `pii` or `decision`: treat a missing `pii` as `false` and a
  missing `decision` as not-drop (conservative — never fabricate a PII-drop the map
  did not state). A placeholder `derived_from` (`<...>`) -> returns_column None.

## Honest-skip reality (stated, not buried)

Against the ONLY committed filled mapping (`mappings/retail_store_sales/source-map.yaml`):
`derived_columns: []` (RC8 deviated) and every column is `decision: keep` (the one
`pii:true`, customer_id, is kept). So `load_drift_semantics()` there returns
`DriftSemantics(returns_column=None, dropped_pii_columns=frozenset())` — a **no-op**;
neither class can fire on the current real data. This design WIRES THE SEAM; it does
not DEMONSTRATE returns/PII drift end-to-end (no filled mapping exercises it yet, and
the live DB round-trip is itself the deferred honest-skip path). The loader's
non-empty behavior is proven with SYNTHETIC fixture yaml (precedent: the classifier's
synthetic `_profile`/`_col` tests). The PR body states this plainly.

## Testing

Unit (no DB, no real mapping needed — synthetic fixture yaml written to tmp_path):
1. dropped-PII set = `{pii:true ∩ drop}` — a `pii:true`+`keep` column is excluded.
2. returns_column = the `derived_from` of the `is_return` derived column.
3. `derived_columns: []` / absent -> returns_column None.
4. placeholder `derived_from: "<...>"` -> returns_column None.
5. malformed yaml / missing `columns` -> ValueError.
6. the REAL `mappings/retail_store_sales/source-map.yaml` -> `DriftSemantics(None,
   frozenset())` (pins the documented no-op, and guards against a future mapping
   change silently activating a class).

CLI (monkeypatch, no DB):
7. auto-discovered sibling source-map is loaded (patch `load_drift_semantics`, assert
   it was called with the sibling path).
8. `--source-map PATH` overrides the sibling.
9. `--source-map` naming a missing file -> clean stderr + rc 1.

## Scope boundaries (YAGNI)

- No new drift class (`semantic_pair_drift` stays unwired — separate work).
- No source-map WRITER / no mutation of the mapping.
- `column_retyped` and tolerance bands are out of scope (separate enhancements).
- The loader reads ONLY the fields it needs (columns[].pii/decision/source_name,
  derived_columns[].name/derived_from) — it is not a general source-map parser and
  does not duplicate `validate_targets`' target-derivation.
```
