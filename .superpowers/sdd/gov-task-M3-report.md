# Milestone M3 — Implementation Report

**Date:** 2026-06-24
**Branch:** spec/pbi-governance-layer
**Status:** COMPLETE — all 5 SQL rules implemented, 19 new tests green, 90 total unit tests passing, ruff + black clean, all_rules() = 13.

---

## Per-rule files and tests

### M3.1 — SQL Lexer (`src/retail/sql.py`)

**Files created:**
- `src/retail/sql.py` — `SqlToken`, `tokenize_sql`, `iter_sql_files`, `stale_schema_tokens`
- `tests/unit/test_sql_lexer.py` — 6 tests

**Commit:** `6db02dc` — `feat: add SQL lexer and schema-position matcher for retail check`

**Tests (6):** `test_tokenize_tracks_line_numbers`, `test_tokenize_strips_line_comment`, `test_tokenize_strips_string_literal_contents`, `test_stale_schema_passes_snake_case_column`, `test_stale_schema_flags_create_schema_raw`, `test_stale_schema_flags_qualifier_and_from`

---

### M3.2 — S1 + S2 (`src/retail/rules/sql.py`)

**Files created/modified:**
- `src/retail/rules/sql.py` — added S1 + S2 (replacing the 2-line stub)
- `tests/unit/test_sql.py` — 5 tests
- `tests/fixtures/sql/pass_s1_s2.sql`
- `tests/fixtures/sql/fail_s1_quoted_caps.sql`
- `tests/fixtures/sql/fail_s2_create_schema_raw.sql`

**Commit:** `453c606` — `feat: add S1 snake_case and S2 medallion-schema SQL rules`

**Tests (5):** `test_s1_passes_snake_case`, `test_s1_flags_quoted_caps`, `test_s2_passes_raw_amount_column`, `test_s2_flags_create_schema_raw`, `test_s2_exempts_warehouse_readme`

---

### M3.3 — S3 (`src/retail/rules/sql.py`)

**Files created/modified:**
- `src/retail/rules/sql.py` — appended S3
- `tests/unit/test_sql.py` — 2 additional tests
- `tests/fixtures/sql/pass_s3_vw.sql`
- `tests/fixtures/sql/fail_s3_no_prefix.sql`

**Commit:** `4a8dcf9` — `feat: add S3 vw_ view-prefix SQL rule`

**Tests (2):** `test_s3_passes_prefixed_views`, `test_s3_flags_unprefixed_view`

---

### M3.4 — S4a (`src/retail/rules/sql.py`)

**Files modified:**
- `src/retail/rules/sql.py` — appended S4a
- `tests/unit/test_sql.py` — 4 additional tests

**Commit:** `9440370` — `feat: add S4a migration filename and numbering SQL rule`

**Tests (4):** `test_s4a_passes_contiguous_unique`, `test_s4a_flags_bad_name`, `test_s4a_flags_gap`, `test_s4a_flags_duplicate`

---

### M3.5 — S4b (`src/retail/rules/sql.py`)

**Files created/modified:**
- `src/retail/rules/sql.py` — appended S4b
- `tests/unit/test_sql.py` — 2 additional tests + import consolidation + ruff/black fixes
- `tests/unit/test_sql_lexer.py` — removed unused `SqlToken` import
- `tests/fixtures/sql/pass_s4b_guarded.sql`
- `tests/fixtures/sql/fail_s4b_bare.sql`

**Commit:** `3db9c92` — `feat: add S4b migration guard-form SQL warning rule`

**Tests (2):** `test_s4b_passes_guarded_forms`, `test_s4b_warns_on_bare_create_and_alter`

---

## Full suite output

```
90 passed in 3.74s
```

Coverage:
```
src/retail/rules/sql.py    94%  (6 missed: lines 47, 73, 78, 155-157 — guarded branches not exercised by SQL rule tests)
src/retail/sql.py          94%  (4 missed: lines 41-44 — block-comment newline counting)
```

---

## ruff + black output

