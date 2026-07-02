# Quickstart: Verify the Design-Foundation Lane (G1)

All verification is read-only inspection. No execution, no report authoring.

## 1. Grouping exists and is categorical (C1, C2)

- Open `docs/roadmap/idea-backlog.md`.
- Confirm a first-class design-foundation grouping is present (per the human-ruled
  grain: a `## ` section, a per-idea tag, or a filter view).
- Confirm design-layer ideas (`strengthens_layer = design-system`) are attributed
  to it and that no numeric score is attached to the grouping or its membership.

## 2. Never promotes (C3)

- Confirm the grouping does not assign any roadmap F-number and does not move an
  idea onto the roadmap.

## 3. Ledger shape + read-only (C4)

- Open `docs/roadmap/shipped-ideas.yaml`.
- Confirm the entry contract is unchanged `{ status, pr_sha, f_row }` (or the
  human-ruled schema, if FR-012 was decided otherwise) and that NO fabricated
  design entry was added.
- Confirm the header's human-curated / engine-read-only / never-assigns-F-row
  language still holds.

## 4. Engine edit is routing-only (C5)

- Review the `.claude/workflows/idea-engine.js` diff: it groups/routes/renders the
  existing design lens + design-foundation reviewer output under the grouping and
  adds nothing else (no scoring, no Memory-contract change, no authoring).

## 5. Discoverability pointer (C6)

- Open `.claude/skills/powerbi-dashboard-design/SKILL.md`, read `## See also`, and
  confirm the design-foundation lane pointer is present.

## 6. Generic + no rule module (C7, C8)

- Grep the change set for worked-example specifics (pharmacy/c086 paths, hexes,
  metric names) -> expect none.
- Confirm `src/retail/rules/` has no new module and the change set has no
  reconciler.
- Run the governance gate: `retail check` -> expect Passed.
