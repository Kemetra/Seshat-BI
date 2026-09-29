"""Pure observation and closed-world comparison for native plugin surfaces.

This module never executes a plugin, launches an MCP server, or contacts a
network. Unknown or malformed capability state is represented explicitly so a
caller can fail closed.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from seshat.integrations.catalog import McpSurfacePolicy, NativePluginPolicy
from seshat.integrations.plugin_components import (
    COMPONENT_KEYS,
    InvalidDeclaration,
    declarations,
    declared_paths,
    inline_hook_events,
    markdown_names,
    skill_names,
)

# plugin.json component declarations, keyed by component field.
_Declared = Mapping[str, object]


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
    commands: frozenset[str] | None = frozenset()
    # plugin.json keys this firewall cannot review; any one of them blocks.
    unknown_components: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ManifestBlocker:
    """One categorical reason a plugin surface cannot be activated."""

    kind: str
    detail: str


@dataclass(frozen=True)
class _SurfaceContext:
    origin: str
    kind: str


class _InvalidMcpManifest(ValueError):
    """Raised internally when an MCP registration cannot be normalized."""


class _InvalidHookManifest(ValueError):
    """Raised internally when a hook manifest cannot be normalized."""


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _children(root: Path) -> tuple[Path, ...] | None:
    if not root.is_dir():
        return None
    try:
        return tuple(root.iterdir())
    except OSError:
        return None


def _default_skills(root: Path) -> frozenset[str] | None:
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


def _default_agents(root: Path) -> frozenset[str] | None:
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


def _default_commands(root: Path) -> frozenset[str] | None:
    commands_root = root / "commands"
    if not commands_root.exists():
        return frozenset()
    if not commands_root.is_dir():
        return None
    try:
        return markdown_names(commands_root)
    except InvalidDeclaration:
        return None


def _declared_union(
    root: Path,
    declared: _Declared,
    key: str,
    default: frozenset[str] | None,
    names_at: Callable[[Path], frozenset[str]],
) -> frozenset[str] | None:
    """Default-directory names plus every name under the plugin.json paths."""
    if default is None or key not in declared:
        return default
    names = set(default)
    try:
        for path in declared_paths(root, declared[key]):
            names |= names_at(path)
    except (InvalidDeclaration, OSError):
        return None
    return frozenset(names)


def _observe_skills(root: Path, declared: _Declared) -> frozenset[str] | None:
    return _declared_union(root, declared, "skills", _default_skills(root), skill_names)


def _observe_agents(root: Path, declared: _Declared) -> frozenset[str] | None:
    return _declared_union(
        root, declared, "agents", _default_agents(root), markdown_names
    )


def _observe_commands(root: Path, declared: _Declared) -> frozenset[str] | None:
    return _declared_union(
        root, declared, "commands", _default_commands(root), markdown_names
    )


def _hook_manifest_path(root: Path) -> Path | None:
    hooks_root = root / "hooks"
    if not hooks_root.exists():
        return None
    if not hooks_root.is_dir():
        raise _InvalidHookManifest
    manifest = hooks_root / "hooks.json"
    if not manifest.is_file():
        raise _InvalidHookManifest
    return manifest


def _read_hook_manifest(manifest: Path) -> object:
    try:
        return _read_json(manifest)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _InvalidHookManifest from exc


def _hook_names(payload: object) -> frozenset[str]:
    if not isinstance(payload, dict):
        raise _InvalidHookManifest
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        raise _InvalidHookManifest
    return frozenset(_hook_name(name) for name in hooks)


def _hook_name(name: object) -> str:
    if not isinstance(name, str):
        raise _InvalidHookManifest
    if not name.strip():
        raise _InvalidHookManifest
    return name


def _declared_hook_names(root: Path, value: object) -> frozenset[str]:
    """Hook events declared in plugin.json: an inline object or manifest paths."""
    if isinstance(value, dict):
        return _hook_names({"hooks": inline_hook_events(value)})
    try:
        paths = declared_paths(root, value)
    except InvalidDeclaration as exc:
        raise _InvalidHookManifest from exc
    names: set[str] = set()
    for path in paths:
        names |= _hook_names(_read_hook_manifest(path))
    return frozenset(names)


def _observe_hooks(root: Path, declared: _Declared) -> frozenset[str] | None:
    try:
        manifest = _hook_manifest_path(root)
        names = (
            frozenset()
            if manifest is None
            else _hook_names(_read_hook_manifest(manifest))
        )
        if "hooks" in declared:
            names |= _declared_hook_names(root, declared["hooks"])
        return names
    except _InvalidHookManifest:
        return None


def _package_from_args(args: tuple[str, ...]) -> str | None:
    for argument in args:
        if argument and not argument.startswith("-"):
            return argument
    return None


def _mcp_server_entries(payload: object) -> dict[object, object]:
    if not isinstance(payload, dict):
        raise _InvalidMcpManifest
    raw_servers = payload.get("mcpServers", payload)
    if not isinstance(raw_servers, dict):
        raise _InvalidMcpManifest
    return raw_servers


def _mcp_server_config(name: object, raw: object) -> tuple[str, dict[object, object]]:
    if not isinstance(name, str):
        raise _InvalidMcpManifest
    if not name.strip():
        raise _InvalidMcpManifest
    if not isinstance(raw, dict):
        raise _InvalidMcpManifest
    return name, raw


def _optional_mcp_string(raw: dict[object, object], field: str) -> str | None:
    value = raw.get(field)
    if value is not None and not isinstance(value, str):
        raise _InvalidMcpManifest
    return value


def _mcp_args(raw: dict[object, object]) -> tuple[str, ...]:
    value = raw.get("args", [])
    if not isinstance(value, list) or not all(
        isinstance(argument, str) for argument in value
    ):
        raise _InvalidMcpManifest
    return tuple(value)


def _mcp_transport(raw: dict[object, object], command: str | None) -> str:
    value = raw.get("transport") or raw.get("type")
    if value is None:
        return "stdio" if command else "http"
    if not isinstance(value, str):
        raise _InvalidMcpManifest
    return value


def _normalize_mcp_server(name: object, raw: object) -> ObservedMcpServer:
    server_name, config = _mcp_server_config(name, raw)
    command = _optional_mcp_string(config, "command")
    args = _mcp_args(config)
    package = _optional_mcp_string(config, "package")
    return ObservedMcpServer(
        name=server_name,
        transport=_mcp_transport(config, command),
        command=command,
        args=args,
        package=package or _package_from_args(args),
    )


def _normalize_mcp_servers(payload: object) -> tuple[ObservedMcpServer, ...] | None:
    try:
        servers = (
            _normalize_mcp_server(name, raw)
            for name, raw in _mcp_server_entries(payload).items()
        )
        return tuple(sorted(servers, key=lambda server: server.name))
    except _InvalidMcpManifest:
        return None


def _read_mcp_manifest(manifest: Path) -> object:
    if not manifest.is_file():
        raise _InvalidMcpManifest
    try:
        return _read_json(manifest)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _InvalidMcpManifest from exc


def _servers_from(payload: object) -> tuple[ObservedMcpServer, ...]:
    servers = _normalize_mcp_servers(payload)
    if servers is None:
        raise _InvalidMcpManifest
    return servers


def _declared_mcp_servers(root: Path, value: object) -> list[ObservedMcpServer]:
    """MCP servers declared in plugin.json: an inline object or config paths."""
    if isinstance(value, dict):
        return list(_servers_from({"mcpServers": value}))
    try:
        paths = declared_paths(root, value)
    except InvalidDeclaration as exc:
        raise _InvalidMcpManifest from exc
    servers: list[ObservedMcpServer] = []
    for path in paths:
        servers.extend(_servers_from(_read_mcp_manifest(path)))
    return servers


def _merge_servers(
    servers: list[ObservedMcpServer],
) -> tuple[ObservedMcpServer, ...]:
    """Merge every declaration; one name declared two different ways is unknown."""
    by_name: dict[str, ObservedMcpServer] = {}
    for server in servers:
        if by_name.get(server.name, server) != server:
            raise _InvalidMcpManifest
        by_name[server.name] = server
    return tuple(sorted(by_name.values(), key=lambda server: server.name))


def _observe_mcp_servers(
    root: Path, declared: _Declared
) -> tuple[ObservedMcpServer, ...] | None:
    """Every MCP server: `.mcp.json` AND plugin.json's own `mcpServers`, merged."""
    try:
        servers: list[ObservedMcpServer] = []
        standalone = root / ".mcp.json"
        if standalone.exists():
            servers.extend(_servers_from(_read_mcp_manifest(standalone)))
        if "mcpServers" in declared:
            servers.extend(_declared_mcp_servers(root, declared["mcpServers"]))
        return _merge_servers(servers)
    except _InvalidMcpManifest:
        return None


