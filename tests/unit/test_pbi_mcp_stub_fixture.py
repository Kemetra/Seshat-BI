"""Spec 149 T003 -- prove the stub fixture is derived, not hand-invented.

A fixture is only trustworthy if it cannot drift from the artifact it stands in
for. These tests pin that property itself: the stub payload must be byte-equal
to what the SHIPPED producer emits, and the stub transport must satisfy the
SHIPPED protocol. If either upstream shape changes, these fail -- which is the
whole point.
"""

from __future__ import annotations

import json

import pytest

from seshat.pbi_mcp import preflight
from tests.unit._pbi_mcp_stub import (
    STUB_GENERATED_AT,
    StubTransport,
    stub_preflight_payload,
    stub_preflight_result,
    stub_server,
)

pytestmark = pytest.mark.unit


def test_stub_payload_is_produced_by_the_shipped_renderer() -> None:
    """Byte-equality with the real producer -- the anti-circularity guarantee.

    If this fixture were hand-written, this assertion is what would fail the
    moment the artifact shape changed upstream.
    """
    expected = preflight.render_result_json(stub_preflight_result(), STUB_GENERATED_AT)
    assert stub_preflight_payload() == json.loads(expected)


def test_stub_payload_carries_the_shipped_authority_labels() -> None:
    """The artifact is derived evidence and says so -- never an approval."""
    payload = stub_preflight_payload()
    assert payload["authority"] == "derived-evidence-only"
    assert payload["readiness_effect"] == "none; named-human approval required"
    assert payload["schema_version"] == preflight.SCHEMA_VERSION


def test_stub_payload_carries_no_score() -> None:
    """Hard rule #9 at the fixture boundary.

    ``schema_version`` is an integer by design, so this asserts on the
    score-shaped names rather than on "no integers anywhere".
    """
    payload = stub_preflight_payload()
    for forbidden in ("score", "confidence", "maturity", "rating", "grade"):
        assert forbidden not in payload


def test_stub_transport_satisfies_the_shipped_protocol() -> None:
    """Structural conformance to ``McpTransport``.

    Asserted by USE, not by ``isinstance`` against a Protocol: calling
    ``describe()`` and getting a real ``ServerDescription`` back is the behavior
    the shipped preflight actually depends on.
    """
    transport = StubTransport()
    described = transport.describe()
    assert isinstance(described, preflight.ServerDescription)
    assert transport.calls == [("describe", {})]


def test_stub_server_protocol_version_is_one_the_shipped_module_supports() -> None:
    """The happy-path fixture must not be quietly incompatible."""
    assert stub_server().protocol_version in preflight.SUPPORTED_PROTOCOL_VERSIONS


def test_stub_transport_can_advertise_drifted_tools() -> None:
    """The seam US4 needs: perturb one field, leave the rest real."""
    drifted = StubTransport().with_tools(("unexpected_tool",))
    assert drifted.describe().tools == ("unexpected_tool",)
    assert StubTransport().describe().tools != ("unexpected_tool",)


def test_stub_transport_can_simulate_an_unavailable_runtime() -> None:
    """The shipped module raises ``RuntimeUnavailable``; the stub must too."""
    transport = StubTransport(fail_with=preflight.RuntimeUnavailable("no runtime"))
    with pytest.raises(preflight.RuntimeUnavailable):
        transport.describe()
