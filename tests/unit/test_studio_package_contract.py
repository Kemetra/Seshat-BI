"""T004 -- the Studio package contract, written before the package exists.

Spec 139 requirements under test:

* FR-002 -- a dedicated ``seshat-studio`` launcher OUTSIDE the existing
  ``seshat``/``retail`` dispatch chain.
* FR-005 -- the prebuilt frontend ships inside the wheel; end users need no Node.
* FR-006 -- a base ``seshat-bi`` install stays free of Studio web dependencies;
  FastAPI and Uvicorn live in a ``studio`` optional extra.

The missing-extra path is tested as a first-class behaviour, not an afterthought:
an absent extra must produce a NAMED diagnostic with both install lanes, never an
ImportError traceback. ``tests/unit/test_issue_regression_513_extra_enable.py``
is the precedent for that shape (its ``mcp`` error-path test), and its
``_reresolves_seshat`` oracle is the property the Studio hint must also satisfy.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _pyproject() -> dict:
    with open(_REPO_ROOT / "pyproject.toml", "rb") as handle:
        return tomllib.load(handle)


# --------------------------------------------------------------------------- #
# FR-006 -- the extra exists and carries the web dependencies                  #
# --------------------------------------------------------------------------- #


def test_pyproject_declares_a_studio_extra() -> None:
    extras = _pyproject()["project"]["optional-dependencies"]

    assert "studio" in extras, "no `studio` extra declared in pyproject"


def test_the_studio_extra_carries_fastapi_and_uvicorn() -> None:
    """FR-006 names both distributions explicitly."""
    specs = " ".join(_pyproject()["project"]["optional-dependencies"]["studio"])

    assert "fastapi" in specs
    assert "uvicorn" in specs


def test_the_base_install_declares_no_web_dependency() -> None:
    """FR-006: a normal `seshat-bi` install stays free of Studio web deps.

    The runtime `dependencies` list is what a bare `pip install seshat-bi` pulls
    in, so the web stack must be absent from it.
    """
    runtime = " ".join(_pyproject()["project"].get("dependencies", []))

    for forbidden in ("fastapi", "uvicorn", "starlette"):
        assert forbidden not in runtime, (
            f"{forbidden} leaked into the base install; FR-006 requires it to live "
            "in the `studio` extra only"
        )


# --------------------------------------------------------------------------- #
# FR-002 -- a dedicated launcher, outside the seshat/retail dispatch chain     #
# --------------------------------------------------------------------------- #


def test_pyproject_declares_the_seshat_studio_console_script() -> None:
    scripts = _pyproject()["project"]["scripts"]

    assert "seshat-studio" in scripts, "no `seshat-studio` console script declared"


def test_the_launcher_is_outside_the_seshat_cli_dispatch_chain() -> None:
    """FR-002 -- "outside the existing `seshat`/`retail` CLI dispatch chain".

    `seshat` and `retail` both dispatch through `seshat.cli`. The Studio launcher
    must NOT, or a Studio web import would sit on the static core's import path
    and trip the B1 never-execute boundary at `src/seshat/cli/*.py`.
    """
    scripts = _pyproject()["project"]["scripts"]
    studio_target = scripts["seshat-studio"]

    assert not studio_target.startswith("seshat.cli"), (
        f"`seshat-studio` dispatches through the CLI chain ({studio_target}); "
        "FR-002 requires a dedicated launcher outside it"
    )
    assert studio_target.startswith("seshat.studio"), (
        f"expected the launcher to live in seshat.studio, got {studio_target}"
    )


def test_importing_the_launcher_module_pulls_in_no_web_stack() -> None:
    """The launcher module must be import-light: no module-scope fastapi/uvicorn.

    This is the property that keeps `seshat check` and CI from loading the web
    stack, mirroring the documented `pbi_mcp` idiom ("All pbi_mcp imports are
    LAZY so `seshat check` / CI never load this family").
    """
    import ast

    source = (_REPO_ROOT / "src/seshat/studio/__main__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    module_scope_imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            module_scope_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            module_scope_imports.append(node.module)

    for name in module_scope_imports:
        root = name.split(".")[0]
        assert root not in {"fastapi", "uvicorn", "starlette"}, (
            f"module-scope import of {name!r} in the launcher; it must be lazy so "
            "the base install and `seshat check` never load the web stack"
        )


# --------------------------------------------------------------------------- #
# FR-006 -- the missing-extra diagnostic, and its install-hint property        #
# --------------------------------------------------------------------------- #


def test_the_studio_extra_is_in_the_shared_dependency_table() -> None:
    """`seshat.cli._EXTRA_DEPENDENCIES` is the ONE table both hint surfaces read.

    An extra absent from it falls back to `pipx install --force "seshat-bi[x]"`,
    which re-resolves the app from the index and would silently replace a
    candidate, pinned, or local build (#513).
    """
    from seshat.cli import _extra_dependency_specs

    assert _extra_dependency_specs("studio"), (
        "`studio` is missing from _EXTRA_DEPENDENCIES, so its install hint would "
        "fall back to the build-replacing `pipx install --force` form"
    )


def test_the_studio_dependency_table_matches_pyproject() -> None:
    """Same drift guard the mcp/dbt/db extras already carry."""
    from seshat.cli import _extra_dependency_specs

    declared = _pyproject()["project"]["optional-dependencies"]["studio"]

    assert list(_extra_dependency_specs("studio")) == declared, (
        "the studio table drifted from pyproject"
    )


def test_the_studio_install_hint_never_reresolves_seshat() -> None:
    """The #513 property, applied to Studio's lane.

    `pipx inject seshat-bi --force <deps>` adds dependencies without re-resolving
    the app; `pipx install`/`pipx upgrade` against seshat-bi does not.
    """
    from seshat.cli import _extra_install_hint

    hint = _extra_install_hint("studio")
    pipx_line = next(line for line in hint.splitlines() if "pipx" in line)
    command = re.sub(r"^\s*(pipx install|pip install):\s*", "", pipx_line)

    assert not re.search(r"\bpipx\s+(install|upgrade)\b[^\n]*seshat[-_]bi", command), (
        f"the studio hint would replace the installed build: {pipx_line!r}"
    )
    assert "pipx inject seshat-bi" in pipx_line


def test_a_missing_studio_extra_is_a_named_diagnostic_not_a_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-006 -- absence of the extra is a reported state with a recovery action.

    Modelled on `test_the_mcp_error_path_never_reresolves_seshat`: simulate the
    absent web stack, then assert the reader gets a clean refusal exit code and a
    stderr that names the extra and both install lanes -- never a traceback.
    """
    import builtins

    from seshat.studio import __main__ as launcher

    original = builtins.__import__

    def missing(name: str, *args: object, **kwargs: object) -> object:
        root = name.split(".")[0]
        if root in {"fastapi", "uvicorn", "starlette"}:
            # `name=` mirrors the real import machinery, which always sets it.
            raise ModuleNotFoundError(f"No module named {root!r}", name=root)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)

    exit_code = launcher.main([])

    assert exit_code == 2, "a missing extra must be a refusal (2), not a crash"

    err = capsys.readouterr().err
    assert "studio" in err
    assert "pipx inject seshat-bi" in err
    assert "pip install" in err
    assert "Traceback" not in err


def test_the_launcher_carries_the_workspace_it_was_given(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-001 -- exactly one resolved workspace per process.

    A launcher that accepts `--repo` and discards it would silently serve the wrong
    workspace once T007 lands, so the accepted value must be resolved and reported.
    """
    import sys
    import types

    from seshat.studio import __main__ as launcher
    from seshat.studio import assets, config

    (tmp_path / ".seshat").mkdir()  # a RECOGNIZED workspace, not just a directory

    # Stand in for the extra so the launcher reaches the workspace step. Real
    # modules, not mocks of the launcher's own logic.
    monkeypatch.setitem(sys.modules, "fastapi", types.ModuleType("fastapi"))
    monkeypatch.setitem(sys.modules, "uvicorn", types.ModuleType("uvicorn"))
    monkeypatch.setattr(assets, "describe_missing_assets", lambda directory: None)

    recorded: list[config.LaunchConfiguration] = []
    original_for_workspace = config.LaunchConfiguration.for_workspace

    def record(workspace: object, **kwargs: object) -> config.LaunchConfiguration:
        launch = original_for_workspace(workspace, **kwargs)  # type: ignore[arg-type]
        recorded.append(launch)
        return launch

    monkeypatch.setattr(config.LaunchConfiguration, "for_workspace", record)

    exit_code = launcher.main(["--repo", str(tmp_path)])

    assert exit_code == 0
    # The launcher must PIN the workspace it was given. It deliberately does not
    # print the absolute path -- FR-026 redacts operator layout from output -- so the
    # pinned configuration is the honest assertion, not the message text.
    assert recorded, "the launcher never built a LaunchConfiguration"
    assert recorded[0].workspace_root == tmp_path.resolve()
    assert str(tmp_path.resolve()) not in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# FR-005 -- the prebuilt frontend ships in the wheel                          #
# --------------------------------------------------------------------------- #


def test_the_packaged_static_directory_ships_inside_an_included_package() -> None:
    """FR-005 -- end users must not need Node, so the build output ships prebuilt.

    The asset path must sit INSIDE a declared wheel package, so hatchling ships it
    automatically once T012 writes the build output there. A force-include would be
    both unnecessary and actively harmful before that directory exists -- see
    `test_every_wheel_force_include_source_exists`.
    """
    from seshat.studio import assets

    packages = _pyproject()["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    static_directory = assets.packaged_static_directory()

    assert any(
        static_directory.is_relative_to((_REPO_ROOT / package).resolve())
        for package in packages
    ), (
        f"the Studio static directory {static_directory} is not inside any declared "
        f"wheel package {packages}, so the prebuilt frontend would not ship"
    )


def test_missing_static_assets_are_a_named_diagnostic() -> None:
    """A wheel built without the frontend must say so, not serve a blank page."""
    from seshat.studio import assets

    problem = assets.describe_missing_assets(Path("/nonexistent/studio/static"))

    assert problem is not None
    assert "studio" in problem.lower()
    assert "build" in problem.lower()


def test_every_wheel_force_include_source_exists() -> None:
    """A declared force-include whose source is absent breaks EVERY install.

    Hatchling raises `FileNotFoundError: Forced include not found` during metadata
    generation, so a path that does not exist yet is not a Studio-only problem --
    it makes `pip install seshat-bi` fail for everyone. Studio's prebuilt frontend
    therefore may not be force-included until `studio-ui/` actually produces it
    (T012); the package data must be declared in a way that tolerates its absence.
    """
    force_include = _pyproject()["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ]

    missing = [source for source in force_include if not (_REPO_ROOT / source).exists()]

    assert not missing, (
        f"force-include sources do not exist and would fail the wheel build for "
        f"every install: {missing}"
    )
