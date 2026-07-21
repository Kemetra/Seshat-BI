"""CLI brand-consistency surface (issues #402 + #399).

Two first-impression papercuts for a fresh external customer who installs the
tool as `seshat`:

- **#402** -- several subcommands echoed a hardcoded ``retail ...`` prefix even
  when the user typed ``seshat``. The output prefix must follow the *invoked*
  command name (the same seam #378 fixed for usage/help text), so the brand the
  customer typed and the brand the tool echoes back match.
- **#399** -- the missing-DB-driver guidance said ``pip install 'retail[db]'``:
  wrong brand (the distribution is ``seshat-bi``) AND wrong mechanism on the
  documented ``pipx`` install path (``pip install`` inside a pipx venv is not how
  a customer adds an extra). The message must name the real distribution and the
  ``pipx inject`` remedy so the guidance is actionable, not a dead end.

``main()`` catches argparse's SystemExit and RETURNS the code (the established
contract), and threads the invoked ``prog`` onto ``args`` so every handler can
echo the right brand. These tests pass ``prog="seshat"`` explicitly -- exactly as
the #378 identity tests do -- so the customer-facing ``seshat`` path is actually
asserted, not just the ``retail`` fallback the module-direct test harness sees.
"""

from __future__ import annotations

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# #402 -- output prefix follows the invoked command name
# ---------------------------------------------------------------------------


def test_status_prefix_follows_invoked_prog(capsys, tmp_path) -> None:
    # `status` with no committed readiness prints a one-liner; under `seshat` it
    # must say "seshat status:", not "retail status:".
    rc = main(["status", "--repo", str(tmp_path)], prog="seshat")
    combined = capsys.readouterr()
    text = combined.out + combined.err
    assert rc == 0
    assert "seshat status:" in text
    assert "retail status:" not in text


def test_validate_deferred_prefix_follows_invoked_prog(capsys, monkeypatch) -> None:
    # Deferred validate (no --source-map) with the driver present emits the
    # "surface is built" note; under `seshat` its prefix must be "seshat".
    from seshat import cli

    monkeypatch.setattr(cli, "_ensure_driver", lambda: True)
    rc = main(["validate", "--dsn", "postgresql://x@h/db"], prog="seshat")
    err = capsys.readouterr().err
    assert rc == 1
    assert "seshat validate:" in err
    assert "retail validate:" not in err


def test_drift_deferred_prefix_follows_invoked_prog(capsys) -> None:
    rc = main(
        ["drift", "--baseline", "mappings/retail_store_sales/source-profile.md"],
        prog="seshat",
    )
    err = capsys.readouterr().err
    assert rc == 1
    assert "seshat drift:" in err
    assert "retail drift:" not in err


def test_retail_alias_still_echoes_retail(capsys, tmp_path) -> None:
    # The deprecated `retail` alias keeps its own identity: when invoked AS
    # `retail`, the prefix is `retail` -- the fix follows the invoked name, it
    # does not hardcode `seshat` either.
    rc = main(["status", "--repo", str(tmp_path)], prog="retail")
    captured = capsys.readouterr()  # capture once: a 2nd call drains the buffer
    text = captured.out + captured.err
    assert rc == 0
    assert "retail status:" in text


# ---------------------------------------------------------------------------
# #402 (PR #403 review) -- module-run stems must normalize, never leak
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("argv0", "expected"),
    [
        # console scripts: the stem IS the brand -> honored verbatim
        ("seshat", "seshat"),
        ("retail", "retail"),
        ("/usr/local/bin/seshat", "seshat"),
        (r"C:\pipx\venvs\seshat-bi\Scripts\seshat.exe", "seshat"),
        # module runs: the stem is the entry FILE, not the brand -> normalize to
        # seshat so no command ever prints `__main__ status:` / `cli drift:`.
        ("/x/seshat/cli/__main__.py", "seshat"),  # python -m seshat.cli
        ("/x/retail/cli.py", "seshat"),  # python -m retail.cli (stem `cli`)
        ("__main__", "seshat"),
        ("cli", "seshat"),
        # no argv0 at all (python -c) -> the primary brand, never a garbage stem
        ("", "seshat"),
    ],
)
def test_invoked_prog_normalizes_unknown_stems(monkeypatch, argv0, expected) -> None:
    # The oracle on the mechanism the PR #403 review flagged: _invoked_prog reads
    # argv[0], and only the two real brand stems survive; everything else is the
    # primary brand. (The module entry points ALSO pass an explicit prog, but this
    # guards the fallback that leaked `__main__` before.)
    import sys

    from seshat.cli import _invoked_prog

    monkeypatch.setattr(sys, "argv", [argv0])
    assert _invoked_prog() == expected


def test_invoked_prog_handles_empty_argv(monkeypatch) -> None:
    # argv itself empty (not just argv[0]) -> still the primary brand, no IndexError.
    import sys

    from seshat.cli import _invoked_prog

    monkeypatch.setattr(sys, "argv", [])
    assert _invoked_prog() == "seshat"


# ---------------------------------------------------------------------------
# #399 -- missing-driver guidance names the real distribution + pipx remedy
# ---------------------------------------------------------------------------


def test_validate_missing_driver_guidance_is_actionable(capsys, monkeypatch) -> None:
    from seshat import cli

    monkeypatch.setattr(cli, "_ensure_driver", lambda: False)
    rc = main(
        ["validate", "--dsn", "postgresql://x@h/db", "--source-map", "x.yaml"],
        prog="seshat",
    )
    err = capsys.readouterr().err
    assert rc == 1
    # Names the real distribution, not `retail`.
    assert "seshat-bi[db]" in err
    assert "retail[db]" not in err
    # Points at the pipx remedy so a pipx-installed customer is not dead-ended.
    assert "pipx inject" in err


def test_drift_missing_driver_guidance_is_actionable(capsys, monkeypatch) -> None:
    from seshat import cli

    monkeypatch.setattr(cli, "_ensure_driver", lambda: False)
    rc = main(
        [
            "drift",
            "--baseline",
            "mappings/retail_store_sales/source-profile.md",
            "--dsn",
            "postgresql://x@h/db",
        ],
        prog="seshat",
    )
    err = capsys.readouterr().err
    assert rc == 1
    assert "seshat-bi[db]" in err
    assert "retail[db]" not in err
    assert "pipx inject" in err
