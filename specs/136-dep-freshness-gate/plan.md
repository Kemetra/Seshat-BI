# Implementation Plan: Governed Dependency Freshness and Co-Resolution

**Branch**: `136-dep-freshness-gate` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/136-dep-freshness-gate/spec.md`

## Summary

Add a fail-closed **co-resolution CI job** that proves every declared install
environment and cross-product resolves as one install (catching the exact
spec-133 / spec-134 conflict on the day it lands), plus an **advisory freshness
reporter** that proposes latest-stable bumps of governed pins WITHOUT applying
them. Declared environments live as committed DATA in a manifest; the resolver
proof runs `pip install --dry-run --report` in an ephemeral venv per environment
so nothing is installed into the CI interpreter (the lazy-import isolation posture
is preserved). Dependabot is extended to watch the orchestration project and to
emit scope-free, P2-passing commit subjects. No new `seshat` CLI verb.

## Technical Context

**Language/Version**: Python 3.13 (matches the repo `requires-python`).

**Primary Dependencies**: stdlib only for the script core (`json`, `subprocess`,
`urllib`, `tomllib`, `venv`), reusing the repo's existing `pyyaml` (already a
runtime dep) to read the manifest inside a step that already tolerates yaml, and
`pip`'s resolver invoked as a subprocess. No new third-party dependency added to
the package.

**Storage**: N/A. Inputs are committed text (pyproject files + the manifest);
outputs are a CI artifact (JSON/Markdown report) and process exit codes.

**Testing**: pytest. Unit tests stub the PyPI index and the resolve subprocess so
they are deterministic and offline (marker `unit`). The real live resolve runs only
in the new CI job.

**Target Platform**: GitHub Actions `ubuntu-latest` (network-capable). The offline
static gate is unaffected and stays platform-agnostic.

**Project Type**: Single project (script + CI job + committed manifest), consistent
with the existing `scripts/` + `.github/workflows/` shape.

**Performance Goals**: The co-resolution job resolves a bounded set of declared
environments (currently well under a dozen); each resolve is a dry-run and does not
download or build wheels. Total job time on the order of the existing CI install
steps.

**Constraints**: Offline static `seshat check` MUST remain network-free and
stdlib-only (Principle VIII). The resolver proof MUST NOT install optional extras
into the CI test interpreter (SC-002). ASCII only; short repo-relative paths
(Windows MAX_PATH); no committed secret shapes.

**Scale/Scope**: Two Python surfaces (a `scripts/` gate/reporter module and its
tests), one committed manifest, one new CI job (added to the existing `ci.yml` or a
sibling workflow), and a `dependabot.yml` edit. No package API change, no new CLI
verb, no pin value change.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS. The co-resolution gate is a
  non-zero process exit the agent CALLS, not a paragraph of prose and not a new
  command the agent operates. The freshness reporter proposes; the exit code /
  owner disposes.
- **Principle II (Depend, Never Fork)**: PASS. Uses `pip` as-is; forks nothing.
- **Principle V (Agent Stops at Judgment Calls)**: PASS -- load-bearing. Governed
  pins are never self-bumped; a bump is a human action on a PROPOSAL. Whether to
  bump, whether the job is merge-blocking, and whether to auto-merge are recorded
  as UNANSWERED human seams in spec Clarifications.
- **Principle VIII (Static-First Governance, Live Deferred)**: PASS -- load-bearing.
  The static `seshat check` core stays stdlib-only and network-free; this
  network-dependent check is a SEPARATE CI job (mirrors how `dagster-smoke`,
  `retail semantic-check`, and `retail kit-lint` sit outside the stdlib-only core).
  The `--dry-run --report` resolve preserves the driver-free import path (B1/B3):
  no optional extra is imported by or installed into the CI test interpreter.
- **Principle IX (Secrets and Reproducibility)**: PASS. Surfaced resolver errors are
  redacted through the repo's existing C2 secret-shape posture (FR-016); the manifest
  and report carry no credentials; paths are short.

**Noted, honest deviation (not a violation)**: the co-resolution/freshness work
touches the network, which the static core never does. This is DELIBERATE and
SCOPED to a CI job; it does not move any behavior into the offline gate and does not
lower the static floor. Framed per Principle VIII's own precedent (live surfaces
live in their own spec/job), this is the correct home for a network check.

No entry in Complexity Tracking: there is no principle violation to justify.

## Project Structure

### Documentation (this feature)

```text
specs/136-dep-freshness-gate/
|- spec.md         # Feature specification (committed)
|- plan.md         # This file
|- tasks.md        # Dependency-ordered, TDD-shaped tasks
`- analysis.md     # Cross-artifact consistency read
```

