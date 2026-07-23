# Design — `seshat pbir-validate-bindings` (issue #454)

**Status:** Approved design for a fix-branch build (autonomous recommended run,
owner's standing "go" rule). Read-only check verb; no readiness semantics change.

## Problem

Nothing in the kit checks that a committed report's field bindings actually
resolve against the semantic model before a human opens Power BI Desktop. Every
unresolved binding (missing measure, missing column, unknown entity, or a
PII-masked/renamed column — the exact ex-2 defect: `dim_staff_c086[person_name]`
vs the gold model's `staff_name_masked`) ships as a "Fix this / Something's wrong
with one or more fields" error card, discovered only inside Desktop, one
close/reopen cycle at a time. `pbir-validate-blueprint` deliberately checks
contract *identity*, not field-level resolution (its own docstring names the gap).

## Decision: a new narrow read-only check verb

`seshat pbir-validate-bindings --report <*.Report dir> --model <*.SemanticModel dir>`

Justified by the SAME check-surface precedent as R1/R2 and
`pbir-validate-blueprint` (`pbir_validate_blueprint.py:10-23`): a read-only,
scriptable surface that POLICES what writers (the compiler, pbi-cli, or a human
Desktop build) already produced. It is NOT an authoring skill and does not widen
the CLI beyond a gate (ratified Option B respected).

Alternatives rejected:
- extending `pbir-validate-blueprint --model`: that verb *requires* a blueprint +
  binding map; the reported case (Desktop-owned report, Get-Data model) has
  neither, so the gap would remain unreachable.
- a `seshat check` rule: only sees tracked files; the pre-Desktop iterate loop
  works on not-yet-committed trees. A future rule can reuse this module's core.

## Architecture

New module `src/seshat/pbir_validate_bindings.py` (pure stdlib + `yaml`-free;
`json`/`pathlib`/`re`/`difflib` + `tmdl.parse_tmdl` reuse). Two sides + a compare:

1. **Model symbol table** — scan `<model>/definition/**/*.tmdl`; split each file
   into top-level `table` segments (column-0 `table <name>` headers; Desktop
   sometimes writes multi-table `model.tmdl`, and `parse_tmdl` alone attributes
   every block to the first table), parse each segment with the shipped
   `tmdl.parse_tmdl` (reused, never reimplemented). Result:
   `{casefold(table): (table, {casefold(col)}, {casefold(measure)})}`.
   Case-insensitive because Power BI object names are case-insensitive —
   exact-case comparison would fabricate error cards that Desktop never shows.

2. **Report reference walker** — for every `<report>/definition/**/*.json`
   (visual.json, page.json, report.json, bookmarks: one walker, no bucket
   enumeration), recursively find every dict of shape
   `{"Column"|"Measure": {"Expression": {"SourceRef": …}, "Property": p}}`.
   `SourceRef` resolves either directly (`{"Entity": e}`) or through the
   document-wide alias table collected from `"From": [{"Name": n, "Entity": e}]`
   lists; an unresolvable alias is skipped (never a fabricated finding).
   Wrappers other than `Column`/`Measure` (`HierarchyLevel`, …) are out of scope
   for this increment and are ignored, stated in the module docstring.

3. **Resolution** — per reference:
   - entity not a model table → `unknown_entity` (blocked)
   - property in neither columns nor measures → `unresolved_field` (blocked);
     message names the nearest model field (`difflib.get_close_matches` over the
     entity's fields) and states the common cause: a governed rename/PII mask.
   - `Column`-wrapped but property is a measure, or `Measure`-wrapped but
     property is a column → `projection_kind` (warning) — the detection side of
     issue #456; the authoring fix lives in the generator, not here.
   Findings dedupe on (file, kind, entity, property, dimension).

## Fail-closed posture (the #453 lesson)

Never a silent "0 findings" pass over nothing:
- report `definition/` missing, or ZERO `visuals/*/visual.json` found → blocked
  naming the path ("nothing to validate here" is an error, not a pass);
- model yields ZERO parsed tables → blocked naming the path;
- any unparseable JSON under `definition/` → `unparseable_json` blocked finding
  (a corrupt visual is itself an error-card source — never skipped silently).

Visuals present but zero field references → `pass`, with reference counts in the
evidence lines so the emptiness is visible, not hidden.

## Result + CLI contract

`BindingValidationResult(status, unresolved, kind_mismatches, evidence,
grants_approval=False)` — mirrors `BlueprintValidationResult`: four-status
vocabulary (`pass`/`warning`/`not_started`/`blocked`), never a numeric score,
no field or method that can grant approval. Roll-up: any blocked-class finding →
`blocked` (exit 1); only kind mismatches → `warning` (exit 0, printed); clean →
`pass` (exit 0). stdout format mirrors `pbir-validate-blueprint`
(`status:` line, `[unresolved]`/`[kind]` lines, closing grants-no-approval note).

## Wiring surfaces (the O2 oracle makes most of these mandatory)

| Surface | Change |
|---|---|
| `src/seshat/pbir_validate_bindings.py` | new module (core + `pbir_validate_bindings_main`) |
| `src/seshat/cli/parser.py` | `_add_pbir_validate_bindings_parser` beside the blueprint one |
| `src/seshat/cli/__init__.py` | `_DISPATCH["pbir-validate-bindings"]` lazy entry |
| `docs/capabilities/capabilities.yaml` | shipped/agent-runnable entry (O2: unlisted dispatch fails) |
| `docs/tools/pbir-binding-validator.md` | dev-tree doc: inputs, finding classes, exit codes |
| `distribution/bundle-templates/shared/skills/powerbi-workflows/SKILL.md` | route the pre-Desktop check through the verb |
| `distribution/bundle-templates/claude/commands/powerbi-review.md` | mention beside `pbir-validate-blueprint` |
| `integrations/{claude-code,codex}/…` | regenerated via `scripts/export_agent_bundles.py` (CI runs `--check`) |
| `CHANGELOG.md` | feat entry closing #454 |
| `tests/unit/test_pbir_validate_bindings.py` | see below |

## Testing (TDD; deterministic, no live PBI/DB/network)

- symbol table: split multi-table `model.tmdl`; tables/*.tmdl layout; quoted
  names; measures vs columns; zero-table model → blocked.
- walker: queryState projections (Category/Y/Values); filterConfig field via
  `From`-alias resolution; sort refs; non-Column/Measure wrappers ignored;
  BOM-tolerant reads (`utf-8-sig`).
- resolution: unknown entity; missing column (with did-you-mean naming the
  masked rename); missing measure; case-difference resolves clean; #456 shape
  (dimension attribute bound as `Measure`) → warning + exit 0.
- fail-closed: no visuals → exit 1; corrupt visual.json → exit 1; empty model →
  exit 1; missing dirs → exit 1.
- CLI: main() exit codes; output lines; `grants_approval` is always False and
  the result type has no approval-granting member (mirror the FR-031 tests).
- oracle/packaging seams: capabilities entry present (existing O2 test covers),
  bundle export `--check` clean.

## Non-goals (YAGNI, stated)

No hierarchy/variation resolution, no conditional-formatting expression parse,
no auto-discovery of the model from `definition.pbir` (explicit `--model` only),
no `--format json`, no readiness-stage writes, no fix-ups of the #456 generator.
