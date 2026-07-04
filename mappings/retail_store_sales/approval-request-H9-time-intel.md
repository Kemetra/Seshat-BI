# Approval Request -- `H9-time-intel`

- **question_id:** `H9-time-intel`
- **stage:** `semantic_model_ready`
- **subject:** the planned time-intelligence + same-store metric contracts (`ytd-net-sales`, `net-sales-growth`, `same-store-sales-growth`) for the retail KPI layer
- **owner_required:** `metric-owner`  *(these are metric-contract policy decisions; see Authority class below)*
- **status:** `answered`  *(ruled 2026-07-05 by Ahmed Shaaban (metric_owner): D1=C, D2=A, D3=C -- see `approval-decision-H9-time-intel.md`. A request is `open` until a named human answers it via approval-decision.md; it never answers itself.)*

> **Why this is packaged, not decided.** The three planned contracts each depend on a
> business-definition ambiguity the kit is forbidden to resolve on its own (Principle V;
> `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` A3 + A11, both carry a
> **Needs business definition** flag). Until the named metric owner rules, the contracts
> stay `[planned]` and every downstream H-family guard (H6/H10) has an empty set to check.
> This package poses the three sub-decisions; it records none of them.

## Decision needed (one sentence)

> Set the three metric-contract policies the planned time-intelligence contracts require:
> (D1) the same-store / comparable-store eligibility rule, (D2) the primary date each
> time contract compares on, and (D3) the year-over-year comparison-baseline convention.

---

## Sub-decision D1 -- same-store eligibility rule  *(ambiguity A11)*

### Evidence (measured facts + committed source paths)

- The ambiguity is documented and flagged unresolved: "Same-store / comparable store needs
  an explicit rule: minimum months open, handling of relocations and major refurbishments,
  treatment of closures. Without an agreed rule, same-store growth is not reproducible and
  stays **Needs business definition**."  (source: `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` A11)
- The route is planned, not seeded: "Same-store numbers don't reconcile -> metric-ambiguity-checklist (same-store **[planned]**)."  (source: `skills/retail-kpi-knowledge/INDEX.md:41`)
- Branch identity is keyed, not named (a same-store rule must key on the branch key): A9 in the same ambiguities file.  (source: `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` A9)

### Options

- **A.** **Minimum-months-open rule.** A store is "same-store" for a period if it has been open for the full comparison window plus a stated minimum (e.g. 12 months) before the period start; relocations/refurbishments/closures each get an explicit inclusion or exclusion sub-rule stated in the contract.
- **B.** **Continuously-open-both-periods rule.** A store is comparable only if it traded in BOTH the current and the prior comparison period (no minimum-months threshold); relocations and refurbishments do not break comparability, only a closure gap does.
- **C.** **Defer same-store entirely.** Author `ytd-net-sales` and `net-sales-growth` now (they do not need A11) and keep `same-store-sales-growth` flagged **Needs business definition** until a later ruling.

### Impact (per option)

- **A ->** unblocks a fully-seeded `same-store-sales-growth.yaml` with a reproducible eligibility predicate; commits the layer to a months-open threshold + explicit relocation/refurb/closure treatment (most rigorous, most fields to define).
- **B ->** unblocks `same-store-sales-growth.yaml` with a simpler both-periods-traded predicate; less to define, but a store reopening after a gap is handled coarsely.
- **C ->** unblocks the two non-same-store contracts immediately; `same-store-sales-growth` stays `[planned]` and its H-family guards stay inert until A11 is answered later.

---

## Sub-decision D2 -- primary date for the time contracts  *(ambiguity A3)*

### Evidence (measured facts + committed source paths)

- The ambiguity is documented and flagged: "Which date drives the time axis? Sale date, posting date, and return date can all differ. A KPI compared on sale date will not reconcile to one compared on posting date. Each contract names its primary date and flags alternatives."  (source: `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` A3)
- The canonical worked-example table has ONE date semantic confirmed (one row = one single-item transaction; `total_spent` is the line total), and no separate posting/return date column.  (source: `mappings/retail_store_sales/unresolved-questions.md` Q3 Resolution; returns are a separate figure per the Q3/returns note)

### Options

