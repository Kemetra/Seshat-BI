"""Regression tests for the LOW-severity security-hardening findings in the
external audit (Report #1, 2026-06-26): #24 git option-injection on a commit
range, #25 re.escape on an interpolated func, #27 git stderr sanitized in errors.
(#26 path-traversal on --metrics-dir is covered in test_cli_semantic.py.)
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# --- #24: a commit range starting with `-` is rejected (option injection) ----


def test_validate_commit_range_rejects_leading_dash() -> None:
    """A `--commit-range` value starting with `-` would be parsed by git as an
    OPTION (e.g. `--output=/etc/passwd`), not a revision. It must be rejected
    before reaching git (audit #24)."""
    from retail.gitutil import validate_commit_range

    for bad in ("--output=/tmp/x", "-n1", "--upload-pack=evil"):
        with pytest.raises(ValueError):
            validate_commit_range(bad)


def test_validate_commit_range_accepts_normal_ranges() -> None:
    """Legitimate revision ranges must pass unchanged."""
    from retail.gitutil import validate_commit_range

    for ok in ("origin/main..HEAD", "HEAD~20..HEAD", "abc123", "v1.0...v2.0"):
        assert validate_commit_range(ok) == ok


def test_validate_commit_range_rejects_trailing_newline() -> None:
    """A trailing newline must be rejected: Python `$` matches before a final `\\n`,
    so a `"a..b\\n"` would otherwise pass and be handed to git verbatim. The regex
    uses `\\Z` to anchor the true end (adversarial pass 2026-06-26)."""
    from retail.gitutil import validate_commit_range

    for bad in ("a..b\n", "HEAD\n", "origin/main..HEAD\n"):
        with pytest.raises(ValueError):
            validate_commit_range(bad)


# --- #25: an interpolated func is regex-escaped --------------------------------


def test_outer_call_treats_func_literally() -> None:
    """`_outer_call` interpolates `func` into a regex; a func with metacharacters
    must be matched LITERALLY, not as a pattern (audit #25 defense-in-depth)."""
    from retail.metric_drift import _outer_call

    # A func containing regex metachars must only match that literal name.
    assert _outer_call("A.B(x)", "A.B") == "x"  # the dot is literal, not "any char"
    assert _outer_call("AXB(x)", "A.B") is None  # `.` must NOT match the `X`


# --- #27: git stderr is not echoed verbatim into the error ---------------------


def test_git_output_error_sanitizes_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing git command must not splice raw, unbounded stderr into the
    RuntimeError (which a rule then surfaces in a Finding) (audit #27)."""
    import subprocess

    from retail import gitutil

    noisy = "fatal: " + "A" * 5000 + "\nsecret-looking-token-xyz"

    class _Result:
        returncode = 128
        stdout = ""
        stderr = noisy

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Result())

    with pytest.raises(RuntimeError) as exc:
        gitutil.git_output(__import__("pathlib").Path("."), "log", "bad..range")

    msg = str(exc.value)
    # The message must be bounded (not the full 5000-char dump).
    assert len(msg) < 1000, f"stderr not truncated: {len(msg)} chars"
    # And it must not be empty / must keep the exit code for debuggability.
    assert "128" in msg
    # The truncation marker must be ASCII -- a non-ASCII ellipsis raises
    # UnicodeEncodeError on a Windows charmap console (adversarial pass 2026-06-26).
    assert msg.isascii(), f"non-ASCII in error message: {msg!r}"
