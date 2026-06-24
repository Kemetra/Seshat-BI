# Milestone M2 Report — Git-Metadata Rules

**Date:** 2026-06-24
**Branch:** spec/pbi-governance-layer

---

## Summary

All 8 M2 rules implemented, tested, and committed. Full unit suite: **66 passed, 0 failed**.

---

## Files Created / Modified

| File | Action |
|---|---|
| `src/retail/gitutil.py` | Created — git subprocess helpers |
| `src/retail/rules/git_meta.py` | Replaced stub — all 8 rules |
| `tests/unit/_gitfix.py` | Created — shared git repo fixture helpers |
| `tests/unit/test_git_meta.py` | Created — 29 unit tests |

---

## Per-Rule Status

### M2.1 — gitutil helpers
- `git_output`, `git_check_ignore`, `git_log_subjects` implemented in `src/retail/gitutil.py`.
- Fixture helpers `make_git_repo`, `commit_all`, `context_for` in `tests/unit/_gitfix.py`.
- Test: `test_git_check_ignore_respects_gitignore` — PASSED.

### M2.2 — G5: Windows MAX_PATH discipline
- Rule: `rule_g5_path_length` — flags `tracked_files` paths > 200 chars.
- Tests: `test_g5_flags_long_path`, `test_g5_passes_short_paths` — PASSED.

### M2.3 — P1: Approach-A layout
- Rule: `rule_p1_layout` — checks required dirs, PBIP under `powerbi/`, SQL under `warehouse/`.
- Tests: `test_p1_accepts_good_layout`, `test_p1_flags_misplaced_sql_and_pbip`, `test_p1_flags_missing_required_dir` — PASSED.

### M2.4 — G1: .gitignore correctness
- Rule: `rule_g1_gitignore_correctness` — must-contain subset check + `git check-ignore` on definition probe paths.
- Tests: `test_g1_accepts_correct_gitignore`, `test_g1_flags_missing_required_entry`, `test_g1_flags_ignored_definition_path` — PASSED.

### M2.5 — G2: definition artifacts committed
- Rule: `rule_g2_definition_committed` — INFO when no PBIP present; ERROR for tracked `.pbi/cache.abf`.
- Tests: `test_g2_emits_info_when_no_pbip`, `test_g2_flags_tracked_cache_abf` — PASSED.

### M2.6 — P2: commit-message convention
- Rule: `rule_p2_commit_subjects` — three modes: commit_message, commit_range, fallback HEAD~20.
- Tests: `test_p2_flags_bad_subject`, `test_p2_validates_single_commit_message`, `test_p2_exempts_merge_commits` — PASSED.

### M2.7 — C2: no committed secrets
- Rule: `rule_c2_no_committed_secrets` — .env gitignored/untracked, .env.example keys, content scan.
- Tests (6): `test_c2_clean_repo_passes`, `test_c2_flags_real_endpoint_in_scanned_file`, `test_c2_ignores_angle_bracket_placeholder_in_scanned_file`, `test_c2_skips_docs_and_example_files`, `test_c2_flags_tracked_env`, `test_c2_flags_env_example_with_filled_secret` — ALL PASSED.
- Key behavior: angle-bracket placeholders `<your-db-host>.db.ondigitalocean.com` do NOT fire; `docs/` and `*.example` files excluded from content scan.

### M2.G3 — G3: UTF-8 without BOM
- Rule: `g3_no_bom` — reads first 3 bytes of `*.tmdl/*.pbir/*.json/*.pbism`; flags EF BB BF.
- Helper: `_read_leading_bytes(path, count=3)` — binary read, never decodes.
- Tests (5): `test_read_leading_bytes_returns_first_three_bytes`, `test_read_leading_bytes_short_file_returns_fewer`, `test_g3_flags_tmdl_with_bom`, `test_g3_passes_tmdl_without_bom`, `test_g3_ignores_non_target_extension_with_bom` — PASSED.

### M2.G4 — G4: .gitattributes EOL policy
- Rule: `check_gitattributes_eol` — subset check, exact first-token match, 10 required glob/attribute pairs.
- Tests (4): `test_g4_passes_when_all_required_mappings_present`, `test_g4_flags_missing_tmdl_crlf`, `test_g4_flags_contradicting_token_with_line_locator`, `test_g4_flags_all_when_file_absent` — PASSED.
- Note: Brief states 11 findings when file absent but lists 10 required globs. Implementation has 10 `_G4_REQUIRED` entries; test asserts 10 — consistent.

---

## Full pytest Output (unit suite)

```
66 passed in 4.51s

Name                           Stmts   Miss  Cover
--------------------------------------------------
src\retail\rules\git_meta.py     160      7    96%
src\retail\gitutil.py             18      2    89%
(total)                          288     10    97%
```

