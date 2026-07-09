# Implementation Plan: Non-Duplicate Dashboard Planner

**Branch**: `116-dashboard-duplicate-planner` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/116-dashboard-duplicate-planner/spec.md`

## Summary

Classify ONE caller-supplied PROPOSED dashboard idea for ONE table into exactly
one categorical verdict -- `new` / `extends <page>` / `duplicate of <page>` -- by
reducing both the proposal and each committed page to its set of
`(business_question, bound_contract, dimension)` tuples and computing a
DETERMINISTIC SET RELATIONSHIP (coverage / partial-overlap / disjoint) over them.
The comparison corpus is the target table's committed design directory
`mappings/<table>/design/` (`dashboard-layout.md` + `visual-list.md` +
`visual-contract-binding-map.md`). Output is PRINTED (text or `--format json`);
nothing is written; no gate is added; no metric is invented. `new by absence` when
the corpus is missing.

**Technical approach**: a small deterministic Python classifier
(`src/retail/dashboard_planner.py`) plus a CLI verb, mirroring the shipped
read-only runtime surfaces (`approval_inbox.py`, `blocker_explainer.py`,
`run_next.py`) exactly -- same driver-free import path, same print-only /
zero-write posture. The verdict is decided by set membership over committed tuples
(hard rule #9: NO overlap number, threshold, or ranking). The classifier is paired
with a committed, non-gating unit-test VERIFIER that sits ON the classification
OUTPUT (independent of the classifier) and mechanically asserts: (a) the verdict is
one of the three categorical values; (b) every cited match is a REAL corpus row
(the named page + row id + contract + dimension exist in the parsed corpus); (c)
the named page for a `duplicate`/`extends` verdict exists; (d) no numeric-score /
overlap / ranking token appears in the output; (e) the proposal tuples are echoed
as supplied (no invented tuple/metric). Classification and verification are
DECOUPLED -- the classifier decides; the verifier (tests) proves the guarantees --
so FR-003/FR-005/FR-006/FR-010/FR-012 and SC-002/SC-003/SC-004 are mechanically
real, the property that distinguishes this planner from a free-composed opinion.

## Technical Context

**Language/Version**: Python 3.11+ (matches `src/retail/`; stdlib-only core)

**Primary Dependencies**: stdlib only for the classifier. Markdown-table / YAML
parsing reuses the in-repo readers already used by the shipped surfaces
(`blocker_explainer.py`'s `_load_yaml_mapping` idiom + the markdown-table reading
the design artifacts use); no new dependency is added -- the design artifacts are
committed markdown/tables, parsed with stdlib.

**Storage**: reads the target table's committed design corpus under
`mappings/<table>/design/` (`dashboard-layout.md`, `visual-list.md`,
`visual-contract-binding-map.md`). Writes NOTHING (print-only; optional
`--format json` to stdout). No DB, no network.

**Testing**: pytest, `@pytest.mark.unit`. Fixtures under `tests/` covering:
a `duplicate` proposal (all tuples covered by a committed page), an `extends`
proposal (shares >=1 tuple, adds >=1), a `new` proposal (disjoint), a multi-page
precedence case, a missing/empty-corpus `new by absence` case, and a
proposal-referencing-an-unknown-measure case (adds-new, no invented contract). The
output-faithfulness verifier is a test helper reused across fixtures.

**Target Platform**: CLI on Windows/Linux (same as the rest of `retail`); ASCII
output, UTF-8 no BOM.

**Project Type**: single-project CLI/library (extends the existing `src/retail`).

**Performance Goals**: N/A -- one proposal vs one table's small committed corpus;
not perf-sensitive.

**Constraints**: driver-free import path (no psycopg2 / no DB import at module
load, matching the static core, Principle VIII); print-only, zero write calls
(structurally grep-verifiable, matching the shipped read-only surfaces); ASCII-only
output (Principle IX); short repo-relative paths (Windows MAX_PATH, Principle IX);
the verdict decision MUST reduce to set membership -- no computed overlap/score/rank
anywhere (hard rule #9).

**Scale/Scope**: one proposal + one table per invocation; one printed verdict.
Generic across all mapped tables (Principle VII).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Bearing on this feature | Verdict |
|-----------|-------------------------|---------|
| I. Agent-First, Gate-Enforced | Adds NO gate; is not a `retail check` rule; does not claim rule-pass authority. A read-only triage companion the agent may invoke around design. | PASS (adds no gate, lowers no floor) |
| II. Depend, Never Fork | Touches no execution adapter; pure in-repo classifier over committed text. | PASS (n/a) |
| III. Medallion, Postgres-First, Gold-Only | Reads committed design artifacts, not any warehouse layer; opens no DB. | PASS (n/a) |
| IV. Source Mapping Before Silver | Reads a Stage-6 design artifact downstream of the mapping gate; adds no mapping gate, writes no `silver.*`. | PASS |
| V. Agent Stops at Judgment Calls | LOAD-BEARING. The verdict is a SET RELATIONSHIP over committed facts, cited to committed rows; it originates NO judgment, ranks nothing, and recommends no build/drop. A `new` verdict is NOT clearance; the human decides build/extend/drop. This feature REINFORCES Principle V. | PASS (reinforces; the verifier mechanically prevents a synthesized rank/score) |
| VI. Defaults Then Deviations | Makes no default/deviation ruling; reads the committed design corpus only. | PASS (n/a) |
| VII. C086 Is An Example | Generic classifier parameterized by `<table>`; no hardcoded table/page/question/contract/dimension names (FR-013, SC-006). `retail_store_sales` is a cited fixture only. | PASS |
| VIII. Static-First, Live Deferred | Static, committed-text-only; driver-free import path; no live surface. | PASS |
| IX. Secrets and Reproducibility | Reads committed text, writes nothing; ASCII, UTF-8 no BOM; no secrets touched; deterministic verdict (FR-014). | PASS |

**Hard rule #9 (no fabricated confidence/score)**: PASS -- the verdict is decided
by set membership over committed tuples (Clarification Q2 / FR-003), not by an
overlap percentage, threshold, or ranking; FR-010 forbids any score/count/overlap/
ranking; a verifier test asserts no numeric-score / overlap / ranking token appears
in output. The three verdict values are categorical (mirroring idea-engine's
ADOPT/PARK/REJECT and the four readiness statuses).

**Four hard-stops**: never_self_grant_approval (grants nothing, moves no stage),
no_dashboard_before_metric_contracts (gate-agnostic -- neither enforces nor clears
it; a `new` verdict is not a gate pass), never_fabricate_a_confidence_score (set
membership, not a score), no_silver_before_mapping (n/a -- reads a Stage-6 artifact,
writes no silver). All respected.

**Gate result**: PASS, no violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

Authored in this spec-only slice (the three artifacts committed and ratified):

```text
specs/116-dashboard-duplicate-planner/
  spec.md              # the feature specification (specify)
  plan.md              # This file (plan)
  tasks.md             # dependency-ordered task list (tasks)
