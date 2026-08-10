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

  it("surfaces an input defect instead of quietly shortening the table list", async () => {
    stubFetch(
      snapshot({
        input_defects: [
          {
            code: "unreadable_readiness_file",
            message: "the committed readiness file for broken_table could not be read",
            source_ref: "mappings/broken_table/readiness-status.yaml",
            recovery_action: "fix the YAML syntax",
          },
        ],
      }),
    );
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: /input needs attention/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/could not be read/)).toBeInTheDocument();
    expect(screen.getByText("fix the YAML syntax")).toBeInTheDocument();
  });

  it("renders no numeric readiness signal anywhere (FR-009)", async () => {
    stubFetch(
      snapshot({
        tables: [journey("a", "pass"), journey("b", "blocked")],
      }),
    );
    const { container } = render(<App />);
    await screen.findByRole("heading", { name: "retail_workspace" });

    // No percentage, no "n of m", no bare score. The status word and its evidence are
    // the whole signal.
    expect(container.textContent).not.toMatch(/\d+\s*%/);
    expect(container.textContent).not.toMatch(/\b\d+\s*(of|\/)\s*\d+\b/);
    expect(container.textContent?.toLowerCase()).not.toContain("score");
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
