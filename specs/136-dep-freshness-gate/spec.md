# Feature Specification: Governed Dependency Freshness and Co-Resolution

**Feature Branch**: `136-dep-freshness-gate`

**Created**: 2026-07-17

**Status**: Draft -- awaiting ratification

**Input**: User description: "Governed dependency freshness and co-resolution: keep
dependencies proposed at the latest stable versions and CONFIRM the declared pin
sets actually wire together -- a fail-closed proof that every declared environment
(root package extras, the orchestration project, and their governed cross-products)
resolves as one install, plus advisory latest-stable reporting that PROPOSES bumps
of governed pins to the owner and never self-applies them."

## Purpose and Readiness Stage

This feature adds a **dependency-integrity CI gate** and an **advisory freshness
report**. It is infrastructure that protects the repository's declared install
environments; it is NOT a readiness stage and it advances no table through
Source -> Mapping -> Silver -> Gold -> Semantic Model -> Dashboard -> Publish.

It exists because a real conflict landed on `main` this week and sat undetected:

- Spec 133 pinned `dbt-core==1.12.0` in the root package `dbt` extra.
- Spec 134 pinned `dagster-dbt==0.29.14` in the orchestration project, and that
  release declares `dbt-core <1.12`.
- No job ever installed the two pin sets together, so the `ResolutionImpossible`
  conflict was invisible on `main` from the day both merged until spec 135's first
  implementation task tried to build one environment and hard-stopped. The owner
  had to make an unplanned pin decision mid-implementation (spec 135, in flight on
  a parallel branch, resolves it by dropping the unused `dagster-dbt` pin).

This feature ensures the NEXT such conflict is caught by CI on the day it lands,
not months later, and that latest-stable drift is surfaced to the owner as a
PROPOSAL rather than silently applied.

## Constraints (ratified posture this feature must honor)

- **NO new public `seshat` CLI verb** (ratified Option B). The co-resolution gate
  and the freshness report ship as a script under `scripts/` plus a CI job. Any
  agent-facing surface is a skill or an extension of an EXISTING surface -- never
  a new verb. (Principle I: the gate is what the agent CALLS; the agent does not
  gain a new command.)
- **The co-resolution gate needs the network** (it asks PyPI to resolve declared
  pin sets). Therefore it is a **CI job**, NOT part of the offline, stdlib-only
  static `seshat check` gate. The offline static core stays network-free
  (Principle VIII). This is an honest, feature-justified boundary, not a weakening
  of the static-first posture.
- **The co-resolution gate is a SOLVER check, not an install-into-CI change.** It
  proves declared extras and cross-products resolve together in EPHEMERAL, throwaway
  environments; it MUST NOT install any optional extra into the CI test interpreter.
  The existing isolation posture -- CI installs `.[dev]` only, so a passing unit
  suite proves every driver/reader/adapter import is lazy (B1/B3) -- MUST be
  preserved unchanged.
- **Governed pins are never auto-bumped.** Freshness output is a PROPOSAL to the
  owner carrying a solve-proof for the proposed combination. The agent proposes;
  the owner disposes (Principle V).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Co-resolution proof catches a cross-environment conflict (Priority: P1)

A contributor opens a PR that pins a dependency in one declared environment which
is incompatible with a pin already declared in another declared environment (the
exact spec-133 / spec-134 shape). A CI job resolves every declared environment and
every declared cross-product in an isolated ephemeral environment and FAILS the
PR, printing the resolver's own error text (redacted if it carries anything
sensitive), naming which declared environment or cross-product could not resolve.

**Why this priority**: This is the whole reason the feature exists. It is the
fail-closed proof that converts a silent, months-long latent conflict into a
same-day red check. Shipping only this story already delivers the core value.

**Independent Test**: Point the gate at a manifest whose declared cross-product is
the historical dbt-core / dagster-dbt pair; the job exits non-zero with the
resolver error. Point it at a manifest of mutually compatible environments; the
job exits zero. Both verifiable without a database and without publishing anything.

**Acceptance Scenarios**:

1. **Given** a manifest declaring the root `dbt` extra and the orchestration
   project as a cross-product, **When** those two pin sets conflict,
   **Then** the job exits non-zero and prints the resolver's `ResolutionImpossible`
   text identifying the incompatible requirement.
2. **Given** a manifest whose declared environments and cross-products are all
   mutually resolvable, **When** the job runs, **Then** it exits zero and records
   one PASS line per declared environment.
3. **Given** a resolve run, **When** it completes, **Then** NO optional extra has
   been installed into the CI test interpreter (the isolation posture is intact).

---

### User Story 2 - Advisory latest-stable freshness proposal (Priority: P2)

