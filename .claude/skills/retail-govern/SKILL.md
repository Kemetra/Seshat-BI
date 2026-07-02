---
name: retail-govern
description: >-
  Run the Seshat BI governance checker and interpret its findings. Use when
  someone asks to check, validate, or gate Power BI / DAX / TMDL / PBIR / SQL
  work in the Seshat BI repo, when `retail check` reports a rule
  violation, or when you need to know what a rule id (D8, C2, S2, G1, …) means
  and where to fix it. Invoke-and-interpret only: this skill does NOT build
  models, run pbi-cli, or auto-fix — it runs the checker and maps ids to fixes.
---

# retail-govern

Seshat BI's conventions are enforced by a static checker, `retail check`. This
skill teaches you to **run it, read its findings, and map each rule id to the file
and fix it points at**. The authoritative catalog is `docs/glossary.md` (the
"Static check rules" section), which mirrors the live registry in
`src/retail/rules/`; `docs/rules/rules-manifest.json` is the machine-readable
inventory. (An older 23-rule spec, `docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md` §5,
is a historical design doc, NOT the current count -- do not cite it for the catalog.)

## Scope boundary (read this first)

This skill is **invoke-and-interpret only**. It does **not** orchestrate a Power BI
build, does **not** call `pbi-cli` or Power BI Desktop, and does **not** auto-fix or
self-heal violations. Those are deferred D-layer work (spec §9). Here you run the
checker, explain a finding, and tell the user (or the `powerbi-analyst` agent) the
single place to change — then stop.

## Run the checker

From the repo root:

```
retail check
```

