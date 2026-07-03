# Data Model: Worked-Example Factory

**Feature**: `specs/084-worked-example-factory/` | **Phase**: 1 (design)

This is a documentation feature; there is no database schema or API payload.
"Data model" here means the **artifact set** a worked example comprises -- the
entities the factory process and its completeness contract reason about. Every
artifact cites an existing template; this feature defines none new.

## Entity: Worked-Example Candidate

A domain not yet built, under consideration for the next worked example.

| Field | Meaning | Source of truth |
|-------|---------|------------------|
| `domain_name` | Short label (e.g. "inventory", "customer loyalty") | Author's choice; illustrative only in this feature |
| `genericity_axes_stressed` | Which axes it varies vs. existing examples (returns, PII, language, rollups, source shape) | `research.md` Sec 1 selection rule |
| `expressible_with_existing_defaults` | Whether RC1-RC16 + the current `retail check` rule set can model it without a new default/rule | Author judgment at profiling time; if "no", the domain is deferred (spec.md FR-012) |

This entity exists only in an author's head / a future ADR-style note when a
domain is actually chosen -- this feature defines the *fields that matter*, not
a template file for it (there is no `templates/candidate-domain.md`; adding one
is out of scope, see plan.md Complexity Tracking).

## Entity: Worked-Example Artifact Set

The concrete, committed files one complete worked example comprises. This is
the artifact inventory retail_store_sales already instantiates; the factory
process is "produce one of these per new table," nothing more.

| # | Artifact | Template it fills | Committed location (pattern) | Produced during (readiness stage) |
|---|----------|--------------------|-------------------------------|-------------------------------------|
| 1 | Source profile | `templates/source-profile.md` | `mappings/<table>/source-profile.md` | Source Ready |
| 2 | Source map | `templates/source-map.yaml` | `mappings/<table>/source-map.yaml` | Mapping Ready |
| 3 | Assumptions (defaults vs. deviations) | `templates/assumptions.md` | `mappings/<table>/assumptions.md` | Mapping Ready |
| 4 | Unresolved questions | `templates/unresolved-questions.md` | `mappings/<table>/unresolved-questions.md` | Mapping Ready |
| 5 | Reconciliation report | `templates/reconciliation-report.md` | `mappings/<table>/reconciliation-report.md` | Gold Ready (filled after a live run) |
| 6 | Silver migration | (SQL, no template; follows `docs/medallion-playbook.md` + RC13) | `warehouse/migrations/NNNN_create_silver_<table>.sql` | Silver Ready |
| 7 | Gold migration | (SQL, no template; follows RC14/RC15) | `warehouse/migrations/NNNN_create_gold_<table>_star.sql` | Gold Ready |
| 8 | Metric contracts | `templates/metric-contract.yaml` | `mappings/<table>/metrics/*.yaml` | Semantic Model Ready |
| 9 | Governed semantic model | (PBIP/TMDL, no single template; follows Power BI policy in README) | `powerbi/<Table>.SemanticModel/` | Semantic Model Ready |
| 10 | Dashboard design set | `templates/dashboard-layout.md`, implied visual-list/binding-map shape | `mappings/<table>/design/` | Dashboard Ready |
| 11 | Handoff pack | `templates/handoff/` set | `mappings/<table>/handoff/` | Publish Ready |
| 12 | Readiness status | `templates/readiness-status.yaml` | `mappings/<table>/readiness-status.yaml` | tracked throughout, all 7 stages |
| 13 | Narrative worked-example doc | Section structure of `docs/worked-examples/retail-store-sales.md` (no separate blank template exists; this doc's structure IS the template, per its own "How to reuse this" section) | `docs/worked-examples/<table>.md` | authored last, summarizing 1-12 |
| 14 | Index registration | one row added | `docs/worked-examples/README.md` "The examples" table | authored alongside 13 |

**Note on item 13**: `docs/worked-examples/retail-store-sales.md` itself states
"copy this section structure" (its own header) and `docs/worked-examples/
README.md` "How to reuse it" confirms this -- there is deliberately no separate
`templates/worked-example-narrative.md` blank. This feature's completeness
contract (`contracts/worked-example-completeness.md`) treats the *existing
filled doc's section structure* as the template for item 13, rather than
proposing a new template file (keeps this feature docs-only, adds no new
`templates/*` file -- a Complexity-Tracking-relevant choice, see plan.md).

## Entity: Completeness Tier

A classification of how far a given worked example has progressed, applied
per-item against the artifact set above. See `contracts/worked-example-
completeness.md` for the full checklist; summarized here as the two tiers
`research.md` Sec 5 derived:

| Tier | What it requires | What it explicitly does NOT require |
|------|-------------------|--------------------------------------|
| `repo-only` | Artifacts 1-4, 6-8, 10, 12 (partial), 13, 14 authored; internally consistent (e.g. `assumptions.md` deviations match `source-map.yaml`); `retail check` exit 0 over the new files; every live-gated stage in artifact 12 marked `blocked` or evidenced `[PENDING LIVE PROFILE]`, never a fabricated `pass` | Any `approvals[]` entry; artifact 5 filled with real numbers; artifact 9's live semantic-check; a live `retail validate` run |
| `human/live-gated` | All of `repo-only`, plus: artifact 5 filled from a real live run; the four always-required named-human `approvals[]` entries (Mapping Ready, Semantic Model Ready, Dashboard Ready, Publish Ready) -- plus a fifth, conditional Source Ready entry for a file (csv/excel) source, per `templates/readiness-status.yaml` -- each recorded by a named person; `retail validate` exit 0 | -- (this is the full bar; matches retail_store_sales' own achieved state through Dashboard Ready) |

A factory process run by an agent with no live DB and no human reviewer present
can only ever produce `repo-only` -- this is stated as a hard limit, not a goal
to eventually automate around (spec.md FR-004, Human-Approval Boundaries).

## Entity: Maturity Rung (referenced, not owned by this feature)

Already fully defined in `templates/maturity-report.md` (L0-L6, binary
evidence-gated). This feature's only relationship to it: completing a second
worked example under this process is the specific evidence the L2 (and,
if Gold Ready is reached, L3) binary test checks for. This feature does not
add, redefine, or number a rung.

## Relationships

```text
Worked-Example Candidate  --(if selected + built)-->  Worked-Example Artifact Set
Worked-Example Artifact Set  --(scored against)-->  Completeness Tier (repo-only | human/live-gated)
Completeness Tier = human/live-gated for >=2 examples  --(is evidence for)-->  Maturity Rung L2 (and L3 if Gold Ready)
```

No entity in this feature is mutable state this spec chain writes to -- all of
the above describe artifacts a *future* worked-example-building effort would
create. This spec chain creates none of them (spec.md Non-Goals, FR-011).