Once per cadence (and on demand), a script reports, for each governed pin, the
latest STABLE version available on PyPI and -- when a newer stable exists --
PROPOSES a bump. Each proposal carries a solve-proof: the script attempts to
resolve the affected declared environment WITH the proposed version substituted,
and records whether that combination resolves. The report is an artifact (and,
optionally, a PR comment); it changes NO pin value and opens NO auto-PR.

**Why this priority**: Freshness keeps the repository current, but it is advisory.
The owner must be the one who decides to bump a governed pin (Principle V). This
story depends on the resolver mechanism built in US1 (it reuses the solve-proof),
so it is second.

**Independent Test**: Run the script against the manifest with a stubbed PyPI
index that reports a newer stable version for a governed pin; the report lists the
current pin, the latest stable, and a solve-proof result for the proposed bump. No
tracked pin value changes.

**Acceptance Scenarios**:

1. **Given** a governed pin behind the latest stable, **When** the freshness script
   runs, **Then** the report proposes the bump AND records whether the proposed
   version co-resolves in its declared environment.
2. **Given** a proposed bump whose solve FAILS, **When** the script runs, **Then**
   the report STILL renders, marking that proposal as "proposed, does not resolve"
   rather than crashing or omitting it.
3. **Given** any freshness run, **When** it completes, **Then** no tracked pin value
   in any pyproject.toml has changed and no pull request has been opened.

---

### User Story 3 - Dependabot PRs pass the P2 commit-subject rule and cover every environment (Priority: P3)

Dependabot watches every declared pip environment (including the orchestration
project directory, which is NOT watched today) and its PR commit subjects are
scope-free so they pass the repository's P2 governance rule WITHOUT a human editing
the subject.

**Why this priority**: This removes a standing operational friction (every
Dependabot PR fails CI on its `chore(deps):` scoped subject today) and closes the
coverage hole (the orchestration project is unwatched). It is independent of US1/US2
and is the lowest-risk slice.

**Independent Test**: Inspect `.github/dependabot.yml`: it declares a pip update for
the orchestration project directory, and every pip update block sets a commit-message
prefix that yields a scope-free subject. A subject produced by that configuration
matches the P2 `SUBJECT_RE` used by the governance rule.

**Acceptance Scenarios**:

1. **Given** the updated dependabot config, **When** Dependabot opens a pip PR,
   **Then** the commit subject is scope-free (e.g. `build: bump X from A to B`) and
   passes the P2 rule with no human edit.
2. **Given** the updated dependabot config, **When** the orchestration project has a
   dependency update, **Then** Dependabot raises a PR for it (the directory is
   watched).

---

### Edge Cases

- **PyPI unreachable in CI**: A network/index failure MUST be classified and
  surfaced as an INFRASTRUCTURE failure, distinguishable from a RESOLUTION failure.
  The two exit distinguishably (distinct exit codes / distinct machine-readable
  status), so a flaky network is never mistaken for a real dependency conflict and
  a real conflict is never excused as "probably the network."
- **A proposed bump whose solve fails**: The freshness report MUST still render,
  marking that one proposal as non-resolving; it MUST NOT crash or silently drop it.
- **Yanked releases**: A yanked version MUST NOT be proposed as the latest stable.
- **Pre-releases / dev / rc versions**: Excluded from "latest stable." A pin already
  intentionally on a pre-release is reported as such but pre-releases are never
  proposed as the stable target.
- **A governed pin with an upper bound** (e.g. `mcp>=1.28,<2`): "latest stable" is
  reported honestly even when it sits ABOVE the declared ceiling. The solve-proof
  ALWAYS substitutes the proposed version (FR-009); when the declared ceiling or a
  sibling pin forbids it, the proof records RESOLUTION with the forbidding
  requirement named -- that IS the actionable information (what the owner would
  have to relax). The gate never silently relaxes a ceiling (plan-review D3).
- **A manifest entry pointing at a missing pyproject or an undefined extra**: The
  gate fails closed with a clear message naming the bad manifest entry (a
  configuration error is distinguishable from both INFRA and RESOLUTION).
- **An environment with no pins to check** (only unpinned floors): still resolved
  as a declared environment; a successful empty-delta freshness result is a PASS,
  not an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain the declared install environments as
  committed DATA in a manifest file, NOT hardcoded in any script. Each entry
  declares which pyproject to read, which extras to include, and any cross-product
  combinations to resolve together.
- **FR-002**: The co-resolution gate MUST resolve each declared environment and each
  declared cross-product using PyPI, in an EPHEMERAL environment per environment,
  and MUST NOT install any optional extra into the CI test interpreter. Any member
  that IS a repository-local project (the root package, the orchestration project)
  MUST be assembled as a LOCAL PATH requirement (e.g. the checkout root with its
  extras), NEVER by distribution name -- the gate proves the PR's tree resolves,
  not PyPI's published copy of it (plan-review D1). The manifest schema marks
  local projects explicitly.
