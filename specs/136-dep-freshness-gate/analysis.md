# Cross-Artifact Analysis: Feature 136 (Dependency Freshness and Co-Resolution)

**Scope**: A non-destructive consistency read across `spec.md`, `plan.md`, and
`tasks.md` for feature 136, plus a check against the repository's ground truth
(constitution, P2 rule, dependabot.yml, pyproject files, existing CI). This is a
read-only analysis; it changes no other artifact. Findings are recorded honestly,
including against the author's own work.

**Adversarial plan-review is a SEPARATE reviewer's job and is deliberately not
performed here** (no `plan-review.md`).

## Method

- Requirement coverage: every FR traced to at least one task and to a user story.
- User-story <-> task alignment: every task carries a story or a shared/polish
  phase; every acceptance scenario has a covering task.
- Ground-truth checks: P2 accepts a `build:` scope-free subject (verified: `build`
  is in `_P2_TYPES`); the orchestration project is currently unwatched by Dependabot
  (verified against the committed `.github/dependabot.yml`); the offline static core
  is stdlib-only and network-free (verified against Principle VIII and `ci.yml`).
- Constitution alignment: Principles V and VIII (load-bearing) checked against the
  spec's constraints and the plan's Constitution Check.
- Hard-rule checks: ASCII-only, no BOM, no committed secret shapes (verified by a
  byte scan and a C2-shape grep over the three artifacts -- both clean).

## Requirement -> task coverage matrix

| FR | Covered by | Story |
|----|-----------|-------|
| FR-001 (manifest is DATA) | T001, T003, T004 | US1 |
| FR-002 (ephemeral resolve, no install into CI interp) | T008, T011, T014 | US1 |
| FR-003 (fail-closed, surface resolver text) | T007, T011, T013 | US1 |
| FR-004 (INFRA vs RESOLUTION distinguishable) | T009, T011, T013 | US1 |
| FR-005 (CONFIG distinguishable) | T003, T004 | US1 |
| FR-006 (CI job, not offline check) | T013, T014 | US1 |
| FR-007 (latest stable excl. pre-release/yanked) | T015, T020 | US2 |
| FR-008 (propose, never change pin / open PR) | T019, T022 | US2 |
| FR-009 (proposal carries solve-proof) | T016, T021 | US2 |
| FR-010 (failed solve still renders) | T017, T021 | US2 |
| FR-011 (CI artifact; opt-in comment) | T022, T023 | US2 |
| FR-012 (no auto-apply/bump/merge) | T019, T022 | US2 |
| FR-013 (dependabot watches orchestration) | T025, T026 | US3 |
| FR-014 (scope-free P2-passing subjects) | T024, T025, T027 | US3 |
| FR-015 (generic; correct across spec 135) | T001, T004 | US1 |
| FR-016 (redaction reuses C2 posture) | T005, T006 | Foundational/US1 |
| FR-017 (offline-testable; PyPI stubbed) | T002, and every RED test task | all |

Every FR is covered by at least one task. Every task maps to a story or a
shared/polish phase. Every acceptance scenario in spec.md has a corresponding test
task (US1 scenarios -> T007-T010; US2 -> T015-T019; US3 -> T024-T025).

## Findings

### Consistency and coverage

- **C1 (INFO)**: Full FR coverage. All 17 FRs trace to concrete tasks; no orphan FR
  and no orphan task. The edge cases in spec.md (PyPI unreachable, failed solve,
  yanked, pre-release, plus the upper-bound and bad-manifest cases) each have a
  covering test (T009, T017, T015, T018, T003).

- **C2 (INFO)**: Story independence holds. US1 is a self-contained MVP (gate + CI
  job); US2 legitimately depends on US1's resolve function (documented in both
  plan.md and the tasks dependency section, not hidden); US3 is independent and
  correctly marked parallelizable.

### Ambiguities the author is flagging against their own work

- **A1 (LOW)**: The CI job's HOME workflow is left as "add to `ci.yml` OR a sibling
  `dep-integrity.yml`." This is a deliberate implementation-time choice (both satisfy
  FR-006), but it means tasks.md T014/T023 name two possible files. Not a defect --
  the constraint (a separate job, not the offline check) is unambiguous -- but the
  final file is decided at build time. Recorded so the reviewer knows it is
  intentional latitude, not an oversight.

- **A2 (LOW)**: `dependency-environments.yaml` is read by a `scripts/` module while
  the repo's runtime yaml reads live behind lazy imports in `src/seshat`. The script
  is NOT part of the stdlib-only static core (it is a CI script, like
  `scripts/release_candidate_audit.py`), so importing `yaml` there does not violate
  the B1/B3 stdlib-only import posture of `seshat check`. Confirmed against ci.yml:
  scripts run as their own steps, not inside `retail check`. No action; noted so the
  reviewer does not mistake it for a stdlib-core leak.

