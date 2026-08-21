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
Active plan: `specs/140-studio-governed-workbench/plan.md` (Studio Governed Analyst
Workbench, ratified by Ahmed Shaaban 2026-08-21). The owner moved the fence here on
2026-08-21, satisfying FR-140-020's second condition; all four phases are implemented on
`feat/140-studio-governed-workbench`.

**Spec 149 is PARKED, not complete.** The fence is a singleton, so moving it here parked
149 with FOUR tasks open, verified against the filesystem rather than the checkboxes:
T012b (`ApprovedDefinition` resolution feeding `operation_binds`), T017 (`target.py`
absent), T018 (`git_safety.py` absent), and T053 -- **owner-facing**, because retiring
`VENDORED_RUNTIME_DIR` narrows the identity set the bypass-prohibition matcher
`_looks_powerbi_shaped` recognises. Parking is safe: the shipped adapter can refuse and
cannot write at all. Its own `tasks.md` carries the full parking note. #658 also remains
open, blocked externally until Microsoft publishes a non-prerelease runtime (re-measured
2026-08-21: only `0.5.0-beta.2`..`.12`).
**Spec 155 (guided setup execution) is IMPLEMENTED and RATIFIED** (Ahmed Shaaban, owner,
2026-08-21) -- `seshat integrations setup --derived` selects only the components a
project's committed evidence needs, then provisions them through the existing installer
behind spec 154's committed `governance` approval. `DEFAULT_PROFILE` and every `--profile`
run are untouched; the bridge is `integrations/guided_setup.py`, deliberately NOT
`derivation.py`, because two shipped spec-153 tests assert that file holds no execution or
approval call site -- that boundary survives ratification and is still binding. The build
preceded the ratification here (implementation shipped on the owner's instruction while
the spec read `Draft`); its `Status history` records that order, so do not cite 155 as a
precedent for building ahead of a ratification.
**Specs 153 and 154 are COMPLETE** -- capability derivation with requirement strength and
declines, and the committed named-human provisioning approval read at HEAD (`--apply` is
intent; `--yes` only suppresses the prompt; neither authorizes).
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
