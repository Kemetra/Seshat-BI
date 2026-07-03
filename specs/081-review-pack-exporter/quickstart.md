# Quickstart: Review Pack Exporter

This describes how a producer, a consumer, or a test is expected to use the exporter, once
implemented (per plan.md's identified module, `src/retail/review_pack_export.py` -- not
created by this spec-work run). All examples are illustrative Python, not executed here.

## For a producer (e.g. J1's skill, LVR, a future review engine)

1. Assemble a `Pack` object from whatever content you already composed. You do NOT need to
   change how you gather that content -- the exporter never reads your sources for you
   (spec.md FR-001).

   ```python
   from retail.review_pack_export import Pack, Section

   pack = Pack(
       schema_version="1.0",
       title="mytable: mapping_ready review pack",
       generated_at=None,
       source_note="composed by approval-evidence-pack skill",
       sections=[
           Section(
               name="Gate requirement",
               status="pass",
               evidence=["mapping_ready gate requirement documented at docs/readiness/mapping-ready.md"],
               blocking_reasons=[],
           ),
           Section(
               name="Readiness state",
               status="blocked",
               evidence=[],
               blocking_reasons=["grain not confirmed unique on data"],
           ),
       ],
   )
   ```

2. Render whichever format(s) you need, from the SAME `pack` object:

   ```python
   from retail.review_pack_export import to_markdown, to_json, to_compact_ci_summary

   markdown_text = to_markdown(pack)             # -> str, for a human-readable doc
   json_doc = to_json(pack)                       # -> dict; caller does json.dumps(json_doc)
   ci_line = to_compact_ci_summary(pack)          # -> str, for a PR comment / CI log line
   ```

3. If your content includes governance findings (e.g. from `retail check --format json`),
   pass them through unchanged:

   ```python
   Section(
       name="Static findings",
       status="warning",
       evidence=[],
       blocking_reasons=[],
       findings=[f.to_dict() for f in some_findings],   # core.Finding.to_dict() shape
   )
   ```

## For a consumer (e.g. a CI script parsing the JSON format)

- Always check `schema_version` first.
- Read only the fields you need; IGNORE any field you do not recognize (FR-008) -- do not fail
  merely because a newer document has an extra key.
- Treat `status` as an opaque string to compare against your OWN known-token list; if you see a
  token you do not recognize, treat it conservatively (e.g. as if it were `blocked`) rather
  than assuming it is safe.

```python
import json

doc = json.loads(raw_json_text)
assert doc["schema_version"].startswith("1.")   # MAJOR-version pin
for section in doc["sections"]:
    status = section["status"]                   # verbatim token, never remapped
    if status not in KNOWN_SAFE_TOKENS:
        # unrecognized or explicitly unsafe -> treat conservatively
        ...
```

## For a human reading the Markdown format

Open the rendered `.md` output directly (however the producer chose to name/store it -- this
feature does not dictate a file path, unlike J1's fixed
`mappings/<table>/approval-evidence-pack-<stage>.md` convention). Every status, evidence line,
and blocking reason traces back to something the producer already knew; nothing in the document
is invented by the renderer.

## For CI / a PR bot

Call `to_compact_ci_summary(pack)` and post/print the returned string. The string never
contains a numeric score or a completeness tally (contracts/compact-ci-summary.md) -- it is
safe to surface directly in a PR comment or CI log without a human first sanity-checking that
no fabricated confidence number slipped in.

## Verifying a schema change stays compatible (for a future contributor)

Before merging a change to `Pack`, `Section`, or `FindingRecord`:

1. Read data-model.md section 4's additive-only rule.
2. Compare your change against `contracts/backwards-compat-example.md`'s compliant vs.
   non-compliant pair.
3. If your change only adds an optional field, bump the MINOR version and add a golden-file
   test pairing an old-shape document with a new-shape document (per that contract's closing
   note).
4. If your change renames, removes, or repurposes an existing field or a status token's
   meaning, it is MAJOR -- do not ship it as a MINOR bump.
