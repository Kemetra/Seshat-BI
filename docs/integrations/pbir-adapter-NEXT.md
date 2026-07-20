# PBIR-authoring adapter -- session handoff / what to do next

> A durable, in-repo resume note so this can be continued from any device or a later
> session. Written 2026-07-05, updated 2026-07-07. If anything here disagrees with
> the code, the code + `git log` win -- re-verify before acting.

## Where things stand (all on `main`)

The goal: a self-contained tool that generates themes/backgrounds and formats a
Power BI report's visuals -- writing the PBIR/PBIP JSON directly, no external tool
(no pbi-cli, no live Power BI). Authorized by ADR
`docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md` (A/B/C) and ADR
`docs/decisions/0016-pbir-adapter-geometry-increment-d.md` (D).

| Piece | Status | Verb / where |
|-------|--------|--------------|
| Slice 1 -- theme generator | **SHIPPED** (PR #204) | `retail theme-gen` -> `src/seshat/theme_gen.py` |
| Adapter A -- apply theme to a report | **SHIPPED** (PR #206) | `retail pbir-apply-theme` -> `src/seshat/pbir_theme_apply.py` |
| Adapter B -- format cards/charts | **SHIPPED** (PR #207) | `retail pbir-format-visual` -> `src/seshat/pbir_visual_format.py` |
| Adapter C -- page background image | **SHIPPED** (2026-07-06, from a real owner sample) | `retail pbir-set-page-background` -> `src/seshat/pbir_page_background.py` |
| Adapter D -- visual geometry (position/size/z) | **SHIPPED** (2026-07-06, PR #216) | `retail pbir-set-geometry` -> `src/seshat/pbir_geometry.py` |
| Core lint R2 (polices written report.json) | SHIPPED | `src/seshat/rules/pbir.py` |

Everything above is green on `main` (`seshat check` exit 0; full `pytest -m unit`
passing). The four verbs chain: generate a theme -> apply it to a report -> format
individual visuals -> lay out (position/size/stack order) existing bound visuals.

**All four adapters ship LATENT**: they are built and tested against fixtures, but
the real `powerbi/RetailStoreSales.Report/` page has zero visuals, so nothing live
exercises them yet. The next real milestone for this thread is binding a first real
visual to an approved metric contract in that report -- not more adapter increments.

## Increment C (page background image) -- RESOLVED / SHIPPED 2026-07-06

Was held (blocked-on-real-wire-format). The owner provided a real Desktop-authored
sample (a page background on the c086 sales report), which revealed the wire format
that could not be guessed: the image URL is a **`ResourcePackageItem`** wrapper
(`PackageName`/`PackageType: 1`/`ItemName`), not a Literal. C was built from that real
format and shipped as `retail pbir-set-page-background`. The hold was vindicated --
guessing would have produced the wrong structure. (Background *color* was correctly
NOT used as a substitute; that is the surface-3 theme fill.)

`docs/integrations/pbir-adapter-C-unblocker.md`'s recipe is now historical record of
how the real wire format was obtained -- no action needed, kept for the pattern (ask
the owner for a real Desktop sample rather than guessing a schema).

## Increment D (visual geometry: position/size/z) -- SHIPPED 2026-07-06

Authorized by ADR 0016 (ratified same day). Writer verified against the real c086
report's wire format (`visual.json` top-level `position {x,y,z,height,width,tabOrder}`;
`page.json` top-level `width`/`height` for canvas). Mirrors increment B's shape
(allow-list, FR-003 snapshot-preserve, round-trip, clean errors). The off-canvas guard
reads REAL canvas dims from `page.json` -- never hardcoded -- proven by a dedicated
fixture (non-default 1600x900 canvas + a decoy visual that is off-canvas at 1600x900
but on-canvas at a hardcoded 1280x720, so a hardcoding writer fails the test). Overlap
is allowed (design judgment, not mechanically checkable); only off-canvas is rejected.
`visualType` changes remain forbidden (FR-003-guarded, unchanged).

## Other open threads (not blocking, lower priority)

- **The real bottleneck: no live target.** All four adapters (A/B/C/D) are proven only
  against `tests/fixtures/pbir/` fixtures. The committed `powerbi/RetailStoreSales.Report/`
  page still has zero real visuals, so nothing exercises A/B/C/D for real. Getting a
  first real visual bound to an approved metric contract in that report is the actual
  next milestone for this thread -- not another adapter increment.
- **Smart-formatting layer (the actual "great dashboards automatically" dream):** a
  design-intelligence step where Opus picks good formatting from the generated theme
  and drives A/B/C/D. This is a NEW feature -- needs its own brainstorm -> spec -> plan,
  not a quick build. A first slice (formatting-plan ledger + DL7 lint) has since shipped
  separately (PR #211); see `docs/decisions/` for the verb-C background-row decision
  (PR #214, held at `needs-owner-decision` by design -- not a bug, see the ledger's
  Principle-V note in `templates/formatting-plan.md`).
- **End-to-end hardening:** an integration test that chains theme-gen -> apply ->
  format -> geometry on one fixture report (proves all four verbs compose). Small;
  agent can do it autonomously anytime.
- **same-store-sales-growth / A11** (older, unrelated thread): still `[planned]`,
  deferred by the H9 D1=C ruling; needs an owner A11 decision to seed.

## How to resume (say any of these to the agent)

- "Get a real visual into the report" -> agent works the metric-contract -> visual
  binding path so A/B/C/D have something live to act on.
- "Start the smart-formatting design" -> agent brainstorms/continues the
  design-intelligence layer.
- "Do the end-to-end hardening" -> agent adds the chained integration test.

## Pointers

- Adapter overview + increments: `docs/integrations/pbir-adapter.md`
- C unblocker recipe (historical): `docs/integrations/pbir-adapter-C-unblocker.md`
- Authorization ADRs: `docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md`
  (A/B/C), `docs/decisions/0016-pbir-adapter-geometry-increment-d.md` (D)
- Spec: `specs/106-pbir-authoring-adapter/spec.md`
