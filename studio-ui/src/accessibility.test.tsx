/**
 * SC-007 -- automated accessibility checks over every critical state (T032, FR-031).
 *
 * SC-007 names four states and this file covers exactly those four: Command Room,
 * empty, blocked, and approval. Adding a fifth is welcome; dropping one silently
 * narrows the success criterion, so each test names the state it stands for.
 *
 * **`axe` was absent from `package.json` until now.** Every other frontend test asserts
 * accessibility by QUERYING through the accessibility tree -- `getByRole`, accessible
 * names, `role="alert"` -- which is real discipline and catches labelling regressions,
 * but it is not a WCAG audit. Nothing checked contrast pairs, duplicate ids, nesting, or
 * region structure. A criterion that says "automated browser accessibility checks report
 * no critical or serious violations" cannot be satisfied by a suite with no checker in
 * it, and asserting SC-007 without one would have been the exact over-claim this spec's
 * own Phase 6 record documents.
 *
 * **jsdom is not a browser, and that bound is stated rather than hidden.** Colour
 * contrast needs real layout and paint, so axe cannot evaluate it here -- `color-contrast`
 * is reported as `incomplete`, never as a pass. The tokens are audited separately by
 * eye against WCAG 2.2 AA, and T032's browser pass over the running app remains the
 * measurement for the rules jsdom cannot reach. What this file does prove, on every
 * run and for free, is the large class of structural violations that ARE decidable
 * without paint.
 */

import { render, waitFor, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";

import { App } from "./App";
import { ApprovalPanel } from "./components/ApprovalPanel";
import { approvalFromEvent } from "./api/approvalPayload";
import type { StudioEvent, WorkspaceSnapshot } from "./api/types";

/** Only critical and serious violations fail, which is exactly SC-007's wording. */
const BLOCKING_IMPACTS = new Set(["critical", "serious"]);

function snapshot(overrides: Partial<WorkspaceSnapshot> = {}): WorkspaceSnapshot {
  return {
    identity: {
      display_name: "retail_workspace",
      root_fingerprint: "abc123",
      branch: null,
      revision: "rev1",
    },
    generated_at: "2026-08-11T00:00:00Z",
    tables: [],
    pending_decision_count: 0,
    input_defects: [],
    agent_health: {
      state: "disabled",
      summary: "The agent bridge is not part of this slice.",
      recovery_action: "Deterministic views remain usable.",
      provider: "disabled",
      version: null,
    },
    ...overrides,
  };
}

function stubFetch(body: unknown, status = 200): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    }),
  );
}

function journey(tableId: string, status: "pass" | "blocked") {
  return {
    table_id: tableId,
    display_name: tableId,
    current_stage: "mapping_ready" as const,
    stages: [
      {
        stage: "mapping_ready" as const,
        status,
        evidence: [],
        // Fields taken from the generated `BlockingReason`, not invented: an earlier
        // draft used `reason`/`live_state`, which do not exist, and `blockerSummary`
        // crashed on the missing `message` rather than rendering a blocked state.
        blocking_reasons:
          status === "blocked"
            ? [
                {
                  code: null,
                  message: "Mapping Ready has no approved source map.",
                  source_ref: "mappings/store_sales/source-map.yaml",
                },
              ]
            : [],
        required_authority: status === "blocked" ? ["named_human"] : [],
      },
    ],
    forbidden_scope: [],
  };
}

/**
 * Render one approval panel from a payload, and return its container.
 *
 * The two approval states differ ONLY in their payload, so the event envelope and the
 * narrow-or-throw dance are shared. Each test still states its own payload in full --
 * the fields ARE the state under audit, and hiding them behind overrides would make it
 * hard to see what distinguishes a permitted approval from a refused one.
 */
function renderApproval(
  sequence: number,
  payload: Record<string, unknown>,
): HTMLElement {
  const event: StudioEvent = {
    thread_id: "t1",
    sequence,
    type: "approval_required",
    occurred_at: "2026-08-13T00:00:00Z",
    turn_id: "turn1",
    payload: { reason: "Verify the mapping change", ...payload },
    ignored_for_state: false,
  };
  const approval = approvalFromEvent(event);
  if (approval === undefined) {
    throw new Error("fixture produced no approval");
  }
  return render(
    <ApprovalPanel approval={approval} threadId="t1" domKey={sequence} />,
  ).container;
}

/** Every critical or serious violation, as sentences a human can act on. */
async function blockingViolations(container: HTMLElement): Promise<string[]> {
  const results = await axe(container);
  return results.violations
    .filter((violation) => BLOCKING_IMPACTS.has(String(violation.impact)))
    .map(
      (violation) =>
        `${violation.impact} ${violation.id}: ${violation.help} ` +
        `(${violation.nodes.length} node(s))`,
    );
}

describe("SC-007 -- no critical or serious WCAG violations", () => {
  it("Command Room, with tables listed", async () => {
    stubFetch(snapshot({ tables: [journey("store_sales", "pass")] }));
    const { container } = render(<App />);
    await screen.findByRole("heading", { name: "retail_workspace" });

    expect(await blockingViolations(container)).toEqual([]);
  });

  it("empty state -- a workspace with no tables onboarded", async () => {
    stubFetch(snapshot());
    const { container } = render(<App />);
    await screen.findByRole("heading", { name: /no tables are onboarded yet/i });

    expect(await blockingViolations(container)).toEqual([]);
  });

  it("blocked state -- a table whose stage cannot advance", async () => {
    stubFetch(snapshot({ tables: [journey("store_sales", "blocked")] }));
    const { container } = render(<App />);
    await screen.findByRole("heading", { name: "retail_workspace" });
    // By ROLE: the table name appears both as a heading and in the journey body, so a
    // bare text query matches twice and throws before axe ever runs.
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "store_sales" })).toBeInTheDocument(),
    );

    expect(await blockingViolations(container)).toEqual([]);
  });

  it("approval state -- a decidable technical approval", async () => {
    // Rendered directly rather than through a streamed turn: `App` cannot reach an
    // approval without a live EventSource, and the state SC-007 names is the panel.
    const container = renderApproval(1, {
      approval_id: "a1",
      required_authority: "technical",
      action: "run_command",
      target: "pytest -q",
      scope: "read_only",
      risk: "high",
      allow_permitted: true,
      forbidden_reasons: [],
    });

    expect(await blockingViolations(container)).toEqual([]);
  });

  it("approval state -- an allow that readiness forbids", async () => {
    // The refusal branch renders prose and a list the permitted branch does not, so it
    // is a genuinely different DOM rather than the same tree with one button removed.
    const container = renderApproval(2, {
      approval_id: "a2",
      required_authority: "named_human",
      action: "apply_change",
      target: "mappings/store_sales/source-map.yaml",
      scope: "propose_changes",
      risk: "low",
      allow_permitted: false,
      forbidden_reasons: ["No silver work before Mapping Ready passes."],
    });

    expect(await blockingViolations(container)).toEqual([]);
  });
});
