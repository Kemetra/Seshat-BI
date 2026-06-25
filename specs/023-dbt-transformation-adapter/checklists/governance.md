# Governance Checklist: dbt Transformation Adapter

**Purpose**: Verify the spec respects Core Authority -- that dbt is the build ENGINE and
Tower BI remains the brain. This is the feature's "does it respect Core Authority" gate.
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)  **Roadmap feature**: F029 (spec-dir 023)

This feature is the batch's FIRST DB-connected adapter, so the authority bar is HIGHER than
a pure-docs feature's: dbt connects to the DB and runs builds/tests. The questions below
confirm that connection grants dbt EXECUTION rights only -- never the right to create truth.

## Core-vs-Module authority (the architectural rule)

- [ ] CHK-G01 The spec states Core Authority owns truth and dbt (a module/adapter) may only
      READ evidence (the approved map), EXECUTE approved steps (build/test behind the gate),
      and WRITE DERIVED evidence (run/test/parity results) -- never CREATE truth.
- [ ] CHK-G02 dbt does NOT define source mapping, grain, PK, PII flags, or placement; every
      dbt model CITES the approved `source-map.yaml` (FR-002). A model that extends the map is
      a defect.
- [ ] CHK-G03 dbt does NOT define metric contracts, business rollups, or segment mappings
      (those are F009, owned by the metric owner) (FR-003).
- [ ] CHK-G04 dbt does NOT publish or materialize a Power BI model -- it is DB-connected, not
      publish-capable; publishing is the parked F016 adapter, gated separately (FR-009).

## No self-approval (the governance hinge)

- [ ] CHK-G05 A green `dbt test` / `dbt build` does NOT move Silver Ready or Gold Ready to
      `pass`; the stage status is decided by Tower readiness + a named human, citing the dbt
      evidence + the approval (FR-004, US3, SC-003).
- [ ] CHK-G06 dbt run/test/parity results are recorded as `evidence[]` / `blocking_reasons[]`
      in `mappings/<table>/readiness-status.yaml`; the stage status is NOT written by dbt.
- [ ] CHK-G07 dbt does NOT flip a table's default build path from migrations to dbt on its
      own; that switch needs a passing parity test AND a named human approval (FR-006, US4).
- [ ] CHK-G08 The entry gate is absolute: dbt runs NO staging/silver/gold model for a table
      whose Mapping Ready is not `pass` (FR-001, Principle IV, SC-001).

## Principle V -- stop-and-ask (judgment calls)

- [ ] CHK-G09 Grain ambiguity, sentinel-vs-null, PII publish-safety, and business
      rollup/segment mapping are stop-and-ask: dbt never auto-resolves one; the agent
      recommends and a named human decides (FR-003, US1.3, edge cases).
- [ ] CHK-G10 dbt never SILENTLY changes the declared grain; a grain change requires a
      re-approved map, and a model's grain citation would otherwise fail to resolve.
- [ ] CHK-G11 The Human approval boundary section names WHO decides each call (the table/data
      owner for stage transitions + build-path switches; a named reviewer for dbt version
      bumps).

## No fake confidence

- [ ] CHK-G12 Readiness is expressed as `status` + `evidence[]` + `blocking_reasons[]`; the
      spec emits NO numeric confidence/health score for the dbt build or the stage (rule #9).
- [ ] CHK-G13 Every recorded outcome is a MEASURED number (test pass counts, failing row
      counts, the parity row-count/sum deltas) -- never an adjective like "looks clean".

## Generic (no C086 / retail_store_sales baked in)

- [ ] CHK-G14 The generic planned artifacts (the two `templates/dbt-*-contract.md`, the ADR,
      the integration doc, the skill) carry ZERO `retail_store_sales` / C086 specifics
      (FR-012, SC-004).
- [ ] CHK-G15 `retail_store_sales` appears ONLY as the cited filled first-MVP example and the
      named parity target -- never inlined into a generic template (Principle VII).

## Secrets / paths

- [ ] CHK-G16 Only `profiles.example.yml` (placeholders, no secrets) is planned for commit;
      the real `profiles.yml` is enumerated as git-ignored (FR-008, SC-006).
- [ ] CHK-G17 No DSN, credential, host, token, Kaggle/Power BI secret, or local-machine path
      appears anywhere in the spec or the planned artifacts (Principle IX).
- [ ] CHK-G18 All five files are ASCII + UTF-8 no BOM; arrows are `->`, dashes are `--`; no
      Unicode symbols (Principle IX / Windows charmap).

## Allowed-vs-forbidden operations (the explicit boundary)

- [ ] CHK-G19 The spec carries an Allowed operations section (read truth; build/test behind
      the gate; run parity; write derived evidence; recommend a transition) and a Forbidden
      operations section that mirrors every authority rule above.
- [ ] CHK-G20 Forbidden operations explicitly include: running a model before Mapping Ready =
      `pass`; defining mapping/metric/business meaning; auto-approving a stage on a green
      test; silently switching the build path; silently changing grain; publishing Power BI;
      committing a secret; automerging a dbt minor/major bump; creating any dbt file this
      slice.

## Evidence required

- [ ] CHK-G21 The spec states the evidence required for each gated action: a stage `pass`
      needs dbt run/test results + the parity result + a named human approval (owner + date);
      a build-path switch needs the passing parity result + the approval; a blocked stage
      records the measured failing numbers.
- [ ] CHK-G22 Each dbt model's required evidence is its source-map citation (path + git ref +
      rows) for grain/PK/each column.

## Planning-only / scope discipline

- [ ] CHK-G23 This slice writes ONLY the five spec-kit files; the dbt project, both contract
      templates, the ADR, the integration doc, and the skill are ENUMERATED as planned future
      outputs, NOT created (FR-011, SC-005).
- [ ] CHK-G24 The spec edits NO roadmap, NO runtime code, NO existing migration, and NO
      shipped skill; it reconciles WITH `warehouse/migrations` (migrations stay the default)
      without changing it.

## Notes

- The decisive governance question for this DB-connected adapter is CHK-G05/CHK-G08: dbt's DB
  connection buys it EXECUTION (build/test behind a cleared gate) and the right to write
  DERIVED evidence -- it never buys the right to grant itself a `pass` or to build from an
  unapproved source. If a reviewer can find any path where a green `dbt test` alone advances
  a stage, the spec has failed this gate.
- Authority bar vs a pure-docs feature: a docs feature reads nothing and writes only text; a
  DB-connected adapter reads truth, executes, and writes evidence. The extra checks here
  (CHK-G05..CHK-G08, CHK-G16..CHK-G18, CHK-G21..CHK-G22) exist precisely because dbt does more
  than a docs feature and so must be held to more.