```
ruff check src tests   → All checks passed!
black --check src tests → 24 files would be left unchanged.
```

**Ruff fixes applied (not in brief verbatim code, necessary for compliance):**
1. `E501` Line too long in `rules/sql.py` line 110 — the verbatim message string was split across two lines using raw string concatenation.
2. `E402` Module-level imports not at top — the brief appended imports mid-file per TDD step; consolidated all `from retail.rules.sql import ...` into a single import block at the top of `test_sql.py`.
3. `F401` Unused `SqlToken` import in `test_sql_lexer.py` — removed (the verbatim brief imported it but no test used it directly).

---

## all_rules() id list (13 total)

```
['G5', 'P1', 'G1', 'G2', 'P2', 'C2', 'G3', 'G4', 'S1', 'S2', 'S3', 'S4a', 'S4b']
```

8 git-meta (G1, G2, G3, G4, G5, P1, P2, C2) + 5 SQL (S1, S2, S3, S4a, S4b) = 13.

---

## `retail check --repo .` output

```
[error] P2 commit subject must match '<type>: <desc>' (feat|fix|refactor|docs|chore) (test: add hand-authored golden PBIP fixture and TMDL parser smoke test)
```

Exit code: 1 (1 grandfathered P2 error — expected, pre-existing). No S-rule violations fired. The `warehouse/` directory contains only `.gitkeep`, so no real SQL files are scanned by any S-rule.

---

## Commit SHAs (M3 only)

| Commit     | Description                                          |
|------------|------------------------------------------------------|
| `6db02dc`  | feat: add SQL lexer and schema-position matcher      |
| `453c606`  | feat: add S1 snake_case and S2 medallion-schema SQL rules |
| `4a8dcf9`  | feat: add S3 vw_ view-prefix SQL rule                |
| `9440370`  | feat: add S4a migration filename and numbering SQL rule |
| `3db9c92`  | feat: add S4b migration guard-form SQL warning rule  |

---

## tests/ exemption decision

**Decision: no additional skip added.**

The SQL rules all consume `iter_sql_files`, which is positively scoped to `warehouse/**/*.sql`. Real test fixtures live under `tests/fixtures/sql/` — they never start with `warehouse/`, so `iter_sql_files` never returns them. The exemption is already satisfied by construction. This is consistent with the brief's "if the brief already handles this, good" guidance.

The harness-staged copies written by tests into `tests/fixtures/sql/warehouse/` also start with `tests/`, not `warehouse/`, so they too are outside the scope of `iter_sql_files` when running against the real repo via `retail check`. No false positives in `retail check --repo .`.

---

## Concerns

1. **Test-harness writes into the real working tree.** Tests write staged fixture files into `tests/fixtures/sql/warehouse/` via `mkdir`/`write_text` (not `tmp_path`). These files appear as untracked after `pytest` runs. They are under `tests/` so are excluded from all rule scans, but they create noise in `git status`. This is the brief-mandated pattern; refactoring to `tmp_path` would diverge from verbatim code.

2. **Inter-test ordering dependency.** `test_s2_passes_raw_amount_column` relies on `test_s1_passes_snake_case` having already staged `pass_s1_s2.sql`. Works under pytest's default definition order + the file persisting on disk between tests. Not fragile in practice, but a smell.

3. **Black Python 3.14 parse warning.** Black emits `Warning: Python 3.13 cannot parse code formatted for Python 3.14` during `--check`. This is a black version mismatch warning, not an error; all files pass. Acceptable for current machine setup.

4. **`_is_guarded(toks: list, ...)` bare `list` annotation.** This is the verbatim brief code; ruff does not flag it under current config. Left as-is per instruction.

---

## POST-REVIEW FIX (2026-06-24) — test-staging defect

