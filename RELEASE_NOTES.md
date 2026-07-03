# Seshat BI Release Notes

## v0.1.0 - Release readiness snapshot

This is the first tagged **release-readiness snapshot** of Seshat BI. It does not
add new behaviour. It turns the current `main` into a state a new user can read,
verify locally, and pick up as a downloadable kit.

### What v0.1 contains

v0.1 is the governance kit that is already on `main`, captured as a coherent
snapshot:

- The **seven-stage readiness spine** (Source Ready -> Mapping Ready -> Silver
  Ready -> Gold Ready -> Semantic Model Ready -> Dashboard Ready -> Publish
  Ready), where each stage is a gate that the next stage cannot skip.
- The **source-mapping gate**: no `silver.*` SQL is written until a table's
  `source-map.yaml` has been reviewed.
- **Medallion warehouse conventions** (`bronze` -> `silver` -> `gold`), with
  Power BI reading `gold` only.
- The `retail` CLI surfaces:
  - `retail check` -- the static governance gate over committed SQL, TMDL/PBIR,
    config, and repo text (the exit code is the authority).
  - `retail validate` -- live data checks against a materialized table (requires
    a database).
  - `retail semantic-check` -- contract-vs-measure drift detection.
  - `retail value-check` -- value-proxy check of a live aggregate against an
    owner-approved expected value (requires a database).
  - `retail generate` -- a verified best-practice DAX measure from an approved
    metric contract.
- The **SQL**, **DAX**, and **Python** knowledge layers that the agent routes
  through.
- One worked example, **retail_store_sales**
  (`docs/worked-examples/retail-store-sales.md`), the domain that traverses the
  full spine to Dashboard Ready with Publish Ready honestly at `warning`. An
  earlier client-specific (C086) example was archived out of the kit so that
  the shipped example stays generic, not tied to one client's schema.
- **Power BI / PBIP governance and handoff** conventions (plain-text TMDL/PBIR,
  handoff packs, gold-only reads).

### How Seshat BI should be understood

Seshat BI is an **agent-first Retail BI readiness system**. It answers one
question safely: *is this retail source ready to become trusted Power BI
analytics?* Readiness is never a faked confidence score -- it is
`status` + `evidence` + `blocking_reasons`, held by a gate.

- **Power BI is a reporting target, not the source of truth.** The warehouse
  (medallion `gold`) is the source of truth; Power BI reads `gold` only.
- **The product is the readiness system** -- the gates, contracts, examples, and
  agent workflow -- not Power BI automation.
- The current CLI / package alias is **`retail`** (see `pyproject.toml`).

### What is intentionally not included yet

These are deliberately deferred or human-gated, not missing through neglect:

- **F016 -- Power BI execution adapter.** Execution-only, deferred by design; not
  startable before `semantic_model_ready` is `pass`.
- **One-click dashboard generation.** Seshat BI is not an automatic dashboard
  generator; dashboards are designed from approved metric contracts.
- **Automated ingestion / live DB provisioning.** Manual load now; no automated
  feed shipped.
- **Fully automated mapping approval.** The mapping gate requires human review.

### How to verify locally

From a clean checkout with Python 3.13:

```bash
pip install -e ".[dev]"
ruff format --check src tests
ruff check src tests
pytest -m unit
retail check
retail semantic-check --repo .
```

> [!NOTE]
> On the current `main`, `retail check` exits `1` because its P2 rule scans the
> recent commit range (`HEAD~20..HEAD`) and flags two pre-existing nonconforming
> commit subjects (#48, #42) that predate this release -- a known, recorded
> condition, not a regression from this pack. The other surfaces above exit
> cleanly. (`HEAD~20..HEAD` is the local fallback range; CI passes an explicit
> `--commit-range`, so it scopes to the PR's own commits.) See
> [`docs/quality/local-verification.md`](docs/quality/local-verification.md).
>
> **Update (#112):** the local fallback was later narrowed to `HEAD~1..HEAD`
> (current commit only); a bare `retail check` on a compliant HEAD now exits
> cleanly and no longer surfaces those aged-out subjects. CI/commit-msg P2
> enforcement is unchanged. Note retained as the release-time record.

A full local-verification checklist (including the optional DB/live path) is in
[`docs/quality/local-verification.md`](docs/quality/local-verification.md).

### Honesty note

- **GitHub Actions status must not be claimed unless it is visible.** Do not state
  that CI is green unless a successful run is actually shown in GitHub Actions.
- **Live validation must not be claimed unless it was run against a real
  database.** Without a DB, `retail validate` and `retail value-check` are
  *pending*, not *passed*. The kit never fakes a pass.
