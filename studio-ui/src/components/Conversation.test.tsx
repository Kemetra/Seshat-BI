/**
 * T018 -- the chat surface, written before it exists.
 *
 * These tests target the failure modes this feature has already produced twice, rather
 * than the happy path:
 *
 * * **FR-032 -- no tool vocabulary in the primary journey.** The bridge emits
 *   `tool_started` with BOTH `name` (`read_workspace`) and `public_label` (`Reading the
 *   workspace`). Rendering the wrong one puts internal vocabulary on the main screen.
 *   This is the same defect class as `blockerSummary`, so it gets the same treatment: an
 *   explicit assertion that the internal string is absent while the public one is shown.
 * * **`ignored_for_state` must look different.** The server retains a late event and
 *   flags it rather than dropping it, precisely so an anomaly stays visible. Rendering it
 *   identically to a live event would defeat the reason the field exists.
 * * **Draft preservation's real case is a FAILED SEND**, not a remount. A draft that
 *   survives unmounting but is cleared on a 422 loses the user's text at the exact moment
 *   they need it back.
 * * **Reconnect must resume, not restart.** The endpoint is a finite replay, so the
 *   browser reconnects constantly; a consumer that ignores `Last-Event-ID` would
 *   re-render every event on every poll.
 *
 * Approval UI is deliberately NOT built here: `file_change_proposed` and
 * `approval_required` belong to Phase 6 (T024-T027). They render as inert activity, and
 * a test below pins that they carry no actionable control -- so the boundary cannot be
 * crossed accidentally before the approval semantics exist.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { StudioEvent } from "../api/types";
import {
  FakeEventSource,
  installFakeEventSource,
  type FakeEventSourceRegistry,
} from "../api/fakeEventSource";
import { Conversation } from "./Conversation";

let registry: FakeEventSourceRegistry;
let uninstall: () => void;

beforeEach(() => {
  ({ registry, uninstall } = installFakeEventSource());
});

afterEach(() => {
  uninstall();
  vi.restoreAllMocks();
});

function event(overrides: Partial<StudioEvent>): StudioEvent {
  return {
    thread_id: "t1",
    sequence: 1,
    type: "agent_message",
    occurred_at: "2026-08-11T00:00:00Z",
    turn_id: "turn1",
    payload: {},
    ignored_for_state: false,
    ...overrides,
  };
}

/** A `startTurn` that succeeds, and records what it was called with. */
function acceptingTurn() {
  return vi.fn().mockResolvedValue({ turn_id: "turn1" });
}

