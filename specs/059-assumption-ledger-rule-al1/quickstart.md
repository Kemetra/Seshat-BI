# Quickstart: Assumption Ledger Rule (AL1)

How to run and verify AL1. All commands run from the repo root.

## 1. Run the rule's own firing tests

```
pytest -m unit tests/unit/test_assumptions.py
```

Proves: AL1 fires exactly one ERROR Finding on a `blocked`+bound synthetic contract
(C1); emits nothing on an honest blocked-unbound draft (C2), a `pass`+bound contract
(C3), and an empty tree (C5); and fails loud on an unparseable contract (C6). This
closes the wiring-latent-gap (the rule is exercised, not merely registered).

## 2. Run the wiring / drift-guard test

```
pytest -m unit tests/unit/test_rules_wiring.py
```

Proves: `AL1` is registered exactly once, the registered id set equals
`EXPECTED_RULE_IDS`, and the count moved 33 -> 34 with AL1 the sole addition.

## 3. Regenerate + verify the rule manifest (043 snapshot)

```
retail manifest --repo .
pytest -m unit tests/unit/test_rules_manifest_snapshot.py
```

Proves: `docs/rules/rules-manifest.json` includes AL1 and matches the live registry.

## 4. Run the whole static gate on the repo

```
retail check
```

Proves: AL1 runs inside the gate over the committed metric contracts and yields ZERO
AL1 Findings on `main`'s contracts (all `status: pass`, no blocked+bound
contradiction) -- a GENUINE pass (the convention exists and is checked; the tree has
no offending contract), not a vacuous one.

## What NOT to expect

- AL1 opens no database/network/Power BI connection and evaluates no DAX.
- AL1 writes no file -- it never clears an assumption or edits a readiness state.
- AL1 emits no numeric score. It is categorical (ERROR present / absent).
