/**
 * The seven agent health presentations (T014, FR-024, FR-025).
 *
 * FR-024: each state must be DISTINCT and carry a recovery action. Distinct means a
 * different headline and a different explanation, not one banner whose colour changes --
 * an analyst who cannot tell "signed out" from "quota limited" cannot act on either.
 *
 * FR-025: deterministic workspace views stay available in EVERY state, so this component
 * is strictly additive. It renders a notice; it never replaces, blocks, or wraps the
 * workspace, and it has no error path that could swallow the page.
 *
 * `role="status"` (implicitly `aria-live="polite"`) rather than `alert`: agent health is
 * context, not an emergency, and interrupting a screen-reader user mid-sentence for it
 * would be hostile.
 */

import type * as React from "react";

import type { AgentHealth } from "../api/types";
import "./AgentHealth.css";

type State = AgentHealth["state"];

/**
 * Local wording per state.
 *
 * The server's `summary`/`recovery_action` are preferred when present -- it knows more
 * about why a bridge failed than the browser does. These are the fallback, and they are
 * also what makes each state distinguishable when a server sends terse text.
 */
const PRESENTATION: Record<State, { headline: string; detail: string; recovery: string }> =
  {
    healthy: {
      headline: "Seshat is ready",
      detail: "The agent is signed in and responding.",
      recovery: "Nothing to do.",
    },
    missing: {
      headline: "Seshat is not installed here",
      detail: "No agent executable was found in this environment.",
      recovery: "Install the agent, then reopen Studio.",
    },
    signed_out: {
      headline: "Seshat is signed out",
      detail: "The agent is installed but has no active session.",
      recovery: "Sign in through the agent's own login, then reload this page.",
    },
    incompatible: {
      headline: "This agent version is not supported",
      detail:
        "The installed agent speaks a protocol Studio has not been tested against.",
      recovery: "Move to a supported agent version, then reopen Studio.",
    },
    quota_limited: {
      headline: "Seshat has reached its usage limit",
      detail: "The agent is signed in but currently cannot take new work.",
      recovery: "Wait for the limit to reset, or use a plan with more capacity.",
    },
    crashed: {
      headline: "Seshat stopped unexpectedly",
      detail: "The agent process ended while Studio was connected.",
      recovery: "Reopen Studio to start a fresh agent session.",
    },
    disabled: {
      headline: "Asking Seshat is not part of this version",
      detail: "This build reads the workspace only.",
      recovery: "Everything on this page works without the agent.",
    },
  };

/** Prefer the server's wording, but never render blank text because it sent blank. */
function orFallback(fromServer: string, fallback: string): string {
  return fromServer.trim().length > 0 ? fromServer : fallback;
}

export function AgentHealthNotice({
  health,
}: {
  health: AgentHealth;
}): React.JSX.Element {
  const local = PRESENTATION[health.state];
  return (
    <p
      role="status"
      data-agent-state={health.state}
      className="agent-health"
    >
      <strong className="agent-health__headline">{local.headline}</strong>{" "}
      <span className="agent-health__detail">
        {orFallback(health.summary, local.detail)}
      </span>{" "}
      <span className="agent-health__recovery" data-testid="agent-recovery">
        {orFallback(health.recovery_action, local.recovery)}
      </span>
      {health.version !== null && (
        // FR-032: a version string is technical detail, not primary journey wording.
        <details className="agent-health__detail-disclosure">
          <summary>Technical detail</summary>
          <span>
            {health.provider} {health.version}
          </span>
        </details>
      )}
    </p>
  );
}
