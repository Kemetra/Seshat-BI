# Task M1.7 Report — mode-aware `build_context` + CLI flags

## Files Modified

- `src/retail/runner.py` — widened `build_context` signature; made `_git_ls_files` tolerant of non-git dirs
- `src/retail/cli.py` — refactored to `_build_parser()` + `main()`; added `--commit-range` and `--commit-msg-file` flags
- `tests/unit/test_cli_context.py` — NEW, 7 unit tests (verbatim from brief)

---

## Exact Diffs

### `src/retail/runner.py`

**`_git_ls_files` change** (non-git tolerance — see deviation section):

```diff
 def _git_ls_files(repo_root: Path) -> tuple[str, ...]:
+    """Return repo-relative POSIX paths for every tracked file.
+
+    Returns an empty tuple when ``repo_root`` is not a git repository (e.g.
+    in unit tests that call ``build_context`` on a bare tmp dir) rather than
+    raising ``CalledProcessError``.
+    """
     result = subprocess.run(
         ["git", "ls-files"],
         cwd=repo_root,
-        check=True,
         capture_output=True,
         text=True,
     )
+    if result.returncode != 0:
+        return ()
     # git ls-files already emits forward slashes; split on newlines, drop blanks.
     return tuple(line for line in result.stdout.splitlines() if line)
```

**`build_context` widening**:

```diff
-def build_context(repo_root: Path) -> RuleContext:
-    return RuleContext(repo_root=repo_root, tracked_files=_git_ls_files(repo_root))
+def build_context(
+    repo_root: Path,
+    commit_range: str | None = None,
+    commit_message: str | None = None,
+) -> RuleContext:
+    """Build the read-only context every rule receives.
+
+    ``commit_range`` and ``commit_message`` are the contract-v2 invocation
+    fields: populated by the CLI flags ``--commit-range`` / ``--commit-msg-file``
+    and consumed by P2. Both default to ``None`` (no commit context), which is
+    the local ``retail check`` mode.
+    """
+    return RuleContext(
+        repo_root=repo_root,
+        tracked_files=_git_ls_files(repo_root),
+        commit_range=commit_range,
+        commit_message=commit_message,
+    )
```

### `src/retail/cli.py`

Full replacement — adds `_build_parser()`, moves `retail.rules` import to fire registrations, and wires both new flags:

```diff
-def main(argv: list[str] | None = None) -> int:
-    parser = argparse.ArgumentParser(prog="retail")
-    sub = parser.add_subparsers(dest="command", required=True)
-    check = sub.add_parser("check", help="run static governance checks")
-    check.add_argument("--repo", default=".", help="repo root to check")
-
-    try:
-        args = parser.parse_args(argv)
-    except SystemExit as exc:
-        return int(exc.code or 0)
-
-    if args.command == "check":
-        ctx = build_context(Path(args.repo))
-        return run(all_rules(), ctx)
-
-    return 0
+import retail.rules  # noqa: F401  (import for side effects: fires every @register)
+
+def _build_parser() -> argparse.ArgumentParser:
+    parser = argparse.ArgumentParser(prog="retail", ...)
+    sub = parser.add_subparsers(dest="command", required=True)
+    check = sub.add_parser("check", ...)
+    check.add_argument("--repo", default=".", ...)
+    check.add_argument("--commit-range", dest="commit_range", default=None, ...)
+    check.add_argument("--commit-msg-file", dest="commit_msg_file", default=None, ...)
+    return parser
+
+def main(argv: list[str] | None = None) -> int:
+    try:
+        args = _build_parser().parse_args(argv)
+    except SystemExit as exc:
+        return int(exc.code or 0)
+
+    if args.command == "check":
+        commit_message: str | None = None
+        if args.commit_msg_file is not None:
+            commit_message = (
+                Path(args.commit_msg_file).read_text(encoding="utf-8").rstrip("\n")
+            )
+        ctx = build_context(
+            Path(args.repo),
+            commit_range=args.commit_range,
+            commit_message=commit_message,
+        )
+        return run(all_rules(), ctx)
+
+    return 0
```

---

## Pytest Output

### Failing run (Step 2 — before implementation)

