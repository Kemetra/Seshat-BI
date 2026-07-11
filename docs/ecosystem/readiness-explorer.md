# Readiness Explorer

The readiness explorer is a **self-contained, offline HTML page** over the
portfolio's committed readiness state: every table's seven-stage status,
evidence (with availability), blocking reasons, approval receipts, next
allowed action, and the metric lineage recorded in committed contracts.

It exists for stakeholders who don't run the CLI: generate the page locally,
open it in any evergreen browser (desktop or mobile), and inspect readiness
without database, Power BI, or repository write access (FR-046).

## Generating

```console
$ retail explorer build --repo .
tables: 2
written: .seshat-output/explorer/index.html
The page is local and offline; publishing it anywhere is an explicit human action after disclosure review.
```

- The page is generated **solely from committed, permitted artifacts**
  (`mappings/*/readiness-status.yaml`, `mappings/*/metrics/*.yaml`) through
  the shared readiness projection (FR-043).
- Output is contained under the gitignored `.seshat-output/` root; the
  command cannot write anywhere else (exit `2` for an uncontained path).
- The result is one file with inlined CSS/JS and an embedded brand asset —
  it works from `file://`, needs no network, and renders at desktop and
  mobile widths.

## Truthfulness rules (FR-045)

The explorer **never infers a pass**. Statuses render verbatim, and the
awkward states stay explicit:

| State | How it renders |
|-------|----------------|
| Missing evidence file | The reference is listed with a `missing` marker. |
| Deferred live evidence (`[PENDING ...]`) | Listed with a `deferred` marker — pending, not failed, not passed. |
| Malformed `readiness-status.yaml` | The table appears as an explicit **input defect** entry naming the file. |
| `pass` with no evidence / `blocked` with no reason | The projection invariant blocks generation entirely (see below). |
| Unreadable metric contract | An explicit `input_defect` lineage node; no edge is invented. |

## Disclosure gate (FR-047)

Generation is **fail-closed**: the projection is scanned for secrets,
connection strings, PII-bearing fields, raw value arrays, and machine-local
absolute paths — and for the readiness invariants above. Any finding blocks
generation with exit `1`; no partial or redacted page is written.

Publishing the generated file (hosting it, mailing it, committing it
anywhere) is an **explicit human action**. Review the page before you share
it; the disclosure scan is a guardrail, not a substitute for review.

## Offline hosting

The file is static: any static host, internal wiki attachment, or shared
drive works. Nothing in the page phones home, and the readiness data inside
it is a snapshot of the revision named in the header — regenerate after new
commits.

## Relationship to the rest of the kit

- Reads the same shared projection as the demo proof, review integration,
  MCP governor, and passports — one disclosure-safe view, many formats.
- It renders recorded state only: it runs no validator, opens no database,
  and cannot move a stage or grant an approval.
- Optional enrichment from passports (US4) and pack metadata (US5) can be
  layered on later; the explorer is fully functional without either.
