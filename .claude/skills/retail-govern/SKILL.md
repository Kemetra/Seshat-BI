---
name: retail-govern
description: >-
  Run the Seshat BI governance checker and interpret its findings. Use when
  someone asks to check, validate, or gate Power BI / DAX / TMDL / PBIR / SQL
  work in the Seshat BI repo, when `seshat check` reports a rule
  violation, or when you need to know what a rule id (D8, C2, S2, G1, …) means
  and where to fix it. Invoke-and-interpret only: this skill does NOT build
  models, run pbi-cli, or auto-fix — it runs the checker and maps ids to fixes.
---

# retail-govern

Seshat BI's conventions are enforced by a static checker, `seshat check`. This
skill teaches you to **run it, read its findings, and map each rule id to the file
and fix it points at**. The authoritative catalog is the glossary's "Static check
rules" section, which mirrors the checker's live rule registry; the rules manifest
is the machine-readable inventory. (An older 23-rule governance-layer design doc
is a historical record, NOT the current count -- do not cite it for the catalog.)

## Scope boundary (read this first)

This skill is **invoke-and-interpret only**. It does **not** orchestrate a Power BI
build, does **not** call `pbi-cli` or Power BI Desktop, and does **not** auto-fix or
self-heal violations. Those are deferred D-layer work (spec §9). Here you run the
checker, explain a finding, and tell the user (or the `powerbi-analyst` agent) the
single place to change — then stop.

## Run the checker

From the repo root:

```
seshat check
```