It parses the committed TMDL / PBIR / SQL / git text — **no Power BI Desktop, no
`pbi-cli`, no network** — and exits non-zero if any `error`-severity finding exists.
`warning` and `info` findings are printed but do not fail the build. Severity is
layer-aware (see `src/retail/severity_posture.py` + `docs/rules/severity-posture.json`
for the observed per-rule posture), so treat that record — not a hardcoded list here —
as the source of truth for which ids warn vs error. (`G2` emits an `info` "no PBIP
project present" when the repo has no model yet.)

## Read a finding

Each finding carries four fields: `rule_id`, `severity` (`error` / `warning` /
`info`), a one-line `message`, and a `locator`. The locator is the **most specific**
pointer available — `path:line` for an in-file violation, otherwise a file path, git
ref, or commit SHA (the git-metadata rules have no natural line number). Start at the
locator; the rule id tells you which fix below applies.

## Rule id → meaning → where to fix

This table covers **all 47 rules** (mirrors `docs/glossary.md`; source module in the
Fix column). Meanings are the glossary's; verify the source module by its `RULE_ID`
under `src/retail/rules/`.

| Rule | Means | Fix at (source module) |
|------|-------|--------|
| S1   | Non-snake_case SQL identifier. | Rename the identifier in `warehouse/**/*.sql` (`sql.py`). |
| S2   | Stale `raw`/`marts` schema token (only in schema position). | Rename the schema to `bronze`/`silver`/`gold` (`sql.py`). |
| S3   | View missing `vw_` prefix. | Rename the `CREATE VIEW` object (`sql.py`). |
| S4a  | Migration filename / numbering broken. | Rename to `^\d{4}_.+\.sql$`; contiguous + unique (`sql.py`). |
| S4b  | Bare `CREATE`/`ALTER` (layer-aware WARNING). | Use a guarded form (`IF NOT EXISTS`, `CREATE OR REPLACE VIEW`) (`sql.py`). |
| S5   | Type discipline (RC7): money/qty not exact NUMERIC, or leading-zero id not TEXT. | Fix the cast/type in the silver SQL (`sql.py`). |
| S6   | Gold dim missing its `-1` unknown member (RC14). | Add the `-1` unknown member + FK COALESCE in the gold dim (`sql.py`). |
| S7   | Date dim not a contiguous `generate_series` calendar (RC15). | Build the date dim as a contiguous generated calendar (`sql.py`). |
| S8   | A marked date table carries a `-1`/NULL member. | Remove the sentinel member from the date dim (`sql.py`). |
| D1   | Measure not `PascalCase`. | Rename the measure in its `.tmdl` (`dax.py`). |
| D2   | Measure missing `displayFolder`. | Add a `displayFolder` to the measure block (`dax.py`). |
| D3   | Duplicated measure logic. | Replace the inlined body with a `[Name]` reference (`dax.py`). |
| D4   | `/` in a measure. | Replace with `DIVIDE(num, den)` (`dax.py`). |
| D5   | Implicit aggregation (WARNING). | Set `summarizeBy: none` or annotate the exception (`dax.py`). |
| D6   | Bidirectional relationship. | Set `crossFilteringBehavior: singleDirection`, or justify (`dax.py`). |
| D7   | Time-intelligence without a date-table marker. | Mark a date table in the model (`dax.py`). |
| D8   | Model sources a non-`gold` schema. | Repoint the partition/expression `Schema=`/`FROM` to `gold` (`dax.py`). |
| D9   | Hardcoded date literal in a measure. | Anchor on the date table instead of a literal (`dax.py`). |
| D10  | `FILTER(ALL/ALLSELECTED/ALLEXCEPT(...))` full-table-scan anti-pattern. | Rewrite without the full-table scan (`dax.py`). |
| D11  | Measure missing a `///` doc comment. | Add a `///` doc comment above the measure (`dax.py`). |
| R1   | Report model reference is absolute / `byConnection`. | Make `datasetReference.byPath.path` relative in `definition.pbir` (`pbir.py`). |
| C1   | Connection-string literal in a source. | Replace the server/database arg with a parameter identifier (`git_meta.py`). |
| C2   | Committed secret / connection context (`.env`, DSN, DO cluster slug). | Remove it, gitignore `.env`, rotate; move real values to `.env` (`git_meta.py`). |
| G1   | `.gitignore` missing a required entry. | Add `**/.pbi/localSettings.json`, `**/.pbi/cache.abf`, `.env`; never ignore `definition/` (`git_meta.py`). |
| G2   | A `definition/` artifact is untracked, or a cache file is tracked. | `git add` the definition; stop tracking `.pbi/localSettings.json` / `cache.abf` (`git_meta.py`). |
| G3   | UTF-8 BOM in a committed text file. | Re-save as UTF-8 without BOM (`git_meta.py`). |
| G4   | `.gitattributes` EOL entry missing. | Add the glob→eol mapping (TMDL/PBIR/JSON=CRLF; SQL/MD/PY=LF) (`git_meta.py`). |
| G5   | Repo-relative path > 200 chars. | Shorten the PBIP project/table name (`git_meta.py`). |
| G6   | Real host/value in a committed PBIP parameter. | Replace with a `<placeholder>`; real value comes from `.env` at refresh (`g6.py`). |
| P1   | PBIP outside `powerbi/`, or SQL outside `warehouse/`. | Move the file to the right folder (`git_meta.py`). |
| P2   | Commit subject off-convention. | Reword to `^(feat\|fix\|refactor\|docs\|chore\|build\|ci\|perf\|test\|style\|revert\|brand): .+` (the 12 allowed types; `git_meta.py`). |
| RS1  | A readiness-status file is internally inconsistent (status/evidence/blockers/approvals/current-stage disagree). | Fix the offending field in `mappings/<table>/readiness-status.yaml` (`readiness_status.py`). |
| A1   | A route-registry target does not resolve and is not honestly marked planned. | Fix the path or mark the route planned in the route registry (`routes.py`). |
| A3   | Knowledge-map route ids ↔ `routes.yaml` ids are not in bijection. | Reconcile the two id sets (`routes_coverage.py`). |
| B1   | Module-scope DB/network import in the static core. | Make the DB/network import lazy (inside the function) (`never_execute.py`). |
| B3   | A live-surface module keeps a module-scope DB/network import. | Move the import lazy in the live-surface module (`live_surface_boundary.py`). |
| PP1  | A required handoff-pack section is unfilled (incl. the publish-approval slot). | Fill the section in the handoff pack (never self-grant the approval) (`publish_pack.py`). |
| SC1  | A prose status claim (planned/built) contradicts tracked-file evidence. | Correct the stale prose claim (`status_claims.py`). |
| SC2  | A prose "N rules" count claim disagrees with the authoritative count. | Update the count + the `rule-count-claims.yaml` anchor together (`rule_count_claims.py`). |
| DF1  | A parked-on dependency edge contradicts tracked-file evidence. | Fix the parked-on edge or the evidence (`parked_on.py`). |
| SL1  | A coverage scorecard is malformed (bad status enum / unnamed blocker / a percentage). | Fix the scorecard structure (`scorecard.py`). |
| AL1  | A metric contract is `blocked` (+reasons) yet carries a SETTLED gold binding. | Either resolve the assumption (unblock) or revert the binding to a placeholder (`assumptions.py`). |
| AL2  | Contracts on one gold table record contradictory decided ambiguity rulings. | Reconcile the conflicting rulings across the contracts (`assumption_coherence.py`). |
| AD1  | A metric's additivity class is composed illegally with its lineage parents (or is absent/ambiguous). | Set/fix the additivity class + lineage (`additivity_consistency.py`). |
| AQ1  | A decision-question route dangles (Seeded but missing) or a Planned marker is stale. | Fix the route target or its planned marker (`answerability_reconciler.py`). |
| DL1  | Theme JSON is impure (carries more than styling defaults). | Strip non-default content from the theme file (surface 3) (`design_theme.py`). |
| DL2  | A page background spec carries dynamic/data-bound content (not static structure). | Remove the dynamic content from the background spec (surface 2) (`design_background.py`). |

## What to do after interpreting

Report the failing ids, their locators, and the one fix each needs. Hand DAX/PBIP
fixes to the `powerbi-analyst` agent; SQL fixes belong in `warehouse/`. Then **stop** —
re-running `retail check` to confirm green is the user's (or agent's) next call, not an
automated loop this skill performs.

## Orchestration

When a table is being driven end-to-end, the `retail-orchestrate` conductor skill
sequences this verb with the others and runs the self-heal loop against the gate
exit code. This skill stays single-purpose: it does its job and STOPS. The loop
(run gate -> classify findings -> auto-fix mechanical / HARD-STOP judgment calls ->
re-run) lives ONLY in `retail-orchestrate`, never here.
