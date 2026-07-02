# Contract: `scaffold` CLI subcommand

The helper is exposed as a new `scaffold` subcommand alongside the existing
governance subcommands (`check`, `validate`, `semantic-check`, `value-check`,
`generate`, `manifest`, `severity-posture`), following the same argparse
subparser pattern.

## Modes

The subcommand has two modes. Exact flag spelling is an implementation detail;
the contract is the behavior.

### Author mode (default when an id + title are supplied)

```
retail scaffold --id <RULE_ID> --title "<one-line title>" [--repo <path>]
```

**WRITES (and only these three):**
1. A new stub rule module under `src/retail/rules/` that calls
   `@register(<RULE_ID>, "<title>")` with generic placeholder logic (a rule body
   that yields no findings; zero worked-example specifics).
2. A matching test stub under `tests/unit/` that FAILS until real logic is added
   (honest red).
3. An insertion of `<RULE_ID>` into `EXPECTED_RULE_IDS` in
   `tests/unit/test_rules_wiring.py`.

**PRINTS (never runs / never writes):**
- The exact command to regenerate the rule-inventory golden record.
- The exact command to regenerate the severity-posture golden record.
- A suggested rule-family row text for the human to paste into
  `docs/glossary.md`.
- The import + `__all__` edit for `src/retail/rules/__init__.py` (the human
  applies it, or the tooling may write the stub module but the import wiring is
  shown for review).

**REFUSES (makes no changes) when:**
- `<RULE_ID>` is already registered (FR-009).
- A stub module for `<RULE_ID>` already exists (no overwrite).
- `<RULE_ID>` is malformed or `<title>` is empty (FR-010).

**Exit codes (author mode):**
- `0` -- scaffold wrote the three targets and printed the follow-ups.
- non-zero -- refused (already registered / would overwrite / invalid input),
  with a clear message and no changes made.

### Doctor mode (verify; read-only)

```
retail scaffold --doctor [--id <RULE_ID>] [--repo <path>]
```

- With `--id`: verify that one id across all five places.
- Without `--id`: SWEEP every registered rule id across all five places
  (the default value driver).

**READS (never writes):** the registry, the package import list + `__all__`, the
expected-id set, the two golden record JSON files, and the glossary prose rows.

**REPORTS:** per checked id, per place, one of `present` / `missing` /
`unverifiable` (`unverifiable` when a place's file cannot be read, FR-015).

**Exit codes (doctor mode) -- FR-014:**
- `0` -- every checked id is `present` in all five places (no drift).
- non-zero -- at least one checked id is `missing` in at least one place (drift
  found), so CI can gate on "no wiring drift".
- An unknown/unregistered `--id` is reported (absent everywhere / unknown) but
  does not crash-exit like an internal error.

## Hard invariants (asserted by tests)

- Doctor writes NOTHING (no file mtime changes after a doctor run).
- Author mode writes NOTHING to any golden record file or to `docs/glossary.md`.
- The helper imports no third-party package, opens no DB connection, and makes no
  network call (stdlib-only, Principle VIII).
- The helper's declared five-place list matches the repo's actual places
  (guard test, FR-017).
- All authored files are UTF-8 without BOM and ASCII-safe (Principle IX).