def observe_plugin(
    install_path: Path,
    inventory_entry: Mapping[str, object],
    declared_elsewhere: Mapping[str, object] | None = None,
) -> ObservedPlugin:
    """Observe every standard capability class under one installed plugin.

    The default directories AND the component fields of the plugin's own
    ``plugin.json`` are enumerated; ``declared_elsewhere`` adds component fields
    declared outside it (a marketplace entry). Unrecognised plugin.json keys are
    carried as ``unknown_components`` so the comparison fails closed on them.
    """

    raw_id = inventory_entry.get("id", inventory_entry.get("name", install_path.name))
    plugin_id = raw_id if isinstance(raw_id, str) else ""
    raw_version = inventory_entry.get("version")
    version = raw_version if isinstance(raw_version, str) and raw_version else None
    declared, unknown = declarations(install_path, declared_elsewhere)
    return ObservedPlugin(
        plugin_id=plugin_id,
        version=version,
        skills=_observe_skills(install_path, declared),
        mcp_servers=_observe_mcp_servers(install_path, declared),
        agents=_observe_agents(install_path, declared),
        hooks=_observe_hooks(install_path, declared),
        commands=_observe_commands(install_path, declared),
        unknown_components=unknown,
    )


def _marketplace_plugins(manifest_path: Path) -> list[object]:
    payload = _read_json(manifest_path)
    plugins = payload.get("plugins") if isinstance(payload, dict) else None
    if not isinstance(plugins, list):
        raise ValueError(f"invalid plugin marketplace manifest: {manifest_path}")
    return plugins


