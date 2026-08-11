/**
 * `blockerSummary` must keep the analyst-actionable words and drop the unsafe spans.
 *
 * A review found the previous behaviour -- one generic sentence for every blocker -- left
 * the initial Command Room unable to say WHY a stage was blocked, and made multiple
 * blockers indistinguishable until every disclosure was opened. US1 requires the blocker
 * explained up front, so the summary keeps the concrete phrase.
 *
 * Removing SPANS is safe in a way classifying whole strings was not: anything path- or
 * command-shaped is excised regardless of what surrounds it, so an unrecognised identifier
 * cannot ride along inside an otherwise readable sentence. Strings below are real -- taken
 * from the committed workspace and from the reviewer's own citations.
 */

import { describe, expect, it } from "vitest";

import { blockerSummary } from "./TableJourney";

describe("blockerSummary", () => {
  it("keeps a concrete, analyst-actionable blocker readable", () => {
    expect(blockerSummary("source-map.yaml is missing a grain declaration")).toBe(
      "is missing a grain declaration",
    );
  });

  it("keeps a blocker that carries no technical spans untouched", () => {
    expect(blockerSummary("no named-human approval recorded")).toBe(
      "no named-human approval recorded",
    );
  });

  it("drops paths, commands, and source locations from a real blocker", () => {
    const summary = blockerSummary(
      "retail validate has not run; see src/seshat/validate.py:236-239 and " +
        "mappings/finance_gl_actuals/approval-request-model-integrity.md",
    );

    for (const unsafe of [
      "retail validate",
      "src/seshat",
      ".py:",
      "mappings/",
      ".md",
    ]) {
      expect(summary, `leaked ${unsafe}`).not.toContain(unsafe);
    }
  });

  it("drops skill names, stage identifiers, and feature ids", () => {
    const summary = blockerSummary(
      "retail-semantic-check verdict pending for publish_ready (F016)",
    );

    expect(summary).not.toContain("retail-semantic-check");
    expect(summary).not.toContain("publish_ready");
    expect(summary).not.toContain("F016");
  });

  it("falls back when SQL or code vocabulary survives the scrub", () => {
    // Real committed text from `mappings/finance_gl_actuals/readiness-status.yaml`. The
    // span scrubber removes paths, commands, and identifiers, but SQL keywords, call
    // syntax, and line references are none of those -- so the residue leaked. Rather than
    // widen the regex a fifth time, anything still carrying code shapes falls back.
    const summary = blockerSummary(
      "L21: the -1 unknown member hides the defect matrix's required D1/D2 refusal. " +
        "COALESCE(da.account_sk, -1) rewrites a FAILED natural-key lookup into a valid " +
        "row; LEFT JOIN ... WHERE d.pk IS NULL is the only honest form",
    );

    for (const unsafe of ["COALESCE", "LEFT JOIN", "WHERE", "L21", "IS NULL"]) {
      expect(summary, `leaked ${unsafe}`).not.toContain(unsafe);
    }
    expect(summary).toMatch(/see technical detail/i);
  });

  it("falls back rather than showing a mangled fragment", () => {
    // Scrubbing a message that is ONLY a path leaves nothing worth reading, so the
    // generic sentence is better than two stray words.
    expect(blockerSummary("mappings/x/y.md")).toMatch(/see technical detail/i);
  });

  it("distinguishes two different blockers", () => {
    // The defect the reviewer named: one generic sentence made every blocker identical.
    const first = blockerSummary("source-map.yaml is missing a grain declaration");
    const second = blockerSummary("no named-human approval recorded");

    expect(first).not.toBe(second);
  });
});
