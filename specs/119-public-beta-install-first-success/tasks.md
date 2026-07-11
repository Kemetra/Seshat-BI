# Tasks: Seshat BI Public Beta — Install to First Success

**Feature dir**: `specs/119-public-beta-install-first-success/`
**Inputs**: spec.md, plan.md, research.md, data-model.md, contracts/first-success-cli.md, quickstart.md

> **✅ RATIFIED by Ahmed Shaaban (owner), 2026-07-11 — build is cleared.** The Principle-V
> ratify seam is passed; these tasks may now be implemented. Implementation is still a
> deliberately-kicked-off piece of work (not auto-started on ratification). **MVP = User
> Story 1** (first success on the distribution name `seshat-bi`); the `retail`→`seshat`
> module rename is **Phase 5, post-MVP**. Publication (PyPI / public marketplace) remains
> a SEPARATE unmade owner act — ratifying the spec did not authorize publishing.
>
> **Independence to preserve**: **User Story 1 (first success) is shippable on its own and
> does NOT depend on the `retail`→`seshat` import-module rename.** The distribution rename
> (FR-009) unblocks `pipx install seshat-bi`; the module rename (FR-009a) is an internal
> follow-on. Do not blur them: US1 can land with the distribution name alone.

**Tests**: the feature spec defines an acceptance oracle (`contracts/first-success-cli.md`)
and release-quality criteria (FR-021), so verification tasks ARE requested — they reuse
spec 108's install smoke harness rather than a new framework.

---

## Phase 1: Setup (shared prerequisites)

- [ ] T001 Confirm spec 108's release readiness is present and reusable (read `docs/operations/versioning-policy.md`, `CHANGELOG.md`, and the CI `smoke` job in `.github/workflows/ci.yml`); record the reuse points in a short note in `specs/119-public-beta-install-first-success/research.md` reuse ledger
- [ ] T002 [P] Inventory every `retail` reference that a rename touches: `grep -rn "import retail\|from retail\|python -m retail\|src/retail\|packages = \[\"src/retail\"\]" src tests docs integrations pyproject.toml` and save the list to `specs/119-public-beta-install-first-success/rename-inventory.md` (evidence for FR-009a scope)
- [ ] T003 [P] Confirm the six user-facing/contributor extras in `pyproject.toml` (`db`,`mssql`,`mysql`,`snowflake`,`files`; `dev`,`livetest`) are unchanged and note which are user-path vs contributor-only (FR-011/FR-012)

---

## Phase 2: Foundational (distribution identity — blocks first success)

**Purpose**: the minimum packaging identity that makes `pipx install seshat-bi` real. This
is FR-009 (distribution name) ONLY — deliberately NOT the module rename (that is Phase 5).

- [ ] T004 In `pyproject.toml`, set `[project].name = "seshat-bi"` (distribution name); leave the import package and `[project.scripts]` targeting `retail` for now so this step is independently shippable (FR-009)
- [ ] T005 Verify both console scripts remain declared (`seshat` and `retail`) and both dispatch the same entry point (FR-002)
- [ ] T006 Record the version bump for the distribution rename per spec 108's versioning policy and add a `CHANGELOG.md` entry (FR-008)

**Checkpoint**: `pyproject.toml` builds a `seshat-bi`-named artifact; import module still
`retail`; both scripts present. US1 can now proceed on the distribution name alone.

---

## Phase 3: User Story 1 — First success without a database (P1) 🎯 MVP

**Goal**: a new user installs, confirms the command, creates a workspace, and verifies with
no database and no Power BI Desktop, in <10 min on Windows.
**Independent test**: run contract rows C1–C6 in a clean environment; all exit as specified,
`next` returns a truthful Source Ready action with no fabricated readiness / no score.

### Verification (reuse spec 108 smoke harness)

