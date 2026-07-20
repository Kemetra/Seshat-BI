# Dependency Update Policy -- how every dependency and toolchain bump is classified, checked, and merged safely

- **Status:** Authored (the F031 enumerated deliverable; docs/operations, no runtime
  code, no CI/bot config, no `seshat check` rule).
- **Authority category:** Maintenance Automation  *(sub-axis: none / `--`)* -- per
  `docs/architecture/product-modules.md` (the five-category contract, F024 / on-disk
  spec 018). Maintenance Automation runs WITHOUT a per-invocation human trigger
  (scheduled / CI / a bot PR) and emits ONLY derived evidence (a lane label, recorded
  per-check results); it never creates truth and never self-approves. It carries no
  Module capability level and no Adapter connectivity level, and it declares NO
  connectivity level -- only Execution Adapters do.
- **Roadmap feature:** F031  **On-disk spec:** `specs/025-adapter-maintenance-policy`.
  When the spec-dir number (025) and the roadmap F-number (F031) disagree, the F-number
  wins.
- **Decision record:** `docs/decisions/0011-safe-auto-updates.md` (the ADR that records
  why automerge is confined to Lane A on green CI, below the readiness spine).
- **Readiness stage affected:** none directly (see the closing section).

## What this is

This is the policy that makes Constitution Principle II ("Depend, Never Fork") safe in
practice. It classifies every update PR into one of three lanes by blast radius, fixes
the required checks an update PR must pass before it can merge, and states the one
invariant that keeps the whole thing inside the Constitution. It governs the kit's
borrowed engines and toolchain (the dev tools, the Postgres driver, the dbt / Dagster /
Power BI adapters) so the kit stays current without ever letting an upgrade become a
quiet change to truth.

The adapter-specific overlay -- the compatibility-review trigger and the Lane B vs Lane
C split for the dbt / Dagster / Power BI execution adapters -- lives in
`docs/operations/adapter-update-policy.md`. That doc references THIS lane table rather
than re-stating it.

## The load-bearing invariant (stated identically across this policy, the adapter overlay, and the ADR)

> No update in ANY lane may bypass a readiness gate or move any stage to `pass`;
> automerge lives entirely below the readiness spine.

An update that could regress a gate (`seshat check`, `retail validate`, the silver/gold
build, the semantic-model checks) MUST re-pass that gate before merge. It never
auto-promotes a stage and never clears a blocker. Automerge is a mechanical action in
the dependency / CI plane only -- it does NOT define business meaning, approve a metric
or mapping, publish a Power BI artifact, or touch the readiness spine.

## The three lanes (the classification spine)

Every update PR is classified into EXACTLY ONE lane before it can merge. The lane
decides automerge eligibility and whether a named human review is mandatory. The
package names are LANE-MEMBERSHIP examples (Principle VII) -- the borrowed-engine and
toolchain names this policy governs, not worked-example specifics. A real PR also names
its `<dependency>` and resolved `<lane>` explicitly.

| Lane | Membership (examples -- not exhaustive) | Automerge eligible | Named human review |
|------|------------------------------------------|--------------------|--------------------|
| **Lane A -- allowed-auto** | Ruff, Pytest, pre-commit / dev tools, GitHub Actions patch/minor, docs tooling | YES, ONLY if every required check is green | not required when checks are green |
| **Lane B -- human-review-required** | `dbt-core`, `dbt-postgres`, `dagster` (`dagster-dbt` removed by the spec-135 owner decision, 2026-07-17), `psycopg2`, Postgres-driver changes, Power BI modeling utilities | NO | REQUIRED before merge -- green checks are necessary but not sufficient |
| **Lane C -- never-automerge** | the official Power BI MCP / execution adapter, anything publish-capable, major DB-driver changes, anything touching credentials / auth, anything that changes semantic-model behavior | NO -- forbidden under any check state | REQUIRED before merge |

Classification is a read-only analysis of the diff, the changed packages, and their
transitive effects. No PR is unclassified; only Lane A items are ever automerge-eligible.

