---
name: pbir-authoring-adapter
description: >-
  The Power BI report-AUTHORING adapter (F034 completion). Use when someone asks to
  apply a generated theme to a committed PBIR report, or (later increments) to set
  visual formatting or a page background by writing the report's PBIR JSON directly
  -- the settings a human sets by hand in the Power BI UI. This is a COMPANION
  execution/authoring adapter (the F029-dbt / F030-Dagster pattern), NOT part of the
  static DEFINE/CHECK core. It writes committed PBIR JSON within a tight allow-list,
  deterministically and validated; it uses NO pbi-cli, NO live Power BI, NO external
  dependency, and NO network. It grants no readiness pass and emits no score.
---

# pbir-authoring-adapter

The adapter that completes F034: it writes the committed PBIR report the kit
previously left for a human to build in Power BI Desktop. Authorized by
**ADR 0015** (owner-ratified 2026-07-05), which lifts spec-001 FR-008/FR-009 *for
this bounded adapter only* -- the static core stays forbidden from writing PBIR.

## What it is (and is NOT)

- It **is** a companion authoring adapter: reads a generated theme (Slice 1
  `retail theme-gen`) + committed PBIR, WRITES committed PBIR JSON within an
  allow-list, and validates every write.
- It is **NOT** the brain: it defines no metric, mapping, or semantic logic; it
  writes formatting/wiring, never business meaning.
- It is **NOT** publish-capable: it stops at the committed on-disk PBIR. Publishing
  to a live workspace is the parked F016 adapter (separate, gated).
- It does **NOT** build a dashboard from nothing: it restyles/positions visuals a
  human authored. "Great professional dashboards" is a design-intelligence layer
  that would ride on top -- this adapter is the mechanism, not that layer.

## The boundary (carry into every increment)

1. **Allow-list only.** Write ONLY the declared formatting/wiring properties (see
   `templates/pbir-adapter-contract.md`). Increment A's allow-list: the report's
   `themeCollection.baseTheme` + its `resourcePackages` item + the BaseTheme
   resource file. Nothing else -- no `visual.json`, no `page.json` geometry, no
   semantic-model file.
2. **No external dependency.** No pbi-cli, no Power BI MCP, no live connection, no
   network. stdlib `json` + `pathlib` only. The tool is complete in itself.
3. **Deterministic + validated + reversible.** Byte-identical re-run; reviewable git
   diff; stage -> validate (valid JSON + `$schema` preserved + round-trip stable +
   R1 model-ref + R2 authoring-lint) -> commit-or-roll-back; all-or-nothing.
4. **Evidence, not approval.** A successful write is evidence formatting was applied;
   it moves NO readiness stage and emits NO score (hard rule #9). The
   `dashboard_ready` / design-review sign-off stays a named human's decision.
5. **The core polices; the adapter writes.** `seshat check` R2 is the read-only core
   lint over the written report; the writer (`src/seshat/pbir_theme_apply.py`) is the
   adapter. The core never writes PBIR (ADR 0015 decision 1).

## Increment A -- apply a generated theme (SHIPPED)

`retail pbir-apply-theme --theme <theme.json> --report <*.Report/>` writes the theme
as a BaseTheme resource and repoints `report.json`'s `themeCollection` at it. Works
on an empty report page (no visuals needed). This is the safe smallest slice.

## Increment B -- per-visual formatting (SHIPPED)

`retail pbir-format-visual --visual <visual.json> --formatting <json>` sets
allow-listed formatting under a visual's `objects` (chart-content: legend, labels,
dataPoint, axes) and `visualContainerObjects` (chrome: border, title, subTitle,
background, dropShadow) subtrees. **The FR-003 guarantee:** the visual's data
binding (`query` + `visualType`) is asserted byte-identical before+after; the write
is refused if it would change. It formats a visual a human already authored -- it
never binds data or creates a visual. (Latent until a human builds a visual in
Desktop; there is no live target to format yet.)

## Increment C -- page background (SHIPPED)

`retail pbir-set-page-background --asset <img> --report <*.Report/> --page <name>
[--scaling Fit|Fill|Normal]` sets a page's canvas background to a committed surface-2
image asset: it copies the asset into `StaticResources/RegisteredResources/`,
registers it in `report.json` (the RegisteredResources package), and references it
from `page.json` `objects.background` via a `ResourcePackageItem` URL + name +
scaling. Allow-list-only: touches ONLY `objects.background` + the RegisteredResources
package -- every other page object (e.g. `outspacePane`) and report key is preserved.
Surface-2 purity: references a static image, bakes no data into it. The wire format
(`ResourcePackageItem`, `PackageType: 1`) was taken verbatim from a real
Desktop-authored sample -- it was NOT guessed (increment C was held until that sample
existed).

## Increment D -- visual geometry / layout (SHIPPED)

`retail pbir-set-geometry --visual <visual.json> --geometry <json>` writes ONLY a
visual's layout rectangle -- `x`, `y`, `width`, `height`, `z` (stack/tab order) -- for
a visual that already exists and is already on the approved binding-map. It repositions
existing truth; it NEVER changes `visualType`, creates/deletes a visual, or adds/removes
a page (creation is authoring truth, out of scope here). Off-canvas positions are
rejected; overlap is allowed (a design judgment). Authorized separately by ADR 0016
(the formatting-only ADR 0015 deliberately refuses geometry). No `--force`: position
keys always pre-exist, so a differs-then-refuse gate would block every real move;
overwrite safety is the reviewable git diff + human ratification.

## Hard stops

- STOP before writing anything outside the current increment's allow-list.
- STOP if ADR 0015 is not the recorded authorization (never self-grant the lift).
- STOP at the on-disk PBIR -- never open a live Power BI / workspace (that is F016).

## See also

- Authorization: `docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md`
  (A/B/C), `docs/decisions/0016-pbir-adapter-geometry-increment-d.md` (D geometry),
  and `docs/decisions/0017-pbir-creation-primitive.md` (the spec-123 blueprint->PBIR
  compiler, which CREATES pages/visuals -- a separate capability beyond this adapter).
- Spec / plan / tasks: `specs/106-pbir-authoring-adapter/{spec,plan,tasks}.md`.
- The contract: `templates/pbir-adapter-contract.md`.
- The enumerated shape + allow-list: `docs/integrations/pbir-adapter.md`.
- The writer + verb: `src/seshat/pbir_theme_apply.py` (`retail pbir-apply-theme`).
- The core lint: `src/seshat/rules/pbir.py` (R2).
- The theme source consumed: `src/seshat/theme_gen.py` (`retail theme-gen`, Slice 1).
- The parked publish adapter (separate): F016.
