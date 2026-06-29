# Adversarial Plan-Review: Severity-Posture Regression Lock (044)

**Reviewer stance**: single default-adverse skeptic. READ-ONLY -- findings name
fixes; no artifact was edited. Five axes: hidden-principle-violation,
assumes-deferred-capability, c086-leak, fabricated-confidence, over-scope.

**Date**: (date pending -- operator to fill)

**Inputs reviewed**: spec.md, plan.md, tasks.md, analysis.md (all present;
analyze verdict clean). A draft missing analyze or tasks would be automatic
BLOCKED -- both are present, so that auto-block does not apply.

## Axis 1 -- Hidden principle violation

- **Principle V (the load-bearing one).** The grain (FR-009) and L3 coverage
  (FR-010) are the two judgment calls. They are REFUSED in spec `## Clarifications`
  and HARD-GATED by tasks T000 (which explicitly blocks T004 and T010). The plan
  repeatedly states grain/coverage are parameters, not plan decisions. I tried to
  find a place where the agent quietly picks a grain anyway -- the closest is the
  plan's "the plan stays correct under all three options" and the analysis M1
  note, but both stop short of choosing. VERDICT: no hidden resolution. Clean.
- **Principle I.** The lock strengthens (never weakens) the gate; it adds no new
  EXPECTED_RULE_ID and does not touch exit-code logic. Clean.
- **ADR-0007 (semantic.py has zero @register).** T010 and the Out-of-Scope blocks
  explicitly forbid adding @register to semantic.py under either L3 ruling. Clean.

  One LOW note recorded below (axis 5) on T010's phrasing.

## Axis 2 -- Assumes deferred capability

- Searched for any dependency on the Power BI Execution Adapter (F016) or the
  spec-only runtimes (F031-F033). None. Observation is over planted text fixtures
  via in-process rule calls; no live model/query/agent. The plan and tasks both
  carry explicit "no dependency on F016 or F031-F033" lines. Clean.

## Axis 3 -- C086 / example-domain leak

- The record itself keys on generic rule ids + severity classes (FR-006, SC-005).
- The real leakage vector is the planted FIXTURES used to trigger rules (the
  grounding flagged this). T007 mandates fixtures be synthetic/minimal,
  NON-exempt-path, and contain NO example-domain table/column/value, and SC-005
  asserts 0 example-domain identifiers in the record. The plan's Principle-VII
  paragraph names the fixture vector explicitly.
- RESIDUAL RISK (LOW, recorded): SC-005 measures the RECORD, not the fixture
  FILES. A fixture file could still inadvertently embed an example-domain name
  without tripping SC-005. The intent is covered by FR-006/T007 prose but there
  is no success criterion that scans the fixture files themselves. Fix named
  below. Not a blocker -- the record (the committed generic artifact) is
  protected; the fixtures live under tests/ and are synthetic by mandate.

## Axis 4 -- Fabricated confidence

- No numeric readiness/health/confidence score anywhere (Hard rule #9). The record
  is an exact observed posture (class equality). The analysis verdict "clean" is
  backed by an explicit coverage matrix, not an assertion. SC values are counts
  (0 new rules, 0 byte diff), not invented percentages. No self-granted readiness
  pass; Status stays "Draft". Clean.

## Axis 5 -- Over-scope (YAGNI)

- The feature is one helper module + one generator subcommand + one golden JSON +
  one test + one .gitattributes line -- a tight mirror of the 043 sibling. No
  `--check` CI mode, no rule reordering, no new gating rule. Out-of-Scope blocks
  in plan and tasks are explicit and aligned. Clean.
- LOW note: T010 ("if L3 ruled IN, observe semantic.verdict_to_finding over both
  verdict statuses") edges toward implementation specifics for a path that may be
  ruled OUT. This is acceptable -- it is conditional on T000 and adds no scope
  unless the human opts in -- but the implementer should not pre-build the L3
  section before the ruling.

## Recommended fixes (none blocking)

1. **(LOW, axis 3)** Add a check (or fold into T007/T018) that scans the planted
   fixture FILES under `tests/fixtures/severity/` for example-domain identifiers,
   not just the generated record -- closing the residual fixture-leak gap. The
   existing `is_test_path` exemption means the live rules will not scan them, so
   the lock test itself is the natural place to assert fixture genericity.
2. **(MEDIUM, from analysis M2)** When grain is ruled (T000 -> T004), if option
   (b) (per-branch) is chosen, pin the sub-key to a STABLE branch tag rather than
   the finding's full message text, so message wording edits do not flake the
   lock.
3. **(LOW)** Operator: fill the "(date pending)" placeholders and note the cosmetic
   doubled-number branch name (`044-045-...`) vs spec dir (`044-...`) at
   ratification.

## Verdict

**PASS-WITH-NOTES.**

The draft is internally consistent (analyze clean, full FR/SC coverage), honors
the Principle-V carve-out via a hard human gate (T000) rather than guessing, and
introduces no deferred-capability assumption, no fabricated confidence, and no
over-scope. The notes are refinements -- the most material is the residual
fixture-leak gap (axis 3, fix #1), which is LOW because the committed generic
artifact is already protected and fixtures are synthetic by mandate. No CRITICAL
or HIGH finding. Ready to hand off to the human ratify gate, where the grain and
L3-coverage rulings (T000) must be made before implementation.
