# Approval Request -- `source-profile-writethrough`

- **question_id:** `source-profile-writethrough`
- **table:** `retail_store_sales`
- **stage:** `source_ready`
- **subject:** write the four already-answered Q1-Q4 rulings (2026-06-25) through
  to `source-profile.md`, so the committed profile carries the decisions that
  currently live only in `unresolved-questions.md` and the readiness `approvals[]`
- **owner_required:** `data-owner`  *(the same named human who answered Q1-Q4)*
- **status:** `open`  *(a request is `open` until a named human answers it via
  `approval-decision-source-profile-writethrough.md`; it never answers itself)*
- **prepared:** 2026-07-26 (agent-assembled; the edit is drafted, NOT applied)
- **raised by:** issue #514 review -- the narrative brief cannot derive a
  customer-level question while the profile records the PII question as open

> **Why this is a request, not a patch.** `source-profile.md` is the committed
> Stage-1 artifact behind a `source_ready` gate the data owner already signed. The
> agent does not edit a signed artifact, and does not decide that a `warning`
> becomes a `pass`. Every word of the proposed edit below is a TRANSCRIPTION of a
> ruling the owner already made on 2026-06-25 -- no new judgment is introduced.

## Decision needed (one sentence)

> Approve writing the four already-recorded Q1-Q4 rulings into
> `source-profile.md` (and, consequently, whether its `Source-ready status`
> becomes `pass`), so the profile carries the decisions that downstream
> derivation is required to read from it.

---

## Why this matters: a real blocker, not tidiness

The narrative-brief derivation route permits **exactly two inputs** -- the
approved metric contracts and `source-profile.md`. It does **not** permit
`unresolved-questions.md` or `readiness-status.yaml`.

Today the profile says:

> `Source-ready status:` **`warning`** -- mechanical numbers are complete, BUT the
> semantic proposals (grain single-item-vs-basket, `discount_applied` blank
> meaning) are unconfirmed and the `customer_id` PII question is open. Not `pass`
> until the analyst confirms the semantics and governance rules on the PII column.

and its `customer_id` row says `PII question (see unresolved-questions)`.

**But all four questions are `answered` and the gate is `CLEARED`** (
`unresolved-questions.md:15`: "all four questions answered 2026-06-25"). The
rulings exist; the profile was simply never updated.

The consequence is concrete and currently blocking:

- An agent deriving **strictly** from the two permitted inputs must treat
  customer-level publishing as **unresolved**, so the drafted brief records it as
  a `gaps[]` entry rather than a question.
- The signed binding map contains **v10** (`TransactionCount` by
  `dim_customer_rss[customer_id]`, "Q6 top customers"). With no customer
  question in the brief, v10 has no `decision_questions` to bind to, which is an
  `orphan_visual` finding under `seshat.binding-map/v1`.
- So `narrative-check --binding-map` **cannot pass** until either this
  write-through happens (v10 binds to a real question) or v10 is dropped from the
  design.

That makes this request a prerequisite for issue #514's "both narrative-check
modes pass" criterion.

## The proposed edit (transcription only -- verify each line against its source)

### 1. The `customer_id` column row (line 43)

```diff
-| `customer_id` | TEXT | 0 / 0.00% | 25 | no | `CUST_xx`; pseudonymous customer surrogate -> dim candidate. PII question (see unresolved-questions) |
+| `customer_id` | TEXT | 0 / 0.00% | 25 | no | `CUST_xx`; pseudonymous customer surrogate -> `dim_customer`. PII RULED 2026-06-25 (data owner): KEEP -- pseudonymous surrogate, no raw PII; RC4 deviation stands (assumptions.md) |
```

Source: `unresolved-questions.md` Q1 -- *"2026-06-25 (data owner): KEEP
`customer_id` as `dim_customer` -- it is a pseudonymous surrogate, no raw PII. RC4
deviation stands (recorded in assumptions.md)."*

### 2. The `Source-ready status` block (lines 130-133)

```diff
-Source-ready status: **`warning`** -- mechanical numbers are complete, BUT the semantic
-proposals (grain single-item-vs-basket, `discount_applied` blank meaning) are unconfirmed
-and the `customer_id` PII question is open. Not `pass` until the analyst confirms the
-semantics and governance rules on the PII column.
+Source-ready status: **`pass`** -- mechanical numbers are complete AND all four semantic /
+governance questions were answered by the data owner on 2026-06-25 (Gate status: CLEARED,
+see `unresolved-questions.md`). The rulings, transcribed:
+
+- **Q1 (PII / governance):** KEEP `customer_id` as `dim_customer` -- a pseudonymous
+  surrogate, no raw PII. RC4 deviation stands (`assumptions.md`).
+- **Q2 (`discount_applied` blank):** blank = UNKNOWN -> NULL in silver (RC5). Do NOT
+  coerce to False; discount metrics EXCLUDE unknowns.
+- **Q3 (grain):** one row = one single-item transaction; `total_spent` is the line total.
+  No separate basket/line dimension.
+- **Q4 (missing `item`):** KEEP the rows; FK COALESCE the missing `item` to the `-1`
+  unknown member of `dim_product` (RC14). Do not drop sales.
```

Sources: `unresolved-questions.md` Q1-Q4, all `answered` 2026-06-25, quoted
verbatim above.

## What the owner must rule

- **W1.** Is the transcription of each of Q1-Q4 **accurate** to the ruling made?
  (The agent transcribed; it did not interpret.)
- **W2.** Does `Source-ready status` become **`pass`**? All four cited blockers are
  answered and the gate is CLEARED, so the stated `warning` condition no longer
  holds — but promoting a readiness status is a named-human call, never the
  agent's. Declining leaves it `warning` with the rulings recorded, which still
  unblocks derivation.
- **W3.** Consequently: may a **customer-level question** enter the narrative
  brief (making v10 bindable), or should v10 be dropped from the design instead?

## What the agent did NOT do

- Did **not** apply the edit. `source-profile.md` is unchanged on disk.
- Did **not** decide W2. The diff above proposes `pass`; that is a proposal for
  the owner, and the request states plainly that declining is a valid outcome.
- Did **not** add a customer-level question to the brief. It stays a `gaps[]`
  entry, naming this request as the unlocking condition.

## How this request gets answered

The named human records the ruling in a **separate** decision file:

```
mappings/retail_store_sales/approval-decision-source-profile-writethrough.md
```

stating `question_id` (matching this request), `selected_option` for W1-W3,
`owner` (name + authority class), `date`, `rationale`, and an
`artifacts_updated` section. The agent **may transcribe** a ruling the owner
supplied — it may never pick W1-W3, supply the owner, invent the rationale, or
flip this request's `status:` when no human answered.

### Data safety

- [x] This request contains no secrets, real connection strings, client data, or
      raw PII. `customer_id` values are pseudonymous surrogates (`CUST_xx`) and
      none is reproduced here.
