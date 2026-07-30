# Quickstart: walking the Finance GL example

**Feature**: 137-finance-gl-genericity-proof | **Date**: 2026-07-30

For the author (agent or analyst) who will execute this feature after the owner ratifies
the planning package. Read `spec.md` first; this file is the order of operations.

## The one rule that makes this feature meaningful

**Do not fix the kit to make finance fit.** When something in the kit assumes retail,
write a ledger row and keep walking. The ledger is the deliverable; a smoothed-over walk
with no ledger rows proves nothing, and a walk that stops to redesign the kit produces no
evidence at all.

If a kit change looks genuinely unavoidable, that is an owner decision (raise it), not an
edit to make quietly.

## Order of operations

1. **Generate the clean fixtures.** Run the generator into a git-ignored directory. Then
   run it a second time into a different directory and compare bytes. If they differ, stop
   and fix determinism before authoring anything downstream -- every later artifact cites
   these files.

2. **Profile each source separately.** `finance_gl_actuals` and `finance_gl_budget` are two
   tables with two grains. Resist any urge to profile them as one subject.

3. **Fill the mapping artifacts per table**, using the existing templates only. Each table
   gets its own directory, its own declared grain and PK, its own assumptions, and its own
   unresolved questions. Deviations from the ratified cleaning defaults are recorded with
   the data fact that triggered them.

4. **Stop at the gate.** The mapping gate needs a NAMED human approval per table (OD-4).
   Do not write `silver.*` SQL before it clears, and never record the approval yourself.

5. **Author silver, then gold.** Two silver tables, then one gold star with two facts and
   three conformed dimensions. Actuals may roll UP to the budget grain; budget never
   spreads DOWN (OD-3).

6. **Author the seven metric contracts.** Use the existing template's field set exactly.
   Variance % is computed after separate aggregation. Missing budget is a flag, not a zero.
   Leave OD-1 and OD-2 open and blocking -- a contract that quietly picks a sign convention
   or a baseline is a governance failure, not progress.

7. **Run the defect variants.** Record, for each of D1-D13, the declared expected outcome
   and the OBSERVED one. Report mismatches, including over-refusals, exactly as observed.
   D12 must pass as `proceed`; if the gate refuses it, that is the over-refusal finding and
   it goes in the report rather than being tuned away.

8. **Register the six judgment scenarios** in the existing benchmark scenario format. No new
   format, no new runner.

9. **Author the dashboard blueprint and binding map.** All eight visuals are `human_only`
   for creation and binding (see `plan.md`). The human authors the page in Power BI Desktop
   and commits the PBIR; then run binding validation and the theme/formatting/geometry
   steps that the adapter does support.

10. **Write the ledger and the worked-example narrative.** Then register the example in the
    existing declaration surfaces (index row, doc-anchored claims, capability manifest)
    without claiming any capability that does not exist.

11. **Prove the negative.** Show the diff contains no rule change, no CLI verb change, and
    no skill addition or rename. That diff is an acceptance artifact.

## Definition of done (repo-only tier)

- Fixtures regenerate byte-identically.
- Both tables have complete mapping artifacts and a readiness record.
- Silver + gold SQL authored (not executed); live legs marked `[PENDING LIVE PROFILE]`.
- Seven contracts authored; OD-1/OD-2 visibly open and blocking where they apply.
- All 13 variants have declared + observed outcomes.
- One committed report page whose every visual traces to one approved contract.
- Ledger complete, categorical conclusion, no score anywhere.
- No self-granted approval anywhere in any artifact.

## What would make this feature a failure

Not "many leaks were found" -- that is a useful result. It fails if: the walk was smoothed
by silent kit edits; the ledger is empty because nothing was recorded rather than because
nothing was hit; a business judgment was defaulted instead of raised; or the outcome is
written up as "Seshat now supports finance".
