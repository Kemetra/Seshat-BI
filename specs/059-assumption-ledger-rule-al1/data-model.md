# Phase 1 Data Model: Assumption Ledger Rule (AL1)

AL1 defines no new persisted schema. It reads the EXISTING generic metric-contract
shape. The "entities" below are the in-memory predicates and records the rule
computes over each committed contract.

## Entity: Metric contract (read-only input)

A committed `mappings/<table>/metrics/<Metric>.yaml`. Fields AL1 reads:

| Field | Type | Meaning to AL1 |
|-------|------|----------------|
| `readiness.status` | string in `{not_started, blocked, warning, pass}` | drives the marker predicate |
| `readiness.blocking_reasons` | list | must be non-empty to confirm a real `blocked` marker |
| `binds_to.gold_table` | string (`gold.<...>`) | drives the settled-binding predicate |
| `binds_to.columns` | list of strings | drives the settled-binding predicate |

AL1 never writes any of these.

## Predicate: unresolved-assumption marker (C1 / FR-015)

`is_marked(contract)` is TRUE iff:

- `readiness.status == "blocked"`, AND
- `readiness.blocking_reasons` is a non-empty list.

Rationale: this is the contract's OWN mechanism for recording an unresolved human
judgment call (per the template authoring notes). No new token is introduced.

## Predicate: settled measure binding (C2 / FR-016)

`is_bound(contract)` is TRUE iff BOTH hold:

- `binds_to.gold_table` is a non-empty string that does NOT contain an angle-bracket
  placeholder (`<...>`) -- i.e. a real `gold.<name>` value, not the template
  placeholder; AND
- `binds_to.columns` is a non-empty list with at least one entry that is not an
  angle-bracket placeholder.

The `<...>` placeholder test reuses the SAME polarity PP1/G6 established (a remaining
`<...>` marks an unfilled slot). An honest blocked draft that has not yet filled its
binding leaves these as placeholders and is therefore NOT `is_bound`.

## Trigger: coexistence (C1 AND C2 -> ERROR) / FR-009

For each selected contract: if `is_marked(contract) AND is_bound(contract)`, emit
exactly ONE `Finding(rule_id="AL1", severity=Severity.ERROR, ...)` whose `locator`
is the contract's repo-relative path and whose message names the coexistence
(a settled gold binding presented atop a still-blocked assumption). Otherwise emit
nothing for that contract.

## Predicate: contract selection (FR-003 / FR-004)

`is_target(path)` is TRUE iff:

- `path` matches `mappings/<table>/metrics/<name>.yaml` (any table), AND
- `path != "templates/metric-contract.yaml"` (generic template excluded), AND
- `not is_test_path(path)` (committed test fixtures excluded).

## Error record: unreadable / unparseable contract (FR-010)

A tracked target that cannot be read or `yaml.safe_load`-parsed produces a loud
`Finding(rule_id="AL1", severity=Severity.ERROR, message="could not read/parse
metric contract: <exc>", locator=path)` -- never a silent pass. (Mirrors PP1's
read-error handling.)

## Registration record (FR-001 / FR-002)

- `@register("AL1", "<title>")` in `src/retail/rules/assumptions.py`.
- `"AL1"` added to `EXPECTED_RULE_IDS` in `tests/unit/test_rules_wiring.py`
  (33 -> 34, sole addition).
- `docs/rules/rules-manifest.json` regenerated to include AL1.

## Non-entities (explicitly out)

- No numeric score / confidence / threshold (rule #9).
- No readiness-state write, no assumption clearing, no approval (Principle V).
- No DAX evaluation, no DB/network connection (Principle VIII).
- No C086/pharmacy literal (Principle VII).
