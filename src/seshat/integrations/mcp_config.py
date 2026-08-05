"""Generating and merging MCP registrations, with conflict refusal.

Two properties carry the weight here.

**Exactness.** Every generated command carries a resolved version. `npx -y
@microsoft/powerbi-modeling-mcp@latest` and a bare `uvx dbt-mcp` are both moving
references: the operator's config would silently change meaning when upstream
publishes. The builders below take a resolved version and REFUSE to build
without one.

**Never clobbering.** An existing server with the same name is compared, not
overwritten. Identical configuration is `present`; different configuration is a
`conflict` that refuses. There is deliberately no force-overwrite flag -- the
operator's hand-edits outrank this registration, and adding an override is a
separate decision.
"""

from __future__ import annotations

import json
from pathlib import Path

PRESENT = "present"
CONFLICT = "conflict"


class McpConfigError(Exception):
    """An MCP config that cannot be read. Never overwritten."""


def powerbi_entry(version: str) -> dict:
    """The read-only Power BI modeling MCP entry, pinned to an exact version.

    `--readonly` is not optional: this server can author a semantic model, and
    the curated stack registers it for inspection only.
    """
    if not version:
        raise ValueError("powerbi-modeling-mcp requires an exact resolved version")
    return {
        "type": "stdio",
        "command": "npx",
        "args": [
            "-y",
            f"@microsoft/powerbi-modeling-mcp@{version}",
            "--start",
            "--readonly",
        ],
    }


def dbt_entry(version: str) -> dict:
    """The dbt MCP entry, pinned to an exact version.

    A bare `uvx dbt-mcp` resolves whatever is newest at launch time, so the
    version is spelled into the package spec.
    """
    if not version:
        raise ValueError("dbt-mcp requires an exact resolved version")
    return {"type": "stdio", "command": "uvx", "args": [f"dbt-mcp=={version}"]}


def load_config(path: Path) -> dict:
    """The existing config, or an empty one when absent.

    Raises McpConfigError when the file exists but cannot be parsed -- the
    refusal signal. An operator's unparseable config is left exactly as they
    left it.
    """
    if not path.exists():
        return {"mcpServers": {}}
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise McpConfigError(f"unparseable config: {path}") from exc
    if not isinstance(body, dict):
        raise McpConfigError(f"config must be a JSON object: {path}")
    servers = body.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise McpConfigError("mcpServers must be an object")
    return body


def classify(config: dict, name: str, entry: dict) -> str | None:
    """`present` for an identical registration, `conflict` for a different one.

    None means "not registered yet", i.e. safe to plan or write. The comparison
    is on the full entry, so a changed argument -- including a changed pinned
    version -- reads as a conflict rather than being quietly replaced.
    """
    existing = config.get("mcpServers", {}).get(name)
    if existing is None:
        return None
    return PRESENT if existing == entry else CONFLICT


def merge(config: dict, name: str, entry: dict) -> dict:
    """A copy of `config` with `name` registered. Unrelated servers survive."""
    servers = dict(config.get("mcpServers", {}))
    servers[name] = dict(entry)
    merged = dict(config)
    merged["mcpServers"] = servers
    return merged


def write_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
