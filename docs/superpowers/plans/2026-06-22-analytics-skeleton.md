# Retail Tower Analytics Skeleton — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the `Retail_Tower_analytics` repository — folder structure, git config, secrets pattern, and documentation — so a teammate can clone it and know exactly how to add the first SQL mart and the first Power BI (PBIP) report.

**Architecture:** A standalone analytics service. SQL under `warehouse/` defines a DigitalOcean PostgreSQL analytics DB (tool-agnostic: `raw` landing schema → `marts` reporting schema). Power BI (PBIP, plain-text) is the only tool-specific folder and reads from `marts`. `pipelines/` documents manual ingestion now and reserves the seam for a future automated feed. No live DB, no real SQL content, no reports in this pass.

**Tech Stack:** Git, PostgreSQL (DigitalOcean), Power BI Desktop (PBIP preview format), Markdown docs. No application runtime in the skeleton.

## Global Constraints

- Repo lives at `C:\Users\user\Documents\GitHub\Retail_Tower_analytics` (short root path — Windows 260-char limit applies to PBIP).
- `.gitignore` PBIP baseline must be **exactly** these two lines (Microsoft official, docs updated 2025-12-15): `**/.pbi/localSettings.json` and `**/.pbi/cache.abf`.
- `.env` is NEVER tracked. Secrets only in `.env`; `.env.example` holds variable names with empty/placeholder values.
- Power BI connects via **parameters**, never a baked-in connection string in committed model files.
- SQL naming: `snake_case`; schemas `raw` + `marts`; views `vw_`, facts `fct_`, dimensions `dim_`; migrations numbered + idempotent.
- DAX/PBIP naming: measures `PascalCase` with display folders; one semantic model per subject area.
- Git: `core.autocrlf=true` (Power BI uses CRLF). Commit type prefixes: `feat|fix|docs|chore|refactor`.
- Commits in this repo: signing is enabled via 1Password SSH and prompts interactively. Each commit step notes this — the executor either approves the 1Password prompt or, if explicitly authorized, appends `--no-gpg-sign`.
- Out of scope: live DB provisioning, real SQL content, any `.pbip`, automated ingestion code, orchestrator integration.

---

### Task 1: Git configuration and line-ending handling

**Files:**
- Create: `.gitattributes`

**Interfaces:**
- Consumes: existing git repo (already initialized; `main` branch; one prior commit).
- Produces: `.gitattributes` enforcing LF normalization with CRLF on checkout for PBIP/SQL/MD text files; `core.autocrlf=true` set in local git config.

- [ ] **Step 1: Write `.gitattributes`**

```gitattributes
# Normalize line endings; Power BI Desktop writes CRLF for PBIP text files.
# Store LF in the repo, check out CRLF on Windows so diffs stay clean.
* text=auto

*.tmdl   text eol=crlf
*.pbir   text eol=crlf
*.pbism  text eol=crlf
*.json   text eol=crlf
*.sql    text eol=lf
*.md     text eol=lf
*.py     text eol=lf

# Binary artifacts — never normalize.
*.pbix   binary
*.abf    binary
*.png    binary
*.svg    text eol=lf
```

- [ ] **Step 2: Set autocrlf in local git config**

Run:
```bash
cd "C:/Users/user/Documents/GitHub/Retail_Tower_analytics"
git config core.autocrlf true
git config --get core.autocrlf
```
Expected output: `true`

- [ ] **Step 3: Verify `.gitattributes` is recognized**

Run:
```bash
git check-attr text eol -- powerbi/Sample.SemanticModel/definition/model.tmdl
```
Expected output (path need not exist — check-attr reads rules, not files). The
specific `*.tmdl` rule overrides the general `* text=auto`, so `text` resolves to
`set`, not `auto`:
```
powerbi/Sample.SemanticModel/definition/model.tmdl: text: set
powerbi/Sample.SemanticModel/definition/model.tmdl: eol: crlf
```