- **FR-003**: The co-resolution gate MUST be fail-closed: any declared environment
  or cross-product that cannot resolve MUST cause a non-zero exit, and the resolver's
  own error text MUST be surfaced (redacted only if it carries a sensitive value).
- **FR-004**: The gate MUST distinguish an INFRASTRUCTURE failure (PyPI/index
  unreachable, network error) from a RESOLUTION failure (a genuine dependency
  conflict) via distinct, machine-readable outcomes, so CI can tell a flaky network
  from a real conflict. Classification MUST default to RESOLUTION (fail-closed,
  non-zero) when ambiguous; INFRA requires an explicit, fixture-tested network
  signature. An unrecognized failure is never excused as INFRA (plan-review D2).
- **FR-005**: The gate MUST also distinguish a CONFIGURATION error (manifest points
  at a missing pyproject or an undefined extra) from both INFRA and RESOLUTION.
- **FR-006**: The co-resolution gate MUST run as a CI job, NOT as part of the
  offline static `seshat check` gate, and MUST NOT add a new rule to the static
  checker or change any existing rule's behavior.
- **FR-007**: The freshness reporter MUST, for each governed pin, determine the
  latest STABLE version available on PyPI, EXCLUDING pre-releases, dev/rc builds,
  and yanked releases.
- **FR-008**: When a newer stable version than a governed pin exists, the freshness
  reporter MUST emit a PROPOSAL to bump it, and MUST NOT change any tracked pin
  value and MUST NOT open a pull request.
- **FR-009**: Each freshness PROPOSAL MUST carry a solve-proof: the reporter attempts
  to resolve the affected declared environment with the proposed version substituted
  and records whether that combination resolves.
- **FR-010**: A proposed bump whose solve-proof FAILS MUST still be rendered in the
  report, marked as non-resolving; the report MUST NOT crash or omit it.
- **FR-011**: The freshness report MUST be produced as a CI artifact. It MAY
  additionally be posted as a PR comment, but posting MUST be opt-in (off by default)
  and MUST NOT be a merge-blocking verdict.
- **FR-012**: The system MUST NOT auto-apply, auto-bump, or auto-merge any dependency
  change. Every bump of a governed pin is a human action taken on a PROPOSAL.
- **FR-013**: `.github/dependabot.yml` MUST declare a pip update for the orchestration
  project directory (currently unwatched), in addition to the existing root pip and
  github-actions ecosystems.
- **FR-014**: Every pip update block in `.github/dependabot.yml` MUST configure a
  commit-message prefix that yields a SCOPE-FREE subject (no parenthesized scope),
  so a Dependabot pip PR passes the P2 governance rule with no human edit.
- **FR-015**: The manifest MUST be generic over declared environments: it MUST be
  correct both BEFORE spec 135 merges (orchestration pins `dagster-dbt`) and AFTER
  (orchestration drops `dagster-dbt`, adds `seshat-bi[dbt]`). The gate MUST NOT
  hardcode today's pin list; adding a future project or extra is a manifest edit
  only.
- **FR-016**: The redaction applied to any surfaced resolver error MUST reuse the
  repository's existing secret-shape posture (the C2 connection-string shapes), so
  the gate cannot leak a credential-shaped token in a traceback.
- **FR-017**: The gate and reporter MUST be exercised by tests that do NOT contact a
  real database and do NOT require live PyPI in the unit path (PyPI/index behavior is
  stubbed or fixtured for the deterministic unit tests; a live-network CI job runs
  the real resolve).

### Key Entities *(include if feature involves data)*

- **Declared environment**: A named install target -- a pyproject path plus a set of
  extras -- that MUST resolve as one install. Example: the root package with the
  `dbt` extra; the orchestration project.
- **Cross-product**: A named combination of two or more declared environments (or a
  pyproject + a union of extras) that MUST resolve together as one install. This is
  the entity the spec-133 / spec-134 conflict lived in and that nothing checked.
- **Governed pin**: A dependency requirement whose version a spec deliberately pins
  (the spec-133 dbt pair, the spec-134 dagster pin, any pin a spec names). It is
  NEVER auto-bumped; freshness only PROPOSES changing it.
- **Freshness proposal**: An advisory record: current pin, latest stable, and the
  solve-proof result for the proposed substitution.