- [ ] T007 [P] [US1] Extend the spec-108 install smoke test to build wheel+sdist, install into a clean throwaway env, and assert contract rows C1 (`seshat --help`), C4 (`status --format json` → `{"tables": []}`), C5 (`next --format agent` truthful Source Ready, no score), C6 (`check` exit 0) from `contracts/first-success-cli.md` — Windows leg is the gate (SC-002)
- [ ] T008 [P] [US1] Add a truthfulness assertion to the smoke test: no numeric score and no fabricated pass appear in C4/C5 output (FR-004, SC-004)
- [ ] T031 [P] [US1] Add a **clean-install dependency assertion** to the smoke test: after `pipx install seshat-bi` (NO extras) in a throwaway env, assert that `dev` (pytest/ruff), `livetest` (testcontainers), and every DB/file driver (psycopg2, pyodbc, mysql-connector, snowflake-connector, openpyxl) are **absent** from the installed environment (FR-012, **SC-003**). NOTE: distinct from the existing module-scope import-guard tests — those prove the *code* doesn't import drivers; this proves the *install* doesn't *pull* them.
- [ ] T009 [P] [US1] Add best-effort, **non-blocking** macOS/Linux legs of the same smoke test to CI (FR-007, R7)

### Documentation (the artifact SC-001/SC-002 measure)

- [ ] T010 [US1] Land the first-success walkthrough from `quickstart.md` into a new top-of-`README.md` quickstart section: one-sentence value, 3-step quickstart, Windows / macOS-Linux separated, expected output, "Try without a database" (FR-019, FR-020, SC-005) — every `pipx install seshat-bi` line carries the "target — not yet published" caveat (SC-008)
- [ ] T011 [US1] Reconcile `docs/install/user-install.md` with the README quickstart (truthful status label; no duplicate/contradictory install system) (FR-020)
- [ ] T012 [P] [US1] Add the top-N first-run troubleshooting table (PATH/`pipx ensurepath`, Python missing, git-not-init, plugin-not-published) to the README section (FR-006, FR-019)

### Actionable-error behavior (FR-006)

- [ ] T013 [US1] Verify/spec the actionable-error contract rows E1–E4 (Python missing, `seshat` off PATH, Git missing, install broken) resolve to a named-prerequisite message, not a silent/misleading result — document the checks in the quickstart where the tool cannot itself emit them (E2)

**Checkpoint**: US1 is independently demonstrable end-to-end on the distribution name; the
module rename has NOT happened yet.

---

## Phase 4: User Story 2 — Start the Claude Code workflow (P2)

**Goal**: install/activate the public plugin, open Claude Code, issue one instruction,
receive the truthful next allowed action.
**Independent test**: with US1 satisfied, run plugin-contract rows P1–P3; the Seshat skill +
`/seshat-*` commands load; the returned action is the truthful Source Ready onboarding action.

- [ ] T014 [US2] Resolve the R4 manifest-discovery option (root manifest / remote-URL source / generated mirror) and record the decision + rationale in `research.md` R4; this decides whether a separate mirror repo is created (FR-016)
- [ ] T015 [US2] Update `integrations/claude-code/README.md` to document the **verified public** flow — `/plugin marketplace add <owner>/<repo>` → `/plugin install seshat-bi@seshat-bi-marketplace` → `/plugin marketplace update` — and explicitly mark the local `marketplace add ./…` form as dev-only, never the public command (FR-015, SC-008)
- [ ] T016 [P] [US2] Ensure the plugin exposes the existing Seshat skill + `/seshat-*` commands unchanged (FR-017); no new CLI verb added (FR-014)
- [ ] T017 [P] [US2] Set/verify the truthful status label (draft/beta/released) in `plugin.json` and `marketplace.json` metadata; no wording implies public availability before publication (FR-018, SC-008)
- [ ] T018 [US2] Author `docs/install/agent-install.md` (new M2 deliverable): the agent/plugin reference, separated from the user quickstart (FR-020)
- [ ] T019 [US2] If a mirror repo is chosen (T014), specify the **one-way** release process from `Seshat_BI` and that all plugin references — including the `python -m retail.cli` fallback — are regenerated from source, never hand-forked (FR-016)

**Checkpoint**: a user can go from first success to a running Seshat-guided Claude Code
workflow via the verified public plugin story.

---

## Phase 5: `retail` → `seshat` import-module rename (FR-009a) — internal follow-on

**Goal**: carry the clean brand into the import module WITHOUT breaking anything.
**Not on the US1 critical path** — sequenced after the shippable first-success slice.

