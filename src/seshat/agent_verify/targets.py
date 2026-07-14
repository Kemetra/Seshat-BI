"""Data-driven registry of shipped agent-verify targets (spec 129).

Every path below is repository-relative and points at already-committed,
already-shipped artifacts (the generated plugin bundles under
``integrations/``, the repo-root marketplace/discovery manifests, the
provenance manifest, and each target's own exported operating contract).
Adding a third integration is one registry entry here, not a code fork.
"""

from __future__ import annotations

from .model import AgentVerifyError, VerifyTargetSpec

SUPPORTED_TARGETS: tuple[str, ...] = ("claude", "codex")


class UnknownVerifyTargetError(AgentVerifyError):
    """``--target`` names an integration verify does not recognize.

    The CLI maps this to exit 2 (input defect), never an empty PASS.
    """


_REGISTRY: dict[str, VerifyTargetSpec] = {
    "claude": VerifyTargetSpec(
        name="claude",
        manifest_path="integrations/claude-code/seshat-bi/.claude-plugin/plugin.json",
        provenance_manifest="integrations/claude-code/seshat-bi/bundle-manifest.json",
        version_source="claude_plugin",
        footprint_source="integrations/claude-code/seshat-bi/bundle-manifest.json",
        operating_contract="integrations/claude-code/seshat-bi/portable-operating-contract.md",
        # Claude Code ships this bundle as CLI skills + commands only; it
        # declares no IDE-specific surface (external_agent_acceptance.py's
        # CLIENTS map lists claude-code as {"cli"} only).
        ide_surface=False,
    ),
    "codex": VerifyTargetSpec(
        name="codex",
        manifest_path="integrations/codex/seshat-bi/.codex-plugin/plugin.json",
        provenance_manifest="integrations/codex/seshat-bi/bundle-manifest.json",
        version_source="codex_plugin",
        footprint_source="integrations/codex/seshat-bi/bundle-manifest.json",
        operating_contract="integrations/codex/seshat-bi/portable-operating-contract.md",
        # Codex declares an IDE client in addition to CLI (external_agent_
        # acceptance.py's CLIENTS map lists codex as {"cli", "ide"}), and its
        # plugin.json carries an "interface" block the IDE surface reads.
        ide_surface=True,
    ),
}

# The repo-root marketplace/discovery entry per target. Not part of
# VerifyTargetSpec's data-model fields (data-model.md keeps that dataclass to
# the six declared fields); kept as a small sibling lookup instead.
_MARKETPLACE_PATHS: dict[str, str] = {
    "claude": ".claude-plugin/marketplace.json",
    "codex": ".agents/plugins/marketplace.json",
}


def resolve_target(name: str) -> VerifyTargetSpec:
    """Resolve a target name to its spec; fail closed on an unknown name."""
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise UnknownVerifyTargetError(
            f"unknown verify target {name!r}; supported targets: "
            f"{', '.join(SUPPORTED_TARGETS)}"
        ) from exc


def marketplace_path_for(name: str) -> str:
    """The repo-root marketplace/discovery manifest path for ``name``."""
    try:
        return _MARKETPLACE_PATHS[name]
    except KeyError as exc:
        raise UnknownVerifyTargetError(
            f"unknown verify target {name!r}; supported targets: "
            f"{', '.join(SUPPORTED_TARGETS)}"
        ) from exc


def supported_targets() -> tuple[str, ...]:
    return SUPPORTED_TARGETS
