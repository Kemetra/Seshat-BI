/**
 * The technical approval panel (T026; FR-019, FR-020, FR-021, FR-022, FR-031).
 *
 * An approval is the one streamed event the analyst can ACT on, so it gets a component
 * rather than a row of activity prose.
 *
 * **The allow control is ABSENT, not disabled, when readiness forbids the scope.**
 * FR-021 asks that no allow control be OFFERED, and a greyed-out button is still an
 * offer: it says "you could allow this if something changed", which is a claim about
 * governance nobody made. `mayAllow` decides whether the control exists in the DOM at
 * all. The server refuses with a 403 regardless -- that is the authority -- but a
 * control that appears and then fails is exactly the present-then-retract shape the
 * requirement forbids.
 *
 * **Deny is always available, including for a named-human ruling.** This asymmetry is
 * deliberate and mirrors the server (`approval_delivery.py`): refusing to GRANT a
 * governance ruling Studio may not make is different from refusing to ANSWER the
 * provider, and an unanswered request blocks the turn either way. So a `named_human`
 * item renders as a prepared summary with Deny only, and says who can decide it.
 *
 * **The browser performs no side effect (FR-020).** One POST carrying a decision. The
 * one-time property belongs to the server's ledger -- the in-flight disable here only
 * stops a double-submit, and the authoritative refusal of a replay is the 409.
 */

import { useState } from "react";

import { StudioRequestError, respondToToolApproval } from "../api/client";
import type { ApprovalDecision } from "../api/client";
import { mayAllow } from "../api/approvalPayload";
import type { Approval } from "../api/approvalPayload";
import "./ApprovalPanel.css";

/**
 * What the analyst is told for each failure.
 *
 * A CLOSED lookup rather than a status-code transform: two of these codes are absent
 * from the OpenAPI (422, 502), and 502 in particular must never read as retryable --
 * the decision was recorded, the id is spent, and the provider was never answered.
 */
const FAILURE_MESSAGES: Record<number, string> = {
  403: "This decision is not Studio's to grant.",
  404: "This conversation is no longer available.",
  409: "This approval is no longer awaiting a decision.",
  422: "Studio sent a decision the server did not recognise.",
  502: "The decision was recorded but never reached the agent, so this turn cannot continue. It cannot be sent again.",
};

/** What the analyst can DO about each failure, when there is anything. */
const FAILURE_RECOVERY: Record<number, string> = {
  409: "Another decision may already have been made. Reload to see the current state.",
  502: "Start a new conversation; this approval cannot be decided again.",
  422: "Reload Studio. If it recurs, this is a defect worth reporting.",
};

interface ApprovalPanelProps {
  approval: Approval;
  threadId: string;
  /**
   * The event sequence this panel was rendered from, used only to build a unique DOM id.
   *
   * NOT the approval id: a provider may re-request the same `itemId`, and two panels
   * sharing a heading id make `aria-labelledby` resolve to the FIRST match -- so the
   * second approval would be announced to a screen reader with the first one's heading.
   * The sequence is server-assigned and unique per event, which is exactly the property
   * a DOM id needs.
   */
  domKey: string | number;
}