---

## ruff + black Output

```
ruff check src tests         -> All checks passed!
black --check src tests      -> 21 files would be left unchanged.
                               (Warning: Python 3.13 parsing Python 3.14 target — benign)
```

---

## `retail check --repo .` Output on This Repo

```
[error] P1 PBIP artifact must live under powerbi/ (tests/fixtures/golden_pbip/RetailGold.Report/definition.pbir)
[error] P1 PBIP artifact must live under powerbi/ (tests/fixtures/golden_pbip/RetailGold.SemanticModel/definition/model.tmdl)
[error] P1 PBIP artifact must live under powerbi/ (tests/fixtures/golden_pbip/RetailGold.SemanticModel/definition/relationships.tmdl)
[error] P1 PBIP artifact must live under powerbi/ (tests/fixtures/golden_pbip/RetailGold.pbip)
[error] P2 commit subject must match '<type>: <desc>' (feat|fix|refactor|docs|chore) (test: add hand-authored golden PBIP fixture and TMDL parser smoke test)
```

**Expected / legitimate findings:** The M0 golden fixture at `tests/fixtures/golden_pbip/` is intentionally placed outside `powerbi/` (it is a test fixture, not a live model). The P2 finding is a pre-M2 commit on the branch that used `test:` as a type (not in the allowed set). These will be reconciled in M8 per the brief.

---

## Commit SHAs

| SHA | Message |
|---|---|
| `f93332e` | feat: add git subprocess helper for git-metadata rules |
| `1999e54` | feat: add G5 path-length rule, P1 Approach-A layout rule |

(All 8 rules are in `1999e54`; gitutil/fixtures in `f93332e`.)

---

## Registry Verification

```python
>>> import retail.rules; from retail.registry import all_rules
>>> [r.id for r in all_rules()]
['G5', 'P1', 'G1', 'G2', 'P2', 'C2', 'G3', 'G4']
```

All 8 git-meta rule IDs present in `all_rules()`.

---

## Concerns / Notes

1. **G4 required-count discrepancy:** The brief prose says 11 findings for absent `.gitattributes`; the implementation code has 10 `_G4_REQUIRED` entries. Test asserts 10 (consistent with implementation). The brief's table has 10 rows — the "11" in the prose appears to be a typo.

2. **Black Python 3.14 warning:** `black --check` emits a warning about Python 3.13 vs. 3.14 target version. All files pass; this is a version-mismatch warning, not a failure.

3. **P2 fallback range:** `DEFAULT_BASE_REF = "HEAD~20"` — on a repo with fewer than 20 commits, git returns `fatal: bad revision 'HEAD~20..HEAD'` silently via the `git_log_subjects` function (git returns an empty list). This is safe — no crash — but the local fallback will silently no-op on shallow repos. Acceptable per spec. (A `# TODO` documenting this was added at the constant in the post-review fix round below.)

---

## POST-REVIEW FIX ROUND (2026-06-24)

Review verdict: **Spec PASS / Quality Approved.** Three approved fixes applied.

### Fixes Applied

| # | Fix | Covering test(s) | Result |
|---|---|---|---|
| 1 | `rule_p1_layout` now `continue`s on `tests/`-prefixed paths before the PBIP and `.sql` checks; production `powerbi/`/`warehouse/` checks still apply to all non-`tests/` paths. | `test_p1_exempts_pbip_under_tests`, `test_p1_still_flags_pbip_outside_powerbi_and_tests`, `test_p1_exempts_sql_under_tests`, `test_p1_still_flags_sql_outside_warehouse_and_tests` (4 new) | PASS — fixture P1 findings gone |
| 2 | Renamed `g3_no_bom` → `rule_g3_no_bom` (id "G3" and title unchanged); updated import + 3 call sites in test file. | Existing G3 tests (`test_g3_*`) updated to new name | PASS |
| 3 | Added `# TODO` at `DEFAULT_BASE_REF = "HEAD~20"` documenting silent no-op on repos with <20 commits. | (comment-only) | N/A |

### Commands + Output

```
$ python -m pytest -m unit -q
......................................................................   [100%]
70 passed in 4.95s          (was 66; +4 new P1 tests)
src\retail\rules\git_meta.py     162      7    96%
(total)                          290     10    97%

$ python -m ruff check src tests
All checks passed!

$ python -m black --check src tests
All done! 21 files would be left unchanged.
(benign Python 3.13-vs-3.14 target warning only)
```

### Post-Fix `retail check --repo .` Output (COMPLETE)

```
[error] P2 commit subject must match '<type>: <desc>' (feat|fix|refactor|docs|chore) (test: add hand-authored golden PBIP fixture and TMDL parser smoke test)
[error] C2 possible committed connection string / secret (tests/unit/test_git_meta.py:343)
[error] C2 possible committed connection string / secret (tests/unit/test_git_meta.py:370)
[error] C2 possible committed connection string / secret (tests/unit/test_git_meta.py:374)
```