def _named_marketplace_entry(
    plugins: list[object], manifest_name: str
) -> dict[object, object]:
    matches = [
        entry
        for entry in plugins
        if isinstance(entry, dict) and entry.get("name") == manifest_name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"plugin manifest entry {manifest_name!r} must appear exactly once"
        )
    return matches[0]


def _locked_plugin_source(
    upstream_root: Path, entry: dict[object, object], plugin_id: str
) -> Path:
    raw_source = entry.get("source", ".")
    if not isinstance(raw_source, str) or not raw_source.strip():
        raise ValueError(f"{plugin_id}: plugin source is not a relative path")
    source = (upstream_root / raw_source).resolve()
    if not source.is_relative_to(upstream_root.resolve()):
        raise ValueError(f"{plugin_id}: plugin source escapes checkout")
    return source


def locked_plugin_policy(
    upstream_root: Path, policy: NativePluginPolicy
) -> ObservedPlugin:
    """Resolve and observe one plugin from its locked marketplace checkout."""

    manifest_path = upstream_root / Path(*policy.manifest_path.split("/"))
    plugins = _marketplace_plugins(manifest_path)
    entry = _named_marketplace_entry(plugins, policy.manifest_name)
    source = _locked_plugin_source(upstream_root, entry, policy.plugin_id)
    inventory = dict(entry)
    inventory["id"] = policy.plugin_id
    elsewhere = {key: entry[key] for key in COMPONENT_KEYS if key in entry}
    return observe_plugin(source, inventory, elsewhere)


def _surface_sets(
    plugin: ObservedPlugin,
) -> tuple[tuple[str, frozenset[str] | None], ...]:
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
        ("command", plugin.commands),
    )


def _allowed_sets(
    policy: NativePluginPolicy,
) -> dict[str, frozenset[str]]:
    return {
        "skill": frozenset(policy.allowed_skills),
        "mcp": frozenset(server.name for server in policy.allowed_mcp_servers),
        "agent": frozenset(policy.allowed_agents),
        "hook": frozenset(policy.allowed_hooks),
        "command": frozenset(policy.allowed_commands),
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
    lowered = {argument.lower() for argument in observed.args}
    missing = _select_mcp_args(policy.required_args, lowered, present=False)
    forbidden = _select_mcp_args(policy.forbidden_args, lowered, present=True)
    return [
        *_render_mcp_arg_blockers(
            prefix, missing, "mcp-required-arg", "is missing required"
        ),
        *_render_mcp_arg_blockers(
            prefix, forbidden, "mcp-forbidden-arg", "includes forbidden"
        ),
    ]


def _select_mcp_args(
    candidates: tuple[str, ...], observed: set[str], *, present: bool
) -> tuple[str, ...]:
    return tuple(
        argument for argument in candidates if (argument.lower() in observed) is present
    )


def _render_mcp_arg_blockers(
    prefix: str, arguments: tuple[str, ...], kind: str, relation: str
) -> list[ManifestBlocker]:
    return [
        ManifestBlocker(kind, f"{prefix} {relation} {argument}")
        for argument in arguments
    ]


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
    context: _SurfaceContext,
    actual: frozenset[str] | None,
    allowed: frozenset[str],
    incompatible: frozenset[str],
) -> list[ManifestBlocker]:
    origin = context.origin
    kind = context.kind
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
            _surface_blockers(
                _SurfaceContext(origin, kind), actual, allowed[kind], incompatible
            )
        )
    return blockers


def _unknown_component_blockers(
    origin: str, plugin: ObservedPlugin
) -> list[ManifestBlocker]:
    return [
        ManifestBlocker(
            "unknown-component",
            f"{origin} plugin.json declares {key!r}, a capability this firewall "
            "cannot enumerate",
        )
        for key in sorted(plugin.unknown_components)
    ]


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
        blockers.extend(_unknown_component_blockers(origin, plugin))
        blockers.extend(_plugin_mcp_blockers(origin, policy, plugin))

    return tuple(blockers)
