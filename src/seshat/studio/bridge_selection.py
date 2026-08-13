"""Which authentication mode a bridge runs under (T023a, FR-013 / FR-013a).

The subscription path is the default and the only one Studio certifies. An API-key or
access-token bridge is permitted, but ONLY as an explicitly operator-configured
alternate -- never reached by inference, by degradation, or as a response to any
health state.

**Health is not an input to the decision, and that is the whole point.** It is passed
in so this module can be tested across the entire failure table, but no branch reads
it. The dangerous implementation is the plausible one: `signed_out` or `quota_limited`
looks exactly like "the subscription is unusable, fall back to the key we have" --
which silently moves an operator onto a billed path they never chose. Every one of
those states stays a REPORTED condition with a recovery action.

**A present credential is not a configuration.** An environment that happens to carry
`OPENAI_API_KEY` must not flip the mode; that is selection by inference. The operator
has to say so, and if they say so without a credential this fails closed rather than
quietly continuing on the subscription -- otherwise they would believe they were on
the alternate path while billing behaved differently.

**Pure function, no environment reads.** Everything is an argument. A selector that
consulted `os.environ` itself could answer differently between two calls in one
process, which is how "never by inference" degrades into "usually not by inference".
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AGENT_PROVIDERS",
    "AUTHENTICATION_MODES",
    "AlternateAuthUnavailable",
    "BridgeSelection",
    "ProviderSelection",
    "select_bridge",
    "select_provider",
]

#: The two literals `studio-ui/src/api/types.ts` pins for `authentication_mode`.
AUTHENTICATION_MODES: tuple[str, ...] = (
    "subscription",
    "operator_configured_alternate",
)

_SUBSCRIPTION_DISCLOSURE = (
    "Signed in through the Codex subscription. Studio never handles the credential "
    "and no request is billed per token."
)

_ALTERNATE_DISCLOSURE = (
    "Running on the operator-configured alternate credential. This is a BILLED path: "
    "requests are charged per token rather than covered by a subscription. Studio "
    "certifies only the subscription path."
)


class AlternateAuthUnavailable(RuntimeError):
    """The alternate mode was configured but no credential was supplied."""


@dataclass(frozen=True, slots=True)
class BridgeSelection:
    """The chosen mode, with the disclosure the interface must show."""

    authentication_mode: str
    uses_billed_path: bool
    disclosure: str


def select_bridge(
    *,
    health_state: str,
    operator_configured_mode: str | None = None,
    alternate_credential_present: bool = False,
) -> BridgeSelection:
    """Choose the authentication mode for this bridge.

    `health_state` is accepted and deliberately UNUSED. It is part of the signature so
    that a caller cannot pass health "for the selector to consider", and so the test
    suite can walk the whole failure table asserting the answer never moves. Deleting
    the parameter would make that guarantee untestable at this seam.
    """
    del health_state  # never an input to this decision -- see the module docstring

    if operator_configured_mode is None or operator_configured_mode == "subscription":
        # A present credential is intentionally ignored here. Reading it would be
        # exactly the inference FR-013a forbids.
        return BridgeSelection(
            authentication_mode="subscription",
            uses_billed_path=False,
            disclosure=_SUBSCRIPTION_DISCLOSURE,
        )

    if operator_configured_mode not in AUTHENTICATION_MODES:
        raise ValueError(
            f"unknown authentication mode {operator_configured_mode!r}; expected one "
            f"of {list(AUTHENTICATION_MODES)}"
        )

    if not alternate_credential_present:
        raise AlternateAuthUnavailable(
            "the alternate authentication mode is configured but no credential was "
            "supplied. Studio refuses rather than silently continuing on the "
            "subscription, which would misreport which path is billed."
        )

    return BridgeSelection(
        authentication_mode="operator_configured_alternate",
        uses_billed_path=True,
        disclosure=_ALTERNATE_DISCLOSURE,
    )


#: The agent implementations Studio can run. `fake` is the deterministic bridge that
#: needs nothing installed; `codex` is the live app-server.
AGENT_PROVIDERS: tuple[str, ...] = ("fake", "codex")


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    """Which agent implementation runs, and why -- reported, never inferred."""

    provider: str
    detail: str


def select_provider(
    *,
    configured_provider: str,
    executable: str | None,
    version: str | None,
    version_is_tested: bool,
) -> ProviderSelection:
    """Choose the agent implementation for this process.

    Every input is an ARGUMENT: this reads no environment and runs no subprocess, so
    two calls in one process cannot disagree. The caller probes once at startup and
    the answer is pinned for the process's lifetime.

    Three ways a configured Codex bridge degrades to the fake, and each REPORTS a
    reason rather than degrading silently. A silent fallback is the dangerous shape:
    the operator sees a working Studio, believes Codex is answering, and gets
    deterministic fake text instead -- indistinguishable from a real reply until it
    matters.

    An untested version is refused rather than attempted. The compatibility contract
    is explicit that semver proximity is not compatibility evidence: a build outside
    the recorded range is `incompatible` until its generated schema and handshake
    fixtures pass.
    """
    if configured_provider not in AGENT_PROVIDERS:
        raise ValueError(
            f"unknown agent provider {configured_provider!r}; expected one of "
            f"{list(AGENT_PROVIDERS)}"
        )

    if configured_provider == "fake":
        # NOT a fallback: this is what an operator who configured nothing asked for.
        # An installed CLI is deliberately not consulted -- presence is not consent.
        return ProviderSelection(
            provider="fake",
            detail="The deterministic bridge is configured; no agent CLI is used.",
        )

    if executable is None:
        return ProviderSelection(
            provider="fake",
            detail=(
                "Codex is configured but the CLI was not found on PATH, so agent "
                "turns are refused. Install the Codex CLI and restart; deterministic "
                "workspace views remain fully usable meanwhile."
            ),
        )

    if not version_is_tested:
        observed = version or "an unreadable version"
        return ProviderSelection(
            provider="fake",
            detail=(
                f"Codex reports {observed}, which is outside the range Studio has "
                "exercised, so agent turns are refused rather than run against an "
                "unverified protocol. Deterministic workspace views remain fully "
                "usable meanwhile."
            ),
        )

    return ProviderSelection(
        provider="codex",
        detail=f"Codex {version} is driving turns.",
    )