**Coordinator review flagged the test-staging pattern (concerns #1 and #2 above) as an Important defect that must be fixed before M3 is accepted.** Both concerns are now resolved.

### The defect

The M3 SQL-rule tests staged fixture `.sql` files into the **real** repo tree at
`tests/fixtures/sql/warehouse/` via `mkdir`/`write_text`, which:
- (a) left **untracked** files after `pytest` (`git status` showed `?? tests/fixtures/sql/warehouse/`), breaking CI clean-tree checks; and
- (b) created a hidden **ordering dependency**: `test_s2_passes_raw_amount_column` read a file staged by `test_s1_passes_snake_case`, so it would fail under `pytest-randomly`/`xdist` or if run in isolation.

### The fix

Rewrote `tests/unit/test_sql.py` to stage every fixture into a **per-test `tmp_path`**:
- New `_stage(tmp_path, name)` copies the canonical fixture content (still read-only from the tracked flat files under `tests/fixtures/sql/*.sql`) into `tmp_path/warehouse/<name>.sql` and returns the repo-relative path.
- `_ctx(tmp_path, *rel)` builds `RuleContext(repo_root=tmp_path, tracked_files=...)`. Since every SQL rule reads `iter_sql_files(ctx)` (from `ctx.tracked_files`) and then `ctx.repo_root / rel`, pointing `repo_root` at `tmp_path` and listing the staged paths in `tracked_files` fully isolates each test.
- Removed all `mkdir`/`write_text` into the real `FIXTURES` tree. `FIXTURES` is now used only as a read-only content source.
- Every test takes the `tmp_path` fixture and is fully independent — `test_s2_passes_raw_amount_column` stages its own `pass_s1_s2.sql`. All original assertions (rule_id, severity, locator, message) and all positive+negative cases retained verbatim.
- S4a tests need no staging (S4a inspects filenames only, never reads file contents) — they pass synthetic `warehouse/migrations/*.sql` paths directly in `tracked_files`.

Also cleaned the already-polluted tree: `rm -rf tests/fixtures/sql/warehouse` (it was never committed — `git ls-files` confirmed only the flat fixtures were tracked, so no `git rm` needed).

### Minors applied

- `src/retail/rules/sql.py`: `_is_guarded(toks: list, ...)` → `_is_guarded(toks: list[SqlToken], ...)`; added `SqlToken` to the `from ..sql import ...` line. (Concern #4 resolved.)
- S4b CREATE/ALTER-only scope left unchanged; `_is_guarded`'s DROP handling retained as instructed.

### Verification commands + output

`pytest-randomly` / `pytest-forked` / `pytest-xdist` are **not installed** on this
machine (`pytest 8.4.2`, no randomizer/forked plugins). Independence was therefore
proven by (1) running the full suite twice, (2) running the formerly-coupled
`test_s2_passes_raw_amount_column` standalone, and (3) running a hand-picked
reverse-order subset.

```
=== RUN 1: full unit suite ===
90 passed in 3.58s

=== RUN 2: full unit suite (repeat) ===
90 passed in 4.07s

=== RUN 3: test_s2_passes_raw_amount_column standalone (was coupled to S1) ===
1 passed in 0.14s

=== Reverse-order subset (s4b, then s2, then s1) ===
3 passed in 0.13s

=== git status --porcelain (after all test runs — NO tests/fixtures/sql pollution) ===
 M src/retail/rules/sql.py
 M tests/unit/test_sql.py

=== ruff check src tests ===
All checks passed!

=== black --check src tests ===
All done! 24 files would be left unchanged.

=== retail check --repo . ===
[error] P2 commit subject must match '<type>: <desc>' (feat|fix|refactor|docs|chore) (test: add hand-authored golden PBIP fixture and TMDL parser smoke test)
exit=1   # the single grandfathered P2 finding — unchanged
```

`git status --porcelain` shows only the two intentional modified files and **no
untracked `tests/fixtures/sql/` pollution** — the clean-tree defect is gone.

### Residual concern

No randomizer plugin is installed, so independence is demonstrated rather than
enforced by a shuffled run. The new design has zero cross-test state (each test
owns its `tmp_path`), so this is a tooling gap, not a correctness risk. Installing
`pytest-randomly` in CI would make the guarantee automatic.