### The transitive-escalation rule (highest blast radius wins)

If a lower-lane update pulls a higher-lane change -- transitively, or via a lockfile
that bumps a publish-capable or driver dependency -- the PR is RECLASSIFIED upward to
the highest lane any affected package falls in. A Lane A label never shields a Lane B/C
effect. The highest blast radius wins; the lowest-friction label never overrides it.

### An update that could change a readiness gate's behavior

An update to a `seshat check` rule dependency, a validator library, or anything that
could change how a gate decides is at minimum **Lane B**: the affected gate MUST
re-pass, and the PR MUST state which gate it touches. No such update is Lane A.

## The required checks for ANY update PR

A fixed set of required checks must pass before merge, in EVERY lane. Lane A may
automerge when they are all green; Lane B/C require the same green checks PLUS the
lane's mandatory named-human review. A red check blocks the merge regardless of lane.

| Required check | Source / availability |
|----------------|------------------------|
| ruff format check | already in `.github/workflows/ci.yml` |
| ruff lint | already in `.github/workflows/ci.yml` |
| `pytest -m unit` | already in `.github/workflows/ci.yml` |
| `seshat check` | already in `.github/workflows/ci.yml` |
| `retail validate` fixture mode | if available (the live surface fixture mode) |
| semantic check fixture mode | if available |
| dbt compile/build smoke | once the dbt adapter exists (F029) |
| Dagster definitions-load smoke | once the Dagster adapter exists (F030) |
| no-secrets scan | hard blocker -- see below |
| no-raw-data scan | hard blocker -- see below |
| dependency-invariants note | recorded per PR -- see below |

ALL required checks MUST pass before merge. A red or absent required check blocks the
merge in every lane, including Lane A automerge; the failing check is named in the PR
and no lane can override it.

### A check that does not yet exist

A required check whose runtime does not yet exist (e.g. the dbt or Dagster smoke before
that adapter exists, or a fixture mode before it is wired) is marked
**"not applicable yet (`<reason>`)"** -- it is NEVER silently treated as passed, and its
absence MUST NOT unblock a merge that another required check is blocking.

### The no-secrets / no-raw-data / no-local-paths hard blocker (Principle IX)

No update may introduce a secret, credential, DSN, token, or local machine path into a
tracked file -- often via a lockfile or a vendored sample. The no-secrets / no-paths /
no-raw-data scan is a HARD merge blocker in every lane. If such a value appears in the
diff: STOP, do not merge, and sweep for similar occurrences. Secrets and connection
values stay in git-ignored `.env` / `.example` files with placeholders only.

### The dependency-invariants note (the minimum three)

Every update PR records a dependency-invariants note that affirms, at minimum, three
invariants -- each `pass`/`fail` with a one-line reason. An unaffirmed invariant FAILS
the check. The note MAY add further invariants but MUST assert at least these three:

1. **Gold-only read surface preserved (Principle III).** The update does not let Power
   BI read `silver` / `bronze`; the gold-only read surface is intact.
2. **No new runtime dependency on the static core's import path unless explicitly
   intended and named (Principle VIII).** The DB driver stays an OPTIONAL, lazily-imported
   extra; the update does not pull an optional/dev dependency into the `seshat check`
   core import chain.
3. **No fork / vendor / re-implement to take the update (Principle II, no fork tax).**
   The update is taken by upgrading the dependency, with no local patch an upstream bump
   would force re-applying.

## Major-version bumps and the compatibility-review trigger

A major-version bump (Lane B/C) or any adapter update triggers an explicit
compatibility review -- naming the gates it could regress, the named reviewer, and the
outcome -- whose durable record lives in F032's compatibility matrix
(`docs/operations/adapter-compatibility-matrix.md`). The policy ROUTES the trigger and
RECORDS the evidence; the compatibility verdict is the named reviewer's, never the
policy's. The adapter overlay (`docs/operations/adapter-update-policy.md`) details this
trigger and the F031/F032 record-vs-policy boundary.

