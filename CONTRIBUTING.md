# Contributing to Seshat BI

Thanks for contributing.

> **First contribution?** You don't need this whole document. Read
> [`docs/contributing/first-contribution.md`](docs/contributing/first-contribution.md),
> pick a bounded starter lane from
> [`docs/contributing/contribution-lanes.yaml`](docs/contributing/contribution-lanes.yaml),
> and come back here only for the *Dev setup* and *Branches & pull requests*
> sections. Structured issue forms (defect, capability, pack, compatibility,
> starter claim) live under `.github/ISSUE_TEMPLATE/`.

This repo is a **standalone, agent-first analytics service**
(Power BI primary; DigitalOcean Postgres source; data flows `bronze` -> `silver` -> `gold`,
and Power BI reads the `gold` schema only).
Most work is docs/skills/templates first; code follows only once the artifacts prove
useful (hard rule #8). Read this before opening a PR.

> **Authoritative companions:** `AGENTS.md` (the short operating contract),
> `.specify/memory/constitution.md` (the full governance law), `docs/conventions.md`
> (SQL/PBIP/DAX style), `docs/glossary.md` (terms + rule ids), and
> `docs/roadmap/roadmap.md` (the hard rules).

## Ground rules (read first)

- **No fabricated confidence.** Readiness is explicit `status` + `evidence` +
  `blocking_reasons`, never a made-up score (hard rule #9).
- **Stop at judgment calls.** Grain, PII, business rollups, and approvals are for a
  named human, recorded in `approvals[]` -- never self-granted (Principle V).
- **Respect the stage order.** No source goes to silver before Mapping Ready passes; no
  dashboard before approved metric contracts; no Power BI execution before Semantic Model
  Ready (hard rules #2/#5/#6). See `docs/readiness/readiness-model.md`.
- **Secrets live only in `.env`** (git-ignored). Never commit a real host, credential, or
  connection string; Power BI uses parameters, not baked-in values (rules `C2`, `G6`).
- **Scope discipline (YAGNI).** No live DB provisioning, automated ingestion, or
  orchestrator integration unless explicitly requested. Add the seam, not the
  implementation.

## Dev setup

The package targets **Python 3.13+**.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"      # ruff, black, pytest, pyyaml
# optional, only for a LIVE `retail validate` run against Postgres:
pip install -e ".[db]"       # psycopg2-binary
cp .env.example .env         # fill locally; never commit real values
```

The static `seshat check` core is **stdlib-only** by design (no `pyyaml` import) -- keep
it that way; YAML-parsing logic belongs in `retail semantic-check`, not the static core.

## Before you commit

Run what CI runs (`.github/workflows/ci.yml`) locally:

```bash
ruff format --check src tests   # formatting
ruff check src tests            # lint (E, F, I)
pytest -m unit                  # unit tests
seshat check                    # static governance gate (see docs/glossary.md for the rule families)
retail semantic-check --repo .  # contract <-> DAX drift (L3)
```

A pre-commit hook runs `seshat check` automatically and blocks the commit on any
ERROR-severity finding:

```bash
pip install pre-commit && pre-commit install
```

When `seshat check` flags a rule id (e.g. `S4b`, `D7`, `G6`), the **`retail-govern`**
skill maps the id to its meaning and fix; `docs/glossary.md` lists the families.

## Commit messages

Follow `<type>: <description>` -- **scope-free** (use `docs:`, not `docs(018):`). Allowed
types: `feat fix refactor docs chore build ci perf test style revert brand`. An automated
`[bot] ...` prefix is exempt. This is enforced by rule **`P2`** (see
`docs/decisions/0012-p2-commit-types.md`).

```
docs: add a project glossary
feat: add layer-aware S4b guard-form check
```

## Branches & pull requests

1. Branch off `main`; never push directly to `main`.
2. Keep the change focused; update the relevant `docs/` and templates alongside code.
3. Ensure all local checks above pass and committed text is **ASCII / UTF-8 without BOM**
   (rules `G3`/`G4`; edit PBIP/TMDL text externally as UTF-8 no BOM).
4. Open the PR as **ready for review**; the pull-request template
   (`.github/pull_request_template.md`) prompts for what changed, the readiness
   stage touched, scope, tests, evidence, human decisions, and secret/data
   safety -- fill each section rather than deleting it.
5. CI must be green (ruff, tests, `seshat check`, `retail semantic-check`).

## Working on warehouse / Power BI changes

Follow the medallion playbook and the readiness spine -- do not skip stages:

- **New raw table:** start with the `retail-onboard-table` / `source-mapping` flow ->
  profile -> map -> **stop at the source-mapping gate** (no `silver.*` SQL until the map is
  reviewed and approved). See `docs/worked-examples/` for two end-to-end examples.
- **Silver/gold SQL:** `warehouse/migrations/NNNN_description.sql`, numbered, idempotent
  (`DROP+CREATE` in one transaction for rebuildable `silver`/`gold`; never bare-DROP
  `bronze`). `snake_case`; schema prefixes `vw_`/`fct_`/`dim_`.
- **Power BI:** save as **PBIP** (preview feature); one semantic model per subject area;
  connect via parameters and read from `gold` only. Keep PBIP/table names short (Windows
  260-char path limit). Never git-ignore `definition/` folders -- that is the model; the
  `.gitignore` baseline is exactly `**/.pbi/localSettings.json` and `**/.pbi/cache.abf`.
- **Metrics/measures:** define a metric contract first (`mappings/<table>/metrics/`); every
  model measure must bind 1:1 to an approved contract (Semantic Model Ready).

## Repository map

| Path | What lives there |
|------|------------------|
| `src/retail/` | the `retail` CLI: static `check`, live `validate`, `semantic-check`, `generate`, `value-check` + the rule registry (`rules/`) |
| `warehouse/migrations/` | numbered silver/gold SQL migrations |
| `mappings/<table>/` | per-table mapping artifacts (profile, map, assumptions, questions, metrics, design, handoff, readiness-status) |
| `powerbi/` | PBIP semantic models + reports |
| `templates/` | the blank artifacts to copy per table |
| `docs/` | the spine, readiness stages, decisions (ADRs), conventions, glossary, worked examples, roadmap |
| `.claude/skills/` | the agent skills (docs-first companions) |
| `specs/` | per-feature Spec-Kit specs |

## See also

- `docs/glossary.md` -- terms, abbreviations, and the static rule families.
- `docs/conventions.md` -- SQL / PBIP / DAX style.
- `docs/medallion-playbook.md` -- the 7-phase method + the retail trap-checklist.
- `docs/worked-examples/README.md` -- two end-to-end examples to copy.
- License: Apache-2.0 (see `LICENSE`).
## Generated public agent bundles

The five Knowledge Bases under `skills/` are canonical. Claude and Codex copies are
generated through the literal policy in
`distribution/public-knowledge-allowlist.yaml`. Do not hand-edit
`integrations/claude-code/seshat-bi/` or `integrations/codex/seshat-bi/`.

After changing canonical public knowledge or bundle templates, regenerate with
`python scripts/export_agent_bundles.py`, then prove a clean tree with
`python scripts/export_agent_bundles.py --check`. Review the source, allowlist,
generated diff, and both provenance manifests together. Allowlist review is content
classification only; it does not approve a version, tag, upload, catalog, directory
submission, or release.
