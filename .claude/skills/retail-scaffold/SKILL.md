---
name: retail-scaffold
description: >-
  Author a NEW static governance rule's boilerplate, or verify an existing rule's
  wiring for drift, in the Seshat BI repo -- an invoke-and-interpret wrapper over the
  `retail scaffold` CLI verb. Use when someone asks to "add a new governance rule",
  "scaffold a rule", "create a seshat check rule", "wire a new rule", "author a rule
  stub", or "check rule-wiring drift / is rule X fully wired", or runs `retail
  scaffold`. Author mode WRITES exactly three targets (a stub rule module, a failing
  test stub, and the EXPECTED_RULE_IDS insertion) and PRINTS the remaining follow-ups
  (golden-record regen commands, a glossary row, the import/__all__ edit) for a human
  to apply -- it never edits prose or golden records and never self-grants a wiring
  pass. Doctor mode is read-only: it reports, per rule id, which of the five wiring
  places the id is present in or missing from. This skill does NOT invent rule intent
  (the author supplies id + title + logic), does NOT run the golden regenerations, and
  does NOT decide whether a rule passed -- the test suite + gate exit code remain the
  authority.
---

# retail-scaffold

The authoring front door for a NEW `seshat check` rule. Adding a rule means wiring the
same **five places** every time; doing it by hand silently under-governs a rule when a
place is missed (a shipped rule once had no glossary row). This skill runs the
`retail scaffold` CLI verb, which automates the mechanical part with a strict
write/print split, and interprets its output.

## Boundary vs `retail-govern` (read first)

Both wrap a governance CLI verb; they do opposite jobs:

- **`retail-govern`** -- INTERPRET existing `seshat check` findings: map a reported rule
  id (`D8`, `C2`, `S2`, `G1`, …) to its meaning and fix. It reasons about rules that
  already exist.
- **`retail-scaffold`** (this skill) -- AUTHOR a NEW rule + verify its wiring. It
  creates a rule that does not yet exist, or doctors an existing rule's five-place
  wiring for drift.

Use `retail-govern` when a check FAILED and you need the fix; use `retail-scaffold`
when you are ADDING a rule or checking whether one is fully wired.

## Scope + non-negotiables

- **Invoke-and-interpret only.** This skill runs `retail scaffold` and reads its
  output; it does not hand-edit the five places itself.
- **The CLI (not this skill) is the source of the five wiring places.** They are
  declared in `src/seshat/scaffold.py` (`FIVE_PLACES`); this skill points at that
  authority and never re-enumerates a competing list (anti-fork).
- **Never invents rule intent (DEC-1).** The author supplies the id, the title, and
  the real check logic. The generated stub yields no findings until the author fills
  it in; its test stub fails on purpose (honest red).
- **Never self-grants a wiring pass (Principle I).** Whether a rule is correctly wired
  is disposed of by the test suite + the gate exit code, not by this skill or the
  helper.
- **Prose + golden records are PRINT-only (Principle V).** The helper writes exactly
  three targets and PRINTS the rest (golden-regen commands, a suggested glossary row,
  the import/`__all__` edit) for a human to apply by hand. It never writes the
  glossary or a golden record.

## Author mode -- add a new rule

```bash
retail scaffold --id <RULE_ID> --title "<one-line title>"
```

WRITES exactly three targets:
1. a generic stub rule module under `src/seshat/rules/` (registered no-op body);
2. a matching failing test stub under `tests/unit/` (honest red);
3. the insertion of `<RULE_ID>` into `EXPECTED_RULE_IDS` in the wiring test.

PRINTS (for the human to run / apply -- never written by the helper):
- the golden-record regen commands (`retail manifest`, `retail severity-posture`);
- a suggested glossary row to paste into `docs/glossary.md`;
- the import + `__all__` edit for `src/seshat/rules/__init__.py`.

Then: fill the stub with real logic, replace the failing test with a real one, run the
printed regen commands, apply the printed edits, and let `seshat check` + the suite
decide it is wired. Refuses (no writes) on an invalid id, an already-registered id, or
an existing stub module.

## Doctor mode -- verify wiring drift (read-only)

```bash
retail scaffold --doctor            # sweep every registered rule id
retail scaffold --doctor --id <RULE_ID>   # verify one id
```

Reports, per id, which of the five places it is present in / missing from, and exits
non-zero on any drift. The sweep is the value driver: a rule missing from just the
glossary is only discoverable by sweeping. Read-only -- it reports drift, never repairs
it.

## After a scaffold -- the fix loop

If a freshly authored (or edited) rule then trips `seshat check`, switch to the
`retail-govern` skill to map the finding id to its fix -- that is govern's job, not
this skill's.

## See also

- The CLI verb + write/print helper: `src/seshat/scaffold.py` (`FIVE_PLACES` is the
  authoritative wiring-place list); the spec: `specs/062-scaffold-rule-generator/`.
- The interpret sibling: `.claude/skills/retail-govern/SKILL.md` (map a rule id → fix).
- Rule families + ids: `docs/glossary.md`; the gate: the `seshat check` static surface.
