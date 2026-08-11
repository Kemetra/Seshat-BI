/**
 * `stageLabel` must never echo an unrecognised identifier (FR-032).
 */

import { describe, expect, it } from "vitest";

import { stageLabel } from "./StatusBadge";

describe("stageLabel", () => {
  it.each([
    ["source_ready", "Source"],
    ["mapping_ready", "Mapping"],
    ["silver_ready", "Silver"],
    ["gold_ready", "Gold"],
    ["semantic_model_ready", "Semantic model"],
    ["dashboard_ready", "Dashboard"],
    ["publish_ready", "Publish"],
  ])("names %s as %s", (stage, expected) => {
    expect(stageLabel(stage)).toBe(expected);
  });

  it("does not echo an unrecognised identifier", () => {
    // The previous string-munging version turned this into "Reticulating", putting a
    // server-supplied identifier into visible text and the aria-label.
    const label = stageLabel("reticulating_ready");

    expect(label).not.toContain("reticulating");
    expect(label).not.toContain("Reticulating");
    expect(label.trim().length).toBeGreaterThan(0);
  });
});
