# Adversarial Plan-Review: 044-kpi-derivation-lineage

**Reviewer posture**: single default-adverse skeptic, READ-ONLY (records fixes; edits nothing).
**Date**: 2026-06-29 | **Artifacts reviewed**: spec.md, plan.md, tasks.md, analysis.md (+ live repo files).
**Axes**: hidden-principle-violation, assumes-deferred-capability, c086-leak, fabricated-confidence, over-scope

## Verdict: PASS-WITH-NOTES

The draft is complete (specify + clarify + plan + tasks + analyze all ran) and internally consistent.
The edge set and base/derived partition were re-verified against the LIVE contract files (not just the
spec), which is the check /speckit-analyze structurally cannot do. Three NOTES survive scrutiny; none
blocks. All three are honesty/precision points the ratifier should see before authoring.

## Live-repo verification performed (the 042 lesson)

I read the source contracts directly to confirm every FR-005 edge is genuinely in committed prose:

- KPI-MC-01 Gross Sales: "Gross Sales = sum of gross sales amount (unit list price x quantity ...)" -- direct field SUM, no KPI dependency. BASE confirmed.
- KPI-MC-03 Quantity Sold: "sum of quantity sold over qualifying sales lines" -- BASE confirmed.
- KPI-MC-04 Transactions Count: "count of distinct transaction id" -- BASE confirmed.
- KPI-MC-06 Discount Amount: "sum of (line discount + header discount)" -- BASE confirmed.
- KPI-MC-02 Net Sales: "Net Sales = Gross Sales - total discount (line + header), pre-tax" -> KPI-MC-01, KPI-MC-06. CONFIRMED.
- KPI-MC-05 ATV: "ATV = Net Sales / Transactions Count" + "net sales amount (from Net Sales contract)" -> KPI-MC-02, KPI-MC-04. CONFIRMED.
- KPI-MC-07 Discount Rate %: "Discount Rate % = Discount Amount / Gross Sales x 100" -> KPI-MC-06, KPI-MC-01. CONFIRMED.
- KPI-MC-08 Returns Rate %: "Returns Rate % = Return Value / Net Sales x 100" -> KPI-MC-02 only (Return Value is a field). CONFIRMED.
- KPI-MC-09 Gross Margin: "Gross Margin = Net Sales - COGS" -> KPI-MC-02 only (COGS is a field). CONFIRMED.
- KPI-MC-10 Gross Margin %: "Gross Margin % = Gross Margin / Net Sales x 100" -> KPI-MC-09, KPI-MC-02. CONFIRMED.

Every edge in FR-005 traces to committed prose. Zero invented edges. The Principle-V boundary holds.

## Findings

### PR1 -- Gross Sales prose references quantity, but the edge is to a FIELD, not to KPI-MC-03 (axis: fabricated-confidence / hidden-principle-violation, severity: low)

Gross Sales (KPI-MC-01) prose reads "unit list price x quantity". A naive author could draw an edge
KPI-MC-01 derives_from KPI-MC-03 (Quantity Sold). That would be WRONG and a Principle-V violation: the
prose references a quantity FIELD at line level, not the KPI-MC-03 aggregate metric. The spec already
classifies KPI-MC-01 as BASE (FR-004) and lists no such edge, which is correct -- but the tasks do not
explicitly warn against this specific trap.

FIX (record only): when authoring T009, the lineage doc MUST classify KPI-MC-01 as base with NO edge to
KPI-MC-03; a "unit list price x quantity" reference is a field computation, not a KPI derivation. Add this
to the T009/T015 provenance check so the author does not over-connect the graph. Mirrors the existing
"COGS / Return Value are fields, not nodes" rule.

### PR2 -- "Derived" vs "non-additive" are different axes; the doc must not conflate them (axis: hidden-principle-violation, severity: low)

KPI-MC-03 Quantity Sold and KPI-MC-04 Transactions Count are BASE (no derives-from edge) yet KPI-MC-04 is
non-additive-ish at distinct-count semantics; conversely some derived KPIs are non-additive ratios. A
reader could assume base == additive and derived == non-additive. They are orthogonal. The lineage doc is
about DERIVATION edges only; it must not restate or re-rule additivity (that lives in each contract's
"Additivity" section and in knowledge/kpi-additivity-and-grain.md).

FIX (record only): the lineage doc should state explicitly that it maps DERIVATION (which KPI is computed
from which), NOT additivity, and point additivity questions to the existing additivity knowledge file.
Prevents scope creep into a second relationship type and avoids a fabricated cross-claim.

### PR3 -- INDEX routing edit (FR-010 / T013) is genuinely optional; ensure the ratifier is not surprised by a no-op (axis: over-scope, severity: low)

Verified against the live INDEX.md: it does NOT enumerate references/ as a counted file list (routing table
lines ~20-26 + a prose summary line ~85 naming "template, field requirements, id conventions, source map,
research notes"). So FR-010 collapses to an optional routing-row + prose-mention with NO count bump. plan.md
states this correctly. The only risk is that a reader of the spec's SC-007 ("router lists the doc") expects a
mandatory edit. T013's built-in SKIP-and-record clause handles it.

FIX (record only): acceptable as-is. If the human ratifier prefers zero router churn, T013 may be skipped
entirely with the recorded justification "references/ is not enumerated in INDEX"; SC-007's second branch
("if none exists, record it") is then satisfied. No spec change needed.

## Axis-by-axis summary

- hidden-principle-violation: PR1 (over-connect to a field) and PR2 (additivity conflation) are pre-empted by the spec's "fields are not nodes" rule and by adding the two record-only notes. No actual violation in the artifacts.
- assumes-deferred-capability: NONE. No F016 / F031-F033 / live DB / generator is assumed; plan + tasks explicitly forbid an executor/generator (hard-rule #8, Principle VIII). Clean.
- c086-leak: NONE. All nodes are the 10 generic KPI-MC contracts; T016 enforces a token scan; the spec forbids inlining C086. Clean.
- fabricated-confidence: NONE. No score, no ranking, no computed value; the graph is categorical; T017/T020 enforce. PR1 is the only place a false RELATIONSHIP could be fabricated, and it is now flagged. Clean.
- over-scope: NONE beyond the (correctly de-scoped) other-8-contracts and the optional INDEX edit. Front-matter rejected; generator rejected; only 2 exemplar contracts + 1 template + 1 new doc touched. Clean.

## Completeness gate

- specify: DONE (spec.md). clarify: DONE (Clarifications block, Session 2026-06-29 + carried Principle-V item). plan: DONE. tasks: DONE (T001-T020). analyze: DONE (analysis.md, CLEAN). All present -> not auto-BLOCKED.

## Bottom line

PASS-WITH-NOTES. The spec is ratifiable. The three notes are record-only precision guards for the LATER
authoring run; none requires a spec edit. The single thing the human author must hold in mind is PR1: a
field reference (quantity, COGS, Return Value) is never a KPI-derivation edge -- transcribe relations
between the 10 KPI-MC nodes only.
