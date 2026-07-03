<!--
=============================================================================
 dbt-adapter-contract.md  --  the copy-me declaration a dbt Transformation Adapter fills
=============================================================================
 Seshat BI  -  feature F029 (on-disk spec 023-dbt-transformation-adapter).
 Authority category (F024): Execution Adapter / DB-connected (NOT publish-capable).
 See: docs/architecture/product-modules.md (the normative reference -- the five
      categories, the authority matrix, the two sub-vocabularies),
      templates/adapter-contract.md (the GENERIC copy-me Adapter declaration this
      specializes -- this dbt contract is a filled, dbt-specific instance of it),
      docs/decisions/0009-dbt-is-transformation-adapter.md (the decision record),
      docs/integrations/dbt-adapter.md (how dbt plugs in behind the gate).

 WHAT THIS IS
   A GENERIC, copy-me declaration for a dbt Transformation Adapter -- a build engine
   that materializes already-approved staging/silver/gold transformations over a live
   database. It is one Execution Adapter in the F024 category "Execution Adapter,
   DB-connected". Every dbt adapter instance fills one copy of this contract to
   declare, up front and reviewably: the entry gate it is downstream of, the
   evidence-not-approval rule, the reconciliation parity requirement, the
   optional-alternative posture, the no-secrets rule, the auto-update policy, and the
   operations the authority matrix forbids it.

 THE BOUNDARY  (verbatim from templates/adapter-contract.md / product-modules.md -- do not drift)
   An Execution Adapter is EXECUTION-ONLY. It MUST NOT define metrics, mappings,
   semantic logic, or dashboard design; the definition it executes MUST already exist
   in Core Authority. It MUST NOT create truth or grant approval (named-human / Core
   Authority only). It runs downstream of a gate and fails closed when its required
   approval/evidence is absent.

 HOW TO USE
   Copy this file next to the dbt project it declares (or under the dbt project dir),
   fill every <ANGLE-BRACKET> field, delete this comment banner, and keep it committed
   alongside the project. GENERIC -- no retail_store_sales / C086 values, no real
   hostnames / DSNs / credentials (Principle IX; secrets stay in the git-ignored
   profiles.yml -- only profiles.example.yml with placeholders is committed).
=============================================================================
-->

# dbt Adapter Contract -- <DBT PROJECT NAME>

- **Authority category:** Execution Adapter
- **Connectivity level:** `DB-connected`  *(exactly one -- the STRONGEST it uses; dbt is NEVER publish-capable; it stops at gold)*
- **Product layer:** `<2-3>`  *(the functional axis -- silver/gold transformation; see docs/roadmap/roadmap.md; orthogonal to category)*
- **Roadmap feature:** F029  **On-disk spec:** `specs/023-dbt-transformation-adapter`
- **Engine:** `dbt-core + dbt-postgres`  *(pinned together -- see Auto-update policy)*
- **Owner:** `<named human or role>`
- **Status:** `<Planned | Authored | Shipped>`

## What it does (one line)

> Materializes the already-approved staging -> silver -> gold transformations for a
> mapped table over a live `<database>`, runs dbt tests + the reconciliation parity
> test, and records the results as DERIVED evidence -- it never decides a stage.

## Gate it is DOWNSTREAM of  (the entry gate -- verbatim rule)

An adapter only runs after a readiness gate has passed. For dbt the gate is Mapping Ready.

- **Gated on stage:** Mapping Ready = `pass` for the table.
- **Required approval / evidence:** the approved `source-map.yaml` (path + git ref)
  recorded in `mappings/<table>/readiness-status.yaml` with Mapping Ready = `pass`.
- **Fail-closed behavior (verbatim):** the adapter MUST refuse to run any
  staging/silver/gold dbt model for a table whose `mappings/<table>/readiness-status.yaml`
  does not record Mapping Ready = `pass`, recording a `blocking_reason` instead
  (Principle IV; entry condition). The presence of dbt model files is NOT permission to
  build.

## Boundaries it CROSSES (connectivity)

dbt is `DB-connected` only. Enumerate every external boundary; dbt crosses exactly one.

- opens a connection to a live database to materialize models (`DB-connected`).
- does NOT publish or materialize a Power BI artifact -- that is the parked F016
  `publish-capable` adapter, gated separately. dbt stops at gold (Principle III).

## Approved artifact it MATERIALIZES

The definition MUST already exist in Core Authority (the approved `source-map.yaml`). The
adapter executes it; it does not author it.

- materializes silver and gold from the approved silver -> gold transformations for the
  mapped table (staging -> silver -> gold dbt models that CITE the approved map).
- Every model MUST cite, via its model contract (`templates/dbt-model-contract.md`), the
  approved `source-map.yaml` (path + git ref) and the rows justifying its grain, PK, and
  each column. A model column with no approved map citation is a defect.

## Derived run-evidence it WRITES  (the evidence-not-approval rule -- verbatim)

An adapter may write a RUN RECORD as derived evidence. This is never a new truth or approval.

