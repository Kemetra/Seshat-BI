# Adversarial Plan-Review: Feature 062 Scaffold-Rule Generator + Doctor

**Stance**: single default-adverse skeptic. Read-only over spec.md, plan.md,
tasks.md, research.md, data-model.md, contracts/scaffold-cli.md, analysis.md.
I report fixes; I do not edit the artifacts. Prerequisite check: analysis.md
present, tasks.md present -- not auto-BLOCKED.

## Axis 1 -- Hidden principle violation

- **Principle V / auto-editing a source-of-truth set.** The single sharpest
  attack: the generator WRITES into `EXPECTED_RULE_IDS` (place #3), a
  source-of-truth set, while refusing to touch the golden records and glossary.
  Is inserting an id into that set a forbidden judgment the helper is
  self-granting? Verdict: NO. Membership in EXPECTED_RULE_IDS is a mechanical
  mirror of "this rule is registered"; it is not a pass/approve verdict, and the
  wiring TEST (not the helper) still decides whether the registered set equals the
  expected set. The helper cannot make a broken rule pass by editing the set --
  if the id is not actually registered, the guard/wiring test fails. The
  asymmetry (write the membership set; print the regen + prose) is defensible and
  is consistently justified (research R5, plan Design Decision 5). NOT a violation,
  but see Axis 4 -- it must not be OVER-claimed as risk-free.
- **Principle I / the helper becoming the authority.** Doctor emits only
  present/missing/unverifiable + has_drift; no "approved" verdict exists in the
  model. Gate exit code stays the truth. Clean. (analysis GAP-1 correctly flags
  that no test asserts the ABSENCE of an approval field -- a LOW hardening gap,
  not a violation.)
- **Principle VIII / never-execute.** stdlib-only, reads/writes text, prints
  commands rather than running them. Matches manifest.py / severity_posture.py.
  Clean.

Result: no hidden principle violation.

## Axis 2 -- Assumes a deferred capability

- No dependence on the Power BI execution adapter (F016) or any spec-only runtime
  (F031-F033). The plan's "Deferred / Not Built" section explicitly disclaims
  them. Doctor reads golden JSON + source text; author writes text. Nothing here
  needs a live DB, a model, or a network. Clean.
- The two golden regenerations are treated as EXISTING commands to PRINT, not as
  new capability to build -- confirmed against the live cli.py (manifest,
  severity-posture subcommands both present). Clean.

Result: no deferred-capability assumption.

## Axis 3 -- C086 / worked-example leak

- FR-003 + T008 mandate a generic stub and a test that FAILS if worked-example
  tokens appear. The known drift instance is cited generically ("a registered
  rule with no glossary row"), never by its specific rule id or any pharmacy/C086
  field. data-model + contract carry no domain specifics. Clean.
- One caution for implement time (not a plan defect): T013 asserts "the known
  drift instance is reported missing-from-glossary." Whoever implements T013 must
  key that test on a GENERICALLY-derived condition (registered id absent from the
  glossary rows) rather than hardcoding the specific drifted rule id, or the test
  will both leak an identity and become brittle when the human finally pastes the
  missing row. Recorded as a note; the spec/tasks already say "cited generically."

Result: no leak in the plan; one implement-time guard noted.

## Axis 4 -- Fabricated confidence

- No readiness score, no fabricated percentage, no "pass" claim anywhere. Spec
  states plainly it advances NO readiness stage. Good.
- The write/print asymmetry is presented as the load-bearing decision AND flagged
  for the reviewer (plan Design Decision 5 ends "called out for the reviewer") --
  honest, not over-sold. The analysis names it as the axis most likely to be
  challenged. This is the opposite of fabricated confidence. Good.
- Minor: SC-001 ("replacing the five-place hand ceremony") slightly overstates --
  the helper replaces THREE of five places with writes and converts the other two
  to printed steps; the human still runs 2 regens + 1 paste. This is accurately
  described everywhere else (write/print split), so SC-001's shorthand is not a
  contradiction, but an implementer reading only SC-001 could over-expect. LOW.

Result: no fabricated confidence; one LOW wording caution.

## Axis 5 -- Over-scope

- Scope is disciplined: one module, one subcommand, one test file, a guard test.
  Dynamic five-place discovery is explicitly deferred (YAGNI) with a guard test
  compensating for the hardcoded list -- the correct thin-seam choice.
- No auto-repair, no golden regen execution, no prose write, no new retail check
  rule, no DB/network. The "Out of Scope" list in the spec and the tasks' scope
  note agree. Clean.
- US3 (place-list guard) could be seen as gold-plating, but it directly answers
  the idea bank's flagged meta-risk (a hardcoded list that itself drifts), so it
  is in-scope and load-bearing, not scope creep.

Result: no over-scope.

## Findings summary

| ID   | Axis                    | Severity | Finding                                                                 | Fix |
|------|-------------------------|----------|------------------------------------------------------------------------|-----|
| PR-1 | hidden-principle (defense-in-depth) | LOW | No test asserts DoctorReport exposes no "approved/pass" field (mirrors analysis GAP-1). | Add the negative assertion in T014/T016 at implement time. |
| PR-2 | c086-leak (implement-time guard)    | LOW | T013 must key the drift test on a generic condition, not the specific drifted rule id, to avoid identity leak + brittleness. | Implement T013 as "some registered id absent from glossary rows," not a hardcoded id. |
| PR-3 | fabricated-confidence               | LOW | SC-001 shorthand ("replacing the five-place ceremony") could over-promise vs the write/print split. | Optional: soften SC-001 to "collapses the five-place ceremony to one command plus a printed checklist." |

All three are LOW and none blocks ratification. The write/print asymmetry -- the
one genuinely contestable design choice -- survives scrutiny: it is internally
consistent, principle-justified, and cannot be used to make a broken rule pass a
gate.

## Verdict

Verdict: PASS-WITH-NOTES

Rationale: all five axes clear with only three LOW, implement-time notes; the
cross-artifact set is consistent (analyze: 0 critical / 0 high / 1 low); the
constitution posture (Principles I/V/VII/VIII/IX) holds by construction. No
CRITICAL or HIGH finding. The spec remains **Status: Draft** for a human to
ratify.
