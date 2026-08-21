# CLAUDE.md — Seshat BI

Repo-specific rules. Global rules in `~/.claude/CLAUDE.md` still apply.

## What this repo is

A **standalone analytics service** — NOT bound by the Retail Tower OS
orchestrator / contract-boundary rules. Power BI primary; DigitalOcean Postgres
source. Data flows `bronze` → `silver` → `gold`; Power BI reads the `gold`
schema only.

For new retail mart work, start from a filled worked example under `docs/worked-examples/` and follow the medallion playbook.

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
Active plan: `specs/141-studio-operations-client-review/plan.md` (Studio Operations and
Client Review). Ratified by Ahmed Shaaban 2026-08-21, all five user stories; the owner
moved the fence here the same day, so FR-141-020 is fully satisfied and implementation is
authorized. 15 tasks across four phases: A disclosure primitives, B Operations, C run
history, D client review and support bundle. **Phase A must be green before B-D** --
every later phase discloses through its primitives.

Its security character differs from spec 140's. 140 guarded a WRITE (writing a decision
is not granting one); 141 guards a DISCLOSURE, so `contracts/export-boundary.md` separates
softening (pending shown as approved), leaking (a DSN in an export) and acting (a recovery
button that repairs). Read that contract before touching an export path.

**Spec 140 is DELIVERED and PARKED**: ratified, implemented, merged (`421c8f4d`, PR #695)
and accepted 2026-08-21. Its 95 per-step boxes are unmarked on purpose -- read its
acceptance record rather than inferring completeness from checkboxes.

**Spec 149 remains PARKED, not complete.** The fence is a singleton, so it stays parked
with FOUR tasks open, verified against the filesystem rather than the checkboxes: T012b
(`ApprovedDefinition` resolution feeding `operation_binds`), T017 (`target.py` absent),
T018 (`git_safety.py` absent), and T053 -- **owner-facing**, because retiring
`VENDORED_RUNTIME_DIR` narrows the identity set the bypass-prohibition matcher
`_looks_powerbi_shaped` recognises. Its own `tasks.md` carries the full note.

<!-- SPECKIT END -->
<!-- SESHAT-KIT START -->
**Seshat BI kit router** (v0.2.0) -- generated from `.seshat/kit-source.yaml`; do not edit here.

Orient first: *What readiness stage am I serving?* State lives in `readiness-status.yaml (per TABLE, recomputed)` (recomputed; this file stores none).

Verbs the agent drives:
- `retail-orchestrate` -- conductor -- sequence the medallion verbs, self-heal against the gate
- `first-hour-compass` -- first-arrival worked-example offer + single-source seam list + single-table orientation card
- `retail-onboard-table` -- Source->Mapping front door; owns the Stage-1 read-only DB-backed profile (grain candidates, column types)
- `retail-discover-portfolio` -- metadata-only portfolio discovery -> governed domain/scope proposals -> selected-table onboarding -> interview handoff
- `business-knowledge-interview` -- after DB discovery, interview the owner into the Decision Store (batch low-risk, explicit critical); records decisions, never self-grants approval
- `source-mapping` -- the mapping gate -- produces source-map.yaml
- `kpi-contract-builder` -- drive the shipped kpi_contracts engine: assess answerability, list the decisions to approve, preview with per-field provenance, then draft/finalize -- never self-grants approval
- `retail-build-warehouse` -- author silver/gold SQL; stop before executing
- `retail-validate` -- live checks; needs db extra + DSN, else [PENDING LIVE PROFILE]
- `retail-govern` -- static check (seshat check)

Hard-stops (orientation the agent reads; enforcement is the lint rules + G6/C2, not this file):
- never_self_grant_approval
- no_silver_before_mapping_cleared
- no_dashboard_before_metric_contracts
- never_fabricate_a_confidence_score
<!-- SESHAT-KIT END -->
