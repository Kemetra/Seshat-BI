---
name: retail-govern
description: >-
  Run the Retail Tower governance checker and interpret its findings. Use when
  someone asks to check, validate, or gate Power BI / DAX / TMDL / PBIR / SQL
  work in the Retail_Tower_analytics repo, when `retail check` reports a rule
  violation, or when you need to know what a rule id (D8, C2, S2, G1, …) means
  and where to fix it. Invoke-and-interpret only: this skill does NOT build
  models, run pbi-cli, or auto-fix — it runs the checker and maps ids to fixes.
---

# retail-govern

Retail Tower's conventions are enforced by a static checker, `retail check`. This
skill teaches you to **run it, read its findings, and map each rule id to the file
and fix it points at**. The authoritative catalog is spec §5 in
`docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md`.

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
`warning` and `info` findings are printed but do not fail the build (`S4b` and `D5`
are warnings; `G2` emits an `info` "no PBIP project present" when the repo has no
model yet).

## Read a finding

Each finding carries four fields: `rule_id`, `severity` (`error` / `warning` /
`info`), a one-line `message`, and a `locator`. The locator is the **most specific**
pointer available — `path:line` for an in-file violation, otherwise a file path, git
ref, or commit SHA (the git-metadata rules have no natural line number). Start at the
locator; the rule id tells you which fix below applies.

## Rule id → meaning → where to fix

| Rule | Means | Fix at |
|------|-------|--------|
| S1   | Non-snake_case SQL identifier. | Rename the identifier in `warehouse/**/*.sql`. |
| S2   | Stale `raw`/`marts` schema token (only in schema position). | Rename the schema to `bronze`/`silver`/`gold` in the SQL. |
| S3   | View missing `vw_` prefix. | Rename the `CREATE VIEW` object. |
| S4a  | Migration filename / numbering broken. | Rename to `^\d{4}_.+\.sql$`; make numbering contiguous + unique. |
| S4b  | Bare `CREATE`/`ALTER` (WARNING). | Use a guarded form (`IF NOT EXISTS`, `CREATE OR REPLACE VIEW`). |
| D1   | Measure not `PascalCase`. | Rename the measure in its `.tmdl`. |
| D2   | Measure missing `displayFolder`. | Add a `displayFolder` to the measure block. |
| D3   | Duplicated measure logic. | Replace the inlined body with a `[Name]` reference. |
| D4   | `/` in a measure. | Replace with `DIVIDE(num, den)`. |
| D5   | Implicit aggregation (WARNING). | Set `summarizeBy: none` or annotate the intentional exception. |
| D6   | Bidirectional relationship. | Set `crossFilteringBehavior: singleDirection` in `relationships.tmdl`, or justify the many-to-many. |
| D7   | Time-intelligence used without a date-table marker. | Mark a date table in the model. |
| D8   | Model sources a non-`gold` schema. | Repoint the partition/expression `Schema=`/`FROM` to `gold`. |
| R1   | Report model reference is absolute / `byConnection`. | Make `datasetReference.byPath.path` relative in `definition.pbir`. |
| C1   | Connection-string literal in a source. | Replace the server/database arg with a parameter identifier. |
| C2   | Committed secret / `.env` not ignored. | Remove the secret, gitignore `.env`, rotate the credential. |
| G1   | `.gitignore` missing a required entry. | Add `**/.pbi/localSettings.json`, `**/.pbi/cache.abf`, `.env`; never ignore `definition/`. |
| G2   | A `definition/` artifact is untracked, or a cache file is tracked. | `git add` the definition; stop tracking `.pbi/localSettings.json` / `cache.abf`. |
| G3   | UTF-8 BOM in a committed text file. | Re-save the `.tmdl`/`.pbir`/`.json`/`.pbism` as UTF-8 without BOM. |
| G4   | `.gitattributes` EOL entry missing. | Add the required glob→eol mapping (TMDL/PBIR/JSON=CRLF; SQL/MD/PY=LF). |
| G5   | Repo-relative path > 200 chars. | Shorten the PBIP project/table name. |
| P1   | PBIP outside `powerbi/`, or SQL outside `warehouse/`. | Move the file to the right folder. |
| P2   | Commit subject off-convention. | Reword to `^(feat|fix|refactor|docs|chore): .+`. |

## What to do after interpreting

Report the failing ids, their locators, and the one fix each needs. Hand DAX/PBIP
fixes to the `powerbi-analyst` agent; SQL fixes belong in `warehouse/`. Then **stop** —
re-running `retail check` to confirm green is the user's (or agent's) next call, not an
automated loop this skill performs.
