# Approval Request -- `YTD-year-start`

- **question_id:** `YTD-year-start`
- **stage:** `semantic_model_ready`
- **subject:** the year-start boundary + partial-period normalization for the planned `ytd-net-sales` time-intelligence metric contract
- **owner_required:** `metric-owner`  *(a metric-contract policy decision; F009 additive class -- see Authority class below)*
- **status:** `open`  *(a request is `open` until a named human answers it via approval-decision.md; it never answers itself)*

> **Why this is packaged separately from H9.** `H9-time-intel` ruled three
> time-intelligence policies (D1 same-store / A11, D2 primary date / A3, D3 comparison
> baseline). None of those touch `ytd-net-sales`'s OWN remaining ambiguity: whether
> "year" is the fiscal or calendar year, and how a partial current period is normalized
> when comparing YTD across years. The `ytd` contract flags this as owner-pending and
> un-coded (`skills/retail-kpi-knowledge/contracts/ytd.md` "Open ambiguity"). The H9
> request's to-do line said "D2+D3 answered -> author ytd", but that overlooked this
> boundary decision; the contract is ground truth. Until the named metric owner rules
> this, `ytd-net-sales` stays `[planned]` -- its gap is now narrowed to JUST the
> year-start boundary. This package poses the decision; it records none of it.

## Decision needed (one sentence)

> Set the `ytd-net-sales` year boundary: (E1) does "year" mean the fiscal year or the
> calendar year, and (E2) how is a partial current period normalized when a to-date YTD
> is compared to a full prior-year YTD?

---

## Sub-decision E1 -- fiscal vs calendar year-start  *(ytd own ambiguity, un-coded)*

### Evidence (measured facts + committed source paths)

- The ambiguity is documented and flagged unresolved: "**The year-start boundary and
  the partial-period handling are owner-pending** ... this contract does NOT decide
  them."  (source: `skills/retail-kpi-knowledge/contracts/ytd.md` Business definition + Open ambiguity)
- The contract's Owner names Finance as the boundary owner: "Finance (owns the
  fiscal-year boundary) + Sales Analytics."  (source: `ytd.md` Owner)
- The domain overview also flags it: "Fiscal vs calendar year -- use the business's
  fiscal calendar."  (source: `skills/retail-kpi-knowledge/domains/time-intelligence.md` Key ambiguities)
- This worked example carries NO declared fiscal calendar in its mapping artifacts
  (no fiscal-year attribute in `source-map.yaml` / the gold `dim_date_rss`), so a
  calendar-year default would be the only one implementable today without new fields.  (source: `mappings/retail_store_sales/readiness-status.yaml` gold_ready evidence -- dim_date_rss is a marked date table with no fiscal attribute cited)

### Options

- **A.** **Calendar year.** Year-start = 1 January; no fiscal calendar. Simplest;
  implementable today with the existing marked date table.
- **B.** **Fiscal year.** Year-start = the organization's declared fiscal-year start;
  requires a fiscal-year attribute on the date dimension (not present in this worked
  example today -- would need sourcing).
- **C.** **Per-tenant, owner-declared.** The contract stays generic: it REQUIRES a
  declared year-start attribute and names neither default; each tenant declares fiscal
  or calendar. (Keeps the generic KPI seed tenant-neutral.)

### Impact (per option)

- **A ->** `ytd-net-sales` seeds with a calendar-year boundary; H6/H10 guards get a
  live target immediately. Diverges from finance if the org runs a fiscal year.
- **B ->** aligns YTD to finance's fiscal periods; blocked here until a fiscal-year
  attribute is sourced onto the date dimension.
- **C ->** seeds a tenant-neutral contract that asserts "a declared year-start is
  required" without choosing one; each worked example/tenant supplies it. Most generic;
  the retail_store_sales instance would still need its own A-or-B sub-ruling to go live.

---

## Sub-decision E2 -- partial-period normalization  *(ytd own ambiguity, un-coded)*

### Evidence (measured facts + committed source paths)

- Flagged as a common mistake in the contract: "Comparing a partial current YTD to a
  full prior-year YTD without normalization."  (source: `ytd.md` Common mistakes)
