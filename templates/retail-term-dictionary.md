# Retail Term Dictionary (Arabic <-> English) -- `<table-id>`

> **Template -- copy this file to `mappings/<table>/retail-term-dictionary.md`**
> (per [ADR 0003](../docs/decisions/0003-mapping-artifact-location.md)), fill every
> `<placeholder>` and blank cell, commit it.
> This is an **OPTIONAL Source Ready (Stage 1) strengthening artifact** for a bilingual
> retail source: it records each source-language (e.g. Arabic) term's canonical English
> meaning ONCE, so silver mapping references a single shared vocabulary instead of
> re-deriving it. See `docs/source-intelligence.md`. The ONE required Stage-1 artifact
> is still `source-profile.md`.
>
> **PROPOSED, not invented.** Every meaning defaults to `proposed` (awaiting a NAMED
> human confirmation). A returns / rollup / PII meaning is routed to
> `mappings/<table>/unresolved-questions.md`, never decided by the agent (Principle V).
>
> **Generic, not C086.** This is a SCHEMA. Do NOT inline any real source term -- no real
> Arabic billing/returns/segment string, no `Z`-style code, no `PHARMA`/segment value,
> no real product / store / staff name. The placeholder for a source-language term is
> the LITERAL token `<arabic-term>` -- never a real Arabic string (which would also
> break the ASCII rule). Cite the filled instance in `docs/data-dictionary.md`; never
> copy it.
>
> **ASCII only.** Use `->` for arrows, `<->` for pairs. No unicode -- a real Arabic
> string does not belong in this generic template; the filled per-table copy is where
> real terms live.
>
> **No fake confidence.** Status is `proposed` | `confirmed` + evidence. NO numeric
> score field (roadmap rule #9).

---

## Header

| Field | Value |
|-------|-------|
| Table id | `<table-id>` |
| Source system | `<source-system>` (e.g. bilingual POS export) |
| Profiled from | `mappings/<table>/source-profile.md` |
| Registered on | `<YYYY-MM-DD>` |
| Registered by | `<analyst / agent>` |

---

## Dictionary entries

One row per source-language term. Synonyms / surface variants (including
encoding-corruption "mojibake" spellings) are recorded UNDER ONE canonical meaning --
an encoding variant is a surface form, NOT a new term. Placeholder rows show the shape.

| Term (source language) | Canonical English meaning | Synonyms / surface variants | Source column | Status | Evidence |
|------------------------|---------------------------|-----------------------------|---------------|--------|----------|
| `<arabic-term>` | `<english-meaning>` | `<variant-1>`, `<mojibake-variant>` | `<column-x>` | `proposed` | `source-profile.md` row `<n>` |
| `<arabic-term-2>` | `<english-meaning>` | `<variant>` | `<column-y>` | `proposed` | `source-profile.md` row `<n>` |
| `<arabic-returns-term>` | `<english-meaning, e.g. a return/credit>` | `<variant>` | `<authoritative-billing-column>` | `proposed` | -> see RC8 note below |

## RC8 -- returns identity comes from the authoritative column

A returns-related term's meaning MUST state that **whether a row is a return is
determined by the AUTHORITATIVE billing/transaction-type column, NOT by the sign of a
measure** (RC8). The measure sign misses zero-value and edge-case returns. Record the
authoritative column in the entry's `Source column`; never infer returns from a
negative amount.

## Encoding-variant discipline

The SAME source term may appear in two encodings (clean vs corrupted/mojibake). Record
both as synonyms/surface variants of ONE canonical meaning -- encoding corruption is a
surface-form variant, not a distinct term. This keeps the vocabulary from forking.

## Discipline (shared with the registry)

- Default `proposed`; promotion to `confirmed` is a NAMED human action (agent never
  self-confirms).
- Route returns / rollup / PII meanings to `unresolved-questions.md`; stay `proposed`.
- Surface (do not bury) any entry that contradicts the source profile.
- No numeric score -- status + evidence only.

## See also

- The stage this strengthens: `../docs/readiness/source-ready.md`.
- The Layer-2 explainer: `../docs/source-intelligence.md`.
- The business-term sibling: `business-meaning-registry.md`.
- Where judgment-call meanings route: `unresolved-questions.md`.
- Cleaning defaults this bakes in: RC8 (returns from the authoritative column) +
  RC-encoding (surface variants), `../docs/decisions/0002-retail-cleaning-defaults.md`.
- Principles: `../.specify/memory/constitution.md` V (Agent Stops at Judgment Calls),
  VI (Defaults Then Deviations / RC8), VII (C086 Is An Example).
- The FILLED instance this template CITES, never inlines: `../docs/data-dictionary.md`
  (the billing_type Arabic->English table + business_segment rollup), and a filled
  worked example under `../docs/worked-examples/`.
