# Implementation Plan: Background-Spec Forbidden-Dynamic-Content Assertion Rule

**Branch**: `064-background-spec-purity` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/064-background-spec-purity/spec.md`

## Summary

Add one static governance rule to the retail rule registry that discovers
committed FILLED background specs and asserts the declared boolean contract from
`templates/background-spec.yaml`: every `forbidden_dynamic_content` key MUST be
`false` (a `true` entry is a declared defect) and every `qa_checklist` item MUST
be `true` (or `false` with a recorded reason). A declared violation is an ERROR
finding with a file-plus-pointer locator; a compliant filled spec produces no
findings. The rule is stdlib-only at module scope (YAML is a lazy in-function
import), generic (discovers filled specs by a suffix convention, exempts the
blank template and test fixtures, never hardcodes a tenant path/key), inert on an
empty corpus (zero filled specs -> zero findings), and wired into the five
governance records. This is the surface-2 sibling of the shipped surface-3
theme-JSON purity rule (DL1, spec 060). The filled-spec file-discovery convention
is a Principle-V owner-convention judgment recorded OPEN in the spec
Clarifications; this plan defines the seam that consumes that convention, and the
rule stays inert (green) until the convention is ruled and a filled spec lands.

## Technical Context

**Language/Version**: Python 3.13 (CI); 3.12 local also supported. Stdlib only at
module scope; YAML via a lazy in-function import (PyYAML is a dev/optional dep,
never in the never-execute static core -- B1/B3).

**Primary Dependencies**: None beyond the standard library and the existing
in-repo retail governance framework (`src/retail/registry.py`, `src/retail/core`).
YAML parsing is deferred to a function-local `import yaml`, matching the existing
YAML-reading rules (`assumptions.py`, `parked_on.py`, `readiness_status.py`). No
new third-party package is added to the check core.

**Storage**: N/A -- the rule reads committed text files; it persists nothing.

**Testing**: pytest, `-m unit`. Fixture-based unit tests under `tests/unit/`,
using the `is_test_path` exemption so fixtures may deliberately declare defects.

**Target Platform**: CI (Linux) and local Windows; runs as part of the `retail
check` governance gate.

**Project Type**: Single project -- a library rule module inside an existing
package, invoked by the existing rule runner.

**Performance Goals**: Negligible -- the committed filled-spec corpus is small
(zero today; order of tens at most); a single YAML parse + boolean assertion pass
per file is sufficient.

**Constraints**: stdlib-only at module scope (YAML lazily imported); no network,
no Power BI Desktop, no image library, no live service, no rendering (Principle
VIII, Principle II). ASCII, UTF-8 without BOM, short paths (Principle IX). Generic
vocabulary/convention only (Principle VII). Fails closed on a declared violation
per the resolved ERROR severity (Principle I). No adjudication of a reason's
adequacy, no numeric score, no self-granted readiness (Principle V).

**Scale/Scope**: One new rule module (~1 file), five golden-record wiring touches,
one fixture set + unit tests. No new subsystem.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS -- a declared-contract
  violation is an ERROR that drives a non-zero exit; the rule enforces, it does
  not advise.
- **Principle II (Depend, Never Fork / execution-only deferred)**: PASS -- the
  rule authors no PBIP/PBIR, runs no DAX, opens no image, performs no import; it
  only asserts the declarative surface-2 spec's own booleans. Consistent with
  surface-2 being NOT gated on contracts and import_instructions being NOTES only
  (F016 owns any automation).
- **Principle V (Agent Stops at Judgment Calls)**: PASS -- the rule performs only
  a categorical boolean/reason-presence check; it computes no confidence/readiness
  score and never self-grants a readiness or dashboard-ready pass. The filled-spec
  discovery convention is RECORDED as an OPEN human ruling, not auto-invented; the
  rule stays inert until it is ruled, so nothing is frozen ahead of the human.
- **Principle VII (C086 Is An Example, Not The Schema)**: PASS -- the rule
  discovers filled specs by a generic suffix convention and derives its boolean
  vocabulary verbatim from the generic template contract; no tenant/pharmacy/brand
  path or key appears in the rule.
- **Principle VIII (Static-First Governance)**: PASS -- stdlib-only at module
  scope over committed text, CI-able, no live dependency, no rendering. The YAML
  read is a lazy in-function import so the never-execute static core stays
  stdlib-only (B1/B3). Squarely static-core.
- **Principle IX (Secrets/Reproducibility)**: PASS -- reads a declarative spec
  that carries no secrets; all authored artifacts are ASCII / UTF-8-no-BOM /
  short-path.
- **Ratified 044 (severity observed, not declared)**: PASS -- the rule declares
  one id; severity is observed per branch from emitted findings. No governed
  per-rule severity table is introduced.
- **YAGNI / scope discipline**: PASS -- adds the seam (a declared-boolean-contract
  assertion), not an image-binary verifier, not a required-key invention beyond
  the template's declared blocks, and not a discovery convention the human has not
  yet ruled.

No violations. Complexity Tracking table omitted (nothing to justify).

## Project Structure

### Documentation (this feature)

```text
specs/064-background-spec-purity/
|-- plan.md              # This file
|-- research.md          # Phase 0 output
|-- data-model.md        # Phase 1 output
|-- quickstart.md        # Phase 1 output
|-- contracts/
|   `-- rule-contract.md  # Phase 1 output (the rule's behavioral contract, C1..Cn)
|-- checklists/
|   `-- requirements.md   # Spec quality checklist (Stage 2)
`-- tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/retail/
|-- registry.py                 # existing: @register decorator + all_rules() (unchanged)
|-- core.py                     # existing: Finding, RuleContext, Severity, is_test_path (unchanged)
|-- severity_posture.py         # existing: regenerated golden record (adds the new id)
`-- rules/
    |-- __init__.py             # MODIFIED: add design_background to import tuple + __all__
    |-- design_theme.py         # existing: closest structural precedent (DL1)
    |-- readiness_status.py     # existing: lazy `import yaml` precedent
    `-- design_background.py    # NEW: the @register declared-boolean assertion rule

docs/rules/
|-- rules-manifest.json         # REGENERATED: adds the new rule id + title
`-- severity-posture.json       # REGENERATED: adds the new rule id's observed severity

