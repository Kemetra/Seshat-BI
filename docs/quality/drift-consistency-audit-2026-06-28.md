# Docs Drift & Consistency Audit — 2026-06-28

A read-only sweep of the repository's documentation for **drift**: stale numeric
claims, cross-document contradictions, broken internal references, and skill↔doc
mismatches. This file records what was inspected, what was **fixed in the same
change**, what is **left open for a human decision**, and what was **deliberately
not touched** (point-in-time historical artifacts).

This is an evidence record, not a score. Every status below is a word
(`fixed` / `open` / `not-a-defect` / `false-alarm`), never a number — per hard
rule #9.

## Method

Four parallel read-only passes (one per drift axis), then **independent
re-verification of every headline claim against the source code** before any edit:

1. Numeric / status claims (rule counts, feature status, dates).
2. Cross-document contradictions (README / RELEASE_NOTES / roadmap / COMPASS / AGENTS).
3. Broken internal references (markdown links + backtick path mentions).
4. Skill definition (`.claude/skills/*/SKILL.md`) vs the matching doc.

## Ground truth established (verified against `src/`)

| Fact | Verified value | How verified |
|------|----------------|--------------|
| Static `retail check` rule count | **33** | `@register(` count = 33; distinct ids = 33 |
| Distinct rule ids | `A1 B1 C1 C2 D1–D11 G1–G6 P1 P2 R1 S1–S8` | grep of `src/retail/rules/` |
| Rule **families** (letter prefixes) | **8** — S, D, C, R, G, P, **A**, **B** | distinct id prefixes |
| `A1` | "route-registry targets resolve or are honestly marked planned" | `src/retail/rules/routes.py` |
| `B1` | "no module-scope DB/network import in the static core (never-execute)" | `src/retail/rules/never_execute.py` |

> Two of the four automated passes mis-stated the count as **34** and the families
> as ambiguous. Independent verification corrects this to **33 / 8 families**.
> The lesson: the count is asserted as free text in many files, so it drifts —
> see the root-cause note at the end.

## Fixed in this change

| File | Was | Now | Why |
|------|-----|-----|-----|
| `docs/worked-examples/c086-pharmacy.md` | "the 23-rule static gate" (line 17) | "the 33-rule static gate" | Self-contradicted line 182 of the same file, which already says 33 |
| `docs/architecture/tower-bi-agent-kit.md` | "(`src/retail/`, 31 static rules)" (line 51) | "33 static rules" | Inconsistent with the same doc's own "33 rules" at lines 85/167 |
| `docs/architecture/tower-bi-agent-kit.md` | `[ADR 0003](decisions/0003-…)` (line 125) | `[ADR 0003](../decisions/0003-…)` | Broken relative link — missing parent prefix |
| `CONTRIBUTING.md` | "the 6 rule families" (line 51) | "the 8 rule families" | A and B families (idea-bank rules) were added; 6 is stale |
| `docs/glossary.md` | family table listed 6 (S D C R G P) | added **A** (route registry) and **B** (never-execute) rows | The canonical family list was missing the two idea-bank families |
| `docs/superpowers/plans/2026-06-22-analytics-skeleton.md` | links `docs/conventions.md`, `docs/superpowers/specs/` (lines 537–538) | `../../conventions.md`, `../specs/` | Absolute-style paths broke from the nested location |
| `docs/decisions/0012-p2-commit-types.md` | two references to `memory/p2-rule-no-commit-scopes.md` (lines 36, 76) | references removed; the decision context is already stated inline | Target file never existed (also flagged in the external-audit report) |

## Open — needs a human decision (not auto-fixed)

| Item | Why it was not auto-fixed |
|------|---------------------------|
| **Product/repo naming: "Retail Tower Analytics"** appears in `CLAUDE.md` (header), `.claude/agents/powerbi-analyst.md`, and three `docs/superpowers/` plans/specs — a **third** label alongside "Seshat BI" (the product) and "Tower BI Agent Kit" (the prior internal name). It is also used pervasively as the *repo/service* name in skill descriptions. Whether it is a deliberate repo-vs-product distinction or stale branding is a **product-identity judgment call** (Principle V), so it is surfaced here rather than renamed unilaterally. **Suggested resolution:** decide whether "Retail Tower Analytics" is the repo/service name (keep, and state the distinction once in the glossary) or stale (rename to Seshat BI everywhere). |

## Not a defect / deliberately not touched

- **`specs/**`, `.specify/memory/constitution.md`, `templates/`, dated
  `docs/superpowers/specs|plans/*`, and ADR bodies** cite older counts
  (21/22/23/26/27/28/31). These are **point-in-time artifacts** describing the
  state when authored; rewriting them would be noisy and historically dishonest.
  *Exception worth a future look:* the constitution (`.specify/memory/`) is a
  living governing doc and still says "26 rule" / "23-rule" in places — refresh it
  via the `speckit-constitution` flow if/when convenient, not in this docs pass.
- **`README.md` does mention F034** (rows at lines 147 and 275) — an automated
  pass wrongly reported it as omitted. **False alarm.**
- **Docs that already say "33 rules"** (roadmap, `post-idea-bank-capability-state`,
  README line 139) are **correct** — not drift.
- **F016 "official Power BI MCP preferred, `pbi-cli` no longer preferred"** guidance
  is consistent in substance across skills and docs; only minor wording variance
  in `docs/readiness/dashboard-ready.md` ("no longer *the* preferred path"). Cosmetic.

## Discoverability observation (not a contradiction)

Only 4 skills have an operator guide under `docs/tools/`
(approval-console, evidence-pack-generator, readiness-viewer, pr-readiness-reviewer).
The other skills are documented in their own `SKILL.md` (and, for the adapters,
`docs/integrations/`), but a reader browsing `docs/tools/` will not find them.
Optional follow-up: have `docs/operations/agent-operating-playbook.md` index every
skill with its landing path. Left as a note, not done here.

## Root cause & recommendation

The dominant drift is the **rule count repeated as free text in ~13+ files**, so
every new rule leaves a tail of stale numbers. `docs/glossary.md` already declares
*"the live registry in `src/retail/rules/` is the authoritative list and count"* —
the remaining step is to stop **restating** the number elsewhere: prose should say
"the static gate (see the glossary / `retail check --list` for the current count)"
rather than hardcoding "N rules". That single-source-of-truth convention, applied
going forward, prevents the next round of this audit.
