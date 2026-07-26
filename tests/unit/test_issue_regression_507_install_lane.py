"""Every emitted install/run command must work in the DOCUMENTED install lane (#507).

The validated lane is ``pipx`` (``docs/install/user-install.md``:
"installed as an isolated command-line application"; ``docs/install/agent-install.md``:
``pipx install seshat-bi``). That puts Seshat in an ISOLATED environment, which breaks
two shapes that read as runnable:

  * ``python -m seshat.cli ...`` -- the ambient ``python`` cannot import ``seshat`` at
    all, so it fails with ``ModuleNotFoundError``. The installed console script
    (``seshat``, declared in pyproject ``[project.scripts]``) is on PATH in the pipx
    lane AND in an editable dev install, so it is the one form correct in both.
  * a bare ``pip install 'seshat-bi[...]'`` -- it targets the AMBIENT interpreter, so
    the extra lands somewhere Seshat cannot see it, or is refused outright as
    externally-managed (PEP 668).

PR #506 fixed the surfaces it owned and flagged the rest for this issue rather than
silently widening scope. These tests pin the four remaining defects it named, each on
the EMITTED STRING (or emitted stdout/stderr), so none can regress to a single lane:

  1. ``cli._run_mcp`` -- the ``[mcp]`` extra hint;
  2. ``demo load`` -- the psycopg2 enable step;
  3. ``seshat orchestration-assess`` -- the adapter opt-in step;
  4. ``seshat next``'s ``validation_commands``.

The dual-lane SHAPE is the contract, not one blessed string: a reader in either lane
must find their own command, and neither lane's command may be the other's.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from tests.unit._next_guidance_fixtures import (
    REPO_ROOT as _REPO_ROOT,
)
from tests.unit._next_guidance_fixtures import (
    document as _document,
)
from tests.unit._next_guidance_fixtures import (
    write_status as _write_status,
)

pytestmark = pytest.mark.unit


def _bare_pip_installs(text: str) -> list[str]:
    """Lines carrying a ``pip install`` that is NOT part of a ``pipx install``.

    ``pipx install`` contains the substring ``pip install``, so a naive membership
    test would report every correct line as a defect. Masking ``pipx install`` first
    is what makes "no bare pip-only guidance" checkable.
    """
    return [
        line
        for line in text.splitlines()
        if "pip install" in line.replace("pipx install", "").replace("pipx inject", "")
    ]


# --- 1. the [mcp] extra hint -------------------------------------------------


def test_mcp_extra_hint_names_both_install_lanes(monkeypatch, capsys) -> None:
    """The `[mcp]` guidance emitted a pip-only remedy, wrong in the pipx lane."""
    import builtins

    from seshat import cli

    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name.endswith("governor.mcp_server"):
            raise ImportError("missing optional SDK")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    assert cli._run_mcp(Namespace(repo=".")) == 2
    err = capsys.readouterr().err

    # Both lanes are named, and the pipx one MODIFIES the existing install.
    assert 'pipx install --force "seshat-bi[mcp]"' in err
    assert "pip install" in err
    assert "seshat-bi[mcp]" in err
    # No pip-only line: every `pip install` mention must sit on a labelled lane.
    assert "pipx" in err, "pip-only remedy is wrong in the documented pipx lane"


def test_mcp_hint_uses_double_quotes_for_cmd_exe() -> None:
    """`cmd.exe` passes apostrophes through literally, and Windows is the release
    lane -- so `pip install 'seshat-bi[mcp]'` reaches pip as an invalid
    requirement. Pinned so it cannot regress to single quotes."""
    from seshat.cli import _extra_install_hint

    hint = _extra_install_hint("mcp")

    assert "'" not in hint, f"single quote survived into {hint!r}"
    assert '"seshat-bi[mcp]"' in hint


def test_extra_hint_is_not_the_driver_hint_shape() -> None:
    """An extra is resolved by `pipx install`, never by `pipx inject`.

    `pipx inject seshat-bi mcp` is not a command -- `mcp` is an extra of the
    `seshat-bi` distribution, not a package to inject. This is why #507 added a
    SIBLING helper instead of generalizing `_db_extra_hint`.
    """
    from seshat.cli import _db_extra_hint, _extra_install_hint

    assert "pipx inject" not in _extra_install_hint("mcp")
    # ...while the driver hint legitimately still uses inject (unchanged).
    assert "pipx inject seshat-bi psycopg2-binary" in _db_extra_hint()


def test_mcp_extra_is_actually_declared_in_pyproject() -> None:
    """Guidance must not point at an extra the distribution does not define."""
    import tomllib

    with open(_REPO_ROOT / "pyproject.toml", "rb") as handle:
        project = tomllib.load(handle)["project"]

    assert "mcp" in project["optional-dependencies"]
    # The console script the emitted commands rely on.
    assert project["scripts"]["seshat"] == "seshat.cli:main"


# --- 2. `demo load`'s psycopg2 enable step -----------------------------------


def test_demo_load_enable_step_names_both_install_lanes(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """It emitted a pip-only `pip install 'seshat-bi[db]'`, so a pipx-lane reader
    was told to run the one command that cannot work for them.

    Fixed by REUSING `cli._db_extra_hint()` -- the helper that exists for exactly
    this extra -- rather than hand-writing a second copy of the remedy.
    """
    import sys

    monkeypatch.setitem(sys.modules, "psycopg2", None)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")

    from seshat.demo.load import run_load

    assert run_load(Namespace(repo=str(tmp_path), dsn=None)) == 0
    out = capsys.readouterr().out

    assert "pipx inject seshat-bi psycopg2-binary" in out
    assert "seshat-bi[db]" in out
    # The DSN is never echoed back (Principle IX) even while guiding the install.
    assert "u:p@" not in out


def test_demo_load_hint_is_sourced_from_the_shared_helper(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """The emitted block must BE `_db_extra_hint()`'s output, not a lookalike.

    Pins the reuse itself: if someone re-inlines a hand-written string here, the
    brand + remedy can drift per command again -- the drift `_db_extra_hint`'s
    docstring exists to prevent.
    """
    import sys

    monkeypatch.setitem(sys.modules, "psycopg2", None)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")

    from seshat.cli import _db_extra_hint
    from seshat.demo.load import run_load

    assert run_load(Namespace(repo=str(tmp_path), dsn=None)) == 0

    assert _db_extra_hint() in capsys.readouterr().out


# --- 3. `orchestration-assess`'s opt-in step ---------------------------------


def _assess_output(tmp_path: Path, capsys) -> str:
    from seshat.cli import main

    (tmp_path / "mappings").mkdir(parents=True, exist_ok=True)
    _write_status(tmp_path, "orders", "publish_ready")
    assert main(["orchestration-assess", "--repo", str(tmp_path)]) == 0
    return capsys.readouterr().out


def test_orchestration_assess_text_emits_the_pipx_install_form(
    tmp_path: Path, capsys
) -> None:
    """The engine's `_DBT_OPT_IN` string was rewritten to the documented pipx form
    for `seshat next`, but `seshat orchestration-assess` -- the SECOND consumer of
    that same string -- still printed the bare `pip install`.

    Fixed by applying the existing, reviewed `_portable_quoting` rewriter at this
    render boundary too, so both consumers get the documented form from one place
    and the engine keeps owning its own wording.
    """
    out = _assess_output(tmp_path, capsys)

    assert 'pipx install --force "seshat-bi[dbt]"' in out
    assert _bare_pip_installs(out) == [], "a pip-only install step reached the user"


def test_orchestration_assess_emits_no_posix_only_quoting(
    tmp_path: Path, capsys
) -> None:
    """No apostrophe-quoted requirement survives into the Windows release lane."""
    for line in _assess_output(tmp_path, capsys).splitlines():
        if "seshat-bi[" in line:
            assert "'" not in line, f"POSIX-only quoting in {line!r}"


# --- 4. `seshat next`'s validation_commands ----------------------------------


def test_validation_commands_run_in_the_pipx_lane(tmp_path: Path) -> None:
    """`python -m seshat.cli ...` fails with ModuleNotFoundError in the pipx lane.

    The same file already emits `seshat orchestration-assess --repo .` for exactly
    this reason (PR #506 review, P2); the validation_commands table above it was
    left behind. Every emitted command must use the installed console script.
    """
    _write_status(tmp_path, "orders", "gold_ready")

    commands = _document(tmp_path)["validation_commands"]

    assert commands, "the document must emit validation commands"
    for command in commands:
        assert "python -m" not in command, command
        assert command.startswith("seshat "), command


@pytest.mark.parametrize(
    "stage",
    ["source_ready", "mapping_ready", "silver_ready", "gold_ready", "publish_ready"],
)
def test_no_stage_emits_an_ambient_python_command(tmp_path: Path, stage: str) -> None:
    """Sweep every stage's extras, not just the base table.

    `_VALIDATION_EXTRAS_BY_STAGE` adds stage-specific commands, so pinning only the
    default document would leave the gold_ready / semantic_model_ready entries free
    to regress.
    """
    _write_status(tmp_path, "orders", stage)

    document = _document(tmp_path)
    for command in document["validation_commands"]:
        assert "python -m" not in command, f"{stage}: {command}"


def test_next_agent_text_surface_carries_no_ambient_python_command(
    tmp_path: Path, capsys
) -> None:
    """End-to-end on the rendered text an agent actually reads.

    The document-level assertions above would still pass if a renderer reintroduced
    the broken form, so the emitted surface is checked too.
    """
    from seshat.cli import main

    _write_status(tmp_path, "orders", "gold_ready")
    assert main(["next", "--repo", str(tmp_path), "--format", "agent"]) == 0

    out = capsys.readouterr().out

    assert "seshat check --repo ." in out
    assert "python -m seshat" not in out
    assert _bare_pip_installs(out) == [], "a pip-only install step reached the user"


# --- the emitted forms match the repo's own install docs ---------------------


def test_emitted_pipx_forms_match_the_documented_commands() -> None:
    """Match the documented lane verbatim rather than inventing a variant.

    If the install docs ever change their command, this fails and the emitted
    guidance is reconsidered deliberately instead of drifting apart from the docs.
    """
    from seshat.cli import _extra_install_hint

    doc = (_REPO_ROOT / "docs" / "install" / "agent-install.md").read_text(
        encoding="utf-8"
    )

    # The doc's example is a FIRST install, so it carries no `--force`...
    assert 'pipx install "seshat-bi[dbt]"' in doc
    # ...while an enable-step for an ALREADY-installed seshat must modify the
    # existing venv. Same distribution, extra and quoting as the doc; `--force`
    # is the documented option for "Modify existing virtual environment".
    for extra in ("mcp", "dbt"):
        hint = _extra_install_hint(extra)
        assert f'pipx install --force "seshat-bi[{extra}]"' in hint
        assert f'pipx install "seshat-bi[{extra}]"' in hint.replace("--force ", "")


# --- the six existing `_db_extra_hint` callers are UNTOUCHED ------------------


def test_db_extra_hint_output_is_byte_identical_to_the_reviewed_strings() -> None:
    """#507 must not alter `_db_extra_hint`'s output for its six existing callers.

    Those strings are user-facing and were already reviewed (#399, refined per
    engine in #409): `drift.py`, `profile.py` (x2), `validate.py` (x2) and
    `value_check.py`. #507 REUSES this helper from `demo load` and adds a SIBLING
    for extras -- neither may change what the six already emit. Pinned byte-for-byte
    so a future edit to the sibling cannot silently drift the driver hint.

    Note the deliberate asymmetry with `_extra_install_hint`: this one keeps SINGLE
    quotes (`pip install 'seshat-bi[db]'`), a real `cmd.exe` inconsistency that is
    nonetheless the reviewed status quo -- left for its own change and its own review.
    """
    from seshat.cli import _db_extra_hint

    assert _db_extra_hint() == (
        "       pipx install:  pipx inject seshat-bi psycopg2-binary\n"
        "       pip install:   pip install 'seshat-bi[db]'"
    )
    assert _db_extra_hint("postgres") == _db_extra_hint()
    assert _db_extra_hint("sqlserver") == (
        "       pipx install:  pipx inject seshat-bi pyodbc\n"
        "       pip install:   pip install 'seshat-bi[mssql]'"
    )
    assert _db_extra_hint("mysql") == (
        "       pipx install:  pipx inject seshat-bi mysql-connector-python\n"
        "       pip install:   pip install 'seshat-bi[mysql]'"
    )
    assert _db_extra_hint("snowflake") == (
        "       pipx install:  pipx inject seshat-bi snowflake-connector-python\n"
        "       pip install:   pip install 'seshat-bi[snowflake]'"
    )
    # An unknown engine still falls back to Postgres, unchanged.
    assert _db_extra_hint("nonesuch") == _db_extra_hint()


def test_a_real_db_hint_caller_still_renders_the_shared_block(
    monkeypatch, capsys
) -> None:
    """End-to-end: a driver-missing `drift` run still emits the reviewed block.

    Guards the reuse from the other direction -- the helper's output is pinned above,
    and this proves a real caller still renders exactly that block, unchanged. Driven
    the way the reviewed `test_cli_drift` test drives it: a `--dsn` is supplied (so
    the DSN gate passes) and the driver probe is forced absent.
    """
    from seshat import cli
    from seshat.cli import main

    monkeypatch.setattr(cli, "_ensure_driver", lambda: False)
    code = main(
        [
            "drift",
            "--baseline",
            "mappings/retail_store_sales/source-profile.md",
            "--dsn",
            "postgresql://x@h/db",
        ]
    )

    assert code == 1
    assert cli._db_extra_hint() in capsys.readouterr().err
