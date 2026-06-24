# Milestone M7 — D-Seam Report

## Files Created / Modified

| Action   | Path |
|----------|------|
| Modified | `.claude/agents/powerbi-analyst.md` |
| Created  | `.claude/skills/retail-govern/SKILL.md` |
| Created  | `tests/unit/test_dseam.py` |

---

## New Skill Frontmatter (`retail-govern`)

```yaml
name: retail-govern
description: >-
  Run the Retail Tower governance checker and interpret its findings. Use when
  someone asks to check, validate, or gate Power BI / DAX / TMDL / PBIR / SQL
  work in the Retail_Tower_analytics repo, when `retail check` reports a rule
  violation, or when you need to know what a rule id (D8, C2, S2, G1, …) means
  and where to fix it. Invoke-and-interpret only: this skill does NOT build
  models, run pbi-cli, or auto-fix — it runs the checker and maps ids to fixes.
```

Frontmatter validated by `test_skill_frontmatter_valid` (stdlib hand-parse, no PyYAML).

---

## How `powerbi-analyst.md` Now References the Checker

- `description:` frontmatter updated from "marts-based data models" to "gold-only data models".
- Repo context block changed to `read the 'gold' schema ONLY (never bronze/silver/raw)` — "marts" removed from the negative list (see Concerns below).
- The old "Key principles / DAX guidance / Checklist" sections replaced with:
  - "The rules are enforced — do not restate them, satisfy them" section pointing at `retail check`.
  - A rule-id table (D1–D8, R1, C1, C2) with one-line descriptions.
  - D8 entry explicitly states "never bronze/silver/raw" (no "marts").
  - Cross-reference to spec §5 and the `retail-govern` skill.
- Workflow section: three steps ending with `re-run until clean`.

---

## Frontmatter Parses Confirmation

`test_skill_frontmatter_valid` passed: the leading `---` fence, `name: retail-govern`, and `description:` key are all present and the closing fence was found.

---

## Suite Count

| Suite | Count |
|-------|-------|
| Existing (pre-M7) | 149 |
| New D-seam tests  | 7   |
| **Total**         | **156** |

`pytest -m unit` result: **156 passed** in 5.19s. No regressions.

---

## `retail check --repo .` Behavior

Unchanged from pre-M7:
- 2 `[error]` P2 findings on old `test:` commits (pre-existing, not caused by M7).
- 24 `[warning]` S4b findings on SQL migrations (pre-existing).
- `all_rules()` = 23 (ids: S1 S2 S3 S4a S4b D1–D8 R1 C1 C2 G1–G5 P1 P2).

---

## `git status --porcelain`

Clean (no output). Working tree matches committed state.

---

## Commit SHAs

| Commit | SHA | Message |
|--------|-----|---------|
| M7.1   | `cb3eb7e` | `docs: point powerbi-analyst agent at retail check + rule ids (gold-only)` |
| M7.2   | `1e9cad8` | `docs: add bounded retail-govern skill mapping rule ids to fixes` |

---

## Concerns

**"marts" removed from negative lists (deviation from verbatim brief).**

The brief's verbatim agent body included "marts" in two negative lists (e.g. `never bronze/silver/raw/marts`). However, the brief's own acceptance test (`test_agent_drops_marts_only_claim`) asserts `"marts" not in text.lower()` — passing verbatim content would have caused that test to fail. The fix applied (on advisor recommendation): remove "marts" from both negative lists, leaving `never bronze/silver/raw`. Gold-only semantics are fully preserved (gold supersedes marts; the test's comment explicitly says "Gold-only supersedes marts-only everywhere"). This is the correct resolution of the brief's internal contradiction; the test is the acceptance gate.
