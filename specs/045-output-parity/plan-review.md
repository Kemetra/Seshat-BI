# Adversarial Plan-Review: Text/JSON Output Equivalence Property Test

**Date**: 2026-06-29 | **Branch**: `045-output-parity`
**Reviewer posture**: single default-adverse skeptic, READ-ONLY (reports fixes, edits nothing).
**Artifacts reviewed**: spec.md, plan.md, tasks.md, analysis.md (all present).

A draft missing analyze or tasks is automatic BLOCKED. Both are present and committed -> not
auto-blocked on completeness. Proceeding to the five axes.

## Axis 1 -- Hidden principle violation

- Principle I (gate-enforced): the test asserts the two paths agree on the exit code; it hardens
  the gate and adds no new rule. No violation. It does NOT itself run inside `retail check`, so it
  cannot weaken the gate surface.
- Principle V (stops at judgment calls): the ONE judgment call (roadmap promotion) is reserved for
  the owner and NOT answered. No grain/PII/rollup/identity decision is embedded (the test operates
  on synthetic in-memory findings -- no data grain, no published PII, no business segment, no
  product identity). Correct posture.
- Principle VIII (static-first, stdlib-only): the test imports only stdlib + `retail.core` +
  `retail.runner`, and FR-010 + T011 explicitly forbid importing `retail.rules` or `psycopg2`.
  WATCH ITEM (not a violation): importing `retail.runner` must not transitively import the rules
  package -- but `tests/unit/test_runner.py::test_importing_runner_does_not_import_rules_package`
  already proves the runner has no such transitive import, so the constraint is satisfiable and
  already guarded by an existing test. No violation.
- Principle IX (Windows-safe text): no committed text artifact is read by this test, so there is no
  on-disk byte-stability surface; the only text-handling concern is the trailing-newline split on
  captured stdout, which FR-012/T006 address. No violation.

Verdict: no hidden principle violation.

## Axis 2 -- Assumes deferred capability

- No artifact assumes the Power BI Execution Adapter (F016) or any spec-only runtime (F031-F033).
  Spec Assumptions, plan Technical Context, and tasks Out-of-Scope all state this explicitly.
- The test runs the EXISTING `run`/`run_json` functions over in-memory synthetic rules -- both
  functions exist today (confirmed at `src/retail/runner.py` lines 84-117). No unbuilt capability
  is leaned on.
- The real-registry tmp-repo fixture (whose existence is UNCONFIRMED per the grounding) is
  deliberately NOT assumed: Q1 scopes the property to synthetic fixtures precisely so the test does
  not depend on an artifact that may not exist. This is the correct mitigation of the one genuine
  grounding gap.

Verdict: no deferred-capability assumption.

## Axis 3 -- C086 leak

- FR-011, SC-004, US3, and tasks T005/T011 all mandate generic synthetic fixtures and explicitly
  forbid billing codes, insurance/PII columns, pharmacy rule ids, and worked-example locators.
- The c086_risk the grounder flagged (a fixture author reaching for the real C086 rules or a
  pharmacy tmp-repo) is structurally avoided by Q1's synthetic-only decision -- there is no path in
  this plan that touches the real registry or a worked-example repo.

Verdict: no C086 leak; the known risk is mitigated by construction.

## Axis 4 -- Fabricated confidence

- Status remains "**Status**: Draft". No "Ratified" line is authored (verified: zero occurrences).
- No numeric readiness/health/confidence score is invented anywhere (hard rule #9). The test
  asserts an EXACT equivalence (Counter equality + integer exit-code equality); SC-001 says
  divergence is caught "100% of the time", which is a property-of-the-assertion statement, not a
  fabricated metric.
- The analyze verdict (CLEAN, 0/0) is backed by the coverage matrices in analysis.md, not asserted
  bare.
- The spec correctly DOWNGRADES the backlog's "V7 / F8" tag to a scoring-panel score (not a roadmap
  F-number) and the "33-vs-34 rule" note to irrelevant-for-this-test, rather than parroting them as
  fact. No inherited fabricated confidence.

Verdict: no fabricated confidence.

## Axis 5 -- Over-scope

- The feature adds exactly ONE file (`tests/unit/test_runner_output_parity.py`); plan Structure
  Decision and tasks Path Conventions both pin this.
- FR-008/FR-009 + T012 + tasks Out-of-Scope forbid: new rule, new EXPECTED_RULE_ID, any change to
  `runner.py`/`core.py`, a real-registry fixture, a robust adversarial parser, and any
  DB/network/Power BI/executor wiring. The git diff against main shows zero src/ changes.
- The two deferred design options (real-registry fixture Q1; robust inverse parser Q2) are recorded
  as explicitly out-of-scope rather than silently pulled in. This is disciplined YAGNI.

Verdict: no over-scope.

## Residual notes (non-blocking)

1. (LOW) The inverse-of-`_format` parser correctness depends entirely on the fixture-shape
   constraint in FR-006 (no embedded ") (" or unescaped brackets). This is sound for a property
   over CONTROLLED fixtures, but the implementer MUST keep the constraint honored when adding
   fixtures later; T005/T006 carry it, so it is documented, not hidden. Not a blocker.
2. (LOW) US1 and US2 are both labelled P1. That is intentional (the two halves of one property), but
   a reader skimming priorities should note the MVP is "both halves", not "either half". The spec's
   "Why this priority" text makes this clear. Not a blocker.
3. (INFO) Branch numbering: this feature took `045` (not the script-proposed `044`) because four
   concurrent sibling workflows had already claimed `044-*` branch names; the spec header documents
   this. The ratify handoff must target THIS worktree's `045-output-parity` branch, not the
   abandoned empty `044-output-parity` shell that exists in a separate worktree. Recorded so the
   handoff does not point at the wrong branch.

## Verdict

PASS. All five axes clear with no CRITICAL or HIGH finding. Two LOW residual notes and one INFO
note (branch-number provenance) are recorded for the implementer/operator but do not block. The
spec stays Draft; ratification is the human owner's action, including the one reserved Principle-V
roadmap-promotion call.
