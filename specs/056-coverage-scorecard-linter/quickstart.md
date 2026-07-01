# Quickstart: Coverage Scorecard Linter (SL1)

## What this rule does

Fails `retail check` closed when a committed per-table coverage scorecard breaks one
of the template's structural laws: an invalid Coverage status, a Blocked row with no
named blocker, a Covered row citing a non-resolving contract path, or a percentage
token. It reads committed markdown with the stdlib only; it opens no connection and
writes no file.

## Run the rule's tests

```bash
pytest -m unit tests/unit/test_scorecard.py
```

Proves: bad-enum (C1), missing-blocker (C2), unresolved-contract (C3), Planned/Out of
scope `--` exempt (C3b), percentage present (C4), `%`-in-KPI-name allowed (C4b),
well-formed passes (C5), template + fixtures excluded (C6), empty tree silent-pass
(C7), unreadable fail-loud (C8), anchored parse (C9), and the rule FIRES on a
known-bad fixture (C11).

## Run the wiring / snapshot tests

```bash
pytest -m unit tests/unit/test_rules_wiring.py
```

Proves: the live registry id set equals `EXPECTED_RULE_IDS` with `SL1` added, and
`len(all_rules()) == len(EXPECTED_RULE_IDS)` (no literal baseline count).

## Regenerate the rules manifest

```bash
retail manifest --repo .
```

Regenerates `docs/rules/rules-manifest.json` from the live registry so it contains
`SL1`; verify it is the only intended diff (guarded by the 043 snapshot test).

## Run the full static gate

```bash
retail check
```

On the current tree this reports ZERO new Findings: no filled scorecard instance is
committed yet (the rule silent-passes by absence). It fires only once a malformed
instance is committed under the defined location (spec Q1).

## What NOT to do (Principle V / scope)

- Do NOT populate, grant, or self-validate any coverage status -- the rule checks
  STRUCTURE only.
- Do NOT self-assign a readiness stage or a roadmap F-number (Open-for-human).
- Do NOT treat the working id `SL1` as final -- it is a recommendation pending human
  ratification.
