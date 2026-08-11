/**
 * T013 -- the Command Room's table journey, written before the component exists.
 *
 * Drives US1 acceptance scenario 2 in particular: "it names Mapping as current, shows
 * the concrete blocker and evidence, offers the mapping action, and leaves Silver and
 * later work LOCKED."
 *
 * "Locked" is the subtle part. A stage after the blocked one is `not_started`, but the
 * REASON matters: it has not started because the gate ahead of it is closed, not because
 * nobody got round to it. Conveying that without inventing a fifth status means the
 * journey shows ordering and gating using only the four canonical statuses plus
 * position.
 *
 * Assertions go through the accessibility tree, never CSS selectors: FR-031 requires the
 * interface to work for a keyboard and screen-reader user, and a selector-based test
 * would pass on markup that does not.
 */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { StageState, TableJourney as Journey } from "../api/types";
import { TableJourney } from "./TableJourney";

const STAGES = [
  "source_ready",
  "mapping_ready",
  "silver_ready",
  "gold_ready",
  "semantic_model_ready",
  "dashboard_ready",
  "publish_ready",
] as const;

function stage(
  name: (typeof STAGES)[number],
  status: StageState["status"],
  extra: Partial<StageState> = {},
): StageState {
  return {
    stage: name,
    status,
    evidence: [],
    blocking_reasons: [],
    required_authority: [],
    ...extra,
  };
}

/** A table blocked at Mapping -- US1 scenario 2's exact shape. */
function blockedAtMapping(): Journey {
  return {
    table_id: "store_sales",
    display_name: "store_sales",
    current_stage: "mapping_ready",
    stages: [
      stage("source_ready", "pass", {
        evidence: [
          {
            label: "source profile recorded",
            source_ref: "evidence/source-profile.md",
            kind: "committed_reference",
            live_state: "verified",
          },
        ],
      }),
      stage("mapping_ready", "blocked", {
        blocking_reasons: [
          {
            code: null,
            message: "source-map.yaml is missing a grain declaration",
            source_ref: "mappings/store_sales/readiness-status.yaml",
          },
        ],
        required_authority: ["named_human"],
      }),
      ...STAGES.slice(2).map((name) => stage(name, "not_started")),
    ],
    next_action: {
      id: "store_sales:next",
      label: "Agree the table's grain, then record the mapping",
      explanation: "Projected from the committed readiness file.",
      requires_agent: false,
      requires_named_human: true,
    },
    forbidden_scope: ["silver", "gold"],
  };
}

