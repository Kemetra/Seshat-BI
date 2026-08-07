"""Safe configuration generation for the Power BI MCP family (#450 slice 3).

Two placeholder-only renderers -- a read-only ``.mcp.json`` template (local
stdio, remote HTTP, or both) and the generated setup guidance doc -- plus the
write path that (a) runs the C1/C2-style secret scan over EVERY rendered byte
before anything is emitted and (b) refuses to overwrite an existing file.
Nothing here launches a runtime or contacts a server; a template is text.
"""

from __future__ import annotations

import json
from pathlib import Path

from .scan import refuse_if_secret_shaped

TRANSPORT_LOCAL = "local"
TRANSPORT_REMOTE = "remote"
TRANSPORT_BOTH = "both"
TRANSPORTS: tuple[str, ...] = (TRANSPORT_LOCAL, TRANSPORT_REMOTE, TRANSPORT_BOTH)

SETUP_DOC_RELPATH = "docs/generated/powerbi-mcp-setup.md"

# The local stdio server entry -- byte-identical in shape to the committed
# .mcp.json.example (read-only default; relative vendored path, never a
# machine path). A drift between the two is caught by a unit test.
_LOCAL_SERVER: dict[str, object] = {
    "command": "tools/powerbi-modeling-mcp/extension/server/powerbi-modeling-mcp.exe",
    "args": ["--readonly", "--compatibility=powerbi"],
}

# The remote server entry -- Microsoft's published, public endpoint (a
# documented URL, not a secret); auth is Entra ID at connect time, so the
# template carries no credential field at all.
_REMOTE_SERVER: dict[str, object] = {
    "type": "http",
    "url": "https://api.fabric.microsoft.com/v1/mcp/powerbi",
}


class GenerateRefusal(ValueError):
    """A generation request that must not proceed (overwrite, bad transport)."""


def render_mcp_template(transport: str) -> str:
    """Render the read-only, placeholder-only ``.mcp.json`` template text."""
    servers: dict[str, object] = {}
    if transport in (TRANSPORT_LOCAL, TRANSPORT_BOTH):
        servers["powerbi-modeling"] = _LOCAL_SERVER
    if transport in (TRANSPORT_REMOTE, TRANSPORT_BOTH):
        servers["powerbi-remote"] = _REMOTE_SERVER
    if not servers:
        raise GenerateRefusal(
            f"unknown transport {transport!r}; expected one of: "
            + ", ".join(TRANSPORTS)
        )
    text = json.dumps({"mcpServers": servers}, indent=2) + "\n"
    return refuse_if_secret_shaped(text, context=".mcp.json template")


def render_setup_doc() -> str:
    """Render the generated setup guidance (placeholder-only, ASCII-only)."""
    text = _SETUP_DOC
    if not text.isascii():
        raise GenerateRefusal("setup doc rendering produced non-ASCII output")
    return refuse_if_secret_shaped(text, context=SETUP_DOC_RELPATH)


def write_generated(path: Path, text: str) -> Path:
    """Write ``text`` to ``path``, refusing to overwrite an existing file.

    The text has already passed the secret scan inside its renderer; scanning
    again here keeps the chokepoint honest for any future renderer.
    """
    target = Path(path)
    if target.exists():
        raise GenerateRefusal(
            f"refused: {target.as_posix()} already exists -- generation "
            "never overwrites; delete the file deliberately to regenerate"
        )
    refuse_if_secret_shaped(text, context=target.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    return target


_SETUP_DOC = """\
<!--
GENERATED -- do not hand-edit.
Regenerate (after deleting this file -- generation refuses to overwrite) with:
  seshat pbi-mcp generate-config --setup-doc --out docs/generated/powerbi-mcp-setup.md
Placeholder-only by contract: no credential, tenant id, hostname, or user
path may ever appear here (the generator refuses secret-shaped output).
-->

# Power BI MCP setup (generated, read-only)

This guidance covers wiring Microsoft's two OFFICIAL Power BI MCP servers as
the machine-local, READ-ONLY configuration this repo's F016 slot anticipates.
Start with `docs/integrations/pbi-mcp-adapter.md` -- it disambiguates the
three things called "MCP" around this repo and tabulates the local vs remote
servers; this page only shows the config shapes.

Nothing on this page authorizes a write or a publish. F016 stays parked
pending an owner-ratified ADR; the committed default is `--readonly`, and
`--skipconfirmation` is forbidden in every mode.

## Local stdio shape (Power BI Modeling MCP)

Copy the template into the gitignored `.mcp.json` (never commit it):

```json
{
  "mcpServers": {
    "powerbi-modeling": {
      "command": "tools/powerbi-modeling-mcp/extension/server/powerbi-modeling-mcp.exe",
      "args": ["--readonly", "--compatibility=powerbi"]
    }
  }
}
```

- The vendored binary lives under `tools/powerbi-modeling-mcp/` (gitignored);
  the npx alternative is `npx @microsoft/powerbi-modeling-mcp` and needs
  Node.js 20+.
- `--readonly` is this repo's non-negotiable default. Never add
  `--readwrite` (or the older `--read-write` spelling) and never add
  `--skipconfirmation` -- the read-only preflight refuses both.
- Auth is machine-local: interactive Entra ID sign-in, a Service Principal
  (`--authmode=serviceprincipal` with the `AZURE_*` environment variables in
  the gitignored `.env`), or the server's access-token environment variable.
  No auth value ever goes in a tracked file.

## Remote HTTP shape (published-model queries)

```json
{
  "mcpServers": {
    "powerbi-remote": {
      "type": "http",
      "url": "https://api.fabric.microsoft.com/v1/mcp/powerbi"
    }
  }
}
```

- That URL is Microsoft's published public endpoint, not a secret; sign-in is
  Entra ID (OAuth) under the caller's own permissions.
- Prerequisites live tenant-side and are not detectable from this machine:
  the tenant preview setting, Build permission on the target model, and a
  Copilot license for the Generate Query tool. If any is unmet, stop.
- The remote server queries already-published models only; it is never a
  readiness-gate input, and row-level security is NOT enforced for Service
  Principal callers -- do not route RLS-sensitive queries through one.

## After configuring

1. `seshat pbi-mcp doctor --intent <task> [--target <table>]` -- maps your task
   to the governed surface and lists missing prerequisites. Native report
   authoring requires an exact target and routes to Microsoft's official
   `powerbi-report-authoring` skill; activation/discovery is verified separately.
2. `seshat pbi-mcp preflight` -- read-only capability discovery + target
   allowlist validation; refuses write-mode or `--skipconfirmation` configs
   and fails closed while `semantic_model_ready` has not passed.

See also: `templates/pbi-mcp-adapter-contract.md` (the F016 contract),
`docs/operations/adapter-compatibility-matrix.md` (the F016 status row --
`unknown` is never compatible), and `.mcp.json.example` (the committed
read-only example this template mirrors).
"""
