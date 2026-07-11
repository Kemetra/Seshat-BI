# Readiness Passports

A readiness passport is a **portable, disclosure-safe snapshot** of one or
more tables' committed readiness state, exported by `retail passport export`
(or the `seshat` alias). It carries statuses, evidence identities, blocking
reasons, approval receipts, and the validation boundary — so another team,
tool, or repository can inspect what was true at export time and later check
whether that evidence still holds.

## What a passport is — and is not

A passport is **evidence transport, never authority**:

- It records approvals that named humans already granted; it cannot grant one.
- It cannot advance a readiness stage, clear a blocker, or stand in for the
  gate (`retail check`) or a live validation run.
- Every passport embeds this fixed statement in `authority_disclaimer`:

  > This passport records readiness statuses, evidence identities, and
  > existing approval receipts. It does not grant approval and does not
  > independently advance readiness.

Treat a passport the way you would treat a notarized photocopy: useful for
review and comparison, meaningless as a signature.

## Exporting

```console
$ retail passport export --repo . --table orders
passport: passport-0123456789abcdef
scope: orders
artifacts: 2 identities recorded
written: .seshat-output/passports/passport.json
```

- `--table` is repeatable; omit it to include every table with a committed
  `mappings/<table>/readiness-status.yaml`.
- Output is **contained**: it must stay under `.seshat-output/` (gitignored).
  Sharing the file elsewhere is an explicit human action.
- Export is **disclosure-gated and fail-closed**: the document is scanned for
  secrets, connection strings, PII fields, raw value arrays, and absolute
  paths before any file is written. Findings mean no passport.
- Export is deterministic for identical committed inputs; only
  `generated_at` varies, and `passport_id` is a content digest that excludes
  it.

## Compatibility

`schema_version` follows the additive `MAJOR.MINOR` contract published at
`schemas/readiness-passport.schema.json`. Consumers accept any minor within a
known major and must fail closed on an unknown major — `retail passport
verify` reports such a document as `incompatible` rather than guessing.

## Verifying

```console
$ retail passport verify --repo . --passport .seshat-output/passports/passport.json
passport: passport-0123456789abcdef
outcome: verified
  [verified] mappings/orders/readiness-status.yaml
  [verified] mappings/orders/source-profile.md
```

Verification re-derives each recorded artifact identity and reports **five
distinct categories** per artifact, plus one worst-first overall outcome:

| Category | Meaning |
|----------|---------|
| `verified` | The artifact exists and its content hash matches the passport. |
| `changed` | The artifact exists but its content no longer matches. |
| `missing` | The artifact is no longer present in the workspace. |
| `incompatible` | The entry (or the whole passport) cannot be interpreted safely — unknown schema major, path escaping the workspace, malformed entry. |
| `unavailable` | The passport recorded no content hash — deferred live evidence such as `[PENDING LIVE PROFILE]`, or prose evidence that records a fact rather than a file — so there is nothing to re-check. |

Verification is **non-mutating**: it never rewrites the passport, any source
artifact, or any readiness state. It also compares the recorded
`source_revision` against the current git revision when both are available.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Export succeeded / every artifact verified or disclosed as `unavailable` (prose or deferred-live evidence — a disclosed limit, not a failure). |
| 1 | Changed or missing evidence; or export blocked by disclosure findings. |
| 2 | Input defect: unknown table, unreadable passport, incompatible schema, uncontained output path. |

## Relationship to the rest of the kit

- The passport reads the same shared projection
  (`seshat.readiness_projection`) used by the demo HTML proof, the review
  integration, the MCP governor, and the static explorer — one disclosure-safe
  view, many formats.
- The readiness explorer (US8) can enrich its display from a passport, but
  works without one.