- **A.** **Sale date (transaction date).** Every time contract compares on the transaction/sale date; posting and return dates are flagged as alternatives not used.
- **B.** **Posting / accounting date.** Time contracts compare on the accounting posting date (aligns KPIs to finance's ledger period).
- **C.** **Per-contract, owner-named.** Each contract names its own primary date explicitly; no single layer-wide default is set.

### Impact (per option)

- **A ->** all three contracts (and H6's date-field assertion) key on one sale-date field; simplest reconciliation, aligns with the operational sales view.
- **B ->** contracts key on posting date; reconciles to finance ledgers but diverges from operational sale timing.
- **C ->** maximum flexibility; H6 asserts *presence* of a named primary-date field per contract but the layer carries no default, so cross-contract comparisons need care.

---

## Sub-decision D3 -- comparison-baseline convention  *(the YoY / prior-period basis)*

### Evidence (measured facts + committed source paths)

- H6 (the Comparison-Baseline Declaration Guard) requires each time-family contract to declare a baseline; the guard is `[planned]` pending this convention.  (source: `docs/roadmap/idea-backlog.md` H6 First step)
- The gross-vs-net basis is already settled upstream as an ambiguity to state per contract, but the *baseline period* is not.  (source: `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` A4)

### Options

- **A.** **Year-over-year (same period, prior year)** as the default growth baseline for `net-sales-growth`; `ytd-net-sales` compares YTD-this-year vs YTD-prior-year.
- **B.** **Prior-period (immediately preceding comparable period, e.g. prior month/quarter)** as the default baseline.
- **C.** **Both declared, YoY primary.** Contracts carry YoY as the primary baseline and prior-period as a named secondary comparison.

### Impact (per option)

- **A ->** `net-sales-growth.yaml` seeds with a YoY baseline field; H6 asserts its presence; seasonality handled by construction.
- **B ->** growth baseline is prior-period; more responsive to recent trend, less seasonality-robust.
- **C ->** both baselines defined; richest, but each contract must state which visuals use which.

---

## recommended_default

> **Omitted.** The source (`kpi-ambiguities.md`) carries **no** default for A3 or A11 -- both
> are explicitly **Needs business definition**, and D3 has no ADR/RC default either. Per the
> transcribe-never-author boundary, the console does not invent a default; the named metric
> owner sets each policy. (There is nothing to mark "NOT auto-accepted" because no default exists.)

## artifacts_to_update_after_decision

Once the named metric owner answers (via `approval-decision.md`), the decision is written
through to:

- `mappings/retail_store_sales/unresolved-questions.md` -- add the matching `H9-time-intel` row's `Resolution` cell + `Status` `answered` (or a KPI-layer questions artifact if the owner prefers the decision recorded off the mapping-stage table, which is already `CLEARED`).
- `mappings/retail_store_sales/readiness-status.yaml` -- an `approvals[]` entry for `semantic_model_ready` (owner + `at`).
- **Downstream authored AFTER the decision (NOT by this console -- these are F009 contract-authoring, a separate step):**
  - D2 + D3 answered -> author `skills/retail-kpi-knowledge/contracts/ytd-net-sales.md` and `net-sales-growth.md`; flip their INDEX/domain rows `[planned]` -> `[seeded]`. Unblocks **H6** (date + baseline presence rule) and **H10** (additivity/grain over the new contracts).
  - D1 answered (option A or B) -> author `same-store-sales-growth.md`; flip its row `[planned]` -> `[seeded]`. If D1 = option C, that contract stays `[planned]` with the **Needs business definition** flag.

## Authority class (who may decide)

- **metric-owner** -- these are metric-contract policy decisions (F009 additive class). A11/A3
  are business-meaning calls about how a metric is defined, owned by the named metric owner.
  A decision recorded under any other class (e.g. `analyst` alone) is refused by the console
  unless the owner formally holds the metric-owner authority for this layer.

> **Serialization note.** When written back, `readiness-status.yaml` `approvals[].owner` gets
> the full named-decider shape `"Person Name (metric_owner)"`; a role-only owner is rejected (RS1 / audit C4).

## Duplicate guard

`H9-time-intel` resolves to exactly ONE request (this file). If packaged again, the console
surfaces the duplicate and declines a second decidable copy -- this request is authoritative.

## See also

- The ambiguities this packages: `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` (A3, A11).
- The recorded answer this is decided into: `templates/approval-decision.md`.
- The console verb + boundary: `.claude/skills/approval-console/SKILL.md`, `docs/tools/approval-console.md`.
- The planned routes it unblocks: `skills/retail-kpi-knowledge/INDEX.md` (same-store [planned]).
- The blocked-idea triage this serves: `docs/roadmap/idea-backlog.md` (H6/H9/H10).
