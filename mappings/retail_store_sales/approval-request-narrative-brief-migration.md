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
   APPROVE that draft, or DECIDE any of D1-D5 on the owner's behalf
   (`never_self_grant_approval`) -- though it may TRANSCRIBE a ruling the owner
   supplied (see "TRANSCRIPTION vs DECIDING" below). D1-D4 are therefore the
   review agenda for a draft, not work handed to the owner.

**Do not "fix"** `tests/unit/test_narrative_check.py::test_real_worked_example_map_still_needs_phase_b_migration`.
It pins today's fail-closed state on purpose; its flipping is the signal that
this migration really happened.

## One rule interaction this migration surfaced (FYI -- no action needed here)

Migrating the first REAL artifact exposed a notation collision between two shipped
features, which fixture-only testing could not have found:

**HR9** (`rename_impact_guard`) scans a binding map for `[Something]` and resolves
it against the committed TMDL measure set — a valuable guard, since a renamed
measure would otherwise silently orphan its references. But
`seshat.binding-map/v1`'s `decision_questions: [Q3]` is **YAML flow-list syntax**,
not a DAX measure reference, so HR9 read `Q3` as an orphaned measure and errored.

Worked around **in this example only**, by writing every `decision_questions` as a
YAML **block sequence** (`- Q1` on its own line) rather than a flow list. Both
forms are identical YAML and `narrative-check` accepts both; only the bracket
notation trips HR9. `seshat check` is clean again.

The general fix — teaching HR9 to skip a `seshat.binding-map/v1` front section, or
narrowing `_BARE_MEASURE_REF` so it cannot match a YAML list — is a **tooling
change proposed separately**, not folded into this owner-gated example. Worth
noting because any FUTURE binding map written with flow lists will hit the same
error, and the fix is one line of the author's YAML style until the rule is
adjusted.

## Verified current state (run, not assumed)

```
$ seshat narrative-check --table retail_store_sales --report .
status: blocked
[finding] missing_brief: no narrative-brief.md at mappings\retail_store_sales\narrative-brief.md
          -- nothing to check (fail closed)
```

| Fact | Evidence |
|---|---|
| A brief is **drafted** (agent-authored, unreviewed) | `mappings/retail_store_sales/narrative-brief.md` -- `narrative-check` -> `status: pass`, 6 questions / 5 contracts |
| Map is **migrated** to `seshat.binding-map/v1` (draft, unsigned) | `design/visual-contract-binding-map.md` -- v1 front section added, signed two-way content preserved verbatim |
| Both narrative-check modes pass | brief mode `pass`; `--binding-map` three-way mode `pass` (9 visuals / 6 questions / 5 contracts) |
| The gate is genuinely enforcing, not vacuous | adversarial mutations block correctly: a `Q99` cite -> `orphan_visual` + `unanswered_question`; a headline on an action-stage question -> `bare_total_headline_visual` |
| The pin test flipped, deliberately | `test_real_worked_example_map_passes_the_three_way_gate` in the NEW file **`tests/unit/test_narrative_worked_example.py`** replaces `test_real_worked_example_map_still_needs_phase_b_migration` (formerly in `test_narrative_check.py`), with STRONGER assertions (real counts >= 5, no findings, `grants_approval is False`) plus a companion brief test |
| v10 is **held out** | no customer-level question exists; the `customer_id` PII question is open in `source-profile.md` (see `approval-request-source-profile-writethrough.md`) |
| 5 contracts approved `pass` | `metrics/*.yaml`, owner-approved 2026-06-25 |
| No readiness stage moved | `seshat next --table retail_store_sales` -> `terminal_pass`, unchanged; nothing here grants an approval |

> **This request is not auto-discovered.** `seshat approvals` reads only
> `mappings/*/readiness-status.yaml`, and `seshat next` reads only the seven-stage
> spine -- neither scans `approval-request-*.md`. That is true of the two sibling
> packages in this directory as well: they are **reviewer-facing documents**, and a
> human (or an agent reading this directory) is what surfaces them. Wiring an
> `approval-request-*.md` scanner into `next` was attempted in this PR and
> reverted: trusting a markdown `status:` field as proof of a human ruling creates
> a second, weaker approval-trust path beside the authoritative
> `readiness-status.yaml` `approvals[]` one, which is a governance design decision
> in its own right. Tracked separately.
| A generic template now exists | `templates/narrative-brief.md` (added with this package; schema-verified `status: pass`) |

