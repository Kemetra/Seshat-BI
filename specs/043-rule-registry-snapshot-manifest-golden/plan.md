# Implementation Plan: Rule Registry Snapshot Manifest (golden-file rule inventory)

**Branch**: `043-rule-registry-snapshot-manifest-golden` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/043-rule-registry-snapshot-manifest-golden/spec.md`

## Summary

Generate `docs/rules/rules-manifest.json` from `registry.all_rules()` (each entry = exactly
`id` + `title`) via a `retail` CLI subcommand, and add a stdlib-only golden-equality snapshot test
(`tests/unit/test_rules_manifest_snapshot.py`) that compares the committed manifest against the
live registry and FAILS CLOSED on drift (with newline-normalized, UTF-8 no-BOM comparison so it
cannot flake under `core.autocrlf=true`). Correct the stale "26 rules" text in the live
constitution principle body so documented counts cite the generated manifest. This adds NO new
registered rule and NO new `EXPECTED_RULE_ID` -- it is a test-only golden assertion, not a gate
rule. It is meta-infrastructure that hardens the existing static gate; it advances no readiness
stage.

## Technical Context

**Language/Version**: Python 3.13 (repo interpreter); stdlib-only for this feature (`json`,
`pathlib`, `argparse`).

**Primary Dependencies**: NONE new. Reuses `retail.registry.all_rules()`, `retail.core.RegisteredRule`,
and the existing `retail.cli` argparse seam. Test uses `pytest` (already in the repo).

**Storage**: A committed text artifact -- `docs/rules/rules-manifest.json`. No database.

**Testing**: `pytest` unit test, marked `@pytest.mark.unit`.

**Target Platform**: CI + local dev on Windows (`core.autocrlf=true`) and Linux. Must be
cross-platform byte-stable.

**Project Type**: Single project (existing `src/retail` CLI + `tests/unit`).

**Performance Goals**: N/A -- inventories ~33 entries; runs in milliseconds.

**Constraints**: stdlib-only; no DB/network/Power BI dependency; UTF-8 no-BOM; deterministic
`\n`-terminated serialization with stable key order; test normalizes line endings before compare.

**Scale/Scope**: One generator subcommand, one golden JSON, one snapshot test, one `.gitattributes`
line, two corrected constitution lines. No more.

## Constitution Check

*GATE: Must pass before implementation.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS. The snapshot test fails closed on drift
  (enforced, not advised). It adds NO new `EXPECTED_RULE_ID` and does not weaken the gate -- it is
  a test sitting upstream of the id-set guard, not a new rule.
- **Principle VII (C086 is an example)**: PASS. The manifest carries only generic rule ids/titles
  (S/D/C/R/G/P/A/B families); no per-table, billing, segment, or PII data flows in.
- **Principle VIII (Static-First Governance)**: PASS. Generator + test are stdlib-only, CI-able,
  no DB/network/Power BI; they inventory committed code and execute no rules.
- **Principle IX (Secrets & Reproducibility / Windows-safe text)**: PASS *by construction* --
  this is the load-bearing risk. The manifest is UTF-8 no-BOM, stable key order, `\n` endings,
  trailing newline; the snapshot test normalizes line endings + reads UTF-8 before comparing; a
  `.gitattributes` entry pins the file to `text eol=lf`.
- **Hard rule #7 (generic only)**: PASS. id + title only; no worked-example enrichment.
- **Hard rule #8 (docs/static-first hardening favored)**: PASS. A generated inventory + golden
  test is exactly the low-risk static hardening this rule favors.
- **Hard rule #9 (no fake confidence)**: PASS. The manifest is an EXACT inventory (id+title
  equality), never a numeric confidence/health score.

No violations -> Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/043-rule-registry-snapshot-manifest-golden/
|-- spec.md              # Stage 2 output
|-- plan.md              # This file
|-- tasks.md             # Stage 4 output (/speckit-tasks)
|-- analysis.md          # Stage 5 output (/speckit-analyze) -- repo convention
|-- plan-review.md       # Stage 6 output (adversarial review)
`-- checklists/
    `-- requirements.md  # spec quality checklist
```

### Source Code (repository root)

```text
src/retail/
|-- cli.py               # ADD a `manifest` subcommand (reuses all_rules() already imported)
|-- registry.py          # UNCHANGED -- the inventory source of truth
`-- core.py              # UNCHANGED -- RegisteredRule(id, rule, title)

docs/rules/
`-- rules-manifest.json  # NEW generated artifact (created by the generator, committed)

tests/unit/
|-- test_rules_manifest_snapshot.py  # NEW golden-equality test (fails closed on drift)
`-- test_rules_wiring.py             # UNCHANGED -- existing id-set drift guard (no new id)

.gitattributes           # ADD: docs/rules/rules-manifest.json text eol=lf
.specify/memory/constitution.md      # EDIT lines 377+381 only (stale "26 rules" -> cite manifest)
```

**Structure Decision**: Single-project layout. The generator is a `retail` CLI subcommand
(spec Q1) so it reuses the existing argparse seam and import-side-effect registration; no new
top-level module tree. The committed JSON lives under a new `docs/rules/` directory.

## Implementation Notes (seam, not over-build)

- **Generator**: a small function that takes `all_rules()` and returns the manifest data
  structure (list of `{"id", "title"}` in a stable order), plus a serializer that writes UTF-8
  no-BOM with `\n` and a trailing newline. Wired behind a `retail manifest` subcommand. A
  `--check` style flag is OUT OF SCOPE for the first step (the snapshot test already enforces
  drift); add the seam, not the extra mode.
- **Stable order**: sort entries by `id` (or preserve registration order if that is already
  deterministic) -- the plan mandates a single deterministic order; tasks pick and document it.
- **Snapshot test**: read the committed file as UTF-8, normalize line endings, parse JSON, and
  assert equality against the manifest data derived from the live `all_rules()`. On mismatch,
  emit an actionable message (drifted/missing/unexpected ids + "regenerate and commit").
- **Constitution edit**: correct ONLY the two live-principle-body lines (377 + 381). Do NOT touch
  historical Sync-Impact-comment occurrences of older counts.
- **No deferred capability**: nothing here depends on F016 (Power BI Execution Adapter) or the
  F031-F033 spec-only runtimes.

## Out of Scope (YAGNI)

- No new `@register` rule; no new `EXPECTED_RULE_ID`; no change to `retail check` behavior.
- No `retail manifest --check` CI-verify mode (the snapshot test covers drift for the first step).
- No severity/family/count fields in the manifest.
- No rewrite of the historical constitution Sync-Impact comments.
- No DB/network/Power BI integration.
