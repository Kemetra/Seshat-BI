# Implementation Plan: PBIR-authoring adapter -- increment A (theme application)

**Branch**: `106-pbir-authoring-adapter` | **Date**: 2026-07-05 | **Spec**: `specs/106-pbir-authoring-adapter/spec.md`

**Input**: Feature specification from `specs/106-pbir-authoring-adapter/spec.md`; authorization ADR `docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md` (RATIFIED).

## Summary

Build the **first, safest increment** of the PBIR-authoring adapter: **apply a
`retail theme-gen` theme to a committed PBIR report** by writing it as a BaseTheme
resource and pointing the report's `themeCollection.baseTheme` at it -- plus the
validation and the core-side authoring-lint that police the write.

**Why this increment first (Phase-0 finding, not the spec's original US1 order):**
the committed report page `powerbi/RetailStoreSales.Report/` is **empty** (a scaffold
`page.json`, ZERO `visual.json` files). Per-visual formatting (spec US1) therefore
has no live target and needs a fixture report with real visuals. But
**theme-application needs no visuals** -- it writes a BaseTheme resource + one
reference in `report.json`, exactly mirroring the committed `CY26SU05` base theme.
It works on the empty page, is immediately visible, reuses Slice 1's output almost
verbatim, and touches NO `visual.json` (avoiding the `pbip-workflow` warning against
hand-editing layout/visual files). It is the honest smallest safe slice.

**Honest scope (carried from the design review):** this increment restyles the
report's THEME (palette/fonts every visual inherits). It does NOT populate the empty
page, build visuals, or write data bindings -- FR-003 forbids that, and the human
still authors the visuals. "Edits like a human in the UI" here == the human's
"apply theme" action, not "build my dashboard."

## Technical Context

**Language/Version**: Python 3.13 (matches the kit).
**Primary Dependencies**: stdlib (`json`, `pathlib`) + `pyyaml` (already a dep). NO
pbi-cli, NO Power BI MCP, NO network, NO new dependency (ADR 0015 decision 4).
**Storage**: local committed files only -- the PBIR tree under `powerbi/*.Report/`.
**Testing**: `pytest -m unit`; a fixture PBIR report under `tests/fixtures/pbir/`.
**Target Platform**: local file transform (Windows/Linux; ASCII, UTF-8 no BOM, `\n`).
**Project Type**: a companion authoring adapter (skill + contract) + ONE new core
lint rule. Two homes -- see Structure Decision.
**Performance Goals**: n/a (a few-file deterministic transform).
**Constraints**: deterministic (byte-identical re-run), all-or-nothing per report,
traversal-guarded, no overwrite without intent, validated (round-trip + R1 + lint).
**Scale/Scope**: one report, one theme, one page-independent write per run.

## Constitution Check

*GATE: must pass before Phase 0. Re-checked after design.*

- **ADR 0015 ratified** (FR-008/009 lifted for THIS adapter only) -- the Principle-V
  gate is CLEARED. PASS.
- **Core stays forbidden from writing PBIR** (ADR 0015 decision 1): the *writer* lives
  in a companion skill/adapter, NOT in `src/retail/` rules. The only core addition is
  a READ-ONLY lint rule. PASS by design (Structure Decision).
- **Evidence-not-approval** (decision 3): a successful write moves NO readiness stage
  and emits NO score (hard rule #9). PASS.
- **No external dependency** (decision 4): stdlib + pyyaml only. PASS.
- **Deterministic + validated + reversible** (decision 5): enforced by tasks. PASS.
- **live-target-before-rule** (project discipline): the authoring-lint has no target
  until the writer produces one -> the writer task is sequenced BEFORE the lint task
  (the writer creates the lint's first live target). PASS by sequencing.
- **Generic, no tenant inlined** (Principle VII): `retail_store_sales` is a CITED
  fixture/example, never inlined into the adapter/contract/lint. PASS.

No violations -> Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/106-pbir-authoring-adapter/
├── spec.md          # done
├── plan.md          # this file
├── research.md      # Phase 0 findings (below, inlined -- small feature)
└── tasks.md         # /speckit-tasks output (NOT created here)
```

### Source Code (repository root)

Two homes -- the ADR forbids the core writing PBIR, but the lint IS core:

```text
# The companion authoring adapter (writes PBIR) -- NOT the static core:
.claude/skills/pbir-authoring-adapter/
└── SKILL.md                         # the adapter's procedure + boundary
templates/
└── pbir-adapter-contract.md         # the F024 adapter contract (like dbt's)
docs/integrations/
└── pbir-adapter.md                  # the enumerated shape + allow-list
src/retail/
└── pbir_theme_apply.py              # the deterministic theme-application writer
                                     #   (importable; a `retail` verb wraps it)

# The core-side READ-ONLY lint (police the written PBIR) -- this IS core:
src/retail/rules/
└── pbir.py                          # ADD a sibling authoring-lint to the R1 module

# Tests + fixtures:
tests/fixtures/pbir/                 # a fixture report (empty-page + a visual variant)
tests/unit/
├── test_pbir_theme_apply.py
└── test_pbir_authoring_lint.py
```

**Structure Decision**: the *writer* (`pbir_theme_apply.py` + the skill/contract) is
the companion adapter -- it may write PBIR (ADR 0015). The *lint* is a read-only
`retail check` rule added beside R1 in `src/retail/rules/pbir.py` (the core polices,
never writes). This is the ADR's core-vs-adapter split made concrete.

## Phase 0 -- research (inlined; findings that shaped this plan)

1. **PBIR is schema-versioned.** Every file carries a `$schema` URL (report `3.3.0`,
   page `2.1.0`, base theme is a plain JSON resource). "Schema UNCERTAIN" becomes
   "pin to the committed `$schema`" -- validate the written report parses + keeps its
   `$schema`.
2. **Theme application = BaseTheme resource + reference**, NOT per-visual edits. The
   committed `report.json` has `themeCollection.baseTheme -> {name, type:
   SharedResources}` + a `resourcePackages` entry pointing at
   `StaticResources/SharedResources/BaseThemes/CY26SU05.json`. Applying a generated
   theme = write `StaticResources/SharedResources/BaseThemes/<name>.json` (the theme
   JSON) + update the two references. This is the safe path.
3. **R1 exists** at `src/retail/rules/pbir.py` (`@register("R1", "PBIR model
   reference must be relative")`). The authoring-lint is a sibling there.
4. **The committed report page is EMPTY** -> tests use a fixture PBIR, not the
   committed report; and the writer must NOT require any visual to exist.

## Phase 1 -- design (contracts + data model, inlined)

**The write (deterministic):** given a generated theme JSON path + a target
`*.Report/` dir, the writer (a) validates both paths stay in-repo, (b) reads the
theme JSON, (c) writes it to `StaticResources/SharedResources/BaseThemes/<name>.json`
(refuse-without-force if present), (d) sets `report.json` `themeCollection.baseTheme.name`
= `<name>` and ensures the matching `resourcePackages` item, (e) stages all changes,
validates (JSON valid + `$schema` preserved + R1 green + round-trip stable), then
commits-or-rolls-back. Key ordering is stable (sorted where PBIR allows) for a
byte-identical re-run.

**The allow-list (this increment):** exactly two report-level write targets --
`themeCollection.baseTheme` and its `resourcePackages` item + the BaseTheme resource
file. NO `visual.json`, NO `page.json` geometry, NO semantic-model file. The
allow-list is a guard-tested constant (grows only by a reviewed change).

**The authoring-lint (core, read-only):** in `pbir.py`, a new rule that, for a
committed `*.Report/`, asserts (a) `report.json` is valid JSON keeping its `$schema`,
(b) any BaseTheme resource referenced by `themeCollection` exists at its declared
relative path, (c) no forbidden key was written into report/page JSON (the report-file
analogue of DL1's styling-only check). ERROR + locator on violation; clean report =
no finding.

## Complexity Tracking

No constitution violations -> not applicable.

## The increments AFTER this one (separate plans, not built here)

- **Increment B -- per-visual formatting** (spec US1 proper): needs a fixture report
  WITH visuals; writes allow-listed `visual.json` formatting keys. Larger; its own
  plan (and its own fixture-authoring step).
- **Increment C -- backgrounds as surface-2 output** (spec US2): sets a page
  background to a committed asset. Independent of A/B; its own plan.

Slicing rationale: A (theme) needs no visuals and is immediately shippable; B needs a
visual fixture; C is orthogonal. `writing-plans` says decompose multi-subsystem specs
-- these are three increments, planned separately.

## See also

- Spec + ADR: `specs/106-pbir-authoring-adapter/spec.md`,
  `docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md`.
- The theme source consumed: `src/retail/theme_gen.py` + `themes/` (Slice 1, PR #204).
- The existing PBIR rule extended: `src/retail/rules/pbir.py` (R1).
- The adapter-contract precedent: `templates/adapter-contract.md`, ADR 0009 (dbt).
- The committed PBIR structure this targets: `powerbi/RetailStoreSales.Report/`.