## No fake confidence (hard rule #9)

This policy emits NO health / maturity / confidence score for a dependency. An update's
status is the explicit per-check pass/fail plus the lane and (for B/C) the named
reviewer -- never a fabricated number. A request for a "dependency health score" is
DECLINED with this rationale; any maturity score is DEFERRED (see F033 Release &
Maturity Management).

## What this policy MUST NOT do (the forbidden set)

- Automerge any Lane B or Lane C update, or any update with a red/absent required check.
- Bypass, skip, or weaken any readiness gate (`seshat check`, `retail validate`, the
  silver/gold build, the semantic-model checks) via an update.
- Move any readiness stage to `pass`, clear a blocker, or self-approve -- through an
  update PR or its automerge (Core Authority owns truth; Principle V).
- Introduce a secret, credential, DSN, token, or local machine path into a tracked file.
- Self-decide a compatibility verdict for a major-version / adapter update -- the policy
  routes and records; the named human decides.
- Emit a dependency health / maturity / confidence score.
- Fork, vendor, or re-implement a dependency to take an update (no fork tax).
- Use `--no-verify`, a gate-skip, an admin force-merge, or a force-push to a protected
  branch. All updates are PR-based; branch protection and the no-`--no-verify` rule are
  assumed (the global git rules), not re-established here.

## How the policy is enforced (the runtime is existing)

The required-check runtime is the EXISTING CI (`.github/workflows/ci.yml`: ruff format
check, ruff lint, `pytest -m unit`, `seshat check`) plus a named human reviewer. This
policy adds NO new runtime, NO `seshat check` rule, NO validator, and NO CLI verb. The
OPTIONAL bot config (`.github/dependabot.yml` / `renovate.json`) is PLANNED, not created:
if later added it ENCODES these lanes (Lane A auto-eligible, Lane B/C review-required,
grouped by package class) and is itself subject to this policy. The dependabot-vs-renovate
choice is DEFERRED to the implementation slice.

## Worked example of classification (the six representative PRs)

To show the lane table is total and unambiguous, the six representative update PRs from
the spec classify with no tie and no gap:

| Update PR | Lane | Automerge-eligible? |
|-----------|------|---------------------|
| A Ruff patch bump | Lane A | yes, if all required checks green |
| A GitHub Action minor bump | Lane A | yes, if all required checks green |
| A `dbt-core` minor bump | Lane B | no -- named review required |
| A `psycopg2` change | Lane B | no -- named review required |
| A major DB-driver bump | Lane C | no -- never automerge |
| A Power BI execution-adapter bump | Lane C | no -- never automerge |

## Readiness stage affected

**None directly.** This policy advances no single readiness stage. It is cross-cutting:
it PROTECTS all seven stages (Source -> Mapping -> Silver -> Gold -> Semantic Model ->
Dashboard -> Publish Ready) from update drift, by requiring that any update which could
regress a gate re-pass that gate before merge, and by forbidding any update from moving a
stage to `pass`. (Mirrors F012's "all stages" cross-cutting framing.)

## See also

- The decision record: `docs/decisions/0011-safe-auto-updates.md`.
- The adapter overlay (references this lane table): `docs/operations/adapter-update-policy.md`.
- The version-truth record this policy reads and enforces against:
  `docs/operations/adapter-compatibility-matrix.md` (F032, on-disk spec 026).
- The category home (Maintenance Automation): `docs/architecture/product-modules.md`
  (F024 / on-disk spec 018).
- The required-check runtime: `.github/workflows/ci.yml`; the `seshat check` static
  surface and the `retail validate` live surface.
- The principles: `.specify/memory/constitution.md` (Principles II, III, V, VIII, IX);
  hard rule #9, `docs/roadmap/roadmap.md`.
- The worked-example reference (cited, never inlined): a filled worked example under `docs/worked-examples/`.
- The spec: `specs/025-adapter-maintenance-policy/spec.md`.