- **A3 (LOW)**: The plan says the github-actions dependabot block is "left as-is
  except for the same prefix if a `chore(deps):`-shaped subject would otherwise trip
  P2." This is a genuine conditional the author could not fully resolve without
  observing a produced github-actions subject. tasks.md scopes the guaranteed pip
  fix (T027) but does not force a github-actions change. This is honest
  under-commitment, not a gap in the stated pip scope; the reviewer should decide
  whether to require the github-actions block to carry the prefix too. (Out-of-scope
  note in spec.md limits non-pip ecosystem changes.)

- **A4 (LOW)**: FR-016's "reuse the existing C2 posture" is precise only once the
  split in the existing code is acknowledged: `src/seshat/rules/git_meta.py` DETECTS
  secret shapes (returns Findings/bool) but exposes no text-masking function; the
  actual masking lives in `src/seshat/pr_summary.py` (`mask`). plan.md section 6 now
  states this explicitly and directs the implementation to extract a shared helper
  (consume the C2 shapes, return redacted text) rather than assume a redactor already
  exists on `git_meta`. The FR is sound; the earlier phrasing that treated
  redaction-reuse as a single settled call was imprecise, and is corrected here
  against the author's own work.

### Constitution and hard-rule alignment

- **G1 (INFO)**: Principle V is honored end-to-end. Every governed-pin bump, the
  merge-blocking decision, the default-on comment decision, and any auto-merge are
  left UNANSWERED under spec.md "Open for human" -- none is silently answered. The
  four open items are verbatim, framed as questions, and attributed to the owner.

- **G2 (INFO)**: Principle VIII is honored. The network check is a separate CI job;
  the offline static core is untouched; the `--dry-run --report` resolve preserves
  the "CI installs only `.[dev]`" isolation proof (SC-002). The plan frames the
  network dependency as an honest, scoped deviation, not a principle violation, and
  the Constitution Check's Complexity Tracking table is correctly empty.

- **G3 (INFO)**: No new `seshat` CLI verb. The gate/reporter is a `scripts/` module;
  no `src/seshat/cli` dispatch entry is added. The ratified Option-B constraint is
  stated in spec.md and reasserted in plan.md and tasks.md.

- **G4 (INFO)**: Hard rules pass. All three artifacts are ASCII-only and UTF-8
  without BOM (byte-scanned). No committed secret shape appears (C2-shape grep
  clean). Package pins referenced in prose (e.g. `dbt-core==1.12.0`,
  `dagster-dbt==0.29.14`, `mcp>=1.28,<2`) are version specifiers, not secret shapes,
  and do not match any C2 pattern. Paths are short (`dependency-environments.yaml`,
  `scripts/dep_coresolve.py`) -- well under the 200-char MAX_PATH target.

### Verified ground-truth facts

- **V1**: P2 `_P2_TYPES` includes `build` (line 263 of `src/seshat/rules/git_meta.py`),
  and `SUBJECT_RE` rejects a parenthesized scope. A `build: bump X from A to B`
  subject therefore passes P2. FR-014's mechanism is sound.
- **V2**: The committed `.github/dependabot.yml` watches pip at `/` and
  github-actions at `/` ONLY -- the orchestration project directory is genuinely
  unwatched today, confirming the FR-013 coverage hole is real.
- **V3**: The dagster-smoke workflow already builds the orchestration project in its
  OWN isolated venv (`orchestration/dagster`), so the co-resolution job's per-env
  ephemeral-venv approach is consistent with existing repo practice and does not
  duplicate or disturb it.
- **V4**: The incident is accurately described: root `dbt` extra pins
  `dbt-core==1.12.0` (pyproject.toml lines 75-78); orchestration pins
  `dagster-dbt==0.29.14` (orchestration/dagster/pyproject.toml line 26). The
  cross-product of the two is exactly the entity nothing resolved.

## Severity summary

| Severity | Count | Items |
|----------|-------|-------|
| CRITICAL | 0     | --    |
| HIGH     | 0     | --    |
| MEDIUM   | 0     | --    |
| LOW      | 4     | A1 (CI-job home file), A2 (script yaml vs stdlib core), A3 (github-actions prefix conditional), A4 (redaction detect-vs-mask split) |
| INFO     | 7     | C1, C2, G1-G4 alignment, V-series ground-truth confirmations |

## Top items for the reviewer

1. **A3 (LOW)** -- Decide whether the github-actions dependabot block must also carry
   the scope-free commit-message prefix, or whether the spec's "non-pip ecosystems out
   of scope" note governs. The author under-committed honestly rather than assume.
2. **A1 (LOW)** -- Confirm the CI-job home (extend `ci.yml` vs a new
   `dep-integrity.yml`); both satisfy FR-006. A sibling workflow keeps the network
   job visually separate from the offline gate, which some reviewers prefer.
3. **A2 (LOW)** -- Confirm the reviewer agrees a `scripts/` yaml read is outside the
   stdlib-only static-core import boundary (it is, per ci.yml step separation), so
   FR-006 is not weakened by the manifest format choice.

No CRITICAL/HIGH/MEDIUM findings. The three LOW items are intentional latitude or
open policy questions, each recorded rather than silently resolved.