- **The 4× P1 findings on `tests/fixtures/golden_pbip/` are GONE** — fix #1 confirmed.
- **P2** still reports the historical `test:` commit — separate branch-hygiene item, left per instructions.
- **3× C2** findings on `tests/unit/test_git_meta.py` are NEW IN THIS REPORT but PRE-EXISTING in behavior. Verified via `git stash` against the committed `c39a9bf` state: the same three hits were present (at lines 307/334/338, shifted to 343/370/374 by the +4 P1 tests). They were absent from the *original* report's retail-check section only because that capture was taken **pre-commit, while `test_git_meta.py` was still untracked** (`git ls-files` did not yet include it, so C2 did not scan it). The two report sections are reconciled by this timing, not contradictory.
- C2 is firing **correctly**: the test file legitimately contains realistic endpoint literals (`db-prod-01.db.ondigitalocean.com`, `postgresql://…@…`) that are verbatim from the brief and load-bearing for `test_c2_flags_real_endpoint_in_scanned_file`. They must NOT be edited (would break the test) and C2 behavior must NOT change (out of scope). Recorded, not fixed — per the original task's "record findings, do not fix" guidance.

### New Concern (M8 reconciliation, not implemented here)

4. **C2 likely warrants a `tests/` exemption symmetric to the P1 one added in fix #1.** C2's content scan currently flags its own tracked test fixtures that contain intentional endpoint literals. The clean long-term fix is to extend C2's scan-exclusion (currently `docs/` + `*.example`) to also skip `tests/`. Out of scope this round (C2 behavior frozen); flagged for M8. **[RESOLVED in the C2 fix round below.]**

---

## POST-REVIEW FIX ROUND 2 — C2 content-scan `tests/` + `.superpowers/` exemption (2026-06-24)

Applies the symmetric exemption flagged as concern #4 above, approved for this round.

### Fix Applied

Extended **only** the C2 CONTENT/regex scan's exclusion predicate. The `_scan_excluded(path)` helper (used solely by `_scan_contents`, the postgres-URI / `*.db.ondigitalocean.com` regex scan over tracked files) now skips paths under `tests/`, `.superpowers/`, and `docs/`, or ending in `.example`. Consolidated into `_C2_SCAN_EXCLUDED_PREFIXES = ("docs/", "tests/", ".superpowers/")`.

**Preserved unchanged** (verified — `_scan_excluded` is not referenced by either):
- `_check_env_file` — `.env` gitignored-AND-untracked assertion: unchanged.
- `_check_env_example` — six `ANALYTICS_DB_*` keys present + HOST/NAME/USER/PASSWORD empty: unchanged.

Rationale: `tests/` holds fixtures that intentionally contain secret-LOOKING literals to exercise the scanner; `.superpowers/` holds SDD scratch/reports quoting those fixtures. Neither is tracked source that could leak a real secret.

### Covering Tests + Results

| Test | Purpose | Result |
|---|---|---|
| `test_c2_skips_tests_path_fixtures` (NEW) | A `tests/`-path file with a real endpoint + postgres URI is NOT flagged | PASS |
| `test_c2_flags_real_endpoint_in_scanned_file` (kept) | Positive case still fires — uses repo-root `config.txt` (not under any exempt dir) | PASS |
| `test_c2_clean_repo_passes`, `test_c2_ignores_angle_bracket_placeholder_in_scanned_file`, `test_c2_skips_docs_and_example_files`, `test_c2_flags_tracked_env`, `test_c2_flags_env_example_with_filled_secret` | Other C2 sub-checks unchanged | PASS |

### Commands + Output

```
$ python -m pytest -m unit -q
.......................................................................  [100%]
71 passed in 5.34s          (was 70; +1 new C2 test)
src\retail\rules\git_meta.py     163      7    96%
(total)                          291     10    97%

$ python -m ruff check src tests
All checks passed!

$ python -m black --check src tests
All done! 21 files would be left unchanged.   (benign 3.13-vs-3.14 target warning only)
```

### Final `retail check --repo .` Output

```
[error] P2 commit subject must match '<type>: <desc>' (feat|fix|refactor|docs|chore) (test: add hand-authored golden PBIP fixture and TMDL parser smoke test)
```

- **The 3× C2 findings on `tests/unit/test_git_meta.py` are GONE** — C2 fix confirmed.
- **Exactly one finding remains:** the P2 historical `test:` commit — the pre-baseline branch-hygiene item, decided at final review to leave. (Exit code 1 reflects this single ERROR; expected.)

No new concerns. Concern #4 above is now resolved.
