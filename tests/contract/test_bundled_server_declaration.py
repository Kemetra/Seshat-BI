"""The plugin must make the governor's tools available with no manual registration.

Spec 138 US1, `contracts/bundled-server-declaration.md`. T011-T014.

One shared declaration is projected into both bundle roots; each harness manifest
points at its copy. The declaration adds no tool, carries no path and no secret.

The assertion that earns its keep is the camelCase `mcpServers` wrapper key. One
platform's published example shows snake_case `mcp_servers`, which its parser does
not recognise -- the struct carries a camelCase rename, so a snake_case wrapper
yields a server that silently never loads. Nothing errors at export time; the only
symptom is an absent tool in a live session, which is why it has to be a test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "distribution/bundle-templates/shared"
DECLARATION_REL = "mcp-servers.json"
SHARED_DECLARATION = SHARED / DECLARATION_REL

BUNDLES = {
    "claude": ROOT / "integrations/claude-code/seshat-bi",
    "codex": ROOT / "integrations/codex/seshat-bi",
}
MANIFESTS = {
    "claude": ROOT / "integrations/claude-code/seshat-bi/.claude-plugin/plugin.json",
    "codex": ROOT / "integrations/codex/seshat-bi/.codex-plugin/plugin.json",
}

# Obligation 2 -- this feature adds no tool.
GOVERNOR_TOOLS = {
    "seshat_get_status",
    "seshat_get_next_action",
    "seshat_explain_blockers",
    "seshat_prepare_approval_request",
    "seshat_run_static_check",
    "seshat_export_evidence_pack",
}

_SECRET_KEY_HINTS = ("token", "secret", "key", "password", "credential", "auth")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _servers(document: dict) -> dict:
    """The server map, under the camelCase wrapper or bare at top level."""
    if "mcpServers" in document:
        return document["mcpServers"]
    return document


def test_the_shared_declaration_exists() -> None:
    """Obligation 5 -- one shared source, projected into both bundles."""
    assert SHARED_DECLARATION.is_file(), (
        f"expected the shared server declaration at {SHARED_DECLARATION}"
    )


def test_the_wrapper_key_is_camel_case() -> None:
    """Obligation 7 -- `mcp_servers` is unparsed and fails silently."""
    document = _load(SHARED_DECLARATION)
    assert "mcp_servers" not in document, (
        "the snake_case `mcp_servers` wrapper is not recognised by one platform's "
        "parser, so the server would silently never load"
    )
    assert "mcpServers" in document, (
        "expected the camelCase `mcpServers` wrapper key (or a bare server map)"
    )


def test_the_declaration_names_one_server_running_the_governor() -> None:
    """Obligation 1 -- enabling the plugin is the whole registration step."""
    servers = _servers(_load(SHARED_DECLARATION))
    assert len(servers) == 1, f"expected exactly one declared server, got {servers}"
    (spec,) = servers.values()
    argv = [str(spec.get("command", ""))] + [str(a) for a in spec.get("args", [])]
    assert "mcp" in argv, f"the declared server must run `seshat mcp`; got {argv}"


def test_the_declaration_carries_no_repository_path_argument() -> None:
    """Obligation 3 -- a literal path would name the plugin's own location.

    The contract's original rationale cited the CLI's `.` default. That default was
    REMOVED by owner ruling 2026-07-31 (research R2): the workspace is now
    discovered and discovery fails by name. The obligation is unchanged and better
    supported -- passing no path is now correct rather than merely conventional.
    """
    servers = _servers(_load(SHARED_DECLARATION))
    (spec,) = servers.values()
    args = [str(a) for a in spec.get("args", [])]
    assert "--repo" not in args, (
        "the declaration must carry no repository path argument: it would resolve to "
        f"the plugin's installed location, not the user's workspace; got {args}"
    )
    offenders = [a for a in args if "/" in a or "\\" in a]
    assert not offenders, f"path-like arguments in the declaration: {offenders}"


def test_the_declaration_carries_no_credential_or_secret() -> None:
    """Obligation 4 -- and no environment value that could hold one."""
    servers = _servers(_load(SHARED_DECLARATION))
    (spec,) = servers.values()
    env = spec.get("env", {})
    assert not env, (
        f"the declaration must carry no environment values that could hold a "
        f"secret; got keys {sorted(env)}"
    )
    serialised = json.dumps(spec).lower()
    present = [hint for hint in _SECRET_KEY_HINTS if hint in serialised]
    assert not present, f"secret-suggesting keys in the declaration: {present}"


def test_the_declaration_adds_no_tool() -> None:
    """Obligation 2 -- exactly the six existing read-only governor tools.

    Asserted against the server module rather than a list repeated here, so a new
    tool cannot be added to the governor and silently ship unreviewed.
    """
    source = (ROOT / "src/seshat/governor/mcp_server.py").read_text(encoding="utf-8")
    declared = {tool for tool in GOVERNOR_TOOLS if tool in source}
    assert declared == GOVERNOR_TOOLS, (
        f"governor tools drifted from the contract: missing "
        f"{sorted(GOVERNOR_TOOLS - declared)}"
    )


def _surface() -> dict:
    import yaml  # noqa: PLC0415

    return yaml.safe_load(
        (ROOT / "distribution/public-command-surface.yaml").read_text(encoding="utf-8")
    )


def test_the_surface_declares_a_bundled_server_class() -> None:
    """Obligation 6 -- a fourth artifact class, with its own fields."""
    surface = _surface()
    servers = surface.get("bundled_servers")
    assert servers, "the surface must gain a bundled-server artifact class"
    for entry in servers:
        assert set(entry) == {
            "name",
            "platforms",
            "intent",
            "declaration",
            "bundle_destination",
            "documentation",
            "status",
        }, entry["name"]
        assert (ROOT / entry["declaration"]).is_file(), entry["name"]
        assert (ROOT / entry["documentation"]).is_file(), entry["name"]
        assert set(entry["platforms"]) <= {"claude", "codex"}, entry["name"]


def test_the_reconciliation_exemption_is_scoped_to_the_bundled_server_class() -> None:
    """Prohibition -- widening the exemption must FAIL, not pass quietly.

    Commands and skills keep the invariant that makes the surface trustworthy: a
    shipped one has a reviewed wrapper and an allowlist entry. Only the bundled-server
    class is exempt, and it is enumerated so that adding a second class here is a test
    failure rather than an unnoticed edit.
    """
    exemptions = _surface().get("reconciliation_exemptions")
    assert exemptions == ["bundled_servers"], (
        "the wrapper+allowlist reconciliation may be waived for the bundled-server "
        f"class ALONE; found {exemptions}"
    )


@pytest.mark.parametrize("harness", sorted(BUNDLES))
def test_each_bundle_carries_the_declaration(harness: str) -> None:
    """Obligation 5 -- identical in both bundles."""
    projected = BUNDLES[harness] / DECLARATION_REL
    assert projected.is_file(), f"{harness} bundle is missing {DECLARATION_REL}"
    assert _load(projected) == _load(SHARED_DECLARATION), (
        f"{harness}'s projected declaration differs from the shared source"
    )


@pytest.mark.parametrize("harness", sorted(MANIFESTS))
def test_each_manifest_points_at_its_declaration(harness: str) -> None:
    """Obligation 5 -- only the harness-specific manifest key may differ."""
    manifest = _load(MANIFESTS[harness])
    pointers = [
        value
        for value in manifest.values()
        if isinstance(value, str) and DECLARATION_REL in value
    ]
    assert pointers, (
        f"{harness}'s plugin.json does not point at {DECLARATION_REL}; without the "
        "pointer the declaration ships but is never read"
    )