- [ ] **Step 4: Commit**

```bash
git add .gitattributes
git commit -m "chore: add .gitattributes for PBIP/SQL line-ending handling"
```
(If the 1Password signing prompt appears, approve it. If signing was explicitly waived, append `--no-gpg-sign`.)

---

### Task 2: `.gitignore` with verified PBIP + secrets exclusions

**Files:**
- Create: `.gitignore`
- Test: temporary touch-files under `powerbi/` and a temp `.env`, removed after verification.

**Interfaces:**
- Consumes: nothing.
- Produces: a `.gitignore` that ignores the two MS PBIP cache/settings files, `.env`, Python/OS junk — and crucially does NOT ignore PBIP `definition/` folders.

- [ ] **Step 1: Write `.gitignore`**

```gitignore
# ── Power BI Project (PBIP) — Microsoft official baseline ──
# Local workspace settings (can carry connection context) and local data cache.
**/.pbi/localSettings.json
**/.pbi/cache.abf

# ── Secrets ──
.env
.env.*
!.env.example

# ── Python (future pipelines) ──
__pycache__/
*.py[cod]
.venv/
venv/
.ipynb_checkpoints/

# ── OS / editor junk ──
.DS_Store
Thumbs.db
*.swp
.idea/
.vscode/*
!.vscode/extensions.json
```

- [ ] **Step 2: Write the failing verification — prove the ignore rules behave**

Create temporary files that SHOULD be ignored and one that should NOT:
```bash
cd "C:/Users/user/Documents/GitHub/Retail_Tower_analytics"
mkdir -p "powerbi/Sample.SemanticModel/.pbi" "powerbi/Sample.SemanticModel/definition"
touch "powerbi/Sample.SemanticModel/.pbi/cache.abf"
touch "powerbi/Sample.SemanticModel/.pbi/localSettings.json"
touch "powerbi/Sample.SemanticModel/definition/model.tmdl"
touch ".env"
```

- [ ] **Step 3: Run the verification**

Run:
```bash
echo "should be IGNORED:"
git check-ignore "powerbi/Sample.SemanticModel/.pbi/cache.abf" \
  "powerbi/Sample.SemanticModel/.pbi/localSettings.json" ".env"
echo "should NOT be ignored (expect empty output):"
git check-ignore "powerbi/Sample.SemanticModel/definition/model.tmdl" || echo "OK: not ignored"
```
Expected: the three cache/settings/.env paths are echoed (ignored); the `definition/model.tmdl` line prints `OK: not ignored`.

- [ ] **Step 4: Clean up the temporary verification files**

Run:
```bash
rm -rf "powerbi/Sample.SemanticModel" ".env"
```
Expected: no errors; `git status` shows only `.gitignore` untracked.

- [ ] **Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore (MS PBIP baseline + secrets + python/OS)"
```
(1Password signing prompt: approve, or `--no-gpg-sign` if waived.)

---

### Task 3: Secrets template (`.env.example`)

**Files:**
- Create: `.env.example`

**Interfaces:**
- Consumes: the `.gitignore` from Task 2 (which ignores `.env` but allows `.env.example`).
- Produces: documented connection variable names used by future SQL apply scripts and Power BI parameters: `ANALYTICS_DB_HOST`, `ANALYTICS_DB_PORT`, `ANALYTICS_DB_NAME`, `ANALYTICS_DB_USER`, `ANALYTICS_DB_PASSWORD`, `ANALYTICS_DB_SSLMODE`.

- [ ] **Step 1: Write `.env.example`**

```dotenv
# DigitalOcean PostgreSQL — analytics database connection.
# Copy to .env and fill in real values. .env is git-ignored; never commit secrets.
# Power BI connects using these as PARAMETERS, not a baked-in connection string.

