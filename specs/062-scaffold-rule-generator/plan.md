# Implementation Plan: Scaffold-Rule Authoring Generator + Doctor

**Branch**: `062-scaffold-rule-generator` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/062-scaffold-rule-generator/spec.md`

## Summary

Add a static, stdlib-only authoring helper -- exposed as a new `scaffold`
subcommand -- with two modes. Scaffold (author) mode WRITES the mechanical
boilerplate a new governance rule needs (a stub rule module, a matching failing
test stub, and an insertion of the new id into the expected-id source-of-truth
set) and PRINTS -- never runs -- the two golden-regen commands and a suggested
glossary row. Doctor (verify) mode READS the five wiring places and reports, per
rule id (single or sweep), which places the id is present in and which it is
missing from. The helper is a thin author over the existing hand-written shape;
it never runs a regeneration, never edits prose, and never self-grants a wiring
pass. Its own five-place list is a declared, guard-tested artifact so it cannot
silently drift.

## Technical Context

**Language/Version**: Python 3.11+ (matches the existing `src/retail/` core;
local dev is 3.13, CI is 3.13).

**Primary Dependencies**: Python standard library only (`argparse`, `pathlib`,
`re`, `ast`/text-parsing, `json` for reading golden records). No third-party
runtime dependency; `dependencies = []` invariant preserved.

**Storage**: None. Reads and writes repo text files only.

**Testing**: pytest, `-m unit` marker, following the existing
`tests/unit/test_*` convention.

**Target Platform**: Local dev + CI (Windows/Linux); pure static, no DB/network.

**Project Type**: Single project -- a CLI subcommand + one new module under
`src/retail/`, mirroring the existing generators (`manifest.py`,
`severity_posture.py`).

**Performance Goals**: Not performance-sensitive; a single scaffold or a full
sweep over the registered rule set completes in well under a second (reads a
handful of files).

**Constraints**: stdlib-only; no execution of rules/model; no DB/network; UTF-8
no BOM; ASCII-safe output; short repo-relative paths (Principle IX). The
write/print split is a hard boundary: the only files scaffold writes are the stub
module, its test, and the expected-id set; everything else is printed.

**Scale/Scope**: First step only. One new module (`src/retail/scaffold.py`), one
new subcommand in `cli.py`, one new test file, and a guard test for the
five-place list. No dynamic repo-introspecting place discovery.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS. The helper is a helper the
  agent calls; it never becomes the authority. Doctor reports presence/absence;
  it MUST NOT declare a rule approved. The test suite + gate exit code remain the
  truth (FR-018, DEC-2).
- **Principle V (Agent Stops at Judgment Calls)**: PASS. The helper never invents
  rule intent (DEC-1), never auto-edits prose (glossary is print-only, FR-008),
  never runs the golden regenerations (print-only, FR-006/FR-007), and never
  self-grants a wiring pass. The three human-owned decisions are recorded, not
  answered.
- **Principle VII (C086 Is An Example, Not The Schema)**: PASS. The generated
  stub rule and test carry generic placeholder logic with zero worked-example
  specifics (FR-003). The known drift instance is cited generically as a Doctor
  fixture, never hardcoded.
- **Principle VIII (Static-First Governance)**: PASS. stdlib-only, no DB, no
  network, no execution -- matches `manifest.py` and `severity_posture.py`
  exactly (FR-016).
- **Hard rule #8 (templates/docs first, automate after artifacts prove useful)**:
  PASS. The ceremony has many hand-wired instances and a proven drift, so
  automating a thin author over the existing shape is justified.
- **Principle IX (Secrets/Reproducibility/Windows-safe)**: PASS. Authored files
  are UTF-8 no BOM, ASCII, short paths (FR-019). No secrets involved.
- **Readiness spine**: PASS. Advances NO readiness stage (DX/governance tooling);
  the plan introduces no readiness score.

No violations. No complexity-tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/062-scaffold-rule-generator/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── scaffold-cli.md  # CLI contract (subcommand surface + write/print split)
├── checklists/
│   └── requirements.md  # From /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/retail/
├── cli.py               # EDIT: add `scaffold` subparser + dispatch (mirrors manifest/severity-posture)
├── scaffold.py          # NEW: the author + doctor logic (write/print split; declared 5-place list)
├── registry.py          # UNCHANGED (register/all_rules mechanism the stub calls)
└── rules/
    ├── __init__.py      # (place #2) generator PRINTS the import/__all__ edit; may write the stub module file
    └── <new_stub>.py    # generated stub module (per invocation; not committed by this feature)

tests/unit/
├── test_scaffold.py     # NEW: TDD for scaffold write/print split + doctor report + input validation
└── test_rules_wiring.py # (place #3) generator inserts the new id into EXPECTED_RULE_IDS
```

Note: the `<new_stub>.py` and the EXPECTED_RULE_IDS insertion are what the helper
PRODUCES at author time for a real new rule; this FEATURE ships the helper +
tests, not a specific new rule.

## Design Decisions

1. **Write/print split is enforced in code, not convention.** Scaffold has
   exactly three write targets (stub module, test stub, expected-id set) and a
   fixed set of print targets (two regen commands, one glossary row). A test
   asserts scaffold touches no other file (SC-004).

2. **Five-place list is a declared constant with a guard test (FR-017).** The
   list lives as an explicit in-code declaration in `scaffold.py`. A guard test
   cross-checks it against the wiring places the repo actually has, so a future
   sixth place forces a list update. Dynamic discovery is deferred (YAGNI).

3. **Doctor is pure read + report.** Doctor reads: the registry (place #1), the
   package import list + `__all__` (place #2), the expected-id set (place #3),
   the two golden record JSON files (place #4), and the glossary prose rows
   (place #5). It returns a per-id, per-place presence record and never writes.

4. **Doctor exit-code contract (FR-014)** is stated explicitly in the CLI
   contract: Doctor exits non-zero when it finds drift (so CI can gate on it) and
   zero when every checked id is present in every place; an unknown/unregistered
   id is reported without the crash-style exit of a real defect.

5. **Insertion into EXPECTED_RULE_IDS is a WRITE, deliberately.** Per the idea's
   own design and the clarify ruling, the expected-id set is a source-of-truth
   set the author is entitled to have the helper edit (it is a mechanical
   membership insertion, not a judgment). The two GOLDEN records and the PROSE
   glossary are NOT written (they carry regeneration/editorial semantics) --
   those stay print-only. This asymmetry is the load-bearing boundary of the
   feature and is called out for the reviewer.

## Deferred / Not Built (guard against assuming these exist)

- No Power BI execution adapter, no live DB validation, no runtime -- none are
  touched or assumed (F016 / F031-F033 remain deferred and irrelevant here).
- No dynamic five-place discovery engine.
- No auto-repair of drift (Doctor reports only).
- No new readiness stage or score.

## Phase 0: Research

See [research.md](./research.md): confirms the five places against the live repo,
the stdlib-only posture of the existing generators, the existing drift instance,
and the hardcode-vs-derive decision.

## Phase 1: Design

See [data-model.md](./data-model.md) (the entities: WiringPlace, ScaffoldResult,
DoctorReport) and [contracts/scaffold-cli.md](./contracts/scaffold-cli.md) (the
subcommand surface, arguments, write/print split, and exit-code contract), plus
[quickstart.md](./quickstart.md).
