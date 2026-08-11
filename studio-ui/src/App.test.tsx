/**
 * Shell tests (T012).
 *
 * Assertions are made through the ACCESSIBILITY tree -- roles, headings, alerts --
 * rather than CSS selectors, because FR-031 requires the interface to work for a
 * keyboard and screen-reader user and a selector-based test would pass on markup that
 * does not.
 *
 * Component tests for the Command Room's detail views belong to T013.
 */

import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { WorkspaceSnapshot } from "./api/types";

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

function journey(
  tableId: string,
  status: "pass" | "blocked" | "warning" | "not_started",
) {
  return {
    table_id: tableId,
    display_name: tableId,
    current_stage: "mapping_ready" as const,
    stages: [
      {
        stage: "mapping_ready" as const,
        status,
        evidence: [],
        blocking_reasons: [],
        required_authority: [],
      },
    ],
    forbidden_scope: [],
  };
}

describe("the Studio shell", () => {
  it("names the workspace once the projection loads", async () => {
    stubFetch(snapshot());
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "retail_workspace" }),
    ).toBeInTheDocument();
  });

  it("states the pending decision count, which US1 names explicitly", async () => {
    stubFetch(snapshot({ pending_decision_count: 3 }));
    render(<App />);
    await screen.findByRole("heading", { name: "retail_workspace" });

    // US1: the Command Room "immediately explains the current readiness stage,
    // blockers, evidence, PENDING DECISION COUNT, and one next allowed action".
    // A queue length is not a readiness score, so FR-009 does not forbid the number --
    // but it must read unmistakably as a count of waiting decisions.
    expect(screen.getByText(/3 decisions await/i)).toBeInTheDocument();
  });

  it("uses singular wording for exactly one pending decision", async () => {
    stubFetch(snapshot({ pending_decision_count: 1 }));
    render(<App />);
    await screen.findByRole("heading", { name: "retail_workspace" });

    expect(screen.getByText(/1 decision awaits/i)).toBeInTheDocument();
    expect(screen.queryByText(/1 decisions/i)).not.toBeInTheDocument();
  });

  it("says so plainly when no decision is waiting", async () => {
    stubFetch(snapshot({ pending_decision_count: 0 }));
    render(<App />);
    await screen.findByRole("heading", { name: "retail_workspace" });

    expect(screen.getByText(/no decisions are waiting/i)).toBeInTheDocument();
  });

  it("shows a first-arrival state for a workspace with no tables", async () => {
    stubFetch(snapshot());
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: /no tables are onboarded yet/i }),
    ).toBeInTheDocument();
  });

  it("lists each table with its current stage status", async () => {
    stubFetch(snapshot({ tables: [journey("store_sales", "blocked")] }));
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "store_sales" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
    expect(screen.getByText("Mapping")).toBeInTheDocument();
  });

  it("announces a failure as an alert rather than a silent blank page", async () => {
    stubFetch(
      {
        type: "about:blank",
        title: "Unauthenticated",
        status: 401,
        detail: "No valid Studio session is present.",
        recovery_action: "Reopen Studio from the agent.",
      },
      401,
    );
    render(<App />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No valid Studio session is present.");
    expect(alert).toHaveTextContent("Reopen Studio from the agent.");
  });

  /**
   * The REAL strings `seshat.studio.projection._unreadable_defect` produces.
   *
   * Copied verbatim rather than invented: an earlier version of this test used a
   * sanitised fixture ("fix the YAML syntax") that no code path emits, so it proved
   * nothing about FR-032. These name `templates/readiness-status.yaml` and
   * `` `seshat check` `` because a governance record legitimately does -- which is
   * exactly why they must not appear in the primary journey.
   */
  const REAL_DEFECT = {
    code: "unreadable_readiness_file",
    message:
      "the committed readiness file for broken_table could not be read as a YAML mapping",
    source_ref: "mappings/broken_table/readiness-status.yaml",
    recovery_action:
      "make the file a readable YAML mapping matching templates/readiness-status.yaml; " +
      "`seshat check` reports a malformed readiness spine under rule RS1",
  };

  it("surfaces an input defect instead of quietly shortening the table list", async () => {
    stubFetch(snapshot({ input_defects: [REAL_DEFECT] }));
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: /input needs attention/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/readiness record could not be read/i),
    ).toBeInTheDocument();
  });

  it("keeps the server's technical wording behind an explicit disclosure (FR-032)", async () => {
    stubFetch(snapshot({ input_defects: [REAL_DEFECT] }));
    render(<App />);
    await screen.findByRole("heading", { name: /input needs attention/i });

    // The disclosure exists, is closed, and is keyboard reachable as a real control.
    const disclosure = screen.getByText("Technical detail");
    expect(disclosure.closest("details")).not.toHaveAttribute("open");

    // The technical strings ARE present in the DOM -- inside the closed disclosure,
    // which is what "explicitly opened" means -- but not in the primary text.
    const details = disclosure.closest("details");
    expect(details?.textContent).toContain("templates/readiness-status.yaml");
    expect(details?.textContent).toContain("seshat check");
  });

  it("shows no tool vocabulary outside the disclosure, using the REAL defect strings", async () => {
    stubFetch(snapshot({ input_defects: [REAL_DEFECT] }));
    const { container } = render(<App />);
    await screen.findByRole("heading", { name: /input needs attention/i });

    // Remove every disclosure, then assert on what remains: that residue is the
    // primary journey, and FR-032 governs exactly it.
    const clone = container.cloneNode(true) as HTMLElement;
    clone.querySelectorAll("details").forEach((node) => node.remove());
    const primary = clone.textContent ?? "";

    for (const forbidden of [
      "seshat ",
      "retail ",
      "templates/",
      ".yaml",
      "RS1",
      "mappings/",
    ]) {
      expect(primary).not.toContain(forbidden);
    }
  });

  it("renders no numeric readiness signal anywhere (FR-009)", async () => {
    stubFetch(
      snapshot({
        tables: [journey("a", "pass"), journey("b", "blocked")],
      }),
    );
    const { container } = render(<App />);
    await screen.findByRole("heading", { name: "retail_workspace" });

    // The status word and its evidence are the whole signal.
    //
    // An earlier version checked only `%`, "n of m", and the WORD "score". A review
    // injected five real score forms -- "Readiness 71 percent complete", "Health index
    // 0.71", "Maturity level 3", a bare "71%", "4 of 7 stages" -- and every test still
    // passed. These patterns cover the FORMS a numeric readiness signal actually takes,
    // which is what FR-009 forbids.
    const text = container.textContent ?? "";
    const forbidden: [RegExp, string][] = [
      [/\d+\s*%/, "a percentage"],
      [/\bpercent\b/i, "the word percent"],
      [/\b\d+\s*(of|\/)\s*\d+\b/, "an n-of-m ratio"],
      [/\b(score|confidence|completeness|maturity|index)\b/i, "a score-like noun"],
      [/\b0?\.\d+\b/, "a fractional value"],
      [/\blevel\s*\d+\b/i, "a numbered level"],
    ];
    for (const [pattern, what] of forbidden) {
      expect(text, `FR-009: rendered ${what}`).not.toMatch(pattern);
    }
  });

  it("shows no command names, skill names, or raw paths in the primary journey", async () => {
    stubFetch(snapshot({ tables: [journey("store_sales", "blocked")] }));
    const { container } = render(<App />);
    await screen.findByRole("heading", { name: "store_sales" });

    // FR-032: the analyst journey must not surface the tool's own vocabulary.
    const text = container.textContent ?? "";
    for (const forbidden of ["seshat ", "retail ", "source-mapping", "C:\\", "/src/"]) {
      expect(text).not.toContain(forbidden);
    }
  });

  it("marks the region busy while the projection is still loading", () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));
    render(<App />);

    expect(screen.getByRole("main")).toHaveAttribute("aria-busy", "true");
  });

  it("requests the workspace same-origin so the session cookie is attached", async () => {
    stubFetch(snapshot());
    render(<App />);
    await screen.findByRole("heading", { name: "retail_workspace" });

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/v1/workspace",
        expect.objectContaining({ credentials: "same-origin" }),
      );
    });
  });
});
