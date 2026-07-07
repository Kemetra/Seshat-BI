# Tasks: Release & distribution maturity (roadmap M11)

**Branch**: `feat/108-release-distribution-maturity` | **Spec**: `spec.md` | **Plan**: `plan.md`

All tasks below are complete. This file is the task-by-task record and the
FR-to-evidence mapping the spec's Status line references.

## Tasks

- [X] **T001** Write `docs/operations/versioning-policy.md` (FR-001): semver scheme,
  the kit-specific bump table (new rule = MINOR, rule-behavior change = MAJOR,
  docs/tests-only = PATCH), where the version lives (`pyproject.toml`), and that the
  owner bumps it (Principle V, never self-granted).
- [X] **T002** Write `CHANGELOG.md` at repo root (FR-002): Keep a Changelog format,
  seeded from `docs/roadmap/roadmap.md` + `docs/roadmap/shipped-ideas.yaml` (never
  invented), an honest note that the package has never been published/tagged, an
  `[Unreleased]` section for this roadmap arc's session work, and an update-discipline
  note.
- [X] **T003** Write `scripts/install_smoke_test.py` (FR-003): builds a wheel
  (`pip wheel . --no-deps`), installs it into a clean, throwaway `venv`, asserts both
  `retail` and `seshat` console scripts resolve, and runs `check --help` via both,
  asserting exit 0 each time. No `build` module dependency (pip alone is sufficient in
  this environment).
- [X] **T004** Run the smoke test locally end-to-end and confirm PASS (see Evidence
  below) — proves the script works outside CI, not just in theory.
- [X] **T005** Add a new, independent `smoke` job to `.github/workflows/ci.yml`
  (FR-003/FR-005): checkout + setup-python 3.13 + one run step invoking the script.
  No `fetch-depth: 0` (no git-metadata rule runs there). No `needs:` (parallel with
  `check`, not sequenced after it).
- [X] **T006** Diff-verify the existing `check` job is byte-identical before/after
  (FR-005) — confirmed: the diff is a pure append after the job's last existing line;
  zero lines inside `check:` changed or removed.
- [X] **T007** Validate `.github/workflows/ci.yml` YAML well-formedness with
  `python -c "import yaml; yaml.safe_load(open(...))"`.
- [X] **T008** Confirm no secret/credential/registry token was introduced anywhere in
  this change (FR-004) — the smoke job has no publish step and reads no CI secret.
- [X] **T009** Run the full existing gate (`pytest -m unit`, `retail check`,
  `retail semantic-check --repo .`, `retail kit-lint --repo .`, `ruff check`,
  `ruff format --check`) and confirm all green with the new files present.
- [X] **T010** Update `spec.md` Status → BUILT and resolve the "Held-decision notes"
  section to record the owner-directed authorization (this file's existence is part of
  that resolution).

## FR → evidence mapping

| FR | Requirement | Evidence |
|----|-------------|----------|
| FR-001 | Documented versioning policy | `docs/operations/versioning-policy.md` (T001) |
| FR-002 | Changelog with update discipline | `CHANGELOG.md` (T002), including its own "How to update this changelog" section |
| FR-003 | Install smoke test, runnable in CI and locally | `scripts/install_smoke_test.py` (T003); ran locally and PASSed (T004); wired into CI as the `smoke` job (T005) |
| FR-004 | No secret/credential/token committed; no publish step | Verified by inspection (T008) — the `smoke` job builds + installs + checks only; it never runs `pip publish`/`twine upload`/any registry command, and reads no `secrets.*` context |
| FR-005 | Smoke test / CI addition respects the existing gate (`retail check` + `pytest -m unit`) and does not weaken either | **Satisfied at the workflow level.** The existing `check` job — unedited, byte-identical (T006) — already runs `retail check` and `pytest -m unit` on every push/PR. The new `smoke` job is additive and independent; it does not remove, skip, or soften any step of `check`. Re-running `retail check`/`pytest` a second time inside `smoke` was deliberately NOT done — it would be redundant with the unedited `check` job and would work against the "keep the YAML diff small and auditable" constraint. |

## Local verification run (2026-07-07)

```
python scripts/install_smoke_test.py         -> PASS (wheel built, clean venv install,
                                                 both console scripts resolved,
                                                 `retail check --help` and
                                                 `seshat check --help` both exit 0)
python -m pytest -m unit -q                  -> 1422 passed, 4 skipped, 8 deselected
PYTHONPATH=src python -m retail.cli check    -> exit 0
PYTHONPATH=src python -m retail.cli semantic-check --repo .  -> exit 0 (no drift)
PYTHONPATH=src python -m retail.cli kit-lint --repo .        -> exit 0 (no projection drift)
ruff check src tests                         -> All checks passed!
ruff format --check src tests                -> 222 files already formatted
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"  -> OK, 2 jobs
```

## Out of scope (unchanged from spec.md)

No PyPI publish, no tag automation, no version bump performed by this change (the
version stays `0.1.0`; bumping it is a separate owner action per the new policy),
no `[project.scripts]` change.
