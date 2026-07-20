# Adapter Update Policy -- the adapter-specific overlay: compatibility review, the Lane B/C split, and the no-fork-tax rule

- **Status:** Authored (the F031 enumerated deliverable; docs/operations, no runtime
  code, no CI/bot config, no `seshat check` rule).
- **Authority category:** Maintenance Automation  *(sub-axis: none / `--`)* -- per
  `docs/architecture/product-modules.md` (the five-category contract, F024 / on-disk
  spec 018). Maintenance Automation runs WITHOUT a per-invocation human trigger and
  emits ONLY derived evidence (a lane label, a recorded compatibility-review hand-off);
  it never creates truth and never self-approves. It carries no Module capability level
  and no Adapter connectivity level, and it declares NO connectivity level -- only the
  Execution Adapters it governs (dbt, Dagster, Power BI) do.
- **Roadmap feature:** F031  **On-disk spec:** `specs/025-adapter-maintenance-policy`.
  When the spec-dir number (025) and the roadmap F-number (F031) disagree, the F-number
  wins.
- **Decision record:** `docs/decisions/0011-safe-auto-updates.md`.
- **Readiness stage affected:** none directly (see the closing section).

## What this is

This is the adapter-specific OVERLAY on the general dependency update policy. It does
not restate the lane table or the required checks -- those live in
`docs/operations/dependency-update-policy.md`, which this doc references. It adds the
three things that are specific to upgrading the kit's borrowed EXECUTION ADAPTERS:

1. the Lane B vs Lane C split for the dbt / Dagster adapters versus the Power BI
   execution adapter,
2. the major-version / adapter compatibility-review trigger and what the review must
   name, and
3. the no-fork-tax restatement (Principle II): an adapter update is taken by upgrading
   the dependency, never by vendoring or re-implementing it.

The adapters governed here are INPUTS to this policy; this feature redefines none of
them. It defines HOW they are upgraded, not WHAT they do.

## The load-bearing invariant (stated identically across this overlay, the dependency policy, and the ADR)

> No update in ANY lane may bypass a readiness gate or move any stage to `pass`;
> automerge lives entirely below the readiness spine.

An adapter update that could regress a gate (`seshat check`, `retail validate`, the
silver/gold build, the semantic-model checks) MUST re-pass that gate before merge. No
adapter update auto-promotes a stage or clears a blocker.

## The adapter Lane split (which adapter falls in which lane)

The lanes and the automerge rules are defined in the dependency update policy; this is
the adapter-specific membership:

| Adapter / dependency class | Lane | Why |
|-----------------------------|------|-----|
| dbt transformation adapter -- `dbt-core`, `dbt-postgres` (F029) | **Lane B** | a named human review is required before merge; green checks are necessary but not sufficient |
| Dagster orchestration adapter -- `dagster` (F030; `dagster-dbt` REMOVED by the spec-135 owner decision, 2026-07-17 -- it excluded dbt-core 1.12 and sat on no execution path) | **Lane B** | a named human review is required before merge |
| Postgres driver -- `psycopg2` / driver changes; Power BI modeling utilities | **Lane B** | a named human review is required before merge |
| **Major DB-driver change** (a major version of the driver) | **Lane C** | never automerge under any check state |
| the official Power BI MCP / execution adapter (F016, parked) -- anything publish-capable, credential / auth, or semantic-model-behavior changes | **Lane C** | never automerge under any check state; publish-capable / credential changes always need a named human |

Lane C governance for the Power BI execution adapter PRESUMES F016 (the execution-only,
publish-capable Power BI adapter), which is parked. This overlay constrains HOW that
adapter is bumped; it adds no execution behavior and does not un-park F016. `pbi-cli` is
no longer the preferred path -- the official Power BI MCP / connection is the preferred
future adapter, and this policy governs its UPDATES, not its implementation.

The transitive-escalation rule still applies (defined in the dependency policy): if a
Lane B adapter update pulls a Lane C transitive change (e.g. a publish-capable or
credential dependency), the PR is reclassified UP to Lane C. The highest blast radius
wins.

The activated feature-133 compatibility boundary is the exact pair
`dbt-core==1.12.0` + `dbt-postgres==1.10.2`. Change the pair together, regenerate the
sanitized manifest fixture, rerun `seshat dbt doctor`, `seshat dbt validate`,
`seshat dbt plan`, the accepted-plan build/test path, and
`seshat dbt inspect-run`, then update the compatibility matrix. Static parse/list
evidence does not satisfy the live boundary; absent a database, record
`[PENDING LIVE PROFILE]`. No dependency update may grant a migration switch or
compatibility attestation.

## The compatibility-review trigger (the F031 / F032 boundary)

