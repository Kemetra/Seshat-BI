# CLAUDE.md — Seshat BI

Repo-specific rules. Global rules in `~/.claude/CLAUDE.md` still apply.

## What this repo is

A **standalone analytics service** — NOT bound by the Retail Tower OS
orchestrator / contract-boundary rules. Power BI primary; DigitalOcean Postgres
source. Data flows `bronze` → `silver` → `gold`; Power BI reads the `gold`
schema only.

For new retail mart work, start from `docs/worked-examples/c086-pharmacy.md` and follow the medallion playbook.

## Hard rules

- **Secrets:** credentials only in `.env` (git-ignored). Never write real values
  into tracked files. Power BI uses parameters, not baked-in connection strings.
- **PBIP `.gitignore` baseline is exact:** `**/.pbi/localSettings.json` and
  `**/.pbi/cache.abf`. Never ignore `definition/` folders — that's the model.
- **PBIP is a preview feature** (as of 2025-12); enable it in Power BI Desktop.
- **Windows 260-char path limit** — keep PBIP project/table names short.
- **Line endings:** `core.autocrlf=true`; rely on `.gitattributes`. Edit PBIP
  text externally only as UTF-8 without BOM.

## Conventions

SQL: `snake_case`; schemas `bronze`/`silver`/`gold`; `vw_`/`fct_`/`dim_` prefixes;
numbered idempotent migrations. DAX: `PascalCase` measures in display folders. Full
detail in `docs/conventions.md`.

## Scope discipline (YAGNI)

No live DB provisioning, no automated ingestion code, no orchestrator integration
unless explicitly requested. Add the seam, not the implementation.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/072-kit-drift-linter/plan.md`
<!-- SPECKIT END -->
<!-- SESHAT-KIT START -->
**Seshat BI kit router** (v0.2.0) -- generated from `.seshat/kit-source.yaml`; do not edit here.

Orient first: *What readiness stage am I serving?* State lives in `readiness-status.yaml (per TABLE, recomputed)` (recomputed; this file stores none).

Verbs the agent drives:
- `retail-orchestrate` -- conductor -- sequence the medallion verbs, self-heal against the gate
- `first-hour-compass` -- first-arrival worked-example offer + single-source seam list + single-table orientation card
- `retail-onboard-table` -- Source->Mapping front door; owns the Stage-1 read-only DB-backed profile (grain candidates, column types)
- `source-mapping` -- the mapping gate -- produces source-map.yaml
- `retail-build-warehouse` -- author silver/gold SQL; stop before executing
- `retail-validate` -- live checks; needs db extra + DSN, else [PENDING LIVE PROFILE]
- `retail-govern` -- static check (retail check)

Hard-stops (orientation the agent reads; enforcement is the lint rules + G6/C2, not this file):
- never_self_grant_approval
- no_silver_before_mapping_cleared
- no_dashboard_before_metric_contracts
- never_fabricate_a_confidence_score
<!-- SESHAT-KIT END -->