> dbt test results (counts of passing/failing tests and the failing rows' measured
> numbers) are recorded as `evidence[]` / `blocking_reasons[]` in the readiness status.
> A green `dbt test` MUST NOT move Silver Ready or Gold Ready to `pass`. Tower readiness
> + a named human decide that, citing the dbt evidence + the recorded approval.

- the `dbt build` / `dbt test` run record (what ran, when, with what pass/fail counts).
- the reconciliation parity result (the four assertions below + measured deltas).
- these flow into the EXISTING `mappings/<table>/readiness-status.yaml` `evidence[]` /
  `blocking_reasons[]`; the stage status is decided by Tower readiness + a named human.

## Reconciliation parity requirement  (the optional-alternative posture -- verbatim)

> `warehouse/migrations` remains the DEFAULT build path. dbt becomes a table's build path
> ONLY after the reconciliation parity test passes AND a named human approves the switch.
> Both paths MUST NOT silently feed the same gold tables.

The parity test asserts, for a table already built by migrations, against the
migration-built gold fact:

1. equal fact row count;
2. preserved distinct count of the fact's degenerate / business key;
3. each additive money-measure sum equal to the cent -- absolute delta `<= 0.01` per
   additive measure, matching the committed money scale (e.g. `NUMERIC(12,2)`);
4. equal per-dimension distinct member counts -- each conformed dimension's member count,
   including any unknown / sentinel member where the gold model defines one.

**Tolerance:** cent-level (absolute delta `<= 0.01` per additive measure) is the stated
default; it stays owner-confirmable when the adapter is built. This is NOT a score.

**After an approved switch:** the table's migration files are RETAINED (not deleted) as
the parity oracle and the rollback path, marked superseded-but-kept. While the oracle is
retained, the parity test MUST RE-RUN on EVERY dbt build for that table -- a
one-time-at-switch check is insufficient. Retiring a retained migration is a SEPARATE,
later named-human decision, never a side effect of the switch.

## Auto-update policy (pin dbt-core + dbt-postgres together)

- `dbt-core` and `dbt-postgres` are pinned TOGETHER (never one without the other).
- patch / minor versions open a PR; a major version requires named-human review.
- NO automerge for a dbt minor or major bump until compatibility tests exist.
- record any bump as `<adapter-version-record>`; a major (and, until compatibility tests
  exist, a minor) bump is approved by a named reviewer.

## Secrets handling (Principle IX)

- **Credentials:** the real `profiles.yml` is git-ignored and supplied by the operator;
  it holds the host / DSN / credentials. NEVER inline real values in any tracked file.
- **Committed example only:** `profiles.example.yml` with placeholder values only
  (NO host, NO DSN, NO credential, NO token).

## Forbidden operations (the matrix says NO)

These hold for EVERY dbt Transformation Adapter:

- MUST NOT define source mapping, metrics, business rollups, segment mappings, semantic
  logic, or dashboard design (execution-only); the definition MUST already exist in the
  approved map / metric contracts.
- MUST NOT change the declared grain without a re-approved map; MUST NOT resolve any
  Principle V judgment call (grain ambiguity, sentinel-vs-null, PII publish-safety,
  business rollup) -- these stop-and-ask for a named human.
- MUST NOT create truth or grant approval / move Silver Ready or Gold Ready to `pass`
  (named-human / Core Authority only); a green `dbt test` alone never moves a stage.
- MUST NOT run any model for a table whose Mapping Ready is not `pass` -- it fails closed.
- MUST NOT switch a table's default build path from migrations to dbt without a passing
  parity test AND a named human approval; MUST NOT delete/retire the migration oracle as a
  side effect of a switch; MUST NOT skip the parity re-run on a dbt build while the oracle
  is retained.
- MUST NOT publish or materialize a Power BI model (NOT publish-capable; that is F016).
- MUST NOT emit a numeric / maturity / confidence score (hard rule #9).
- MUST NOT commit `profiles.yml` or any real hostname / DSN / credential / token
  (Principle IX).
- MUST NOT automerge any dbt-core / dbt-postgres minor or major bump.

## How it handles a missing definition or approval

When the artifact it would execute is undefined (no approved map citation), or the gate it
is downstream of is not `pass`, the adapter SURFACES it as a `blocking_reason` and fails
closed -- it never invents the definition, self-approves, or executes past the missing gate
(Principle V; stop-and-ask). A parity mismatch keeps Gold Ready `blocked` and keeps
migrations as the default.

## See also

- The normative reference: `docs/architecture/product-modules.md`.
- The generic copy-me Adapter declaration this specializes: `templates/adapter-contract.md`.
- The per-model contract: `templates/dbt-model-contract.md`.
- The decision record: `docs/decisions/0009-dbt-is-transformation-adapter.md`.
- The integration doc + the enumerated `dbt/` shape: `docs/integrations/dbt-adapter.md`.
- The skill that runs dbt behind the gate: `.claude/skills/dbt-transformation-adapter/SKILL.md`.
- The example connection profile: `profiles.example.yml` (placeholders only).
- The filled first-MVP instance is CITED, never inlined: a filled worked example under `docs/worked-examples/`.
