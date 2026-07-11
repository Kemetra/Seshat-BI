# PBIR geometry writer (increment D) -- design

- **Date:** 2026-07-06
- **Author:** agent (grounded in the real c086 wire format + advisor review) + Ahmed
  Shaaban (ratified ADR 0016, resolved its 3 open questions).
- **Surface:** the EXECUTE side of the PBIR authoring adapter -- a new `apply_verb: D`
  that writes the position + size of an existing, binding-mapped visual, plus a geometry
  authoring-lint. Authorized by `docs/decisions/0016-pbir-adapter-geometry-increment-d.md`.
- **Status:** design, pending owner review before writing-plans.

## What this is (and the ratified boundary)

Increment D lets the adapter re-lay-out visuals that ALREADY exist and are ALREADY on the
approved binding-map -- turning the geometry anti-patterns (#1/#5/#6/#7), currently
`handoff-only`, into an applyable layout increment. Per ratified ADR 0016:

- **Lifted (writable):** a visual's `position` rectangle -- `x`, `y`, `width`,
  `height`, `z`, and `tabOrder` (z-order resolved IN-scope; `tabOrder` is the same
  stacking concept and is written consistently with `z`).
- **Excluded (still forbidden):** `visualType` (representation-as-meaning, stays
  FR-003-guarded), creating/deleting a visual or page, moving an unbound visual, and
  auto-ranking the headline (that stays `needs-owner-decision`).
- **Overlap policy:** the lint rejects OFF-CANVAS only (objective mechanical validity);
  it ALLOWS overlap (intentional layering is a design judgment the lint must not make).

## The verified wire format (read from the real c086 report, not guessed)

Confirmed against `BI/powerbi/c086 _sales.Report` (owner's report; SHAPE copied,
literals never inlined -- Principle VII):

- **Visual geometry** lives in `visual.json` at a top-level `position` object:
  `{"x": <num>, "y": <num>, "z": <num>, "height": <num>, "width": <num>, "tabOrder": <num>}`.
  (All numbers; the real sample had float x/y/height/width and integer z/tabOrder=2000.)
- **Page canvas dimensions** live in `page.json` at top-level `width` + `height`
  (the real sample: 1280 x 720 -- but these MUST be READ from the file, never assumed).
- Path layout: `<report>.Report/definition/pages/<page>/page.json` and
  `.../pages/<page>/visuals/<v>/visual.json`.

## Architecture -- one writer + one lint, mirroring increment B

| Role | Where | What | New? |
|------|-------|------|------|
| EXECUTE (apply) | `retail pbir-set-geometry` -> `src/seshat/pbir_geometry.py` | write a visual's `position` rectangle, preserving binding (FR-003) + validating on-canvas | new verb |
| CHECK | a geometry guard INSIDE the writer (pre-write) + the existing R1/authoring-lint family | reject off-canvas / negative / non-numeric rectangles, read REAL canvas dims | new guard |
| PROPOSE | `formatting-plan.md` workflow (`apply_verb: D` rows) | later: emit D rows (out of THIS slice; slice = the writer + guard) | deferred |

The writer mirrors `pbir_visual_format.py` exactly: allow-list, snapshot-preserve the
binding, round-trip-stable staged JSON, `PbirGeometryError` (clean, never a traceback),
a `pbir_geometry_main(args)` CLI entry. NO pbi-cli / live Power BI / network; stdlib
json + pathlib only. Grants no readiness pass, emits no score.

## The writer -- `set_geometry(visual_json, position, force)`

- Reads the target `visual.json` (utf-8-sig); requires a `visual` object + a `position`
  object (a visual with no `position` is malformed for this verb -> clean error).
- `position` input maps the allow-listed keys to numbers:
  `{"x": .., "y": .., "width": .., "height": .., "z": .., "tabOrder": ..}`. Keys are
  optional per call (you may move without resizing); ANY key outside the allow-list is
  refused. Every provided value must be a number (int/float); non-numeric -> clean error.
- **FR-003 guarantee (unchanged):** snapshot `visual.query` + `visual.visualType` before
  and after; refuse to write if either changed. Geometry is added BESIDE the binding
  guard, never through it.
- **On-canvas guard (the load-bearing check):** locate the sibling `page.json`
  (`visual_json.parents[2] / "page.json"` -- `.../<page>/visuals/<v>/visual.json` ->
  `.../<page>/page.json`), read its real `width`/`height`. Compute the RESULT rectangle
  (existing position merged with the requested keys) and reject if `x < 0`, `y < 0`,
  `x + width > canvas_width`, `y + height > canvas_height`, or any of the four is
  non-numeric. Overlap with other visuals is NOT checked (ratified: allowed).
  - If `page.json` is missing or has no numeric `width`/`height`: clean error naming the
    file -- NEVER fall back to a hardcoded canvas size (a wrong constant misjudges
    off-canvas; ADR 0016 build note).
- Overwrite: re-setting the same rectangle is idempotent; a DIFFERENT rectangle requires
  `force=True` (matches increment B's value-change gate).
- Stage -> round-trip check (`_dump(json.loads(text)) == text`) -> write utf-8/newline=\n.

## Testing -- the canvas-dims invariant is enforced, not just documented

A dedicated **generic** fixture `tests/fixtures/pbir/geometry.Report/` (Principle VII:
placeholder names, generic dims -- SHAPE from c086, no literals). Deliberately built so:

- `page.json` canvas is a **non-default 1600 x 900** (NOT 1280 x 720).
- Two visuals with `position` blocks (so overlap + order are meaningful).
- One test moves a visual to a rectangle that is off-canvas at 1600 x 900 but WOULD read
  as on-canvas under a hardcoded 1280 x 720. **A writer that hardcodes the default passes
  this write and the test FAILS.** This converts "read real canvas dims, never hardcode"
  from a caution into an enforced invariant -- the strongest guard on the one real
  correctness risk in this increment.

Other tests: writes a valid rectangle (round-trips, binding byte-identical); refuses a
`visualType`/`query` change (FR-003); refuses an out-of-allow-list key; refuses
non-numeric; refuses off-canvas (negative + overrun); ALLOWS overlap (two visuals'
rectangles intersect -> no error); missing `page.json` -> clean error (no hardcode
fallback); overwrite gated by force; CLI parses + dispatches (exit 0/2).

## Scope discipline

- Writes ONLY a visual's `position` rectangle. No `objects`, no `visualType`, no binding,
  no page/visual creation. DEFINE-adjacent EXECUTE, adapter-only; core stays forbidden.
- Ships LATENT: the real report page has zero visuals, so the writer + guard are proven
  on the fixture and are latent until a real multi-visual report lands (same posture as
  A/B/C, theme-compile, the smart-formatting layer). Stated plainly; not "it works on
  your report."
- No score, no self-granted pass. Every failure a clean `PbirGeometryError`.
- The `formatting-plan` `apply_verb: D` PROPOSAL rows are a SEPARATE later slice; this
  slice is the writer + guard + fixture only.

## The single sharpest risk that remains

The on-canvas guard is only as correct as its canvas-dims source. If `page.json` is not
where the guard looks (`parents[2]`), or a real report nests pages differently than the
fixture, the guard reads the wrong dims or errors on a valid report. Mitigation: the
guard path is derived from the SAME path convention the shipped `pbir_page_background.py`
already uses for `page.json`; the non-default-canvas test proves the dims are read (not
hardcoded); and a missing/!numeric `page.json` is a clean refusal, never a silent
hardcode. Beyond that, the whole increment is latent until a real multi-visual report
exercises it -- which is where a path-convention mismatch (if any) would surface, and is
the owner's un-blocker, not this slice's claim.

## See also

- The authorization: `docs/decisions/0016-pbir-adapter-geometry-increment-d.md` (ratified).
- The pattern it mirrors: `src/seshat/pbir_visual_format.py` (increment B).
- The `page.json` path convention it reuses: `src/seshat/pbir_page_background.py`.
- The proposer that will later emit `apply_verb: D` rows:
  `.claude/skills/powerbi-dashboard-design/workflows/formatting-plan.md`.
- `.specify/memory/constitution.md` (Principles III, IV, V, VII; hard rule #9).
