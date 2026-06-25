# Handoff Review Checklist -- retail_store_sales

Filled instance of `templates/handoff/handoff-review-checklist.md`. The completeness
gate a human walks before publish. `[x]` = satisfied (evidence cited); a `[ ]` that
cannot be checked is a gap. ASCII, UTF-8 no BOM.

## 1. Prior-stage gate
- [x] Stages 1-6 each `pass` in `../readiness-status.yaml` (source/mapping/silver/gold/semantic_model/dashboard).

## 2. Required sections resolve to existing evidence
- [x] Metric contracts -> `../metrics/*.yaml` (5, all `pass`).
- [x] Readiness scorecard -> `../readiness-status.yaml`.
- [x] Reconciliation evidence -> `../reconciliation-report.md` (FILLED, PASS: penny-exact, 0 orphans). Totals tie.
- [x] Data dictionary present and matches the DEPLOYED `gold` schema (every deployed column once; no non-deployed column). Verified against information_schema 2026-06-25.

## 3. Caveats present and honest (all four)
- [x] PII exclusion stated (customer_id pseudonymous, kept; no raw PII).
- [x] Returns handling stated (NONE in this source; RC8 N/A; not from a measure sign).
- [x] Known gaps with MEASURED counts (discount 33.39% unknown -> rate is a floor; item 9.65% missing -> -1 member; measures ~4.8% NULL).
- [x] Out-of-scope list present (margin, returns, demographics, live publish).

## 4. Publish approval (named human sign-off; agent never self-grants)
- [ ] A `publish_ready` approval is recorded in `../readiness-status.yaml` `approvals[]`
      and in the pack. **PENDING RE-APPROVAL** -- a publish approval was recorded
      2026-06-25 and then RETRACTED: it was given against a pack framing
      DiscountedTransactionRate as 33.55%, since corrected to the approved known-status
      rate (50.37%). The owner must re-approve the corrected pack. `publish_ready` =
      `warning` until then.

## 5. Guardrails
- [x] No fabricated confidence/health NUMBER anywhere -- statuses + evidence + counts only.
- [x] No publishing / execution-adapter / Fabric action taken (F016 deferred, gated).
- [x] No worked-example (C086) specifics inlined -- this is the retail_store_sales instance.

## Verdict

All sections + caveats + reconciliation + data-dictionary-matches-schema are
satisfied EXCEPT the publish approval (item 4), which is pending RE-approval after the
DiscountedTransactionRate correction (the prior 2026-06-25 approval was retracted). So
the pack supports `publish_ready: warning` now, and `pass` the moment the owner
re-approves the corrected pack. Stages 1-6 remain `pass`. The live publish/refresh
ACTION is the deferred, gated F016 execution adapter.

## See also

- The pack: `bi-handoff-pack.md`. The stage authority: `../../../docs/readiness/publish-ready.md`.
