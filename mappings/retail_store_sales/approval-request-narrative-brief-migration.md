# Approval Request -- `narrative-brief-migration`

- **question_id:** `narrative-brief-migration`
- **table:** `retail_store_sales`
- **stage:** `dashboard_ready`  *(the signed Stage-6 design artifacts; issue #514)*
- **subject:** the `seshat.narrative-brief/v1` brief and the
  `seshat.binding-map/v1` migration of the signed `visual-contract-binding-map.md`
- **owner_required:** `report-owner`  *(the named human who signed the binding map
  2026-06-25; see Authority class below)*
- **status:** `open`  *(a request is `open` until a named human answers it via
  `approval-decision-narrative-brief-migration.md`; it never answers itself)*
- **prepared:** 2026-07-26 (agent-assembled evidence package)
- **governing ruling:** R5, `docs/superpowers/specs/2026-07-26-nine-issue-rulings.md`

> **What is packaged, and what is not.** The AGENT authors the brief -- deriving
> ranked decision-questions, framings, guardrail bases, story order, and callouts
> from the two committed inputs is exactly what `bi-analyst-knowledge` is for, and
> ending on prose instead of a committed brief is the anti-pattern. What the agent
> may **not** do is APPROVE it (`No self-granted pass`), and it may **not**
> re-sign the already-SIGNED binding map -- the gate R5 named.
>
> So this request does **not** ask the owner to perform the derivation. It asks
> the owner to **approve or revise a drafted brief**, and to rule the one call no
> draft can settle (D5, re-signing). The proposals below are the agent's grounded
> draft positions, offered as something concrete to react to.

## Decision needed (one sentence)

> Review the drafted `retail_store_sales` narrative brief and either approve it or
> return revisions -- D1-D4 are the agent's draft positions on the questions,
> framings, story order, and visual bindings; D5 is the one ruling the owner alone
> can make (whether the 2026-06-25 sign-off carries forward or a fresh design
> review is required).

## How to use this package

1. **The agent drafts** `mappings/retail_store_sales/narrative-brief.md` from
   `templates/narrative-brief.md`, grounded in the 5 approved contracts and the
   committed source-profile, and runs
   `seshat narrative-check --table retail_store_sales --report .` until it passes.
   A clean check is **evidence for** this review, never an approval.
2. **The owner reviews that draft** against D1-D4 below -- accept, or return
   revisions. The draft is a proposal, not a fait accompli: the checker asserts
   the brief obeys its schema, never that a question is the RIGHT question.
3. **The owner rules D5** and records everything in the paired
   `approval-decision-narrative-brief-migration.md`.

D1-D4 are listed as explicit decisions because each involves a judgment the
checker cannot make. They are the review agenda for the draft, not homework
assigned to the owner.

## Authority class

`report-owner`. The binding map's own sign-off block
(`design/visual-contract-binding-map.md:58-68`) names the reviewer as the BI
report owner, and `report-intent.yaml` names `owner: "Ahmed Shaaban
(report_owner)"`. R5 ruled that the delegated-ruling mandate covers design
rulings but **not** re-signing signed artifacts, so this specific gate needs the
named signer, not a delegate.

---

## Why this is a request and not a patch

R5 ruled the five mechanical `#474` criteria in scope and left this one out,
stating the boundary plainly:

> Migrating a signed artifact under a delegated ruling would override a gate
> that names a *different* review (named-owner review of the signed map). The
> delegation covers design rulings, not re-signing signed artifacts.

What that boundary does and does not cover:

1. **The binding map is already signed -- so its migration is NOT the agent's.**
   `design/visual-contract-binding-map.md:58-68` records reviewer `data_owner`,
   decision `approved`, at `2026-06-25`, and `readiness-status.yaml` carries the
   matching `dashboard_ready: pass`. Rewriting it into the v1 front-section
   format re-issues a signed artifact, which is the gate R5 named.
2. **The brief itself IS the agent's to draft** -- deriving the questions,
   framings, guardrail bases, story order, and callouts from the two committed
   inputs is the `bi-analyst-knowledge` route's job. What the agent may not do is
   APPROVE that draft, or record the ruling on the owner's behalf
   (`never_self_grant_approval`). D1-D4 below are therefore the review agenda for
   a draft, not work handed to the owner.

**Do not "fix"** `tests/unit/test_narrative_check.py::test_real_worked_example_map_still_needs_phase_b_migration`.
It pins today's fail-closed state on purpose; its flipping is the signal that
this migration really happened.

## Verified current state (run, not assumed)

```
$ seshat narrative-check --table retail_store_sales --report .
status: blocked
[finding] missing_brief: no narrative-brief.md at mappings\retail_store_sales\narrative-brief.md
          -- nothing to check (fail closed)
```

| Fact | Evidence |
|---|---|
| No brief exists | `mappings/retail_store_sales/narrative-brief.md` absent |
| Map is still F011 two-way Markdown | `design/visual-contract-binding-map.md` -- pipe table, no fenced `yaml` front section |
| 5 contracts approved `pass` | `metrics/*.yaml`, owner-approved 2026-06-25 |
| Stage is otherwise complete | `seshat next --table retail_store_sales` -> `terminal_pass` (all seven gates `pass`) |
| A generic template now exists | `templates/narrative-brief.md` (added with this package; schema-verified `status: pass`) |

## Decision 1 -- the ranked decision-questions

**These six are UNAPPROVED PROPOSALS, not established owner input.**
`design/report-intent.yaml` declares them via `report-intent-interview` and names
`owner: "Ahmed Shaaban (report_owner)"`, but that same file records its own
readiness as **`blocked`**:

> `no report_intent_approval decision recorded yet for branch_performance_weekly
> -- awaiting named report_owner approval (Principle V; never self-granted)`

So the file naming an owner does **not** make its questions approved. Each one
below needs explicit **acceptance, modification, or rejection** — the migration
must not inherit decisions the named owner has never approved. They are listed
here as the starting proposal set so the owner has something concrete to react
to, not as settled input:

| Intent id | Owner's question text (verbatim) |
|---|---|
| q1 | How are we doing overall right now? (headline volume + basket value + discount share) |
| q2 | How do sales move over time -- trend / seasonality? |
| q3 | Which product categories drive sales and units? |
| q4 | How do sales split by channel (location: in-store vs online) and payment method? |
| q5 | What is the basket value (avg transaction value) and how does it vary by channel? |
| q6 | Who are the highest-activity customers (transaction count)? |

**What the owner reviews in the draft:**

- **1a.** **Accept, modify, or reject each of q1-q6.** They are proposals from a
  `blocked` intent, so none carries forward by default; silence is not acceptance.
- **1b.** **Rank them.** Index order IS the rank (owner priority x data
  strength) -- the intent file states no ranking, so this is genuinely new.
- **1c.** Each must be **re-phrased as a decision**, not a metric request. The
  derivation route requires "where do I push spend", not "show TotalSales by x".
  The intent text is currently phrased as questions.
- **1d.** One `callout` per question -- the so-what sentence it yields.

## Decision 2 -- framing + guardrail basis per question

Each question needs exactly one of the **eight** framing cards. Six of them are
**guardrail-bearing** (`trend-anomaly`, `period-variance`, `concentration`,
`segment-behavior`, `benchmark-threshold`, `signal-vs-noise`) and then a named
`guardrail.basis` is **mandatory** -- verified adversarially against the shipped
checker:

```
[finding] missing_guardrail_basis: question Q1 uses guardrail-bearing framing
          'trend-anomaly' but states no guardrail.basis -- a claim with no basis
          is a defect (the checker asserts presence, not wisdom)
```

The checker asserts a basis is *present*; **whether the basis is wise is exactly
this review.** `report-intent.yaml` offers `comparisons: ["vs prior period",
"trend over time (month)"]` as candidate bases, but assigns none to a question.

**What the owner reviews in the draft:** the framing card for each question, and for every
guardrail-bearing choice, the named `basis` (plus optional `window` /
`min_sample_floor`).

## Decision 3 -- the story order (four stages)

`story_order` needs all four keys; every question id appears in **exactly one**
stage; a question's stage there must equal its own `stage` field; and `overview`
**must be non-empty**.

**What the owner reviews in the draft:** the assignment of each question to
`overview` / `change` / `why_where` / `action`, and the order within each stage.

**Headline rule (FR-006):** every `stage: overview` question must set
`comparison` to a **named** value -- `"none"` is rejected. A bare-total headline
is a defect. q1 is the natural overview candidate and is currently phrased as a
bare "how are we doing overall", so it needs a comparison chosen.

## Decision 4 -- the three-way visual bindings

The signed map is two-way (`visual -> contract`). The v1 format adds a
**third leg**: `decision_questions` per visual. The existing map's
`business_question` column already references Q1-Q6 informally, so the mapping
below is a **proposal read off the signed artifact** -- it needs owner
confirmation, especially the multi-question rows.

| visual | type | bound contract (signed) | proposed `decision_questions` | note |
|---|---|---|---|---|
| v01 | card | TotalSales | [Q1] | `headline: true` candidate |
| v02 | card | TransactionCount | [Q1] | `headline: true` candidate |
| v03 | card | AvgTransactionValue | [Q1, Q5] | map says "Q1/Q5" -- **two questions** |
| v04 | card | DiscountedTransactionRate | [Q1] | carries the discount caveat |
| v05 | line | TotalSales | [Q2] | by `dim_date_rss[full_date]` (month) |
| v06 | bar | TotalSales | [Q3] | by `dim_product_rss[category]` |
| v07 | bar | TotalQuantity | [Q3] | by `dim_product_rss[category]` |
| v08 | bar/donut | TotalSales | [Q4] | by `dim_location_rss[location]` |
| v09 | column | AvgTransactionValue | [Q5] | by `dim_payment_method_rss[payment_method]` |
| v10 | table | TransactionCount | [Q6] | by `dim_customer_rss[customer_id]` (Top N) |

**What the owner reviews in the draft:**

- **4a.** Confirm or correct each `decision_questions` list. The checker's
  `orphan_visual` rule requires the bound contract to be one the answered
  question **actually cites** -- membership in both sets separately is not
  enough.
- **4b.** Which visuals are `headline: true`. Any headline visual must answer an
  **overview-stage** question or `bare_total_headline_visual` fires.
- **4c.** q4 covers *both* channel and payment method while v08 (location) and
  v09 (payment method) are separate visuals -- confirm whether q4 splits into
  two questions or both visuals answer the one.

## Decision 5 -- re-signing the migrated map

The migration preserves the signed two-way content and adds the front section.
**What the owner must rule:** whether the 2026-06-25 sign-off carries forward
with a migration note, or a **fresh** design review is required. The agent
cannot make this call -- it is the gate R5 named.

## Contract citations (mechanical -- stamped for the owner)

Every `contracts[].revision` must equal the contract's **current** blob sha or
the citation is stale. Computed 2026-07-26 via `git hash-object`:

```yaml
contracts:
  - id: TotalSales
    revision: f019492a4d10acbb6a57bf8cf3d7da850bd28c44
  - id: TotalQuantity
    revision: 221e385c504cabeb592b3c33951e9acc566cd23f
  - id: TransactionCount
    revision: 250309e6b75c86ae131e4ee99c8730e0cfffe35b
  - id: AvgTransactionValue
    revision: 506e449bc1cace4230ac83302a6772cfe00ce0ef
  - id: DiscountedTransactionRate
    revision: 7873eb89ad3a79185a78ebaea300ed19a6fbd23b
```

**Re-stamp these if any contract changes before the brief is committed.**

Dimensions available for `cites.dimensions` (from `report-intent.yaml`):
`dim_date_rss.full_date`, `dim_product_rss.category`, `dim_location_rss.location`,
`dim_payment_method_rss.payment_method`, `dim_customer_rss.customer_id`.
Note `cites.dimensions` is **not** ground-checked in v1 (the dotted-ref vs
bare-column mismatch is a recorded owner inconsistency, not a checker gap).

## Known caveat that any narrative must carry

`report-intent.yaml` and the publish pack both record: **33.39% of transactions
have unknown discount status** (floor 33.55% if treated as not-discounted;
handoff re-approved 2026-07-05 on the corrected 50.37% known-status framing).
Any q1/v04 callout mentioning discount share must state this, or the brief
narrates a number the data does not support.

## Candidate `gaps[]` (agent-identified, owner to confirm)

`gaps` must be present (may be `[]`). `report-intent.yaml` declares
`exclusions_and_non_goals`, which are gap candidates:

| Owner decision | Missing source fact | Unlocking feed |
|---|---|---|
| Which categories are actually profitable? | no cost/margin column in this source | a cost or purchase-price feed |
| What is being returned, and why? | no returns rows in this source (RC8 N/A) | a returns/credit-note feed |

A gap must **not** also appear as a `questions[]` entry -- you cannot frame what
you cannot answer.

## Definition of done (from issue #514, unchanged)

- [ ] `narrative-brief.md` with a `seshat.narrative-brief/v1` front section
      (owner-authored questions, cites, story order) plus the human-first body.
- [ ] Binding map migrated to `seshat.binding-map/v1`, preserving the signed
      two-way content.
- [ ] `seshat narrative-check --table retail_store_sales --report .` passes, and
      `--binding-map` passes the three-way linkage check.
- [ ] `test_real_worked_example_map_still_needs_phase_b_migration` updated
      **deliberately** to assert the new passing state.
- [ ] Named-owner review recorded per the usual approval seam.

## How this request gets answered

**Not in this file.** Per the convention the two sibling packages in this
directory already follow (`approval-request-H9-time-intel.md` pairs with
`approval-decision-H9-time-intel.md`; same for `YTD-year-start`), the named human
records the ruling in a **separate** decision file:

```
mappings/retail_store_sales/approval-decision-narrative-brief-migration.md
```

That file states `question_id` (matching this request), `selected_option` for
each of D1-D5, `owner` (the named human plus authority class), `date`,
`rationale`, and an `artifacts_updated` section listing the committed artifacts
the decision was written through to.

When it exists and names this `question_id`, this request's `status:` flips from
`open` to `answered` with a pointer to it.

**The agent that assembled this package is structurally forbidden from creating
that decision file, or from flipping the `status:` field above.** Only the named
report owner writes the ruling. A "do the recommended actions" instruction does
**not** clear this seam -- R5 named it, and it is the one item in issue #514 that
no delegated mandate covers.