tests/unit/
|-- test_rules_wiring.py        # MODIFIED: add new rule id to EXPECTED_RULE_IDS
|-- test_rules_manifest_snapshot.py  # (golden asserts; regenerated snapshot)
|-- test_severity_posture.py         # (golden asserts; regenerated snapshot)
`-- test_design_background.py   # NEW: fixture-based unit tests for the rule
    (+ fixture filled-spec YAML files under the test-exemption path)
```

**Structure Decision**: Single-project library rule. The rule module joins the
existing `src/retail/rules/` package and is discovered by the existing runner via
the side-effecting import in `__init__.py`. This mirrors every existing rule
(design_theme.py is the closest structural precedent, readiness_status.py the
closest YAML-lazy-import precedent) and requires no new subsystem, directory, or
dependency.

## Phase 0 -- Research

See [research.md](./research.md). Key decisions:
- Reuse the `design_theme.py` structural pattern (generic discovery, is_test_path
  exemption, categorical check, one Finding per violation with a `file#/pointer`
  locator, unparseable -> Finding not crash, @register).
- Reuse the `readiness_status.py` lazy in-function `import yaml` pattern to keep
  the never-execute static core stdlib-only (B1/B3).
- Discover filled background specs generically by a suffix convention (recommended
  default `*.background.yaml`), exempt `templates/` and the test-fixture path.
  The exact suffix is the OPEN owner-convention ruling; represented as a single
  module-level constant seam pending that ruling.
- Assert the DECLARED boolean contract: `forbidden_dynamic_content` keys MUST be
  `false`; `qa_checklist` items MUST be `true` or `false`-with-reason. The
  boolean vocabulary is frozen verbatim from the template (Clarifications Q2).

## Phase 1 -- Design

See [data-model.md](./data-model.md), [contracts/rule-contract.md](./contracts/rule-contract.md),
and [quickstart.md](./quickstart.md).

**Constitution re-check after design**: no new violations introduced. The design
keeps the boolean vocabulary as a single generic constant frozen from the
template, keeps the discovery convention as a single documented seam pending the
human ruling, keeps the check categorical (boolean + reason-presence only), and
keeps the rule inert on an empty corpus -- consistent with Principles II, V, VII,
VIII and ratified 044.

## Phase 2 -- Tasks

Generated by `/speckit-tasks` into [tasks.md](./tasks.md). Task ordering follows
TDD (fixtures + failing tests first, then the rule, then the five-place wiring,
then regenerate the golden records, then the full wiring/gate check).

## Complexity Tracking

Not applicable -- Constitution Check has no violations.