ANALYTICS_DB_HOST=
ANALYTICS_DB_PORT=25060
ANALYTICS_DB_NAME=
ANALYTICS_DB_USER=
ANALYTICS_DB_PASSWORD=
# DigitalOcean managed Postgres requires TLS.
ANALYTICS_DB_SSLMODE=require
```

- [ ] **Step 2: Verify `.env.example` is trackable and `.env` is not**

Run:
```bash
cd "C:/Users/user/Documents/GitHub/Retail_Tower_analytics"
cp .env.example .env
git check-ignore .env && echo "OK: .env ignored"
git check-ignore .env.example || echo "OK: .env.example trackable"
rm .env
```
Expected: prints `.env` then `OK: .env ignored`, then `OK: .env.example trackable`.

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "chore: add .env.example for analytics DB connection vars"
```
(1Password signing prompt: approve, or `--no-gpg-sign` if waived.)

---

### Task 4: `warehouse/` data layer scaffold

**Files:**
- Create: `warehouse/README.md`
- Create: `warehouse/schema/.gitkeep`
- Create: `warehouse/marts/.gitkeep`
- Create: `warehouse/migrations/.gitkeep`

**Interfaces:**
- Consumes: SQL naming conventions from Global Constraints.
- Produces: the tool-agnostic SQL folder layout (`schema/`, `marts/`, `migrations/`) that any BI tool reads from; documented in `warehouse/README.md`.

- [ ] **Step 1: Create the folder placeholders**

Run:
```bash
cd "C:/Users/user/Documents/GitHub/Retail_Tower_analytics"
mkdir -p warehouse/schema warehouse/marts warehouse/migrations
touch warehouse/schema/.gitkeep warehouse/marts/.gitkeep warehouse/migrations/.gitkeep
```

- [ ] **Step 2: Write `warehouse/README.md`**

```markdown
# warehouse/ — tool-agnostic data layer

SQL that defines the DigitalOcean PostgreSQL analytics database. Any reporting
tool (Power BI today, others later) reads from here — nothing in this folder is
Power BI-specific.

## Schemas

| Schema  | Purpose |
|---------|---------|
| `raw`   | Landing zone. Manual loads now; a future automated feed targets the same tables. |
| `marts` | Reporting views/tables consumed by BI tools. |

## Folders

- `schema/` — DDL: `CREATE SCHEMA`, table definitions.
- `marts/` — reporting view/mart definitions (read by Power BI).
- `migrations/` — ordered, idempotent change scripts (`NNNN_description.sql`).

## Conventions

- `snake_case` everywhere.
- Views prefixed `vw_`, fact tables `fct_`, dimension tables `dim_`.
- Migrations numbered and idempotent (`CREATE ... IF NOT EXISTS`, guarded `ALTER`).

## Applying against DigitalOcean Postgres

Connection variables live in `.env` (see `.env.example`). DigitalOcean managed
Postgres requires TLS (`sslmode=require`). Apply migrations in numeric order, e.g.:

\`\`\`bash
psql "host=$ANALYTICS_DB_HOST port=$ANALYTICS_DB_PORT dbname=$ANALYTICS_DB_NAME \
  user=$ANALYTICS_DB_USER sslmode=$ANALYTICS_DB_SSLMODE" -f warehouse/migrations/0001_init.sql
\`\`\`

> No live DB or real SQL content exists yet — this is the structure the first
> mart and migration drop into.
```

- [ ] **Step 3: Verify structure**

Run:
```bash
find warehouse -type d | sort
```
Expected: lists `warehouse`, `warehouse/marts`, `warehouse/migrations`, `warehouse/schema`.

- [ ] **Step 4: Commit**

```bash
git add warehouse/
git commit -m "feat: scaffold warehouse/ SQL data layer with conventions"
```
(1Password signing prompt: approve, or `--no-gpg-sign` if waived.)

---

### Task 5: `powerbi/` and `pipelines/` scaffolds

**Files:**
- Create: `powerbi/README.md`
- Create: `powerbi/.gitkeep`
- Create: `pipelines/README.md`
- Create: `pipelines/.gitkeep`

