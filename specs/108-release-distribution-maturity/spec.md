# Feature Specification: Release & distribution maturity (roadmap M11)

**Feature Branch**: `108-release-distribution-maturity`

**Created**: 2026-07-07

**Status**: **DRAFT — SPEC ONLY, NOT BUILT.** Authored autonomously (2026-07-07 overnight
run) and HELD for owner review. Touches CI/packaging — per the overnight discipline, CI
changes wait for human eyes. Not gated on the A-vs-B fork. See
`docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md` M11.

**Input**: Roadmap M11 — "Distribution and Release Maturity": the changelog, versioning
policy, and install smoke test that make Seshat BI a distributable product (prerequisite
for the M2 published-install experience actually working).

---

## Context and boundary

M1 (the `seshat` alias) and M2 (the user-install *docs*) shipped, but the package is not
actually published or release-managed. M11 adds the release discipline: a versioning
policy, a changelog, and an install smoke test — so that when the package IS published,
`pipx install seshat-bi` reliably yields a working `seshat` command.

## User Scenarios & Testing

### User Story 1 — a reproducible, versioned release (P1)
A maintainer cuts a release: the version is bumped per a documented policy, the changelog
records what changed, and a smoke test proves a fresh install exposes a working `seshat`
command (`seshat --help` exits 0, `seshat check` runs) in a clean environment.

## Requirements (FR)

- **FR-001** A documented **versioning policy** (`docs/operations/versioning-policy.md`):
  scheme (semver?), what bumps major/minor/patch for a governance kit, where the version
  lives (`pyproject.toml`), and who bumps it.
- **FR-002** A **changelog** (`CHANGELOG.md`) with a documented update discipline
  (Keep-a-Changelog-style or the repo's own convention).
- **FR-003** An **install smoke test**: builds the package, installs it into a clean
  throwaway environment, and asserts the `seshat`/`retail` console scripts exist and
  `seshat check` runs — runnable in CI and locally.
- **FR-004** No secret, credential, or registry token is committed; publishing credentials
  (if a publish step is added) come from CI secrets, never tracked files.
- **FR-005** The smoke test and any CI addition respect the repo's existing gate: they run
  `retail check` + `pytest -m unit` and do not weaken either.

## Out of scope
- Actually publishing to PyPI (a separate owner decision — needs an org/account + a name
  reservation; this spec builds the *readiness*, not the publish act).
- Automated release cutting (tag→publish automation) — a later increment once the manual
  policy is proven.

## Held-decision notes
Spec only. CI/workflow changes (`.github/workflows/*`) and a publish story are exactly the
kind of change that deserves human review before landing — no `tasks.md`, no CI edits until
the owner approves this spec.
