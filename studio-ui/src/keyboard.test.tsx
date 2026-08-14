/**
 * FR-031 keyboard operability and focus, over the real controls (T032).
 *
 * T032 names "keyboard, focus, ... over all critical states". The axe pass in
 * `accessibility.test.tsx` cannot cover this: axe audits a STATIC tree, so it sees that a
 * button exists and has an accessible name, but never that a keyboard user can reach it,
 * activate it, or tell where they are. Those are behaviours, and they need driven input.
 *
 * What jsdom can and cannot decide, stated rather than blurred:
 *
 * * **Decidable here** -- tab order (DOM order plus tabindex), whether a control is
 *   reachable at all, keyboard activation (Enter/Space on a button, typing into a
 *   textarea), programmatic focus, and label association. These are DOM state.
 * * **NOT decidable here** -- whether the focus ring is VISIBLE. `:focus-visible` styling
 *   needs paint, so `contrast.test.ts` proves the ring colour can meet 1.4.11 and a real
 *   browser pass (T036) remains the measurement for whether it is drawn.
 *
 * The controls are all native elements -- `<button>`, `<textarea>`, a real
 * `<label htmlFor>` -- which is why this passes rather than by accident of tabindex
 * juggling. That is the property under test: a `<div onClick>` would be invisible to
 * every assertion below.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  installFakeEventSource,
  type FakeEventSourceRegistry,
} from "./api/fakeEventSource";
import { ApprovalPanel } from "./components/ApprovalPanel";
import { approvalFromEvent } from "./api/approvalPayload";
import { Conversation } from "./components/Conversation";
import type { StudioEvent } from "./api/types";

let registry: FakeEventSourceRegistry;
let uninstall: () => void;

beforeEach(() => {
  ({ registry, uninstall } = installFakeEventSource());
});

afterEach(() => {
  uninstall();
  vi.restoreAllMocks();
});

function renderConversation(
  startTurn = vi.fn().mockResolvedValue({ turn_id: "turn1" }),
) {
  const result = render(
    <Conversation
      threadId="t1"
      startTurn={startTurn}
      interruptTurn={vi.fn().mockResolvedValue(undefined)}
      onTurnSettled={vi.fn()}
    />,
  );
  return { ...result, startTurn };
}

/** An approval panel, permitted or refused, from the generated payload shape. */
function renderApproval(allowPermitted: boolean) {
  const event: StudioEvent = {
    thread_id: "t1",
    sequence: 1,
    type: "approval_required",
    occurred_at: "2026-08-14T00:00:00Z",
    turn_id: "turn1",
    payload: {
      reason: "Verify the mapping change",
      approval_id: "a1",
      required_authority: allowPermitted ? "technical" : "named_human",
      action: "run_command",
      target: "pytest -q",
      scope: "read_only",
      risk: "high",
      allow_permitted: allowPermitted,
      forbidden_reasons: allowPermitted ? [] : ["No silver work before Mapping Ready."],
    },
    ignored_for_state: false,
  };
  const approval = approvalFromEvent(event);
  if (approval === undefined) {
    throw new Error("fixture produced no approval");
  }
  return render(<ApprovalPanel approval={approval} threadId="t1" domKey={1} />);
}

