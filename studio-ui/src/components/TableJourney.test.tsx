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

/**
 * A journey built from the shape the REAL projection produces.
 *
 * `projection._evidence_ref` assigns the committed string to BOTH `label` and
 * `source_ref`, and `_next_action` copies the committed instruction verbatim -- so real
 * labels are file paths and real next actions name commands. The earlier fixtures
 * invented human-readable text the production code never emits, which is why they missed
 * three FR-032 leaks. Values below are copied from `build_workspace_snapshot(".")` on
 * this repository.
 */
function realWorldJourney(): Journey {
  const committed = "mappings/finance_gl_actuals/source-profile.md";
  return {
    table_id: "finance_gl_actuals",
    display_name: "finance_gl_actuals",
    current_stage: "gold_ready",
    stages: [
      stage("source_ready", "pass", {
        evidence: [
          {
            label: committed,
            source_ref: committed,
            kind: "committed_reference",
            live_state: "verified",
          },
        ],
      }),
      stage("mapping_ready", "pass"),
      stage("silver_ready", "pass"),
      stage("gold_ready", "blocked", {
        blocking_reasons: [
          {
            code: null,
            message:
              "retail validate has not run; see src/seshat/validate.py:236-239 and " +
              "mappings/finance_gl_actuals/approval-request-model-integrity.md",
            source_ref: "mappings/finance_gl_actuals/readiness-status.yaml",
          },
        ],
      }),
      ...STAGES.slice(4).map((name) => stage(name, "not_started")),
    ],
    next_action: {
      id: "finance_gl_actuals:next",
      label:
        "OBTAIN THE MODEL-INTEGRITY RULINGS B and C " +
        "(mappings/finance_gl_actuals/approval-request-model-integrity.md)",
      explanation: "Projected verbatim from the committed readiness file.",
      requires_agent: false,
      requires_named_human: true,
    },
    forbidden_scope: [],
  };
}

/** Everything the analyst sees WITHOUT opening a disclosure. */
function primaryText(container: HTMLElement): string {
  const clone = container.cloneNode(true) as HTMLElement;
  clone.querySelectorAll("details").forEach((node) => node.remove());
  return clone.textContent ?? "";
}

describe("FR-032 against REAL projection output", () => {
  it("keeps evidence file paths out of the primary journey", () => {
    const { container } = render(<TableJourney journey={realWorldJourney()} />);

    expect(primaryText(container)).not.toContain("mappings/");
    expect(primaryText(container)).not.toContain(".md");
  });

  it("keeps blocker command names and source paths out of the primary journey", () => {
    const { container } = render(<TableJourney journey={realWorldJourney()} />);
    const primary = primaryText(container);

    for (const forbidden of ["retail validate", "src/seshat/", ".py:", "mappings/"]) {
      expect(primary).not.toContain(forbidden);
    }
  });

  it("keeps the verbatim next action out of the primary journey", () => {
    const { container } = render(<TableJourney journey={realWorldJourney()} />);

    expect(primaryText(container)).not.toContain("approval-request-model-integrity.md");
  });

  it("still tells the analyst what is happening, in plain language", () => {
    render(<TableJourney journey={realWorldJourney()} />);

    // Suppressing the technical text must not leave the reader with nothing: a blocked
    // stage and a waiting action have to be legible without opening anything.
    expect(screen.getByText(/blocked/i)).toBeInTheDocument();
    expect(screen.getByText(/named human/i)).toBeInTheDocument();
  });

  it("keeps the technical text reachable when explicitly opened", () => {
    const { container } = render(<TableJourney journey={realWorldJourney()} />);

    // Present in the DOM, inside a disclosure -- which is what FR-032 permits.
    expect(container.textContent).toContain("approval-request-model-integrity.md");
  });
});

