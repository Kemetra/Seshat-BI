# Customer Domain

Retention, purchase frequency, and lifetime value of customers. Every KPI here
requires reliable customer identification, which is an unmade ruling -- so each
KPI below stays Planned until a human owner confirms the identity key and grain.

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| Customer Retention Rate | — | Planned (needs confirmed customer identity / grain) |
| Purchase Frequency | — | Planned (needs confirmed customer identity / grain) |
| Customer Lifetime Value (CLV) | — | Planned (needs identity + CLV horizon ruling) |
| New-vs-Returning Customer split | — | Planned (needs identity + first-purchase anchor) |

No row is Seeded: a customer contract cannot be seeded before the identity/grain
ruling is made (see Owner ruling triggers below).

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract or an honest
planned marker. A question never implies a formula and never invents a contract.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| What share of customers return to buy again? | — | Planned (Customer Retention Rate) |
| How often does a customer purchase in a period? | — | Planned (Purchase Frequency) |
| What is a customer worth over their lifetime? | — | Planned (Customer Lifetime Value) |
| How much of our revenue is new vs returning customers? | — | Planned (New-vs-Returning split) |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- Identity resolution across channels -- the same person may appear as multiple
  loyalty ids, cards, phones, or accounts; without a confirmed identity key these
  KPIs cannot be computed. This is a reserved ruling, not a default.
- Retention window definition -- retained over what period (rolling 12 months,
  calendar year, since first purchase)? Different windows give different rates.
- CLV horizon and discounting -- lifetime over what horizon, and is future value
  discounted? An unstated horizon makes CLV non-comparable.
- One-time vs repeat customer -- the cut between "new" and "returning" depends on the
  first-purchase anchor and the identity key above.

## Owner questions

Ask these before this domain's contracts are handed off. Each card is the owner-facing
form of an ambiguity listed above: it names the question in business language, the
silent breakage if it goes unanswered, and the `decision_type` under which the answer is
recorded in the Decision Store. The **layer default** is context shown to the owner, never
a recorded ruling -- an unanswered card stays `pending` and this domain stays blocked
(`knowledge/kpi-ambiguities.md`, Resolution rule: this layer never invents a policy to
make a number appear).

Every ambiguity listed above has a card here UNLESS it is already marked **RULED** (a
settled decision -- re-asking invites a contradicting answer) or states a grain/handling
instruction rather than a question only the owner can answer. Those exclusions are named
in the row list below rather than left silent.

| # | Ask the owner | If unanswered | Layer default (context only) | Records as |
|---|---------------|---------------|------------------------------|------------|
| clv | Over what horizon is customer lifetime value measured, and is future value discounted? | CLV is not comparable between reports or periods | None -- the horizon is a business definition | `policy_ruling` |
| newrepeat | Where is the cut between a new and a returning customer? | New-vs-returning splits shift with the anchor and mislead acquisition reporting | None -- depends on your identity key ruling | `kpi_definition` |
| identity | Which field is the canonical customer key, and how are the other identifiers linked, prioritised and deduplicated? | Unlinked identifiers leave the same person counted as several customers and every retention KPI wrong | None -- a reserved ruling, never defaulted | `kpi_definition` |
| retention | Over what window is a customer counted as retained: rolling 12 months, calendar year, or since first purchase? | Retention rate changes with the window and is not comparable | None -- the window is a business definition | `policy_ruling` |

## Owner

Marketing / CRM and Finance (with Governance for any PII publish ruling).

## Notes

No customer metric contract is seeded. Each future customer contract needs the F009
contract-template + review process AND a confirmed identity/PII ruling first. Customer
KPIs are non-additive (rates and ratios) and identity-dependent: they cannot be summed
across rows and have no meaning until the customer grain is fixed.

## Owner ruling triggers (PII / identity)

These are reserved human rulings (constitution Principle V -- Agent Stops at Judgment
Calls). This file STATES each stop and decides NONE; no customer KPI may become more
than a Planned marker until the relevant ruling is made and recorded by the named owner.
This section is customer-only for now (it is not retrofitted to the other domain files).

- **Customer identity / grain.** What field(s) uniquely identify a customer (loyalty id,
  phone, card, account), and at what grain are retention, frequency, and lifetime value
  defined? No identity key is confirmed in the repo. The agent surfaces this; it never
  decides it.
- **PII publish-safety.** Are customer identifiers, name, or contact details publishable,
  or default-drop? The default is DROP, and Governance must sign off before any customer
  identifier is published. The agent must not decide publish-safety.
- **Business-segment rollups.** Any customer segmentation (new-vs-returning, tier, cohort)
  requires an analyst-supplied value-to-group table. The agent never invents segments.
- **Product identity (where a customer KPI leans on it).** Where a customer KPI uses
  product identity (category affinity, repeat-product purchase), the stable product key is
  itself a reserved identity ruling and is not confirmed here.