describe("the table journey", () => {
  it("names the current stage in plain language", () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    // "Mapping", not "mapping_ready" -- FR-032 keeps the tool's own identifiers out of
    // the primary journey.
    const current = screen.getByRole("listitem", { current: "step" });
    expect(current).toHaveTextContent("Mapping");
    expect(current).not.toHaveTextContent("mapping_ready");
  });

  it("renders all seven stages in the authority's order", () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    // DIRECT children only: evidence and blockers are nested lists, so a plain
    // `getAllByRole("listitem")` -- even scoped with `within` -- also counts their
    // items and reports 11.
    const list = screen.getByRole("list", { name: /readiness stages/i });
    const stages = Array.from(list.children) as HTMLElement[];
    expect(stages).toHaveLength(7);
    expect(stages.map((item) => item.textContent)).toEqual(
      expect.arrayContaining([
        expect.stringContaining("Source"),
        expect.stringContaining("Mapping"),
        expect.stringContaining("Publish"),
      ]),
    );
  });

  it("shows the concrete blocker on the blocked stage", () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    expect(
      screen.getByText("source-map.yaml is missing a grain declaration"),
    ).toBeInTheDocument();
  });

  it("shows the evidence behind a passing stage", () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    expect(screen.getByText("source profile recorded")).toBeInTheDocument();
  });

  it("offers the next action, and says a named human is required", () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    expect(
      screen.getByText("Agree the table's grain, then record the mapping"),
    ).toBeInTheDocument();
    expect(screen.getByText(/named human/i)).toBeInTheDocument();
  });

  it("marks stages after the blocked one as locked, not merely not-started", () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    // US1 scenario 2: "leaves Silver and later work locked". Both facts must be
    // available: the categorical status is still `not_started` (FR-008 forbids
    // inventing a fifth), AND the reader learns it is gated rather than merely
    // untouched.
    const silver = screen.getByRole("listitem", { name: /silver/i });
    expect(silver).toHaveAttribute("data-locked", "true");
    expect(silver).toHaveTextContent(/waiting for mapping/i);
  });

  it("does NOT lock later stages when the current stage is a warning", () => {
    // `docs/readiness/readiness-model.md`: "`blocked` stops the next stage, `warning`
    // does not". A warning stage ADVANCED with a recorded issue, and `run_next` routes
    // it down the proceed path -- so showing later work as gated invents an obstacle the
    // authority does not record. `warning` is also what a clean live run assigns, i.e.
    // the most common non-pass state.
    const journey: Journey = {
      ...blockedAtMapping(),
      stages: [
        stage("source_ready", "pass"),
        stage("mapping_ready", "warning"),
        ...STAGES.slice(2).map((name) => stage(name, "not_started")),
      ],
    };
    render(<TableJourney journey={journey} />);

    expect(screen.getByRole("listitem", { name: /^Silver$/ })).toHaveAttribute(
      "data-locked",
      "false",
    );
  });

  it("locks later stages when the current stage is blocked", () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    expect(screen.getByRole("listitem", { name: /^Silver$/ })).toHaveAttribute(
      "data-locked",
      "true",
    );
  });

  it("derives position from the canonical order, not the array order", () => {
    // The contract pins `stages` LENGTH but never its ordering, so a server that
    // reorders must not invert the gating signal.
    const forward = blockedAtMapping();
    const reversed: Journey = { ...forward, stages: [...forward.stages].reverse() };
    render(<TableJourney journey={reversed} />);

    // Source PASSED and precedes Mapping: never locked, whatever order it arrived in.
    expect(screen.getByRole("listitem", { name: /^Source$/ })).toHaveAttribute(
      "data-locked",
      "false",
    );
    expect(screen.getByRole("listitem", { name: /^Silver$/ })).toHaveAttribute(
      "data-locked",
      "true",
    );
  });

  it("explains an unresolvable current stage instead of going quiet", () => {
    // A `current_stage` naming a stage absent from the array is server drift. Rendering
    // no current marker AND no explanation leaves the reader unable to tell a
    // never-started table from a broken payload.
    const journey = {
      ...blockedAtMapping(),
      current_stage: "nonexistent_ready" as Journey["current_stage"],
    };
    render(<TableJourney journey={journey} />);

    expect(screen.getByText(/has not reported a current stage/i)).toBeInTheDocument();
  });

  it("shows a stage's required authority even with no evidence or blockers", () => {
    // FR-008 names required authority among the six fields that MUST be preserved. An
    // early return keyed on source references dropped it whenever a stage had an
    // authority but nothing to cite.
    const journey: Journey = {
      ...blockedAtMapping(),
      stages: [
        stage("source_ready", "pass"),
        stage("mapping_ready", "blocked", { required_authority: ["named_human"] }),
        ...STAGES.slice(2).map((name) => stage(name, "not_started")),
      ],
    };
    render(<TableJourney journey={journey} />);

    expect(screen.getByText(/named_human/)).toBeInTheDocument();
  });

  it("renders the forbidden scope FR-008 names", () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    // The projection sends `forbidden_scope`; dropping it silently loses one of the six
    // fields FR-008 requires to be preserved. Asserted on the SENTENCE, because "silver"
    // legitimately appears twice -- once as a stage label, once as forbidden scope.
    expect(
      screen.getByText(/not permitted yet for this table: silver, gold/i),
    ).toBeInTheDocument();
  });

  it("does not mark a stage before the current one as locked", () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    const source = screen.getByRole("listitem", { name: /source/i });
    expect(source).toHaveAttribute("data-locked", "false");
  });

  it("locks nothing when every stage has passed", () => {
    const journey: Journey = {
      ...blockedAtMapping(),
      current_stage: "publish_ready",
      stages: STAGES.map((name) => stage(name, "pass")),
    };
    render(<TableJourney journey={journey} />);

    const list = screen.getByRole("list", { name: /readiness stages/i });
    for (const item of Array.from(list.children)) {
      expect(item).toHaveAttribute("data-locked", "false");
    }
  });

  it("keeps raw source references behind an explicit disclosure (FR-032)", async () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    const clone = document.body.cloneNode(true) as HTMLElement;
    clone.querySelectorAll("details").forEach((node) => node.remove());
    // The blocker TEXT is primary; the file it came from is technical detail.
    expect(clone.textContent).not.toContain("readiness-status.yaml");
    expect(clone.textContent).not.toContain("mappings/");

    // ...and it is reachable when the analyst opens it on purpose.
    const mapping = screen.getByRole("listitem", { name: /^Mapping$/ });
    await userEvent.click(within(mapping).getByText(/technical detail/i));
    expect(screen.getByText(/readiness-status\.yaml/)).toBeInTheDocument();
  });

  it("renders no numeric readiness signal (FR-009)", () => {
    const { container } = render(<TableJourney journey={blockedAtMapping()} />);
    const text = container.textContent ?? "";

    for (const pattern of [
      /\d+\s*%/,
      /\bpercent\b/i,
      /\b\d+\s*(of|\/)\s*\d+\b/,
      /\b(score|confidence|completeness|maturity|index)\b/i,
      /\b0?\.\d+\b/,
    ]) {
      expect(text).not.toMatch(pattern);
    }
  });

  it("uses an ordered list so the journey's sequence is conveyed structurally", () => {
    render(<TableJourney journey={blockedAtMapping()} />);

    // A screen-reader user must be able to tell stage 3 from stage 6 without seeing
    // the layout, so the ordering lives in the markup rather than in visual position.
    expect(screen.getByRole("list", { name: /readiness stages/i }).tagName).toBe("OL");
  });

  it("names a table with no current stage without inventing one", () => {
    const journey: Journey = {
      ...blockedAtMapping(),
      current_stage: null,
      next_action: null,
    };
    render(<TableJourney journey={journey} />);

    expect(screen.getByText(/has not reported a current stage/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("listitem", { current: "step" }),
    ).not.toBeInTheDocument();
  });
});
