---
name: dbt-workflows
description: >-
  Route dbt intent to Seshat's governed shadow workflow or the official dbt
  Labs competence and execution owner, without bypassing readiness or evidence.
---

# Governed dbt workflows

Read `../../portable-operating-contract.md` before acting. For a governed
Seshat shadow workflow, use only the installed `seshat dbt` helpers; never
bypass their fixed selector, target, profile, lock, redaction, or artifact
checks with raw dbt commands.

## Intent ownership

| User intent | Seshat pre-gate | Execution owner | Seshat afterward |
|---|---|---|---|
| Decide whether dbt fits the current BI stage | Readiness and approved-mapping context | Seshat selection policy | State one truthful next action |
| Scaffold governed shadow models | Approved committed source map | Seshat source-map-derived scaffold | Validate citations and the `meta.seshat` contract |
| Governed compile, build, test, or parity | Mapping Ready, exact selector, shadow target, and accepted immutable plan | dbt Core through `seshat dbt` | Normalize artifacts into derived evidence, blockers, and parity findings |
| Generic dbt model authoring, test design, syntax, docs, or troubleshooting | Prove the official skill is activated and discoverable | Official dbt Labs agent skills | If the work enters Seshat's governed project, return through the Seshat gates above |
| Native dbt MCP configuration or tool use | Prove the exact MCP registration is activated and discoverable | Official dbt MCP and its official configuration skill | Do not infer a readiness effect; route governed execution back through `seshat dbt` |
| Switch from migrations to dbt | Passing parity evidence plus a named-human approval | Named human | Retain migrations as parity oracle and rollback path |

Spec 148 provides the read-only harness proof for the official dbt Labs agent
skills. Before routing generic competence, run
`seshat integrations setup --profile analytics-full --harness <claude-code|codex>`
and require the `dbt-agent-skills` result to be discoverable. MCP liveness remains
a separate preflight fact. Report the exact blocker for either surface; do not
copy official guidance into this router, claim an installed payload is usable,
or execute raw dbt commands against the governed project as a fallback.

## Fixed workflow

1. Check prerequisites without a database query:

   `seshat dbt doctor --format json`

2. Materialize the governed model set from the approved map (once per table):

   `seshat dbt scaffold --table <table> --format json`

   This writes, FROM the approved committed source map, the staging model, one
   gold model per fact/dim, the parity-audit model, their native dbt contracts,
   the `seshat_table_<table>` selector row, and the `bronze` + `migration_gold`
   sources. It is non-destructive (an existing file is kept) and needs no
   database. The generated `.sql` files are SKELETONS: their SELECT column list
   is the governed output contract (do not rename or drop columns), but the
   joins, casts, and surrogate-key logic are yours to complete before the live
   build. NOTE: scaffold is non-destructive (it never overwrites an existing
   model), so after a source-map re-commit a plain re-run does NOT refresh a
   stale `source_map_revision` — you must update each model's `source_map_revision`
   by hand, or delete the generated `_models.yml` and re-scaffold. See "The
   `meta.seshat` model contract" below for the shape scaffold emits and `validate`
   enforces.

3. Validate the Mapping Ready gate, shadow schemas, selector, and citations:

   `seshat dbt validate --table <table> --format json`

5. Produce and review the immutable plan:

   `seshat dbt plan --table <table> --format json`

   Confirm the approved mapping identity, pinned dbt versions, exact selected
   model/test IDs, and shadow-only schemas. The returned `digest` is the only
   valid `--accept-plan` value; it is neither a mapping approval nor a readiness
   approval.

6. With the reviewed digest, execute the fixed graph:

   `seshat dbt build --table <table> --accept-plan <digest> --format json`

   Use `seshat dbt test --table <table> --accept-plan <digest> --format json`
   only for a test-only rerun. Both recompute the plan before database access;
   drift stops execution and requires a new plan and review.

7. Review the returned normalized evidence. When a user supplies an existing
   run directory under `.seshat/dbt/runs/`, revalidate it offline with:

   `seshat dbt inspect-run --table <table> --artifacts <run-directory> --format json`

   Do not invent a run directory or treat `inspect-run` as a required second
   build. Report parity failures and `blocking_reasons`, then stop for a named human.
   Passing output is derived evidence only.

## The `meta.seshat` model contract

`seshat dbt scaffold` emits this shape and `seshat dbt validate` enforces it; you
should never need to reverse-engineer it from a gate error. Each `_models.yml`
row carries, at the TOP level of the row (NOT under `config` -- nesting
`meta` there silently orphans the model, because the validator reads
`row['meta']` while the tag reads `row['config']['tags']`):

    - name: <model_name>              # dim_* / stg_* / audit_* / the one fact
      config:
        tags: [seshat_table_<table>]  # the governed selector tag
      meta:
        seshat:
          table_id: <table>
          source_map: mappings/<table>/source-map.yaml
          source_map_revision: <git blob sha of the committed map>
          grain: <one row = ...>
          business_key: [<key column(s)>]
          authority: derived          # always exactly "derived"
      columns:
        - name: <column>
          data_type: <postgres type>  # ADVISORY (source columns only), not an
                                       # enforced contract; the human owns casts
          meta:
            seshat:
              source_columns: [bronze.<table>.<src>]   # OR:
              # derivation: surrogate_key | date_spine | unknown_member | parity_measure

`source_map_revision` is the git BLOB sha of the committed map
(`git rev-parse HEAD:mappings/<table>/source-map.yaml`), so every model is
coupled to one committed map revision: any map edit needs a re-commit AND a
re-scaffold, or `validate` reports `DBT_MODEL_CITATION_STALE`. Every output
column MUST carry either `source_columns` (an approved-map citation) or one of
the four governed `derivation` values -- an uncited column is a defect.

The parity-audit model emits exactly the assertion rows `dbt show` consumes: one
`fact_row_count`, one `business_key_count` (subject = `<fact>.<key cols>`), one
`additive_money_total` per approved money measure, and one
`dimension_member_count` per built dimension (tolerances: money `0.01`, else `0`).
Scaffold derives this set from the approved map's `gold_star.fact` tags
(`business_key`, `additive_money_measures`) and the built `dim_*` models; do not
hand-edit it out of agreement with the map.

## Hard boundaries

- Stop before planning unless Mapping Ready has a named-human approval.
- Put real `SESHAT_DBT_*` values only in the gitignored `.env`; keep
  `profiles.yml` as `env_var()` references.
- If the dbt extra, profile, DSN, or live database is absent, report
  `[PENDING LIVE PROFILE]` with enable steps; never fabricate compile, build,
  test, or parity success.
- Migrations remain the default build path after parity. A separate named
  human must approve switching the active path, and migrations remain the
  parity oracle and rollback path until separately retired.
- Never write a readiness pass, migration-switch approval, confidence score,
  raw adapter output, credential, DSN, or absolute local path.

## Exit meanings

- exit 0: command completed; dbt output remains derived evidence.
- exit 1: handled model, test, or parity failure.
- exit 2: usage or runtime/profile/database prerequisite unavailable.
- exit 3: governance refusal, lock conflict, or accepted-plan drift.
- exit 4: artifact or normalized-evidence integrity failure.
