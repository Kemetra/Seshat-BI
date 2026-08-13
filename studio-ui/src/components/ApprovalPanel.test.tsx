/**
 * The approval panel's invariants (T024, T026; FR-019..FR-022, FR-031).
 *
 * Each test states the invariant in its POSITIVE form, because the negative alone is
 * what made the original Phase 6 boundary test hollow: it asserted the absence of a
 * button whose label the contract never used, so it could not have failed when the
 * boundary was crossed. Where absence IS the invariant (FR-021's missing allow control)
 * the test also asserts what IS present, so a panel that renders nothing at all cannot
 * pass by accident.
 *
 * Payload shapes come from the REAL producer. Codex sends
 * `action`/`target`/`scope`/`risk` and no `question`; the fake bridge sends only
 * `question`. Testing exclusively against the fake would prove nothing about the path
 * that ships.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as client from "../api/client";
import { StudioRequestError } from "../api/client";
import { approvalFromEvent } from "../api/approvalPayload";
import type { StudioEvent } from "../api/types";
import { ApprovalPanel } from "./ApprovalPanel";

afterEach(() => {
  vi.restoreAllMocks();
});

/** A streamed approval in the shape REAL Codex sends. */
function approvalEvent(payload: Record<string, unknown>): StudioEvent {
  return {
    thread_id: "t1",
    sequence: 1,
    type: "approval_required",
    occurred_at: "2026-08-13T00:00:00Z",
    turn_id: "turn1",
    payload: {
      approval_id: "a1",
      required_authority: "technical",
      action: "run_command",
      target: "pytest -q",
      reason: "Verify the mapping change",
      scope: "read_only",
      risk: "low",
      allow_permitted: true,
      forbidden_reasons: [],
      ...payload,
    },
    ignored_for_state: false,
  };
}

function renderPanel(payload: Record<string, unknown> = {}) {
  const approval = approvalFromEvent(approvalEvent(payload));
  if (approval === undefined) {
    throw new Error("fixture produced no approval");
  }
  return render(<ApprovalPanel approval={approval} threadId="t1" />);
}

/** A `respondToToolApproval` that succeeds, and records what it was called with. */
function accepting() {
  return vi
    .spyOn(client, "respondToToolApproval")
    .mockResolvedValue(undefined as unknown as void);
}