describe("FR-032 against the strings the reviewer cited", () => {
  /**
   * Copied verbatim from `mappings/retail_store_sales/readiness-status.yaml`.
   *
   * These are why a lexical heuristic could never be complete: a skill name
   * (`retail-semantic-check`), a model path (`powerbi/RetailStoreSales.SemanticModel`),
   * a stage identifier (`publish_ready`), and a feature id (`F016`) share no form worth
   * matching. The component now treats ALL committed prose as technical instead.
   */
  const CITED = [
    "governed PBIP model authored as TMDL: powerbi/RetailStoreSales.SemanticModel",
    "retail-semantic-check 5-step verdict = pass: retail check exit 0",
    "ALL seven stages pass (publish_ready re-approved 2026-07-05)",
    "F016 dashboard evidence recorded",
  ];

  it("shows none of them in the primary journey", () => {
    const journey: Journey = {
      ...blockedAtMapping(),
      stages: [
        stage("source_ready", "pass", {
          evidence: CITED.map((label) => ({
            label,
            source_ref: label,
            kind: "committed_reference",
            live_state: "verified" as const,
          })),
        }),
        ...STAGES.slice(1).map((name) => stage(name, "not_started")),
      ],
      next_action: {
        id: "x:next",
        label: CITED[2] as string,
        explanation: "verbatim",
        requires_agent: false,
        requires_named_human: false,
      },
    };
    const { container } = render(<TableJourney journey={journey} />);
    const primary = primaryText(container);

    for (const fragment of [
      "retail-semantic-check",
      "powerbi/RetailStoreSales",
      "publish_ready",
      "F016",
      "retail check exit 0",
    ]) {
      expect(primary, `leaked ${fragment}`).not.toContain(fragment);
    }
  });

  it("still says how much evidence exists, so nothing reads as missing", () => {
    const journey: Journey = {
      ...blockedAtMapping(),
      stages: [
        stage("source_ready", "pass", {
          evidence: CITED.map((label) => ({
            label,
            source_ref: label,
            kind: "committed_reference",
            live_state: "verified" as const,
          })),
        }),
        ...STAGES.slice(1).map((name) => stage(name, "not_started")),
      ],
    };
    render(<TableJourney journey={journey} />);

    expect(screen.getByText(/4 committed references recorded/i)).toBeInTheDocument();
  });
});

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

  it("says evidence exists without printing the committed reference", () => {
    // Committed text is technical BY DEFAULT (see TableJourney.tsx): the reference lives
    // in the disclosure, and the primary journey states that evidence was recorded so a
    // reader never mistakes a hidden reference for a missing one.
    const { container } = render(<TableJourney journey={blockedAtMapping()} />);

    expect(screen.getByText(/1 committed reference recorded/i)).toBeInTheDocument();
    expect(primaryText(container)).not.toContain("source profile recorded");
    expect(container.textContent).toContain("evidence/source-profile.md");
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

  it("locks a stage whose EARLIER prerequisite has not passed (P1)", () => {
    // Deriving from the current stage alone was wrong in the other direction too: with
    // Source at `warning` and Mapping `not_started`, Silver is gated by MAPPING, not by
    // Source -- so reporting it unlocked told the analyst work was available when it was
    // not. Every preceding stage has to be inspected.
    const journey: Journey = {
      ...blockedAtMapping(),
      current_stage: "source_ready",
      stages: [
        stage("source_ready", "warning"),
        ...STAGES.slice(1).map((name) => stage(name, "not_started")),
      ],
      next_action: null,
    };
    render(<TableJourney journey={journey} />);

    // Mapping is the frontier itself, so it is not locked...
    expect(screen.getByRole("listitem", { name: /^Mapping$/ })).toHaveAttribute(
      "data-locked",
      "true",
    );
    // Silver cannot: Mapping has not started, so Silver waits on Mapping.
    expect(screen.getByRole("listitem", { name: /^Silver$/ })).toHaveAttribute(
      "data-locked",
      "true",
    );
  });

  it("names the prerequisite a locked stage is actually waiting on", () => {
    const journey: Journey = {
      ...blockedAtMapping(),
      current_stage: "source_ready",
      stages: [
        stage("source_ready", "pass"),
        stage("mapping_ready", "not_started"),
        ...STAGES.slice(2).map((name) => stage(name, "not_started")),
      ],
      next_action: null,
    };
    render(<TableJourney journey={journey} />);

    // "Waiting for Mapping", not "waiting for Source": naming the wrong prerequisite
    // sends the analyst to the wrong place.
    expect(
      screen.getByRole("listitem", { name: /^Silver$/ }),
    ).toHaveTextContent(/waiting for mapping/i);
  });

  it("locks the successor of a WARNING prerequisite (only pass clears a stage)", () => {
    // `docs/readiness/readiness-model.md` carries TWO rules and I first read only the
    // second: "A stage may be entered only when the prior stage is `pass`" AND
    // "`warning` does not block the next stage by itself; a `blocked` does". Those are
    // not in conflict -- entry requires `pass`, and `warning` is simply not the permanent
    // barrier `blocked` is. `run_next._stage_decision` settles it: it stops at a
    // `warning` stage and returns that stage as the next action, so the frontier has NOT
    // moved past it. Showing Silver as available would send the analyst past the
    // recorded stage.
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
      "true",
    );
    expect(
      screen.getByRole("listitem", { name: /^Silver$/ }),
    ).toHaveTextContent(/waiting for mapping/i);
  });

  it("does not lock the warning stage itself", () => {
    // The warning stage is the frontier, not a locked stage: its own prerequisite passed.
    const journey: Journey = {
      ...blockedAtMapping(),
      stages: [
        stage("source_ready", "pass"),
        stage("mapping_ready", "warning"),
        ...STAGES.slice(2).map((name) => stage(name, "not_started")),
      ],
    };
    render(<TableJourney journey={journey} />);

    expect(screen.getByRole("listitem", { name: /^Mapping$/ })).toHaveAttribute(
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

    // ...and it is reachable when the analyst opens it on purpose. Targeted by ROLE
    // rather than by text: the blocker summary now also mentions "technical detail", so
    // a text query matches the prose as well as the control.
    const mapping = screen.getByRole("listitem", { name: /^Mapping$/ });
    const disclosure = within(mapping).getByRole("group");
    await userEvent.click(within(disclosure).getByText(/technical detail/i));
    expect(screen.getByText(/readiness-status\.yaml/)).toBeInTheDocument();
  });

  it("renders no numeric readiness signal (FR-009)", () => {
    const { container } = render(<TableJourney journey={blockedAtMapping()} />);
    const text = container.textContent ?? "";

    // A COUNT of concrete things ("1 committed reference") is not a readiness signal, any
    // more than the pending-decision count is: FR-009 forbids a numeric readiness,
    // health, confidence, completeness, or maturity VALUE.
    for (const pattern of [
      /\d+\s*%/,
      /\bpercent\b/i,
      /\b\d+\s*(of|\/)\s*\d+\b/,
      /\b(score|confidence|completeness|maturity|index)\b/i,
      // `0?` made the leading zero optional, so this matched ".1" formed by `textContent`
      // joining "...evidence." to "1 committed reference" with no separator -- a
      // concatenation artifact, not a fraction. A real one would read "0.71".
      /\b0\.\d+\b/,
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
