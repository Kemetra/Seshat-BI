# 0016 -- The PBIR adapter may write visual GEOMETRY (increment D), bounded

- **Date:** 2026-07-06
- **Status:** **Accepted -- RATIFIED by Ahmed Shaaban (owner) on 2026-07-06.** The owner
  directed ratification of this ADR by name and resolved its three open questions (see
  the Open questions block below). Increment D is authorized to be built under the terms
  of this ADR; the writer/allow-list/lint are enumerated future work and ship no PBIR by
  this decision.
- **Roadmap feature:** F034 (Visual Implementation) -- increment D. Extends the
  formatting-only adapter (ADR 0015, RATIFIED 2026-07-05) to a *bounded* geometry
  (layout) capability. A/B/C (theme / per-visual formatting / page background) shipped;
  D (position + size of existing visuals) is the next increment and needs its own carve-
  out because ADR 0015 and the shipped adapter deliberately REFUSE geometry.
- **Authority category (F024):** Execution / **Authoring** Adapter, `local-file` (same
  category as ADR 0015 -- NOT DB-connected, NOT publish-capable).
- **Context:** the shipped adapter refuses geometry on purpose. `pbir_visual_format.py`
  snapshots `visual.query` + `visual.visualType` and refuses any edit that alters them
  (FR-003); `pbir-authoring-adapter/SKILL.md` says "no `page.json` geometry"; the smart-
  formatting workflow routes the geometry anti-patterns (#1 too many visuals, #5 slicers
  dominate, #6 table-as-headline, #7 no hierarchy) to `handoff-only` because "the verbs
  cannot write position, size, or `visualType`." That is the current, honest limit: a
  human/Desktop fixes layout. The open question this ADR closes: **may the adapter write
  the position and size of an already-approved visual, and under what boundary?**

## Decision (all clauses are PROPOSED -- pending ratification)

### 1. What is lifted: position + size of EXISTING binding-map visuals only

Increment D permits the adapter to write, for a visual that is already present in the
report AND on the approved visual-contract-binding-map, ONLY these geometry properties:

> `x`, `y`, `width`, `height`, `z` (tab/stack order) -- the visual's layout rectangle.

Nothing else. This turns the geometry anti-patterns (#1/#5/#6/#7) from `handoff-only`
into an *applyable* layout increment (a new `apply_verb: D`), but only as a re-layout of
visuals that already exist and are already bound.

### 2. The hard exclusions (the load-bearing part -- geometry is NOT one thing)

Geometry splits into layout (safe) and meaning/creation (forbidden). The adapter MUST
NOT, even under this lift:

> - change a visual's **`visualType`** (bar->line, table->card, ...) -- that is a
>   binding-adjacent representation change, still guarded byte-identical by FR-003;
> - **create** a visual, delete a visual, or add/remove a page -- creation is authoring
>   truth, not laying out existing truth;
> - move/resize a visual that is **absent from the approved binding-map** (`blocked-
>   orphan` -- route upstream, never lay out an unbound visual);
> - decide **which** visual is the headline or the reading order when the questions are
>   not ranked -- that is the Principle-V judgment below, `needs-owner-decision`.

The line: **laying out an existing, bound visual = applyable; creating, retyping, or
ranking = forbidden or owner's.**

### 3. The evidence-not-approval rule holds (unchanged from ADR 0015 decision 3)

> A successful geometry write is EVIDENCE that a layout was applied; it MUST NOT move
> `dashboard_ready` (or any stage) to `pass` and MUST NOT emit a numeric confidence/
> health/maturity score (hard rule #9). Whether the rendered layout is *good* remains a
> human render + `screenshot-review` judgment, recorded by the verb owner.

Geometry is the anti-pattern class MOST dependent on a human render (position/size only
"work" visually), so this rule is even more load-bearing here than for A/B/C.

### 4. Self-contained, deterministic, validated, reversible (unchanged from 0015 4+5)

> Same terms as ADR 0015: no pbi-cli / MCP / live connection / network; every write
> deterministic (byte-identical on re-run), a reviewable git diff, validated (valid JSON
> + round-trip stable + the binding snapshot `query`/`visualType` byte-identical before/
> after + a geometry authoring-lint), all-or-nothing per report, traversal-guarded, no
> overwrite without explicit intent.

A geometry writer that can push a visual off-canvas or overlap two visuals is a real
hazard; the lint MUST at minimum reject off-canvas / negative / non-numeric rectangles.

### 5. Proposes via the formatting-plan ledger; the owner ranks the headline

Geometry decisions are proposed as `apply_verb: D` rows in the `formatting-plan.md`
ledger (the smart-formatting layer), consuming `dashboard-layout.md` reading order where
it is already committed. Where reading order / headline is NOT ranked, the row is
`needs-owner-decision` (Principle V), never auto-`proposed` -- exactly the pattern #8
category-colors and the verb-C background row already follow.

### 6. Authoring, NOT publishing; core stays forbidden (unchanged from 0015 1+6)

The lift is a narrow carve-out for this one bounded adapter. The static DEFINE/CHECK
core (`src/retail/` rules, `retail check`) remains forbidden from writing any PBIR. The
adapter writes committed PBIR and stops; live publish is the separately-parked F016.

### 7. Docs-first; this decision ships NO geometry writer

Consistent with ADR 0015 decision 8 and Principle VIII: this ADR + a future spec
enumerate the shape; the `apply_verb: D` writer, its geometry allow-list, and the
geometry authoring-lint are built under that spec's plan/tasks AFTER ratification. No
geometry is written by this decision.

## Consequences

- The kit could re-lay-out an approved page programmatically (as a git diff), closing the
  #1/#5/#6/#7 anti-patterns that are currently `handoff-only`.
- The constitutional boundary shifts from "adapter formats only, never geometry" to
  "adapter formats + lays out EXISTING bound visuals; never creates, retypes, or ranks."
- FR-003's `query`/`visualType` byte-identity guarantee is UNCHANGED and still enforced --
  geometry is added *beside* it, never through it.
- A NEW geometry authoring-lint is ADDED (off-canvas/overlap/type guards); the gate gets
  stronger, not weaker. No existing rule is weakened.
- No maturity/confidence score is introduced (hard rule #9). "Great layout" stays a human
  render judgment, explicitly NOT claimed.

## Alternatives considered

- **Keep geometry `handoff-only` forever (status quo).** The honest default; rejected
  only if the owner wants programmatic re-layout. Zero risk, zero new capability.
- **Lift `visualType` too (let the adapter change bar->line).** Rejected in this draft:
  representation is binding-adjacent and meaning-carrying; it belongs with the visual's
  contract, not a layout pass. (An owner may choose to include it -- flagged as an open
  question below.)
- **Let the adapter CREATE visuals to fix "too few / missing" (#anti-patterns).**
  Rejected: creation is authoring truth (surface-1 orphan rule); increment D lays out
  what exists, it does not invent.
- **Auto-rank the headline / reading order.** Rejected: that is the Principle-V judgment
  (decision 5); the layer proposes slots, the owner ranks.

## Open questions -- RESOLVED at ratification (owner, 2026-07-06)

1. **`z`/stack order -- INCLUDED as layout.** `z` is spatial/presentation (which visual
   sits on top), the same class as `x/y/width/height`, not data-meaning. It is required
   by the overlap resolution below: once overlap is allowed, stacking order must be
   controllable or layering is nondeterministic. `apply_verb: D` writes `z`.
2. **`visualType` -- EXCLUDED (draft position confirmed).** Changing a visual's type
   (bar->line) changes how the data *reads* -- representation-as-meaning, which
   contradicts the adapter's "styler, not author of truth" identity (ADR 0015 decision
   2) and has no demonstrated need. It stays forbidden and FR-003-guarded. Any future
   `visualType` capability is a separate, more-guarded sub-lift under its own ADR.
3. **Overlap policy -- reject OFF-CANVAS only; ALLOW overlap.** The geometry lint
   enforces *objective mechanical validity* (negative / off-canvas / non-numeric
   rectangles are objectively broken -> lint fails), but it MUST NOT judge whether an
   overlap is accidental occlusion or intentional layering (a KPI over a background
   band) -- that is a design-quality judgment the lint is structurally unqualified to
   make (it belongs to the human render + `screenshot-review`, per the layer's stated
   ceiling). So overlap is permitted; only off-canvas is rejected.
   - **Build note (load-bearing):** with off-canvas as the primary geometry check, the
     lint MUST read the REAL page canvas dimensions from the report's page definition --
     never a hardcoded constant (e.g. 1280x720). A wrong constant makes the lint miss
     real off-canvas or false-positive valid layouts. Verify the source of canvas
     width/height before implementing.

## Ratification

- **ratified_by:** Ahmed Shaaban (owner)
- **ratified_on:** 2026-07-06

The owner directed ratification of this ADR by name (named-owner authority; the agent
recorded the decision, did not self-ratify -- Principle V). Increment D may now be
specced and built under these terms. It ships LATENT: the real report page has zero
visuals, so the writer + lint are proven on a fixture and are latent until a real
multi-visual report lands (same posture as A/B/C and the smart-formatting layer).

## See also

- The precedent it extends: `docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md`.
- The refusal it would lift: `src/retail/pbir_visual_format.py` (FR-003 snapshot);
  `.claude/skills/pbir-authoring-adapter/SKILL.md` ("no page.json geometry");
  the `handoff-only` routing in
  `.claude/skills/powerbi-dashboard-design/workflows/formatting-plan.md` step 3.
- The ledger that would carry `apply_verb: D` rows: `templates/formatting-plan.md`.
- The companion-adapter pattern: ADR 0009 (dbt), 0010 (Dagster);
  `docs/architecture/product-modules.md`.
- `.specify/memory/constitution.md` (Principles III, IV, V, VIII; hard rule #9).
