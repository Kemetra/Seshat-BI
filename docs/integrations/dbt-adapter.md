# dbt as a Transformation Adapter -- how it plugs in behind the gate

- **Status:** Activated by feature 133 as a governed shadow execution adapter.
- **Roadmap feature:** F029 (on-disk spec `023-dbt-transformation-adapter`). When the
  spec-dir number and the F-number disagree, the roadmap F-number wins.
- **Authority category (F024):** Execution Adapter / `DB-connected` (NOT publish-capable).
- **Read with:** `docs/decisions/0009-dbt-is-transformation-adapter.md` (the decision
  record), `templates/dbt-adapter-contract.md` + `templates/dbt-model-contract.md` (the
  contracts), `.claude/skills/dbt-transformation-adapter/SKILL.md` (the agent procedure),
  `profiles.example.yml` (the example connection profile, placeholders only).

## One line

> dbt is the build ENGINE for silver/gold; Seshat BI is the brain. dbt may build only
> after Mapping Ready = `pass`, every model cites the approved map, dbt tests are
> evidence (never an approval), and migrations stay the default until a reconciliation
> parity test shows the dbt mart matches the existing gold tables on the four
> numeric assertions below.

## Official-first ownership routing

`dbt-workflows` remains the broad Seshat entry point because it decides whether
an intent needs Seshat readiness policy or generic upstream competence. It does
not make Seshat the owner of dbt semantics.

| Intent | Seshat pre-gate | Execution owner | Seshat post-validation |
|---|---|---|---|
| Decide whether dbt fits | Readiness and mapping context | Seshat routing policy | Earliest truthful next action |
| Scaffold Seshat shadow models | Approved source map | Seshat scaffold | Citation and `meta.seshat` validation |
| Governed compile/build/test/parity | Mapping Ready, accepted plan, fixed selector, shadow schemas | Official dbt Core through `seshat dbt` | Sanitized derived evidence, parity, blockers |
| Generic authoring/test design/command help/docs/troubleshooting | Official-skill discovery proof | Official dbt Labs agent skills | Re-enter Seshat gates only for governed work |
| Native MCP tools/configuration | Exact registration and discovery proof | Official dbt MCP | No automatic readiness effect |

The integration catalog records `dbt-core`, `dbt-postgres`,
`dbt-agent-skills`, and `dbt-mcp`. That establishes membership and install
identity, not supported-harness activation. Phase 6 must prove activation and
discovery before the official skills or MCP are treated as usable. Until then,
generic upstream intent is an explicit integration gap; raw dbt execution is
not a fallback for the governed Seshat project.

## Where dbt fits in the medallion flow

The warehouse already builds silver and gold as numbered, idempotent SQL migrations under
`warehouse/migrations/`. That hand-authored SQL is the DEFAULT build path and it is
approved and live. dbt is an OPTIONAL ALTERNATIVE engine for the same silver/gold build --
it does not replace migrations. dbt plugs in at one seam: AFTER Mapping Ready = `pass`, the
agent may invoke dbt only through `seshat dbt` to materialize shadow silver/gold objects
and run tests, then records sanitized DERIVED evidence under `.seshat/dbt/runs/`.
Seshat readiness +
a named human still decide Silver Ready / Gold Ready. dbt STOPS at gold (Principle III);
publishing Power BI is the parked F016 adapter, gated separately.

## The three load-bearing rules (the same words appear in the ADR, contracts, and skill)

**Entry gate (Principle IV):** the adapter MUST refuse to run any staging/silver/gold dbt
model for a table whose `mappings/<table>/readiness-status.yaml` does not record Mapping
Ready = `pass`, recording a `blocking_reason` instead. The presence of dbt model files is
NOT permission to build.