describe("Conversation", () => {
  it("opens a stream for its thread", async () => {
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);

    await waitFor(() => expect(registry.current).toBeDefined());
    expect(registry.current?.url).toContain("t1");
  });

  it("renders an agent message", async () => {
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit(
      "agent_message",
      event({ type: "agent_message", payload: { text: "Gold is blocked." } }),
      "1",
    );

    expect(await screen.findByText(/Gold is blocked\./)).toBeInTheDocument();
  });

  // --------------------------------------------------------------------- //
  // FR-032 -- the primary journey carries no tool vocabulary              //
  // --------------------------------------------------------------------- //

  it("shows a tool's public label and never its internal name", async () => {
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit(
      "tool_started",
      event({
        type: "tool_started",
        payload: { name: "read_workspace", public_label: "Reading the workspace" },
      }),
      "1",
    );

    expect(await screen.findByText("Reading the workspace")).toBeInTheDocument();
    expect(screen.queryByText(/read_workspace/)).not.toBeInTheDocument();
  });

  it("falls back to a neutral label when a tool has no public label", async () => {
    // The internal name must NOT be the fallback: a provider that omits the label would
    // otherwise leak its vocabulary through the gap.
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit(
      "tool_started",
      event({ type: "tool_started", payload: { name: "grep_secrets" } }),
      "1",
    );

    expect(await screen.findByText(/working/i)).toBeInTheDocument();
    expect(screen.queryByText(/grep_secrets/)).not.toBeInTheDocument();
  });

  // --------------------------------------------------------------------- //
  // Late events stay visible AND distinguishable                          //
  // --------------------------------------------------------------------- //

  it("marks an ignored_for_state event instead of hiding it", async () => {
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit(
      "agent_message",
      event({
        payload: { text: "arrived after the turn ended" },
        ignored_for_state: true,
      }),
      "1",
    );

    const message = await screen.findByText(/arrived after the turn ended/);
    // Present -- dropping it would hide a real anomaly -- but visibly not part of the
    // live exchange.
    expect(message).toBeInTheDocument();
    expect(screen.getByText(/after this turn ended/i)).toBeInTheDocument();
  });

  // --------------------------------------------------------------------- //
  // Reconnect resumes rather than restarting                              //
  // --------------------------------------------------------------------- //

  it("leaves reconnect to the browser instead of closing the stream on error", async () => {
    // The endpoint closes after every replay, so `error` fires on each ordinary poll.
    //
    // A previous version handled it by calling `close()` and reconnecting immediately.
    // That was two defects at once: a zero-delay busy loop, and -- because `close()`
    // permanently cancels native reconnect -- the server's `retry:` interval was
    // discarded, so `SSE_RETRY_MILLISECONDS` could not affect the client that documented
    // it as "the perceived latency".
    //
    // Native `EventSource` reconnect already waits the declared interval and resends
    // `Last-Event-ID`. So the correct behaviour is to NOT intervene, and that is what this
    // asserts: after an error the component neither closes the stream nor opens a second
    // one. (An earlier assertion here checked `lastEventId` on a second connection, which
    // could not fail: that value is written by the test's own `emit`, never by the
    // component.)
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());
    const opened = registry.current as FakeEventSource;

    opened.fail();
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(registry.connections).toHaveLength(1);
    expect(opened.closed).toBe(false);
  });

  it("does not duplicate an event that arrives twice", async () => {
    // A reconnect can legitimately redeliver the boundary event, so the consumer keys on
    // sequence rather than trusting arrival order.
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());

    const duplicate = event({ sequence: 7, payload: { text: "only once" } });
    registry.current?.emit("agent_message", duplicate, "7");
    registry.current?.emit("agent_message", duplicate, "7");

    expect(await screen.findAllByText(/only once/)).toHaveLength(1);
  });

  // --------------------------------------------------------------------- //
  // Composer and draft preservation                                       //
  // --------------------------------------------------------------------- //

  it("sends the composed prompt and clears the draft on success", async () => {
    const startTurn = acceptingTurn();
    render(<Conversation threadId="t1" startTurn={startTurn} />);

    const box = screen.getByRole("textbox", { name: /ask/i });
    fireEvent.change(box, { target: { value: "what is blocking gold?" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => expect(startTurn).toHaveBeenCalledTimes(1));
    expect(startTurn).toHaveBeenCalledWith("t1", "what is blocking gold?");
    await waitFor(() => expect((box as HTMLTextAreaElement).value).toBe(""));
  });

  it("keeps the draft when the send FAILS", async () => {
    // The discriminating case. Clearing here loses the user's text at the exact moment
    // they need it, and a remount-only test would never catch it.
    const startTurn = vi.fn().mockRejectedValue(new Error("422"));
    render(<Conversation threadId="t1" startTurn={startTurn} />);

    const box = screen.getByRole("textbox", { name: /ask/i });
    fireEvent.change(box, { target: { value: "keep me" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => expect(startTurn).toHaveBeenCalled());
    expect((box as HTMLTextAreaElement).value).toBe("keep me");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("refuses to send an empty prompt", async () => {
    const startTurn = acceptingTurn();
    render(<Conversation threadId="t1" startTurn={startTurn} />);

    fireEvent.change(screen.getByRole("textbox", { name: /ask/i }), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(startTurn).not.toHaveBeenCalled();
  });

  // --------------------------------------------------------------------- //
  // The Phase 6 boundary                                                  //
  // --------------------------------------------------------------------- //

  it("renders an approval as inert activity, with no actionable control", async () => {
    // Approval semantics are T024-T027. Until they exist, offering a button that appears
    // to grant approval would let a user believe they had approved something.
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit(
      "approval_required",
      event({
        type: "approval_required",
        payload: {
          approval_id: "a1",
          question: "Apply the proposed mapping change?",
          required_authority: "named_human",
        },
      }),
      "1",
    );

    expect(
      await screen.findByText(/Apply the proposed mapping change\?/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /approve|apply|reject/i }),
    ).not.toBeInTheDocument();
  });

  // --------------------------------------------------------------------- //
  // Interruption and the post-turn refresh                                //
  // --------------------------------------------------------------------- //

  it("offers a stop control only while a turn is live", async () => {
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());

    // Nothing running: offering "Stop" would be a control that does nothing.
    expect(screen.queryByRole("button", { name: /stop/i })).not.toBeInTheDocument();

    registry.current?.emit(
      "turn_started",
      event({ type: "turn_started", sequence: 1 }),
      "1",
    );

    expect(await screen.findByRole("button", { name: /stop/i })).toBeInTheDocument();
  });

  it("withdraws the stop control once the turn reaches a terminal event", async () => {
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());
    registry.current?.emit("turn_started", event({ type: "turn_started" }), "1");
    await screen.findByRole("button", { name: /stop/i });

    registry.current?.emit(
      "turn_completed",
      event({ type: "turn_completed", sequence: 2 }),
      "2",
    );

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: /stop/i })).not.toBeInTheDocument(),
    );
  });

  it("interrupts the live turn when stop is pressed", async () => {
    const interrupt = vi.fn().mockResolvedValue(undefined);
    render(
      <Conversation
        threadId="t1"
        startTurn={acceptingTurn()}
        interruptTurn={interrupt}
      />,
    );
    await waitFor(() => expect(registry.current).toBeDefined());
    registry.current?.emit(
      "turn_started",
      event({ type: "turn_started", turn_id: "turn9" }),
      "1",
    );

    fireEvent.click(await screen.findByRole("button", { name: /stop/i }));

    await waitFor(() => expect(interrupt).toHaveBeenCalledWith("t1", "turn9"));
  });

  it("refreshes the workspace once a turn completes", async () => {
    // FR-023's "final workspace refresh": a turn can change committed files, so the
    // deterministic views are stale until re-read. Without this the analyst would act on
    // a snapshot the agent has already invalidated.
    const onTurnSettled = vi.fn();
    render(
      <Conversation
        threadId="t1"
        startTurn={acceptingTurn()}
        onTurnSettled={onTurnSettled}
      />,
    );
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit("turn_completed", event({ type: "turn_completed" }), "1");

    await waitFor(() => expect(onTurnSettled).toHaveBeenCalledTimes(1));
  });

  it("refreshes after a FAILED turn too", async () => {
    // A failed turn can still have written files before failing, so refusing to refresh
    // would leave the stale view in exactly the case it matters most.
    const onTurnSettled = vi.fn();
    render(
      <Conversation
        threadId="t1"
        startTurn={acceptingTurn()}
        onTurnSettled={onTurnSettled}
      />,
    );
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit("turn_failed", event({ type: "turn_failed" }), "1");

    await waitFor(() => expect(onTurnSettled).toHaveBeenCalledTimes(1));
  });

  it("does not refresh for a late terminal event", async () => {
    // An `ignored_for_state` terminal did not end anything, so treating it as a turn
    // boundary would refresh the workspace on an event the server already discounted.
    const onTurnSettled = vi.fn();
    render(
      <Conversation
        threadId="t1"
        startTurn={acceptingTurn()}
        onTurnSettled={onTurnSettled}
      />,
    );
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit(
      "turn_completed",
      event({ type: "turn_completed", ignored_for_state: true }),
      "1",
    );

    // Give any erroneous call a chance to land before asserting absence.
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(onTurnSettled).not.toHaveBeenCalled();
  });

  // --------------------------------------------------------------------- //
  // The plan is actually shown                                            //
  // --------------------------------------------------------------------- //

  it("renders the plan steps rather than only announcing a plan exists", async () => {
    // The bridge emits `steps`, and an earlier version returned the constant
    // "Updated the plan." -- so a three-step plan and a one-step plan looked
    // identical and the plan itself was never visible. T018 asks for public plan
    // activity, so the steps have to reach the screen.
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit(
      "plan_updated",
      event({
        type: "plan_updated",
        payload: {
          steps: [
            { label: "Read the committed readiness spine", state: "running" },
            { label: "Summarise what the evidence supports", state: "pending" },
          ],
        },
      }),
      "1",
    );

    expect(
      await screen.findByText(/Read the committed readiness spine/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Summarise what the evidence supports/),
    ).toBeInTheDocument();
  });

  it("drops a plan step that carries no label", async () => {
    // A blank row is a claim nobody made. Rendering `undefined` as a step would put
    // an empty promise in a list whose whole purpose is stating intent.
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit(
      "plan_updated",
      event({
        type: "plan_updated",
        payload: { steps: [{ state: "running" }, { label: "Real step" }] },
      }),
      "1",
    );

    await screen.findByText(/Real step/);
    expect(screen.queryByText(/undefined/)).not.toBeInTheDocument();
  });

  it("survives a plan payload that is not a list", async () => {
    // `payload` is an open object in the contract, so a provider can send anything.
    // Throwing here would unmount the whole conversation -- the FR-025 failure this
    // feature already shipped once with agent_health.
    render(<Conversation threadId="t1" startTurn={acceptingTurn()} />);
    await waitFor(() => expect(registry.current).toBeDefined());

    registry.current?.emit(
      "plan_updated",
      event({ type: "plan_updated", payload: { steps: "not a list" } }),
      "1",
    );

    expect(await screen.findByText(/Updated the plan/)).toBeInTheDocument();
  });

  it("closes its stream on unmount", async () => {
    const { unmount } = render(
      <Conversation threadId="t1" startTurn={acceptingTurn()} />,
    );
    await waitFor(() => expect(registry.current).toBeDefined());
    const opened = registry.current as FakeEventSource;

    unmount();

    expect(opened.closed).toBe(true);
  });
});