**Interfaces:**
- Consumes: PBIP rules and ingestion decisions from Global Constraints / spec.
- Produces: the only tool-specific folder (`powerbi/`) with PBIP setup guidance, and `pipelines/` documenting manual ingestion + the future-feed contract.

- [ ] **Step 1: Create placeholders**

Run:
```bash
cd "C:/Users/user/Documents/GitHub/Retail_Tower_analytics"
mkdir -p powerbi pipelines
touch powerbi/.gitkeep pipelines/.gitkeep
```

- [ ] **Step 2: Write `powerbi/README.md`**

```markdown
# powerbi/ — Power BI projects (PBIP)

The only tool-specific folder. Power BI reports + semantic models are saved here
in **PBIP** (Power BI Project) format — plain-text TMDL/PBIR that git can diff.

## One-time setup

1. Power BI Desktop → **File > Options and settings > Options > Preview features**
   → enable **Power BI Project (.pbip) save option**. *(PBIP is in preview as of
   2025-12; without this, "Save as PBIP" won't appear.)*
2. Save reports here via **File > Save as > Power BI Project (.pbip)**.

## What gets committed

- `*.SemanticModel/definition/**` (TMDL — tables, relationships, **DAX measures**)
- `*.Report/definition/**`, `definition.pbir`, `.platform`, the `*.pbip` file

## What is ignored (see root .gitignore)

- `**/.pbi/localSettings.json`, `**/.pbi/cache.abf`

## Rules

- Connect to the analytics DB via **parameters** (host/db/user/password/sslmode
  from `.env`), never a baked-in connection string.
- Read from the `marts` schema, not `raw`.
- Measures `PascalCase` with display folders; one semantic model per subject area.

## Windows gotchas

- **260-char path limit:** keep project/table names short (repo already at a short root).
- Edit PBIP files externally only as **UTF-8 without BOM**.
- Line endings handled by root `.gitattributes` + `core.autocrlf=true`.
```

- [ ] **Step 3: Write `pipelines/README.md`**

```markdown
# pipelines/ — data ingestion

How raw data lands in the DigitalOcean analytics Postgres (`raw` schema).

## Now: manual loads

Data is loaded manually into the `raw` schema (e.g. `psql \copy`, a CSV import,
or a one-off script run by hand). No automated job runs yet, so this folder holds
no executable pipeline code — only this contract.

## The contract (so manual + future automation stay compatible)

Whatever loads data — a person today or the automated service later — MUST:

- Write into the `raw` schema only (never `marts`).
- Preserve source column names/types as landed; transformations happen in
  `warehouse/marts/`, not at ingestion.
- Be re-runnable: a reload of the same source replaces, not duplicates, its rows.

## Future: automated "flowing" service

A scheduled feed will replace manual loads, targeting the **same `raw` contract**
above. When added, its code lives here; nothing downstream (`marts`, Power BI)
should need to change.
```

- [ ] **Step 4: Verify structure**

Run:
```bash
find powerbi pipelines -type f | sort
```
Expected: `pipelines/.gitkeep`, `pipelines/README.md`, `powerbi/.gitkeep`, `powerbi/README.md`.

- [ ] **Step 5: Commit**

```bash
git add powerbi/ pipelines/
git commit -m "feat: scaffold powerbi/ (PBIP) and pipelines/ (ingestion) folders"
```
(1Password signing prompt: approve, or `--no-gpg-sign` if waived.)

---

### Task 6: `docs/` conventions and data dictionary stub

**Files:**
- Create: `docs/conventions.md`
- Create: `docs/data-dictionary.md`

**Interfaces:**
- Consumes: conventions from Global Constraints.
- Produces: a single canonical conventions doc and a growable data-dictionary stub. (`docs/superpowers/specs/` already holds the committed design spec.)

- [ ] **Step 1: Write `docs/conventions.md`**