describe("ApprovalPanel", () => {
  // --------------------------------------------------------------------- //
  // The exact scope (T024)                                                //
  // --------------------------------------------------------------------- //

  it("shows the exact scope the analyst is being asked to permit", () => {
    renderPanel();

    expect(screen.getByText("pytest -q")).toBeInTheDocument();
    expect(screen.getByText("run_command")).toBeInTheDocument();
    expect(screen.getByText("read_only")).toBeInTheDocument();
    expect(screen.getByText("Verify the mapping change")).toBeInTheDocument();
  });

  it("omits a field the provider did not send rather than inventing one", () => {
    renderPanel({ target: undefined, scope: undefined });

    expect(screen.queryByText("Target")).not.toBeInTheDocument();
    expect(screen.queryByText("Scope")).not.toBeInTheDocument();
    // The positive half: what WAS sent still renders, so this is not an empty panel.
    expect(screen.getByText("run_command")).toBeInTheDocument();
  });

  it("renders a real Codex approval, which carries no question", () => {
    // The fake bridge's `question` is absent here on purpose: a panel that depends on
    // it would show a heading in tests and blank in production.
    renderPanel({ question: undefined });

    expect(screen.getByRole("heading", { name: /asking permission/i })).toBeInTheDocument();
    expect(screen.getByText("pytest -q")).toBeInTheDocument();
  });

  // --------------------------------------------------------------------- //
  // FR-021 -- the allow control is ABSENT, not disabled                   //
  // --------------------------------------------------------------------- //

  it("offers allow-once and decline for a permitted technical approval", () => {
    renderPanel();

    expect(screen.getByRole("button", { name: /allow once/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /decline/i })).toBeInTheDocument();
  });

  it("renders NO allow control when readiness forbids the scope", () => {
    renderPanel({
      allow_permitted: false,
      forbidden_reasons: ["No silver work before Mapping Ready passes."],
    });

    // Absent, not disabled: a greyed-out button still offers something.
    expect(screen.queryByRole("button", { name: /allow once/i })).not.toBeInTheDocument();
    // And the refusal explains itself in the gate's own sentence.
    expect(
      screen.getByText(/No silver work before Mapping Ready passes\./),
    ).toBeInTheDocument();
    // Decline survives: answering the provider is still possible.
    expect(screen.getByRole("button", { name: /decline/i })).toBeInTheDocument();
  });

  it("renders no allow control for a named-human ruling, and says who decides", () => {
    renderPanel({ required_authority: "named_human", allow_permitted: false });

    expect(screen.queryByRole("button", { name: /allow once/i })).not.toBeInTheDocument();
    expect(screen.getByText(/named human must decide/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /decline/i })).toBeInTheDocument();
  });

  it("withholds the allow control when the verdict field is missing entirely", () => {
    // Fails CLOSED. An older server that predates `allow_permitted` must not be read
    // as granting permission by omission.
    renderPanel({ allow_permitted: undefined });

    expect(screen.queryByRole("button", { name: /allow once/i })).not.toBeInTheDocument();
  });

  it("withholds allow when the server says permitted but the authority is not ours", () => {
    // Both conditions are restated client-side: a server bug that set `allow_permitted`
    // on a governance ruling must not put an Allow button in front of it.
    renderPanel({ required_authority: "named_human", allow_permitted: true });

    expect(screen.queryByRole("button", { name: /allow once/i })).not.toBeInTheDocument();
  });

  it("says so when an allow is refused with no reason given", () => {
    renderPanel({ allow_permitted: false, forbidden_reasons: [] });

    expect(screen.getByText(/gave no reason/i)).toBeInTheDocument();
  });

  // --------------------------------------------------------------------- //
  // FR-020 -- one decision, relayed, no local side effect                 //
  // --------------------------------------------------------------------- //

  it("relays an allow as the contract's decision value", async () => {
    const respond = accepting();
    renderPanel();

    fireEvent.click(screen.getByRole("button", { name: /allow once/i }));

    await waitFor(() => expect(respond).toHaveBeenCalledWith("t1", "a1", "allow_once"));
  });

  it("relays a decline as the contract's decision value", async () => {
    const respond = accepting();
    renderPanel();

    fireEvent.click(screen.getByRole("button", { name: /decline/i }));

    await waitFor(() => expect(respond).toHaveBeenCalledWith("t1", "a1", "deny"));
  });

  it("replaces the controls with the decision once it is recorded", async () => {
    accepting();
    renderPanel();

    fireEvent.click(screen.getByRole("button", { name: /allow once/i }));

    expect(await screen.findByText(/allowed once/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /allow once/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /decline/i })).not.toBeInTheDocument();
  });

  // --------------------------------------------------------------------- //
  // Failures the OpenAPI does not document                                //
  // --------------------------------------------------------------------- //

  it("reports a 502 as unrepeatable, because the id is already spent", async () => {
    vi.spyOn(client, "respondToToolApproval").mockRejectedValue(
      new StudioRequestError(502, null),
    );
    renderPanel();

    fireEvent.click(screen.getByRole("button", { name: /allow once/i }));

    const failure = await screen.findByRole("alert");
    expect(failure).toHaveTextContent(/never reached the agent/i);
    expect(failure).toHaveTextContent(/cannot be sent again|cannot be decided again/i);
  });

  it("reports a 409 as stale rather than as a generic failure", async () => {
    vi.spyOn(client, "respondToToolApproval").mockRejectedValue(
      new StudioRequestError(409, null),
    );
    renderPanel();

    fireEvent.click(screen.getByRole("button", { name: /decline/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /no longer awaiting a decision/i,
    );
  });

  it("prefers the server's own recovery sentence over the built-in one", async () => {
    vi.spyOn(client, "respondToToolApproval").mockRejectedValue(
      new StudioRequestError(403, {
        type: "about:blank",
        title: "Refused",
        status: 403,
        detail: "d",
        recovery_action: "Clear the Mapping Ready blockers first.",
      }),
    );
    renderPanel();

    fireEvent.click(screen.getByRole("button", { name: /decline/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Clear the Mapping Ready blockers first\./,
    );
  });

  it("keeps the controls after a failure, so a retryable failure can be retried", async () => {
    vi.spyOn(client, "respondToToolApproval").mockRejectedValue(new Error("offline"));
    renderPanel();

    fireEvent.click(screen.getByRole("button", { name: /decline/i }));

    await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: /decline/i })).toBeInTheDocument();
  });

  // --------------------------------------------------------------------- //
  // FR-031 -- accessibility                                               //
  // --------------------------------------------------------------------- //

  it("announces itself as a status region with an accessible name", () => {
    renderPanel();

    const region = screen.getByRole("status");
    expect(region).toHaveAccessibleName(/asking permission|mapping change/i);
  });

  it("carries high risk in text, not by colour alone", () => {
    renderPanel({ risk: "high" });

    expect(screen.getByText(/high risk/i)).toBeInTheDocument();
    expect(screen.getByText(/escalates privileges/i)).toBeInTheDocument();
  });
});
