"""T031 -- Codex launches fully; Claude stays deterministic-site + native handoff.

Spec 139 FR-029: Claude Code launch MUST remain a deterministic-site and
native-handoff integration, and Foundation MUST NOT embed or route Claude
subscription credentials.

**What these tests prove, and what they do not.** This is an ABSENCE-OF-SURFACE
proof, not a runtime credential audit. They assert that no code path exists through
which Studio could select, spawn, or authenticate a Claude provider -- because the
provider set is a closed enum with two members and every entry point validates
against it. They do NOT observe a live process and cannot prove that some future
transitive dependency never reads an Anthropic variable.

The assertions are written as pins on the CLOSED ENUM rather than as a text search
for "claude" or "anthropic" in the sources. A string grep passes trivially today and
would keep passing if a Claude provider were added under any other name; the enum
assertions fail the moment a third provider appears anywhere in the chain. That is
the property FR-029 actually needs.
"""

from __future__ import annotations

import argparse

import pytest

from seshat.studio import __main__ as studio_main
from seshat.studio import bridge_selection

# FR-029: Codex is the one full-launch provider; `fake` is the deterministic
# bridge. Neither is Claude, and no third member is permitted.
EXPECTED_PROVIDERS = {"fake", "codex"}


# --------------------------------------------------------------------------- #
# The closed provider enum, at every layer that could widen it                 #
# --------------------------------------------------------------------------- #


def test_agent_providers_is_exactly_the_two_permitted_values() -> None:
    """The authority. A Claude provider would have to appear here first."""
    assert set(bridge_selection.AGENT_PROVIDERS) == EXPECTED_PROVIDERS
    assert len(bridge_selection.AGENT_PROVIDERS) == 2


def test_the_launcher_flag_offers_no_third_provider() -> None:
    """`--agent` is the operator-facing surface; it must not widen the enum.

    Read off the built parser rather than the module source, so a divergence
    between the declared choices and the authority is caught rather than assumed.
    """
    parser = studio_main._build_parser()
    agent_action = next(
        action
        for action in parser._actions
        if isinstance(action, argparse.Action) and "--agent" in action.option_strings
    )

    assert set(agent_action.choices) == EXPECTED_PROVIDERS
    assert set(agent_action.choices) == set(bridge_selection.AGENT_PROVIDERS), (
        "the launcher flag and the provider authority disagree"
    )


@pytest.mark.parametrize("provider", ["claude", "claude-code", "anthropic"])
def test_selecting_a_claude_provider_is_refused(provider: str) -> None:
    """No Claude spelling resolves; each is refused by the closed-enum guard."""
    with pytest.raises(ValueError, match="unknown agent provider"):
        bridge_selection.select_provider(
            configured_provider=provider,
            executable="/usr/bin/claude",
            version="1.0.0",
            version_is_tested=True,
        )


def test_a_present_claude_executable_does_not_create_a_provider() -> None:
    """Presence is not consent, and presence is not a provider either.

    The dangerous shape is an installed Claude CLI being treated as an available
    backend. `select_provider` takes the executable as an argument and still
    refuses, because the provider name -- not the binary on disk -- decides.
    """
    with pytest.raises(ValueError):
        bridge_selection.select_provider(
            configured_provider="claude",
            executable="/usr/local/bin/claude",
            version="2.0.0",
            version_is_tested=True,
        )


# --------------------------------------------------------------------------- #
# Codex launches fully; the deterministic bridge stays the default             #
# --------------------------------------------------------------------------- #


def test_codex_is_selectable_as_a_full_launch_provider() -> None:
    """The Codex lane is genuinely reachable -- the enum is closed, not empty."""
    selection = bridge_selection.select_provider(
        configured_provider="codex",
        executable="/usr/local/bin/codex",
        version="0.20.0",
        version_is_tested=True,
    )

    assert selection.provider == "codex"


def test_the_default_agent_is_the_deterministic_bridge() -> None:
    """FR-029's deterministic site: no provider is engaged without being asked."""
    parsed = studio_main._build_parser().parse_args([])

    assert parsed.agent == "fake"


def test_the_deterministic_bridge_needs_no_provider_credential() -> None:
    """The deterministic lane resolves with no executable and no version at all."""
    selection = bridge_selection.select_provider(
        configured_provider="fake",
        executable=None,
        version=None,
        version_is_tested=False,
    )

    assert selection.provider == "fake"


# --------------------------------------------------------------------------- #
# No Claude credential bridge                                                  #
# --------------------------------------------------------------------------- #


def test_authentication_modes_describe_no_claude_subscription() -> None:
    """The two modes are provider-agnostic; neither names a Claude credential.

    FR-029 forbids embedding or ROUTING a Claude subscription credential. The
    authentication surface has exactly two modes, and the alternate one is the
    operator-configured billed path for the Codex lane -- there is no third mode
    into which a Claude credential could be routed.
    """
    assert set(bridge_selection.AUTHENTICATION_MODES) == {
        "subscription",
        "operator_configured_alternate",
    }


def test_no_claude_credential_environment_is_read_by_selection() -> None:
    """Selection is a pure function of its arguments, so no credential leaks in.

    Setting every plausible Anthropic credential variable changes nothing: the
    selector reads no environment, which is what makes "never by inference"
    structural rather than a convention.
    """
    import os
    from unittest import mock

    poisoned = {
        "ANTHROPIC_API_KEY": "sk-ant-should-never-be-read",
        "CLAUDE_API_KEY": "should-never-be-read",
        "CLAUDE_CODE_OAUTH_TOKEN": "should-never-be-read",
    }
    with mock.patch.dict(os.environ, poisoned, clear=False):
        with pytest.raises(ValueError):
            bridge_selection.select_provider(
                configured_provider="claude",
                executable=None,
                version=None,
                version_is_tested=False,
            )
        still_fake = bridge_selection.select_provider(
            configured_provider="fake",
            executable=None,
            version=None,
            version_is_tested=False,
        )

    assert still_fake.provider == "fake"
