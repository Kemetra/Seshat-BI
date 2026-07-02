# Feature Specification: Kit Projection-Drift Linter (Compass-Driven Phase-2 backstage)

**Feature Branch**: `072-kit-drift-linter`

**Created**: 2026-07-02

**Status**: Ratified (Ahmed Shaaban, 2026-07-02)

> Ratified under owner-delegated authority: the owner was shown the DEC-2 cut (the
> source-vs-constitution check removed; MINOR-5 stays partially open) in the ratify
> question and directed "ask advisor and decide" (2026-07-02); the advisor reviewed and
> approved 072 as specified, EXPLICITLY accepting the source-vs-constitution CUT and that
> the fenced-body-vs-constitution assurance stays human-reviewed-at-ratify. Recorded per
> the delegated-authority pattern (cf. spec 062); reversible pre-merge. analyze: 0
> CRITICAL / 0 HIGH, 16/16 FR+SC mapped, no dangling refs. Build authorized (15 tasks).

**Input**: The Phase-2 backstage enforcement deferred by feature 070: a CI-runnable
linter that fails loud when a compass PROJECTION drifts from the canonical kit source.
From `docs/roadmap/distribution-ideas.md` (lines 46, 57, 239-250): "the drift linter
(B2) fails loud if any projection drifts from the source."

> **Provenance.** Phase-2 backstage of the Compass-Driven kit; the projection-drift
> enforcement gap is recorded in `specs/070-retail-init-bootstrap/plan.md` (the
> Phase-2 deferral, lines 122-123) and `plan-review.md` (MINOR-5). Spec'd directly via
> speckit (not `idea-to-spec`), continuing the 070/071 pattern. F024 class:
> **Maintenance Automation** (CI-only, emits derived evidence, creates no truth,
> self-approves nothing).

