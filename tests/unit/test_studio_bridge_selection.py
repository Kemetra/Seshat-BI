"""T023/T023a: bridge selection and the alternate authentication mode (FR-013, FR-013a).

FR-013 forbids an AUTOMATIC switch to a billed path. FR-013a permits an API-key or
access-token bridge only as an EXPLICITLY operator-configured alternate, which must be
named in the interface and in `GET /bootstrap/state`, and is "never selected by
inference, by degradation, or as a response to any condition" in the failure table.

That is a fail-open shape: the dangerous version of this code is one where some
unhealthy state quietly falls through to the billed bridge. So the central test walks
EVERY health state the contract lists and asserts the selection is unchanged, and it
is proven by disabling only the guard -- a test that merely checks the happy path
would pass against an implementation that degrades.

The second risk is subtler: an operator who configures the alternate mode must not be
able to do so ACCIDENTALLY, and once active it must be visible. A silently-active
billed path is worse than a refused one.
"""

from __future__ import annotations

import pytest

from seshat.studio.bridge_selection import (
    AUTHENTICATION_MODES,
    AlternateAuthUnavailable,
    BridgeSelection,
    select_bridge,
)

pytestmark = pytest.mark.unit

#: Every condition in the contract's failure table, plus the healthy case.
ALL_HEALTH_STATES = (
    "healthy",
    "missing",
    "signed_out",
    "incompatible",
    "quota_limited",
    "crashed",
    "disabled",
)


def test_the_default_is_the_subscription_path() -> None:
    selection = select_bridge(health_state="healthy")
    assert selection.authentication_mode == "subscription"
    assert selection.uses_billed_path is False


@pytest.mark.parametrize("health_state", ALL_HEALTH_STATES)
@pytest.mark.parametrize("credential_present", [False, True])
def test_no_health_state_selects_the_billed_path_by_itself(
    health_state: str, credential_present: bool
) -> None:
    """FR-013, asserted over the whole failure table rather than a sample.

    Every row of that table is a state a naive implementation might treat as "the
    subscription is unusable, fall back" -- which is exactly the switch the contract
    forbids. Enumerating them means a future state added to the enum without a
    decision here fails loudly.

    `credential_present` is parametrized because the realistic fail-open needs BOTH
    an unhealthy state and an available key: an earlier version of this test passed
    only the default `False` and therefore missed a degradation branch that a single
    other test happened to catch. A guarantee this important should not depend on
    which test noticed.
    """
    selection = select_bridge(
        health_state=health_state, alternate_credential_present=credential_present
    )
    assert selection.authentication_mode == "subscription"
    assert selection.uses_billed_path is False


@pytest.mark.parametrize("health_state", ALL_HEALTH_STATES)
def test_degradation_does_not_select_the_alternate_even_when_configured(
    health_state: str,
) -> None:
    """The operator's configuration decides the mode; health never overrides it.

    Both directions matter. A configured alternate must not be silently abandoned
    when the subscription looks healthy, and -- the dangerous direction -- an
    unconfigured alternate must not be reached because the subscription is unhealthy.
    """
    unconfigured = select_bridge(health_state=health_state)
    assert unconfigured.authentication_mode == "subscription"

    configured = select_bridge(
        health_state=health_state,
        operator_configured_mode="operator_configured_alternate",
        alternate_credential_present=True,
    )
    assert configured.authentication_mode == "operator_configured_alternate"


def test_the_alternate_requires_an_explicit_operator_choice() -> None:
    """Presence of a credential is NOT a configuration.

    An environment that happens to carry an API key must not switch Studio to a
    billed path -- that is selection by inference, which the contract names
    explicitly.
    """
    selection = select_bridge(
        health_state="signed_out", alternate_credential_present=True
    )
    assert selection.authentication_mode == "subscription"
    assert selection.uses_billed_path is False


def test_configuring_the_alternate_without_a_credential_fails_closed() -> None:
    """Refuse rather than silently continuing on the subscription.

    Quietly ignoring the operator's stated intent would leave them believing they
    were on the alternate path while billing and rate limits behaved differently.
    """
    with pytest.raises(AlternateAuthUnavailable):
        select_bridge(
            health_state="healthy",
            operator_configured_mode="operator_configured_alternate",
            alternate_credential_present=False,
        )


def test_an_unknown_configured_mode_is_refused() -> None:
    with pytest.raises(ValueError):
        select_bridge(health_state="healthy", operator_configured_mode="free_lunch")


def test_the_active_alternate_is_named_and_flagged_as_billed() -> None:
    """FR-013a: when active it must be visible, not merely functional."""
    selection = select_bridge(
        health_state="healthy",
        operator_configured_mode="operator_configured_alternate",
        alternate_credential_present=True,
    )
    assert selection.authentication_mode == "operator_configured_alternate"
    assert selection.uses_billed_path is True
    assert "billed" in selection.disclosure.lower()


def test_the_subscription_mode_discloses_that_it_is_not_billed() -> None:
    selection = select_bridge(health_state="healthy")
    assert selection.disclosure
    assert "subscription" in selection.disclosure.lower()


def test_the_declared_modes_match_the_browser_contract() -> None:
    """`studio-ui/src/api/types.ts` pins these two literals."""
    assert AUTHENTICATION_MODES == ("subscription", "operator_configured_alternate")


def test_a_selection_is_immutable() -> None:
    """The mode must not be mutable after the fact by a later code path."""
    selection = select_bridge(health_state="healthy")
    with pytest.raises((AttributeError, TypeError)):
        selection.authentication_mode = "operator_configured_alternate"  # type: ignore[misc]


def test_selection_is_a_pure_function_of_its_stated_inputs() -> None:
    """No environment read, no global. Same inputs, same answer, every time.

    A selector that consulted `os.environ` directly could change its mind between
    two calls in one process -- which is how "never by inference" quietly becomes
    "usually not by inference".
    """
    first = select_bridge(health_state="quota_limited")
    second = select_bridge(health_state="quota_limited")
    assert first == second
    assert isinstance(first, BridgeSelection)
