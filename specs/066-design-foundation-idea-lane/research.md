# Phase 0 Research: Design-Foundation Idea Lane (G1)

## Confirmed seams (repo, read-only)

- **Design GENERATION lens**: `.claude/workflows/idea-engine.js` defines a
  `design` lens (a "professional BI dashboard designer" standpoint) that generates
  presentation-foundation ideas and sets `strengthens_layer = design-system`.
  Confirmed present.
- **Design-foundation PANEL reviewer**: the panel includes a
  `design-foundation-reviewer` standpoint alongside principle / shipped-dup /
  value-feasibility. Confirmed present.
- **`strengthens_layer` enum**: the idea schema's `strengthens_layer` enum
  includes `design-system` (theme tokens, background/canvas, layout blueprints,
  accessibility, design-review evidence -- governance, never report authoring).
  Confirmed present. This is the signal the lane groups on.
- **IL1 ledger**: `docs/roadmap/shipped-ideas.yaml` maps each idea short-code to
  exactly `{ status, pr_sha, f_row }`, is human-curated and engine-read-only, and
  its header states it NEVER assigns a roadmap F-row (Principle V). Confirmed.
- **Design skill "See also"**: `.claude/skills/powerbi-dashboard-design/SKILL.md`
  already has a `## See also` section (points to `docs/powerbi/*`,
  dashboard-ready.md, the F011/012 dashboard-design skill, F016). Confirmed -- the
  concrete insertion point for the lane pointer.

## Confirmed absent (the deliverable, not a pre-existing seam)

- No design-foundation grouping exists in `docs/roadmap/idea-backlog.md`. Its
  section headers today are ADOPT / CONSIDER / PARK / Rescue notes /
  SHIPPED-SETTLED / Run-health only. The lane is genuinely absent.
- No G-series or design-layer key exists in `shipped-ideas.yaml` (keys are
  A1/B1/B2/F5/F6/F7/F8/A3/B3/PP1/SC1/DF1 and the kraken batch). No design ship has
  occurred yet -- consistent with Clarify Q2 (shape-only, add no entry now).
- No design rule module exists under `src/retail/rules/`. This spec deliberately
  does NOT add one -- it is a BOUNDARY (the HORIZON extension), not a dependency.

## Analog precedents

- **IL1 (spec-dir 052)**: added the ledger seam + engine read step; off-spine,
  `f_row: none`. G1 extends this exact link to the design layer.
- **SC2 (spec-dir 065)**: governance-internal, off-spine, no roadmap F-row
  self-assigned, categorical, fail-loud. Same off-spine posture G1 takes.

## Stale-evidence caution (resolved)

The reviewers' "0 design terms in the backlog" asymmetry evidence is now STALE:
the backlog currently holds the whole design idea cluster (many design-term hits)
because it now carries those ideas. The asymmetry that MOTIVATES G1 (a design
LANE/grouping is missing) still holds; the raw "0 terms" count does not. This
spec does not reuse the "0 terms" figure as a current fact.

## Decisions carried from Clarify (Session 2026-07-02)

- Scope = basic lane only (docs + small JS); rule module + reconciler are HORIZON,
  out of scope (Q1).
- Ledger change = shape-only; no design entry fabricated now (Q2).

## Open (human-owned, not researched away)

- Lane grain (section vs tag vs filter view) -- FR-011, Principle V.
- Ledger schema change vs reuse -- FR-012, Principle V.
- Roadmap F-row for G1 -- Principle V.
