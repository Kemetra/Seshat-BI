# Implementation Plan: CVD (Colorblind) Simulation Evidence Aid

**Branch**: `118-cvd-simulation-evidence` | **Date**: 2026-07-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/118-cvd-simulation-evidence/spec.md`

## Summary

Given ONE committed Power BI theme JSON, apply three deterministic
colour-vision-deficiency simulation transforms (protanope / deuteranope /
tritanope) to the theme's declared `dataColors` categorical palette (and any
declared sequential/diverging ramp stops), then reuse the shipped `delta_e76`
perceptual-distance function (`src/retail/color.py:83`) to MEASURE the pairwise
distance between every colour pair AFTER each simulation. Write ONE durable
companion evidence file (theme-adjacent by default, or at a reviewer-supplied
`--out` path) containing the simulated swatches, the under-simulation pairwise
deltaE, and a BLANK named-reviewer/decision slot, so a human reviewer can fill the
literal
`- [ ] **CVD distinguishability** -- OPEN` checkbox that `theme_gen.py:569`
leaves open. The aid emits EVIDENCE for a human: it computes NO rolled-up score
and NO safe/unsafe verdict (hard rule #9), ticks NO checkbox and moves NO stage
(Principle V), edits NO theme, adds NO `retail check` rule, and opens NO
connection.

**Technical approach**: three net-new deterministic CVD simulation transforms
added to `src/retail/color.py` BESIDE the shipped `delta_e76` (standard published
closed-form colour-space projections -- a fixed matrix per deficiency type, no
model, no randomness), plus a small read-only runtime module
(`src/retail/cvd_evidence.py`) and a CLI verb that reads a committed theme,
simulates the palette, measures under-simulation pairwise `delta_e76`, and writes
the durable blank-slot evidence file. The module mirrors the shipped read-only
surfaces' driver-free import path and the DL4 design-review-evidence
durable-artifact posture. The evidence is decoupled from any verdict: it presents
measured per-pair distances (optionally ordered by the measured distance as a
reading aid) and NEVER a rolled-up number, so a committed unit-test VERIFIER
sitting ON the evidence output can mechanically assert FR-004/FR-005/FR-007/FR-012
and SC-002/SC-003/SC-004/SC-007 -- the property that keeps this an evidence aid,
not an opinion.

## Technical Context

**Language/Version**: Python 3.11+ (matches `src/retail/`; stdlib-only core)

**Primary Dependencies**: stdlib only. Colour parsing and perceptual distance reuse
the in-repo `src/retail/color.py` (`delta_e76` and its hex/RGB helpers); theme JSON
is read with stdlib `json`. No new dependency is added.

**Storage**: reads ONE committed theme JSON at a caller-supplied path (the
`themes/*.theme.json` shape the shipped `theme-compile` / `pbir-apply-theme` verbs
read). Writes exactly ONE durable companion evidence file, THEME-ADJACENT by default
(`themes/<theme-name>.cvd-simulation-evidence.md`, plus an optional `--format json`
shape), or at a reviewer-supplied `--out` path. NOTE (Clarification Q4): the theme
input is repo-global and NOT 1:1 with a table -- a theme (e.g.
`themes/tower-retail.theme.json`) can back MANY tables (referenced by each table's
design artifacts as `palette_source`), so there is NO deterministic theme -> table
resolution; the default output is theme-adjacent, and placing it into a specific
`mappings/<table>/design/` review record is an explicit `--out` choice the reviewer
makes, never inferred. No DB, no network, no other write.

**Testing**: pytest, `@pytest.mark.unit`. Fixtures under `tests/` covering: a
palette with a red/green pair whose under-deuteranope `delta_e76` is materially
smaller than its normal-vision distance (the headline reproducibility case); all
three simulation types present; a no-palette / single-colour theme (`new`-style
honest absence); a malformed/unreadable theme; a ramp-stops-present theme; a
determinism case (two runs -> byte-identical file); and an unreadable-colour-token
case (named + skipped, never guessed). The evidence-faithfulness verifier is a test
helper reused across fixtures.

**Target Platform**: CLI on Windows/Linux (same as the rest of `retail`); ASCII
output, UTF-8 no BOM.

**Project Type**: single-project CLI/library (extends the existing `src/retail`).

**Performance Goals**: N/A -- one theme's small palette per invocation; O(n^2) pairs
over a handful of colours; not perf-sensitive.

**Constraints**: driver-free import path (no DB/network import at module load,
Principle VIII); the ONLY write is the single evidence file (structurally
grep-verifiable: no other write call, no theme edit, no `readiness-status.yaml`
touch); deterministic transforms + deterministic evidence (no randomness, no
wall-clock timestamp in the measured body, FR-002/FR-012); ASCII-only output
(Principle IX); short repo-relative paths (Windows MAX_PATH, Principle IX); NO
rolled-up score / verdict / ranking anywhere (hard rule #9, FR-004).

**Scale/Scope**: one theme per invocation; one evidence file. Generic across all
committed themes (Principle VII).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Bearing on this feature | Verdict |
|-----------|-------------------------|---------|
| I. Agent-First, Gate-Enforced | Adds NO gate; is not a `retail check` rule; claims no rule-pass authority. An optional read-only design-review evidence companion the agent may invoke. | PASS (adds no gate, lowers no floor) |
| II. Depend, Never Fork | Touches no execution adapter; pure in-repo colour arithmetic over a committed theme. | PASS (n/a) |
| III. Medallion, Postgres-First, Gold-Only | Reads a committed theme JSON, not any warehouse layer; opens no DB. | PASS (n/a) |
| IV. Source Mapping Before Silver | Reads a Stage-6 design artifact (a theme) downstream of the mapping gate; adds no mapping gate, writes no `silver.*`. | PASS |
| V. Agent Stops at Judgment Calls | LOAD-BEARING. The aid emits MEASURED evidence (simulated swatches + per-pair deltaE) for a NAMED human; the `- [ ] **CVD distinguishability** -- OPEN` checkbox stays a blank human field. It ticks nothing, sets `colorblind_considerate_categoricals` never, moves no stage. This feature REINFORCES Principle V. | PASS (reinforces; the verifier mechanically prevents a self-granted verdict/score) |
| VI. Defaults Then Deviations | Makes no default/deviation ruling; reads the committed theme only. | PASS (n/a) |
| VII. C086 Is An Example | Generic over ANY committed theme's declared tokens; no hardcoded brand colours, palette values, or table names (FR-011, SC-006). `retail_store_sales` themes are cited fixtures only. | PASS |
| VIII. Static-First, Live Deferred | Static, committed-theme-only; driver-free import path; no live surface, no DB. | PASS |
| IX. Secrets and Reproducibility | Reads committed text, writes one deterministic evidence file; ASCII, UTF-8 no BOM; no secrets; byte-identical re-run (FR-012). | PASS |

**Hard rule #9 (no fabricated confidence/score)**: PASS -- a per-pair `delta_e76`
under a named simulation is a MEASUREMENT (the shipped CT2/CT3 rules already surface
pairwise deltaE); FR-004 forbids any rolled-up "CVD score", pass/fail verdict,
theme ranking, quality-index count, or is/is-not-colorblind-safe statement. The
closest-collapsing "ordering" is a presentation of the measured deltaE values, not
a new computed rank. A verifier test asserts no rolled-up-score / verdict / ranking
token appears in the evidence.

**Four hard-stops**: never_self_grant_approval (ticks no checkbox, sets no theme
value, moves no stage), no_dashboard_before_metric_contracts (gate-agnostic --
neither enforces nor clears it; the evidence is not a gate pass),
never_fabricate_a_confidence_score (measured per-pair deltaE only, no rollup),
no_silver_before_mapping (n/a -- reads a Stage-6 theme, writes no silver). All
respected.

**Gate result**: PASS, no violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

Authored in this spec-only slice (the three artifacts committed and ratified):

```text
specs/118-cvd-simulation-evidence/
  spec.md              # the feature specification (specify)
  plan.md              # This file (plan)
  tasks.md             # dependency-ordered task list (tasks)
  checklists/
    requirements.md    # spec quality checklist (all items pass)
```

The finer companion docs (`research.md`, `data-model.md`, `quickstart.md`,
`contracts/*`) are NOT authored in this spec-only slice and are OPTIONAL
implement-time outputs; the behaviour they would carry is fixed inline here (this
plan's Summary + Technical Context fixes the data model -- the palette-colour ->
simulated-colour -> per-pair deltaE shape -- and the evidence/verifier contract).
An implementer MAY generate them at implement-time; nothing in the spec/plan/tasks
depends on their presence. The one implement-time research item worth naming is the
choice of published CVD transform matrices (see Phase 0 note below); it is bounded
and does not block this spec-only slice.

### Source Code (repository root)

```text
src/retail/
  color.py                      # EDIT: add three deterministic CVD simulation
                                #       transforms (protanope/deuteranope/tritanope)
                                #       BESIDE the shipped delta_e76 -- pure closed-form
                                #       colour maths, no I/O, no new dependency.
  cvd_evidence.py               # NEW: the read-only evidence composer (read theme ->
                                #      simulate palette + ramp stops -> measure per-pair
                                #      delta_e76 under each simulation -> render evidence
                                #      markdown/json). Driver-free, single-write.
  cli/
    commands/
      cvd_evidence.py           # NEW: CLI verb wiring (mirrors cli/commands/pii_notice.py
                                #      / approver_view.py -- a durable-evidence writer verb)
  cli/parser.py                 # EDIT: register the new subcommand
  cli/__init__.py               # EDIT: dispatch the new subcommand (if dispatch lives here)

templates/
  cvd-simulation-evidence.md    # NEW: the durable evidence template with the BLANK
                                #      named-reviewer/decision slot (mirrors
                                #      templates/design-review-evidence.md, the DL4 precedent)

docs/tools/
  cvd-evidence.md               # NEW: the tool doc (mirrors docs/tools/*.md)

tests/unit/
  test_cvd_evidence.py          # NEW: fixtures + the evidence-faithfulness VERIFIER +
                                #      simulation/measurement/determinism/absence tests
  test_color.py                 # EDIT (or NEW if absent): unit tests for the three CVD
                                #      transforms (fixed inputs -> published expected outputs)
```

**Structure Decision**: Extend the existing single-project `src/retail` runtime.
The three CVD transforms live in `color.py` beside `delta_e76` (the panel's stated
first step; colocated with the perceptual-distance maths they feed). The evidence
composer is a runtime module (`cvd_evidence.py`) with a CLI verb under
`cli/commands/`, mirroring the shipped read-only surfaces' driver-free import path.

This feature DIFFERS from spec 116 in one deliberate way: it WRITES a durable
companion evidence file (Clarification Q4), so -- unlike the print-only 116 -- it
DOES add a `templates/cvd-simulation-evidence.md` companion, mirroring the shipped
DL4 design-review-evidence artifact (`templates/design-review-evidence.md` +
`src/retail/rules/design_review_evidence.py`), which is the durable-disclosure
precedent. The zero-write guarantee is therefore SCOPED: structurally, the ONLY
write call is the single evidence file; the theme JSON, `readiness-status.yaml`, and
the OPEN checkbox are never written (verifier-asserted, SC-003). The evidence path
is THEME-ADJACENT by default (`themes/<theme-name>.cvd-simulation-evidence.md`) --
NOT a per-table default -- because the theme input is repo-global and not 1:1 with a
table (Clarification Q4); a `--out` override places it into a table's design review
record only when the reviewer asks, never by inference. This keeps the aid generic
over any committed theme (Principle VII) and removes the underivable theme -> table
resolution.

A runtime-module shape (over a skill-only shape) is required because
FR-002/FR-003/FR-004/FR-007/FR-012 need MECHANICAL guarantees -- deterministic
colour transforms, a reused `delta_e76` measurement, a rollup-free evidence body,
and byte-identical re-runs -- which a prose-only skill cannot provide. The transforms
reuse the shipped `delta_e76`; only the three simulation projections are net-new
colour maths (standard published matrices, not a model).

## Complexity Tracking

> Not required -- Constitution Check passed with no violations.

## Phase 0 note (implement-time, not blocking this slice)

The one bounded research item at implement time: select the published CVD
simulation transform matrices (e.g. a documented Brettel/Vienot-style linear
projection per deficiency type). Constraint: deterministic and reproducible
(FR-002/FR-012), citeable to a published source (so the evidence is auditable,
FR-007), and dependency-free (implementable as fixed constants in `color.py`). This
is a self-contained choice with an obvious default (a widely-cited published matrix
set); it does not affect the spec's fixed behaviour and needs no human ruling.
