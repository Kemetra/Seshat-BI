"""Per-source install handlers for the integration installer.

Extracted from :mod:`seshat.integrations.installer` (which re-exports these
names) so the orchestration of plan/apply/lock and the mechanics of installing
one component live in files of reviewable size. Every handler takes one
:class:`_Install` request and returns ``(status, detail)``.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from seshat.integrations import mcp_config
from seshat.integrations.catalog import (
    MCP_CONFIG,
    NODE_DIR,
    STAGING_DIR,
    Component,
    SourceType,
)
from seshat.integrations.presence import (
    _is_installed,
    _missing_required_payload,
    _profile_env,
    _skill_dir,
    _venv_python,
    installed_coordinate,
)
from seshat.integrations.procs import _detail, remove_tree
from seshat.integrations.resolvers import Resolution

PRESENT = "present"
PLANNED = "planned"
INSTALLED = "installed"
UNAVAILABLE = "unavailable"
FAILED = "failed"
CONFLICT = "conflict"
INCOMPATIBLE = "incompatible"
# Installed, but at a different coordinate than the one now resolved: planned
# work (like `planned`), performed by apply, never reported as `present`.
UPGRADE = "upgrade"

# The statuses that mean a human has something to do.
NEEDS_ACTION = frozenset({FAILED, UNAVAILABLE, CONFLICT, INCOMPATIBLE})


@dataclass(frozen=True)
class _Install:
    """Everything one component's install needs: where, what, and how to run it.

    Every handler took the same five positional arguments, so the shape was
    already a record; naming it means a new handler cannot silently reorder
    `profile` and `root` (both `str`-ish at a call site) and the runner seam
    travels with the request rather than as a trailing bare callable.
    """

    root: Path
    item: Component
    resolved: Resolution
    profile: str
    runner: Callable[[list[str], Path], subprocess.CompletedProcess]

    @property
    def env(self) -> Path:
        """The absolute profile environment this component installs into."""
        return self.root / _profile_env(self.profile)

    def run(self, command: list[str], cwd: Path | None = None):
        """Run `command` through the injected seam, defaulting to the repo root."""
        return self.runner(command, self.root if cwd is None else cwd)


def _handler_for(item: Component):
    """The install handler for one component.

    Registration wins over the source index: `dbt-mcp` resolves from PyPI but
    installs as an MCP entry, not into a virtual environment.
    """
    if item.mcp_server:
        return _install_mcp_server
    return {
        SourceType.PYPI: _install_pypi,
        SourceType.GITHUB: _install_github,
        SourceType.NPM: _install_npm,
    }[item.source_type]


def _install_pypi(req: _Install) -> tuple[str, str]:
    """Install one exact version into the profile's own virtual environment.

    `uv venv` + `uv pip install -p <env>` targets that environment explicitly.
    `sys.executable` is never a target: mutating the operator's active
    interpreter is the boundary this verb was built to hold.
    """
    if shutil.which("uv") is None:
        return UNAVAILABLE, "uv is not on PATH; needed to build an isolated environment"
    if not (req.root / _venv_python(_profile_env(req.profile))).is_file():
        created = req.run(["uv", "venv", str(req.env)])
        if created.returncode:
            return FAILED, _detail(created, "failed to create the profile environment")
    spec = f"{req.item.coordinate}=={req.resolved.version}"
    result = req.run(["uv", "pip", "install", "-p", str(req.env), spec])
    if result.returncode:
        return FAILED, _detail(result, f"failed to install {spec}")
    return INSTALLED, f"{spec} in {_profile_env(req.profile).as_posix()}"


def _clone_at_ref(req: _Install, staging: Path, ref: str) -> str | None:
    """Clone into `staging` pinned to `ref`. A failure detail, or None on success.

    A tagless rolling pin cannot be `--branch`-cloned to a commit, so a failed
    shallow clone falls back to a full clone plus an exact detached checkout.
    Still exact, never a floating default branch.
    """
    url = f"https://github.com/{req.item.coordinate}.git"
    shallow = req.run(
        ["git", "clone", "--depth", "1", "--branch", ref, url, str(staging)]
    )
    if not shallow.returncode:
        return None
    leftover = remove_tree(staging)
    if leftover is not None:
        return leftover
    full = req.run(["git", "clone", url, str(staging)])
    if full.returncode:
        return _detail(full, "git clone failed")
    checkout = req.run(["git", "checkout", "--detach", ref], staging)
    if checkout.returncode:
        return _detail(checkout, f"could not check out {ref}")
    return None


def _activate(staging: Path, target: Path, ref: str) -> str | None:
    """Move the validated clone into place; a failure detail, or None.

    An existing installed tree (an upgrade) is moved aside first and restored if
    the swap fails, so a failed upgrade never leaves the component missing.
    """
    previous = staging.parent / "previous"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if target.exists():
            target.replace(previous)
        staging.replace(target)
    except OSError as exc:
        if previous.exists() and not target.exists():
            previous.replace(target)
        return f"could not activate the staged clone: {exc}"
    (target / ".seshat-installed").write_text(f"{ref}\n", encoding="utf-8")
    return None


def _stage_and_activate(req: _Install, scratch: Path, ref: str) -> tuple[str, str]:
    staging = scratch / "tree"
    failure = _clone_at_ref(req, staging, ref)
    if failure is not None:
        return FAILED, failure
    missing = _missing_required_payload(staging, req.item)
    if missing:
        return FAILED, f"missing required payload: {', '.join(missing)}"
    failure = _activate(staging, req.root / _skill_dir(req.item), ref)
    if failure is not None:
        return FAILED, failure
    return (
        INSTALLED,
        f"{req.item.coordinate} at {ref} in {_skill_dir(req.item).as_posix()}",
    )


def _install_github(req: _Install) -> tuple[str, str]:
    """Clone into a fresh staging directory at an exact ref, then activate.

    Staging is what keeps a partial clone from ever being reported installed:
    the marker file that `_is_installed` looks for is written only after the
    clone succeeded and the tree moved into place. Each attempt stages into its
    own fresh directory, so a leftover from an earlier failure cannot block it,
    and a leftover this attempt cannot delete is named in the failure detail.
    """
    if shutil.which("git") is None:
        return UNAVAILABLE, "git is not on PATH"
    target = req.root / _skill_dir(req.item)
    if target.exists() and not _is_installed(req.root, req.item, req.profile):
        return FAILED, f"incomplete existing directory: {target}"
    ref = req.resolved.tag or req.resolved.commit
    if not ref:
        return FAILED, "refusing to clone without an exact tag or commit"

    staging_root = req.root / STAGING_DIR
    staging_root.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=f"{req.item.id}-", dir=staging_root))
    status, detail = _stage_and_activate(req, scratch, ref)
    leftover = remove_tree(scratch)
    if leftover is not None and status != INSTALLED:
        detail = f"{detail}; {leftover}"
    return status, detail


def _install_npm(
    req: _Install,
) -> tuple[str, str]:  # pragma: no cover - every npm component is an MCP server
    """An npm component that is not an MCP registration has no install path yet."""
    return UNAVAILABLE, f"{req.item.coordinate} has no supported npm install path"


# The launcher each MCP server needs on PATH, and the entry builder for it.
_MCP_LAUNCHERS = {
    "powerbi-modeling-mcp": ("npx", "Node.js/npx is not on PATH"),
    "dbt-mcp": ("uvx", "uvx is not on PATH"),
}

_MCP_ENTRIES = {
    "powerbi-modeling-mcp": mcp_config.powerbi_entry,
    "dbt-mcp": mcp_config.dbt_entry,
}


def _own_older_entry(req: _Install, config: dict) -> bool:
    """Whether the registered entry is exactly the one THIS installer wrote.

    Only an entry byte-identical to our own entry for the version our marker
    records may be replaced; anything an operator changed stays a conflict.
    """
    previous = installed_coordinate(req.root, req.item, req.profile)
    if not previous:
        return False
    existing = config.get("mcpServers", {}).get(req.item.id)
    return existing == _MCP_ENTRIES[req.item.id](previous)


def _install_mcp_server(req: _Install) -> tuple[str, str]:
    """Register an MCP server at an exact version, refusing a name conflict.

    The launcher gate is per component: the Power BI server needs `npx`, the dbt
    server needs `uvx`. Gating both on `npx` would report the dbt server as
    installable on a machine that cannot launch it.
    """
    item, version = req.item, req.resolved.version
    launcher, requirement = _MCP_LAUNCHERS[item.id]
    if shutil.which(launcher) is None:
        return UNAVAILABLE, requirement
    entry = _MCP_ENTRIES[item.id](version or "")
    path = req.root / MCP_CONFIG
    try:
        config = mcp_config.load_config(path)
    except mcp_config.McpConfigError as exc:
        return FAILED, str(exc)
    verdict = mcp_config.classify(config, item.id, entry)
    if verdict == mcp_config.CONFLICT and _own_older_entry(req, config):
        verdict = None  # our own registration at the previous version: upgrade it
    if verdict == mcp_config.PRESENT:
        return PRESENT, f"already registered at {version}"
    if verdict == mcp_config.CONFLICT:
        return (
            CONFLICT,
            f"{item.id} is already registered with a different configuration in "
            f"{MCP_CONFIG.as_posix()}; refusing to overwrite an operator's entry",
        )
    try:
        mcp_config.write_config(path, mcp_config.merge(config, item.id, entry))
    except OSError as exc:
        return FAILED, str(exc)
    marker = req.root / NODE_DIR / item.id / ".seshat-installed"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(f"{version}\n", encoding="utf-8")
    mode = f" ({item.mode})" if item.mode else ""
    return INSTALLED, f"{item.coordinate}@{version}{mode}"