A major-version bump (Lane B/C) or any adapter update triggers an explicit
compatibility review. The review is a named human's decision; this policy ROUTES the
trigger and RECORDS the evidence -- it does not self-decide compatibility (Principle V).

The compatibility review MUST name:

- **the gates it could regress** (which readiness gates -- `seshat check`,
  `retail validate`, the silver/gold build, the semantic-model checks -- this adapter
  version could affect),
- **the named reviewer** (a person/role, never "the agent" and never blank), and
- **the outcome** (the reviewer's verdict and any recorded deviation).

### The record / policy boundary (F031 reads + enforces; F032 records)

> F032 (the Adapter Compatibility Matrix) is the RECORD: what is verified-compatible
> -- the supported version RANGES, the smoke-test STATUS, the last-verified DATES, and
> the named OWNERS. F031 (this policy) is the POLICY: what a dependency-update PR must
> DO about a violation, when to re-verify, and what to block.

This split mirrors the matrix's own boundary statement. Concretely:

- An adapter-update PR that changes a supported version MUST update F032's matrix. F032
  states the matrix is the record such a PR updates; ENFORCING that requirement --
  failing the PR, requiring re-verification, blocking the merge -- is THIS policy's job.
  F032 does not gate the PR itself.
- When a PR bumps an adapter past the recorded supported range, the matrix RECORD shows
  the bump now sits outside the verified range; deciding what the PR must do about it
  (re-verify, block, accept) is this policy, not F032.
- The DURABLE compatibility record (the row, its range, its smoke-test status, its
  attesting owner) lives in F032 (`docs/operations/adapter-compatibility-matrix.md`).
  This policy references that row; it does NOT own or duplicate the record.

A named-but-unrun smoke test never makes a version supported; an untested ceiling is
`unknown`, never assumed compatible. Those rules are F032's; this policy reads them as
the version-truth it enforces against.

## The no-fork-tax rule (Principle II, restated for adapters)

An adapter update is taken by UPGRADING the dependency -- never by forking, vendoring,
or re-implementing the adapter to take the update. If an upgrade would force a local
patch that an upstream bump would then make you re-apply, that is a fork tax and the
update STOPS for a named human to decide (it is not silently vendored). The kit depends
on the borrowed engines; it does not fork them. This is the third minimum
dependency-invariant the dependency policy requires every update PR to affirm.

## No fake confidence (hard rule #9)

This overlay emits NO health / maturity / confidence score for an adapter. An adapter
update's status is the explicit per-check pass/fail (from the dependency policy's
required checks), the lane, the named reviewer, and the recorded compatibility-review
outcome with its durable entry in F032's matrix -- never a fabricated number. Any
maturity score is DEFERRED (see F033 Release & Maturity Management).

## What this overlay MUST NOT do (the forbidden set)

- Automerge any adapter update (all adapter classes are Lane B or Lane C).
- Self-decide a compatibility verdict -- the policy routes and records; the named human
  decides.
- Move any readiness stage to `pass`, clear a blocker, or bypass a gate via an adapter
  update.
- Author, modify, or execute any adapter's runtime code, connection logic, or
  transformations (that is the adapters' own concern -- F016 / F029 / F030).
- Introduce a secret, credential, DSN, token, or local machine path into a tracked file.
- Fork, vendor, or re-implement an adapter to take an update.
- Emit an adapter health / maturity / confidence score.
- Un-park F016 or add execution behavior -- this overlay governs updates only.

## Readiness stage affected

**None directly.** This overlay advances no single readiness stage. Like the dependency
policy, it is cross-cutting: it PROTECTS all seven stages (Source -> Mapping -> Silver
-> Gold -> Semantic Model -> Dashboard -> Publish Ready) from adapter-update drift, by
requiring that any adapter update which could regress a gate re-pass it before merge,
and by forbidding any update from moving a stage to `pass`.

## See also

- The general policy this overlays (the lane table + required checks):
  `docs/operations/dependency-update-policy.md`.
- The decision record: `docs/decisions/0011-safe-auto-updates.md`.
- The version-truth record this policy reads and enforces against:
  `docs/operations/adapter-compatibility-matrix.md` (F032, on-disk spec 026).
- The governed adapters (governed here, NOT redefined): F029 (dbt)
  `specs/023-dbt-transformation-adapter/`, F030 (Dagster)
  `specs/024-dagster-orchestration-adapter/`, F016 (Power BI execution adapter, parked).
- The category home (Maintenance Automation): `docs/architecture/product-modules.md`
  (F024 / on-disk spec 018).
- The principles: `.specify/memory/constitution.md` (Principles II, III, V, VIII, IX);
  hard rule #9, `docs/roadmap/roadmap.md`.
- The worked-example reference (cited, never inlined): a filled worked example under `docs/worked-examples/`.
- The spec: `specs/025-adapter-maintenance-policy/spec.md`.
