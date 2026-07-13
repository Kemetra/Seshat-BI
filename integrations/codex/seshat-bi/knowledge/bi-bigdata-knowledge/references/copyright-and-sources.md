# Copyright and Sources

All content in this skill is original. It was grounded in current public documentation and
practitioner writing on distributed data processing, then re-expressed in our own words and
re-cast into the fictional retail domain.

## Hard rules

- Do not copy paragraphs or prose from any documentation, article, or blog.
- Do not copy or lightly paraphrase third-party examples.
- Do not reproduce code listings from any source. Code idioms here are standard,
  minimal, and re-cast into the retail schema (facts of the engine, not authored
  expression).
- Do not preserve a source's scenario or dataset. Use the fictional retail-at-scale
  schema in `references/retail-bigdata-schema.md`.

## What is allowed

- Explaining a **concept** (e.g. how a shuffle works, what AQE skew-join does) in our own
  words, framed for BI/data agents.
- Stating widely-documented engine behavior and configuration names as facts
  (e.g. `spark.sql.adaptive.enabled`), without copying surrounding prose.
- Original worked examples on the fictional retail schema.

## Sources

Topics were grounded against current (2025–2026) public material on Spark performance
tuning, AQE and skew handling, broadcast vs shuffle joins, the small-files problem,
`collect()`/driver-memory anti-patterns, Polars/DuckDB vs Spark trade-offs, data-quality
validation at scale, and Parquet/Delta/Iceberg table formats. Specific links are recorded
in `references/research-notes.md`. Those notes are a citation list only — no source text is
reproduced.

## Review gate

Every slice's review includes a copyright check against these rules and confirms that all
examples use the fictional retail schema.