- [ ] T020 Rename the package directory `src/retail/` → `src/seshat/`; update `[tool.hatch.build.targets.wheel] packages = ["src/seshat"]` and point both `[project.scripts]` at `seshat.cli:main` (FR-009a)
- [ ] T021 Update every `import retail` / `from retail…` / `python -m retail.cli` reference found in T002's inventory across `src`, `tests`, and `docs` to `seshat` (FR-009a)
- [ ] T022 Add a thin `retail` **compatibility shim** package (`src/retail/`) that re-exports `seshat` so `import retail` and `python -m retail.cli` still resolve for one deprecation cycle (FR-010)
- [ ] T023 [P] Add a backward-compat test asserting contract rows B1 (`python -m retail.cli check` resolves via shim, identical behavior) and B2 (`import retail` resolves) (FR-010)
- [ ] T024 Confirm the plugin's `python -m retail.cli` fallback still resolves post-rename (shim-safe); regenerate plugin references from source if a mirror exists (FR-010, FR-016)
- [ ] T025 Run the full existing unit suite (`pytest -m unit`) and `retail check`/`seshat check` to prove no regression from the rename (SC-006)

**Checkpoint**: import module is `seshat`; `retail` shim keeps old invocations working; suite green.

---

## Phase 6: Release quality & rollback (cross-cutting, FR-021/FR-022)

- [ ] T026 [P] Assemble the release acceptance checklist covering FR-021: build wheel+sdist; clean-env install; `seshat --help`; fresh project; `status`/`next`/`check`; plugin package + install-flow validation; Windows smoke; no secrets/machine-paths in artifacts (SC-007); upgrade + uninstall documented (`pipx upgrade`/`uninstall`)
- [ ] T027 [P] Document the rollback procedure (FR-022): (a) package yank + revert to prior good; (b) plugin mirror revert to prior tag + status-label downgrade to draft/beta; truthful-status discipline preserved throughout
- [ ] T028 [P] Author `docs/install/developer-install.md` (new M2 deliverable): editable/`.[dev]` install, cleanly separated from the user path (FR-020)
- [ ] T029 Final governance pass: run `seshat check` (and `kit-lint`) over the changed tree; confirm no secret/machine-path committed and the generated workspace stays governance-clean (SC-007, FR-005)
- [ ] T030 Flag (do NOT perform) the constitution Scope-Boundaries "NO CLI installer" amendment as a human-ratification follow-up; the agent does not edit `constitution.md`

---

## Dependencies & completion order

```
Phase 1 (Setup: T001–T003)
        ↓
Phase 2 (Distribution identity: T004–T006)   ← FR-009 only, NOT the module rename
        ↓
Phase 3 (US1 first success: T007–T013) 🎯 MVP  ← independently shippable here
        ↓
Phase 4 (US2 Claude Code workflow: T014–T019)
        ↓
Phase 5 (US3-adjacent module rename FR-009a: T020–T025)  ← internal, after MVP
        ↓
Phase 6 (Release quality & rollback: T026–T030)
```

- **US1 (P1)** depends only on Phases 1–2. It does **not** depend on Phase 5.
- **US2 (P2)** depends on US1 (a working CLI + workspace) plus the R4 decision (T014).
- **Phase 5 (module rename)** is deliberately after the MVP — first success ships on the
  `seshat` console script regardless of the import-module name.
- Optional **database connect (P3 / US3)** is documented in T010/T011 (the "Connect your
  database" section) and needs no new task beyond documenting the existing extras.

## Parallel opportunities

- Phase 1: T002, T003 in parallel.
- Phase 3: T007, T008, T009, T031 (smoke legs) and T012 in parallel; T010→T011 sequential (same README/doc set).
- Phase 4: T016, T017 in parallel after T015.
- Phase 6: T026, T027, T028 in parallel.

## Suggested MVP scope

**User Story 1 only** (Phases 1–3): a new user reaches first success without a database via
`pipx install seshat-bi`, on the distribution name alone — no module rename, no plugin work
required. This is the smallest independently valuable, independently testable increment.

## Task summary

- **Total**: 31 tasks (T001–T031)
- **US1 (P1)**: 8 (T007–T013, T031) + 3 foundational (T004–T006)
- **US2 (P2)**: 6 (T014–T019)
- **Module rename (FR-009a)**: 6 (T020–T025)
- **Release quality/rollback + setup**: 8 (T001–T003, T026–T030)
- **Everything gated behind owner ratification of the spec.**
