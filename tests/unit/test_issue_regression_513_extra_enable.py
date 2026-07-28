"""Enabling an extra must never change which Seshat build is installed (#513).

PR #510 fixed a real defect -- a bare ``pipx install "seshat-bi[mcp]"`` no-ops on an
existing venv ("Not modifying existing installation ... Pass '--force'"), so the extra
never arrives -- by adding ``--force``. But ``--force`` is documented as "Modify
existing virtual environment", and pipx implements it by RE-RESOLVING the given spec
from the configured index. The emitted spec carries no version and no local path, so:

    A release reviewer installs a candidate wheel (docs/install/user-install.md:33-38,
    `pipx install .\\seshat_bi-<version>-py3-none-any.whl`), hits a missing extra,
    follows the emitted hint, and the build UNDER VALIDATION is replaced by whatever
    the public index serves. Silently, as a side effect of enabling an extra.

Version-pinning does not fix it: a candidate version is not on the index yet, so
`"seshat-bi[mcp]==<installed>"` either fails or resolves a DIFFERENT artifact with the
same version string. `pipx inject seshat-bi --force <deps>` sidesteps the question --
it adds packages without re-resolving the app.

**The invariant under test is the PROPERTY, not the string**: no emitted extra-enable
command may re-resolve the `seshat-bi` distribution. Asserting an exact command string
would just get bent the next time the wording changes (the lesson from #510's own
tests, which pinned `pipx install --force "seshat-bi[dbt]"` in six places).
"""

from __future__ import annotations

import re
import tomllib
from argparse import Namespace
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Extras currently emitted through the generic install-hint boundary.
_EMITTED_EXTRAS = ("mcp", "dbt", "db")


def _pyproject_extras() -> dict[str, list[str]]:
    with open(_REPO_ROOT / "pyproject.toml", "rb") as handle:
        return tomllib.load(handle)["project"]["optional-dependencies"]


#: The hint's own lane LABEL is `pipx install:` / `pip install:` -- a label, not a
#: command. Stripping it is what makes the oracle read the command; matching the raw
#: line reports every correctly-fixed hint as a defect (caught while writing these).
_LANE_LABEL = re.compile(r"^\s*(pipx install|pip install):\s*")


def _reresolves_seshat(line: str) -> bool:
    """Would running the command on ``line`` re-resolve the ``seshat-bi`` distribution?

    THE oracle, and it must sit on the risk: `pipx install seshat-bi...` and
    `pipx upgrade seshat-bi` re-resolve the app from the index (destructive to a
    candidate/pinned/local build); `pipx inject seshat-bi <deps>` does not --
    `seshat-bi` there names the TARGET venv, not a requirement to resolve.

    A plain `pip install "seshat-bi[x]"` is deliberately NOT counted: in a venv it
    installs in place and pip treats an already-satisfied `seshat-bi` as satisfied,
    so it does not swap the build. The pipx lane is where isolation makes a reinstall
    destructive.
    """
    command = _LANE_LABEL.sub("", line)
    return (
        re.search(r"\bpipx\s+(install|upgrade)\b[^\n]*seshat[-_]bi", command)
        is not None
    )


# --------------------------------------------------------------------------- #
# 1. the property, on every emitting surface                                   #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("extra", _EMITTED_EXTRAS)
def test_the_extra_install_hint_never_reresolves_seshat(extra: str) -> None:
    """FAILS PRE-FIX: emitted `pipx install --force "seshat-bi[mcp]"`."""
    from seshat.cli import _extra_install_hint

    hint = _extra_install_hint(extra)

    pipx_line = next(line for line in hint.splitlines() if "pipx" in line)
    assert not _reresolves_seshat(pipx_line), (
        f"the {extra} hint would replace the installed build: {pipx_line!r}"
    )


def test_the_opt_in_step_never_reresolves_seshat() -> None:
    """The `seshat next` / `orchestration-assess` opt-in step, same property.

    FAILS PRE-FIX -- `_PIPX_INSTALL` was the static `pipx install --force "\\1"`.
    """
    from seshat.cli.commands.next_guidance_render import _portable_quoting
    from seshat.orchestration_assess import _DBT_OPT_IN

    emitted = _portable_quoting(_DBT_OPT_IN)

    assert not _reresolves_seshat(emitted), f"opt-in step swaps the build: {emitted!r}"


