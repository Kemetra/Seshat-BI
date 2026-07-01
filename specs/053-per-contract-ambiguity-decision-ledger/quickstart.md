# Quickstart: Per-Contract Ambiguity Decision Ledger

A DEFINE-layer authoring seam. There is no program to run; "quickstart" here means the
fill-and-read-back walkthrough plus the reviewer checks that stand in for tests.

## What this adds

A top-level `ambiguities` block on the metric-contract template. Each entry records one
recorded owner ruling (or an explicit undecided) for one catalogued A1..A11 ambiguity that
applies to the metric.

## Walkthrough: record a decided ruling (US1)

1. Copy `templates/metric-contract.yaml` to a filled contract location
   (`mappings/<table>/metrics/<MetricName>.yaml`).
2. For each catalogued ambiguity that APPLIES to the metric, add an `ambiguities` entry.
   Example (generic retail store sales, discounted-transaction-rate):
   ```yaml
   ambiguities:
     - id: "A7"        # cancelled / void / blank-status transactions
       decision_status: "pass"
       ruling: "Denominator counts known-status transactions only; cancelled/void/blank are excluded."
       evidence: ["ruled by <metric owner> on <YYYY-MM-DD>"]
   ```
3. Read it back: a reviewer sees the ambiguity id, the ruling intent, and the owner-and-date
   evidence -- with no numeric confidence anywhere.

## Walkthrough: an undecided material ambiguity blocks (US2)

1. The same metric is affected by a material ambiguity the owner has not yet ruled on.
2. Record it undecided and set the readiness block accordingly:
   ```yaml
   ambiguities:
     - id: "A4"        # gross vs net
       decision_status: "blocked"
       ruling: ""
       evidence: []
   readiness:
     status: "blocked"
     evidence: []
     blocking_reasons:
       - "ambiguity A4 (gross vs net) undecided -- owner ruling required"
   ```
3. Confirm there is NO author path to `readiness.status: pass` while a material ambiguity is
   undecided. The agent may recommend a ruling; only a recorded OWNER decision (owner + date)
   clears the block.

## Walkthrough: block propagates to a pack (US3)

1. Point an example pack (`metrics/packs/<pack>.yaml`) at the blocked contract by name.
2. Read the existing rollup rule in `docs/metrics/metric-contract-store.md` ("a pack is no
   more ready than its least-ready contract").
3. Confirm the pack is no more ready than the blocked member -- and that NO new rollup logic
   was added by this feature.

## Reviewer checks (the tests, applied by a human)

- [ ] Every `id` is within A1..A11 (A11 same-store is not dropped; no A1..A10 ceiling).
- [ ] No numeric confidence / score field anywhere.
- [ ] No DAX / SQL / visual spec / `powerbi/` path in any `ruling`.
- [ ] A decided status carries non-empty `evidence` (owner + date).
- [ ] An applicable material ambiguity is present (decided or explicitly undecided); silence
      on one is a defect.
- [ ] The `ambiguities` block is a top-level sibling of `readiness` (not nested); the
      readiness block's verbatim shape is unchanged.
- [ ] No domain-specific (e.g. pharmacy) ruling is inlined in the template or store guide;
      only the generic discounted-transaction-rate case is used, and any real ruling is cited
      via `docs/worked-examples/c086-pharmacy.md`.
- [ ] Files are ASCII + UTF-8 no BOM.
- [ ] No `retail check` rule was added; no `powerbi/` model was read.

## Out of scope (do not expect these)

- No automated enforcement of the block (the enforcing CHECK rule is a separate unbuilt
  idea). The blocker is a human-honored authoring convention.
- No Power BI model read, no execution adapter, no live data.
