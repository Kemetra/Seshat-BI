/**
 * The chat surface: composer, streamed activity, and reconnect (FR-023, FR-032).
 *
 * Three decisions carry the weight, each because the obvious alternative fails:
 *
 * **Events are keyed by `sequence`, not by arrival.** Studio's `/events` endpoint is a
 * finite replay, so the browser reconnects constantly and MAY redeliver the boundary
 * event. Appending whatever arrives would duplicate messages on every poll; keying on the
 * server-assigned sequence makes redelivery idempotent.
 *
 * **A tool without a `public_label` falls back to a neutral phrase, never to `name`.**
 * The `?? payload.name` spelling looks defensive and IS the leak: a provider that omits
 * the label would put `grep_secrets` on the primary journey, which FR-032 forbids.
 *
 * **A failed send keeps the draft.** Clearing on submit is simpler and loses the user's
 * text at the exact moment they need it back.
 *
 * `approval_required` and `file_change_proposed` render as inert activity. Their
 * semantics are Phase 6 (T024-T027); offering a control now would let someone believe
 * they had approved something.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { StudioEvent } from "../api/types";
import "./Conversation.css";

/** Shown when an activity event carries no public label. */
const NEUTRAL_ACTIVITY_LABEL = "Working…";

/** Event types rendered as the agent's prose. */
const MESSAGE_TYPES = new Set(["agent_message"]);

/** Event types rendered as public activity rather than prose. */
const ACTIVITY_TYPES = new Set([
  "plan_updated",
  "tool_started",
  "tool_completed",
  "file_change_proposed",
  "approval_required",
  "connection_state",
]);

export interface ConversationProps {
  threadId: string;
  /** Injected so a test can drive the failure path without a live server. */
  startTurn: (threadId: string, prompt: string) => Promise<{ turn_id: string }>;
}

/** A string field from an opaque payload, or `undefined`. */
function text(payload: Record<string, unknown>, key: string): string | undefined {
  const value = payload[key];
  return typeof value === "string" && value.trim() !== "" ? value : undefined;
}

/**
 * The public description of one activity event.
 *
 * Never consults `name`: see the module docstring. An unlabelled event still gets a row,
 * because hiding it would make the agent look idle while it worked.
 */
export function activityLabel(event: StudioEvent): string {
  const payload = event.payload;
  switch (event.type) {
    case "approval_required":
      return text(payload, "question") ?? "A decision is being prepared.";
    case "file_change_proposed":
      return text(payload, "summary") ?? "A file change was drafted.";
    case "plan_updated":
      return "Updated the plan.";
    case "connection_state":
      return text(payload, "public_label") ?? "Connection state changed.";
    default:
      return text(payload, "public_label") ?? NEUTRAL_ACTIVITY_LABEL;
  }
}

export function Conversation({ threadId, startTurn }: ConversationProps) {
  const [events, setEvents] = useState<Map<number, StudioEvent>>(new Map());
  const [draft, setDraft] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  // A ref so reconnect does not re-run the effect and tear down the stream it just made.
  const generationRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    let source: EventSource | null = null;

    const record = (raw: MessageEvent) => {
      try {
        const parsed = JSON.parse(raw.data as string) as StudioEvent;
        setEvents((previous) => {
          if (previous.has(parsed.sequence)) {
            return previous; // redelivered by a reconnect; already rendered
          }
          const next = new Map(previous);
          next.set(parsed.sequence, parsed);
          return next;
        });
      } catch {
        // A malformed frame is the server's defect to report, not the page's to crash on.
      }
    };

    const connect = () => {
      if (cancelled) {
        return;
      }
      source = new EventSource(`/api/v1/agent/threads/${threadId}/events`);
      for (const type of [...MESSAGE_TYPES, ...ACTIVITY_TYPES, "turn_started", "turn_completed", "turn_failed", "thread_started"]) {
        source.addEventListener(type, record as EventListener);
      }
      // The endpoint closes after replaying, so `error` is the ORDINARY end of a
      // response here. Reconnecting is how the next batch arrives; the browser carries
      // `Last-Event-ID` itself, so nothing has to be threaded through.
      source.onerror = () => {
        source?.close();
        generationRef.current += 1;
        connect();
      };
    };

    connect();
    return () => {
      cancelled = true;
      source?.close();
    };
  }, [threadId]);

  const ordered = useMemo(
    () => [...events.values()].sort((a, b) => a.sequence - b.sequence),
    [events],
  );

  const send = useCallback(async () => {
    const prompt = draft.trim();
    if (prompt === "" || sending) {
      return;
    }
    setSending(true);
    setSendError(null);
    try {
      await startTurn(threadId, prompt);
      setDraft(""); // only on success -- see the module docstring
    } catch {
      setSendError("That request was not accepted. Your message is still here.");
    } finally {
      setSending(false);
    }
  }, [draft, sending, startTurn, threadId]);

  return (
    <section className="conversation" aria-label="Conversation with the agent">
      <ol className="conversation__stream">
        {ordered.map((event) => (
          <EventRow key={event.sequence} event={event} />
        ))}
      </ol>

      {sendError !== null && (
        <p className="conversation__error" role="alert">
          {sendError}
        </p>
      )}

      <div className="conversation__composer">
        <label className="conversation__label" htmlFor="conversation-draft">
          Ask about this workspace
        </label>
        <textarea
          id="conversation-draft"
          className="conversation__input"
          value={draft}
          rows={3}
          onChange={(changed) => setDraft(changed.target.value)}
        />
        <button
          type="button"
          className="conversation__send"
          onClick={send}
          disabled={sending}
        >
          Send
        </button>
      </div>
    </section>
  );
}

function EventRow({ event }: { event: StudioEvent }) {
  const late = event.ignored_for_state;
  const className = late
    ? "conversation__row conversation__row--late"
    : "conversation__row";

  if (MESSAGE_TYPES.has(event.type)) {
    return (
      <li className={className}>
        <p className="conversation__message">
          {text(event.payload, "text") ?? "(no message)"}
        </p>
        {late && <LateNote />}
      </li>
    );
  }

  if (ACTIVITY_TYPES.has(event.type)) {
    return (
      <li className={className}>
        <p className="conversation__activity">{activityLabel(event)}</p>
        {late && <LateNote />}
      </li>
    );
  }

  // Turn lifecycle events are structural, not content: rendering them as prose would
  // fill the transcript with "turn_started" noise.
  return null;
}

/**
 * Why a row is greyed out.
 *
 * The server RETAINS a late event and flags it rather than dropping it, so an anomaly
 * stays visible. Rendering it identically to a live event would defeat that.
 */
function LateNote() {
  return (
    <p className="conversation__late-note">
      This arrived after this turn ended, so it did not change the outcome.
    </p>
  );
}