## Decision 1 -- the ranked decision-questions

**The initial questions must be DERIVED, not inherited from the list below.**
`derivation-route.md` names its inputs as "exactly two; nothing else" — the
approved metric contracts and the committed `source-profile.md`. `report-intent.yaml`
is a **third artifact**, so it may not seed the derivation: an agent that starts
from it produces a brief whose questions came from a forbidden input, and
`narrative-check` would not catch that (it validates measure cites, not question
provenance).

So the drafting order is:

1. **Derive** the ranked questions from the two permitted inputs only — the 5
   approved contracts (`metrics/*.yaml`) and `source-profile.md`.
2. **Then** compare the draft against the intent questions below, as *review
   context* for the owner: a gap between the two is a useful signal (either the
   derivation missed something the owner cares about, or the intent asked for
   something the data cannot answer — which is a `gaps[]` entry, not a question).

**And they are UNAPPROVED PROPOSALS regardless.** `report-intent.yaml` names
`owner: "Ahmed Shaaban (report_owner)"` but records its own readiness as
**`blocked`**:

> `no report_intent_approval decision recorded yet for branch_performance_weekly
> -- awaiting named report_owner approval (Principle V; never self-granted)`

So the file naming an owner does **not** make its questions approved. Each needs
explicit **acceptance, modification, or rejection** — the migration must not
inherit decisions the named owner has never approved. For **review context
only**, not as the derivation's starting set:

> ### ⚠ The numbers do NOT line up -- compare by CONTENT, not by id
>
> The drafted brief's `Q1`-`Q6` are the agent's own derivation and **do not
> correspond** to this intent's `q1`-`q6`. The collision is real and easy to
> misread:
>
> | | intent `q6` | brief `Q6` |
> |---|---|---|
> | is about | **customers** (highest-activity) | **discounting** (is the posture working) |
>
> And the intent's customer question has **no** brief equivalent at all — it is
> `gaps[]` entry 3, because the `customer_id` PII question is still open in
> `source-profile.md` (see the D2 dimension note and
> `approval-request-source-profile-writethrough.md`).
>
> So when ruling D1, read each drafted question's `decision:` text against the
> intent text below. **Matching on the number alone will pair the wrong two.**

| Intent id | Owner's question text (verbatim) |
|---|---|
| q1 | How are we doing overall right now? (headline volume + basket value + discount share) |
| q2 | How do sales move over time -- trend / seasonality? |
| q3 | Which product categories drive sales and units? |
| q4 | How do sales split by channel (location: in-store vs online) and payment method? |
| q5 | What is the basket value (avg transaction value) and how does it vary by channel? |
| q6 | Who are the highest-activity customers (transaction count)? |

**What the owner reviews in the draft:**

A **drafted brief now exists** at `mappings/retail_store_sales/narrative-brief.md`
(`narrative-check` -> `status: pass`, 6 questions / 5 contracts). It was derived
from the two permitted inputs only; the intent questions above were **not** its
source.

### The content pairing (what to actually compare)

| Intent (context) | Drafted brief | Same decision? |
|---|---|---|
| q1 headline volume + basket + discount share | **Q1** overall trading, YoY | yes -- but the drafted Q1 drops discount share into Q6, where the caveat can be stated properly |
| q2 trend / seasonality | **Q2** is the swing real (banded) | yes -- the draft adds the band so a spike is not over-read |
| q3 categories drive sales and units | **Q3** which categories to push/protect/drop | yes |
| q4 channel **and** payment method | **Q4** channel (in-store vs online) | **split** -- the draft separates channel from payment method |
| q5 basket value, varies by channel | **Q5** payment-method basket behaviour | **partly** -- the draft frames it as payment mix; channel basket is read in Q4 |
| q6 highest-activity customers | *(none)* -> `gaps[]` 3 | **NO** -- blocked on the open PII question |
| *(none)* | **Q6** is discounting working | **new** -- the draft promotes the discount caveat to its own action question |

So D1 is a review of concrete text, not a blank-page exercise:

- **1a.** **Accept, modify, or reject each drafted question Q1-Q6.** The draft's
  questions are the agent's derivation, not the intent list -- compare the two and
  say where the derivation missed something you care about.
- **1b.** **Confirm or re-order the rank.** Index order IS the rank. The draft
  ranks by owner-priority x data-strength as the route requires; the intent file
  states no ranking, so this remains genuinely yours.
- **1c.** **Confirm each is phrased as a DECISION**, not a metric request (the
  route requires "where do I push spend", not "show TotalSales by x"). The draft
  attempts this; judge whether each lands.
- **1d.** **Confirm each `callout`** -- the so-what sentence the question yields.

> **D1 carries a required write-through.** Ruling D1 settles the six
> `report-intent.yaml` questions, which makes it **also** a
> `report_intent_approval`. Recording only the narrative-brief decision file would
> leave `dashboard_coordinator._check_intent_approved` blocking. See
> **"Required write-throughs -- D1 is ALSO a `report_intent_approval`"** below for
> both targets; both must appear in the decision file's `artifacts_updated`.

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
this review.** The basis must be grounded in the two permitted inputs -- and
`source-profile.md` is what makes a time-based basis defensible here: it measures
`transaction_date` as `0.00%` missing with 1,114 distinct values spanning
**2022-01-01 .. 2025-01-18**, and the source carries no separate posting or return
date -- so a period comparison has exactly one date to compare on, over three
full years. `report-intent.yaml` happens to list
`comparisons: ["vs prior period", "trend over time (month)"]` and assigns none to
a question -- **review context only**, not the derivation's source.

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
| v10 | table | TransactionCount | [Q6] | by `dim_customer_rss[customer_id]` (Top N) -- **see the `customer_id` PII note under D2's dimension material**: the profile still records that question as open |

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

### Dimension material -- ground it in the source-profile, not this list

The **profiled source columns** are the permitted grounding for a dimension cite,
and `source-profile.md` carries them with measured cardinality and missingness:

| Column | Distinct | Missing | Profile note |
|---|---|---|---|
| `category` | 8 | 0.00% | clean product category -> dim attribute / rollup |
| `item` | 201 | 9.65% | 1:1 with `category` (0 fan-out) |
| `payment_method` | 3 | 0.00% | Cash / Credit Card / Digital Wallet |
| `location` | 2 | 0.00% | In-store / Online |
| `customer_id` | 25 | 0.00% | `CUST_xx` pseudonymous surrogate -> dim candidate. **PII question OPEN in the profile** (see below) |

The v1 schema's `cites.dimensions` wants a **dotted semantic-model** reference
(`dim_product_rss.category`), which the two permitted inputs do not carry -- that
resolution needs the mapping/semantic model, a third artifact. This is the
**recorded v1 inconsistency**, not a checker gap: `cites.dimensions` is
deliberately **not** ground-checked in v1 for exactly this reason, and closing it
needs a schema revision (an owner decision).

So: derive *which* dimensions a question needs from the profiled columns above;
treat the dotted spelling as a mechanical translation, and do not let the
un-ground-checked field become a route for material the two inputs never
supported.

#### `customer_id` -- do NOT assume the PII question is settled

`source-profile.md` records the PII question as **open** and its own
`Source-ready status: warning` for that reason:

> "the `customer_id` PII question is open. Not `pass` until the analyst confirms
> the semantics and governance rules on the PII column."

The Q1 ruling that answers it (`2026-06-25 (data owner): KEEP customer_id as
dim_customer -- pseudonymous surrogate, no raw PII`) lives in
`unresolved-questions.md` and the readiness `approvals[]` -- **neither of which is
one of the two permitted derivation inputs.** The profile was never updated with
the outcome.

Consequences for a customer-level question (the q6 candidate):

- An agent deriving strictly from the two inputs must treat customer-level
  publishing as **unresolved**, and either omit it or record it as a `gaps[]`
  entry -- never assume it is approved.
- **This is a live D-level item for the owner**, and arguably the cleanest fix is
  to write the Q1 outcome (and the resulting `Source-ready status`) THROUGH to
  `source-profile.md`, so the permitted input carries the ruling it depends on.
  That is a profile edit, so it is the owner's call, not the agent's.

## Known caveat that any narrative must carry

Grounded in **`source-profile.md`** (the permitted input), which measures it
directly:

