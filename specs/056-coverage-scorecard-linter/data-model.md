# Phase 1 Data Model: Coverage Scorecard Linter (SL1)

The rule is a pure function `RuleContext -> Iterable[Finding]`. No persistent state,
no new storage. The "entities" below are the in-memory constants and parsed shapes.

## Closed status enum (constant)

The five template statuses, dash-normalized to ASCII `--` for comparison:

- `Covered`
- `Blocked -- missing field`
- `Blocked -- needs business definition`
- `Planned`
- `Out of scope`

Membership is the closed set the rule checks each row's Coverage status cell
against. A value outside the set (after dash normalization + strip) is a violation
(FR-002 / contract C1). This set is derived from the template's own "Coverage
statuses (use exactly these)" table; it hardcodes NO domain content.

## Status-table row (parsed shape)

Parsed POSITIONALLY from the four-column table, matching PP1's non-greedy-middle-cell
technique so an extra trailing column cannot shift a captured cell:

| Column | Field | Used for |
|--------|-------|----------|
| 1 | KPI name | locator context only (never validated for domain content) |
| 2 | Contract | `contracts/<file>.md` or `--`; contract-path-resolves check (Covered only) |
| 3 | Coverage status | enum-membership check |
| 4 | Blocker | named-blocker-present check (Blocked -- rows only) |

## Anchors and placeholders

- **Per-table title anchor**: a line matching `> Table:` marks a scorecard's status
  table region; the header row `| KPI | Contract | Coverage status | Blocker ... |`
  confirms it. Parsing is anchored so a stray four-column table elsewhere in the
  document contributes no rows (FR-009 / contract C9).
- **Em-dash placeholder**: `--` (dash-normalized) is the "no contract / no blocker"
  placeholder. A `--` contract cell is legitimate for Planned / Out of scope; a `--`
  blocker cell on a `Blocked -- ...` row is a MISSING named blocker (violation).
- **Percentage token**: a number-then-`%` sequence (`\d%`). Its presence in any
  status-table cell is a violation (FR-005 / contract C4). A `%` with no adjacent
  digit (e.g. inside a KPI name) is NOT a violation (contract C4b).

## Instance-selection predicate

A tracked file is a scorecard INSTANCE the rule scans iff:

- its path matches the `mappings/`-rooted `coverage-scorecard.md` suffix (spec Q1),
  AND
- it is NOT the explicit template path
  `skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`
  (spec Q2), AND
- it is NOT a `is_test_path()` fixture (`tests/`).

With zero instances committed today, the predicate selects nothing -> zero Findings by
absence (contract C7); the rule must not crash on an empty selection.

## Contract-path resolution (conditional)

For a row whose status is `Covered`, the col-2 `contracts/<file>.md` must resolve to a
tracked file (checked against `ctx.tracked_files`, not the filesystem, so it matches
the committed set). Planned / Out of scope carry `--` and are EXEMPT; Blocked -- rows
are not required to cite a resolving contract (spec Q3 / contract C3, C3b).

## Registration record

- id: `SL1` (working id; RECOMMENDATION pending human ratification -- spec ##
  Clarifications).
- title: e.g. "Committed coverage scorecard is structurally valid (enum, blocker,
  contract-path, no-percentage)".
- Added to `EXPECTED_RULE_IDS` in `tests/unit/test_rules_wiring.py` in the same change
  (single source of truth; no literal baseline count).
- Auto-discovered by the registry's `pkgutil` scan (no `registry.py` edit).

## Finding (emitted)

The existing immutable `retail.core.Finding`: `rule_id="SL1"`,
`severity=Severity.ERROR`, a `message` naming the violated law, and a `locator`
naming the file (and row/KPI where applicable, e.g. `path:row[<kpi>]`). One Finding
per violation; the rule adjudicates no coverage truth and writes no status
(Principle V / FR-006 / contract C10).