```
ERROR collecting tests/unit/test_cli_context.py
ImportError: cannot import name '_build_parser' from 'retail.cli'
```

### Passing run (Step 5 — new tests only)

```
tests/unit/test_cli_context.py::test_build_context_defaults_both_none PASSED
tests/unit/test_cli_context.py::test_build_context_populates_v2_fields PASSED
tests/unit/test_cli_context.py::test_parser_default_flags_are_none PASSED
tests/unit/test_cli_context.py::test_parser_commit_range_flag PASSED
tests/unit/test_cli_context.py::test_parser_commit_msg_file_flag PASSED
tests/unit/test_cli_context.py::test_main_commit_msg_file_is_read_and_stripped PASSED
tests/unit/test_cli_context.py::test_main_commit_range_flag_threads_through PASSED

7 passed in 0.14s
```

### Full unit suite (Step 6)

```
26 passed in 0.42s  (coverage: 99%)
```

All 26 unit tests pass. No regressions.

---

## Commit SHA

`b3c8b68` — "feat: make build_context mode-aware with --commit-range and --commit-msg-file flags"

---

## Deviations from Brief

### 1. `_git_ls_files` — non-git tolerance edit

**What the carry-forward said:** "M1.4 `_git_ls_files` ALREADY EXISTS — M1.7 must NOT redefine it; import/reuse it."

**What happened:** The brief's verbatim Step 1 tests (`test_build_context_defaults_both_none`, `test_build_context_populates_v2_fields`) call `build_context(tmp_path)` on a bare `tmp_path` (no git init). The brief comment explicitly says "tracked_files behavior on a tmp dir is out of scope." Step 5 requires "7 passed." The existing `_git_ls_files` used `check=True`, which raises `CalledProcessError` (exit 128) on a non-git dir — causing 2 failures.

**Resolution:** An in-place robustness edit to `_git_ls_files` — changed `check=True` to `check=False` (removed the kwarg) and added `if result.returncode != 0: return ()`. This is NOT a redefinition (same function, same location, minimal change). The carry-forward's intent was to prevent a duplicate definition being pasted in; a tolerance edit is compatible with that.

**Impact on M1.4 callers:** `test_build_context_uses_git_ls_files` does `git init` first — the git-repo path is unaffected. All 26 unit tests pass.

### 2. `import retail.rules` moved to `cli.py` module-level