- **Resolve outcome**: The classified result of one resolve attempt -- one of PASS,
  RESOLUTION (conflict), INFRA (network/index), or CONFIG (bad manifest entry).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A PR reintroducing the historical dbt-core / dagster-dbt cross-product
  conflict fails the co-resolution CI job with a non-zero exit on the same run,
  before merge (the incident's months-long latency drops to one CI run).
- **SC-002**: After the change, CI still installs only `.[dev]` into its test
  interpreter, and the unit suite still passes -- the lazy-import isolation proof is
  unchanged (no optional extra leaked into the CI env).
- **SC-003**: A Dependabot pip PR (root or orchestration) passes the P2 governance
  rule with zero human edits to its commit subject.
- **SC-004**: When PyPI is unreachable, the job reports INFRA and does NOT report a
  spurious RESOLUTION conflict (a reviewer can tell the difference from the outcome
  alone).
- **SC-005**: The freshness report renders every governed pin's latest-stable status
  and never mutates a tracked pin or opens a PR.

## Assumptions

- The declared environments the gate must protect today are: the root package with
  each of its optional extras, the orchestration project, and the cross-product of
  the root `dbt` extra with the orchestration project (the incident's shape). The
  committed manifest enumerates these; a maintainer edits it as the repository grows.
- `pip` (with its resolver) is the resolution backend, matching what the repository
  and its CI already use to install. Migrating to `uv` or a lockfile is out of scope.
- PyPI is the index of record for "latest stable." A yanked release is treated as
  not-latest; a pre-release/dev/rc is not a stable target.
- The P2 governance rule accepts a scope-free `<type>: <desc>` subject and rejects a
  parenthesized scope; a Dependabot `commit-message.prefix` set to a P2 type without
  `include: scope` yields a conforming subject. (Confirmed against the current
  Dependabot options reference and the P2 rule's `SUBJECT_RE`.)
- The orchestration project keeps its own environment (its dagster-smoke workflow
  builds it in an isolated venv); this feature adds a solver-only co-resolution check
  and does not change that isolation.
- Spec 135 is in flight on a parallel branch and will change the orchestration pin
  set; the manifest and gate are designed to be correct across that change without
  edits to the script.

## Clarifications

Recommended answers are recorded below with one-line reasoning. Anything that would
bump a governed pin, change merge behavior, or auto-approve is a Principle-V human
seam and is left UNANSWERED under "Open for human."

### Recommended (answered)

- **Q: Which resolver backend?** A: `pip` with its dependency resolver, invoked in
  resolve-only mode. Reason: it is what CI already installs with, so a co-resolution
  proof in the same resolver matches production install behavior; no new toolchain.
- **Q: What is the resolve-only mechanism?** A: `pip install --dry-run --report`
  into an ephemeral throwaway virtual environment per declared environment. Reason:
  it reports the resolved set WITHOUT installing into the CI interpreter, preserving
  the lazy-import isolation proof (SC-002).
- **Q: Freshness cadence?** A: Weekly, mirroring the existing Dependabot cadence,
  plus on-demand via `workflow_dispatch`. Reason: aligns freshness with the existing
  dependency-update rhythm; on-demand covers ad hoc checks.
- **Q: What counts as "latest stable"?** A: The highest non-yanked release that is
  NOT a pre-release/dev/rc. Reason: matches the ordinary operator expectation of a
  "stable" upgrade target and avoids proposing churn-y pre-releases.
- **Q: Freshness report surface?** A: A CI job artifact by default; an OPTIONAL,
  off-by-default PR comment (mirroring the existing opt-in friendly-PR-summary
  pattern). Reason: keeps the report visible without turning advisory output into a
  gate or a noisy default.
- **Q: Where does the manifest live and in what format?** A: A single committed YAML
  file at `dependency-environments.yaml` in the repo root, read by the gate script.
  Reason: short repo-relative path (Windows MAX_PATH), YAML matches the repo's other
  committed data manifests, and root placement makes it obvious it governs the whole
  repository. (Author's call per the task; does not require human ratification.)
- **Q: Does the co-resolution gate block merge?** A: The gate JOB itself exits
  non-zero on a real conflict (fail-closed by design); whether that job is a
  REQUIRED status check that blocks the merge button is a repository-administration
  choice -- see "Open for human." Reason: the code posture (fail-closed) is a design
  fact; making it merge-blocking is a human policy decision.

### Open for human

> Should any governed pin actually be bumped as a result of a freshness proposal
> (e.g. raising the `mcp` ceiling, or any dbt/dagster/psycopg2 pin)? The agent
> proposes; only the owner may accept a governed-pin change.

> Should the co-resolution CI job be configured as a REQUIRED (merge-blocking)
> status check on protected branches, or remain a visible-but-non-blocking check?
> This changes merge behavior and is a repository-administration decision.

> Should the advisory freshness PR comment be enabled by default for this
> repository (rather than off-by-default opt-in)? Turning an advisory surface on by
> default is a policy call, not an implementation default.

> Should Dependabot ever be permitted to auto-merge any dependency PR (e.g.
> patch-level github-actions bumps)? Auto-merge is an auto-approve behavior reserved
> to the owner and is explicitly out of scope for the agent to enable.
