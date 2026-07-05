# Tasks: PBIR-authoring adapter -- increment A (theme application)

**Plan**: `specs/106-pbir-authoring-adapter/plan.md` | **Spec**: `spec.md` | **ADR**: `docs/decisions/0015-...md` (RATIFIED)

Increment A only: apply a `retail theme-gen` theme to a PBIR report by writing a
BaseTheme resource + updating `report.json` `themeCollection` -- plus a read-only
core authoring-lint. NO per-visual edits (increment B), NO backgrounds (C).

TDD, bite-sized, frequent commits. `live-target-before-rule`: writer (T1) before
lint (T2).

---

### Task 1: The theme-application WRITER (`src/retail/pbir_theme_apply.py`)

**Files:** Create `src/retail/pbir_theme_apply.py`; Test `tests/unit/test_pbir_theme_apply.py`; fixture `tests/fixtures/pbir/theme_apply/` (a minimal report tree).

**Produces:** `apply_theme(theme_json: Path, report_dir: Path, force: bool=False) -> list[Path]`; `class PbirApplyError(Exception)`.

- [ ] T1.1 Write failing tests: applies theme (BaseTheme file written + report.json themeCollection.baseTheme.name updated + resourcePackages item present); idempotent (byte-identical re-run); refuses path traversal in theme_json/report_dir; refuses overwrite of an existing DIFFERENT base theme without force; invalid theme JSON -> PbirApplyError; report.json keeps its $schema; round-trip stable.
- [ ] T1.2 Run -> fail (module missing).
- [ ] T1.3 Implement the writer (stdlib json + pathlib; in-repo path guard; stage->validate->commit-or-rollback; stable key order).
- [ ] T1.4 Run -> pass.
- [ ] T1.5 Commit.

### Task 2: The core authoring-LINT (add to `src/retail/rules/pbir.py`)

**Files:** Modify `src/retail/rules/pbir.py` (new `@register("R2", ...)` sibling); Test `tests/unit/test_pbir_authoring_lint.py`; fixtures under `tests/fixtures/pbir/`.

**Produces:** rule `R2` -- for a committed `*.Report/`, ERROR if report.json is invalid JSON / lost its $schema / references a BaseTheme resource that does not exist at its declared relative path / contains a forbidden business-logic key. Clean report -> no finding. Read-only. Test fixtures exempted like R1.

- [ ] T2.1 Write failing tests (clean report passes; missing referenced BaseTheme file -> R2 error; forbidden key in report.json -> R2 error; invalid JSON -> R2 error; tests/ fixtures exempted).
- [ ] T2.2 Run -> fail.
- [ ] T2.3 Implement R2 in pbir.py + wire into EXPECTED_RULE_IDS + regen golden manifests (rules-manifest + severity-posture).
- [ ] T2.4 Run -> pass.
- [ ] T2.5 Commit.

### Task 3: The `retail pbir-apply-theme` CLI verb

**Files:** Modify `src/retail/cli.py` (subparser + dispatch); `pbir_theme_apply.py` (add `pbir_apply_main`); Test `tests/unit/test_pbir_theme_apply_cli.py`.

- [ ] T3.1 Add `pbir_apply_main(args) -> int` (exit 2 on PbirApplyError).
- [ ] T3.2 Write failing CLI test (generates a theme via theme-gen into a fixture, applies it, exit 0; bad path exit 2).
- [ ] T3.3 Wire subparser + dispatch.
- [ ] T3.4 Run -> pass.
- [ ] T3.5 Commit.

### Task 4: Adapter contract + skill + integration doc (the F024 artifacts)

**Files:** Create `.claude/skills/pbir-authoring-adapter/SKILL.md`, `templates/pbir-adapter-contract.md`, `docs/integrations/pbir-adapter.md`.

- [ ] T4.1 Author the three docs (boundary, allow-list, no-external-dep, evidence-not-approval, gate=ADR 0015). Generic; retail_store_sales cited only.
- [ ] T4.2 Commit.

### Task 5: Full gate + dogfood

- [ ] T5.1 `ruff format --check src tests` + `ruff check src tests` + `pytest -m unit` + `retail check` all green.
- [ ] T5.2 (Dogfood, NON-committed proof) apply the Slice-1 `executive-dark` theme to a COPY of the report in a tmp dir; confirm valid + R2 green. Do NOT commit a restyled live report here (that is a human design-review action).
- [ ] T5.3 Final commit if anything pending; open PR.
