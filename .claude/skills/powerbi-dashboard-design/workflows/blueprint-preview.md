# blueprint-preview (spec 123, US4)

Surface 1 (report visuals), a REVIEW aid layered on top of an already-authored
page blueprint. Open this workflow when someone asks to "preview the blueprint",
"see the design before it's built", or "show me what this page will look like"
-- BEFORE any PBIR implementation. It is the deterministic, no-live-data
counterpart of `page-blueprint.md` (which authors the design) and
`visual-implementation-review.md` (which checks BUILT PBIR against the design,
after the fact). This workflow checks nothing and builds nothing; it renders.

## Scope (read first)

This workflow renders a **deterministic, placeholder-only SVG** from artifacts
that are ALREADY committed: a page blueprint (`templates/dashboard-page-blueprint.yaml`
shape), its visual specs (`templates/visual-spec.yaml` shape), the report
composition (`templates/report-composition.yaml` shape), and the layout grid
(`design/grids/16x9-grid.yaml` or the mobile grid). It does NOT:

- author or edit the blueprint / visual specs / composition (that is
  `page-blueprint.md` + `visual-design-system.md` + the coordinator, US2);
- read a live database, call Power BI, or produce any real business figure
  (SEC-001 / SEC-002) -- every KPI/trend/table value in the preview is the
  literal token `PLACEHOLDER`, never a number;
- create, touch, or reference any PBIP/PBIR/DAX artifact (FR-016) -- this is
  not F016 territory;
- grant `dashboard_ready: pass` or any approval -- the preview is a REVIEW aid,
  not a sign-off (Principle V; the human blueprint review still owns approval).

## The one load-bearing rule: pure function, not free-hand rendering

**Never hand-draw or free-write the SVG.** Determinism (FR-015: identical
inputs -> identical output; SC-006) is the product, and an agent free-handing
markup cannot guarantee byte-identical reruns. Always call the pure library
function -- never improvise markup, never invent a business value to make the
preview "look realistic."

```python
from pathlib import Path
from seshat.blueprint_preview import render_blueprint_preview

svg = render_blueprint_preview(
    blueprint_path=Path("mappings/<subject-area>/design/<page>-blueprint.yaml"),
    visual_spec_paths=[Path("mappings/<subject-area>/design/visuals/<v>.yaml"), ...],
    composition_path=Path("mappings/<subject-area>/design/report-composition.yaml"),
    grid_path=Path("design/grids/16x9-grid.yaml"),
)
```

`render_blueprint_preview` (`src/seshat/blueprint_preview.py`) is read-only: it
opens exactly the four YAML paths given and returns a string. It performs no
write of its own -- if you want the preview committed for review, write the
returned text yourself (see "Where the preview lives" below).

## Step 1 -- Confirm the artifacts exist and are the APPROVED set

Preview the blueprint the reviewer is actually going to approve, not a draft
mid-edit. Confirm the page blueprint, its visual specs, and the composition are
the committed files under `mappings/<subject-area>/design/` (not
`templates/`), and name each path explicitly rather than guessing.

If any of the four inputs is missing, `render_blueprint_preview` degrades that
input to an empty structure rather than raising (never fabricates a
substitute) -- treat a suspiciously bare-looking preview (missing sections,
missing visuals) as a signal to STOP and confirm the right paths were passed,
not as "the design is actually simple."

## Step 2 -- Render, once per page

Call the function once per page blueprint (a report is several pages; render
each separately, matching "one file = one page" from `page-blueprint.md`). The
rendered SVG's page title line includes the page's 1-based order within the
composition (e.g. `page 1/3`), so the reviewer can tell where this page sits in
the report without opening the composition file separately.

## Step 3 -- What the preview represents (verify against FR-015)

Confirm the rendered SVG shows, for the page under review:

- the page name, its order within the report, audience, and business question;
- which of the seven sections are present (header / kpi_strip / main_insight /
  diagnostic / exception_detail / filter_rail / footer_status);
- every visual's id, type, grid position/size, and the metric-contract NAME it
  binds to (never a formula/DAX -- the contract owns the definition);
- slicers/filters, the narrative region (headline / so_what / recommended
  action / key exception), inter-page navigation, and a freshness/DQ line;
- references (by name/path, never inlined) to the theme, the desktop grid, and
  the mobile grid -- the accessibility/RTL intent is cited via the a11y/RTL
  checklist reference, not re-derived here.

Every value slot that would otherwise carry a real business figure reads the
literal token `PLACEHOLDER`. A request for "realistic preview numbers" gets the
same placeholder-only output -- the function has no data-source input at all,
so it is structurally unable to invent one (US4 AC#2 / SEC-002). Explain this
to the requester rather than trying to satisfy the request some other way.

## Step 4 -- Confirm determinism across revisions (the review value)

Re-render after any committed change to the blueprint/visual-specs/composition
and diff the two SVG strings (they are plain text, so a normal text diff
works). Because the renderer is a pure function of its committed inputs, an
unchanged design set always reproduces byte-identical output -- a reviewer can
trust that a diff in the preview reflects an ACTUAL design change, never
rendering noise.

## Where the preview lives (if committing it for review)

`data-model.md` (US4) places a committed preview at
`mappings/<subject-area>/design/preview/<page_id>-preview.svg`. Writing that
file is the CALLER's responsibility (a human or another workflow step saving
the string this function returns) -- `render_blueprint_preview` itself performs
no write, consistent with the read-only discipline every other design-review
tool in this skill follows (`dashboard-qa.md`, `visual-implementation-review.md`).

## Stop-and-ask (Principle V)

STOP and ask rather than guessing when:

- it is unclear which committed blueprint/visual-spec/composition set is the
  one actually up for review (a stale draft vs. the latest commit);
- a reviewer asks for the preview to show a specific number "just for this
  review" -- that is a request to fabricate data (SEC-002); explain the
  placeholder-only boundary instead of working around it;
- the preview reveals the design itself looks wrong (missing section, orphan
  visual with no contract name) -- that is a `page-blueprint.md` /
  `visual-design-system.md` fix, not something this workflow patches.

## See also

- The router + the four-surface table: `../SKILL.md`.
- The design-authoring workflow this previews: `page-blueprint.md`.
- The BUILT-PBIR counterpart (after the fact, not before): `visual-implementation-review.md`.
- The pure function itself: `src/seshat/blueprint_preview.py`.
- The four input shapes: `templates/dashboard-page-blueprint.yaml`,
  `templates/visual-spec.yaml`, `templates/report-composition.yaml`,
  `design/grids/16x9-grid.yaml` (desktop) / `design/grids/mobile-grid.yaml` (phone).
- Where the preview's committed location is decided: `specs/123-governed-dashboard-intelligence/data-model.md` (US4).
