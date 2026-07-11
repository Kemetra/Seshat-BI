# retail-scaffold -- usage & boundary

The `retail-scaffold` skill is an **invoke-and-interpret wrapper** over the `retail
scaffold` CLI verb (feature 062). It is the agent-discoverable front door for AUTHORING
a new static governance rule and for VERIFYING an existing rule's wiring.

## What it is

A thin skill that runs `retail scaffold` and interprets its output. The mechanical work
lives in `src/seshat/scaffold.py`; the skill makes that verb reachable through the
normal agent-routing surface (its `description:` frontmatter carries the trigger
phrases) instead of being CLI-only and undiscoverable.

## When to use it (and when not)

- **Use it** when you are ADDING a new `retail check` rule, or checking whether a rule
  is fully wired ("is `S9` in all five places?").
- **Use `retail-govern` instead** when an EXISTING check FAILED and you need to map the
  reported rule id to its fix. Scaffold authors; govern interprets. (See the boundary
  note in the skill.)
- **Do not** use it to invent rule intent, to run the golden regenerations, or to
  decide a rule "passed" -- those are the author's job, print-only follow-ups, and the
  gate's authority respectively.

## The two modes

| Mode | Command | Effect |
|------|---------|--------|
| Author | `retail scaffold --id <ID> --title "<title>"` | writes 3 targets (stub module, failing test, EXPECTED_RULE_IDS insertion); prints the golden-regen commands + glossary row + import/`__all__` edit |
| Doctor | `retail scaffold --doctor [--id <ID>]` | read-only; reports per-id presence across the five wiring places; non-zero exit on drift |

## The five wiring places (authoritative in code, not here)

The five places a rule id must appear in are declared as `FIVE_PLACES` in
`src/seshat/scaffold.py` -- that is the single source of truth. This doc and the skill
point at it; they do not re-list it as a competing authority (anti-fork).

## Boundary discipline

- **Write/print split**: the helper writes exactly three targets and PRINTS the rest;
  it never edits the glossary or a golden record (Principle V).
- **Never self-grants a wiring pass**: the test suite + `retail check` exit code decide
  (Principle I).
- **Never invents rule intent**: the author supplies id + title + real logic (DEC-1).

## See also

- The skill: `.claude/skills/retail-scaffold/SKILL.md`.
- The interpret sibling: `.claude/skills/retail-govern/SKILL.md`.
- The helper + its spec: `src/seshat/scaffold.py`; `specs/062-scaffold-rule-generator/`.
