# Feature Specification: Extract the pure agent-driven BI kit; archive the training-data layer

**Feature Branch**: `076-extract-pure-kit`

**Created**: 2026-07-02

**Status**: Ratified (Ahmed Shaaban, 2026-07-02)

> Ratified by owner directive "ratify 076 with recommended decisions" (2026-07-02),
> adopting each ratify-ledger DEC at its recommended default: **DEC-1** package + archive
> (not a repo split); **DEC-2** current-tip redaction now + history-purge deferred to a
> public-release / erasure trigger (add the cluster id `db-pgsql-fra1-29712` + `ezaby_demo`
> + bare `c086` to the redaction); **DEC-3** narrative-only worked example + one tiny
> synthetic table; **DEC-4** the extraction PR waits for the in-flight c086 supersession
> work to resolve (now clean) before it runs. The owner reviewed and merged the spec
> (#141); the adversarial review's BLOCKER (unclassified `powerbi/` client model + false
> "no host committed") was fixed before ratify. This authorizes the FUTURE extraction PR
> (tasks.md Group B) to proceed under these decisions — it does NOT itself perform the
> extraction. Recorded per the delegated-authority pattern (cf. specs 062, 072).

**Input**: Owner directive — turn the proven-but-data-heavy training repo into a pure,
reusable, agent-driven BI kit. Keep the product layer (`src/retail/`,
`.claude/skills/`, `.seshat/kit-source.yaml`, gates, tests, the `retail
init/profile/validate/check/kit-lint/scaffold` surfaces). Classify + dispose of the
data/example layer (`mappings/*`, C086 worked examples, `warehouse/migrations`,
`ezaby_demo` traces). **SPEC ONLY — do not implement, do not delete data, do not
rewrite history, do not touch the in-flight c086 supersession work.**

