# Dependency integrity: co-resolution gate and freshness reporter (spec 136)

This tool protects the repository's declared install environments. It has two
modes, both driven by one script (`scripts/dep_coresolve.py`) and one committed
data manifest (`dependency-environments.yaml`). There is NO new `seshat` CLI
verb: the gate is a script plus a CI job.

## Why it exists

A real conflict landed on `main` and sat undetected: spec 133 pinned
`dbt-core==1.12.0` in the root package `dbt` extra, while spec 134 pinned
`dagster-dbt==0.29.14` (which declares `dbt-core<1.12`) in the orchestration
project. No job ever installed the two pin sets together, so the
`ResolutionImpossible` conflict was invisible until spec 135's first build tried
to assemble one environment. This tool catches the NEXT such conflict on the day
it lands, and surfaces latest-stable drift as a PROPOSAL rather than applying it.

## The manifest (`dependency-environments.yaml`)

Committed DATA, not code (the script hardcodes no pin list). Three sections:

- **environments** -- each names a `pyproject`, the `extras` to include, and (for
  a repository-local project) `local: true` with a `path`. A local member is
  assembled as a LOCAL PATH requirement (`<path>[extras]`), NEVER by distribution
  name -- so the gate proves the PR's working tree resolves, not PyPI's published
  copy of it (plan-review D1).
- **cross_products** -- each `combine`s two or more environments that MUST resolve
  together as one install. This is the entity the spec-133 / spec-134 conflict
  lived in and that nothing checked.
- **governed_pins** -- the distributions the freshness reporter tracks, by NAME
  only. Versions are read from the referenced pyproject files at run time, so the
  manifest stays correct across a pin change (adding a future project or extra is
  a manifest edit only, never a script edit).

## The four resolve outcomes

Each resolve attempt classifies to exactly one:

- **PASS** -- the environment / cross-product resolves as one install.
- **RESOLUTION** -- a genuine dependency conflict. Fail-closed, non-zero exit; the
  resolver's own (redacted) error text is printed, naming the failing target.
  Classification DEFAULTS to RESOLUTION on any unrecognized non-zero exit -- a
  real conflict is never excused as "probably the network" (plan-review D2).
- **INFRA** -- a network/index failure (DNS, connection refused, timeout, 5xx).
  A DISTINCT exit code so a flaky network is never mistaken for a conflict, and a
  conflict is never excused as a flake. INFRA is claimed only on an explicit,
  fixture-tested network signature.
- **CONFIG** -- a bad manifest entry (missing pyproject, undefined extra, or an
  ephemeral-venv pip too old for `--report`). Distinct label; fails closed.

Exit codes (each outcome distinct, FR-004/FR-005/SC-004): `0` (all PASS), `1`
(RESOLUTION -- a real conflict), `2` (CONFIG -- a bad manifest entry), `3` (INFRA
-- network/index only). Precedence when several occur: RESOLUTION > CONFIG >
INFRA, so a real conflict is never masked by a co-occurring lesser signal.
RESOLUTION and CONFIG both fail CLOSED and are not retryable; INFRA is the one
retryable/annotatable case.

## Running it

- `python scripts/dep_coresolve.py --check` -- the fail-closed co-resolution gate.
  Resolves every declared environment and cross-product in an EPHEMERAL throwaway
  venv via `pip install --dry-run --report`; NOTHING is installed into the caller's
  interpreter (the lazy-import isolation posture SC-002 is preserved). Runs as the
  `co-resolution` job in `.github/workflows/dep-integrity.yml`.
- `python scripts/dep_coresolve.py --freshness --out report.json` -- the advisory
  reporter. Writes a JSON + Markdown report of latest-stable proposals. Runs
  weekly (and on demand) as the `freshness` job; the report is a CI artifact.

## Governed pins are only ever PROPOSED, never auto-bumped

The freshness reporter reads the latest STABLE version on PyPI (excluding
pre-release/dev/rc builds and fully-yanked releases; yanked is per-file -- a
release is yanked only when ALL its files are). When a newer stable exists it
emits a PROPOSAL carrying a solve-proof: it re-resolves the affected environment
with the proposed version SUBSTITUTED for the current pin (a replace, not an add)
and records whether that combination resolves. When the pin's own declared ceiling
forbids the proposed version, the proof records RESOLUTION naming that ceiling --
the actionable information (what the owner would have to relax). The reporter
changes NO tracked pin value and opens NO pull request. Bumping a governed pin is
a HUMAN action taken on a proposal (Principle V).

## Historical-incident note (SC-001)

Before spec 135 (PR #307) merged, the orchestration project still pinned
`dagster-dbt==0.29.14` (which requires `dbt-core<1.12`) while the root `dbt` extra
pins `dbt-core==1.12.0`. The `root-dbt-plus-orchestration` cross-product genuinely
FAILED to resolve at that point -- that was the historical incident reproducing,
and it is the PROOF the gate works (SC-001), not a defect in the gate. PR #307 has
since merged and dropped the `dagster-dbt` pin, so the cross-product now resolves
cleanly and the `co-resolution` CI job is green. The gate is never weakened and the
cross-product is never dropped to force a local pass.
