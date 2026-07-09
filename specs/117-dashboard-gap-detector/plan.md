# Implementation Plan: Dashboard Gap Detector

**Branch**: `117-dashboard-gap-detector` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/117-dashboard-gap-detector/spec.md`

## Summary

A read-only, pre-design gap inventory for ONE subject area. Given a
HUMAN-SUPPLIED page-intent (business questions, each naming its required
metric(s) and slicing dimension(s) -- the same Principle-V input
`dashboard-design` requires), classify each required item against the target
table's committed evidence -- metric contracts (`mappings/<table>/metrics/
*.yaml` `readiness.status`), the gold-star dimension inventory
(`mappings/<table>/source-map.yaml` `gold_star`), and open owner decisions
(`mappings/<table>/unresolved-questions.md` structured rows) -- and emit, per
item, one CATEGORICAL status from SL1's closed five-value enum plus a named
blocker where the item blocks design. Writes nothing, records no `pass`, moves
no stage, adds no gate; prints a read-only view.

**Technical approach**: a STANDALONE `src/retail/gap_detector.py` + CLI verb,
grouped with the shipped read-only surfaces (`blocker_explainer`,
`approval_inbox`, `run_next`). SL1's status VOCABULARY is REUSED (not
re-invented) by EXTRACTING the module-private `_ENUM` frozenset from
`src/retail/rules/scorecard.py` into a shared importable constant
`src/retail/coverage_status.py` that BOTH scorecard.py and gap_detector.py
import -- a behavior-preserving move-refactor so SL1's rule output is
byte-identical and its test stays green (the same reuse-by-extraction pattern
spec 115 used for `readiness_classify`). Paired with a non-gating unit-test
VERIFIER that sits ON the real risk: an uncovered/undecided required item must
NEVER be classified `Covered`, and every emitted status must be a member of
SL1's enum. The verifier's oracle is INDEPENDENT of the classifier under test
(the expected status per fixture item is hand-declared in the test, not read
back from `gap_detector`'s own output).

## Technical Context

**Language/Version**: Python 3.11+ (matches `src/retail/`; stdlib-only core).

**Primary Dependencies**: stdlib + the in-repo YAML reader idiom already used by
the shipped readiness surfaces (`_load_yaml_mapping`); no new third-party
dependency. Reuses the extracted `coverage_status._ENUM`.

**Storage**: reads committed files per table
(`mappings/<table>/metrics/*.yaml`, `mappings/<table>/source-map.yaml`,
`mappings/<table>/unresolved-questions.md`) plus the supplied page-intent;
writes NOTHING. No DB, no network, no PBIP.

**Testing**: pytest `@pytest.mark.unit`. Fixtures: a page-intent + table where
some required metrics are `pass` (Covered), one metric contract is present but
`not_started` (Blocked -- needs business definition), one required metric has no
contract file (Planned), one required dimension is absent from `gold_star`
(Blocked -- missing field), and one required subject is out-of-domain (Out of
scope); a page-intent whose required metric depends on an OPEN
`unresolved-questions.md` row (owner governance/analyst) plus an all-`answered`
table; input-absence cases (no page-intent; missing `source-map.yaml`); and a
second distinct conformant table for the generic proof. Plus a regression-lock
test that SL1's `check_coverage_scorecard` output is unchanged after the `_ENUM`
extraction.

**Target Platform**: CLI, ASCII output, UTF-8 no BOM.

**Project Type**: single-project CLI/library (extends `src/retail`).

**Performance Goals**: N/A -- static compose over a handful of small committed
files.

**Constraints**: driver-free import path (Principle VIII); NO file-write path in
the read view (FR-010, structurally grep-verifiable); NO `@register` rule / no
manifest change (FR-008); categorical-only, no numeric token (FR-011); ASCII
only (Principle IX); short paths (Windows MAX_PATH).

**Scale/Scope**: one table + one page-intent per invocation. Generic across
tables (Principle VII).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Bearing | Verdict |
|-----------|---------|---------|
| I. Agent-First, Gate-Enforced | Adds NO gate; not a `retail check` rule; claims no rule-pass authority. It REPORTS the design-blocking gaps the existing gate/verb already enforce. | PASS |
| II. Depend, Never Fork | No execution adapter touched; no metric/dimension/design defined. | PASS (n/a) |
| III. Medallion, Postgres-First, Gold-Only | Reads committed mapping artifacts, not a warehouse layer; opens no DB. | PASS (n/a) |
| IV. Source Mapping Before Silver | Consumes committed mapping/readiness artifacts; writes no silver; adds no mapping gate. | PASS |
| V. Agent Stops at Judgment Calls | LOAD-BEARING. The required set is a HUMAN-SUPPLIED page-intent (never invented); an open owner decision is a Principle-V gap the detector REPORTS, never resolves; it records no `pass`, grants no approval, moves no stage. REINFORCES Principle V. | PASS (reinforces; never self-grants) |
| VI. Defaults Then Deviations | Reuses SL1's committed status enum; makes no default/deviation ruling. | PASS |
| VII. C086 Is An Example | Generic, per-table; no hardcoded names/keys (FR-014, SC-010). | PASS |
| VIII. Static-First, Live Deferred | Static committed-text only; driver-free; no live surface; no DAX/PBIR. | PASS |
| IX. Secrets and Reproducibility | Reads committed text; ASCII, UTF-8 no BOM; writes nothing. | PASS |

**Hard rule #9 (no fabricated confidence/score)**: PASS -- FR-002/FR-011 forbid
any numeric score/percentage/count; the answer is a categorical status from
SL1's fixed enum plus a named blocker. Verified by a test asserting no numeric
token appears in output and every status is a member of SL1's enum.

**Four hard-stops (CLAUDE.md)**: never_self_grant_approval -- PASS (records no
pass, writes no approvals[]; FR-009). no_dashboard_before_metric_contracts --
PASS (this surface REPORTS the gap that the existing `dashboard-design` gate
enforces; it adds no gate of its own; FR-008). never_fabricate_a_confidence_
score -- PASS (categorical only; FR-011). no_silver_before_mapping -- PASS (n/a;
writes no SQL, opens no DB; FR-012).

**Gate result**: PASS. No violations; Complexity Tracking not required. The
`_ENUM` extraction is a behavior-preserving refactor (regression-locked), not
new complexity.

## Project Structure

### Documentation (this feature)

```text
specs/117-dashboard-gap-detector/
  plan.md               # This file
  spec.md               # Feature spec (specify + clarify)
  tasks.md              # Phase 2 output (speckit-tasks)
```

> research.md / data-model.md / quickstart.md / contracts/ are OPTIONAL for this
> feature and NOT authored in this slice: the spec's Clarifications already fix
> the data flow (three committed inputs + page-intent), the status mapping, and
> the output vehicle, so a separate research/data-model pass would only restate
> them. Any design detail lives in this plan's Structure Decision and in
> tasks.md. (Mirrors the lean 114/115 chain, which carried plan + tasks as the
> load-bearing design docs.)

### Source Code (repository root)

```text
src/retail/
  coverage_status.py            # NEW: shared SL1 status enum -- _ENUM (the closed five-value
                                #      set) + a small membership/normalize helper, EXTRACTED
                                #      from rules/scorecard.py (behavior-preserving)
  rules/
    scorecard.py                # EDIT: import _ENUM from coverage_status instead of the
                                #       module-private copy (SL1 output byte-identical; regression-locked)
  gap_detector.py               # NEW: the pre-design gap inventory -- read page-intent + 3 committed
                                #      inputs, classify each required item, render the read-only view
  cli/
    commands/
      gap_detector.py           # NEW: CLI verb (mirrors cli/commands/blockers.py); no --write; exit 0
  cli/parser.py                 # EDIT: register the new subcommand
  cli/__init__.py               # EDIT: dispatch the new subcommand

docs/tools/
  dashboard-gap-detector.md     # NEW: tool doc (mirrors docs/tools/blocker-explainer.md):
                                #      what it is, run, the scope wall, the SL1 / dashboard-design /
                                #      consumer-data-dictionary boundaries, what it will NOT do

tests/unit/
  test_gap_detector.py          # NEW: independent-oracle status verifier + per-class fixtures +
                                #      no-write proof + no-score proof + generic proof
  test_scorecard.py             # EDIT/CONFIRM: regression-lock SL1 output unchanged after _ENUM extraction
```

**Structure Decision**: STANDALONE `src/retail/gap_detector.py`, NOT a mode
folded into SL1's `rules/scorecard.py`. Rationale: SL1 is a static `retail
check` RULE (emits `Severity.ERROR` Findings into the gate over a committed
scorecard file); the detector is a read-only agent SURFACE that adds no gate,
reads a human-supplied page-intent and three different committed inputs, and
partitions required items into a status inventory with named blockers. These are
two responsibilities with two authority categories -- folding the surface into
the gate rule would give the rule non-gate behavior and blow the scope wall
(FR-008). Vocabulary reuse is achieved WITHOUT co-location by extracting SL1's
`_ENUM` into `coverage_status.py` (a behavior-preserving move-refactor), which
also makes "the detector's statuses ARE SL1's" MECHANICALLY provable (both
import the one constant) rather than a restated list that can drift. The rejected
fold and the extraction are flagged as a ratify-ledger open item for owner
confirmation.

**Page-intent input shape (plan decision)**: the page-intent is supplied as an
INVOCATION INPUT, not a new committed artifact type this feature defines --
concretely a small structured input (the business questions with their required
metric names + dimension names) passed to `build_gap_inventory(repo_root, table,
page_intent)`. The CLI verb accepts it as a path to a caller-provided page-intent
file (or an inline structured argument); the detector reads it, never authors or
templates it. This keeps the required set a Principle-V human input (FR-001) and
avoids minting a new gated artifact. Whether the kit later standardizes a
committed page-intent template is explicitly OUT of scope here (a follow-up
spec), noted for owner review.

## Complexity Tracking

> Not required -- Constitution Check passed. The `_ENUM` extraction is a
> regression-locked behavior-preserving refactor, explicitly NOT new complexity.
