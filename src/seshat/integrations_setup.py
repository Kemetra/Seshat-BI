"""Compatibility facade for the curated analytics integration control plane.

The operational implementation lives in :mod:`seshat.integrations`: the
catalog owns membership and component metadata; the resolver/compatibility
pipeline owns exact coordinates; the installer owns plan/apply/validation and
the lock; the renderer owns output. This module preserves the already-shipped
Python import surface without maintaining another installer.

The default compatibility call is a network-free, write-free plan. A direct
caller requesting apply must supply exact resolvers explicitly; the facade
never creates live resolvers or infers approval.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from seshat.integrations.catalog import (
    ALLOWLISTED_SOURCES,
    DAGSTER_PROJECT,
    DEFAULT_PROFILE,
    INTEGRATIONS_DIR,
    LOCK_FILE,
    MCP_CONFIG,
    PROFILE_NAMES,
    SKILLS_DIR,
    Channel,
    UnknownProfile,
    component,
    profile_components,
)
from seshat.integrations.compat import BASELINE_PINS
from seshat.integrations.installer import (
    NEEDS_ACTION as CANONICAL_NEEDS_ACTION,
)
from seshat.integrations.installer import apply as apply_profile
from seshat.integrations.installer import plan as plan_profile
from seshat.integrations.render import as_json as render_json
from seshat.integrations.render import as_text as render_text
from seshat.integrations.resolvers import Resolvers, live_resolvers

__all__ = [
    "DAGSTER_PROJECT",
    "DBT_CORE_PIN",
    "DBT_POSTGRES_PIN",
    "DBT_SKILLS",
    "DEFAULT_PROFILE",
    "FABRIC_SKILLS",
    "INTEGRATIONS_DIR",
    "LOCK_FILE",
    "MCP_CONFIG",
    "PROFILE_NAMES",
    "Channel",
    "IntegrationResult",
    "McpServer",
    "Resolvers",
    "SkillBundle",
    "UnknownProfile",
    "apply_profile",
    "confirm",
    "live_resolvers",
    "needs_operator_action",
    "plan_profile",
    "profile_components",
    "render_json",
    "render_results",
    "render_text",
    "setup_integrations",
]


@dataclass(frozen=True)
class IntegrationResult:
    """Legacy three-field projection of one canonical component row."""

    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class SkillBundle:
    """Import-compatible view derived from one catalog GitHub component."""

    name: str
    repo: str
    directory: Path
    required: tuple[str, ...]


@dataclass(frozen=True)
class McpServer:
    """Legacy type retained for callers; MCP truth lives in the catalog."""

    name: str
    executable: str
    requirement: str
    entry: dict[str, object]


def _bundle_view(component_id: str) -> SkillBundle:
    item = component(component_id)
    return SkillBundle(
        name=item.id,
        repo=f"{ALLOWLISTED_SOURCES[item.source]}.git",
        directory=SKILLS_DIR / item.id,
        required=item.required_paths,
    )


FABRIC_SKILLS = _bundle_view("fabric-skills")
DBT_SKILLS = _bundle_view("dbt-agent-skills")
DBT_CORE_PIN = f"dbt-core=={BASELINE_PINS['dbt-core']}"
DBT_POSTGRES_PIN = f"dbt-postgres=={BASELINE_PINS['dbt-postgres']}"


def _project(outcome) -> list[IntegrationResult]:
    projected = [
        IntegrationResult(row.component, row.status, row.detail) for row in outcome.rows
    ]
    projected.extend(
        IntegrationResult(
            f"{result.component}/{result.harness}",
            result.status,
            "; ".join(result.blockers) or result.next_action,
        )
        for result in outcome.discovery
    )
    return projected


def setup_integrations(
    root: Path,
    *,
    apply: bool = False,
    resolvers: Resolvers | None = None,
    profile: str = DEFAULT_PROFILE,
    runner=None,
    harnesses: tuple[str, ...] = (),
    discovery_runner=None,
    harness_roots: dict[str, Path] | None = None,
    discovery_tool_lookup=None,
) -> list[IntegrationResult]:
    """Plan or apply through the canonical catalog-backed implementation.

    ``apply=True`` is an explicit write request, but it is not permission to
    discover moving coordinates. Exact resolvers must be supplied by the
    caller, matching the CLI's separate ``--refresh`` gate.
    """

    root = Path(root).resolve()
    if apply and resolvers is None:
        return [
            IntegrationResult(
                "integration-apply",
                "failed",
                "exact resolvers are required for apply; no changes were made",
            )
        ]
    if apply:
        kwargs = {
            "profile": profile,
            "resolvers": resolvers,
            "runner": runner,
        }
        if harnesses:
            kwargs.update(
                harnesses=harnesses,
                discovery_runner=discovery_runner,
                harness_roots=harness_roots,
                discovery_tool_lookup=discovery_tool_lookup,
            )
        outcome = apply_profile(root, **kwargs)
    else:
        kwargs = {"profile": profile, "resolvers": resolvers}
        if harnesses:
            kwargs.update(
                harnesses=harnesses,
                discovery_runner=discovery_runner,
                harness_roots=harness_roots,
                discovery_tool_lookup=discovery_tool_lookup,
            )
        outcome = plan_profile(root, **kwargs)
    return _project(outcome)


def needs_operator_action(results: list[IntegrationResult]) -> bool:
    """Whether any projected canonical status requires human action."""

    return any(item.status in CANONICAL_NEEDS_ACTION for item in results)


def _summary(results: list[IntegrationResult]) -> str:
    if any(item.status == "planned" for item in results):
        return "Dry run only. Approve explicitly (--refresh --apply) to install."
    if needs_operator_action(results):
        return "Some integrations need operator action; no readiness stage is changed."
    return "Integration runtimes and configuration are present."


def render_results(results: list[IntegrationResult], *, as_json: bool = False) -> str:
    """Retain the legacy list renderer for direct Python callers."""

    if as_json:
        return json.dumps([asdict(item) for item in results], indent=2, sort_keys=True)
    lines = ["seshat integration setup"]
    lines.extend(
        f"[{item.status.upper()}] {item.name}: {item.detail}" for item in results
    )
    lines.append(_summary(results))
    return "\n".join(lines)


def confirm(question: str) -> bool:
    """A yes/no prompt that reads every non-answer -- including EOF -- as no."""

    try:
        answer = input(question).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in {"y", "yes"}
