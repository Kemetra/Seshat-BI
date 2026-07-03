# Contract: Markdown output format

Generic worked example (Principle VII -- placeholder table/stage/entity names only). Input is
a `Pack` (data-model.md section 2) with two sections.

## Example input (pack, as a plain-language description)

```text
Pack(
  schema_version="1.0",
  title="<TABLE>: <STAGE> review pack",
  generated_at=None,                      # omitted -> no generated-at line rendered
  source_note="composed by <producer skill/module>, <date>",
  sections=[
    Section(
      name="Gate requirement",
      status="pass",
      evidence=["<STAGE> gate requirement documented at docs/readiness/<stage>-ready.md"],
      blocking_reasons=[],
      findings=None,
      note=None,
    ),
    Section(
      name="Readiness state",
      status="blocked",
      evidence=[],
      blocking_reasons=[
        "grain not confirmed unique on data",
        "PII ruling pending on column <col>",
      ],
      findings=[
        {"rule_id": "S5", "severity": "WARNING", "message": "type discipline check",
         "locator": "warehouse/silver/<table>.sql:12"},
      ],
      note=None,
    ),
  ],
)
```

## Expected Markdown output (byte-exact shape; blank lines significant)

```markdown
# <TABLE>: <STAGE> review pack

_source: composed by <producer skill/module>, <date>_

## Gate requirement

**Status**: pass

**Evidence**:
- <STAGE> gate requirement documented at docs/readiness/<stage>-ready.md

**Blocking reasons**: none recorded

## Readiness state

**Status**: blocked

**Evidence**: none recorded

**Blocking reasons**:
- grain not confirmed unique on data
- PII ruling pending on column <col>

**Findings**:
- [WARNING] S5: type discipline check (warehouse/silver/<table>.sql:12)
```

## Contract rules demonstrated

- `generated_at` absent -> no timestamp line anywhere in the output (determinism, FR-013).
- `status` values (`pass`, `blocked`) appear verbatim as the literal token, not translated to
  prose like "OK" or "Failed" (FR-003).
- An empty `evidence`/`blocking_reasons` list renders as an explicit "none recorded" statement,
  never an omitted section or a blank line that could be misread (data-model.md section 3).
- A `FindingRecord` renders using its four B2-compatible fields (`severity`, `rule_id`,
  `message`, `locator`) in a fixed, documented order.
- Rendering the same `Pack` object twice produces byte-identical Markdown (SC-005) -- there is
  no non-deterministic element (no random ordering, no wall-clock read) in this contract.
- No numeric score, percentage, or "N of M" tally appears anywhere (SC-003).
