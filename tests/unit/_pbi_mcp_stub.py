"""Spec 149 T003 -- the stubbed MCP runtime, derived from the SHIPPED shape.

Why this module exists rather than a hand-written JSON blob: a fixture invented
from an assumption about the artifact shape proves only that the code agrees
with the assumption. When the real producer changes, the hand-written blob keeps
passing while diverging from reality -- the circular-fixture defect this repo has
already paid for.

So the canonical preflight payload here is produced by calling the shipped
``preflight.render_result_json`` on a real ``PreflightResult``. If the producer's
shape changes, this fixture changes with it, and any test pinned to the old
shape fails loudly instead of silently lying.

The stub transport implements the shipped ``McpTransport`` protocol. It never
starts a process, never touches a network, and never needs a tenant -- acceptance
for slice 5 is provable offline (Principle VIII).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any

from seshat.pbi_mcp import preflight

# A capability set that matches what the shipped preflight expects to find. Kept
# as data rather than literals inside tests so a drift test can perturb exactly
# one field (US4 / T037) without re-inventing the whole record.
STUB_SERVER_NAME = "powerbi-modeling-mcp"
STUB_SERVER_VERSION = "0.0.0-preview"
STUB_TOOLS: tuple[str, ...] = (
    "list_tables",
    "list_measures",
    "update_measure",
)

# Deterministic: never ``datetime.now()`` in a fixture, or the artifact differs
# between runs and cannot be byte-compared.
STUB_GENERATED_AT = "2026-08-18T00:00:00Z"


def stub_server(
    *,
    name: str = STUB_SERVER_NAME,
    version: str = STUB_SERVER_VERSION,
    protocol_version: str | None = None,
    tools: tuple[str, ...] = STUB_TOOLS,
) -> preflight.ServerDescription:
    """Build a real ``ServerDescription`` -- the shipped dataclass, not a mock.

    ``protocol_version`` defaults to the first value the shipped module declares
    supported, so the happy path stays green when that list is edited upstream.
    """
    if protocol_version is None:
        protocol_version = preflight.SUPPORTED_PROTOCOL_VERSIONS[0]
    return preflight.ServerDescription(
        name=name,
        version=version,
        protocol_version=protocol_version,
        tools=tools,
    )


@dataclass(frozen=True)
class PreflightSpec:
    """What a stubbed preflight result should say. Happy path by default."""

    status: str = preflight.STATUS_OK
    mode: str = "read-only"
    server: preflight.ServerDescription | None = None
    target: str | None = "sales_model"
    target_allowlisted: bool | None = True
    blockers: tuple[preflight.PreflightBlocker, ...] = ()
    capabilities_verified: bool = True


def stub_preflight_result(**overrides: object) -> preflight.PreflightResult:
    """A real ``PreflightResult`` on the happy path, overridable per test."""
    spec = PreflightSpec(**overrides)  # type: ignore[arg-type]
    resolved_server = stub_server() if spec.server is None else spec.server
    return preflight.PreflightResult(
        status=spec.status,
        mode=spec.mode,
        server=resolved_server,
        tools_present=resolved_server.tools,
        tools_missing=(),
        target=spec.target,
        target_allowlisted=spec.target_allowlisted,
        blockers=spec.blockers,
        notes=(),
        capabilities_verified=spec.capabilities_verified,
    )


def stub_preflight_payload(**kwargs: Any) -> dict[str, Any]:
    """The preflight artifact as a dict, rendered by the SHIPPED producer.

    This is the anti-circularity hinge: the bytes come from
    ``preflight.render_result_json``, so the fixture cannot drift away from the
    real artifact shape without this function changing too.
    """
    result = stub_preflight_result(**kwargs)
    return json.loads(preflight.render_result_json(result, STUB_GENERATED_AT))


@dataclass
class StubTransport:
    """A ``McpTransport`` that answers from memory.

    Records every call so a test can assert what the adapter actually asked for
    -- notably that no bypass flag was ever constructed (T028).
    """

    server: preflight.ServerDescription = field(default_factory=stub_server)
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    fail_with: Exception | None = None

    def describe(self) -> preflight.ServerDescription:
        self.calls.append(("describe", {}))
        if self.fail_with is not None:
            raise self.fail_with
        return self.server

    def with_tools(self, tools: tuple[str, ...]) -> StubTransport:
        """Return a copy advertising a different tool set (drift tests)."""
        return replace(self, server=replace(self.server, tools=tools))
