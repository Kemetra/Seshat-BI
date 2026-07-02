# Adversarial Plan-Review: 067 Land bi-python's Planned Cleaning Artifacts

**Date**: 2026-07-02 | **Reviewer stance**: single default-adverse skeptic,
READ-ONLY (reports fixes, does not edit). **Inputs**: spec.md, plan.md, tasks.md,
analysis.md (all present -- not an automatic BLOCKED).

Five axes checked: hidden-principle-violation, assumes-deferred-capability,
c086-leak, fabricated-confidence, over-scope.

---

## Axis 1 -- Hidden principle violation

**Probe**: Does landing a "review checklist that ends on a verdict" smuggle
gating / metric-meaning / a threshold into a layer whose SKILL.md says it does
NOT own gating or metric meaning?

- The layer ALREADY ships a verdict-ending checklist (`aggregation-grain-checklist.md`
  ends on AGGREGATION SOUND / NON-ADDITIVE MISUSE / GRAIN UNCLEAR / BLOCKED). A
  cleaning review checklist that mirrors that shape is precedented, not novel; it
  is a REVIEW verdict about source-prep soundness, not a readiness/gating decision
  and not a metric definition. Boundary respected.
- FR-006 + SC-006 forbid a numeric score; the verdict is categorical; exact
  vocabulary + pass criteria are DEFERRED to a human ratifier (spec
  ## Clarifications). This is the correct handling of the threshold risk.
- FR-007 keeps human-reserved cleaning decisions (sentinel meaning, dedup
  keep-policy, out-of-range keep-vs-flag, category-domain update) as
  "recorded by a human" checkboxes -- no auto-resolution. Principle V respected.

**FINDING PR-1 (LOW, fabricated-confidence-adjacent)**: T007 and FR-002 pre-commit
to a "four-state" verdict shape. The EXACT verdict set is explicitly deferred to a
human (FR-006), yet fixing the CARDINALITY at four subtly pre-decides part of that
deferred definitional call. Fix: soften T007/FR-002 to "a small set of categorical
verdicts mirroring the aggregation checklist's shape (cardinality to be confirmed
by the ratifier)" so the build does not lock a number the human is meant to rule on.
Non-blocking -- the deferral note already routes the decision to a human; this only
tightens wording.

## Axis 2 -- Assumes a deferred capability

**Probe**: Does any artifact assume F016 (Power BI Execution Adapter) or F031-F033
(spec-only runtimes), or an unshipped I1 route-honesty rule?

- Plan Constraints + spec Assumptions explicitly state deferred capabilities are
  NOT assumed and are irrelevant to a docs-only change. Confirmed no runtime,
  no executor, no new retail check rule anywhere in tasks.
- I1 dependency: spec Assumptions + Clarification C2 correctly record that I1 is
  NOT shipped and NOT a dependency; I2 stands alone. No artifact assumes an I1
  guard exists. Clean.

**No finding.**

## Axis 3 -- C086 / pharmacy leak

**Probe**: Will a generic knowledge artifact bake in pharmacy specifics?

- FR-014 + SC-006 + T015 mandate fictional-retail-schema-only examples and forbid
  inline C086 specifics; C086 allowed only as an EXTERNAL worked-example citation.
  The risk is real (grounding flags it) but the guard is explicit and verified by a
  dedicated task. Clean at plan level; the actual leak can only occur at build time
  and T015 catches it.

**No finding.**

## Axis 4 -- Fabricated confidence

**Probe**: Does any artifact self-grant a readiness pass, a numeric score, or an
F-row?

- Spec Status stays "Draft" (not "Ratified"). Correct -- ratification is a human act.
- FR-016 forbids self-assigning a roadmap F-row / readiness stage; the roadmap-stage
  question is deferred to a human. Correct.
- analysis.md verdict "clean (0 critical / 0 high)" is a genuine cross-artifact
  consistency result, not a readiness score. No cleanliness/quality NUMBER is
  emitted for the feature itself.

**No finding.**

## Axis 5 -- Over-scope

**Probe**: Does the plan build more than the one advertised dead-end needs?

- Clarification C1 explicitly EXCLUDES the optional 1-2 pattern files; tasks.md has
  NO pattern-file task. FR-011 + T010/T011/T016 forbid flipping any other planned
  sibling. Scope = 1 new file + 3 edited files. This is the minimal fix for the one
  route. YAGNI respected.
- The `missing_or_deferred` traps from grounding (groupby knowledge file, profiling,
  dtypes, validation, other planned checklists) are all explicitly kept planned by
  FR-011 and verified by T016.

**No finding.** (Scope is, if anything, admirably tight.)

---

## Summary of findings

| ID | Severity | Axis | Finding | Fix |
|---|---|---|---|---|
| PR-1 | LOW | hidden-principle / fabricated-confidence | T007+FR-002 lock verdict cardinality at "four" while FR-006 defers the verdict set to a human | Soften to "a small set ... cardinality confirmed by ratifier" |

No CRITICAL, no HIGH, no MEDIUM findings. One LOW wording nit that does not block
the build (the deferral to a human is already recorded; PR-1 only prevents the
build from silently pre-deciding the count).

## Verdict

Verdict: PASS-WITH-NOTES

Rationale: All required artifacts (spec, plan, tasks, analysis) are present and
internally consistent; requirements are fully task-covered; every constitutional
gate the plan asserts maps to a real requirement; scope is minimal; the two
Principle-V definitional calls are correctly deferred to a human, not fabricated.
The single LOW note (PR-1) is a wording tightening for the deferred verdict-set
cardinality, safely addressable at build time or by the ratifier -- it does not
undermine the spec. No axis produced a blocking violation.
