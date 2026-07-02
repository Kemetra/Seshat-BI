# Rule Behavioral Contract: Background-Spec Forbidden-Dynamic-Content Assertion

The rule's behavior is specified as contract rows C1..C13, each an
independently-testable assertion mapped to a unit test in
`tests/unit/test_design_background.py`. RED->GREEN TDD: each row is a failing
test before the rule implements it.

## Discovery + exemption

- **C1 (generic discovery)**: Given more than one committed filled background spec
  matching the discovery convention, the rule scans EVERY matching file, not a
  hardcoded list. (FR-002)
- **C2 (template exempt)**: Given the blank `templates/background-spec.yaml`
  (values are `<true|false>` placeholders), the rule does NOT treat it as a filled
  spec and emits zero findings for it. (FR-002)
- **C3 (fixture exempt)**: Given a filled spec under the test-fixture exemption
  path, the live scan does NOT treat it as a live filled spec (fixtures may
  declare defects to exercise the rule). (FR-010)
- **C4 (inert on empty)**: Given zero committed filled specs matching the
  convention, the rule emits zero findings and does not error or flag the absence.
  (FR-011)

## forbidden_dynamic_content assertions

- **C5 (true forbidden key -> ERROR)**: Given a filled spec whose
  `forbidden_dynamic_content` sets a key to real `true`, the rule emits exactly one
  `Severity.ERROR` finding naming the file and a `file#/pointer` to that key, and
  the check fails closed. (FR-001, FR-003, FR-008)
- **C6 (two true keys -> two findings)**: Given two distinct forbidden keys set
  `true` in one filled spec, exactly two findings are emitted (one per key), no
  masking. (FR-004)
- **C7 (all false -> pass)**: Given a filled spec whose forbidden keys are all
  real `false`, the rule emits zero findings for that block. (FR-006)
- **C8 (placeholder in forbidden key -> finding)**: Given a discovered filled spec
  whose forbidden key value is still the `<true|false>` placeholder, the rule
  emits a finding (half-filled, not asserted). (Clarifications Q1)
- **C9 (non-boolean forbidden value -> finding)**: Given a forbidden key set to a
  string/number (not a real boolean), the rule emits a finding (malformed against
  the boolean contract). (FR-005 edge)

## qa_checklist assertions

- **C10 (true item -> pass; bare false -> finding)**: Given a `qa_checklist` item
  that is real `true`, zero findings; given the same item real `false` with NO
  recorded reason, exactly one finding. (FR-001, SC-005)
- **C11 (false with reason -> pass)**: Given a `qa_checklist` item that is `false`
  WITH a non-empty, non-placeholder recorded reason, the rule emits zero findings
  for that item (a reasoned warning is accepted). (FR-006, Clarifications Q3)

## Robustness + genericity

- **C12 (unparseable -> finding, no crash)**: Given a discovered filled spec that
  cannot be parsed as YAML, the rule emits a finding and does NOT raise or silently
  pass the file. (FR-009)
- **C13 (generic vocabulary, no tenant literal)**: The asserted key set is exactly
  the frozen template vocabulary (7 forbidden + 9 qa); no tenant/example/brand path
  or key appears anywhere in the rule. (FR-007, SC-006)

## Invariants across all rows

- The rule performs a categorical boolean + reason-PRESENCE check only; it never
  inspects an image binary, never renders, never judges a reason's adequacy, never
  computes a score, never self-grants readiness (FR-005, FR-012, FR-015).
- YAML is imported lazily inside the check function; the module scope stays
  stdlib-only (FR-012, B1/B3).
- One `Finding` per violation with a `file#/pointer` locator; a compliant filled
  spec produces zero findings.

## Gated by the OPEN owner ruling

The discovery-convention SUFFIX literal (recommended default `*.background.yaml`)
is the OPEN Principle-V owner-convention ruling (spec Clarifications). C1-C13 are
written against a single convention constant; the golden-record freeze (wiring
phase) MUST NOT be committed until the owner's convention is recorded, because the
suffix is encoded into the fixtures and the live discovery. Until then the rule is
inert (C4) and green.