> `discount_applied` | TEXT | **4,199 / 33.39%** missing | 3 distinct |
> ``True``/``False``/``''``; a discount FLAG (not a return). Blank semantics OPEN

and lists it as open item 1: "blank semantics undecided (unknown vs False);
**drives every discount metric downstream**". The publish pack records the same
figure with the corrected framing (floor 33.55% if blanks are treated as
not-discounted; re-approved 2026-07-05 on the 50.37% known-status framing).

Any callout mentioning discount share **must** state this, or the brief narrates a
number the data does not support.

## Candidate `gaps[]` (agent-identified, owner to confirm)

`gaps` must be present (may be `[]`). Both candidates below are grounded in
**`source-profile.md`** -- the permitted input -- not in `report-intent.yaml`'s
`exclusions_and_non_goals` (which happens to agree, and is review context only):

| Owner decision | Missing source fact | Profile evidence | Unlocking feed |
|---|---|---|---|
| Which categories are actually profitable? | no cost/margin column | the profiled column list carries price/quantity/total only -- no cost column exists | a cost or purchase-price feed |
| What is being returned, and why? | no returns rows | "**Returns population & how identified. NONE in this source.** No negative or zero rows, no transaction-type / return-flag column. Confirmed with the data owner: returns exist in a SEPARATE system NOT loaded here. RC8 N/A" | a returns/credit-note feed |

A gap must **not** also appear as a `questions[]` entry -- you cannot frame what
you cannot answer.

## Definition of done

Restated from issue #514. One wording change, deliberate: #514 says
"owner-authored questions", which contradicts `bi-analyst-knowledge` -- the AGENT
derives and drafts the questions, cites, and story order; the owner **approves or
revises** them. An agent reading the original phrasing would hand the derivation
back and stop, producing nothing for the owner to review.

- [ ] `narrative-brief.md` with a `seshat.narrative-brief/v1` front section
      (**agent-authored, owner-reviewed** questions, cites, story order) plus the
      human-first body.
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

### Required write-throughs -- D1 is ALSO a `report_intent_approval`

Ruling D1 settles the six `report-intent.yaml` questions, and that intent carries
its **own** separate gate. Recording only the decision file above would leave the
dashboard coordinator blocked even after all five decisions are ruled:

- `dashboard_coordinator._check_intent_approved` reads the verdict through the
  shipped decision gate (`verdict_for(root, tracked_files, "report_intent")`) and
  returns `blocked` with `no valid report_intent_approval decision in the store`
  whenever that verdict is not `pass`.
- `design/report-intent.yaml` records its own `readiness.status: "blocked"` with
  `no report_intent_approval decision recorded yet for branch_performance_weekly`.

So the D1 ruling must be written through to **both**:

1. a `report_intent_approval` decision record in the project Decision Store for
   `branch_performance_weekly` (the `report_intent` flow stage, which contributes
   to the `dashboard_ready` spine stage), and
2. `design/report-intent.yaml` -- its `readiness` block updated from `blocked` to
   reflect the recorded approval, and any question text the owner revised under D1.

List both in the decision file's `artifacts_updated` section, following the
sibling pattern in `approval-decision-H9-time-intel.md`. Without them, D1-D5 can
all be ruled and Stage-6 authoring still stops on a gate nobody notices.

### Who may write the decision file: TRANSCRIPTION vs DECIDING

The agent **may transcribe** a ruling the named human supplied, and should -- that
is the `approval-console` skill's job (it "only TRANSCRIBES a decision a named
human supplied"), and an approval that lives only in chat cannot be reviewed,
advance a gate, or be audited. Requiring the owner to hand-edit the repository
would leave answered requests sitting `open` and unauditable.

What the agent must **never** do, per that same skill:

- pick the `selected_option` for any of D1-D5;
- supply or forge the `owner`;
- invent the `rationale`;
- auto-accept a recommended default, or treat silence as acceptance;
- flip `status:` to `answered` when no human has actually answered.

A field the human did not supply is **left unfilled** -- never guessed. So:
**the owner decides, the agent may write down what they decided.**

A "do the recommended actions" instruction authorizes the transcription, never
the decision. R5 named this seam, and it is the one item in issue #514 that no
delegated mandate covers.
