# Handoff Review Checklist -- `<schema>.<table>`

> **GENERIC template -- copy alongside the pack to
> `mappings/<table>/handoff/handoff-review-checklist.md`.**
> The completeness GATE a human walks before publish. Each line is either "satisfied
> (with evidence cited)" or "gap (recorded in the pack's caveats)" -- never silently
> skipped. This is a docs artifact, NOT runtime code and NOT a new validator. See
> `docs/readiness/publish-ready.md`.
>
> A `[ ]` that cannot be checked is a GAP -> the pack is incomplete and `publish_ready`
> stays `blocked` (or `warning` for a recorded non-fatal gap, which does NOT
> auto-promote to `pass`). ASCII only, UTF-8 no BOM.

---

## 1. Prior-stage gate

- [ ] Stages 1-6 are each `pass` in `mappings/<table>/readiness-status.yaml`. If any is
      not `pass`, STOP -- record the not-pass stage as a blocking reason; the pack is not
      complete (publish-ready.md: "any prior stage not pass").

## 2. Required sections resolve to existing evidence

- [ ] **Metric contracts** -- the pack's metric-contracts section points at approved
      `mappings/<table>/metrics/<MetricName>.yaml` (stage 5). A consumer-requested metric
      that is NOT in the contracts is NOT invented here -- it goes back through the
      metric-contract store (stage 5), not the handoff.
- [ ] **Readiness scorecard** -- points at the filled `readiness-scorecard.md`.
- [ ] **Reconciliation evidence** -- points at the FILLED `reconciliation-report.md`
      and the totals TIE. An unfilled or FAIL reconciliation FAILS this item; the pack
      MUST NOT edit totals/schema to make it tie -- escalate.
- [ ] **Data dictionary** -- present and matches the DEPLOYED `<schema>.<table>`: every
      deployed column appears exactly once; no non-deployed column is listed (a mismatch
      FAILS -- publish-ready.md).

## 3. Caveats are present and honest (ALL four -- a missing one FAILS)

- [ ] **PII exclusion** statement present (which columns were dropped for PII safety).
- [ ] **Returns / refunds handling** statement present (returns from the authoritative
      billing column, RC8 -- not the measure sign).
- [ ] **Known gaps** list present, sourced from `data-issues.md`, WITH measured counts
      (never softened to an adjective).
- [ ] **Out-of-scope** list present.

## 4. Publish approval (named human sign-off; agent never self-grants)

- [ ] A `publish_ready` approval is recorded in `readiness-status.yaml` `approvals[]`
      as `{stage: publish_ready, owner: <data_owner|governance>, at: <YYYY-MM-DD>}` and
      cited in the pack. If absent -> `publish_ready` is `blocked` ("no recorded publish
      approval"); the agent STOPS and requests the named owner, never writes it itself
      (Principle V).

## 5. Guardrails (must all hold)

- [ ] No fabricated confidence/health NUMBER anywhere -- statuses + evidence + blockers
      only (roadmap rule #9).
- [ ] No publishing / Power BI execution adapter (official Power BI MCP / connection;
      `pbi-cli` no longer preferred) / Fabric action taken -- that is the deferred,
      gated, execution-only F016 adapter (roadmap rule #6).
- [ ] No worked-example (C086) specifics inlined -- generic; the example is cited only
      (Principle VII).

## Verdict

- All items checked + approval recorded -> the pack supports `publish_ready: pass`
  (evidence = the pack files + the approval).
- Any unchecked required item -> `blocked` (or `warning` for a recorded non-fatal gap;
  a `warning` does NOT auto-promote to `pass`).

## See also

- The pack this gates: `bi-handoff-pack.md`.
- The stage authority + blocking reasons: `../../docs/readiness/publish-ready.md`.
- The model + no-fake-confidence rule: `../../docs/readiness/readiness-model.md`.
- The deferred publish adapter (out of scope): roadmap F016. A filled worked example is
  cited under `../../docs/worked-examples/`.
