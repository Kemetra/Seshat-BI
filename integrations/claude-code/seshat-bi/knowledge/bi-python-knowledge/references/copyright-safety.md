# Copyright Safety

All content in this skill is original. Source books and materials are used for
**private grounding of concepts only** — never as a source of text to reproduce.

## Hard rules

- Do not copy paragraphs or prose from any book or article.
- Do not copy or lightly paraphrase book examples.
- Do not copy exercises or their solutions.
- Do not copy datasets, sample tables, or their column layouts.
- Do not reproduce code listings from any source.
- Do not preserve a book's example domain (e.g. its specific datasets, named
  characters, or scenario framing). Re-cast every concept into the fictional retail
  domain.

## What is allowed

- Explaining a **concept** in our own words, framed for BI/data agents.
- Writing **original** code idioms that any pandas user would independently write to
  perform a standard operation (these are facts of the library, not authored
  expression). Keep them minimal and re-cast into the retail schema.
- Building original worked examples on the fictional retail schema in
  `references/retail-dataframe-schema.md`.

## The retail-only test

Before adding any example, confirm:

1. The data is fictional retail (stores, SKUs, orders, returns, suppliers).
2. The framing is ours, not a book's scenario.
3. No table, dataset, or row set is lifted from a source.
4. Any code is a standard idiom, not a transcribed listing.

If an example cannot pass all four, rewrite it until it can, or drop it.

## Review gate

Every slice's review (see the slice plan's build-and-review cadence) includes a
copyright check against these rules. A slice does not pass review until it does.
