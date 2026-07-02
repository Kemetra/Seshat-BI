# Implementation Plan: Kit Drift Linter (Compass-Driven Phase-2)

**Branch**: `072-kit-drift-linter` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/072-kit-drift-linter/spec.md`

## Summary

Add a standalone `retail kit-lint` CI step that fails loud on compass PROJECTION drift:
(1) YAML projection drift, (2) prose projection drift. Both wrap the existing
`compass_project.check_yaml_drift` / `check_prose_drift` (built in 070) — no
re-derivation. Standalone step (not a `retail check` core rule); no new gate rule; may
import pyyaml lazily. Wired into CI after `retail semantic-check`. F024 class:
Maintenance Automation (CI-only, derived evidence, no truth, self-grants nothing).

> **Scope cut (adversarial review):** a third "source-vs-constitution correspondence"
> check was CUT — as designed it was a source-vs-source tautology, and only 2 of 4
> hard_stops have a constitutional-document home. Real governance verification needs a
> human governance decision and is deferred as a human-shaped slice; 072 does the
> projection-drift half only. The fenced-body-vs-constitution assurance stays
> human-reviewed-at-ratify (070's honest current state).

## Technical Context

**Language/Version**: Python 3.13+. The linter MAY import `pyyaml` (already in `dev`) to
load the source — like `semantic-check` / `value-check`, and unlike the stdlib-only
`retail check` core, to which this adds no rule (DEC-1).

**Primary Dependencies**: None new. Reuses `compass_project` (070) for the projection
checks and `fence.read_fence_body` for the fenced-body read.

**Storage**: Files only — reads `.seshat/kit-source.yaml`, `.seshat/compass.yaml`, the
`SESHAT-KIT` fenced regions of `AGENTS.md` / `CLAUDE.md`. Reads NO constitution at all
(FR-010). Writes nothing (read-only, FR-004). No DB.

**Testing**: pytest (unit). New tests cover: YAML/prose drift detected + clean;
not-bootstrapped → exit 0; parse-error reported as a named check not a traceback;
no-constitution-read proof; rule-count-unchanged; read-only.

**Target Platform**: CLI + CI step; Windows-safe (reads via universal newlines; the
byte-exact YAML check already handles EOL — see 070's `.gitattributes` LF pin).

**Project Type**: CLI + CI maintenance automation (single project; `src/retail/` +
`.github/workflows/ci.yml`).

**Performance Goals**: N/A (runs once per CI/commit; O(files), trivial).

**Constraints**: standalone step, NOT a `retail check` rule (DEC-1); reads no
constitution (FR-010); read-only (FR-004); no numeric score (FR-009); projection checks
reuse 070's callables (no re-derivation).

**Scale/Scope**: One new module `src/retail/kit_lint.py` + the `kit-lint` subcommand in
`cli.py` + one CI step + tests. No new gate rule; rule count stays 47.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS. `kit-lint` is a gate the agent /
  CI calls; the EXIT CODE is the authority, not prose. It enforces the compass's own
  consistency (the doc's "enforcement arm for the compass itself"); it never self-grants
  a pass.
- **Principle V (Agent Stops at Judgment Calls)**: PASS. `kit-lint` makes no judgment —
  it byte/render-compares projections to the source and reports drift for a human to fix
  (via `retail init` re-projection). The source-vs-constitution question, which WOULD be
  a judgment call, was deliberately CUT and deferred as a human-shaped governance slice
  rather than faked. `kit-lint` reads no constitution prose (FR-010) and edits nothing
  (FR-004).
- **Principle VII (C086 Is An Example, Not The Schema)**: PASS. No worked-example
  specifics; the linter compares generic kit projections to their source.
- **Principle VIII (Static-First Governance)**: PASS. Standalone step; the `retail check`
  core stays stdlib-only (DEC-1). `kit-lint` may import pyyaml lazily to parse the source,
  matching `semantic-check` / `value-check`. No DB, no network, no execution.
- **Principle IX (Secrets / Reproducibility / Windows-safe)**: PASS. Read-only; writes no
  files, so no encoding/EOL authoring concern. Reads tolerate a BOM (`utf-8-sig`) and use
  universal newlines; the byte-exact YAML check inherits 070's `.gitattributes` LF pin.
- **Hard rule #8 (templates/docs first, automate after artifacts prove useful)**: PASS.
  The 070 substrate + the two drift-check callables already exist and are in use; this
  feature turns proven callables into an enforced gate + adds the deferred half.
- **Hard rule #9 (no fabricated confidence score)**: PASS. `kit-lint` emits explicit
  pass/fail per check + the exit code; no numeric drift / health / confidence score
  (FR-009). Each projection check is a byte/render equality, not a scored similarity.
- **Constitution-amendment safety**: PASS. `kit-lint` reads the kit source + its
  projections; it never edits AGENTS.md / CLAUDE.md or the constitution, and never reads
  constitution prose. It PARTIALLY addresses 070's MINOR-5: the fenced body is now
  machine-verified against the SOURCE (drift can't merge), but the SOURCE-vs-constitution
  half stays human-reviewed-at-ratify (that check was cut — see the scope-cut note).
- **Anti-fork discipline**: PASS. The projection checks reuse 070's single
  implementations (no re-derivation).
- **Readiness spine**: PASS. Advances NO readiness stage; introduces no readiness score;
  matches `manifest.py` / `severity_posture.py` / the 070 substrate.

No violations. No complexity-tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/072-kit-drift-linter/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1 (CheckResult / LintReport shapes)
├── contracts/           # Phase 1 (kit-lint report contract)
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/retail/
├── kit_lint.py    # NEW: the two projection-drift checks + lint()/report
└── cli.py         # MODIFIED: add the `kit-lint` subcommand (thin; lazy-imports kit_lint)

.github/workflows/
└── ci.yml         # MODIFIED: add a `retail kit-lint` step after retail semantic-check

tests/unit/
└── test_kit_lint.py   # NEW: drift detection, not-bootstrapped, parse-error, no-constitution-read, read-only
```

**Structure Decision**: Single module `src/retail/kit_lint.py` holding the two
projection-drift checks + `lint()`. The CLI handler is thin and lazy-imports the module
(keeping the check path yaml-free), exactly like `_run_semantic_check`. The projection
checks are NOT re-implemented — `kit_lint` calls `compass_project`'s
`check_yaml_drift` / `check_prose_drift`.

## Complexity Tracking

> No Constitution Check violations. No entries required.
