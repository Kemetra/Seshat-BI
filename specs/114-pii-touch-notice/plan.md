# Implementation Plan: Personal-Data-Touch Notice

**Branch**: `114-pii-touch-notice` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/114-pii-touch-notice/spec.md`

## Summary

Compose ONE read-only, per-column PII-disclosure notice for ONE table from its
committed `mappings/<table>/source-map.yaml`: one disclosure sentence per
`pii: true` column echoing the committed `pii:` flag + `decision` + recorded
disposition string VERBATIM, and an explicit GAP line for any `pii: true` column
whose disposition is not recorded. Output is one file
`mappings/<table>/pii-touch-notice.md`. No score, no gate, no upstream write.

**Technical approach**: a small deterministic Python composer
(`src/retail/pii_notice.py`) plus a CLI verb, mirroring the existing read-only
runtime surfaces (`approval_inbox.py`, `blocker_explainer.py`). The composer is
paired with a committed, non-gating unit-test VERIFIER that mechanically asserts
FR-011 (every disposition sentence is a verbatim substring of a committed
source-map field) and the never-omit/never-clear invariants (FR-004, SC-003).
Composition and verification are DECOUPLED: the composer writes; the verifier
(tests) proves the guarantees. This makes FR-011/SC-002/SC-003/SC-005/SC-006
mechanically real -- the property that distinguishes this notice from F040's
prose-enforced verbatim-cite posture.

## Technical Context

**Language/Version**: Python 3.11+ (matches `src/retail/`; stdlib-only core)

**Primary Dependencies**: stdlib only for the composer. YAML parsing reuses the
existing in-repo reader used by `source_profile_reader` / the mapping surfaces
(no new dependency; `source-map.yaml` is already parsed elsewhere in `src/retail`).

**Storage**: reads one committed file `mappings/<table>/source-map.yaml`; writes
one committed file `mappings/<table>/pii-touch-notice.md`. No DB, no network.

**Testing**: pytest, `@pytest.mark.unit`. Fixtures under `tests/` covering:
kept+decided PII column, dropped+decided PII column, kept+UNDECIDED PII column
(the safety case), all-`pii:false` table, missing `source-map.yaml`, and an
intra-file inconsistency. The verbatim-substring verifier is a test helper reused
across fixtures.

**Target Platform**: CLI on Windows/Linux (same as the rest of `retail`); ASCII
output, UTF-8 no BOM.

**Project Type**: single-project CLI/library (extends the existing `src/retail`).

**Performance Goals**: N/A -- a single-file static compose; not perf-sensitive.

**Constraints**: driver-free import path (no psycopg2 / no DB import at module
load, matching the static core, Principle VIII); ASCII-only output (Principle IX);
short repo-relative paths (Windows MAX_PATH, Principle IX).

**Scale/Scope**: one table per invocation; one output file. Generic across all
mapped tables (Principle VII).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Bearing on this feature | Verdict |
|-----------|-------------------------|---------|
| I. Agent-First, Gate-Enforced | Adds NO gate; is not a `retail check` rule; does not claim rule-pass authority. A read-only companion the agent may invoke. | PASS (adds no gate, lowers no floor) |
| II. Depend, Never Fork | Touches no execution adapter; pure in-repo composer. | PASS (n/a) |
| III. Medallion, Postgres-First, Gold-Only | Reads a committed mapping artifact, not any warehouse layer; opens no DB. | PASS (n/a) |
| IV. Source Mapping Before Silver | Consumes the CLEARED mapping artifact downstream; adds no mapping gate, writes no `silver.*`. | PASS |
| V. Agent Stops at Judgment Calls | LOAD-BEARING. The notice ECHOES a named human's recorded PII disposition; it originates NONE. An undecided PII column is a GAP (a stop-and-ask surfaced), never self-cleared. This feature REINFORCES Principle V. | PASS (reinforces; the verifier mechanically prevents an authored clearance) |
| VI. Defaults Then Deviations | Reads the RC4 deviation disposition verbatim; makes no default/deviation ruling. | PASS |
| VII. C086 Is An Example | Generic composer parameterized by `<table>`; no hardcoded column names or PII categories (FR-012, SC-006). `retail_store_sales` is a cited fixture only. | PASS |
| VIII. Static-First, Live Deferred | Static, committed-text-only; driver-free import path; no live surface. | PASS |
| IX. Secrets and Reproducibility | Reads/writes committed text only; ASCII, UTF-8 no BOM; no secrets touched; idempotent overwrite of one output file. | PASS |

**Hard rule #9 (no fabricated confidence/score)**: PASS -- FR-006 forbids any
score/count; the composer emits categorical echoes only, verified by a test that
asserts no numeric-score token appears in output.

**Gate result**: PASS, no violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/114-pii-touch-notice/
  plan.md              # This file
  research.md          # Phase 0 output
  data-model.md        # Phase 1 output
  quickstart.md        # Phase 1 output
  contracts/           # Phase 1 output (composer + CLI contract, verifier contract)
    composer.md
    verifier.md
  checklists/
    requirements.md    # from /speckit-specify
  tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/retail/
  pii_notice.py                 # NEW: the composer (read source-map, build notice model, render markdown)
  cli/
    commands/
      pii_notice.py             # NEW: CLI verb wiring (mirrors cli/commands/blockers.py)
  cli/parser.py                 # EDIT: register the new subcommand
  cli/__init__.py               # EDIT: dispatch the new subcommand (if the dispatch table lives here)

templates/handoff/
  pii-touch-notice.md           # NEW: the generic copy-me output template (companion to answerability-summary.md)

docs/tools/
  pii-touch-notice.md           # NEW: the tool doc (mirrors docs/tools/blocker-explainer.md)

tests/unit/
  test_pii_notice.py            # NEW: fixtures + the verbatim-substring VERIFIER + invariant tests
```

**Structure Decision**: Extend the existing single-project `src/retail` runtime,
placing the composer at `src/retail/pii_notice.py` and its CLI verb under
`src/retail/cli/commands/`, exactly mirroring the shipped read-only surfaces
`approval_inbox.py` / `blocker_explainer.py` (PR #229) and their command wiring.
This is chosen over the skill-only F040 pattern precisely because FR-011 requires
a MECHANICAL guarantee that a prose-only skill cannot provide; a Python composer
+ unit-test verifier makes FR-011/SC-002/SC-003/SC-005/SC-006 checkable. The
`templates/handoff/pii-touch-notice.md` companion is added for the generic output
shape (Principle VII), following the `answerability-summary.md` precedent.

## Complexity Tracking

> Not required -- Constitution Check passed with no violations.