- And in the domain overview: "Partial vs full period comparisons must be normalised."  (source: `domains/time-intelligence.md` Key ambiguities)

### Options

- **A.** **To-date vs to-date (like-for-like).** Compare the current partial YTD only
  against the prior year's SAME to-date point (e.g. Jan 1 - Jul 5 both years). No
  full-year comparison until the year closes.
- **B.** **Full-year prior baseline, flagged.** Allow comparing partial current YTD to
  the full prior-year YTD, but the visual MUST carry an explicit "partial period" flag.
- **C.** **Both, to-date primary.** To-date-vs-to-date is the default; full-year prior
  is an explicitly-labelled secondary comparison. (Parallels H9 D3=C's both-baselines shape.)

### Impact (per option)

- **A ->** cleanest, no distortion; cannot answer "are we ahead of last year's total?"
  mid-year.
- **B ->** answers the full-year question but risks the exact distortion the contract
  warns about unless the flag is honored.
- **C ->** richest; each visual states which comparison it uses (consistent with the
  H9 D3=C both-baselines convention already ruled for growth).

---

## recommended_default

> **No auto-acceptable default for either sub-decision.** The formal
> `recommended_default` field is empty -- the source carries no binding default this
> console could auto-accept, and Finance owns the fiscal-year call. Two source notes are
> reproduced for the owner's AWARENESS (not endorsed as defaults):
> - **E1:** `ytd.md` (Open ambiguity, line 51-52) notes an advisory lean -- *"the
>   organization's fiscal year if one is declared, else calendar."* That is a
>   consideration for the owner, not a ruling; the agent does not choose it.
> - **E2:** `ytd.md` carries **no** recommendation for partial-period handling.
>
> Per the transcribe-never-author boundary, this console invents no default; the named
> metric owner (with Finance for the fiscal boundary) sets each policy.

## artifacts_to_update_after_decision

Once the named metric owner answers (via `approval-decision.md`), the decision is written
through to:

- `mappings/retail_store_sales/unresolved-questions.md` -- a pointer note recording
  `YTD-year-start` as `answered` (recorded off the CLEARED mapping-stage Q1-Q4 table, as
  with H9).
- `mappings/retail_store_sales/readiness-status.yaml` -- an `approvals[]` entry for
  `semantic_model_ready` (owner + `at`), framed as a policy amendment (not a re-pass).
- **Downstream authored AFTER the decision (NOT by this console -- a separate F009 step):**
  - E1 + E2 answered (and, if E1=B, a fiscal-year attribute sourced) -> author
    `skills/retail-kpi-knowledge/contracts/ytd-net-sales.md`; flip its INDEX/domain rows
    `[planned]` -> `[seeded]`. Unblocks the YTD portion of **H6** (date + baseline
    presence) and **H10** (additivity/grain).

## Authority class (who may decide)

- **metric-owner** -- a metric-contract policy decision (F009 additive class). The
  year-start boundary is a business-meaning call; the contract names **Finance** as the
  fiscal-year owner alongside Sales Analytics. A decision recorded under any other class
  is refused by the console unless the owner formally holds the metric-owner authority
  for this layer.

> **Serialization note.** When written back, `readiness-status.yaml` `approvals[].owner`
> gets the full named-decider shape `"Person Name (metric_owner)"`; a role-only owner is
> rejected (RS1 / audit C4).

## Duplicate guard

`YTD-year-start` resolves to exactly ONE request (this file). It is DISTINCT from
`H9-time-intel` (which ruled D1/D2/D3 and did not touch the year boundary). If packaged
again, the console surfaces the duplicate and declines a second decidable copy -- this
request is authoritative for the ytd year-start decision.

## See also

- The contract this unblocks: `skills/retail-kpi-knowledge/contracts/ytd.md` (Open ambiguity -- year-start boundary + partial period).
- The prior decision that did NOT cover this: `mappings/retail_store_sales/approval-decision-H9-time-intel.md` (D1/D2/D3).
- The recorded answer this is decided into: `templates/approval-decision.md`.
- The console verb + boundary: `.claude/skills/approval-console/SKILL.md`, `docs/tools/approval-console.md`.
- The planned guards it unblocks: `docs/roadmap/idea-backlog.md` (H6/H10).