```markdown
# Conventions

## SQL (warehouse/)

- `snake_case` for all identifiers.
- Schemas: `raw` (landing) and `marts` (reporting).
- Object prefixes: views `vw_`, fact tables `fct_`, dimension tables `dim_`.
- Migrations: numbered `NNNN_description.sql`, applied in order, idempotent
  (`IF NOT EXISTS`, guarded `ALTER`).

## Power BI / PBIP (powerbi/)

- Save as PBIP (preview feature must be enabled in Power BI Desktop).
- One semantic model per subject area; reports reference the model relatively.
- Connect via parameters; read from `marts` only.

## DAX

- Measures in `PascalCase`, organized into display folders.
- One measure per business concept; avoid duplicating logic across measures.

## Git

- Commit messages: `<type>: <description>` where type ∈
  `{feat, fix, refactor, docs, chore, perf}`.
- `core.autocrlf=true`; line endings governed by `.gitattributes`.
```

- [ ] **Step 2: Write `docs/data-dictionary.md`**

```markdown
# Data Dictionary

Catalog of analytics tables, columns, and marts. Grows as the warehouse fills in.

## raw schema

_No tables yet._

| Table | Column | Type | Source | Notes |
|-------|--------|------|--------|-------|
| _(none)_ | | | | |

## marts schema

_No marts yet._

| Mart / View | Grain | Columns | Description |
|-------------|-------|---------|-------------|
| _(none)_ | | | |
```

- [ ] **Step 3: Verify files exist**

Run:
```bash
ls docs/conventions.md docs/data-dictionary.md
```
Expected: both paths listed, no error.

- [ ] **Step 4: Commit**

```bash
git add docs/conventions.md docs/data-dictionary.md
git commit -m "docs: add conventions and data-dictionary stub"
```
(1Password signing prompt: approve, or `--no-gpg-sign` if waived.)

---

### Task 7: Top-level `README.md` and `CLAUDE.md`

**Files:**
- Modify: `README.md` (currently one line: `# Retail_Tower_analytics`)
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: every folder/convention from Tasks 1–6 (this is the entry-point doc).
- Produces: a README that orients a fresh teammate end-to-end, and a CLAUDE.md encoding repo-specific agent rules (PBIP preview, Windows path limit, secrets, conventions).

- [ ] **Step 1: Overwrite `README.md`**

```markdown
# Retail Tower Analytics

Standalone analytics service for the Retail Tower ecosystem. Power BI is the
primary reporting tool; the layout leaves room for other tools later. Data is
served from a dedicated **PostgreSQL database on DigitalOcean**.

## Layout

| Folder | Purpose |
|--------|---------|
| `warehouse/` | Tool-agnostic SQL: `raw` landing schema → `marts` reporting schema, plus migrations. |
| `powerbi/` | Power BI projects in **PBIP** (plain-text) format — the only tool-specific folder. |
| `pipelines/` | Data ingestion: manual now, automated feed later (same `raw` contract). |
| `docs/` | Design specs, conventions, data dictionary. |

## Architecture

\`\`\`
DigitalOcean PostgreSQL
  raw (landing)  →  marts (reporting)  →  Power BI (PBIP)
        ▲
   manual loads now · automated feed later
\`\`\`

## Getting started

1. Copy `.env.example` to `.env` and fill in the DigitalOcean Postgres connection
   values. `.env` is git-ignored — never commit it.
2. **For Power BI:** enable **Power BI Project (.pbip)** in Power BI Desktop
   Preview features (it's in preview as of 2025-12), then save projects under
   `powerbi/`. See `powerbi/README.md`.
3. **For SQL:** add schema/marts/migrations under `warehouse/`. See
   `warehouse/README.md`.

## Conventions

See [`docs/conventions.md`](../../conventions.md). Design rationale lives in
[`docs/superpowers/specs/`](../specs/).

## Notes for Windows

PBIP enforces a 260-char path limit; this repo intentionally sits at a short root
path. Line endings are handled by `.gitattributes` + `core.autocrlf=true`.
```