def test_the_mcp_error_path_never_reresolves_seshat(monkeypatch, capsys) -> None:
    """End-to-end on the stderr a reader actually sees when `seshat mcp` fails."""
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

    for line in err.splitlines():
        assert not _reresolves_seshat(line), f"emitted to stderr: {line!r}"
    # ...and the reader is still told how to get the extra.
    assert "pipx inject seshat-bi" in err
    assert "mcp" in err


def test_orchestration_assess_text_never_reresolves_seshat(
    tmp_path: Path, capsys
) -> None:
    """The second consumer of the engine's opt-in string."""
    from seshat.cli import main
    from tests.unit._next_guidance_fixtures import write_status as _write_status

    (tmp_path / "mappings").mkdir(parents=True, exist_ok=True)
    _write_status(tmp_path, "orders", "publish_ready")
    assert main(["orchestration-assess", "--repo", str(tmp_path)]) == 0

    for line in capsys.readouterr().out.splitlines():
        assert not _reresolves_seshat(line), f"emitted: {line!r}"


# --------------------------------------------------------------------------- #
# 2. the emitted command must still WORK -- the #510 defect must not return    #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("extra", _EMITTED_EXTRAS)
def test_the_pipx_command_still_modifies_an_existing_venv(extra: str) -> None:
    """`--force` is what #510 correctly added; dropping it re-breaks the no-op.

    Without it pipx declines to touch an existing venv and exits having changed
    nothing, so the extra stays absent and the retry fails identically.
    """
    from seshat.cli import _extra_install_hint

    pipx_line = next(
        line for line in _extra_install_hint(extra).splitlines() if "pipx" in line
    )

    assert "--force" in pipx_line, f"would no-op on an existing venv: {pipx_line!r}"


@pytest.mark.parametrize("extra", _EMITTED_EXTRAS)
def test_the_emitted_command_names_every_dependency_of_the_extra(extra: str) -> None:
    """An `inject` that omits a dependency leaves the feature still broken."""
    from seshat.cli import _extra_dependency_specs, _extra_install_hint

    specs = _extra_dependency_specs(extra)
    assert specs, f"no dependency table for the {extra} extra"

    pipx_line = next(
        line for line in _extra_install_hint(extra).splitlines() if "pipx" in line
    )
    for spec in specs:
        assert spec in pipx_line, f"{spec} missing from {pipx_line!r}"


def test_the_dependency_table_matches_pyproject() -> None:
    """The literal table must not drift from `[project.optional-dependencies]`.

    This is the cost of enumerating rather than reading metadata at runtime, so it
    is pinned rather than trusted.
    """
    from seshat.cli import _extra_dependency_specs

    declared = _pyproject_extras()
    for extra in _EMITTED_EXTRAS:
        assert list(_extra_dependency_specs(extra)) == declared[extra], (
            f"the {extra} table drifted from pyproject"
        )


# --------------------------------------------------------------------------- #
# 3. shape guarantees carried over from #507/#510 -- must not regress          #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("extra", _EMITTED_EXTRAS)
def test_no_posix_only_quoting_survives(extra: str) -> None:
    """`cmd.exe` passes apostrophes through literally; Windows is the release lane."""
    from seshat.cli import _extra_install_hint

    hint = _extra_install_hint(extra)

    assert "'" not in hint, f"single quote survived into {hint!r}"


@pytest.mark.parametrize("extra", _EMITTED_EXTRAS)
def test_both_install_lanes_are_still_named(extra: str) -> None:
    """A pipx-only or pip-only remedy is wrong for one of the two lanes."""
    from seshat.cli import _extra_install_hint

    hint = _extra_install_hint(extra)

    assert "pipx" in hint
    assert re.search(r"(?<!pipx )\bpip install\b", hint), "no plain-venv lane named"


def test_an_unknown_extra_falls_back_rather_than_emitting_a_no_op() -> None:
    """An incomplete table must not emit `pipx inject seshat-bi --force` with no
    packages -- that would silently do nothing.

    The fallback is the previous `pipx install --force` form: it re-resolves (the
    #513 defect) but it at least WORKS, and every extra this package emits a hint
    for is in the table, pinned by `test_the_dependency_table_matches_pyproject`.
    """
    from seshat.cli import _extra_install_hint

    hint = _extra_install_hint("nonesuch")

    assert "pipx inject seshat-bi --force\n" not in hint
    assert 'pipx install --force "seshat-bi[nonesuch]"' in hint


