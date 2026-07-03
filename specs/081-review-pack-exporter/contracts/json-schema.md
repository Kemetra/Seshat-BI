# Contract: JSON output format

Generic worked example over the same input pack as `markdown.md` (Principle VII -- placeholder
values only). This is the machine format (FR-002b); it carries `schema_version` at the top
level (FR-007) and preserves any embedded `FindingRecord` field-for-field against B2's
`Finding.to_dict()` shape (FR-009, SC-007).

## JSON Schema (informal, documenting the shape from data-model.md)

```text
{
  "schema_version": "<MAJOR>.<MINOR>",     // e.g. "1.0"
  "title": "<string>",
  "generated_at": "<string> | null",
  "source_note": "<string> | null",
  "sections": [
    {
      "name": "<string>",
      "status": "<string>",                 // one of data-model.md section 1's tokens,
                                             // or any other string (unrecognized pass-through)
      "recognized": true | false,           // present ONLY when status is outside the
                                             // documented union (FR-017); omitted otherwise
      "evidence": ["<string>", ...],        // may be empty array
      "blocking_reasons": ["<string>", ...],// may be empty array
      "findings": [                          // OPTIONAL key; omitted if the section carries none
        {
          "rule_id": "<string>",
          "severity": "<string>",
          "message": "<string>",
          "locator": "<string>"
        }
      ],
      "note": "<string> | null"
    }
  ]
}
```

## Example output (for the pack described in `markdown.md`)

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
      "evidence": ["<STAGE> gate requirement documented at docs/readiness/<stage>-ready.md"],
      "blocking_reasons": [],
      "note": null
    },
    {
      "name": "Readiness state",
      "status": "blocked",
      "evidence": [],
      "blocking_reasons": [
        "grain not confirmed unique on data",
        "PII ruling pending on column <col>"
      ],
      "findings": [
        {
          "rule_id": "S5",
          "severity": "WARNING",
          "message": "type discipline check",
          "locator": "warehouse/silver/<table>.sql:12"
        }
      ],
      "note": null
    }
  ]
}
```

## Contract rules demonstrated

- `schema_version` is present and is the FIRST thing a consumer reads to know what field set to
  expect (FR-007).
- The `findings` key is entirely OMITTED on the first section (it had none) rather than
  present-and-empty vs. present-and-populated being ambiguous -- a consumer checks for key
  presence, not truthiness, to know whether findings were even considered by the producer.
  (This is a documented convention, not a data-model.md field default; note it in
  implementation.)
- The embedded finding under "Readiness state" has EXACTLY the four B2 field names
  (`rule_id`, `severity`, `message`, `locator`) with no renaming and no extra wrapper (SC-007).
- No field in this document is a numeric confidence/health score or a completeness count
  (SC-003) -- there is no `"health": 0.75` or `"sections_passed": 1` anywhere.
- A consumer parsing this JSON that only understands `schema_version: "1.0"`'s documented
  fields ignores any field it does not recognize (FR-008) -- see
  `backwards-compat-example.md` for the worked MINOR-bump case.
