# Live-DB provenance for readiness evidence -- design note (issue #485)

- **Date:** 2026-07-25
- **Status:** **DESIGN NOTE -- decides nothing.** Written at owner direction
  ("design note only, no code") because the fix requires a breaking schema change
  and a migration of committed readiness records. No field is added, no schema is
  edited, and no rule is wired by this note. It exists so the owner can rule on a
  concrete shape rather than on a bug report.
- **Issue:** #485 -- `seshat next` reports `terminal_pass` from committed
  `mappings/` evidence without cross-checking live DB identity.
- **Related:** #486 (rule-scope qualification), #487 (approval-shape
  qualification). All three are the same seam at different levels; see "Why this
  is the third instance" below.

## The defect, reproduced

Built offline, no database touched: a temp repo with one
`mappings/sales_c086_raw/readiness-status.yaml` at seven stages `pass` with
shape-valid approvals and evidence strings naming "Ex-1 (live)", plus `.env` and
process env pointing `ANALYTICS_DB_NAME` / `SESHAT_DBT_DBNAME` at an unrelated
database. Result:

```
outcome = terminal_pass | readiness_state = pass | caveats = []
```

The evidence is echoed verbatim. Nothing indicates the configured live DSN now
resolves to a different -- and far less complete -- database.

Reporter's field case: `bronze.sales_c086_raw` was copied into a new database
`ex-3` (bronze only, no silver/gold ever built there) and `.env` repointed. The
tool still reported all seven stages `pass`, citing the `Ex-1` evidence.

## Root cause

`terminal_pass` is decided after looping the seven stages of the committed YAML,
whose sole input is the readiness file:

- `src/seshat/run_next.py:420-422` -- returns `terminal_pass`
- `src/seshat/agent_next.py:288-306` -- `readiness_state` becomes `"pass"`
  unconditionally when `outcome == "terminal_pass"`
- `src/seshat/status_surface.py:118-138` -- `seshat status` projects the same
  YAML verbatim, same gap

There is no DB-identity comparison anywhere in this path, by design: these
modules document a no-DB/no-network contract (`agent_next.py:19-24`,
`status_surface.py:9-11`, `run_next.py:5-7`). **The bug is not that they refuse
to connect -- it is that the evidence they trust carries no machine-checkable
statement of which live system earned it.**

### No structured DB-identity field exists today

Grepped `templates/`, `schemas/`, and every committed `mappings/*`: no
`database` / `dbname` / `host` / `fingerprint` field anywhere. DB identity exists
only as free prose inside `evidence[]` -- e.g.
`mappings/retail_store_sales/readiness-status.yaml:42` reads
`"...0003_create_silver_retail_store_sales.sql applied to training; 12,575 silver
rows"`, where `training` is a database name in a sentence. Adjacent evidence
schemas do not carry it either: `dbt-run-evidence.schema.json:63`'s `target` is
`{"name": {"const": "shadow"}, "schemas": {...}}`; `dagster-run-evidence` carries
`run_id, commit_sha, workspace_dirty, tables, run_status`.

### A precision caveat, so the record is accurate

`next_allowed_action` *can* emit a `STOP ... [PENDING LIVE PROFILE]` line via
`_live_validation_next_override` (`agent_next.py:242-274`), and it did fire in the
reproduction. But that override keys on **committed-artifact / repo-revision**
identity, not database identity: `_dagster_run_states`
(`portfolio_watch.py:479-521`) checks `commit_sha`, `workspace_dirty`, input
digests, and `run_status`. With verified run evidence present it returns
`verified` and the override goes silent -- even when that evidence was produced
against a different database. `outcome`, `readiness_state`, and `evidence[]` are
never qualified on any path.

## What a fix requires (the reason this is a note, not a patch)

1. **A new structured provenance field** in `readiness-status.yaml`, recorded when
   live evidence is captured.
2. **`templates/readiness-status.yaml`** -- documents the field. (One edit covers
   the packaged copy too: `pyproject.toml:159` force-includes it as
   `seshat/stage1_templates/readiness-status.yaml` at wheel-build time.)
3. **`schemas/agent-status.schema.json`** is `additionalProperties: false`, so
   projecting the field is a **breaking** schema change, not an additive one.
4. **RS1 enforcement** (`src/seshat/rules/readiness_status.py`).
5. **Migration of committed records** -- `mappings/retail_store_sales`,
   `mappings/demo_sample_orders`, the `tests/fixtures/**` readiness files, and
   downstream consumer/fixture repos (e.g. Seshat-BI-Examples) that this repo does
   not control.

### Hard constraint: the field must not store a raw DSN

`ANALYTICS_DB_NAME` is on this repo's own secret/redaction lists
(`dagster_adapter/redaction.py:53`, `rules/git_meta.py:506,513`,
`severity_posture.py:375`). A provenance field that committed a raw host or
database name would put a redacted value into a tracked file -- trading a
correctness bug for a secret-hygiene bug. It must store a **stable, salted-or-
plain digest** (e.g. `sha256("<host>/<dbname>")`, truncated) that can be compared
without disclosing the target.

### Comparison is possible without opening a connection

Two existing helpers make a *recorded-vs-configured* check feasible while keeping
the no-DB contract intact:

- `seshat.validate.resolve_dsn(env)` (`validate.py:53-83`) -- pure env -> string,
  explicitly driver-free (`validate.py:47`)
- `seshat.connection_env.connection_environment(repo_root)`
  (`connection_env.py:105-115`) -- `.env` overlay without mutating `os.environ`

So the check reads config, never the database. Note `rules/live_surface_boundary.py`
(B3) is an *import-boundary* guard and cannot be extended for this.

## Options for the owner

**A -- Structured fingerprint field + RS1 enforcement (the real fix).**
Detects the wrong-DB case. Costs a breaking schema change and a migration this
repo cannot fully perform (downstream repos). Recommend pairing with a
grandfather ruling: records without the field report a caveat, not a failure,
until a stated date.

**B -- Non-blocking caveat only (no schema change).**
`next`/`status` always emit a caveat stating that stage evidence carries no
machine-checkable DB provenance. Honest and non-breaking, but it does **not**
detect the reporter's case -- it warns on every table equally, which risks being
tuned out. Strictly a stopgap.

**C -- Do nothing, document the limitation.**
Cheapest. Leaves an agent or analyst able to read `terminal_pass` for a database
that has none of the claimed objects, which is the specific trust failure the
readiness gate exists to prevent.

**Recommendation:** A, gated behind a grandfather ruling, with B's caveat shipped
first as the interim signal. B alone should not be treated as closing #485.

## Why this is the third instance of one seam

#485, #486, and #487 are the same architectural gap at three levels: evidence is
trusted for what it *asserts*, never qualified by *where it came from*.

- #487 -- shape level: is this approvals[] entry well-formed? (three surfaces
  disagreed; fixed by one shared predicate)
- #486 -- scope level: does this rule even apply to this repo? (substrate presence
  was mistaken for kit identity; fixed by splitting the predicate)
- #485 -- provenance level: which live system earned this evidence? (**open** --
  no field exists to answer it)

Each fix adds a *qualifier* to a fail-closed gate, and adding a qualifier can flip
currently-passing states. That is why #487's tightening was safe (a census proved
every committed entry already used `at:`) and why #485's is not (no committed
record carries provenance at all, so every one of them would newly fail).

## Governance

No hard rule is violated by the current behavior: the surfaces faithfully report
committed state and fabricate nothing. This is a **qualification gap**, not a
fabricated-readiness defect. Nothing in this note grants a stage, ratifies a
decision, or emits a confidence score.
