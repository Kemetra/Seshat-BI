"""Pure observation and closed-world comparison for native plugin surfaces.

This module never executes a plugin, launches an MCP server, or contacts a
network. Unknown or malformed capability state is represented explicitly so a
caller can fail closed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from seshat.integrations.catalog import McpSurfacePolicy, NativePluginPolicy


@dataclass(frozen=True)
class ObservedMcpServer:
    """One normalized MCP registration exposed by a plugin."""

    name: str
    transport: str
    command: str | None
    args: tuple[str, ...]
    package: str | None


@dataclass(frozen=True)
class ObservedPlugin:
    """A complete observed plugin surface; ``None`` means unenumerable."""

    plugin_id: str
    version: str | None
    skills: frozenset[str] | None
    mcp_servers: tuple[ObservedMcpServer, ...] | None
    agents: frozenset[str] | None
    hooks: frozenset[str] | None


@dataclass(frozen=True)
class ManifestBlocker:
    """One categorical reason a plugin surface cannot be activated."""

    kind: str
    detail: str


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _children(root: Path) -> tuple[Path, ...] | None:
    if not root.is_dir():
        return None
    try:
        return tuple(root.iterdir())
    except OSError:
        return None


def _observe_skills(root: Path) -> frozenset[str] | None:
    skills_root = root / "skills"
    if not skills_root.exists():
        return frozenset()
    children = _children(skills_root)
    if children is None:
        return None
    names: set[str] = set()
    for child in children:
        if not child.is_dir() or not (child / "SKILL.md").is_file():
            return None
        names.add(child.name)
    return frozenset(names)


def _observe_agents(root: Path) -> frozenset[str] | None:
    agents_root = root / "agents"
    if not agents_root.exists():
        return frozenset()
    children = _children(agents_root)
    if children is None:
        return None
    names: set[str] = set()
    for child in children:
        if not child.is_file() or child.suffix.lower() != ".md":
            return None
        names.add(child.stem)
    return frozenset(names)


def _observe_hooks(root: Path) -> frozenset[str] | None:
    hooks_root = root / "hooks"
    if not hooks_root.exists():
        return frozenset()
    if not hooks_root.is_dir():
        return None
    manifest = hooks_root / "hooks.json"
    if not manifest.is_file():
        return None
    try:
        payload = _read_json(manifest)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict) or not all(
        isinstance(name, str) and name.strip() for name in hooks
    ):
        return None
    return frozenset(hooks)


def _package_from_args(args: tuple[str, ...]) -> str | None:
    for argument in args:
        if argument and not argument.startswith("-"):
            return argument
    return None


def _normalize_mcp_servers(payload: object) -> tuple[ObservedMcpServer, ...] | None:
    if not isinstance(payload, dict):
        return None
    raw_servers = payload.get("mcpServers", payload)
    if not isinstance(raw_servers, dict):
        return None
    servers: list[ObservedMcpServer] = []
    for name, raw in raw_servers.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(raw, dict):
            return None
        command = raw.get("command")
        if command is not None and not isinstance(command, str):
            return None
        raw_args = raw.get("args", [])
        if not isinstance(raw_args, list) or not all(
            isinstance(argument, str) for argument in raw_args
        ):
            return None
        args = tuple(raw_args)
        raw_transport = raw.get("transport") or raw.get("type")
        if raw_transport is None:
            transport = "stdio" if command else "http"
        elif isinstance(raw_transport, str):
            transport = raw_transport
        else:
            return None
        package = raw.get("package")
        if package is not None and not isinstance(package, str):
            return None
        servers.append(
            ObservedMcpServer(
                name=name,
                transport=transport,
                command=command,
                args=args,
                package=package or _package_from_args(args),
            )
        )
    return tuple(sorted(servers, key=lambda server: server.name))


def _observe_mcp_servers(root: Path) -> tuple[ObservedMcpServer, ...] | None:
    mcp_manifest = root / ".mcp.json"
    if mcp_manifest.exists():
        if not mcp_manifest.is_file():
            return None
        try:
            return _normalize_mcp_servers(_read_json(mcp_manifest))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None

    plugin_manifest = root / ".claude-plugin" / "plugin.json"
    if not plugin_manifest.exists():
        return ()
    if not plugin_manifest.is_file():
        return None
    try:
        payload = _read_json(plugin_manifest)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or "mcpServers" not in payload:
        return ()
    return _normalize_mcp_servers({"mcpServers": payload["mcpServers"]})


def observe_plugin(
    install_path: Path, inventory_entry: Mapping[str, object]
) -> ObservedPlugin:
    """Observe every standard capability class under one installed plugin."""

    raw_id = inventory_entry.get("id", inventory_entry.get("name", install_path.name))
    plugin_id = raw_id if isinstance(raw_id, str) else ""
    raw_version = inventory_entry.get("version")
    version = raw_version if isinstance(raw_version, str) and raw_version else None
    return ObservedPlugin(
        plugin_id=plugin_id,
        version=version,
        skills=_observe_skills(install_path),
        mcp_servers=_observe_mcp_servers(install_path),
        agents=_observe_agents(install_path),
        hooks=_observe_hooks(install_path),
    )


def locked_plugin_policy(
    upstream_root: Path, policy: NativePluginPolicy
) -> ObservedPlugin:
    """Resolve and observe one plugin from its locked marketplace checkout."""

    manifest_path = upstream_root / Path(*policy.manifest_path.split("/"))
    payload = _read_json(manifest_path)
    if not isinstance(payload, dict) or not isinstance(payload.get("plugins"), list):
        raise ValueError(f"invalid plugin marketplace manifest: {manifest_path}")
    matches = [
        entry
        for entry in payload["plugins"]
        if isinstance(entry, dict) and entry.get("name") == policy.manifest_name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"plugin manifest entry {policy.manifest_name!r} must appear exactly once"
        )
    entry = matches[0]
    raw_source = entry.get("source", ".")
    if not isinstance(raw_source, str) or not raw_source.strip():
        raise ValueError(f"{policy.plugin_id}: plugin source is not a relative path")
    source = (upstream_root / raw_source).resolve()
    try:
        source.relative_to(upstream_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{policy.plugin_id}: plugin source escapes checkout") from exc
    inventory = dict(entry)
    inventory["id"] = policy.plugin_id
    return observe_plugin(source, inventory)


def _surface_sets(
    plugin: ObservedPlugin,
) -> tuple[
    tuple[str, frozenset[str] | None],
    tuple[str, frozenset[str] | None],
    tuple[str, frozenset[str] | None],
    tuple[str, frozenset[str] | None],
]:
    mcp_names = (
        None
        if plugin.mcp_servers is None
        else frozenset(server.name for server in plugin.mcp_servers)
    )
    return (
        ("skill", plugin.skills),
        ("mcp", mcp_names),
        ("agent", plugin.agents),
        ("hook", plugin.hooks),
    )


def _allowed_sets(
    policy: NativePluginPolicy,
) -> dict[str, frozenset[str]]:
    return {
        "skill": frozenset(policy.allowed_skills),
        "mcp": frozenset(server.name for server in policy.allowed_mcp_servers),
        "agent": frozenset(policy.allowed_agents),
        "hook": frozenset(policy.allowed_hooks),
    }


def _is_moving_coordinate(package: str | None) -> bool:
    if not package:
        return True
    if package.endswith("@latest"):
        return True
    if package.startswith("@"):
        return package.count("@") < 2 or not package.rsplit("@", 1)[1]
    return "@" not in package or not package.rsplit("@", 1)[1]


def _compare_mcp(
    origin: str,
    policy: McpSurfacePolicy,
    observed: ObservedMcpServer,
) -> list[ManifestBlocker]:
    prefix = f"{origin} MCP {policy.name}"
    blockers = _mcp_transport_blockers(prefix, policy, observed)
    blockers.extend(_mcp_package_blockers(prefix, policy, observed))
    blockers.extend(_mcp_argument_blockers(prefix, policy, observed))
    return blockers


def _mcp_transport_blockers(
    prefix: str, policy: McpSurfacePolicy, observed: ObservedMcpServer
) -> list[ManifestBlocker]:
    if observed.transport != policy.transport:
        return [
            ManifestBlocker(
                "mcp-transport",
                f"{prefix} transport {observed.transport!r}; "
                f"expected {policy.transport!r}",
            )
        ]
    return []


def _mcp_package_blockers(
    prefix: str, policy: McpSurfacePolicy, observed: ObservedMcpServer
) -> list[ManifestBlocker]:
    if policy.package is not None and observed.package != policy.package:
        moving = "moving coordinate " if _is_moving_coordinate(observed.package) else ""
        return [
            ManifestBlocker(
                "mcp-package",
                f"{prefix} uses {moving}{observed.package!r}; "
                f"expected {policy.package!r}",
            )
        ]
    if policy.forbid_moving_coordinate and _is_moving_coordinate(observed.package):
        return [
            ManifestBlocker(
                "mcp-package", f"{prefix} uses moving coordinate {observed.package!r}"
            )
        ]
    return []


def _mcp_argument_blockers(
    prefix: str, policy: McpSurfacePolicy, observed: ObservedMcpServer
) -> list[ManifestBlocker]:
    blockers: list[ManifestBlocker] = []
    lowered = {argument.lower() for argument in observed.args}
    for required in policy.required_args:
        if required.lower() not in lowered:
            blockers.append(
                ManifestBlocker(
                    "mcp-required-arg", f"{prefix} is missing required {required}"
                )
            )
    for forbidden in policy.forbidden_args:
        if forbidden.lower() in lowered:
            blockers.append(
                ManifestBlocker(
                    "mcp-forbidden-arg", f"{prefix} includes forbidden {forbidden}"
                )
            )
    return blockers


def _identity_blockers(
    policy: NativePluginPolicy, locked: ObservedPlugin, observed: ObservedPlugin
) -> list[ManifestBlocker]:
    if locked.plugin_id == policy.plugin_id and observed.plugin_id == policy.plugin_id:
        return []
    return [
        ManifestBlocker(
            "plugin-identity",
            f"expected {policy.plugin_id!r}; locked={locked.plugin_id!r}, "
            f"active={observed.plugin_id!r}",
        )
    ]


def _version_blockers(
    locked: ObservedPlugin, observed: ObservedPlugin
) -> list[ManifestBlocker]:
    if locked.version is None or observed.version is None:
        return [
            ManifestBlocker(
                "unknown-version", "locked or active plugin version is unknown"
            )
        ]
    if locked.version == observed.version:
        return []
    return [
        ManifestBlocker(
            "version-mismatch",
            f"locked version {locked.version!r} != active version {observed.version!r}",
        )
    ]


def _surface_blockers(
    origin: str,
    kind: str,
    actual: frozenset[str] | None,
    allowed: frozenset[str],
    incompatible: frozenset[str],
) -> list[ManifestBlocker]:
    if actual is None:
        return [
            ManifestBlocker(
                f"unknown-{kind}",
                f"{origin} {kind} capabilities cannot be enumerated",
            )
        ]
    blockers = [
        ManifestBlocker(
            f"undeclared-{kind}",
            f"{origin} plugin exposes undeclared {kind} {name!r}",
        )
        for name in sorted(actual - allowed)
    ]
    blockers.extend(
        ManifestBlocker(
            f"missing-{kind}",
            f"{origin} plugin is missing allowed {kind} {name!r}",
        )
        for name in sorted(allowed - actual)
    )
    blockers.extend(
        ManifestBlocker(
            "incompatible-capability",
            f"{origin} plugin exposes incompatible capability {name!r}",
        )
        for name in sorted(actual & incompatible)
    )
    return blockers


def _plugin_surface_blockers(
    origin: str, policy: NativePluginPolicy, plugin: ObservedPlugin
) -> list[ManifestBlocker]:
    allowed = _allowed_sets(policy)
    incompatible = frozenset(policy.incompatible_capabilities)
    blockers: list[ManifestBlocker] = []
    for kind, actual in _surface_sets(plugin):
        blockers.extend(
            _surface_blockers(origin, kind, actual, allowed[kind], incompatible)
        )
    return blockers


def _plugin_mcp_blockers(
    origin: str, policy: NativePluginPolicy, plugin: ObservedPlugin
) -> list[ManifestBlocker]:
    if plugin.mcp_servers is None:
        return []
    observed_by_name = {server.name: server for server in plugin.mcp_servers}
    blockers: list[ManifestBlocker] = []
    for mcp_policy in policy.allowed_mcp_servers:
        server = observed_by_name.get(mcp_policy.name)
        if server is not None:
            blockers.extend(_compare_mcp(origin, mcp_policy, server))
    return blockers


def compare_plugin(
    policy: NativePluginPolicy,
    locked: ObservedPlugin,
    observed: ObservedPlugin,
) -> tuple[ManifestBlocker, ...]:
    """Compare locked and active plugin surfaces against one exact policy."""

    blockers = _identity_blockers(policy, locked, observed)
    blockers.extend(_version_blockers(locked, observed))
    for origin, plugin in (("locked", locked), ("active", observed)):
        blockers.extend(_plugin_surface_blockers(origin, policy, plugin))
        blockers.extend(_plugin_mcp_blockers(origin, policy, plugin))

    return tuple(blockers)