describe("FR-031 -- the composer is operable by keyboard alone", () => {
  it("reaches the textarea and the send button by tabbing, in reading order", async () => {
    const user = userEvent.setup();
    renderConversation();

    const textarea = screen.getByRole("textbox", { name: /ask about this workspace/i });
    const send = screen.getByRole("button", { name: /send/i });

    await user.tab();
    // The composer's own controls must come in DOM order. Asserting the SEQUENCE rather
    // than "is focusable" is what catches a stray positive tabindex, which makes a
    // control reachable while silently reordering the whole page.
    expect(textarea).toHaveFocus();

    await user.tab();
    expect(send).toHaveFocus();
  });

  it("types a prompt and sends it with the keyboard, never the mouse", async () => {
    const user = userEvent.setup();
    const { startTurn } = renderConversation();

    await user.tab();
    await user.keyboard("does this workspace reconcile");
    // `{Enter}` on a focused <button type="button"> is the native activation path. A
    // handler bound only to onClick would still fire here -- which is the point: React
    // synthesises click from keyboard activation ONLY for real buttons.
    await user.tab();
    await user.keyboard("{Enter}");

    await waitFor(() =>
      expect(startTurn).toHaveBeenCalledWith("t1", "does this workspace reconcile"),
    );
  });

  it("keeps the typed draft reachable after focus moves away", async () => {
    const user = userEvent.setup();
    renderConversation();

    const textarea = screen.getByRole("textbox", { name: /ask about this workspace/i });
    await user.tab();
    await user.keyboard("half a question");
    await user.tab();

    // Focus left the field; the text must still be there to come back to.
    expect(textarea).toHaveValue("half a question");
  });

  it("associates the visible label with the field, so focus announces a name", () => {
    renderConversation();

    // `getByRole` with an accessible name only resolves through a working association.
    // A stray `htmlFor` typo would leave the field nameless and this query would throw.
    const textarea = screen.getByRole("textbox", { name: /ask about this workspace/i });
    expect(textarea).toHaveAttribute("id", "conversation-draft");
  });
});

describe("FR-031 -- approval controls are operable by keyboard alone", () => {
  it("reaches and activates the permitted decision with the keyboard", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    renderApproval(true);

    const allow = screen.getByRole("button", { name: /allow once/i });
    const decline = screen.getByRole("button", { name: /decline/i });

    await user.tab();
    expect(allow).toHaveFocus();
    await user.tab();
    expect(decline).toHaveFocus();

    // Space is the other native button activation, and it is the one a handler bound to
    // keydown-Enter alone would miss.
    await user.tab({ shift: true });
    await user.keyboard(" ");

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  });

  it("exposes no unreachable control when readiness forbids the allow", async () => {
    const user = userEvent.setup();
    renderApproval(false);

    // The allow is ABSENT rather than disabled in this branch, so the keyboard must not
    // land on it. A `disabled` button would also skip in tab order -- the distinction
    // matters because a disabled control still announces itself to a screen reader as a
    // thing that exists and cannot be used, which is a different message.
    expect(screen.queryByRole("button", { name: /allow once/i })).toBeNull();

    const decline = screen.getByRole("button", { name: /decline/i });
    await user.tab();
    expect(decline).toHaveFocus();
  });

  it("moves focus to nothing outside the panel on the first tab", async () => {
    const user = userEvent.setup();
    renderApproval(true);

    await user.tab();
    // Whatever holds focus must be INSIDE the rendered panel. A control that escapes its
    // own container is how a keyboard user ends up somewhere unannounced.
    //
    // `status`, not `group`: the panel deliberately uses `role="status"` because the
    // codebase reserves `alert` for faults and an approval is a pause. Its accessible
    // name comes from the heading via `aria-labelledby`, so querying by that name also
    // proves the association resolves.
    //
    // The heading is `approval.question`, and these fixtures deliberately omit it --
    // real Codex may send no question, so the documented fallback is the honest case to
    // pin here. Querying the field name I *wished* existed (`reason`) is what the
    // approvalPayload module warns about.
    const panel = screen.getByRole("status", { name: /asking permission/i });
    expect(panel.contains(document.activeElement)).toBe(true);
  });
});

describe("FR-031 -- the stop control appears only while it can act", () => {
  it("is absent before a turn is live, so the keyboard never reaches a dead control", () => {
    renderConversation();

    // A focusable button that does nothing is worse than no button: it costs a keyboard
    // user a tab stop and tells them an action is available when it is not.
    expect(screen.queryByRole("button", { name: /^stop$/i })).toBeNull();

    // The stream IS subscribed at this point -- the control's absence is about there
    // being no live turn, not about the component having failed to mount.
    expect(registry.connections.length).toBeGreaterThan(0);
  });
});
