# Contract: Design-Foundation Lane + Ledger Extension (G1)

Prose contract (this feature adds no code interface / no HTTP surface). It states
the invariants any implementation of the lane MUST satisfy.

## C1 -- Grouping presence

The rendered `docs/roadmap/idea-backlog.md` MUST contain a first-class
design-foundation grouping. Design-layer ideas (`strengthens_layer =
design-system`) MUST be attributed to it. Non-design ideas MUST NOT be forced
into it.

## C2 -- Categorical, never scored

The grouping and membership in it MUST be categorical (section/tag/status). No
computed or ranked numeric score may be attached (roadmap hard rule #9).

## C3 -- Never promotes

The lane MUST NOT promote any idea onto the roadmap and MUST NOT self-assign an
F-number. An `f_row` is present only when a human already placed one; otherwise it
is the literal `none` (Principle V; IL1 header invariant).

## C4 -- Ledger read-only + shape-preserving

`docs/roadmap/shipped-ideas.yaml` MUST stay human-curated and engine-READ-ONLY.
No engine/automated step may append, rewrite, or derive an F-row from it. A
design-layer ship, when a human records it, MUST use the existing
`{ status, pr_sha, f_row }` entry shape (default, pending the FR-012 human
ruling). This feature adds NO design entry now (no design ship has occurred).

## C5 -- Engine edit is routing-only

The `.claude/workflows/idea-engine.js` change MUST be limited to
grouping/routing/rendering the existing design lens + design-foundation reviewer
output under the grouping via the existing `design-system` signal. It MUST NOT add
scoring, MUST NOT change the read-only Memory contract, and MUST NOT introduce
report/PBIP/PBIR authoring, DAX generation, or metric invention.

## C6 -- Discoverability pointer

`.claude/skills/powerbi-dashboard-design/SKILL.md`'s `## See also` section MUST
name the design-foundation lane and point to its backlog location.

## C7 -- Generic-only

No worked-example (pharmacy/c086) path, hex, metric name, or sample datum may be
baked into the lane definition or any seed content (rule 7).

## C8 -- No rule module, no reconciler

No `src/retail/rules/` module and no automated reconciler is added. Those are the
deferred HORIZON extension (FR-009).

## Verification (all read-only)

- C1/C2: inspect the rendered backlog headers + a design idea's attribution.
- C3/C4: inspect the ledger + its header; confirm no fabricated entry, no F-row
  self-assignment.
- C5: inspect the idea-engine diff -- render/routing only.
- C6: read the skill's See also section.
- C7: grep the change set for worked-example specifics -> none.
- C8: confirm `src/retail/rules/` has no new module and the change set has no
  reconciler; run `retail check` -> stays green.
