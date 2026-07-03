# dbt as a Transformation Adapter -- how it plugs in behind the gate

- **Status:** Planned (the integration posture is authored here; the dbt project itself is
  a PLANNED future output -- this slice creates NO dbt files).
- **Roadmap feature:** F029 (on-disk spec `023-dbt-transformation-adapter`). When the
  spec-dir number and the F-number disagree, the roadmap F-number wins.
- **Authority category (F024):** Execution Adapter / `DB-connected` (NOT publish-capable).
- **Read with:** `docs/decisions/0009-dbt-is-transformation-adapter.md` (the decision
  record), `templates/dbt-adapter-contract.md` + `templates/dbt-model-contract.md` (the
  contracts), `.claude/skills/dbt-transformation-adapter/SKILL.md` (the agent procedure),
  `profiles.example.yml` (the example connection profile, placeholders only).

## One line

> dbt is the build ENGINE for silver/gold; Tower BI is the brain. dbt may build only
> after Mapping Ready = `pass`, every model cites the approved map, dbt tests are
> evidence (never an approval), and migrations stay the default until a reconciliation
> parity test proves the dbt mart reproduces the existing gold tables.

## Where dbt fits in the medallion flow

The warehouse already builds silver and gold as numbered, idempotent SQL migrations under
`warehouse/migrations/`. That hand-authored SQL is the DEFAULT build path and it is
approved and live. dbt is an OPTIONAL ALTERNATIVE engine for the same silver/gold build --
it does not replace migrations. dbt plugs in at one seam: AFTER Mapping Ready = `pass`, the
agent may invoke dbt (via the skill) to materialize silver/gold and run tests, then records
the results as DERIVED evidence into the table's `readiness-status.yaml`. Tower readiness +
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

For a table already built by migrations, the dbt mart must reproduce the SAME gold output.
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

## The planned dbt project shape (ENUMERATED -- NOT created this slice)

This slice creates NO dbt files. The build slice will create a top-level `dbt/` directory
(its own home, parallel to `warehouse/`, so the two build paths stay clearly separate):

```text
dbt/                                  # PLANNED -- not created this slice
|- dbt_project.yml                    #   project config (profile: a generic profile name)
|- profiles.example.yml               #   -> committed at repo root; real profiles.yml git-ignored
|- models/
|  |- sources/                        #   sources -> the already-built bronze/silver; cite the approved map
|  |- staging/                        #   staging models: clean/type per the approved map (stg_<table>)
|  |- intermediate/                   #   intermediate transforms (only if a model needs one)
|  |- marts/                          #   marts that reproduce the gold star (<table>_mart -> gold.<fact>)
|- tests/                             #   schema + data tests + the reconciliation parity test
|- macros/                            #   shared macros (e.g. the parity-assertion macro)
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

The first table to PLAN (not implement) is the `retail_store_sales` worked example: one
`retail_store_sales` staging model + one mart model + the basic test set above, with the
reconciliation parity test against that table's migration-built gold fact. The filled dbt
models for the worked example will live under the planned `dbt/models/` tree; the GENERIC
templates (`templates/dbt-adapter-contract.md`, `templates/dbt-model-contract.md`), the
ADR, and the skill carry NO `retail_store_sales` / C086 values (Principle VII). The filled
instance is documented in a filled worked example under `docs/worked-examples/`; its column / table
specifics are never inlined into the generic artifacts.

## Connection + secrets (Principle IX)

dbt connects via a `profiles.yml`. Only `profiles.example.yml` (placeholders -- NO host,
NO DSN, NO credential, NO token) is committed at the repo root. The real `profiles.yml`
is git-ignored and supplied by the operator: copy `profiles.example.yml` to `profiles.yml`,
fill the real values, and keep `profiles.yml` OUT of version control. No connection string,
credential, or host MAY appear in any tracked file.

> Human-gated: this slice does NOT edit `.gitignore`. Before the build slice creates a
> real `profiles.yml`, a `profiles.yml` ignore entry must be added to `.gitignore`
> (no `profiles.yml` entry exists today; `.gitignore` ignores `.env*`, the `.pbi/`
> workspace files, `data/raw/`, Python/build caches, and agent scratch dirs, but
> nothing matching `profiles.yml`).

## Auto-update policy

`dbt-core` + `dbt-postgres` are pinned TOGETHER. Patch / minor versions open a PR; a major
version requires named-human review. NO automerge for a dbt minor or major bump until
compatibility tests exist. (Recorded in `templates/dbt-adapter-contract.md` and ADR 0009.)

## What dbt does NOT do (the scope wall)

- does NOT replace Tower BI's authority -- a green `dbt build` / `dbt test` never moves a
  stage to `pass` (Tower readiness + a named human do).
- does NOT define source mapping, metric contracts, business rollups, segment mappings,
  semantic logic, or dashboard design -- it cites the approved map / reads F009 contracts.
- does NOT publish or materialize a Power BI model (`DB-connected`, not publish-capable;
  that is the parked F016 adapter).
- does NOT resolve a Principle V judgment call (grain ambiguity, sentinel-vs-null, PII
  publish-safety, business rollup) and never silently changes the declared grain.
- creates NO dbt file or runtime code in THIS planning-only slice.

## See also

- The decision record: `docs/decisions/0009-dbt-is-transformation-adapter.md`.
- The contracts: `templates/dbt-adapter-contract.md`, `templates/dbt-model-contract.md`.
- The agent procedure: `.claude/skills/dbt-transformation-adapter/SKILL.md`.
- The example connection profile: `profiles.example.yml`.
- The category contract: `docs/architecture/product-modules.md`; the copy-me Adapter
  declaration: `templates/adapter-contract.md`.
- The parity target + the worked example: `warehouse/migrations/`,
  a filled worked example under `docs/worked-examples/`.
- The spec / plan / tasks: `specs/023-dbt-transformation-adapter/{spec,plan,tasks}.md`.
- `.specify/memory/constitution.md` (Principles III, IV, V, VI, VII, VIII, IX).
