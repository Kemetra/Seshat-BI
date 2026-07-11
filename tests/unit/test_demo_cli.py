"""US1: CLI wiring for the `retail demo` verb group (spec 083)."""

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit


def test_demo_subparsers_registered(capsys):
    """T009: the four demo subcommands are registered and show help.

    main() catches argparse's SystemExit and returns the code, so --help returns
    an int (0) rather than raising; assert on the captured help text.
    """
    rc = main(["demo", "--help"])
    out = capsys.readouterr().out
    assert rc == 0
    for sub in ("init", "load", "run", "report"):
        assert sub in out


def test_demo_requires_subcommand():
    """`retail demo` with no subcommand is a usage error (argparse exit 2)."""
    # required=True on the demo subparsers => argparse exits non-zero.
    assert main(["demo"]) != 0