The original M1.5 `cli.py` did not import `retail.rules` (registration side effects were already handled by `runner.py`'s `from . import rules as _rules`). The brief's Step 4 replacement adds `import retail.rules  # noqa: F401` at the top of `cli.py`. Both modules now trigger registration on import — double registration is handled harmlessly because the `_RULES` list is cleared in the test fixture (`_clear_registry`). In production use, the two imports both fire but no module-level code is duplicated. This is safe but slightly redundant; a future cleanup could consolidate to one import site.

---

## Concerns

1. **Silent "all clear" on broken git**: `_git_ls_files` now returns `()` on ANY non-zero git exit (not just "not a git repository"). If git is unavailable or broken in CI, `build_context` will succeed with zero tracked files, and git-aware rules will silently produce no findings — a false "all clear" for the gate. In production this only affects a mis-configured CI environment (valid `repo_root` always has git), but it is worth documenting.

2. **Duplicate `retail.rules` import**: Both `runner.py` and `cli.py` now import `retail.rules` for the registration side effect. This is harmless but redundant — ideally one import site owns it. Suggest consolidating to `cli.py` only in a future cleanup (since `runner.py` is the lower-level module and should not depend on the rules package).

---

## Review Fixes (post-acceptance review round)

The reviewer rated the self-flagged `_git_ls_files` swallow-all-failures issue as
CRITICAL. The following 4 items were fixed. (Both concerns from the section above
are now resolved by fixes #1 and #4 respectively.)

### Fix #1 [CRITICAL] — `_git_ls_files` dispatches on returncode

`src/retail/runner.py` — replaced the blanket `if returncode != 0: return ()`
with a three-way dispatch:

- `0` -> tracked-file tuple (unchanged).
- `128` (new module constant `_GIT_NOT_A_REPO`) -> `()` (expected non-repo / bare
  tmp-dir case the tests rely on).
- any OTHER non-zero -> `raise RuntimeError(f"git ls-files failed (exit {rc}): {stderr}")`
  so CI misconfiguration fails LOUD (red), never silent green.

`build_context(tmp_path)` on a bare dir still works (hits the 128 path -> `()`).

### Fix #2 [IMPORTANT] — missing `--commit-msg-file` exits 1 cleanly

`src/retail/cli.py` — wrapped `Path(...).read_text()` in `try/except
FileNotFoundError`; on miss, prints `error: commit message file not found: <path>`
to **stderr** and `sys.exit(1)` (no raw traceback). Added `import sys`.

### Fix #3 [MINOR] — strip `\r\n` not just `\n`

`src/retail/cli.py` — changed `.rstrip("\n")` to `.rstrip("\r\n")` so a Windows
`COMMIT_EDITMSG` (`\r\n`) leaves no trailing `\r` on `commit_message`.

### Fix #4 [MINOR] — remove rules import from runner.py (composition-root decision)

`src/retail/runner.py` — removed `from . import rules as _rules`. The low-level
runner no longer depends on the rules package; `import retail.rules` lives only in
`cli.py` (the composition root). `all_rules()` is still populated when the CLI
runs. Verified: importing `retail.runner` alone no longer pulls in `retail.rules`.

### Covering tests (one-line result each)

| Fix | Test | Result |
|-----|------|--------|
| #1 (128 -> ()) | `test_runner.py::test_git_ls_files_returns_empty_on_not_a_repo` | PASS |
| #1 (non-128 -> raise) | `test_runner.py::test_git_ls_files_raises_on_non_128_failure` | PASS |
| #2 (missing file -> exit 1) | `test_cli_context.py::test_main_missing_commit_msg_file_exits_1_with_message` | PASS |
| #3 (CRLF strip) | `test_cli_context.py::test_main_commit_msg_file_strips_crlf` | PASS |
| #4 (runner no rules dep) | `test_runner.py::test_importing_runner_does_not_import_rules_package` | PASS |

### Commands run + output

**Targeted (M1.7 + runner):**

```
$ python -m pytest tests/unit/test_cli_context.py tests/unit/test_runner.py -v
...
tests/unit/test_cli_context.py::test_main_commit_msg_file_strips_crlf PASSED
tests/unit/test_cli_context.py::test_main_missing_commit_msg_file_exits_1_with_message PASSED
tests/unit/test_runner.py::test_git_ls_files_returns_empty_on_not_a_repo PASSED
tests/unit/test_runner.py::test_git_ls_files_raises_on_non_128_failure PASSED
tests/unit/test_runner.py::test_importing_runner_does_not_import_rules_package PASSED
16 passed in 0.28s
```

**Full unit suite:**

```
$ python -m pytest -m unit -q
...............................                                          [100%]
src\retail\cli.py    32   1  97%
src\retail\runner.py 24   0 100%
TOTAL               101   1  99%
31 passed in 0.39s
```

(Was 26 passed pre-review; +5 new tests = 31. No regressions.)

**Lint + format:**

```
$ python -m ruff check src/retail/cli.py src/retail/runner.py tests/unit/test_cli_context.py tests/unit/test_runner.py
All checks passed!
$ python -m black --check src/retail/cli.py src/retail/runner.py tests/unit/test_cli_context.py tests/unit/test_runner.py
All done! (4 files would be left unchanged)
```

### Remaining concern

`raw.rstrip("\r\n")` (fix #3) also strips a trailing `\r` mid-context-edge-case
only at the very end of the message — this is the intended behavior for git's
`COMMIT_EDITMSG` and matches the original `\n` strip's intent. No further concern.
Fix #1's `RuntimeError` propagates uncaught out of `build_context`/`main` (no
`try/except SystemExit` for it in `main`), so a genuine git misconfiguration
surfaces as a Python traceback with non-zero exit — loud and red, as required.
If a cleaner CI message is later desired, `main` could catch `RuntimeError` and
`sys.exit(1)` with a one-liner, but that was not in scope for this review round.