### Source Code (repository root)

```text
dependency-environments.yaml          # NEW committed DATA: declared environments
                                      #   + cross-products (FR-001, FR-015)

scripts/
`- dep_coresolve.py                   # NEW: reads the manifest, resolves each
                                      #   declared environment / cross-product in
                                      #   an ephemeral venv via pip --dry-run
                                      #   --report; classifies PASS/RESOLUTION/
                                      #   INFRA/CONFIG; renders the freshness
                                      #   report; redacts resolver errors.
                                      #   No new CLI verb -- a plain script.

tests/unit/
`- test_dep_coresolve.py             # NEW: offline unit tests. Stub the resolve
                                      #   subprocess + the PyPI index so classify /
                                      #   redact / render / propose logic is tested
                                      #   deterministically without the network.

.github/
|- dependabot.yml                     # EDIT: add the orchestration pip ecosystem
                                      #   (FR-013) + scope-free commit-message
                                      #   prefix on every pip block (FR-014).
`- workflows/
   `- ci.yml  (or dep-integrity.yml)  # EDIT/NEW: the co-resolution CI job +
                                      #   the weekly/on-demand freshness job.
```

**Structure Decision**: Single project. The gate/reporter is a `scripts/` module
(mirroring `scripts/release_candidate_audit.py`, `scripts/export_agent_bundles.py`),
its pure logic is unit-tested under `tests/unit/`, and the manifest is a root-level
committed YAML (`dependency-environments.yaml`) -- a short path, matching the repo's
other committed data manifests. No `src/seshat/` package code and no CLI dispatch
entry are added, honoring the "no new verb" constraint.

## Design detail

### 1. The environments manifest (committed DATA)

`dependency-environments.yaml` (root, YAML, UTF-8 no BOM, ASCII). Shape (illustrative,
not code):

```text
version: 1
environments:
  - id: root-dev
    pyproject: pyproject.toml
    extras: [dev]
  - id: root-dbt
    pyproject: pyproject.toml
    extras: [dbt]
  - id: orchestration
    pyproject: orchestration/dagster/pyproject.toml
    extras: [dev]
cross_products:
  - id: root-dbt-plus-orchestration
    combine: [root-dbt, orchestration]     # the spec-133 / spec-134 shape
governed_pins:
  - dist: dbt-core          # spec 133
  - dist: dbt-postgres      # spec 133
  - dist: dagster           # spec 134
  - dist: dagster-dbt       # spec 134 (removed by spec 135; manifest edit only)
  - dist: psycopg2-binary
  - dist: mcp
```

The script reads pins FROM the referenced pyproject files at run time (it does not
duplicate version strings), so the manifest lists WHICH distributions are governed,
not their current versions. This keeps the manifest correct across spec 135's pin
change (FR-015): when orchestration drops `dagster-dbt` and adds `seshat-bi[dbt]`,
the maintainer edits the manifest's `governed_pins`/`cross_products`, not the script.

Each entry is validated on load; a missing pyproject or an undefined extra yields a
CONFIG outcome (FR-005), distinct from INFRA and RESOLUTION.

### 2. The resolver-proof mechanism

For each declared environment and cross-product:

1. Read the referenced pyproject(s), assemble the full requirement set for the
   declared extras / union (a cross-product unions the requirement sets of its
   members). HARD RULE (plan-review D1): a member that IS a repository-local
   project is assembled as a LOCAL PATH requirement (`<checkout>[extras]`,
   `orchestration/dagster`), NEVER by distribution name -- otherwise pip
   resolves the PUBLISHED seshat-bi from PyPI and the gate validates yesterday's
   pins instead of the PR's tree. The manifest marks local projects explicitly;
   a unit test pins that assembled requirement strings for local members are
   paths, not names. `pip install --dry-run` handles local-path members
   natively; a transitive conflict still surfaces as RESOLUTION.
2. Create an EPHEMERAL throwaway virtual environment (`python -m venv` in a temp
   dir, removed after).
3. Run `pip install --dry-run --report <report.json> <requirements...>` inside that
   venv. `--dry-run` resolves WITHOUT installing; `--report` emits the resolved set
   as JSON. This is the SOLVER check: it proves the pins wire together without
   installing anything into the CI interpreter (SC-002, Principle VIII / B1-B3).
