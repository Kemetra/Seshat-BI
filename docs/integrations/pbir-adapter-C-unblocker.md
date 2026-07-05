# Increment C unblocker -- how to provide a real page-background sample

**Status of increment C:** held / blocked-on-real-wire-format.
**Reason:** no verified PBIR page-background *image* structure was found from any real
source (the page schema delegates to `formattingObjectDefinitions`, which does not
contain it; `gh search code` and the public PBIP sample repos turned up no `page.json`
carrying a background image; and no committed surface-2 asset exists in this repo).
**We will not ship a schema-guess** or lower the grounding bar A and B were built to
(both were proven against real Microsoft-authored wire format). Increment C stays held
until a real Desktop-authored example exists.

This guide tells you exactly how to produce that example. It takes ~5 minutes in
Power BI Desktop.

## What to produce (2 things)

1. A real `page.json` that contains a **canvas/page background IMAGE** (not just a
   color).
2. The **background image asset itself** and its `report.json` registration (the
   resource entry Desktop writes when you add the image).

## Steps in Power BI Desktop

1. Open (or create) a PBIP project. If "Save as Power BI Project" is missing:
   **File > Options and settings > Options > Preview features > Power BI Project
   (.pbip) save option**, then save via **File > Save as > Power BI Project (.pbip)**.
2. Select a report page (click empty canvas).
3. Open the **Format** pane (the page's format, not a visual's):
   **Format your report page > Canvas background**.
4. Set **Image** > **Add image** and pick any small PNG/JPG (a plain gradient or
   logo is fine -- content does not matter, only the structure).
5. Set **Image fit** to **Fit** and **Transparency** to **0%**.
6. **Save** the project (Ctrl+S) so Desktop writes the PBIR files.

## Which files to hand back

From the saved `*.Report/` folder, provide these (a zip or the raw files):

| File | Why we need it |
|------|----------------|
| `definition/pages/<pageId>/page.json` | the real `objects.background` block with the **image** property -- the exact wire structure we must not guess |
| `definition/report.json` | the `resourcePackages` **RegisteredResources** entry Desktop wrote for the image (name -> path mapping) |
| `StaticResources/RegisteredResources/<the image file>` | the actual committed asset the page references (a surface-2 asset) |

The image can be any throwaway picture -- we only need the JSON *shape* and one real
registered-resource example. No real data, no secret, nothing sensitive.

## What happens once you provide it

With a real `page.json` background block in hand, increment C is built exactly like
A and B:

- a `tests/fixtures/pbir/` fixture copied from your real example (so the writer is
  proven against real wire format, never a guess);
- a `pbir-set-page-background` writer that references a committed surface-2 asset by
  its RegisteredResources name and sets the page `objects.background` image +
  scaling + transparency -- allow-list-only, deterministic, all-or-nothing, no
  external dependency (ADR 0015);
- the surface-2 purity rule enforced (no data baked into the image reference);
- the honest caveat that C references an asset a human/designer produced (the kit
  specs and references surface-2 assets; it does not generate the image).

## Why not just ship background *color* instead

Background color/transparency is the **theme's page-fill default** (surface 3), which
Slice 1 already sets (`retail theme-gen` writes `background` into the theme). Shipping
color as "increment C" would deliver an adjacent, already-covered thing and leave the
actual backgrounds goal (a surface-2 image) unmet -- a silent reframe. C is the image
reference or it is held.

## See also

- The adapter integration doc: `docs/integrations/pbir-adapter.md` (increments A/B
  shipped; C enumerated).
- Authorization: `docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md`.
- Spec: `specs/106-pbir-authoring-adapter/spec.md` (US2 = backgrounds).
- The surface-2 template C will fill: `templates/background-spec.yaml`.
