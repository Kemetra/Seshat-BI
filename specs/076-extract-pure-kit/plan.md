# Implementation Plan: Extract the pure agent-driven BI kit

**Branch**: `076-extract-pure-kit` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/076-extract-pure-kit/spec.md`

## Summary

Define (not execute) the extraction of the data-independent tool layer into a pure,
reusable agent-driven BI kit, disposing of the training-data layer. This plan carries
the artifact CLASSIFICATION, the three-strategy comparison + RECOMMENDATION, the
MIGRATION PLAN for a future PR, the SECURITY decision (tip-redaction vs history-purge),
and the ACCEPTANCE CRITERIA. It writes no code, moves no file, rewrites no history, and
does not touch the in-flight c086 supersession work (owner constraints, FR-005/006).

## Technical Context

**Language/Version**: N/A for this spec (analysis + plan). The tool it describes is
Python 3.13 (`src/retail/`), stdlib-only core + lazy pyyaml in the yaml-parsing steps.

**Primary Dependencies**: None introduced. The plan reasons about existing structure.

**Storage**: N/A — no writes beyond the `specs/076-*` docs.

**Testing**: The plan NAMES the non-regression gate the future PR must keep green
(`retail check`, `retail kit-lint`, `pytest -m unit`, a live `profile`/`validate`
smoke); it runs none destructively here.

**Target Platform**: The extracted kit targets any repo an adopter runs `retail init`
in, against any Postgres via `.env`.

**Project Type**: Product-structure / repo-topology change (spec-only).

**Constraints**: spec-only (FR-005); do not touch in-flight c086 work (FR-006); preserve
proven behavior (FR-003); no new gate rule / no runtime change (FR-012).

**Scale/Scope**: Classifies ~64 `mappings/` + 10 `warehouse/` + 3 `pipelines/` + 2
worked-example files against the 47-file tool layer. Output is docs only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS. The plan reshapes the kit so the
  agent-first tool ships clean; it changes no gate behavior and self-grants nothing.
- **Principle V (Agent Stops at Judgment Calls)**: PASS. The extraction STRATEGY
  (split/package/archive) and the redact-vs-purge SECURITY posture are recorded as
  RATIFY decisions with a recommendation — not auto-chosen. Deleting data / rewriting
  history are explicitly deferred to a human-authorized future PR (FR-005).
- **Principle VII (C086 Is An Example, Not The Schema)**: PASS — and this feature
  OPERATIONALIZES it: the whole point is that C086 was always an example, now removed
  from the shippable product so the kit is generic.
- **Principle VIII (Static-First Governance)**: PASS. No runtime/DB change; the plan is
  static analysis. The gates it names stay stdlib-only.
- **Principle IX (Secrets / Reproducibility / Windows-safe)**: PASS — CENTRAL here. The
  security section makes the "no client/live data committed" outcome explicit + testable,
  reinforcing the `.env`-only + C2/G6 posture rather than weakening it.
- **Hard rule #8 (templates/docs first, automate after artifacts prove useful)**: PASS.
  The tool is proven (shipped + live-validated); extracting it into a reusable kit is the
  natural next structural step, and this is the docs-first spec of that step.
- **Hard rule #9 (no fabricated confidence score)**: PASS. Classification is
  categorical (KEEP/SYNTHETIC/ARCHIVE/DELETE); no numeric score.
- **Anti-fork / single-source**: PASS. The plan REMOVES the intermixing (tool vs data)
  rather than duplicating anything; the `.seshat/kit-source.yaml` single source stays.
- **In-flight-work safety**: PASS. Explicitly sequences AFTER the c086 supersession work
  and touches none of it (FR-006, SC-006).
- **Readiness spine**: PASS. Advances no readiness stage; a product-structure change.

No violations. No complexity-tracking entries required.

## Artifact classification (FR-001/002 — SC-001)

Every listed artifact → exactly one of KEEP / SYNTHETIC / ARCHIVE / DELETE.

| Artifact | Class | Rationale |
|----------|-------|-----------|
| `src/retail/**` (47 files) | **KEEP** | The tool. Data-independent (only path conventions). |
| `.claude/skills/**` | **KEEP** | The agent verbs (init, onboard, govern, scaffold, kit-lint, …). Generic. |
| `.seshat/kit-source.yaml` + projections | **KEEP** | The kit router / single source. No client content. |
| `tests/**` | **KEEP** (migrate data-coupled tests first) | The suite. Any test reading a C086 instance → re-point to a tmp fixture / synthetic BEFORE removal. |
| gates (`.pre-commit-config`, `.github/workflows/ci.yml`) | **KEEP** | The commit/PR enforcement. Generic. |
| `templates/**` | **KEEP** | Generic artifact templates (already placeholder-only). |
| `docs/` core (readiness, conventions, glossary, roadmap, architecture) | **KEEP** | Tool doctrine; genericize any C086 mentions to placeholders (per-file). |
| `docs/worked-examples/c086-pharmacy.md` | **SYNTHETIC** or **ARCHIVE** | Replace with a synthetic/narrative example, OR archive as reference. The kit needs SOME worked example for `first-hour-compass`; it must not be client data. |
| `docs/worked-examples/retail-store-sales.md` | **KEEP-if-synthetic / else SYNTHETIC** | Check if it is already generic (fictional store) — if so KEEP; if it carries client specifics, synthesize. |
| `mappings/c086/**` | **ARCHIVE** then **DELETE from product** | Superseded first build + client data. Archive (recoverable), remove from the shipped tree. |
| `mappings/sales_c086/**` | **ARCHIVE** then **DELETE from product** | The approved C086 client map. Real business data; archive, remove from product. |
| `mappings/retail_store_sales/**` | **ASSESS → SYNTHETIC or ARCHIVE** | If it is already a synthetic/fictional example, promote to the shipped SYNTHETIC example; if client-derived, archive. (One assess step in the migration.) |
| `mappings/` directory + `mappings/README.md` | **KEEP (empty/synthetic)** | The runtime path convention stays; ship it empty or with one synthetic table + a README explaining the convention. |
| `warehouse/migrations/**` (0001-0006) | **ARCHIVE** | The C086 silver/gold build SQL — client business logic. Archive; not part of the generic tool. |
| `warehouse/schema/`, `warehouse/gold/` | **ASSESS → ARCHIVE or KEEP-if-generic** | Keep only genuinely generic schema conventions; archive C086-specific DDL. |
| `pipelines/load_bronze.py` + `pipelines/README.md` | **ASSESS → ARCHIVE or SYNTHETIC** | If C086-specific ingestion → ARCHIVE (YAGNI per CLAUDE.md anyway); if a generic loader pattern → KEEP/genericize. |
| `docs/` / `specs/` historical C086 references | **KEEP as historical record** (genericize only the shipped-facing ones) | Past specs legitimately cite the worked example; they are history, not shipped product. The security section decides redaction depth. |
| **`powerbi/c086 _sales.Report` + `.SemanticModel`** | **ARCHIVE** then **DELETE from product** | A FULL client BI deliverable (5-page report + the c086 star: `dim_customer`/`dim_salesperson`/`dim_branch`/`fct_sales` + measures). Client data — archive, remove from product. (Caught by the adversarial review; the bare-`c086` dir name evaded the first grep.) |
| **`powerbi/Retailgold.Report` + `.SemanticModel`** | **ASSESS → almost certainly ARCHIVE** | The SAME c086 schema under a GENERIC-looking name (`dim_billing_type`/`dim_branch`/`dim_salesperson`/`fct_sales`) — evades a c086-name filter. Verify it is the c086 model; if so ARCHIVE+remove. Do NOT ship on the strength of a generic name. |
| **`powerbi/RetailStoreSales.Report` + `.SemanticModel`** | **ASSESS → SYNTHETIC-KEEP or ARCHIVE** | The retail-store-sales example model; KEEP as the shipped synthetic example only if it is genuinely fictional/generic, else ARCHIVE. Same assess rule as `mappings/retail_store_sales/`. |
| **`reports/`, `assets/`, `themes/`, `design/`, `checklists/`, `tools/`, top-level `skills/`** | **ASSESS (default KEEP) → per the catch-all rule** | Mostly generic tool/doc assets; classify each via the catch-all below (KEEP unless it matches the client-marker grep, then ARCHIVE/redact). One known hit: `skills/bi-python-knowledge/knowledge/file-source-grain.md` carried a client marker → redact. |
| `docs/` / `specs/` historical C086 references | (as above) | (as above) |
| `.env` (untracked) | **N/A** | Already gitignored; ships nothing. |

> **Catch-all (FR-001 completeness):** every top-level tracked dir is
> `git ls-files | awk -F/ 'NF>1{print $1}' | sort -u` → {`.claude`, `.github`, `.seshat`,
> `.specify`, `.superpowers`, `assets`, `checklists`, `design`, `docs`, `mappings`,
> `pipelines`, `powerbi`, `reports`, `skills`, `specs`, `src`, `templates`, `tests`,
> `themes`, `tools`, `warehouse`}. Default class = **KEEP**, EXCEPT any file matching the
> client-marker grep (below) → **ARCHIVE / redact**. The named rows above are the
> non-default cases. No tracked dir is left unclassified (SC-001).

> The **ASSESS** rows (the three `mappings`/`warehouse`/`pipelines` originals + the two
> `powerbi/` non-c086-named projects + the catch-all dirs) are the per-file judgment left;
> the migration plan makes "assess then classify" its first step so nothing is removed
> before it is classified, and nothing generic-NAMED is shipped without a content check.

## Strategy comparison + RECOMMENDATION (FR-011 — SC-005)

| Strategy | What it is | Pro | Con |
|----------|-----------|-----|-----|
| **A. One-repo split** | Tool → new `seshat-kit` repo; data → archived `seshat-training` repo | Cleanest separation; product repo is born pure | Two repos to maintain; loses the single-repo history; heaviest move |
| **B. Package extraction** | Tool becomes the shipped pip package (already is — `packages=["src/retail"]`); the repo keeps tool + SYNTHETIC examples, data removed/archived in-place | Smallest change; the package ALREADY excludes the data (wheel = `src/retail` only); `retail init` distributes the kit into any repo — the distribution model already designed (`distribution-ideas.md`) | The source repo still needs cleaning (data removed from the tree + history decision) |
| **C. Archive strategy** | Data moved to an archive branch/tag; single repo cleaned in place; tool stays | Simple; recoverable; one repo | The repo's IDENTITY stays "the Seshat repo" rather than a clean product; history still carries the data unless purged |

**RECOMMENDATION: B (package extraction) + C (archive) combined — NOT a repo split.**

Reason: the tool is ALREADY a clean pip package (`pyproject.toml` packages only
`src/retail`; the wheel already contains zero client data — verified). So "extract the
pure tool" is largely *already true at the package boundary*; what remains is cleaning
the SOURCE TREE + deciding history. That is Strategy C (archive the data out of the
working tree) layered on the existing package (Strategy B). A full repo split (A) is
heavier than the goal needs — the package boundary already gives adopters a pure kit via
`pip install` + `retail init`. Split only if the training repo must live on
independently as its own maintained thing (a call the owner can make later; not required
for "pure reusable kit").

## Migration plan for the FUTURE implementation PR (FR-007 — SC-002)

Ordered, dry-run-readable. **Precondition: the in-flight c086 supersession work has
landed or been discarded (FR-006). Do not start otherwise.**

1. **Assess the three ASSESS rows** (`retail_store_sales`, `warehouse/schema|gold`,
   `pipelines/`) → finalize each as SYNTHETIC / ARCHIVE / KEEP with a one-line reason.
2. **Migrate data-coupled tests FIRST** — grep `tests/` for any read of a `mappings/c086*`
   / `warehouse/` artifact; re-point to a tmp-repo fixture or a synthetic example. Suite
   green BEFORE any data removal (US2 scenario 1).
3. **Author the SYNTHETIC example** (per FR-004 decision) — a small fictional dataset or
   narrative-only worked example so `first-hour-compass` still has something to offer.
4. **Archive the data** — move `mappings/{c086,sales_c086}` + `warehouse/migrations` +
   any ARCHIVE-classed items to the chosen archive target (branch/tag/out-of-tree);
   record the archive ref in the PR.
5. **Remove from the product tree** — delete the archived instances from `main`'s working
   tree (NOT history in this PR — history is the separate security decision below). Leave
   `mappings/` as the empty/synthetic convention dir + README.
6. **Genericize shipped-facing docs** — replace client specifics in
   `docs/worked-examples` + any shipped doc with placeholders/synthetic.
7. **Run the non-regression gate** — `retail check` + `retail kit-lint` + `pytest -m unit`
   + a live `profile`/`validate` smoke → all green (US2).
8. **Run the acceptance grep** (below) → zero client-data hits.
9. **Rollback note**: the whole PR is a working-tree change on a branch; revert = restore
   from the archive ref. No history rewrite in this PR, so rollback is a normal git
   revert.

## Security: current-tip redaction vs git-history purge (FR-008 — SC-004)

**Findings that scope this:** no raw customer rows are committed (only maps/specs about
the data); no live DSN/**credential** is committed. BUT — correcting an earlier draft
(caught by the adversarial review) — a **real DigitalOcean cluster identifier
`db-pgsql-fra1-29712` + the DB name `ezaby_demo` ARE committed** in 7 tracked files
(`docs/c086-adr0002-compliance.md`, both `docs/worked-examples/*.md`,
`mappings/c086/reconciliation-report.md`, `mappings/{sales_c086/analysis.md,
sales_c086/reconciliation-report.md}`, `mappings/retail_store_sales/reconciliation-bronze-to-gold.md`).
That is **host-identifying, not a secret** (no password, no full DSN — the PBIP connection
strings use `<your-db-host>` placeholders). It evades BOTH guards: the C2 gate's
`DO_ENDPOINT_RE` matches only the FQDN form `*.db.ondigitalocean.com`, not the bare
cluster ID; and the first-draft acceptance grep omitted it. So the cluster ID +
`ezaby_demo` are **added to the redaction target list and the acceptance markers** below.
History is **302 commits** deep.

- **Current-tip redaction (remove from HEAD):** the data leaves the shipped/working tree;
  it REMAINS in git history (reachable by `git log`/checkout of old commits). Cheap,
  reversible, breaks nothing. Adequate when the exposure is client-identifying
  schema/business content (not live secrets/PII rows) and the repo's distribution is the
  PACKAGE (which never contained the data) + a cleaned tip.
- **Git-history purge (`git filter-repo`):** removes the data from ALL 302 commits.
  Rewrites every hash → breaks all PR links, forces every clone to re-clone, and is
  effectively irreversible. Warranted ONLY if a hard requirement says the client's name /
  schema must not exist ANYWHERE in history (e.g. the repo goes public, or a
  contractual/GDPR erasure obligation).

**RECOMMENDATION: current-tip redaction now; purge ONLY if the repo will be made public
or a contractual erasure requires it.** Rationale: the committed exposure is
client-identifying business content, not secrets or PII rows; the shippable artifact (the
pip package) never carried it; and a 302-commit rewrite is a blast-radius cost that the
current (private) distribution does not require. Record the purge as a SEPARATE, explicitly
owner-authorized operation if/when the trigger (public release / erasure demand) occurs —
never bundled into the extraction PR.

## Acceptance criteria — "clean repo, no client/live data" (FR-009 — SC-003)

A future-PR reviewer runs, on the post-extraction tip:

```bash
# 1. No client/business-data markers ANYWHERE in the tracked tree (TREE-WIDE; incl.
#    powerbi/, reports/, assets/). Markers cover bare `c086`, the client name, the DO
#    cluster id + db name, and the schema/PII tokens. Excludes only the C2 gate's own
#    regex, *.example, and legitimately-historical specs/ (documented exclusions):
git grep -nI \
  -e "c086" -e "ezaby" -e "ezaby_demo" -e "db-pgsql-fra1-29712" \
  -e "insurance_no" -e "personel_number" -e "sales_c086" \
  -- ':!src/retail/rules/git_meta.py' ':!*.example' ':!specs/*'   # -> expect: no output
# 2. No committed DSN/host (the C2 gate + the marker grep above; note the C2 regex is
#    FQDN-only, so the marker grep is what catches the bare cluster id):
retail check --repo .            # -> exit 0
# 3. Proven behavior intact:
retail kit-lint --repo .         # -> exit 0
pytest -m unit                   # -> all pass
# 4. The wheel carries only the tool (no data dirs, incl. powerbi/):
python -m build && unzip -l dist/*.whl \
  | grep -c "mappings/\|warehouse/\|powerbi/\|pipelines/\|ezaby\|c086"   # -> 0
```

Green on all four = a clean, pure kit with proven behavior preserved. (The bare-`c086`
marker is what catches the `powerbi/c086 _sales.*` dir the first-draft grep missed; the
cluster-id marker is what catches the host the C2 FQDN regex can't see.)

## Project Structure

### Documentation (this feature)

```text
specs/076-extract-pure-kit/
├── plan.md              # This file (classification, strategy, migration, security)
├── research.md          # Phase 0 (strategy + security deep-dive; the ASSESS-row method)
├── tasks.md             # Phase 2 (the SPEC deliverables as tasks; NOT impl tasks)
├── risk-review.md       # the adversarial / risk review (FR-010)
└── ratify-ledger.md     # STOP for the human strategy + security decision
```

**Structure Decision**: This feature produces DOCS only. No `src/` or repo-tree change.
The implementation it describes is a SEPARATE future PR, gated on ratify + on the
in-flight c086 work resolving.

## Complexity Tracking

> No Constitution Check violations. No entries required.
