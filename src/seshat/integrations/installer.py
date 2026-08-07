"""The plan -> approve -> install -> validate -> lock pipeline.

`plan()` is the default and is network-free and write-free. It reads the catalog,
reads any existing lock, and reports one row per component. `--refresh` swaps in
live resolvers so the rows carry freshly resolved coordinates -- and still writes
nothing. `apply()` is reached only behind explicit approval; it installs into
isolated locations, validates, and only then writes the lock.

Two boundaries are inherited from the shipped verb and preserved verbatim:

* **The ambient interpreter is never modified.** Every Python component installs
  into a per-profile virtual environment under `.seshat/integrations/env/`.
  Nothing here ever runs `pip` against `sys.executable`.
* **Nothing is offered unprompted.** This module is reached only through
  `seshat integrations setup`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

from seshat.integrations import mcp_config
from seshat.integrations.catalog import (
    DAGSTER_PROJECT,
    DEFAULT_PROFILE,
    ENV_DIR,
    LOCK_FILE,
    MCP_CONFIG,
    NODE_DIR,
    SKILLS_DIR,
    STAGING_DIR,
    Channel,
    Component,
    SourceType,
    profile_components,
    profiles_for,
)
from seshat.integrations.compat import apply_policy
from seshat.integrations.discovery import SkillDiscovery, inspect_official_skills
from seshat.integrations.lockfile import LockError, build_lock, read_lock, write_lock
from seshat.integrations.resolvers import Resolution, Resolvers, resolve

PRESENT = "present"
PLANNED = "planned"
INSTALLED = "installed"
UNAVAILABLE = "unavailable"
FAILED = "failed"
CONFLICT = "conflict"
INCOMPATIBLE = "incompatible"

# The statuses that mean a human has something to do.
NEEDS_ACTION = frozenset({FAILED, UNAVAILABLE, CONFLICT, INCOMPATIBLE})

# Bundled skill paths, validated locally rather than downloaded.
_BUNDLED_SKILLS = {
    "seshat-dagster-workflows": (
        "integrations/claude-code/seshat-bi/skills/dagster-workflows/SKILL.md"
    ),
    "seshat-dagster-adapter": "src/seshat/dagster_adapter/__init__.py",
}


@dataclass(frozen=True)
class ComponentPlan:
    """One row of the plan or the result.

    `channel` and `pinned` are what make preview and rolling visible: a row is
    never rendered without saying which channel it came from.
    """

    component: str
    profile: str
    channel: str
    pinned: str
    source: str
    status: str
    detail: str

    @property
    def needs_action(self) -> bool:
        return self.status in NEEDS_ACTION


@dataclass
class SetupOutcome:
    profile: str
    rows: list[ComponentPlan] = field(default_factory=list)
    lock_written: Path | None = None
    notes: list[str] = field(default_factory=list)
    discovery: list[SkillDiscovery] = field(default_factory=list)

    @property
    def needs_action(self) -> bool:
        return any(row.needs_action for row in self.rows) or any(
            result.needs_action for result in self.discovery
        )


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


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _profile_label(item: Component) -> str:
    return ", ".join(profiles_for(item.id)) or "analytics-full"


def _lock_resolution(item: Component, lock) -> Resolution | None:
    """A resolution reconstructed from the lock, when the lock records one.

    This is what lets a plan report exact coordinates with no network call: the
    lock is the memory of the last approved resolution.
    """
    if lock is None:
        return None
    record = lock.components.get(item.id)
    if not isinstance(record, dict):
        return None
    channel = record.get("channel")
    return Resolution(
        component_id=item.id,
        ok=True,
        channel=Channel(channel) if channel in {c.value for c in Channel} else None,
        version=record.get("version"),
        tag=record.get("tag"),
        commit=record.get("commit"),
        sha256=record.get("sha256"),
        signature_verified=record.get("signature_verified"),
        status="locked",
    )


# --------------------------------------------------------------------------- #
# Installed-state detection. A partial install is never `present`.
# --------------------------------------------------------------------------- #


def _skill_dir(item: Component) -> Path:
    return SKILLS_DIR / item.id


def _missing_required_payload(root: Path, item: Component) -> tuple[str, ...]:
    """Catalog-declared payload files absent below ``root``."""
    return tuple(
        required
        for required in item.required_paths
        if not (root / Path(*required.split("/"))).is_file()
    )


def _venv_python(env: Path) -> Path:
    if sys.platform == "win32":
        return env / "Scripts/python.exe"
    return env / "bin/python"


def _profile_env(profile: str) -> Path:
    return ENV_DIR / profile


def _is_installed(root: Path, item: Component, profile: str) -> bool:
    """Whether the component is fully installed -- never partially.

    A skill bundle counts only when its marker file is on disk, and a Python
    component only when its profile interpreter exists AND the distribution has
    metadata inside it. A half-finished clone or a venv without the package
    reports as not installed, so it is re-planned rather than claimed.
    """
    if item.source_type is SourceType.BUNDLED:
        relative = _BUNDLED_SKILLS.get(item.id)
        return bool(relative) and (root / relative).is_file()
    if item.mcp_server:
        # An MCP component is installed when its registration marker exists,
        # whatever index its version came from.
        return (root / NODE_DIR / item.id / ".seshat-installed").is_file()
    if item.source_type is SourceType.GITHUB:
        target = root / _skill_dir(item)
        marker = target / ".seshat-installed"
        return marker.is_file() and not _missing_required_payload(target, item)
    interpreter = root / _venv_python(_profile_env(profile))
    if not interpreter.is_file():
        return False
    return _distribution_present(root / _profile_env(profile), item.coordinate)


# Where a venv keeps installed distribution metadata, on Windows and on POSIX.
_SITE_PACKAGES = ("Lib/site-packages", "lib/python*/site-packages")


def _canonical_dist(name: str) -> str:
    """PEP 503-style canonical form, so `dbt-core` matches `dbt_core.dist-info`."""
    return name.replace("-", "_").lower()


def _distribution_present(env: Path, dist: str) -> bool:
    """Whether `dist` has install metadata inside `env`.

    Reads `*.dist-info` directory names rather than importing anything: an
    import would execute third-party code just to answer a status question.
    """
    canonical = _canonical_dist(dist)
    return any(
        _canonical_dist(info.name.split("-", 1)[0]) == canonical
        for pattern in _SITE_PACKAGES
        for site in env.glob(pattern)
        for info in site.glob("*.dist-info")
    )


# --------------------------------------------------------------------------- #
# Plan.
# --------------------------------------------------------------------------- #


def plan(
    root: Path,
    *,
    profile: str = DEFAULT_PROFILE,
    resolvers: Resolvers | None = None,
    harnesses: tuple[str, ...] = (),
    discovery_runner=None,
    harness_roots: dict[str, Path] | None = None,
    discovery_tool_lookup=None,
) -> SetupOutcome:
    """The default: read-only, and network-free unless `resolvers` is supplied.

    `resolvers` is None for a normal plan -- the coordinates then come from the
    lock, or are reported as needing `--refresh`. Passing live resolvers is what
    `--refresh` does, and even then nothing is written.
    """
    root = Path(root).resolve()
    outcome = SetupOutcome(profile=profile)
    components = profile_components(profile)

    try:
        lock = read_lock(root)
    except LockError as exc:
        # Fail closed: a lock we cannot trust stops the run rather than being
        # treated as absent.
        outcome.rows.append(
            ComponentPlan(
                component="lock",
                profile=profile,
                channel="-",
                pinned="-",
                source=LOCK_FILE.as_posix(),
                status=FAILED,
                detail=str(exc),
            )
        )
        return outcome

    resolutions = _resolve_all(components, resolvers, lock)
    verdict = apply_policy(
        list(zip(components, resolutions)),
        python_version=resolvers.python_version if resolvers else None,
    )
    outcome.notes.extend(verdict.reasons)

    for item, resolved in zip(components, verdict.resolutions):
        outcome.rows.append(_plan_row(root, item, resolved, profile))
    outcome.discovery.extend(
        inspect_official_skills(
            root,
            components,
            installed={
                item.id: _is_installed(root, item, profile) for item in components
            },
            harnesses=harnesses,
            runner=discovery_runner,
            harness_roots=harness_roots,
            tool_lookup=discovery_tool_lookup,
        )
    )
    return outcome


def _resolve_all(
    components: tuple[Component, ...],
    resolvers: Resolvers | None,
    lock,
) -> list[Resolution]:
    resolved: list[Resolution] = []
    for item in components:
        if resolvers is not None:
            resolved.append(resolve(item, resolvers))
            continue
        from_lock = _lock_resolution(item, lock)
        if from_lock is not None:
            resolved.append(from_lock)
            continue
        if item.source_type is SourceType.BUNDLED:
            resolved.append(
                Resolution(
                    component_id=item.id,
                    ok=True,
                    channel=Channel.BUNDLED,
                    status="bundled",
                )
            )
            continue
        resolved.append(
            Resolution(
                component_id=item.id,
                ok=False,
                channel=item.channel,
                status=UNAVAILABLE,
                reason=(
                    "no pinned version is recorded; run with --refresh to resolve "
                    "the latest compatible release"
                ),
            )
        )
    return resolved


def _row(
    item: Component, resolved: Resolution, status: str, detail: str
) -> ComponentPlan:
    """One row carrying the resolution's own coordinate.

    The identity fields (component, profile label, channel, source) are derived
    the same way on every row, so a caller states the verdict and nothing else.
    """
    return ComponentPlan(
        component=item.id,
        profile=_profile_label(item),
        channel=(resolved.channel or item.channel).value,
        pinned=resolved.pinned or "-",
        source=item.source,
        status=status,
        detail=detail,
    )


def _unpinned_row(
    item: Component, resolved: Resolution, status: str, detail: str
) -> ComponentPlan:
    """One row that reports NO pin, whatever the resolution happens to carry.

    Used where a coordinate would be misleading rather than absent: a refused
    component was never pinned, and a bundled artifact that is missing from disk
    must not advertise the version a stale lock remembers for it.
    """
    return replace(_row(item, resolved, status, detail), pinned="-")


def _settled_row(
    root: Path, item: Component, resolved: Resolution, profile: str
) -> ComponentPlan | None:
    """The row for a component that needs no further work, or None to proceed.

    Shared by the plan and the apply pass so the two can never disagree about
    what counts as unresolvable, already present, or a missing bundled artifact.
    """
    if not resolved.ok:
        return _unpinned_row(
            item, resolved, resolved.status or UNAVAILABLE, resolved.reason or item.role
        )
    if _is_installed(root, item, profile):
        return _row(item, resolved, PRESENT, _present_detail(item, resolved))
    if item.source_type is SourceType.BUNDLED:
        relative = _BUNDLED_SKILLS.get(item.id, "")
        return _unpinned_row(
            item, resolved, UNAVAILABLE, f"bundled artifact is absent: {relative}"
        )
    return None


def _plan_row(
    root: Path, item: Component, resolved: Resolution, profile: str
) -> ComponentPlan:
    settled = _settled_row(root, item, resolved, profile)
    if settled is not None:
        return settled
    detail = _planned_detail(item, resolved, profile)
    if resolved.reason:
        detail = f"{detail} ({resolved.reason})"
    return _row(item, resolved, PLANNED, detail)


def _present_detail(item: Component, resolved: Resolution) -> str:
    if item.source_type is SourceType.BUNDLED:
        return "ships with Seshat; validated locally"
    return f"installed at {resolved.pinned or 'an unrecorded version'}"


def _planned_detail(item: Component, resolved: Resolution, profile: str) -> str:
    if item.mcp_server:
        mode = f" ({item.mode})" if item.mode else ""
        return (
            f"register {item.id} at {item.coordinate}@{resolved.version}{mode} in "
            f"{MCP_CONFIG.as_posix()}"
        )
    if item.source_type is SourceType.PYPI:
        env = _profile_env(profile).as_posix()
        return f"install {item.coordinate}=={resolved.version} into {env}"
    if item.source_type is SourceType.GITHUB:
        pin = resolved.tag or resolved.commit or ""
        return f"clone {item.coordinate} at {pin} into {_skill_dir(item).as_posix()}"
    if item.source_type is SourceType.NPM:
        return (
            f"register {item.id} at {item.coordinate}@{resolved.version} in "
            f"{MCP_CONFIG.as_posix()}"
        )
    return item.role


# --------------------------------------------------------------------------- #
# Apply.
# --------------------------------------------------------------------------- #


def apply(
    root: Path,
    *,
    profile: str = DEFAULT_PROFILE,
    resolvers: Resolvers,
    runner=None,
    harnesses: tuple[str, ...] = (),
    discovery_runner=None,
    harness_roots: dict[str, Path] | None = None,
    discovery_tool_lookup=None,
) -> SetupOutcome:
    """Install the approved plan into isolation, validate, then write the lock.

    `resolvers` is REQUIRED: installing without having resolved exact
    coordinates is the thing this whole module exists to prevent. `runner` is
    the subprocess seam, injected so tests never spawn a real clone or venv.
    """
    root = Path(root).resolve()
    runner = runner or _run
    outcome = SetupOutcome(profile=profile)
    components = profile_components(profile)

    try:
        read_lock(root)
    except LockError as exc:
        outcome.rows.append(
            ComponentPlan(
                component="lock",
                profile=profile,
                channel="-",
                pinned="-",
                source=LOCK_FILE.as_posix(),
                status=FAILED,
                detail=str(exc),
            )
        )
        return outcome

    resolutions = [resolve(item, resolvers) for item in components]
    verdict = apply_policy(
        list(zip(components, resolutions)),
        python_version=resolvers.python_version,
    )
    outcome.notes.extend(verdict.reasons)

    installed: list[tuple[str, str, str, Resolution]] = []
    for item, resolved in zip(components, verdict.resolutions):
        row, landed = _install_one(
            _Install(
                root=root,
                item=item,
                resolved=resolved,
                profile=profile,
                runner=runner,
            )
        )
        outcome.rows.append(row)
        if landed is not None:
            installed.append((item.id, item.source_type.value, item.source, landed))

    # The lock records what LANDED, and only after the installs above returned.
    # A run in which nothing installed writes nothing, so a failed apply leaves
    # the previous lock byte-for-byte intact.
    if installed:
        document = build_lock(profile, _now(), installed)
        outcome.lock_written = write_lock(root, document)
    outcome.discovery.extend(
        inspect_official_skills(
            root,
            components,
            installed={
                item.id: _is_installed(root, item, profile) for item in components
            },
            harnesses=harnesses,
            runner=discovery_runner,
            harness_roots=harness_roots,
            tool_lookup=discovery_tool_lookup,
        )
    )
    return outcome


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


def _install_one(req: _Install) -> tuple[ComponentPlan, Resolution | None]:
    """Install one component, returning its row and what to record in the lock.

    The second element is the resolution the lock should remember, or None when
    nothing landed. An already-PRESENT component still counts: it IS installed at
    that coordinate, so dropping it would rewrite the lock without it.
    """
    settled = _settled_row(req.root, req.item, req.resolved, req.profile)
    if settled is not None:
        return settled, (req.resolved if settled.status == PRESENT else None)

    status, detail = _handler_for(req.item)(req)
    row = _row(req.item, req.resolved, status, detail)
    return row, (req.resolved if status == INSTALLED else None)


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        command, cwd=cwd, text=True, capture_output=True, check=False
    )


def _detail(result: subprocess.CompletedProcess, fallback: str) -> str:
    return (result.stderr or result.stdout or "").strip() or fallback


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
    shutil.rmtree(staging, ignore_errors=True)
    full = req.run(["git", "clone", url, str(staging)])
    if full.returncode:
        return _detail(full, "git clone failed")
    checkout = req.run(["git", "checkout", "--detach", ref], staging)
    if checkout.returncode:
        return _detail(checkout, f"could not check out {ref}")
    return None


def _install_github(req: _Install) -> tuple[str, str]:
    """Clone into staging at an exact ref, then activate by rename.

    Staging is what keeps a partial clone from ever being reported installed:
    the marker file that `_is_installed` looks for is written only after the
    clone succeeded and the tree moved into place.
    """
    if shutil.which("git") is None:
        return UNAVAILABLE, "git is not on PATH"
    target = req.root / _skill_dir(req.item)
    if target.exists():
        return FAILED, f"incomplete existing directory: {target}"
    ref = req.resolved.tag or req.resolved.commit
    if not ref:
        return FAILED, "refusing to clone without an exact tag or commit"

    staging = req.root / STAGING_DIR / req.item.id
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.parent.mkdir(parents=True, exist_ok=True)
    failure = _clone_at_ref(req, staging, ref)
    if failure is not None:
        shutil.rmtree(staging, ignore_errors=True)
        return FAILED, failure

    missing = _missing_required_payload(staging, req.item)
    if missing:
        shutil.rmtree(staging, ignore_errors=True)
        return FAILED, f"missing required payload: {', '.join(missing)}"

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        staging.replace(target)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        return FAILED, f"could not activate the staged clone: {exc}"
    (target / ".seshat-installed").write_text(f"{ref}\n", encoding="utf-8")
    return (
        INSTALLED,
        f"{req.item.coordinate} at {ref} in {_skill_dir(req.item).as_posix()}",
    )


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


# `DAGSTER_PROJECT` is re-exported for the docs and tests that name the governed
# orchestration project's location.
__all__ = [
    "DAGSTER_PROJECT",
    "ComponentPlan",
    "SetupOutcome",
    "apply",
    "plan",
]
