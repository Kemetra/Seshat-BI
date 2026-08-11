/**
 * T014 -- the seven agent health presentations, written before the component exists.
 *
 * FR-024: missing, signed-out, incompatible, quota-limited, crashed, and healthy states
 * MUST be DISTINCT and each carry a recovery action. (`disabled` is the seventh in the
 * contract's enum -- the state this Foundation slice actually ships, since no bridge
 * exists yet.)
 *
 * FR-025 is the requirement most easily broken: "deterministic workspace views MUST
 * remain available in every agent health state." A health banner that replaces the page
 * when the agent has crashed would satisfy FR-024 and violate FR-025, so the shell test
 * asserts the table journeys survive all seven.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AgentHealth as Health } from "../api/types";
import { AgentHealthNotice } from "./AgentHealth";

const STATES = [
  "healthy",
  "missing",
  "signed_out",
  "incompatible",
  "quota_limited",
  "crashed",
  "disabled",
] as const;

function health(state: Health["state"], overrides: Partial<Health> = {}): Health {
  return {
    state,
    // Deliberately does NOT contain the enum value: the fixture must not be the reason
    // a "no raw enum in the UI" assertion passes or fails.
    summary: "the server's own summary text",
    recovery_action: "the server's own recovery text",
    provider: state === "disabled" ? "disabled" : "codex",
    version: state === "disabled" ? null : "0.146.0",
    ...overrides,
  };
}

describe("agent health", () => {
  it.each(STATES)("renders a distinct presentation for %s", (state) => {
    render(<AgentHealthNotice health={health(state)} />);

    const notice = screen.getByRole("status");
    expect(notice).toHaveAttribute("data-agent-state", state);
    // Non-empty, human wording -- not the raw enum value echoed back.
    expect(notice.textContent?.trim().length ?? 0).toBeGreaterThan(0);
    expect(notice).not.toHaveTextContent(state);
  });

  it("gives every state a different headline, so none is indistinguishable", () => {
    const headlines = STATES.map((state) => {
      const { unmount } = render(<AgentHealthNotice health={health(state)} />);
      const text = screen.getByRole("status").querySelector("strong")?.textContent;
      unmount();
      return text;
    });

    // FR-024's "MUST be distinct": seven states, seven different headlines.
    expect(new Set(headlines).size).toBe(STATES.length);
  });

  it.each(STATES)("carries a recovery action for %s", (state) => {
    render(<AgentHealthNotice health={health(state)} />);

    // FR-024 requires an action for EVERY state, including healthy -- where the honest
    // action is "nothing to do", not silence that looks like a missing message.
    expect(screen.getByTestId("agent-recovery").textContent?.trim()).not.toBe("");
  });

  it("prefers the server's recovery action when it sends one", () => {
    render(<AgentHealthNotice health={health("crashed")} />);

    // The server knows more than the browser about WHY it crashed, so its wording wins;
    // the local text is the fallback for a server that sends nothing useful.
    expect(screen.getByTestId("agent-recovery")).toHaveTextContent(
      "the server's own recovery text",
    );
  });

  it("falls back to local wording when the server sends an empty action", () => {
    render(
      <AgentHealthNotice health={health("signed_out", { recovery_action: "  " })} />,
    );

    const recovery = screen.getByTestId("agent-recovery").textContent ?? "";
    expect(recovery.trim().length).toBeGreaterThan(0);
    expect(recovery).not.toBe("  ");
  });

  it("announces politely rather than interrupting (FR-031)", () => {
    render(<AgentHealthNotice health={health("quota_limited")} />);

    // `role="status"` is an implicit `aria-live="polite"`: agent health is context, not
    // an emergency, so it must not preempt what the analyst is reading.
    const notice = screen.getByRole("status");
    expect(notice).not.toHaveAttribute("aria-live", "assertive");
  });

  it("names the agent version only as technical detail (FR-032)", () => {
    render(<AgentHealthNotice health={health("incompatible")} />);

    const clone = document.body.cloneNode(true) as HTMLElement;
    clone.querySelectorAll("details").forEach((node) => node.remove());
    expect(clone.textContent).not.toContain("0.146.0");
  });

  it("does not depend on colour alone to convey the state (FR-031)", () => {
    render(<AgentHealthNotice health={health("crashed")} />);

    // A word, not just a hue: the headline states the condition in text.
    expect(screen.getByRole("status").querySelector("strong")?.textContent).toMatch(
      /\S/,
    );
  });

  it("survives a state outside the contract enum without crashing (FR-025)", () => {
    // Server drift must not take the page down. `PRESENTATION[state]` returned
    // undefined for an unknown value, and reading `.headline` off it threw -- with no
    // error boundary the whole tree unmounted, so the ONE component that must never gate
    // the deterministic views could delete them.
    const drifted = { ...health("healthy"), state: "reticulating" as Health["state"] };

    expect(() => render(<AgentHealthNotice health={drifted} />)).not.toThrow();
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByTestId("agent-recovery").textContent?.trim()).not.toBe("");
  });

  it("survives a missing health payload without crashing (FR-025)", () => {
    // An older or partial server may omit the field entirely.
    expect(() =>
      render(<AgentHealthNotice health={undefined as unknown as Health} />),
    ).not.toThrow();
  });

  it("gives every state a distinct RECOVERY action, not just a headline", () => {
    // The headline-only check would pass with two states sharing one recovery, which is
    // the half of FR-024 that actually tells the analyst what to DO.
    const recoveries = STATES.map((state) => {
      const { unmount } = render(
        <AgentHealthNotice health={health(state, { recovery_action: "" })} />,
      );
      const text = screen.getByTestId("agent-recovery").textContent;
      unmount();
      return text;
    });

    expect(new Set(recoveries).size).toBe(STATES.length);
  });

  it("renders no numeric health signal (FR-009)", () => {
    const { container } = render(<AgentHealthNotice health={health("quota_limited")} />);

    // The PRIMARY text only. The agent VERSION (`0.146.0`) lives inside the disclosure
    // and legitimately looks like a fraction -- it is an identifier, not a readiness
    // signal, and FR-009 governs what the analyst is shown up front.
    const clone = container.cloneNode(true) as HTMLElement;
    clone.querySelectorAll("details").forEach((node) => node.remove());
    const text = clone.textContent ?? "";

    for (const pattern of [
      /\d+\s*%/,
      /\bpercent\b/i,
      /\b(score|confidence|health index|maturity)\b/i,
      /\b0?\.\d+\b/,
    ]) {
      expect(text).not.toMatch(pattern);
    }
  });
});
