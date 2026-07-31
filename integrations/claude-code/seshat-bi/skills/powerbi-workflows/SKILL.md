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
against the committed dashboard set (`--proposal`/`--tuple`), and
`seshat dashboard-gaps` inventories design-blocking gaps before any layout
work. The `dashboard-gaps` `--page-intent` file is a YAML mapping with a
`questions:` list (each question naming its required metrics and dimensions);
start from the page-intent example the kit ships and see the
dashboard-gap-detector guide for the shape. A missing, unreadable,
or wrong-format page-intent is refused with a named error and exit 2 -- it is
never an empty "no gaps" read.

Data-bound visual design requires approved metric contracts, committed
semantic-model evidence, AND a committed narrative brief. The narrative brief
(`mappings/<table>/narrative-brief.md`, frozen `seshat.narrative-brief/v1`
schema) is the NEW narrative gate: a design that binds visuals to contracts but
cannot say which owner decision each page serves is itself a gap. Author the
brief FIRST via the `bi-analyst-knowledge` derivation route (ranked
decision-questions, one framing per question, a story order, honest `[GAP]`
entries); its absence is a named blocker, not a warning -- stop and name it.

With all three gates present, produce reviewable design guidance -- a layout
plan, a visual list, and a THREE-WAY binding map (visual -> contract ->
decision-question) where every data-bound visual binds to exactly one approved
contract AND answers at least one brief decision-question. An orphan in either
direction is a defect; every declared page must serve at least one decision; and
every headline (KPI-card class) visual must answer a `stage: overview` question
that names a comparison -- a bare total on a headline is a defect. Give the map a
machine-readable `seshat.binding-map/v1` front section and check it read-only
with `seshat narrative-check --table <t> --binding-map` (and the brief with
`seshat narrative-check --table <t>`); a clean check is evidence for the human
review, never an approval. Slicers and filters belong to a compact filter rail
that never dominates the canvas, and each slicer's field and default selection is
part of the reviewable design. Without the gates, stop and name the missing one.
For the analyst framing catalog + derivation route load `bi-analyst-knowledge`;
for metric meaning load `retail-kpi-knowledge`; for measure semantics load
`bi-dax-knowledge`.

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

A clean binding report does NOT mean the model loads. It checks BINDINGS only;
it does not verify TMDL syntax, so a model with a TMDL defect can pass it and
still fail to open in Desktop. Never report "validated" or "Desktop-ready" on
the strength of this check alone -- say bindings resolve, and name TMDL
loadability as unverified.

When you have hand-authored TMDL, the installed
`seshat tmdl-doc-comment-lint --model <X.SemanticModel>` helper catches ONE
mistake that is otherwise invisible until Desktop: a `///` documentation block
followed by a blank line instead of the declaration it documents, which makes
Desktop reject the whole project. It checks that one rule and nothing else --
it is NOT a TMDL syntax validator, so a pass does NOT mean the TMDL is valid or
that Desktop can load the model. TMDL loadability stays unverified either way;
running both helpers narrows two known classes, it does not clear the model.

## Reopening Desktop after an external edit

Power BI Desktop does not re-read PBIR/TMDL files edited on disk: a running
Desktop serves its in-memory session, and a reopen via File > Open or the
Recent list restores cached view state from `.pbi/localSettings.json` -- the
on-disk edits stay invisible and the old layout (plus phantom error cards) can
persist across close/reopen cycles. After any agent-authored write to a
Desktop-owned project, follow this protocol before a human looks at the
report:

1. Fully quit Desktop and verify both `PBIDesktop.exe` and `msmdsrv.exe` are
   gone -- closing the report tab is not enough.
2. Bump the modification times of the edited `definition/` files so they are
   newer than Desktop's last-known state.
3. Move `.pbi/localSettings.json` aside for BOTH the `.Report` and the
   `.SemanticModel` folders (Desktop regenerates it, with no stale view state
   left to restore).
4. Reopen the project by double-clicking the `.pbip` in File Explorer, not
   from Desktop's Recent list.
5. If Desktop prompts to save a stale session, choose "Don't Save" so the old
   in-memory layout does not overwrite the good on-disk edits.

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
