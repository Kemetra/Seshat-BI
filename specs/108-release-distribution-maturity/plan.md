# Implementation Plan: Release & distribution maturity (roadmap M11) — BUILT

**Branch**: `feat/108-release-distribution-maturity` | **Date**: 2026-07-07 | **Spec**: `spec.md`

**Status: BUILT.** Owner-directed build executed on this branch 2026-07-07; see
`tasks.md` for the task-by-task record and FR-to-evidence mapping. The approach below
was followed as originally planned, with the CI addition landing as a single new
`smoke` job (Approach step 4), not an edit to the existing `check` job.

## Summary

Add the release discipline (versioning policy + changelog + install smoke test) that makes
the M2 published-install experience reliable. Docs + one test + optionally one CI job — no
runtime code change.

## Approach (when approved)

1. **`docs/operations/versioning-policy.md`** — the version scheme, bump rules for a
   governance kit (e.g. a new `retail check` rule = minor; a rule-behavior change = major),
   and that the version lives in `pyproject.toml`.
2. **`CHANGELOG.md`** — seed it from the existing git/roadmap history (the shipped F-rows +
   rule waves are already well-documented in `roadmap.md`/`shipped-ideas.yaml`), then a
   short "how to update" note.
3. **Install smoke test** — `tests/` or a `scripts/` helper that: `python -m build` (or
   `pip wheel`), installs the artifact into a fresh venv/tmp prefix, asserts `seshat` and
   `retail` entry points resolve and `seshat check --help` exits 0. Marked so it can be a
   separate CI job (it needs a build step, unlike the unit suite).
4. **Optional CI job** — a `.github/workflows/` addition running the smoke test on tag/PR.
   HELD hardest: any workflow edit is owner-reviewed.
5. **Gate**: existing `retail check` + `pytest -m unit` + ruff stay green; the smoke test
   does not weaken them.

## Sequencing note
Independent of M3 and of the cli.py decomposition (docs + a build-time test, not the CLI
surface). Can land in any order once approved. Pairs naturally with an owner decision on
whether/where to actually publish (out of scope here).
