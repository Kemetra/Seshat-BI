# Quickstart: Background-Spec Forbidden-Dynamic-Content Assertion Rule

## What it does

Once a page's background spec is filled from `templates/background-spec.yaml`, this
rule asserts the spec's OWN declared boolean contract:

- every `forbidden_dynamic_content` key MUST be `false` (a `true` entry is a
  declared defect -- move that content up to a live visual);
- every `qa_checklist` item MUST be `true`, or `false` with a recorded reason.

A declared violation is an ERROR that fails the `retail check` gate. A compliant
filled spec produces no findings. With no filled spec on disk, the rule is inert.

## Run it

```bash
# Full governance gate (includes this rule):
retail check

# Just the unit tests for this rule:
pytest -m unit tests/unit/test_design_background.py
```

## How a filled spec passes

1. Copy `templates/background-spec.yaml` to the committed filled-spec location
   (per the owner's discovery convention -- recommended `*.background.yaml`).
2. Set every `forbidden_dynamic_content` key to real `false` (no baked-in KPI,
   title, measure, data label, date stamp, filter state, or visual screenshot).
3. Set every `qa_checklist` item to real `true`, or `false` with a recorded
   reason. Replace every `<true|false>` placeholder with a real boolean.

## What it will NOT do

- It does not open or render the background IMAGE; it asserts what the spec
  DECLARES (static-first; image verification is out of scope).
- It does not compute a confidence/readiness score and never self-grants a
  readiness or dashboard-ready pass (that is the design-review verb owner's
  recorded human review).
- It does not flag the ABSENCE of a filled spec; it is inert until content lands.

## OPEN before wiring

The filled-spec file-discovery convention (the suffix that marks a committed
filled spec) is an owner ruling recorded OPEN in the spec Clarifications. The rule
stays inert and green until the owner sets it; wiring the golden records is gated
on that ruling.