> **Provenance.** Follows the session that shipped the kit (init #137, scaffold #138,
> kit-lint #139, init-diff #140) and proved it live against `ezaby_demo`. The owner
> stated the training data will be discarded and the product is "a pure tool, agent
> driven BI". This spec defines that extraction. F024 class: repo/product-structure
> change (not a Product Module; it reshapes the kit, defines no table truth).

## Overview

The repo currently holds **two intermixed layers**:

1. **The tool (product)** — `src/retail/` (47 tracked files: the CLI + rules +
   `init`/`profile`/`validate`/`compass_project`/`fence`/`kit_lint`/`scaffold`),
   `.claude/skills/` (the agent verbs), `.seshat/kit-source.yaml` + its projections,
   the gates (`retail check`/`kit-lint`), and `tests/`. **This is data-independent** —
   it references `mappings/<table>/…` as a runtime PATH CONVENTION (where it looks for
   a user's artifacts), never the specific C086 instances.
2. **The training/test data (scaffolding)** — the committed C086 instances under
   `mappings/c086`, `mappings/sales_c086`, `mappings/retail_store_sales` (64 files),
   `warehouse/migrations` + `warehouse/schema`/`gold` (10 files), `pipelines/` (3
   files), and the `docs/worked-examples/{c086-pharmacy,retail-store-sales}.md`. These
   proved the medallion playbook works; they are not part of the shippable tool.

The goal is a repo (or package) where an adopter gets the **tool + synthetic examples**
and **no client/live data** — while preserving every proven behavior. This spec
classifies each artifact, decides synthetic-vs-archive-vs-delete, chooses the
extraction strategy (one-repo-split / package / archive), and writes a migration plan +
security plan for a FUTURE implementation PR. It writes no code and moves no file.

## Load-bearing findings (grounded this session, inform the decisions)

- **No raw ROW data is committed.** `git ls-files mappings/ warehouse/` shows zero
  `.csv/.parquet/.xlsx` — the data layer is *maps, profiles, and specs ABOUT* the C086
  data, not customer records. The exposure is **client identity + schema + column names
  + business logic** (e.g. `ezaby`, `insurance_no`, `personel_number`, segment
  rollups), NOT PII rows.
- **No credential/DSN is committed, BUT a real host IDENTIFIER is** (corrected after the
  adversarial review). No password, no full DSN (PBIP uses `<your-db-host>`
  placeholders). However the real DigitalOcean cluster id **`db-pgsql-fra1-29712`** + the
  DB name **`ezaby_demo`** are committed in **7 tracked files**. This is host-identifying,
  not a secret — and it evades BOTH guards: the C2 gate's regex is FQDN-only
  (`*.db.ondigitalocean.com`) and never sees the bare cluster id; the first-draft
  acceptance grep omitted it. So the redaction target + acceptance markers now include
  the cluster id + `ezaby_demo` + bare `c086`. The security task is redacting
  *client-identifying content (name + host id + schema)*, not rotating a leaked secret.
- **History is 302 commits deep.** A history purge rewrites all 302 (breaks every
  commit hash, PR link, and any clone) — a heavyweight, irreversible-feeling operation.
  A current-tip redaction (remove/replace at HEAD) is cheap and reversible. This is the
  central security DEC (below).
- **The tool has no hard dependency on the C086 data** — only the `mappings/*/metrics/`
  and `mappings/<table>/source-map.yaml` PATH conventions. Removing the C086 instances
  does not break `src/retail/`; the conventions stay, the instances go.

## Clarifications

### Session 2026-07-02

- Q: Strategy — one-repo split, package extraction, or archive? -> A: See the
  Recommendation section; the spec RECORDS the analysis and a recommended default but
  the final strategy is a ratify decision (it is a product-structure call).
- Q: Do we delete data or rewrite history in THIS task? -> A: **NO** (owner constraint).
  This is spec-only. The migration plan describes the future PR's moves; nothing is
  moved/deleted/rewritten now.
- Q: What happens to the `mappings/` directory itself? -> A: The DIRECTORY + its
  path-convention stays (the tool scans it at runtime). The committed C086 INSTANCES in
  it are what get classified/removed. A pure repo has an empty-or-synthetic `mappings/`.
- Q: Synthetic examples — invent new data? -> A: The worked-example offer
  (`first-hour-compass`) needs SOME example to steer by. Options: (a) a small SYNTHETIC
  non-client dataset (e.g. a fictional store) authored fresh, or (b) ship the examples
  as narrative-only (structure, no client specifics). Recommended: narrative-only +
  optionally one tiny synthetic table. Decided at ratify.
- Q: The in-flight c086 supersession work? -> A: **UNTOUCHED.** It must land (or be
  discarded) by its own author FIRST; this extraction sequences AFTER it. The migration
  plan notes this ordering dependency and does not assume its state.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An adopter gets a clean, data-free kit (Priority: P1)

Someone clones/installs the kit and finds the tool + generic templates + synthetic (or
narrative) examples — and **no client name, no live schema, no `ezaby`/`c086` business
data**. `retail init` bootstraps their repo; `profile`/`validate` work against THEIR DB.

**Why this priority**: This is the whole deliverable — "pure agent-driven BI tool", not
a training repo with someone's pharmacy data baked in. It is also the security outcome
(no client data shipped).

**Independent Test**: On the post-extraction repo, grep the WHOLE tracked tree (incl.
`powerbi/`, `reports/`, `assets/`) for the client/data markers (`c086`, `ezaby`,
`ezaby_demo`, `db-pgsql-fra1-29712`, `insurance_no`, `personel_number`, `sales_c086`,
segment rollups) → zero hits outside the C2 gate's own regex, `*.example`, and
legitimately-historical `specs/`. `retail check` + `retail kit-lint` still exit 0, and
`unzip -l` on the built wheel shows no `powerbi/`/`mappings/`/`warehouse/` paths.

**Acceptance Scenarios**:

1. **Given** the post-extraction repo, **When** the tracked tree is scanned for
   client/business-data markers, **Then** there are zero hits except (a) the C2 gate's
   own detection regex and (b) generic `<placeholder>` forms.
2. **Given** the post-extraction repo, **When** `retail check`, `retail kit-lint`, and
   `pytest -m unit` run, **Then** all pass (proven behavior preserved).
3. **Given** the post-extraction repo, **When** an adopter runs `retail init`, **Then**
   it bootstraps + offers the SYNTHETIC/narrative examples (never the removed C086 data).

---

### User Story 2 - The proven behaviors survive the extraction (Priority: P1)

`retail init`, `profile`, `validate`, `check`, `kit-lint` behave exactly as they do now
after the data is removed — because they never depended on the data, only on the path
conventions + a live DB the adopter supplies.

**Why this priority**: Removing data must not regress the tool. This is the "preserve
proven behavior" constraint made testable. Same P1 — a pure-but-broken kit is worthless.

**Independent Test**: The existing unit suite (which uses tmp-repo fixtures + the
committed `.seshat/kit-source.yaml`, not the C086 data) stays green; a live smoke of
`profile`/`validate` against any Postgres still works via `.env`.

**Acceptance Scenarios**:

1. **Given** the C086 instances removed, **When** `pytest -m unit` runs, **Then** it
   passes with no test depending on a removed `mappings/c086*` artifact (any that do are
   migrated to a tmp-repo fixture or a synthetic example FIRST).
2. **Given** the extraction, **When** `retail kit-lint` runs, **Then** it still passes
   (the `.seshat/` substrate is tool, not data — it stays).
3. **Given** a live DB in `.env`, **When** `retail validate --source-map <a synthetic or
   user map>` runs, **Then** it connects and checks (the live boundary is preserved).

---

### User Story 3 - The removed data is recoverable, and the security decision is explicit (Priority: P2)

Whoever does the future implementation PR knows exactly what moved where, can recover
the archived training data if needed, and has a recorded decision on current-tip
redaction vs git-history purge.

**Why this priority**: Irreversibility risk. Deleting data without an archive, or
purging 302 commits of history without a deliberate decision, are the two ways this goes
wrong. P2 because it guards the P1 work rather than being the value itself.

**Independent Test**: The spec's migration plan names every artifact's destination
(synthetic / archive / delete) and the security section states the redact-vs-purge
decision with its trade-off; a reviewer can execute the future PR from it without
re-deciding.

**Acceptance Scenarios**:

1. **Given** the migration plan, **When** a reviewer reads it, **Then** every data
   artifact has a named destination and the archive location/method is specified.
2. **Given** the security section, **When** a reviewer reads it, **Then** the
   redact-vs-purge decision is stated with its consequence (302-commit rewrite vs
   tip-only), and a recommendation.

### Edge Cases

- **A test depends on the C086 data** → it MUST be migrated to a tmp-repo fixture or a
  synthetic example BEFORE the data is removed (US2 scenario 1); the future PR sequences
  this first.
- **The in-flight c086 supersession work is still uncommitted** when the future PR runs
  → the PR BLOCKS on it (do not extract mid-reorg); the migration plan states this
  ordering dependency.
- **`docs/` / `specs/` reference C086** → those are historical narrative (past specs
  cite the worked example); the spec decides whether they are redacted, left as
  historical record, or genericized — a per-class call, not a blanket delete.
- **The `.seshat/kit-source.yaml` version/verbs** reference nothing client-specific →
  it stays as-is (it is the tool's router, not data).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The spec MUST produce a complete CLASSIFICATION of every tracked artifact
  into exactly one of: **KEEP (tool/product)**, **SYNTHETIC (replace with non-client
  example)**, **ARCHIVE (move out of the product, recoverable)**, or **DELETE (drop; no
  value)**.
- **FR-002**: The classification MUST cover **every top-level tracked dir** (driven by
  `git ls-files | awk -F/ 'NF>1{print $1}' | sort -u`), not a hand-picked subset — at
  minimum: `src/retail/`, `.claude/skills/`, `.seshat/`, `tests/`,
  `mappings/{c086,sales_c086,retail_store_sales}`, `warehouse/{migrations,schema,gold}`,
  `pipelines/`, `docs/worked-examples/*`, any `docs/`/`specs/` C086 references, **`powerbi/`
  (a FULL client BI model lives here — `c086 _sales.*` AND the generically-named
  `Retailgold.*` which is the same c086 star), `reports/`, `assets/`, `themes/`,
  `design/`, `checklists/`, `tools/`, top-level `skills/`.** A catch-all rule
  (default KEEP unless a file matches the client-marker grep) MUST cover any dir not
  named explicitly, so NO tracked artifact is unclassified (SC-001). (The `powerbi/`
  omission was caught by the adversarial review — a generic dir name must never be
  shipped on its name alone; content decides.)
- **FR-003**: The spec MUST preserve the current proven behaviors — `retail
  init/profile/validate/check/kit-lint/scaffold` — as an explicit non-regression
  requirement, with the acceptance test (US2) that proves it.
- **FR-004**: The spec MUST decide the SYNTHETIC-example approach: narrative-only,
  a small synthetic dataset, or both — so the worked-example offer still has something
  to steer by after the client data is gone.
- **FR-005**: The spec MUST NOT delete data, move files, or rewrite git history — it is
  analysis + plan only (owner constraint).
- **FR-006**: The spec MUST NOT touch the in-flight c086 supersession work and MUST
  record the ordering dependency (extraction sequences AFTER that work resolves).
- **FR-007**: The spec MUST include a MIGRATION PLAN for the future implementation PR:
  ordered steps, per-artifact destination, test-migration-first, and a rollback note.
- **FR-008**: The spec MUST include a SECURITY section deciding **current-tip redaction
  vs git-history purge**, grounded in the findings (no row data / no leaked secret / 302
  commits), with a recommendation and its trade-off.
- **FR-009**: The spec MUST include ACCEPTANCE CRITERIA for "a clean repo with no
  client/live data committed" — a concrete, grep-able check (US1 scenario 1).
- **FR-010**: The spec MUST include an ADVERSARIAL / RISK REVIEW covering the failure
  modes (behavior regression, unrecoverable delete, history-purge blast radius,
  colliding with in-flight work, incomplete redaction).
- **FR-011**: The spec MUST end on a clear RECOMMENDATION among: **one-repo split** (tool
  + data become two repos), **package extraction** (tool becomes a pip package; repo
  keeps synthetic examples), or **archive strategy** (data archived, tool stays in a
  cleaned single repo).
- **FR-012**: This feature MUST NOT itself add a `retail check` gate rule or change the
  tool's runtime behavior (it is a structural/plan spec).

### Key Entities

- **Tool/product layer** — `src/retail/`, `.claude/skills/`, `.seshat/`, gates, `tests/`.
  Data-independent; the thing that ships.
- **Training-data layer** — `mappings/{c086,sales_c086,retail_store_sales}`,
  `warehouse/`, `pipelines/`, C086 worked examples. The thing that gets
  synthetic/archived/deleted.
- **Path convention vs instance** — `mappings/<table>/…` (a convention the tool KEEPS)
  vs the committed C086 instances in it (the data that GOES).
- **Archive target** — where removed-but-recoverable training data lands (a branch, a
  tag, a separate repo, or an out-of-tree location) — decided in the plan.
- **Redaction vs purge** — the two security postures for the already-committed
  client-identifying content.

## Success Criteria *(mandatory)*

- **SC-001**: Every artifact in FR-002's list has exactly one classification
  (KEEP/SYNTHETIC/ARCHIVE/DELETE) with a one-line rationale — no artifact unclassified.
- **SC-002**: The migration plan lets a reviewer execute the future PR without
  re-deciding any destination or ordering (a dry-run-readable runbook).
- **SC-003**: The acceptance criteria include a concrete grep/command that, run on the
  post-extraction repo, proves zero client/live-data markers outside the C2 gate regex +
  generic placeholders.
- **SC-004**: The security section states the redact-vs-purge decision + trade-off +
  recommendation, grounded in the 302-commit / no-row-data / no-leaked-secret findings.
- **SC-005**: The recommendation names one of {split, package, archive} with the reason
  it beats the other two for THIS repo's goal ("pure reusable kit").
- **SC-006**: The spec writes no code, moves no file, rewrites no history, and does not
  touch the in-flight c086 work (a `git status` after the spec task shows only the new
  `specs/076-*` files).
- **SC-007**: The non-regression requirement (US2) is testable: the plan names the exact
  commands (`retail check`, `retail kit-lint`, `pytest -m unit`, a live `profile`/
  `validate` smoke) that must stay green post-extraction.

## Assumptions

- The tool layer (`src/retail/` etc.) is genuinely data-independent (verified: no hard
  dependency on the C086 instances, only path conventions).
- No raw customer rows are committed (verified); the security scope is
  client-identifying schema/business content, not PII data.
- The live DSN stays in the gitignored `.env`; the pure kit ships no DSN.
- The in-flight c086 supersession work will resolve (land or be discarded) before the
  extraction PR runs.
- This feature advances NO readiness stage and takes NO roadmap F-row (a
  product-structure change), matching the 070-074 kit-infra slices.
