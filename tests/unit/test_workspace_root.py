"""`seshat mcp` must not infer its workspace from the process working directory.

Spec 138 US1, research R2. Owner ruling 2026-07-31: remove the cwd dependency
rather than measure it.

The failure this prevents: a plugin-launched server starts in the plugin's own
directory, `--repo` defaults to `.`, and the governor reports readiness for the
plugin directory as though it were the user's project. Every answer would be
confidently wrong, and nothing would say so.

The fix is not "guess better". It is that discovery either finds a real workspace
or FAILS BY NAME -- a governor that cannot identify its workspace must not answer
questions about one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def _resolver() -> Any:
    try:
        from seshat import workspace_root  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover -- the RED state
        pytest.fail(
            "expected `seshat.workspace_root.resolve_workspace_root(explicit=None, "
            f"start=None)` raising `WorkspaceRootError` -- {exc}"
        )
    return workspace_root


def _make_workspace(root: Path) -> Path:
    """A workspace as the bootstrap verbs leave it."""
    (root / ".seshat").mkdir(parents=True)
    (root / "mappings").mkdir()
    return root


def test_an_explicit_root_is_honoured(tmp_path: Path) -> None:
    """The manual lane still works: FR-014 keeps the non-plugin form."""
    mod = _resolver()
    workspace = _make_workspace(tmp_path / "project")
    assert mod.resolve_workspace_root(explicit=str(workspace)) == workspace


def test_the_workspace_is_found_by_walking_up_from_the_start_directory(
    tmp_path: Path,
) -> None:
    """A server started deep inside a workspace still identifies the root."""
    mod = _resolver()
    workspace = _make_workspace(tmp_path / "project")
    deep = workspace / "mappings" / "retail_store_sales"
    deep.mkdir(parents=True)
    assert mod.resolve_workspace_root(start=deep) == workspace


def test_a_directory_that_is_no_workspace_fails_by_name(tmp_path: Path) -> None:
    """The whole point: a plugin directory must not be reported as a workspace.

    This is the R2 failure made harmless. Whatever cwd a plugin-launched server
    inherits, if it is not a Seshat workspace the governor refuses rather than
    answering about the wrong tree.
    """
    mod = _resolver()
    plugin_dir = tmp_path / "plugins" / "seshat-bi"
    plugin_dir.mkdir(parents=True)
    with pytest.raises(mod.WorkspaceRootError, match=str(plugin_dir.name)):
        mod.resolve_workspace_root(start=plugin_dir)


def test_an_explicit_root_that_is_no_workspace_also_fails(tmp_path: Path) -> None:
    """An explicit `--repo` is honoured but still validated."""
    mod = _resolver()
    empty = tmp_path / "nowhere"
    empty.mkdir()
    with pytest.raises(mod.WorkspaceRootError):
        mod.resolve_workspace_root(explicit=str(empty))


def test_a_missing_explicit_root_fails_rather_than_falling_back(
    tmp_path: Path,
) -> None:
    """A typo'd `--repo` must not silently degrade into cwd discovery."""
    mod = _resolver()
    _make_workspace(tmp_path / "project")
    with pytest.raises(mod.WorkspaceRootError):
        mod.resolve_workspace_root(
            explicit=str(tmp_path / "project" / "typo"),
            start=tmp_path / "project",
        )


def test_the_markers_are_derived_from_the_scaffold_not_duplicated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workspace carrying only scaffolded directories is still a workspace.

    `retail init` writes `.seshat/`; `init-project` writes the scaffold. A user who
    has run only the latter still has a real workspace, so recognition follows
    `workspace_init._EMPTY_DIRS` rather than a hand-copied list.
    """
    mod = _resolver()
    from seshat import workspace_init  # noqa: PLC0415

    root = tmp_path / "scaffold-only"
    for relative in workspace_init._EMPTY_DIRS:
        (root / relative).mkdir(parents=True)
    assert mod.resolve_workspace_root(start=root) == root
