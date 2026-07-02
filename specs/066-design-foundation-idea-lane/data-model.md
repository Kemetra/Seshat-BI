# Phase 1 Data Model: Design-Foundation Idea Lane (G1)

This feature adds no database and no new runtime schema. The "data" is two
plain-text governance shapes plus one documentation pointer.

## Entity: Design-foundation grouping (in idea-backlog.md)

The first-class cohort in the rendered backlog that design-layer ideas are
attributed to.

- **Membership signal**: an idea's existing `strengthens_layer = design-system`.
- **Presentation**: categorical only (a section heading, a per-idea tag, or a
  filter view -- the exact GRAIN is a human decision, FR-011 / Principle V).
- **Forbidden**: any computed or ranked numeric score on the grouping or its
  membership (roadmap hard rule #9).
- **Empty state**: renders as present-but-empty rather than omitted, so the layer
  stays visible as a first-class cohort.

## Entity: Shipped-ideas ledger entry (in shipped-ideas.yaml)

Reused unchanged from IL1. Keyed by an idea's backlog short-code; value has
EXACTLY three fields:

| Field   | Type   | Meaning                                                        |
|---------|--------|---------------------------------------------------------------|
| status  | enum   | "shipped" or "settled"                                        |
| pr_sha  | string | non-empty PR-number and/or commit-SHA evidence                |
| f_row   | string | a human-placed roadmap label (e.g. "F062") or the literal `none` |

- **Contract**: human-curated; engine READ-ONLY; never auto-appended; never
  derives a roadmap F-row. A design-layer ship reuses this shape.
- **Now**: no design entry is added (Clarify Q2 shape-only) -- no design idea has
  shipped yet, and fabricating a row would violate the read-only/no-fabrication
  contract.
- **Schema change**: whether the ledger gains a design/layer field is HUMAN-OWNED
  (FR-012 / Principle V). Default (pending human ruling) is reuse-unchanged, which
  requires no change to the IL1 ledger-contract guard.

## Entity: Design skill "See also" pointer (in SKILL.md)

A single discoverability line in the existing `## See also` section naming the
design-foundation lane and pointing to its location in
`docs/roadmap/idea-backlog.md`.

## Non-entities (explicitly excluded)

- No `src/retail/rules/` module (HORIZON).
- No automated ledger reconciler (HORIZON).
- No new YAML/JSON schema file, no migration.
