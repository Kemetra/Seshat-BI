# Implementation Plan: Live-validation evidence recorder (validate.py Findings -> readiness-status block)

**Branch**: `057-live-validation-evidence-recorder` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/057-live-validation-evidence-recorder/spec.md`

## Summary

Add a pure, stdlib-only recorder that turns a live validate run's Findings (plus
the target table identity and run mode) into a `gold_ready` readiness-status
block -- `status` + `evidence[]` + `blocking_reasons[]` + recorded `warnings[]`,
never a numeric score. The first-step scope is the transform seam: a deterministic
function that maps `(list[Finding], table_identity, run_mode) -> gold_ready block`
as an in-memory structure, plus the wiring point where `_run_validate` could
obtain it. Whether the block is WRITTEN to `mappings/<table>/readiness-status.yaml`
or only EMITTED for a human to apply, and whether the recorder may set
`status: pass`, are Principle V decisions left open (FR-012 / FR-013 / FR-014);
the seam is built so either ruling can be honored without rework, and the safe
default demonstrated by this slice is EMIT-ONLY, status never set to `pass` by
the recorder.

## Technical Context

**Language/Version**: Python 3.13 (CI) / 3.12 (local dev); stdlib only in the
shared import path.

**Primary Dependencies**: None new. Consumes the existing frozen `Finding`
dataclass (`src/retail/core.py`, `to_dict()` from idea-bank B2) and the existing
`run_live_checks` result shape (`src/retail/validate.py`). Reuses the existing
DSN redaction contract (`_redact_dsn` in `src/retail/cli.py`). No YAML *writer*
dependency enters the shared import path (B3 boundary guard).

**Storage**: N/A for the seam. The eventual write target (if a writer is ever
built under the FR-013 ruling) is a table-specific `mappings/<table>/readiness-status.yaml`
(ADR 0004) -- never the generic template.

**Testing**: pytest (`-m unit`). All recorder tests are pure (synthetic Finding
lists), no DB, no driver, no network.

**Target Platform**: CLI library module invoked by `retail validate`.

**Project Type**: Single project (library/CLI) -- matches the existing
`src/retail/` layout.

**Performance Goals**: N/A (a pure in-memory transform over a small findings list).

**Constraints**: stdlib-only in the shared import path; deterministic output;
DSN/credential redaction preserved; no numeric confidence; generic (no C086
identifiers); must not add a module-scope heavy import to `validate.py` or the
live-surface modules; immutable (never mutate Finding inputs).

**Scale/Scope**: One new small module + its unit tests + a thin, optional wiring
seam in the CLI. No new subsystem.

## Constitution Check

*GATE: must pass before and after design.*

| Principle / rule | How this plan complies |
|------------------|------------------------|
| V (agent stops at judgment calls; no self-grant) | The recorder does NOT set `status: pass` in this slice; pass-set authority (FR-012), write-vs-emit (FR-013), and grain-claim (FR-014) are left as [NEEDS CLARIFICATION] for a human. Default demonstrated: emit-only, status never `pass`. |
| VIII (static-first; live gate is read-only; never fake a pass) | The recorder only records what a run produced; deferred mode is recorded as `blocked`, never inferred to pass. It does not weaken the gate or execute anything. |
| IX (secrets + reproducibility; no fake confidence) | No numeric score field ever; DSN redaction contract preserved end-to-end; output deterministic for fixed inputs. |
| VII (C086 is an example, not the schema) | Recorder is generic; table identifiers arrive only from run inputs and land only in a table-specific filled copy, never the generic template (FR-009 / FR-010). |
| B1/B3 (driver-free / import-boundary guard) | No YAML writer, DB driver, or heavy import at module scope in the shared path; the recorder is stdlib-only and lazily wired. The existing boundary-guard test must stay green (SC-004). |
| Immutability (coding-style) | Recorder builds a new block; never mutates the frozen Finding inputs (FR-007). |
| YAGNI / hard rule #8 (seam, not implementation) | Ships the transform seam + tests only; the file writer is deferred behind the FR-013 ruling. |

Result: PASS (no violation; three items deliberately deferred to human ruling,
recorded as open questions rather than resolved by the agent).

## Project Structure

### Documentation (this feature)

```text
specs/057-live-validation-evidence-recorder/
|-- spec.md              # feature spec (stage 2/3 output)
|-- plan.md              # this file
|-- tasks.md             # stage 4 output
|-- analysis.md          # stage 5 output (repo convention)
|-- plan-review.md       # stage 6 output (repo convention)
`-- checklists/
    `-- requirements.md   # spec quality checklist
```

No research.md / data-model.md / quickstart.md / contracts/ are needed: there is
no external research, no new persisted data model (the block shape is already
defined by the readiness template), and no network contract. The data shapes are
documented inline in the Data Shapes section below.

### Source Code (repository root)

```text
src/retail/
|-- readiness_evidence.py   # NEW: the pure recorder (stdlib-only)
|                           #   build_gold_ready_block(findings, table, mode) -> dict
|-- core.py                 # UNCHANGED: frozen Finding + to_dict (consumed)
|-- validate.py             # UNCHANGED shape; run_live_checks is the source
`-- cli.py                  # OPTIONAL thin wiring seam in _run_validate
                            #   (behind FR-013 ruling; emit-only default)

tests/unit/
`-- test_readiness_evidence.py   # NEW: pure unit tests (synthetic findings)
```

## Data Shapes (no separate data-model.md)

Input (consumed, not defined here):
- `Finding` (frozen): `rule_id`, `severity` (ERROR | WARNING | ...), `message`,
  `locator`; `to_dict()` yields `{rule_id, severity, message, locator}`.
- `table_identity`: the table/source the run targeted (a string id).
- `run_mode`: `live` (a run occurred) | `deferred` (no DSN / no driver).

Output (the produced block; a plain dict mirroring `templates/readiness-status.yaml`
`stages.gold_ready`):

```text
gold_ready:
  status: "not_started" | "blocked" | "warning" | "pass"   # recorder never emits "pass" in this slice
  evidence: [ ... ]            # e.g. "live validate: 0 ERROR findings for <table>"
  blocking_reasons: [ ... ]    # one per ERROR finding: rule_id + message + locator
  warnings: [ ... ]            # one per WARNING finding (recorded, non-fatal)
```

Status derivation (no score, explicit only):
- `run_mode == deferred` -> `blocked` + a deferred-boundary blocking reason.
- any ERROR finding -> `blocked` + one blocking reason per ERROR.
- no ERROR, one+ WARNING -> `warning` + recorded warnings + evidence of the run.
- no ERROR, no WARNING (clean live run) -> status left NOT set to `pass` by the
  recorder (per FR-012); evidence[] records the clean run; a human/approval
  applies the terminal `pass` under the FR-012 ruling.

## Complexity Tracking

No constitution violation requires justification. The only complexity is the
deliberate deferral of the writer/pass-set behavior behind human rulings, which
reduces (not adds) scope.