```

The finer companion docs (`research.md`, `data-model.md`, `quickstart.md`,
`contracts/classifier.md`, `contracts/verifier.md`) are NOT authored in this
spec-only slice and are OPTIONAL implement-time outputs; the behavior they would
carry is fixed inline here (this plan's Summary + Technical Context fixes the data
model -- the `(business_question, bound_contract, dimension)` tuple + the
set-relationship decision -- and the verifier contract). An implementer MAY
generate them at implement-time; nothing in the spec/plan/tasks depends on their
presence. tasks.md references the behavior inline, not these files.

### Source Code (repository root)

```text
src/retail/
  dashboard_planner.py          # NEW: the classifier (read design corpus -> page tuple-sets,
                                #      reduce proposal -> tuples, decide set-relationship verdict,
                                #      render text/json). Read-only, print-only, driver-free.
  cli/
    commands/
      dashboard_planner.py      # NEW: CLI verb wiring (mirrors cli/commands/blockers.py / next.py)
  cli/parser.py                 # EDIT: register the new subcommand
  cli/__init__.py               # EDIT: dispatch the new subcommand (if the dispatch table lives here)

docs/tools/
  dashboard-planner.md          # NEW: the tool doc (mirrors docs/tools/blocker-explainer.md)

tests/unit/
  test_dashboard_planner.py     # NEW: fixtures + the output-faithfulness VERIFIER + verdict tests
```

**Structure Decision**: Extend the existing single-project `src/retail` runtime,
placing the classifier at `src/retail/dashboard_planner.py` and its CLI verb under
`src/retail/cli/commands/`, exactly mirroring the shipped read-only surfaces
`approval_inbox.py` / `blocker_explainer.py` / `run_next.py` (PR #229) and their
command wiring. This runtime-module shape (over a skill-only shape) is chosen
because FR-003/FR-005/FR-006/FR-010/FR-012 require MECHANICAL guarantees -- a
deterministic set-relationship verdict and an output-faithfulness verifier that a
prose-only skill cannot provide. NO template output file is added (unlike spec 114)
because the planner writes nothing (Clarification Q3): its output is a transient
printed triage answer, not a durable disclosure artifact -- so it needs no
`templates/` companion. The classifier retargets `idea-engine.js`'s categorical
verdict shape to the dashboard-design corpus; it does not import or re-run the
idea-engine workflow (that is a JS agent workflow; this is a stdlib Python runtime
surface).

## Complexity Tracking

> Not required -- Constitution Check passed with no violations.
