# Contract: backwards-compatibility worked example

Demonstrates the additive-only rule from `data-model.md` section 4 with a concrete before/after
pair. This is a DESCRIBED expectation for the implementation phase's golden-file tests; no
golden file is generated or committed by this spec-work run (task boundary: no golden-file
regen).

## Compliant change: `schema_version` "1.0" -> "1.1" (MINOR, additive)

**"1.0" document** (as in `json-schema.md`):

```json
{
  "schema_version": "1.0",
  "title": "<TABLE>: <STAGE> review pack",
  "generated_at": null,
  "source_note": "composed by <producer skill/module>, <date>",
  "sections": [
    {
      "name": "Gate requirement",
      "status": "pass",
      "evidence": ["..."],
      "blocking_reasons": [],
      "note": null
    }
  ]
}
```

**Hypothetical "1.1" document** -- adds ONE new OPTIONAL field, `owner_hint`, to `Section`
(e.g. a future feature wants to surface which named human a section's approval would route
to, without this feature resolving or granting that approval):

```json
{
  "schema_version": "1.1",
  "title": "<TABLE>: <STAGE> review pack",
  "generated_at": null,
  "source_note": "composed by <producer skill/module>, <date>",
  "sections": [
    {
      "name": "Gate requirement",
      "status": "pass",
      "evidence": ["..."],
      "blocking_reasons": [],
      "note": null,
      "owner_hint": "<role or name, informational only>"
    }
  ]
}
```

**Why this is compliant**: a consumer written against `"1.0"`'s documented fields
(`schema_version`, `title`, `generated_at`, `source_note`, `sections[].{name, status,
evidence, blocking_reasons, note}`) reads every one of those fields UNCHANGED from the `"1.1"`
document. It simply does not know about `owner_hint` and, per FR-008, MUST ignore it rather
than fail. No existing field was renamed, removed, or repurposed. This is exactly the additive
change data-model.md section 4 permits under a MINOR bump.

## Non-compliant change (MUST be classified as MAJOR, for contrast)

```json
{
  "schema_version": "1.1",
  "title": "<TABLE>: <STAGE> review pack",
  "generated_at": null,
  "source_note": "composed by <producer skill/module>, <date>",
  "sections": [
    {
      "name": "Gate requirement",
      "state": "pass",
      "proof": ["..."],
      "note": null
    }
  ]
}
```

**Why this is NON-compliant as a MINOR bump**: `status` was renamed to `state`, and `evidence`
was renamed to `proof`; `blocking_reasons` was removed entirely. A `"1.0"`-built consumer
reading `section["status"]` or `section["evidence"]` would get a `KeyError`/`None` and silently
misbehave. Per data-model.md section 4, ANY of these three changes alone would require a MAJOR
version bump (e.g. `"2.0"`), not a MINOR one -- and even then, a MAJOR bump does not retroactively
make old `"1.x"` documents invalid; it only means a `"2.x"` document is not guaranteed readable
by a `"1.x"`-built consumer.

## What this contract proves for SC-004

SC-004 ("a JSON document produced at a given `schema_version` remains readable, field-for-field,
by a consumer written against any prior MINOR/PATCH version of the same MAJOR `schema_version`")
is demonstrated here by the compliant `"1.0"` -> `"1.1"` pair: every field the `"1.0"` consumer
contract names is present, unchanged, in the `"1.1"` document. The implementation phase's
`tasks.md` includes a task to encode this exact pair (or an equivalent one) as an executable
pytest golden-file test once the module exists.