export function ApprovalPanel({ approval, threadId, domKey }: ApprovalPanelProps) {
  const [decided, setDecided] = useState<ApprovalDecision | null>(null);
  const [failure, setFailure] = useState<{ text: string; recovery: string | null } | null>(
    null,
  );
  const [inFlight, setInFlight] = useState(false);

  async function decide(decision: ApprovalDecision) {
    setInFlight(true);
    setFailure(null);
    try {
      await respondToToolApproval(threadId, approval.approvalId, decision);
      setDecided(decision);
    } catch (error) {
      setFailure(describeFailure(error));
    } finally {
      setInFlight(false);
    }
  }

  const heading = approval.question ?? "The agent is asking permission.";

  return (
    <section
      className="approval"
      // `status` rather than `alert`: the codebase reserves `alert` for failures and
      // uses `status` for a state that needs attention. An approval is a pause, not a
      // fault -- and a paused turn waiting on a person is the NORMAL case here.
      role="status"
      aria-labelledby={`approval-heading-${domKey}`}
    >
      <h3 className="approval__heading" id={`approval-heading-${domKey}`}>
        {heading}
      </h3>

      <ApprovalScope approval={approval} />

      {!approval.technical && (
        <p className="approval__authority">
          A named human must decide this. Studio can decline it, but cannot grant it.
        </p>
      )}

      {approval.technical && !approval.allowPermitted && (
        <ForbiddenReasons reasons={approval.forbiddenReasons} />
      )}

      {decided !== null ? (
        <p className="approval__decided">
          {decided === "allow_once" ? "Allowed once." : "Declined."}
        </p>
      ) : (
        <div className="approval__controls">
          {/* ABSENT, not disabled, when readiness forbids the scope. */}
          {mayAllow(approval) && (
            <button
              type="button"
              className="approval__allow"
              disabled={inFlight}
              onClick={() => void decide("allow_once")}
            >
              Allow once
            </button>
          )}
          <button
            type="button"
            className="approval__deny"
            disabled={inFlight}
            onClick={() => void decide("deny")}
          >
            Decline
          </button>
        </div>
      )}

      {failure !== null && (
        <p className="approval__failure" role="alert">
          {failure.text}
          {failure.recovery !== null && ` ${failure.recovery}`}
        </p>
      )}
    </section>
  );
}

/**
 * The exact scope, field by field (T024).
 *
 * Every field is omitted when the producer did not send it. A row reading "Scope: —"
 * would state that the scope is unknown in the visual language of a stated scope, and
 * the analyst is being asked to permit precisely this.
 */
function ApprovalScope({ approval }: { approval: Approval }) {
  const rows: Array<[string, string]> = [];
  if (approval.action !== undefined) rows.push(["Action", approval.action]);
  if (approval.target !== undefined) rows.push(["Target", approval.target]);
  if (approval.scope !== undefined) rows.push(["Scope", approval.scope]);
  if (approval.reason !== undefined) rows.push(["Reason", approval.reason]);

  if (rows.length === 0 && approval.risk === undefined) {
    return null;
  }

  return (
    <>
      {rows.length > 0 && (
        <dl className="approval__scope">
          {rows.map(([label, value]) => (
            <div className="approval__scope-row" key={label}>
              <dt className="approval__scope-term">{label}</dt>
              <dd className="approval__scope-value">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {approval.risk !== undefined && <RiskBadge risk={approval.risk} />}
    </>
  );
}

/** Risk, carried by glyph and text as well as colour (FR-031, WCAG 2.2 AA). */
function RiskBadge({ risk }: { risk: string }) {
  const high = risk === "high";
  return (
    <p className={`approval__risk approval__risk--${high ? "high" : "normal"}`}>
      <span className="approval__risk-glyph" aria-hidden="true">
        {high ? "!" : "·"}
      </span>
      <span className="approval__risk-label">{high ? "High risk" : `Risk: ${risk}`}</span>
      {high && (
        <span className="visually-hidden">
          This request escalates privileges beyond the current turn.
        </span>
      )}
    </p>
  );
}

/** Why an allow is refused, in the sentences the readiness gate itself produced. */
function ForbiddenReasons({ reasons }: { reasons: string[] }) {
  if (reasons.length === 0) {
    // Refused with no stated reason: say that, rather than rendering an empty list that
    // reads as "nothing forbids this".
    return (
      <p className="approval__forbidden">
        Studio cannot grant this, and the readiness gate gave no reason.
      </p>
    );
  }
  return (
    <div className="approval__forbidden">
      <p className="approval__forbidden-lead">Studio cannot grant this:</p>
      <ul className="approval__forbidden-list">
        {reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </div>
  );
}

/** A thrown error as something the analyst can read and act on. */
function describeFailure(error: unknown): { text: string; recovery: string | null } {
  if (error instanceof StudioRequestError) {
    const text =
      FAILURE_MESSAGES[error.status] ?? "The decision could not be recorded.";
    // The server's own recovery sentence wins when it sent one: it is redacted, specific
    // to this workspace, and closer to the failure than any constant here.
    return { text, recovery: error.recoveryAction ?? FAILURE_RECOVERY[error.status] ?? null };
  }
  return {
    text: "The decision could not be sent.",
    recovery: "Check that Studio is still running, then try again.",
  };
}
