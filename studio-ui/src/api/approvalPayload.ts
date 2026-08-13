/**
 * Narrowing for the `approval_required` payload (T024, FR-018..FR-022).
 *
 * Separate from `eventPayload.ts` because an approval is the one event the analyst can
 * ACT on, so its payload is read far more strictly than a display label: the difference
 * between "no scope stated" and "scope: read_only" decides whether a control appears.
 *
 * Two producers emit this event and they do not agree. The fake bridge sends
 * `{approval_id, question, required_authority}`. Real Codex sends
 * `{approval_id, required_authority, action, target, reason, scope, risk}` and **no
 * `question`**. Narrowing therefore treats every display field as optional and never
 * depends on one producer's shape -- an approval that renders only under the fake would
 * be a panel that works in tests and blanks in production.
 *
 * The governing rule is `eventPayload.ts`'s, applied where it matters most: **an absent
 * or malformed field yields nothing, never a placeholder.** A fabricated scope on an
 * approval is not a cosmetic defect; it is a claim about what the analyst is permitting.
 */

import { text } from "./eventPayload";
import type { StudioEvent } from "./types";

/** The authority Studio may itself decide. Anything else is a named-human ruling. */
export const TECHNICAL = "technical";

/** One approval, as the panel needs it. */
export interface Approval {
  approvalId: string;
  /** True only when Studio may offer an allow control at all. */
  allowPermitted: boolean;
  /** Why an allow is refused, in the governance sentences readiness produced. */
  forbiddenReasons: string[];
  /** True when this is Studio's to decide; false for a named-human ruling. */
  technical: boolean;
  /** Display fields. Each is absent rather than invented when the producer omits it. */
  action: string | undefined;
  target: string | undefined;
  reason: string | undefined;
  scope: string | undefined;
  risk: string | undefined;
  question: string | undefined;
}

/**
 * One approval from a streamed event, or `undefined` if it carries no id.
 *
 * The id is the only field that is genuinely required: without it there is nothing to
 * POST a decision against, so rendering a panel would offer controls that cannot work.
 * Everything else degrades to absent.
 */
export function approvalFromEvent(event: StudioEvent): Approval | undefined {
  const payload = event.payload;
  const approvalId = text(payload, "approval_id");
  if (approvalId === undefined) {
    return undefined;
  }

  return {
    approvalId,
    // Fails CLOSED: anything other than an explicit `true` withholds the control. A
    // payload from an older server that predates this field must not be read as
    // permission, and `Boolean(undefined)` would be the same answer for the wrong
    // reason -- this states the intent.
    allowPermitted: payload["allow_permitted"] === true,
    forbiddenReasons: sentences(payload["forbidden_reasons"]),
    technical: payload["required_authority"] === TECHNICAL,
    action: text(payload, "action"),
    target: text(payload, "target"),
    reason: text(payload, "reason"),
    scope: text(payload, "scope"),
    risk: text(payload, "risk"),
    question: text(payload, "question"),
  };
}

/** The non-empty strings from an opaque list, or an empty list. */
function sentences(raw: unknown): string[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter(
    (entry): entry is string => typeof entry === "string" && entry.trim() !== "",
  );
}

/**
 * Whether an allow control may be RENDERED for this approval (FR-021).
 *
 * Both conditions, restated on the client rather than inferred from one flag. The server
 * is the authority and refuses with a 403 regardless -- but a control that appears and
 * then fails is precisely what FR-021 forbids, and reading `allowPermitted` alone would
 * let a future server bug that sets it on a `named_human` item put an Allow button in
 * front of a governance ruling.
 */
export function mayAllow(approval: Approval): boolean {
  return approval.technical && approval.allowPermitted;
}
