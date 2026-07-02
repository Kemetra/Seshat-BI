# Phase 1 Data Model: Background-Spec Forbidden-Dynamic-Content Assertion Rule

The rule reads committed text and asserts declared booleans; it persists nothing.
"Entities" below are the conceptual shapes the rule reasons over, not stored
records.

## Entity: Filled background spec (the scanned unit)

A committed copy of `templates/background-spec.yaml`, filled per page.

| Attribute | Meaning |
|-----------|---------|
| file location | repo-relative POSIX path; the discovery convention (a suffix, OPEN owner ruling) decides if it is a filled spec |
| `forbidden_dynamic_content` | mapping of 7 boolean keys; each MUST parse to real `false` to pass |
| `qa_checklist` | mapping of 9 items; each MUST parse to real `true`, OR `false` with a recorded reason |

Exemptions: `templates/background-spec.yaml` (placeholder values) and any path
under the test-fixture exemption (`is_test_path`).

## Frozen vocabulary (verbatim from the template, Clarifications Q2)

### `forbidden_dynamic_content` -- each MUST be `false`

1. `contains_kpi_value`
2. `contains_dynamic_title`
3. `contains_measure_or_metric`
4. `contains_data_label_or_axis_value`
5. `contains_date_or_refresh_stamp`
6. `contains_filter_or_slicer_state`
7. `baked_in_screenshot_of_a_visual`

### `qa_checklist` -- each MUST be `true` (or `false` with a recorded reason)

1. `is_static_structure_only`
2. `no_forbidden_dynamic_content`
3. `exported_at_canvas_size_1to1`
4. `safe_zones_align_to_grid`
5. `whitespace_preserved`
6. `not_dark_behind_dense_charts`
7. `contrast_sufficient_for_visuals`
8. `consistent_aspect_ratio`
9. `branding_is_chrome_not_data`

## Value parse contract (Clarifications Q1, Q3)

For a value under `forbidden_dynamic_content`:

| Parsed value | Verdict |
|--------------|---------|
| real boolean `false` | PASS |
| real boolean `true` | VIOLATION (declared defect) |
| placeholder string `<true|false>` | VIOLATION (half-filled, not asserted) |
| any other non-boolean | VIOLATION (malformed against the boolean contract) |
| key missing entirely | VIOLATION (contract key omitted; declared contract not asserted) |

For an item under `qa_checklist`:

| Parsed value | Reason present? | Verdict |
|--------------|-----------------|---------|
| real boolean `true` | n/a | PASS |
| real boolean `false` | yes (non-empty, non-placeholder string) | PASS (reasoned warning accepted) |
| real boolean `false` | no | VIOLATION (un-reasoned false) |
| placeholder `<true|false>` | n/a | VIOLATION (half-filled) |
| any other non-boolean | n/a | VIOLATION (malformed) |
| item missing entirely | n/a | VIOLATION (contract item omitted) |

"Reason present" = a non-empty, non-placeholder reason string is associated with
the item. The rule detects PRESENCE only; it never judges the reason's adequacy
(Principle V). The exact YAML shape carrying the reason (a sibling key, an inline
comment, or a mapping value) is a design detail settled in the rule contract; the
recommended shape is a mapping/sibling reason field, resolved in the contract doc.

## Entity: Finding (the emitted output)

Reuses the existing `Finding` shape (`src/retail/core.py`).

| Field | Value for this rule |
|-------|---------------------|
| `rule_id` | the fresh design-lint-namespaced id (finalized at wiring) |
| `severity` | `Severity.ERROR` (Clarifications Q4) |
| `message` | human-readable: which key/item, and why (true forbidden key / un-reasoned false / placeholder / malformed / unparseable / missing) |
| `locator` | `file#/pointer` to the offending key/item |

## Entity: Governance records (verifiability, fail-closed on drift)

The registry plus the golden records that make the rule's presence verifiable:
side-effecting import registration + `__all__`, the `EXPECTED_RULE_IDS` set, the
generated `docs/rules/rules-manifest.json`, and the generated
`docs/rules/severity-posture.json` (+ `src/retail/severity_posture.py`
observation). Drift in any one fails a golden test closed.

## Non-entities (explicitly out of scope)

- The actual background IMAGE binary. The rule asserts what the filled spec
  DECLARES, never what the image contains (would require rendering -- Principle
  VIII / II).
- Numeric confidence / readiness score. Never computed (Principle V, rule 9).
- Readiness stage. The rule advances none (Clarifications Q5).