4. Classify the outcome:
   - exit 0 with a report -> **PASS** (record the resolved set).
   - resolver conflict (`ResolutionImpossible` / non-zero with a resolution error in
     stderr) -> **RESOLUTION**; capture the resolver's own text.
   - network/index failure (connection error, index timeout, DNS, 5xx) ->
     **INFRA**; distinct exit code / status so a flaky network is never read as
     a conflict (FR-004, SC-004). Classification defaults to RESOLUTION when
     ambiguous (fail-closed, plan-review D2); INFRA requires an explicit,
     fixture-tested signature. The ephemeral venv's pip must support
     `--report` (>= 22.2); an unusable venv pip is a CONFIG outcome, not a
     crash (plan-review D5).
   - manifest points at a missing file / undefined extra -> **CONFIG** (FR-005).
5. Redact any captured resolver text through the repo's existing C2 secret-shape
   redaction posture before surfacing (FR-016), so no credential-shaped token leaks
   in a traceback.

The gate exits non-zero on any RESOLUTION or CONFIG outcome and prints the
(redacted) resolver text naming the failing environment/cross-product (FR-003). An
INFRA outcome exits with its own distinct code so CI can retry/annotate rather than
mislabel a conflict.

### 3. The freshness reporter surface (NO new CLI verb)

The same `scripts/dep_coresolve.py` (a `--freshness` mode, or a sibling function)
queries the PyPI JSON API (`https://pypi.org/pypi/<dist>/json`) via stdlib `urllib`
for each governed pin, computes the latest STABLE version (drop yanked, drop
pre-release/dev/rc; FR-007), and for each pin behind latest emits a PROPOSAL. Each
proposal runs a solve-proof: re-resolve the affected declared environment with the
proposed version substituted, recording PASS/RESOLUTION (FR-009). A proposal whose
solve fails is still rendered, marked "proposed, does not resolve" (FR-010). The
reporter changes NO pin value and opens NO PR (FR-008, FR-012).

Output: a JSON + Markdown report written to a path uploaded as a CI artifact
(FR-011). An OPTIONAL, off-by-default PR comment reuses the existing opt-in pattern
(mirrors `POST_FRIENDLY_PR_SUMMARY`): posting is gated behind a repo Actions
variable and never blocks merge.

### 4. The CI job design

A new job (added to `.github/workflows/ci.yml`, or a sibling `dep-integrity.yml`
to keep it isolated from the offline gate):

- `co-resolution` job: `ubuntu-latest`, Python 3.13, `pip install --upgrade pip`,
  then `python scripts/dep_coresolve.py --check` (reads the manifest, runs every
  declared resolve, fails closed). It installs NO optional extra into its own
  interpreter -- all resolves happen in per-environment ephemeral venvs.
- `freshness` job (schedule: weekly + `workflow_dispatch`): runs
  `python scripts/dep_coresolve.py --freshness --out report.json`, uploads the
  report artifact, optionally posts the opt-in comment.

The existing `check` / `smoke` / `dagster-smoke` jobs are UNCHANGED; the `check`
job still installs only `.[dev]` (SC-002 preserved).

### 5. The dependabot.yml changes

- ADD a third `package-ecosystem: pip` block with
  `directory: "/orchestration/dagster"` (FR-013), weekly, with the `dependencies`
  label.
- On EVERY pip block, add:
  ```text
  commit-message:
    prefix: "build"
  ```
  `prefix` without `include: scope` yields a scope-free subject
  (`build: bump X from A to B`) that matches the P2 `SUBJECT_RE`
  (`^(?:feat|fix|...|build|...): .+`), so the bot PR passes P2 with no human edit
  (FR-014). `build` is chosen because a dependency bump IS a build-system change and
  `build` is in the P2 allow-list. (`chore` also passes P2; `build` is the more
  precise conventional-commits type for dependency updates.)

The github-actions ecosystem block is left as-is (its subjects already pass, and
its scope is out of this feature's stated pip focus) except for the same
commit-message prefix if a `chore(deps):`-shaped subject would otherwise trip P2 --
verified during implementation against a produced subject.

### 6. Redaction reuse

The gate masks any credential-shaped substring in a surfaced resolver error BEFORE
printing (FR-016). Note the split in the existing code: `src/seshat/rules/git_meta.py`
DETECTS secret shapes (the C2 connection-string patterns, returning Findings/bool),
while the actual text-MASKING capability lives in `src/seshat/pr_summary.py` (`mask`,
used by the friendly-PR-summary step). The implementation should reuse that masking
posture -- extracting a shared helper that consumes the C2 shapes and returns
redacted text, rather than re-implementing either half. This mirrors the memory rule
that every new surface with a failure path reuses the established redaction rather
than inventing a parallel one.

## Complexity Tracking

> No Constitution Check violation -- this table is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| (none)    | --         | --                                   |