It parses the committed TMDL / PBIR / SQL / git text — **no Power BI Desktop, no
`pbi-cli`, no network** — and exits non-zero if any `error`-severity finding exists.
`warning` and `info` findings are printed but do not fail the build. Severity is
layer-aware (see the recorded severity-posture inventory
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

<!-- SESHAT-RULE-FIX-TABLE START -->
This table covers all **80** registered rules. It is GENERATED from
`rule-fixes.yaml` -- edit that file and run
`python scripts/export_rule_fix_table.py`, never this table.

| Rule | Means | Where to fix |
|------|-------|--------------|
| `A1` | A route-registry target does not resolve and is not honestly marked planned | Fix the path or mark the route planned in the route registry (`routes.py`) |
| `A3` | Knowledge-map route ids ↔ `routes.yaml` ids are not in bijection | Reconcile the two id sets (`routes_coverage.py`) |
| `AD1` | A metric's additivity class is composed illegally with its lineage parents (or is absent/ambiguous) | Set/fix the additivity class + lineage (`additivity_consistency.py`) |
| `AL1` | A metric contract is `blocked` (+reasons) yet carries a SETTLED gold binding | Either resolve the assumption (unblock) or revert the binding to a placeholder (`assumptions.py`) |
| `AL2` | Contracts on one gold table record contradictory decided ambiguity rulings | Reconcile the conflicting rulings across the contracts (`assumption_coherence.py`) |
| `AP1` | visual-qa and dashboard-qa list the same anti-patterns with matching numbering and names | align the divergent anti-pattern name or number in `visual-qa.md` |
| `AQ1` | A decision-question route dangles (Seeded but missing) or a Planned marker is stale | Fix the route target or its planned marker (`answerability_reconciler.py`) |
| `B1` | Module-scope DB/network import in the static core | Make the DB/network import lazy (inside the function) (`never_execute.py`) |
| `B3` | A live-surface module keeps a module-scope DB/network import | Move the import lazy in the live-surface module (`live_surface_boundary.py`) |
| `C1` | Connection-string literal in a source | Replace the server/database arg with a parameter identifier (`git_meta.py`) |
| `C2` | Committed secret / connection context (`.env`, DSN, DO cluster slug) | Remove it, gitignore `.env`, rotate; move real values to `.env` (`git_meta.py`) |
| `CB1` | a growth/comparison metric contract declares a comparison baseline and a primary date field | add the baseline (e.g. SPLY) and date field to the contract in the `retail-kpi-knowledge` contracts set |
| `CT1` | declared text/background colour pairs meet the declared WCAG contrast floor | adjust the `text.*` hex values or `accessibility.min_text_contrast_ratio` in `*-design-tokens.yaml` |
| `CT2` | adjacent `colors.data_colors` entries clear the declared deltaE76 floor | adjust the adjacent hex values or `accessibility.min_adjacent_delta_e` in `*-design-tokens.yaml` |
| `CT3` | every pair of `colors.data_colors` entries clears the declared whole-set deltaE76 floor | adjust the closest `data_colors` pair or `accessibility.min_categorical_deltae` in the tokens YAML |
| `D1` | Measure not `PascalCase` | Rename the measure in its `.tmdl` (`dax.py`) |
| `D2` | Measure missing `displayFolder` | Add a `displayFolder` to the measure block (`dax.py`) |
| `D3` | Duplicated measure logic | Replace the inlined body with a `[Name]` reference (`dax.py`) |
| `D4` | `/` in a measure | Replace with `DIVIDE(num, den)` (`dax.py`) |
| `D5` | Implicit aggregation (WARNING) | Set `summarizeBy: none` or annotate the exception (`dax.py`) |
| `D6` | Bidirectional relationship | Set `crossFilteringBehavior: singleDirection`, or justify (`dax.py`) |
| `D7` | Time-intelligence without a date-table marker | Mark a date table in the model (`dax.py`) |
| `D8` | Model sources a non-`gold` schema | Repoint the partition/expression `Schema=`/`FROM` to `gold` (`dax.py`) |
| `D9` | Hardcoded date literal in a measure | Anchor on the date table instead of a literal (`dax.py`) |
| `D10` | `FILTER(ALL/ALLSELECTED/ALLEXCEPT(...))` full-table-scan anti-pattern | Rewrite without the full-table scan (`dax.py`) |
| `D11` | Measure missing a `///` doc comment | Add a `///` doc comment above the measure (`dax.py`) |
| `DF1` | A parked-on dependency edge contradicts tracked-file evidence | Fix the parked-on edge or the evidence (`parked_on.py`) |
| `DL1` | Theme JSON is impure (carries more than styling defaults) | Strip non-default content from the theme file (surface 3) (`design_theme.py`) |
| `DL2` | A page background spec carries dynamic/data-bound content (not static structure) | Remove the dynamic content from the background spec (surface 2) (`design_background.py`) |
| `DL3` | a theme's background and dataColors stay faithful to the design tokens they compile from | correct the drifted `background` or `dataColors[i]` in the `*.theme.json`, or its source tokens YAML |
| `DL4` | a filled design-review evidence record carries every required field, non-placeholder | fill the missing or placeholder required field in that page's `design-review-evidence.md` |
| `DL5` | a layout grid's column/row arithmetic closes against its canvas and margins | correct the canvas/margin/grid numbers or the stale `arithmetic_check` booleans in `design/grids/*.yaml` |
| `DL6` | a visual-spec that self-attests an anti-pattern also records a blocking reason | add a real (non-placeholder) `readiness.blocking_reasons` entry to the `visual-spec.yaml` instance |
| `DL7` | formatting-plan rows cite a real principle/token, use allowed statuses, and never self-ratify | fix the row's `principle_cited`/`token_cited`/`status`/`ratified_by` in `formatting-plan.md` |
| `DL8` | theme sentiment colours stay faithful to a human-declared `meta.sentiment_map` | correct the drifted theme sentiment value, or the `meta.sentiment_map` entry in the tokens YAML |
| `DL9` | a filled Report Intent record carries every required field, non-placeholder | fill the missing field (audience, purpose, owner, evidence) in `report-intent.yaml`, creating the file if absent |
| `DR1` | no tracked file sits under a known-bad path prefix and no known-stale prose phrase survives | delete the file under the flagged prefix, or remove the phrase named in `design-stale-phrases.yaml` |
| `DS1` | Decision Store records carry a valid id/status/decision_type/scope and leak no PII or secrets | fix the malformed field or mask the PII/secret value in `.seshat/semantic-decisions.yaml` |
| `DS2` | an approved decision's approval block is complete, named-human-shaped, and evidence-identified | fill the missing `approved_by`/`evidence_identity` in `.seshat/semantic-decisions.yaml` |
| `DS3` | a decision batch excludes critical types and records valid members, evidence, and confirmation | fix the batch's `members`/`excluded`/`evidence`/`confirmed_by` in the decision store |
| `DS4` | supersession references resolve and no two active decisions conflict on the same scope | fix the dangling `supersedes`/`superseded_by` id, or resolve the scope conflict, in the decision store |
| `DS5` | every approved decision carries non-empty evidence before a pass verdict can rest on it | add `approval.evidence` to the approved decision record in `.seshat/semantic-decisions.yaml` |
| `G1` | `.gitignore` missing a required entry | Add `**/.pbi/localSettings.json`, `**/.pbi/cache.abf`, `.env`; never ignore `definition/` (`git_meta.py`) |
| `G2` | A `definition/` artifact is untracked, or a cache file is tracked | `git add` the definition; stop tracking `.pbi/localSettings.json` / `cache.abf` (`git_meta.py`) |
| `G3` | UTF-8 BOM in a committed text file | Re-save as UTF-8 without BOM (`git_meta.py`) |
| `G4` | `.gitattributes` EOL entry missing | Add the glob→eol mapping (TMDL/PBIR/JSON=CRLF; SQL/MD/PY=LF) (`git_meta.py`) |
| `G5` | Repo-relative path > 200 chars | Shorten the PBIP project/table name (`git_meta.py`) |
| `G6` | Real host/value in a committed PBIP parameter | Replace with a `<placeholder>`; real value comes from `.env` at refresh (`g6.py`) |
| `HR1` | a dimension shared by two or more gold stars is declared conformed or distinct, and matches | declare the dimension's status in `conformed-dimension-map.yaml`, creating the file if absent |
| `HR4` | when `meta.freshness` is present, its `expected_cadence` and `max_staleness` are well-formed | fix or add `meta.freshness.expected_cadence`/`max_staleness` in the table's `source-map.yaml` |
| `HR5` | an A10-flagged metric contract declares a valid `time_additivity` value | set `time_additivity` to fully/semi/non (never fully when A10-flagged) in the metric contract |
| `HR6` | each RLS role contract's filter binds to a real column on a committed gold dimension | fix `filter.gold_table`/`filter.column` in `mappings/<table>/roles/<file>.yaml` to name a real `dim_*` column |
| `HR7` | a non-full-rebuild gold load (append/upsert/partial delete) declares its reload/dedup key | add `ON CONFLICT`, a `-- reload-strategy: <key>` header, or an entry in the warehouse load policy, creating the file if absent |
| `HR8` | `dim_date`'s generate_series uses a one-day step and non-reversed literal bounds | use `INTERVAL '1 day'` and correct the start/end order in the `dim_date` INSERT |
| `HR9` | every column/measure reference in contracts, TMDL DAX, and dashboard bindings resolves | rename the orphaned reference to match a real TMDL column/measure, or fix the stale `visual-contract-binding-map.md` |
| `HR11` | a metric's two or more bound columns share the same declared unit and currency | align the mismatched `columns[].unit`/`currency` values in the table's `source-map.yaml` |
| `HR12` | when present, `source-data-contract.yaml` has a filled schema, arrival cadence, restatement policy | fill `schema`/`arrival.cadence`/`restatement.policy` in `mappings/<table>/source-data-contract.yaml` |
| `HR13` | every `columns[].gold_placement` `dim:` prefix resolves to a dimension the map itself declares | fix the `dim:` prefix or dimension name in `columns[].gold_placement` in the source-map |
| `KP1` | a metric contract opting into provenance fields keeps them well-formed and resolvable | fix `generic_kpi_ref`/`custom`/`decision_refs`/`source_evidence` in the metric contract |
| `KR1` | generic KPI registry entries are well-formed, unique, and free of client or physical-layer leakage | fix the entry, or remove the leaked token, in the `retail-kpi-knowledge` registry |
| `P1` | PBIP outside `powerbi/`, or SQL outside `warehouse/` | Move the file to the right folder (`git_meta.py`) |
| `P2` | Commit subject off-convention | Reword to `^(feat\ |
| `PP1` | A required handoff-pack section is unfilled (incl. the publish-approval slot) | Fill the section in the handoff pack (never self-grant the approval) (`publish_pack.py`) |
| `R1` | Report model reference is absolute / `byConnection` | Make `datasetReference.byPath.path` relative in `definition.pbir` (`pbir.py`) |
| `R2` | a PBIR `report.json` is valid JSON, keeps its `$schema`, resolves BaseTheme refs, defines no logic | remove the business-logic key, or fix the BaseTheme path, in the report's `definition/report.json` |
| `RS1` | A readiness-status file is internally inconsistent (status/evidence/blockers/approvals/current-stage disagree) | Fix the offending field in `mappings/<table>/readiness-status.yaml` (`readiness_status.py`) |
| `S1` | Non-snake_case SQL identifier | Rename the identifier in `warehouse/**/*.sql` (`sql.py`) |
| `S2` | Stale `raw`/`marts` schema token (only in schema position) | Rename the schema to `bronze`/`silver`/`gold` (`sql.py`) |
| `S3` | View missing `vw_` prefix | Rename the `CREATE VIEW` object (`sql.py`) |
| `S4a` | Migration filename / numbering broken | Rename to `^\d{4}_.+\.sql$`; contiguous + unique (`sql.py`) |
| `S4b` | Bare `CREATE`/`ALTER` (layer-aware WARNING) | Use a guarded form (`IF NOT EXISTS`, `CREATE OR REPLACE VIEW`) (`sql.py`) |
| `S5` | Type discipline (RC7): money/qty not exact NUMERIC, or leading-zero id not TEXT | Fix the cast/type in the silver SQL (`sql.py`) |
| `S6` | Gold dim missing its `-1` unknown member (RC14) | Add the `-1` unknown member + FK COALESCE in the gold dim (`sql_gold_members.py`) |
| `S7` | Date dim not a contiguous `generate_series` calendar (RC15) | Build the date dim as a contiguous generated calendar (`sql.py`) |
| `S8` | A marked date table carries a `-1`/NULL member | Remove the sentinel member from the date dim (`sql_gold_members.py`) |
| `S9` | A junk filter targeting `''` runs after nulling, so it is dead and the junk rows survive | Move the junk-row filter ahead of the `''`->NULL conversion (`sql.py`) |
| `SC1` | A prose status claim (planned/built) contradicts tracked-file evidence | Correct the stale prose claim (`status_claims.py`) |
| `SC2` | A prose "N rules" count claim disagrees with the authoritative count | Update the count + the `rule-count-claims.yaml` anchor together (`rule_count_claims.py`) |
| `SF1` | same-basename checklists shared across skills are declared shared/distinct and shared copies match | declare or fix the basename's shared/distinct status in `shared-spine.yaml`, creating the file if absent |
| `SL1` | A coverage scorecard is malformed (bad status enum / unnamed blocker / a percentage) | Fix the scorecard structure (`scorecard.py`) |
<!-- SESHAT-RULE-FIX-TABLE END -->

## What to do after interpreting

Report the failing ids, their locators, and the one fix each needs. Hand DAX/PBIP
fixes to the `powerbi-analyst` agent; SQL fixes belong in `warehouse/`. Then **stop** —
re-running `seshat check` to confirm green is the user's (or agent's) next call, not an
automated loop this skill performs.

## Orchestration

When a table is being driven end-to-end, the `retail-orchestrate` conductor skill
sequences this verb with the others and runs the self-heal loop against the gate
exit code. This skill stays single-purpose: it does its job and STOPS. The loop
(run gate -> classify findings -> auto-fix mechanical / HARD-STOP judgment calls ->
re-run) lives ONLY in `retail-orchestrate`, never here.
