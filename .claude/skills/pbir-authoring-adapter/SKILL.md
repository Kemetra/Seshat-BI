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
5. **The core polices; the adapter writes.** `retail check` R2 is the read-only core
   lint over the written report; the writer (`src/retail/pbir_theme_apply.py`) is the
   adapter. The core never writes PBIR (ADR 0015 decision 1).

## Increment A -- apply a generated theme (SHIPPED)

`retail pbir-apply-theme --theme <theme.json> --report <*.Report/>` writes the theme
as a BaseTheme resource and repoints `report.json`'s `themeCollection` at it. Works
on an empty report page (no visuals needed). This is the safe smallest slice.

## Increments B and C (planned, separate; NOT built here)

- **B -- per-visual formatting**: writes allow-listed `visual.json` formatting keys;
  needs a report with visuals a human already authored.
- **C -- backgrounds**: sets a page background to a committed surface-2 asset.

## Hard stops

- STOP before writing anything outside the current increment's allow-list.
- STOP if ADR 0015 is not the recorded authorization (never self-grant the lift).
- STOP at the on-disk PBIR -- never open a live Power BI / workspace (that is F016).

## See also

- Authorization: `docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md`.
- Spec / plan / tasks: `specs/106-pbir-authoring-adapter/{spec,plan,tasks}.md`.
- The contract: `templates/pbir-adapter-contract.md`.
- The enumerated shape + allow-list: `docs/integrations/pbir-adapter.md`.
- The writer + verb: `src/retail/pbir_theme_apply.py` (`retail pbir-apply-theme`).
- The core lint: `src/retail/rules/pbir.py` (R2).
- The theme source consumed: `src/retail/theme_gen.py` (`retail theme-gen`, Slice 1).
- The parked publish adapter (separate): F016.
