# Business Meaning Registry -- `<table-id>`

> **Template -- copy this file to `mappings/<table>/business-meaning-registry.md`**
> (per [ADR 0003](../docs/decisions/0003-mapping-artifact-location.md)), fill every
> `<placeholder>` and blank cell, commit it.
> This is an **OPTIONAL Source Ready (Stage 1) strengthening artifact** -- it gives the
> semantic-proposal half of the profile a reusable shape (see
> `docs/source-intelligence.md`). The ONE required Stage-1 artifact is still
> `source-profile.md`; this registry adds `evidence[]`, it does not replace the profile.
>
> **PROPOSED, not invented.** Every meaning below defaults to `proposed` (awaiting a
> NAMED human confirmation). The agent never self-confirms a meaning; a business
> rollup, a PII ruling, or a grain meaning is routed to
> `mappings/<table>/unresolved-questions.md`, never decided here (Principle V).
>
> **Generic, not C086.** This is a SCHEMA. Do NOT inline the C086 / El Ezaby pharmacy
> values (the billing_type Arabic->English table, the business_segment rollup, any real
> code / product / store / staff name). Those are a FILLED INSTANCE -- cite
> `docs/data-dictionary.md` and a filled worked example under
> `docs/worked-examples/`, never copy them.
>
> **ASCII only.** Use `->` for arrows, `<->` for pairs, `>=`/`<=` for inequalities,
> `[OK]`/`[x]` for status. No unicode.
>
> **No fake confidence.** Status is `proposed` | `confirmed` plus the evidence it cites.
> There is NO numeric confidence / score field, and a filled copy MUST NOT add one
> (roadmap rule #9).

---

## Header

| Field | Value |
|-------|-------|
| Table id | `<table-id>` (e.g. `C091`) |
| Source system | `<source-system>` (e.g. ERP / POS export) |
| Profiled from | `mappings/<table>/source-profile.md` (the numbers these meanings rest on) |
| Registered on | `<YYYY-MM-DD>` |
| Registered by | `<analyst / agent>` |

---

## Registry entries

One row per business term / coded value the profile surfaced. Every entry is
`proposed` until a NAMED owner confirms it. Placeholder rows below show the shape;
replace them -- do NOT leave a `<placeholder>` in a committed, confirmed entry.

| Term / coded value (as in source) | Canonical meaning | Observed surface forms | Source column(s) | Status | Confirmed by (when `confirmed`) | Evidence |
|-----------------------------------|-------------------|------------------------|------------------|--------|-------------------------------|----------|
| `<source-value-a>` | `<plain-language meaning>` | `<form-1>`, `<form-2>` | `<column-x>` | `proposed` | -- | `source-profile.md` row `<n>` |
| `<source-value-b>` | `<plain-language meaning>` | `<form-1>` | `<column-y>` | `proposed` | -- | `source-profile.md` row `<n>` |
| `<rollup-or-pii-term>` | `<PROPOSED meaning -- see open decision>` | `<form>` | `<column-z>` | `proposed` | -- | -> `unresolved-questions.md` row `<n>` |

- **Status `proposed`**: the meaning is a proposal awaiting human confirmation.
- **Status `confirmed`**: a NAMED owner signed off; record the owner + the date. The
  agent CANNOT self-grant `confirmed` (Principle V).

## Discipline (the rules this shape enforces)

- **Default `proposed`.** A meaning is never stated as fact on first registration.
- **Confirmation is a named human action.** Only a named owner promotes an entry to
  `confirmed`; the agent proposes and stops.
- **Route judgment calls out.** Any entry whose meaning is a business rollup/segment,
  a PII ruling, or a grain decision MUST point to
  `mappings/<table>/unresolved-questions.md` and stay `proposed` -- never self-confirmed.
- **Surface the conflict, never bury it.** If an entry contradicts the source profile
  (e.g. it claims a returns term the authoritative column shows none of), STOP and
  record the conflict for reconciliation (Principle V evidence-cross-check) -- do not
  proceed as if it agreed.
- **No score.** Readiness is `proposed`/`confirmed` + evidence only; never a number.

## See also

- The stage this strengthens: `../docs/readiness/source-ready.md` (the
  PROPOSED-not-invented semantic discipline + its review gate).
- The Layer-2 explainer (how this becomes Source Ready evidence):
  `../docs/source-intelligence.md`.
- The bilingual sibling: `retail-term-dictionary.md`.
- Where judgment-call meanings route: `unresolved-questions.md` (a per-table artifact).
- Principles: `../.specify/memory/constitution.md` V (Agent Stops at Judgment Calls),
  VII (C086 Is An Example).
- The FILLED instance this template CITES, never inlines: `../docs/data-dictionary.md`
  (the reference mappings), plus a filled worked example under `../docs/worked-examples/`.