> **Scope cut (adversarial review, 2026-07-02).** An earlier draft also proposed a
> "source-vs-constitution correspondence" check. That was CUT: as designed (a
> hard_stop→anchor table guard-tied to the source, checked only against the source) it
> was a source-vs-source tautology that verified nothing about the constitution — and
> only 2 of the 4 current hard_stops even have a constitutional-document home
> (`no_dashboard_before_metric_contracts` lives in `roadmap.md`;
> `never_fabricate_a_confidence_score` is a global hard-rule). A real
> governance-verification check needs a HUMAN governance decision (what documents span
> "governance"; whether each hard_stop has a constitutional home) and is recorded as a
> deferred, human-shaped slice — not faked here. **072 delivers the projection-drift
> half only; the fenced-body-vs-constitution assurance stays human-reviewed-at-ratify
> (070's honest current state).**

## Overview

Feature 070 shipped the compass projection generator + two drift checks
(`check_yaml_drift`, `check_prose_drift`) as callables, but **nothing invokes them as
a gate** — they are library functions with no CI entry point, so the single-source
guarantee is aspirational: a maintainer can edit `kit-source.yaml` and forget to
re-project, and the stale `compass.yaml` / fenced regions merge silently.

This feature adds a **standalone `retail kit-lint` CI step** (NOT a `retail check`
core rule — see DEC-1) that runs two deterministic projection-drift checks and fails
loud (exit 1) on any drift:

- **YAML projection drift** — `.seshat/compass.yaml` byte-equals `project_yaml(source)`
  (wraps the existing `check_yaml_drift`).
- **Prose projection drift** — the `SESHAT-KIT` fenced body of each governed file
  (`AGENTS.md`, `CLAUDE.md`) equals `render_prose(source)` (wraps the existing
  `check_prose_drift` via `read_fence_body`).

It reads no constitution prose and emits no numeric score; the exit code is the
authority.

## Clarifications

### Session 2026-07-02

- Q: Is the drift linter a new `retail check` core rule, or a standalone step? -> A:
  **DEC-1: standalone `retail kit-lint` step** (like `retail semantic-check` /
  `retail value-check`). It parses YAML, which the stdlib-only `retail check` core must
  never do (repeats the MAJOR-4 boundary the 070 skeptic caught). It adds NO gate rule;
  the `retail check` rule count stays 47.
- Q: Why not also check the source against the constitution? -> A: **DEC-2: CUT** (see
  the scope-cut note above). As designed it was a source-vs-source tautology, and only
  2 of 4 current hard_stops have a constitutional-document home. A real
  governance-verification check needs a human governance decision and is deferred as a
  human-shaped slice, not faked. 072 reads NO constitution prose at all.
- Q: Does `kit-lint` REPAIR drift? -> A: NO. Read-only report + exit code. Repairing a
  projection is `retail init` re-running (re-projection). The linter reports and fails
  loud; it never rewrites.
- Q: What if `.seshat/` is absent (repo not yet bootstrapped)? -> A: `kit-lint` reports
  "not bootstrapped — run `retail init`" and exits 0 (nothing to lint yet), NOT a
  failure. Absence is the honest not-started state, not drift.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CI fails loud when a projection drifts from the source (Priority: P1)

A maintainer edits `.seshat/kit-source.yaml` (adds a verb) but forgets to re-run
`retail init`, so `compass.yaml` / the fenced regions go stale. CI catches it.

**Why this priority**: This is the linter's core purpose and the whole reason the doc
calls it "the enforcement arm for the compass itself". Without it, the single-source
guarantee is aspirational — projections silently rot. (Note: this machine-verifies the
fenced body against the SOURCE; it does NOT verify the source against the constitution
— that half was cut, see the scope-cut note. The fenced-body-vs-constitution assurance
remains human-reviewed-at-ratify.)

**Independent Test**: In a bootstrapped repo, mutate `compass.yaml` (or a fenced body),
run `retail kit-lint`, and confirm exit 1 with a report naming the drifted projection.
Re-run `retail init`, run `kit-lint`, confirm exit 0.

**Acceptance Scenarios**:

1. **Given** a bootstrapped repo whose `compass.yaml` no longer matches
   `project_yaml(source)`, **When** `retail kit-lint` runs, **Then** it exits 1 and the
   report names the YAML projection drift.
2. **Given** a bootstrapped repo whose `AGENTS.md` fenced body no longer matches
   `render_prose(source)`, **When** `retail kit-lint` runs, **Then** it exits 1 and the
   report names the prose projection drift for that file.
3. **Given** a bootstrapped repo with all projections in sync, **When** `retail
   kit-lint` runs, **Then** it exits 0.

---

### User Story 2 - Runs in CI as the enforcement arm (Priority: P2)

The linter is wired into CI (a step after `retail semantic-check`) so projection drift
can never merge, and is documented so a maintainer runs it locally before pushing.

**Why this priority**: A linter no pipeline invokes is dead code. Wiring it into CI is
what turns the checks into enforcement (the doc: "fails loud"). P2 because the checks
(US1) must exist and pass first; the wiring is the delivery mechanism.

**Independent Test**: The CI workflow has a `retail kit-lint` step; running the repo's
own committed substrate through it exits 0 (the dogfood proof).

**Acceptance Scenarios**:

1. **Given** the CI workflow, **When** it runs, **Then** a `retail kit-lint` step runs
   after `retail semantic-check` and a non-zero exit fails the build.
2. **Given** this repo's committed `.seshat/` + fenced regions, **When** `retail
   kit-lint` runs, **Then** it exits 0 (the substrate is self-consistent).

### Edge Cases

- **`.seshat/` absent**: report "not bootstrapped — run `retail init`", exit 0 (not a
  failure; absence is not drift).
- **A governed file lacks a `SESHAT-KIT` fence**: report it as prose drift for that file
  (the fence should exist post-bootstrap) OR, if `.seshat/` is absent, fold into the
  not-bootstrapped case. A malformed fence is reported, never rewritten.
- **Source unparseable / missing a required block**: catch the parse/shape error and
  report it as a named failing check (exit 1) — a broken source is drift the linter must
  surface with an actionable message, never a raw traceback.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The kit MUST expose a standalone `retail kit-lint` CLI step that runs the
  drift checks and exits non-zero on any drift, zero when clean.
- **FR-002**: `kit-lint` MUST check YAML projection drift (`compass.yaml` byte-equals
  `project_yaml(source)`), wrapping the existing `check_yaml_drift`.
- **FR-003**: `kit-lint` MUST check prose projection drift (each governed file's
  `SESHAT-KIT` fenced body equals `render_prose(source)`), wrapping the existing
  `check_prose_drift` + `read_fence_body`.
- **FR-004**: `kit-lint` MUST be read-only: it reports drift + exits, and NEVER rewrites
  a projection, the source, or a governed file.
- **FR-005**: `kit-lint` MUST NOT be a `retail check` core rule and MUST NOT add a gate
  rule; the `retail check` rule count stays unchanged (DEC-1). It MAY import `pyyaml`
  (like `semantic-check`); the `retail check` core stays stdlib-only.
- **FR-006**: When `.seshat/` is absent, `kit-lint` MUST report "not bootstrapped" and
  exit 0 (absence is not drift).
- **FR-007**: `kit-lint` MUST be wired into CI as a step after `retail semantic-check`,
  so projection drift fails the build.
- **FR-008**: `kit-lint`'s report MUST name each specific drift (which projection / which
  file), not just "drift found" — actionable, traceable output. A parse/shape error in
  the source MUST be caught and reported as a named failing check, never a raw traceback.
- **FR-009**: `kit-lint` MUST NOT emit a numeric health / confidence / drift score (hard
  rule #9); it emits explicit pass/fail per check + the exit code.
- **FR-010**: `kit-lint` MUST NOT read or interpret constitution prose (the
  source-vs-constitution check was cut — see the scope-cut note). It reads only the
  kit source + its projections.

### Key Entities

- **Canonical kit source** — `.seshat/kit-source.yaml` (EXISTING): the single source
  the linter validates projections against.
- **Projections** — `.seshat/compass.yaml` + the `SESHAT-KIT` fenced regions (EXISTING):
  checked byte-exact / render-compare against the source.

## Success Criteria *(mandatory)*

- **SC-001**: A drifted `compass.yaml` or fenced body causes `retail kit-lint` exit 1
  with a report naming the drift; a re-projected repo exits 0.
- **SC-002**: `retail check` rule count is unchanged (no new gate rule); `kit-lint` is a
  standalone step.
- **SC-003**: On an un-bootstrapped repo (no `.seshat/`), `kit-lint` exits 0 with a
  "not bootstrapped" note — never a false-positive failure.
- **SC-004**: This repo's own committed substrate passes `retail kit-lint` (exit 0) — the
  dogfood proof — and a CI step runs it after `semantic-check`.
- **SC-005**: `kit-lint` emits no numeric drift/confidence score — explicit pass/fail +
  exit code only.
- **SC-006**: `kit-lint` reads no constitution file (the source-vs-constitution check
  was cut); it consults only the kit source + its projections.

## Assumptions

- The 070 substrate (`compass_project`, `fence`, `.seshat/kit-source.yaml` + committed
  projections) is on `main` and is the linter's input.
- CI (`.github/workflows/ci.yml`) is where the step is wired, mirroring how
  `retail semantic-check` is a separate step from `retail check`.
- The source-vs-constitution verification is DEFERRED as a human-shaped governance slice
  (what documents span "governance"; whether each hard_stop has a constitutional home) —
  not attempted here.
- This feature advances NO readiness stage and takes NO roadmap F-row (kit maintenance
  automation), matching `scaffold.py` / `manifest.py` / the 070 substrate.