**Evidence, not approval (the governance hinge):** dbt test results (counts of
passing/failing tests and the failing rows' measured numbers) are recorded as `evidence[]`
/ `blocking_reasons[]` in the readiness status. A green `dbt test` MUST NOT move Silver
Ready or Gold Ready to `pass`. Tower readiness + a named human decide that, citing the dbt
evidence + the recorded approval.

**Optional alternative + parity (Principle VI):** `warehouse/migrations` remains the
DEFAULT build path. dbt becomes a table's build path ONLY after the reconciliation parity
test passes AND a named human approves the switch. Both paths MUST NOT silently feed the
same gold tables.

## The reconciliation parity test (four assertions, exact to the cent)

For a table already built by migrations, the dbt mart must match the migration-built
gold output on the four assertions below. Those four are the WHOLE contract -- they are
value assertions, and the enum in `schemas/dbt-run-evidence.schema.json` is closed to
exactly them. A pass therefore does NOT prove the two stars have the same column SET:
a shadow model that gains or loses a column can still pass every assertion (issue #492).
The per-dimension member count in (4) is the deliberate proxy for structural divergence,
not a substitute for a schema comparison.

Column-set drift is therefore surfaced OUTSIDE the parity contract, as an ADVISORY
finding: `seshat dbt validate --table <t>` compares each governed model's declared
column set against its `warehouse/migrations` counterpart and prints an
`advisory: column-shape drift` line per divergent pair. It is deliberately NOT a fifth
assertion class -- an intentional shadow-only column is legitimate while a migration is
in progress, so drift must be VISIBLE without being a failure. The advisory never
changes an exit code, never enters the run-evidence JSON, and never lands in
`blocking_reasons`; a model with no migrations counterpart (or an unreadable DDL) yields
no finding rather than a false alarm.

**What the advisory does NOT cover.** Its shadow side is the GOVERNED DECLARATION in
`dbt/models/**/_models.yml`, not the built relation. Seshat does not set dbt's
`contract: {enforced: true}`, so dbt never checks a materialized model against that
declaration. The comparison is therefore DECLARED-vs-MIGRATION: a model whose SELECT
list drifts from its own `_models.yml` is invisible to it, and a stale declaration can
in principle flag a pair whose built shapes agree. Reading the built shape would need
`information_schema` and a live DSN, which this offline static check deliberately does
not have; reading the scaffold plan instead was rejected because the generated `.sql`
files are skeletons an operator completes, so the plan describes a pre-completion shape
and reported a phantom divergence on the committed worked example. A table whose
migration history contains a column-changing `ALTER TABLE` is omitted from the
comparison entirely rather than compared against a stale `CREATE TABLE` shape.

The parity test asserts, against the migration-built gold fact:

1. equal fact row count;
2. preserved distinct count of the fact's degenerate / business key;
3. each additive money-measure sum equal to the cent -- absolute delta `<= 0.01` per
   additive measure, matching the committed money scale (e.g. `NUMERIC(12,2)`);
4. equal per-dimension distinct member counts -- each conformed dimension's member count,
   including any unknown / sentinel member where the gold model defines one.

The per-dimension count closes the divergent-unknown-member gap (a dbt unknown-member
handling that diverges from the migration's sentinel would otherwise pass a fact-only
check). A mismatch keeps Gold Ready `blocked` and keeps migrations the default. After an
approved switch, the migration files are RETAINED as the parity oracle and the rollback
path; the parity test RE-RUNS on EVERY dbt build while the oracle is retained (never
one-time-at-switch). Retiring a retained migration is a separate, later named-human
decision. The cent tolerance is the stated default -- it is NOT a score.

## The activated dbt project shape

The tracked top-level `dbt/` project stays parallel to `warehouse/`, so the
shadow and migration build paths remain visibly separate:

```text
dbt/
|- dbt_project.yml                    # fixed profile, model roots, and shadow defaults
|- selectors.yml                      # one governed selector per table
|- macros/generate_schema_name.sql    # enforces dbt_shadow_<invocation> schemas
|- models/sources/                    # approved migration-built sources
|- models/staging/<table>/            # cited staging/silver transformation
|- models/marts/<table>/              # cited gold star shadow models
|- models/audit/<table>/              # parity audit model
```

**Model layers (staging -> silver -> gold):**

- `sources/` -- declares the already-built bronze/silver objects dbt reads. Each source
  binds to what the approved map says exists; dbt does not author a source meaning.
- `staging/` -- one staging model per table cleans and types the source per the approved
  `source-map.yaml` (cited by the model contract). Builds the silver shape.
- `marts/` -- one mart model per table reproduces the gold star (the fact + its conformed
  dimensions) exactly as the migration committed it.

**Tests (the first MVP set):**

- `unique(<business_key>)` and `not_null(<business_key>)` on the fact's degenerate /
  business key;
- `relationships` from each fact FK to its dimension;
- the **reconciliation parity test** (the four assertions above) comparing the dbt mart to
  the migration-built gold fact.

Every model carries a filled `templates/dbt-model-contract.md` citing the approved map
(path + git ref + rows for grain/PK/each column). A column with no citation is a defect.

## The first MVP (the CITED worked example -- generic templates stay clean)

The first implemented table is the `retail_store_sales` worked example: one staging
model, six mart models, one parity audit model, and 24 governed tests. The filled dbt
models live under `dbt/models/`; the GENERIC
templates (`templates/dbt-adapter-contract.md`, `templates/dbt-model-contract.md`), the
ADR, and the skill carry NO `retail_store_sales` / C086 values (Principle VII). The filled
instance is documented in a filled worked example under `docs/worked-examples/`; its column / table
specifics are never inlined into the generic artifacts.

## Connection + secrets (Principle IX)

dbt connects via `profiles.yml`. Only `profiles.example.yml`, containing `env_var()`
references and no real host/DSN/credential/token, is committed. Both `profiles.yml` and
`.env` are gitignored; real `SESHAT_DBT_*` values belong only in `.env`.

## Governed command sequence

Install the exact tested pair with `pip install -e ".[dbt]"`:
`dbt-core==1.12.0` and `dbt-postgres==1.10.2`.

```text
seshat dbt doctor --format json
seshat dbt validate --table <table> --format json
seshat dbt plan --table <table> --format json
seshat dbt build --table <table> --accept-plan <digest> --format json
seshat dbt inspect-run --table <table> --artifacts <run-directory> --format json
```

`doctor` opens no database. `validate` proves the static gate/citation contract.
`plan` binds the mapping identity, exact selected graph, versions, and shadow target to
an immutable digest. `build` recomputes that plan before DB access. `inspect-run` is an
optional offline revalidation of an existing run directory, not a second execution.
Missing runtime/profile/DSN/database prerequisites are `[PENDING LIVE PROFILE]`; they
never become fabricated compile, build, test, or parity success.

## Auto-update policy

`dbt-core==1.12.0` + `dbt-postgres==1.10.2` are pinned TOGETHER. Any version change opens a PR; a major
version requires named-human review. NO automerge for a dbt minor or major bump until
compatibility tests exist. (Recorded in `templates/dbt-adapter-contract.md` and ADR 0009.)

## What dbt does NOT do (the scope wall)

- does NOT replace Seshat BI's authority -- a green `dbt build` / `dbt test` never moves a
  stage to `pass` (Tower readiness + a named human do).
- does NOT define source mapping, metric contracts, business rollups, segment mappings,
  semantic logic, or dashboard design -- it cites the approved map / reads F009 contracts.
- does NOT publish or materialize a Power BI model (`DB-connected`, not publish-capable;
  that is the parked F016 adapter).
- does NOT resolve a Principle V judgment call (grain ambiguity, sentinel-vs-null, PII
  publish-safety, business rollup) and never silently changes the declared grain.
- does NOT write outside invocation-scoped shadow schemas or persist raw adapter output.

## See also

- The decision record: `docs/decisions/0009-dbt-is-transformation-adapter.md`.
- The contracts: `templates/dbt-adapter-contract.md`, `templates/dbt-model-contract.md`.
- The agent procedure: `.claude/skills/dbt-transformation-adapter/SKILL.md`.
- The example connection profile: `profiles.example.yml`.
- The category contract: `docs/architecture/product-modules.md`; the copy-me Adapter
  declaration: `templates/adapter-contract.md`.
- The parity target + the worked example: `warehouse/migrations/`,
  a filled worked example under `docs/worked-examples/`.
- Planning history: `specs/023-dbt-transformation-adapter/`; runtime activation:
  `specs/133-activate-dbt-mvp/`.
- `.specify/memory/constitution.md` (Principles III, IV, V, VI, VII, VIII, IX).