- [ ] **Step 2: Write `CLAUDE.md`**

```markdown
# CLAUDE.md — Retail Tower Analytics

Repo-specific rules. Global rules in `~/.claude/CLAUDE.md` still apply.

## What this repo is

A **standalone analytics service** — NOT bound by the Retail Tower OS
orchestrator / contract-boundary rules. Power BI primary; DigitalOcean Postgres
source. Data flows `raw` → `marts` → Power BI.

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

SQL: `snake_case`; schemas `raw`/`marts`; `vw_`/`fct_`/`dim_` prefixes; numbered
idempotent migrations. DAX: `PascalCase` measures in display folders. Full detail
in `docs/conventions.md`.

## Scope discipline (YAGNI)

No live DB provisioning, no automated ingestion code, no orchestrator integration
unless explicitly requested. Add the seam, not the implementation.
```

- [ ] **Step 3: Verify README no longer a stub**

Run:
```bash
wc -l README.md && grep -c "warehouse/" README.md
```
Expected: README has many lines (not 1); grep count ≥ 1.

- [ ] **Step 4: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: write top-level README and repo CLAUDE.md"
```
(1Password signing prompt: approve, or `--no-gpg-sign` if waived.)

---

### Task 8: Final verification — clean tree and full structure

**Files:** none (verification only).

**Interfaces:**
- Consumes: all prior tasks.
- Produces: confirmation the skeleton matches the spec's success criteria.

- [ ] **Step 1: Confirm a clean working tree**

Run:
```bash
cd "C:/Users/user/Documents/GitHub/Retail_Tower_analytics"
git status --short
```
Expected: empty output (everything committed).

- [ ] **Step 2: Confirm the full structure matches the spec**

Run:
```bash
find . -path ./.git -prune -o -type f -print | sort
```
Expected to include: `./.env.example`, `./.gitattributes`, `./.gitignore`,
`./CLAUDE.md`, `./README.md`, `./docs/conventions.md`, `./docs/data-dictionary.md`,
`./docs/superpowers/specs/2026-06-22-analytics-skeleton-design.md`,
`./docs/superpowers/plans/2026-06-22-analytics-skeleton.md`,
`./pipelines/README.md`, `./pipelines/.gitkeep`, `./powerbi/README.md`,
`./powerbi/.gitkeep`, `./warehouse/README.md`, and the three `warehouse/*/.gitkeep`.

- [ ] **Step 3: Re-confirm secrets are not tracked**

Run:
```bash
git ls-files | grep -E "^\.env$" && echo "FAIL: .env tracked" || echo "OK: .env not tracked"
```
Expected: `OK: .env not tracked`.

- [ ] **Step 4: Confirm commit history is coherent**

Run:
```bash
git log --oneline
```
Expected: the initial commit, the design-spec commit, plus the task commits from this plan, each with a `feat|chore|docs` prefix.
```
```

## Self-Review

After writing, checked against the spec:

**1. Spec coverage** — every spec section maps to a task:
- Repo structure (§4) → Tasks 4, 5, 6, 7
- Committed vs ignored (§5) → Task 2 (with `git check-ignore` proof)
- Secrets (§6) → Tasks 2, 3
- Conventions (§7) → Task 6
- Windows/PBIP guardrails (§8) → Tasks 1, 5, 7
- Out of scope (§9) → enforced by Global Constraints; no task adds DB/reports/automation
- Success criteria (§10) → Task 8 verifies clean tree, structure, no tracked secrets

**2. Placeholder scan** — no "TBD/TODO/implement later". The `_(none)_` rows in the data-dictionary stub are intentional content (an empty catalog that grows), not plan placeholders.

**3. Type/name consistency** — folder names, env-var names (`ANALYTICS_DB_*`), schema names (`raw`/`marts`), and the exact two-line `.gitignore` baseline are identical across every task and match the spec.
