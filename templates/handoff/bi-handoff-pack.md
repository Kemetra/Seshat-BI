# BI Handoff Pack -- `<schema>.<table>`

> **GENERIC template -- copy this file to `mappings/<table>/handoff/bi-handoff-pack.md`**,
> fill every `<placeholder>` and index row, commit it.
> The committed documentation/evidence bundle a BI consumer receives when a
> table/report reaches **Publish Ready (stage 7)**. It COMPOSES existing readiness
> evidence -- every section points at an artifact that already exists from an earlier
> stage -- and invents nothing. The two things it ADDS are the handoff-review checklist
> (`handoff-review-checklist.md`) and a recorded publish approval. See
> `docs/readiness/publish-ready.md` (the stage authority).
>
> **Composes, never invents.** Every required section resolves to an existing committed
> artifact path. If an artifact is missing/unfilled, record the GAP -- never fabricate
> the data, a metric, or a number.
>
> **No publishing here.** This pack does NOT publish to a workspace, does NOT invoke
> the Power BI execution adapter (official Power BI MCP / connection; `pbi-cli` no
> longer preferred), and does NOT deploy to Fabric (roadmap rule #6; that is the
> deferred, gated, execution-only F016 adapter).
>
> **No fake confidence.** Readiness is the four explicit statuses + evidence + blockers.
> NO fabricated confidence/health number anywhere (roadmap rule #9).
>
> **Generic, not C086.** Placeholders only; the worked example is cited by reference,
> never inlined. ASCII only, UTF-8 no BOM; keep paths short (Windows MAX_PATH).

---

## Header

| Field | Value |
|-------|-------|
| Table / report | `<schema>.<table>` (the DEPLOYED gold star + governed model) |
| Source family | `<source_family>` |
| Assembled on | `<YYYY-MM-DD>` |
| Assembled by | `<analyst / agent>` |
| Prior-stage gate | stages 1-6 each `pass`? `<yes / NO -- list the not-pass stage(s)>` |

If any prior stage (1-6) is not `pass`, this pack CANNOT be marked complete -- record
the missing prior-stage evidence below as a blocking reason; `publish_ready` stays
`blocked` (publish-ready.md).

## Required-section index (each points at an EXISTING committed artifact)

| # | Section | Points at (existing artifact) | Resolved? |
|---|---------|-------------------------------|-----------|
| a | **Metric contracts** (stage 5, F009/F010) | `mappings/<table>/metrics/<MetricName>.yaml` (+ any pack) -- approved | `<path / GAP>` |
| b | **Readiness scorecard** | the filled `mappings/<table>/readiness-scorecard.md` | `<path / GAP>` |
| c | **Reconciliation evidence** (stage 4) | the FILLED `mappings/<table>/reconciliation-report.md` (totals tie) | `<path / GAP>` |
| d | **Known data issues / caveats** | `mappings/<table>/data-issues.md` + `assumptions.md` (composed below) | `<path / GAP>` |
| e | **Data dictionary** | against the DEPLOYED schema (below) | `<below / GAP>` |
| f | **Publish approval** | the recorded sign-off in `readiness-status.yaml` `approvals[]` (below) | `<recorded / GAP>` |

A section that points at an UNFILLED or FAIL artifact (e.g. an unfilled
`reconciliation-report.md`) is a GAP -> the pack cannot reach "complete" and the gap is
a `publish_ready` blocking reason. The pack MUST NOT edit totals or the schema to make
reconciliation "tie" -- escalate instead.

## Known data issues / caveats (MANDATORY -- all four; a missing one FAILS the checklist)

Composed from `data-issues.md` + `assumptions.md` -- recorded, never re-decided
(Principle V: PII / returns / rollup / identity are human calls carried here, not
invented).

1. **PII exclusion** -- which columns were DROPPED for PII safety (RC4) and are NOT in
   the deployed data: `<list, from source-map.yaml pii:true drops>`.
2. **Returns / refunds handling** -- how returns are identified (the AUTHORITATIVE
   billing column, RC8, never the measure sign) and what the consumer should expect:
   `<statement, citing assumptions.md>`.
3. **Known gaps** -- sourced verbatim from `data-issues.md`, WITH the measured count
   (e.g. "`<N>` rows land on the `-1` unknown member of `dim_<x>`"); never softened to
   an adjective: `<list with counts>`. (The optional interpretive source for these gaps --
   which KPI each distorts and in which direction -- is `dq-signal-interpretation.md`; the
   count itself stays sourced from `data-issues.md`.)
4. **Out of scope** -- what this deployment explicitly does NOT carry: `<list>`.

## Data dictionary (against the DEPLOYED `<schema>.<table>`)

Column-by-column, keyed to the DEPLOYED gold star + governed model (not an aspirational
design). Every deployed column appears EXACTLY once; no non-deployed column is listed
(a mismatch FAILS -- publish-ready.md). Business meaning is carried from
`source-map.yaml`, not invented at handoff.

| Column | Type | Grain role (fact measure / dim attribute / degenerate dim) | Business meaning (from source-map.yaml) |
|--------|------|-----------------------------------------------------------|-----------------------------------------|
| `<column-a>` | `<type>` | `<role>` | `<one-line meaning>` |
| `<column-b>` | `<type>` | `<role>` | `<one-line meaning>` |

## Publish approval (the one non-inherited thing the pack adds)

**This section IS the terminal publish-authorization record -- the record-and-STOP
token.** It records that a table reached publish authorization and the agent STOPS
here; it triggers nothing and crosses no automation boundary. The sign-off / owner
line below is the never-self-grant gate (Principle V -- Agent Stops at Judgment Calls):
the agent verifies the recorded approval exists and CITES it, but never self-grants it.

No automated publish today; F016 (the official Power BI MCP / connection adapter;
`pbi-cli` no longer preferred) is the deferred, gated, execution-only owner and is
verified ABSENT -- this section records authorization and STOPS.

A named, dated human sign-off authorizing publish, recorded in the table's
`readiness-status.yaml` `approvals[]` for stage `publish_ready`. The agent CANNOT
self-grant it (Principle V) -- it STOPS and requests the named owner.

```yaml
approvals:
  - stage: "publish_ready"
    owner: "<data_owner | governance>"   # the named human who authorized release
    at: "<YYYY-MM-DD>"
```

Absent approval -> `publish_ready` is `blocked` ("no recorded publish approval"); it
does NOT become `pass`.

## Readiness verdict for this pack

- `not_started` -- stage 6 (Dashboard Ready) not yet `pass`; pack not begun.
- `blocked` -- a required section is a GAP, a mandatory caveat is missing,
  reconciliation is unfilled/FAIL, the dictionary does not match the deployed schema, or
  no publish approval is recorded.
- `warning` -- pack assembled but a non-fatal gap is recorded (e.g. a caveat marked
  TBD); does NOT auto-promote to `pass`.
- `pass` -- full pack committed, handoff review done (`handoff-review-checklist.md`),
  publish approval recorded; `evidence[]` cites the pack files + the approval.

NO numeric confidence/health score is emitted (roadmap rule #9).

## See also

- The checklist that gates this pack: `handoff-review-checklist.md`.
- The stage authority: `../../docs/readiness/publish-ready.md`; the model + no-fake-
  confidence rule: `../../docs/readiness/readiness-model.md`.
- The inherited evidence: `../readiness-scorecard.md`, `../reconciliation-report.md`,
  `../data-issues.md`, `../assumptions.md`, `../source-map.yaml`, `../metric-contract.yaml`.
- The deferred publish adapter (out of scope here): roadmap F016
  (`../../docs/roadmap/roadmap.md`); Principles V, VII, VIII. For a cited filled
  instance, see a filled worked example under `../../docs/worked-examples/`.
