# Rule Contract: AL1 (Assumption Ledger Rule)

The checkable contract AL1 must satisfy. Each clause maps to a unit test.

| # | Given | AL1 behavior |
|---|-------|--------------|
| C1 | A committed `mappings/<table>/metrics/<M>.yaml` with `readiness.status == "blocked"`, non-empty `blocking_reasons`, AND a filled non-placeholder `binds_to.gold_table` + non-empty non-placeholder `binds_to.columns` | Emit exactly ONE `AL1` ERROR Finding whose `locator` is the contract path |
| C2 | A `blocked` contract with non-empty `blocking_reasons` but a placeholder/empty `binds_to` (honest open draft) | Emit NO Finding for that contract |
| C3 | A `pass` / `warning` / `not_started` contract with a filled binding (no blocked marker) | Emit NO Finding for that contract |
| C4 | The generic template `templates/metric-contract.yaml`, and any `tests/` fixture | EXCLUDED from the scan -> no Finding |
| C5 | A tree with no `mappings/*/metrics/*.yaml` instances | Emit NO Finding (genuine silent pass) |
| C6 | A tracked target that cannot be read or parsed | Emit a loud `AL1` ERROR Finding (file + reason), never a silent pass |
| C7 | Any run | AL1 NEVER writes/clears the assumption, `blocking_reasons`, or any readiness state; it only reads and reports (Principle-V boundary) |
| C8 | The registry + wiring + manifest | `AL1` appears exactly once; registered id set == `EXPECTED_RULE_IDS`; count 33 -> 34; `docs/rules/rules-manifest.json` regenerated; a test exercises AL1 FIRING (not merely listed) |
| C9 | The AL1 module + any generic artifact it touches | No C086/pharmacy literal (dataset path, measure name, discount-status ruling); keys only on the generic SHAPE |
| C10 | Every AL1 Finding | Severity is uniformly `ERROR`; no numeric score/threshold anywhere |

## Import / execution boundary (B1 / B3 / Principle VIII)

- `yaml` imported LAZILY inside the rule function; no module-scope DB/network/yaml
  import. The B1/B3 import-boundary rules pass with `assumptions.py` present.
- No DAX evaluation, no connection opened, no file written.

## Firing-test obligation (closes the wiring-latent-gap)

`tests/unit/test_assumptions.py` MUST assert C1 (a known-bad blocked+bound fixture
produces one ERROR Finding), C2, C3, C5, and C6 -- exercising the rule's logic, not
just its registration.
