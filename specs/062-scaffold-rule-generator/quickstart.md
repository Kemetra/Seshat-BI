# Quickstart: Scaffold-Rule Authoring Generator + Doctor

## Author a new rule's boilerplate

```
retail scaffold --id <RULE_ID> --title "one-line title of the rule"
```

This writes:
- `src/retail/rules/<stub>.py` -- a registered stub rule with generic placeholder
  logic (fill in the real check).
- `tests/unit/test_<stub>.py` -- a failing test stub (make it pass once logic is
  written).
- an insertion of `<RULE_ID>` into `EXPECTED_RULE_IDS` in
  `tests/unit/test_rules_wiring.py`.

and PRINTS the remaining steps for you to run/paste by hand:
- the two golden-regen commands (rule-inventory manifest + severity-posture),
- a suggested rule-family row for `docs/glossary.md`,
- the import + `__all__` edit for `src/retail/rules/__init__.py`.

Run the test suite immediately: the new stub test is RED until you write the
rule. That red state is intentional -- the scaffold never leaves a false green.

## Check for wiring drift (Doctor)

Sweep every registered rule across all five places:

```
retail scaffold --doctor
```

Doctor reports, per rule id, which of the five places it is present in and which
it is missing from -- and exits non-zero if any drift is found. Point it at one id
for a fast targeted check:

```
retail scaffold --doctor --id <RULE_ID>
```

Doctor is read-only: it reports drift, it never repairs it. Regenerating golden
records and editing the glossary stay human-run/human-pasted.

## What it never does

- Never runs a golden regeneration (prints the command instead).
- Never edits the glossary prose (prints a suggested row instead).
- Never declares a rule "approved" or "fully wired" -- the test suite and the gate
  exit code remain the authority.
- Never touches a database, the network, or Power BI.
