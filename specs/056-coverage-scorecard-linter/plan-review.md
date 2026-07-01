# Adversarial Plan-Review: Coverage Scorecard Linter (SL1)

**Feature**: `056-coverage-scorecard-linter` | **Date**: 2026-07-01
**Reviewer posture**: single default-adverse skeptic, read-only over spec.md,
plan.md, tasks.md, research.md, data-model.md, contracts/rule-contract.md,
quickstart.md, analysis.md. Reports fixes; edits nothing.

**Artifact completeness precheck**: spec.md, plan.md, tasks.md, analysis.md all
present (analysis is clean, 0 critical / 0 high). Not auto-BLOCKED.

## Axis 1 -- hidden-principle-violation

Checked whether any FR/task quietly crosses Principle V (adjudicate/grant) or another
principle.

- Contract-path check (C3/FR-004) verifies the cited `contracts/<file>.md` RESOLVES to
  a tracked file -- it does NOT verify the contract is Seeded or that fields are
  present. That is structural, not coverage adjudication. Boundary held.
- Blocker-presence (C2/FR-003) checks the col-4 cell is non-empty / non-`--`; it never
  judges whether the named blocker is the CORRECT one. Structural. Held.
- No status is written, no readiness stage granted, no coverage truth decided; the
  rule emits Findings only. FR-006 + SC-009 + contract C10 + task T012 enforce this,
  and the boundary CONFIRMATION is correctly pushed to a human (OPEN FOR HUMAN).

Verdict: no hidden violation.

## Axis 2 -- assumes-deferred-capability

The rule is a pure stdlib static text read over `RuleContext.tracked_files`. It
depends on no Power BI execution adapter (F016), no spec-only runtime (F031-F033), no
live DB. It reuses only the already-shipped `retail.core` / `retail.registry` API that
PP1 uses. No deferred capability assumed.

Verdict: clean.

## Axis 3 -- c086-leak

The status enum is the template's GENERIC five-value vocabulary; fixtures are
synthetic generic scorecards (T012 asserts no table/column/KPI name and no inlined
worked-example answers); the template file -- which contains the illustrative
`raw.sales` example -- is explicitly excluded from scanning (C6, Q2). No pharmacy /
C086 specific leaks into a generic artifact.

Verdict: clean.

## Axis 4 -- fabricated-confidence

No readiness/coverage score is produced anywhere; indeed the rule's no-percentage
invariant (FR-005) ENFORCES rule IX on the artifacts it scans. The working id `SL1`
and severity `ERROR` are consistently flagged as recommendations pending human
ratification. analyze is recorded as clean, not as a ratification. Status front-matter
remains Draft.

Verdict: clean.

## Axis 5 -- over-scope

Every task maps to the idea-backlog first-step directive. No scorecard-authoring tool,
no readiness-stage mutation, no new severity tier, no new dependency, no executor. YAGNI
respected (seam, not implementation).

Verdict: clean.

## Notes (non-blocking)

- **N1 (dormant-until-populated)**: NO filled scorecard instance exists on main today,
  so `SL1` ships providing ZERO live protection until a first
  `mappings/<table>/**/*coverage-scorecard.md` instance is committed (silent pass by
  absence, C7). This is inherent to the idea (the grounder flagged it) and is the same
  posture PP1/SC1/DF1 accepted; Q1 defines the expected location so the rule is not
  PERMANENTLY dormant. A reviewer / ratifier should be aware the gate is latent until
  the location is populated. Reversible-easy (a suffix/glob change) if the human picks
  a different committed location at ratify.
- **N2 (dash normalization is load-bearing)**: the template renders the status dash as
  an en-dash glyph while authored artifacts use ASCII `--`; the enum matcher MUST
  normalize dashes or a template-styled instance will false-positive on enum
  membership. This is recorded (research R2, data-model, tasks T002) but is a real
  implementation trap worth calling out to the implementer.
- **N3 (working id + severity un-ratified)**: `SL1` and `Severity.ERROR` are advisor
  recommendations; the human ratifier should confirm both (and the roadmap-stage
  placement, which is OPEN FOR HUMAN) before/at ratification.

## Verdict

**Verdict**: PASS-WITH-NOTES

**PASS-WITH-NOTES.** The artifact set is complete, internally consistent (analyze
clean), constitution-aligned, generic-only, never-execute-safe, and within scope.
Three non-blocking notes (dormant-until-populated, dash-normalization trap,
un-ratified id/severity) are surfaced for the implementer and human ratifier. No
CRITICAL or HIGH issue; nothing blocks ratification.
