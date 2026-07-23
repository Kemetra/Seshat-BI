---
name: powerbi-workflows
description: >-
  Route guarded Power BI work -- dashboard/page design, screenshot and report
  QA, theme and background assets, visual formatting and geometry, and existing
  PBIP adoption -- to the correct governed surface. Use when a user asks to
  design, review, restyle, format, or adopt a Power BI report under Seshat BI's
  readiness gates.
---

# Power BI workflows

Read `../../portable-operating-contract.md` before acting. These routes never
replace readiness gates: no invented metric, measure, KPI, or DAX meaning; no
numeric readiness/confidence score; no self-granted approval; no
dashboard-ready claim without committed evidence.

## Design (dashboards and pages)

Check the proposal first with the installed read-only helpers when available:
`seshat dashboard-planner` returns a categorical new/extends/duplicate verdict
against the committed dashboard set, and `seshat dashboard-gaps` inventories
design-blocking gaps before any layout work.

Data-bound visual design requires approved metric contracts and committed
semantic-model evidence. With both present, produce reviewable design guidance
-- a layout plan, a visual list, and a visual-to-contract binding map where
every data-bound visual binds to exactly one approved contract. Slicers and
filters belong to a compact filter rail that never dominates the canvas, and
each slicer's field and default selection is part of the reviewable design.
Without the gates, stop and name the missing one. For metric meaning load
`retail-kpi-knowledge`; for measure semantics load `bi-dax-knowledge`.

## Review and QA

Review a screenshot or built report against the design guidance above and
report concrete, advisory findings. Validate a page blueprint with the
installed `seshat pbir-validate-blueprint` helper when available. Before a
human opens Desktop on any agent-touched report, run the installed
`seshat pbir-validate-bindings --report <X.Report> --model <X.SemanticModel>`
helper when available: it resolves every bound field (projections, filters,
sorts) against the model's TMDL and blocks on unresolved bindings -- missing
measures/columns, unknown entities, PII-masked renames -- the exact class that
otherwise surfaces as Desktop error cards. It needs no blueprint or binding
map, so it also covers Desktop-owned reports. A clean review is evidence for a
named human, never an approval.

## Theme and backgrounds

Generate theme artifacts with `seshat theme-gen` and `seshat theme-compile`;
apply them to a committed report with `seshat pbir-apply-theme` and
`seshat pbir-set-page-background`. Themes cover palette, fonts, visual
defaults, page/wallpaper defaults, sentiment colors, and filter-pane/
filter-card defaults -- the filter pane's LOOK, never what it filters. Theme
and background files carry style and structure only -- never business data,
metric meaning, secrets, or PII.

## Formatting and geometry

Author formatting plans freely, but mutate committed PBIR only through the
allow-listed installed helpers `seshat pbir-format-visual` and
`seshat pbir-set-geometry`, which preserve every data binding byte-for-byte.
Adding a slicer or changing what a visual or filter binds to is a BINDING
change, not formatting -- route it back to the design gate. Anything outside
the allow-list stays a plan for human review.

## Semantic measures (handoff)

From an APPROVED metric contract only, the installed `seshat generate
--contract <path>` produces a verified TMDL measure block into a new
standalone file (never under a `powerbi/` tree, never overwriting); it does
not invent meaning beyond the contract. With a live database and an
owner-approved expected value, `seshat value-check` compares a measure's
recomputed aggregate within tolerance -- report a pending state if the
database extra or DSN is absent.

## Existing PBIP adoption

Follow the `seshat-bi` skill's adoption route: read-only
`seshat adopt-pbip assess`, human review of the exact assessment digest, then
`seshat adopt-pbip scaffold` in a clean Git worktree.

If `seshat` is unavailable, explain that the Python package `seshat-bi` must be
installed; report a pending state rather than simulating helper output.
