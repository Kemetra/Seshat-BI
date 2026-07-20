"""CLI identity + version surface (issue #378).

Two first-impression papercuts for a fresh client:
1. The `seshat` command printed `usage: retail ...` because prog was hardcoded.
2. There was no `--version` on any command (the required subcommand blocked it).

`main()` catches argparse's SystemExit (for bad args, --help, and --version) and
RETURNS the code rather than raising -- the established contract -- so these tests
assert on the return value + captured output, never on a raise.
"""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# #378.1 -- prog follows the invoked command name, not a hardcoded "retail"
# ---------------------------------------------------------------------------


def test_help_uses_invoked_prog_name(capsys) -> None:
    from seshat.cli import main

    rc = main(["--help"], prog="seshat")
    out = capsys.readouterr().out
    assert rc == 0
    assert "usage: seshat" in out
    assert "usage: retail" not in out


def test_prog_defaults_when_not_specified(capsys) -> None:
    # Direct callers / the entry points keep a sensible prog (argv[0] basename or
    # the "retail" fallback) -- help still renders.
    from seshat.cli import main

    rc = main(["--help"])  # no explicit prog
    out = capsys.readouterr().out
    assert rc == 0
    assert "usage:" in out


# ---------------------------------------------------------------------------
# #378.2 -- a top-level --version prints the installed distribution version
# ---------------------------------------------------------------------------


def test_version_flag_prints_version_and_exits_zero(capsys) -> None:
    from seshat.cli import main

    rc = main(["--version"])
    printed = capsys.readouterr().out + capsys.readouterr().err
    assert rc == 0
    # A version-shaped string when installed (e.g. "0.5.2"), or the documented
    # off-package fallback when running from an uninstalled source tree. Either
    # way it prints a version token and exits 0 -- never the argparse error.
    assert re.search(r"\d+\.\d+", printed) or "0+unknown" in printed, printed


def test_version_resolver_matches_pyproject_when_installed() -> None:
    # The resolver reads the seshat-bi distribution metadata. When that metadata
    # IS present (installed / CI), it must equal the source-tree pyproject version;
    # when absent (bare source tree), it returns the documented fallback.
    import tomllib
    from pathlib import Path

    from seshat.cli.parser import _distribution_version

    resolved = _distribution_version()
    if resolved == "0+unknown":
        pytest.skip("seshat-bi is not installed in this environment")
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    declared = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"][
        "version"
    ]
    assert resolved == declared


def test_version_available_without_a_subcommand() -> None:
    # The bug: the required subparser rejected `--version` with
    # "the following arguments are required: command" (exit 2). It must
    # short-circuit to a clean exit 0, NOT the argparse required-arg error.
    from seshat.cli import main

    assert main(["--version"]) == 0


def test_version_string_carries_the_invoked_prog(capsys) -> None:
    from seshat.cli import main

    main(["--version"], prog="seshat")
    printed = capsys.readouterr().out + capsys.readouterr().err
    assert printed.startswith("seshat ")