def test_portable_quoting_is_still_surgical_and_idempotent() -> None:
    """Unrelated steps untouched; a rewritten step is not rewritten again."""
    from seshat.cli.commands.next_guidance_render import _portable_quoting

    assert _portable_quoting("echo 'keep me'") == "echo 'keep me'"
    assert _portable_quoting("seshat dbt init") == "seshat dbt init"

    once = _portable_quoting("pip install 'seshat-bi[dbt]'")
    assert _portable_quoting(once) == once, "not idempotent"


def test_a_lazily_imported_sdk_still_reaches_the_hint_not_a_traceback() -> None:
    """The hint is useless if the reader never sees it.

    `governor/mcp_server.py` imports the SDK LAZILY, inside `create_server`
    (mcp_server.py:12). So `from ..governor.mcp_server import run_stdio` SUCCEEDS
    with the extra absent, the old guard never fired, and the real
    `ModuleNotFoundError` escaped as a raw traceback -- hiding the one message that
    tells the reader how to fix it.

    Found by running `seshat mcp` in a venv without the extra while verifying #513
    end-to-end; the string tests all passed and the user-visible path was broken.
    Simulated here by making the SDK import fail at CALL time, not import time.
    """
    import builtins

    from seshat import cli

    original = builtins.__import__

    def sdk_missing(name, *args, **kwargs):
        if name.startswith("mcp"):
            raise ModuleNotFoundError("No module named 'mcp'")
        return original(name, *args, **kwargs)

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(builtins, "__import__", sdk_missing)
        code = cli._run_mcp(Namespace(repo="."))
    finally:
        monkeypatch.undo()

    assert code == 2, "a missing SDK must exit 2, not raise"


def test_the_emitted_dependency_makes_the_feature_importable() -> None:
    """The table must name the extra's REAL import closure, not a subset.

    A hint that installs an incomplete closure runs clean and leaves the feature
    still broken -- the reader retries, fails identically, and sees the same hint.
    Verified end-to-end in a clean venv before shipping: `seshat mcp` went from
    `ModuleNotFoundError: No module named 'mcp'` to `create_server` returning a
    working `FastMCP` after running exactly the emitted spec.

    Pinned statically here (the e2e run needs a network install): the module the
    SDK import actually needs must be the distribution the table names.
    """
    from seshat.cli import _extra_dependency_specs

    specs = _extra_dependency_specs("mcp")

    # `mcp_server.py` does `from mcp.server.fastmcp import FastMCP`, so the top
    # level package the table installs must be `mcp`.
    assert any(spec.startswith("mcp") for spec in specs)
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "seshat"
        / "governor"
        / "mcp_server.py"
    ).read_text(encoding="utf-8")
    assert "from mcp.server.fastmcp import FastMCP" in source, (
        "the SDK import moved -- re-verify the dependency table against it"
    )


def test_every_extra_with_a_hint_call_site_has_a_dependency_table() -> None:
    """`_EMITTED_EXTRAS` must not certify coverage it does not have.

    The table is only consulted for extras this package actually emits a hint for.
    If a new `_extra_install_hint('files')` call site appears and `files` is not in
    the table, the fallback silently emits the RE-RESOLVING form #513 exists to
    kill -- and a hardcoded test list would not notice. So the call sites are
    DISCOVERED from the source rather than declared here.
    """
    from seshat.cli import _EXTRA_DEPENDENCIES

    src = Path(__file__).resolve().parents[2] / "src" / "seshat"
    called: set[str] = set()
    for path in src.rglob("*.py"):
        called |= set(
            re.findall(
                r"_extra_install_hint\(\s*['\"]([A-Za-z0-9_-]+)['\"]",
                path.read_text(encoding="utf-8"),
            )
        )

    assert called, "no call sites found -- the discovery regex is broken"
    missing = called - set(_EXTRA_DEPENDENCIES)
    assert not missing, (
        f"these extras are emitted but have no dependency table, so they fall "
        f"back to the re-resolving form: {sorted(missing)}"
    )
    # Every table entry must also be a real extra.
    declared = _pyproject_extras()
    assert not set(_EXTRA_DEPENDENCIES) - set(declared), "table names a fake extra"


def test_the_driver_hint_is_untouched() -> None:
    """#513 changes the EXTRA hint; `_db_extra_hint`'s six callers must not move.

    It was already `pipx inject`-shaped -- that is the shape #513 adopts -- so its
    output is pinned byte-for-byte here to prove the sibling edit did not disturb it.
    """
    from seshat.cli import _db_extra_hint

    assert _db_extra_hint() == (
        "       pipx install:  pipx inject seshat-bi psycopg2-binary\n"
        "       pip install:   pip install 'seshat-bi[db]'"
    )
