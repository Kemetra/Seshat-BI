/**
 * Narrowing helpers for `StudioEvent.payload`.
 *
 * The contract declares `payload` an open object (`type: object`), so the generated TS
 * type is `Record<string, unknown>` and every field has to be narrowed explicitly. That
 * work is genuinely separate from rendering, and putting it here keeps the component file
 * about the component: `Conversation.tsx` had accumulated payload parsing, stream
 * lifecycle, and presentation, which pushed its mean complexity past the health gate.
 *
 * The rule these helpers share: **an absent or malformed field yields nothing, never a
 * placeholder.** A blank row, an "undefined" label, or a fabricated status is a claim
 * nobody made, and in a governance tool an invented claim is worse than a missing one.
 */

import type { StudioEvent } from "./types";

/** Shown when an activity event carries no public label. */
export const NEUTRAL_ACTIVITY_LABEL = "Working…";

/** A non-empty string field from an opaque payload, or `undefined`. */
export function text(
  payload: Record<string, unknown>,
  key: string,
): string | undefined {
  const value = payload[key];
  return typeof value === "string" && value.trim() !== "" ? value : undefined;
}

/** One plan step, as the UI needs it. */
export interface PlanStep {
  label: string;
  state: string;
}

/** One step, or nothing if it carries no label. */
function planStep(candidate: unknown): PlanStep[] {
  if (typeof candidate !== "object" || candidate === null) {
    return [];
  }
  const step = candidate as Record<string, unknown>;
  const label = text(step, "label");
  if (label === undefined) {
    return [];
  }
  // `state` falls back to a neutral word rather than inventing progress.
  return [{ label, state: text(step, "state") ?? "planned" }];
}

/**
 * The plan steps in a `plan_updated` payload.
 *
 * A step missing its `label` is DROPPED rather than rendered as "undefined": a plan is a
 * claim about what the agent will do, and a blank row is a claim nobody made. A non-list
 * `steps` yields nothing instead of throwing -- throwing would unmount the whole
 * conversation, which is the FR-025 failure this feature already shipped once with an
 * out-of-enum `agent_health`.
 */
export function planSteps(payload: Record<string, unknown>): PlanStep[] {
  const raw = payload["steps"];
  return Array.isArray(raw) ? raw.flatMap(planStep) : [];
}

/**
 * The public description of one activity event (FR-032).
 *
 * Never consults `name`. The `?? payload.name` spelling looks defensive and IS the leak:
 * a provider that omits `public_label` would put `grep_secrets` on the primary journey.
 * An unlabelled event still gets a row, because hiding it would make the agent look idle
 * while it worked.
 */
export function activityLabel(event: StudioEvent): string {
  const payload = event.payload;
  switch (event.type) {
    case "approval_required":
      return text(payload, "question") ?? "A decision is being prepared.";
    case "file_change_proposed":
      return text(payload, "summary") ?? "A file change was drafted.";
    case "plan_updated":
      return planLabel(payload);
    case "connection_state":
      return text(payload, "public_label") ?? "Connection state changed.";
    default:
      return text(payload, "public_label") ?? NEUTRAL_ACTIVITY_LABEL;
  }
}

/** The step COUNT, so a three-step plan does not read like a one-step plan. */
function planLabel(payload: Record<string, unknown>): string {
  const count = planSteps(payload).length;
  return count > 0 ? `Updated the plan (${count} steps).` : "Updated the plan.";
}
