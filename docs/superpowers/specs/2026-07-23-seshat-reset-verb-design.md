# Design brief — `seshat reset <table>` verb (issue #433)

**Status:** Draft design — NOT ratified, NOT specced, NOT implemented.
**Owner gate:** This is a **net-new CLI verb**. Per the project constitution's
CLI-surface sensitivity and the `ask-before-firing-plan-workflow` rule, this brief
STOPS at the design stage. The owner fires the Spec-Kit chain (`idea-to-spec`) when
ready; nothing here authorizes building the verb.

**Anchors the reset-lifecycle cluster:** #430 (check crash on unstaged deletions —
fixed separately in this batch), #431 (dbt layout collision — guarded separately),
#439 (interim reset docs — shipped in this batch as the manual workaround this verb
will eventually replace).

---

## 1. Problem

Resetting a completed table back to a fresh **Source** stage today requires manually
deleting the correct derived file-set. Only the engine knows the full set (mappings +
warehouse silver/gold SQL + `dbt/models/**/<table>/` + dbt-evidence + the materialized
dagster project). An **incomplete** manual reset is the documented root of:

- **#430** — a leftover deleted-but-unstaged file crashes `seshat check`.
- **#431** — a surviving flat-layout dbt model collides with the new nested scaffold.

So the reset must be **complete** (removes the whole derived set) and **atomic**
(all-or-nothing; a partial reset is the failure mode we are eliminating), and it must
leave the workspace in a truthful state: `seshat next` reports a fresh Source stage.

## 2. Scope (YAGNI)

**In scope:** `seshat reset <table>` — remove the complete DERIVED file-set for one
table, PRESERVE the bronze landing (raw CSV / already-loaded bronze), stage the
deletions, and leave a truthful fresh-Source readiness state.

**Explicitly out of scope:** no live DB mutation (never drops `bronze.<table>`,
`silver.*`, or `gold.*` in Postgres — reset is a *file-tree* operation only; the DB
is the user's to reset); no multi-table / portfolio reset; no undo/restore (git is the
safety net — the staged deletions are recoverable via `git restore --staged` +
`git checkout`); no "reset to an intermediate stage" (only full → fresh Source).

## 3. The derived file-set (verified against the repo, 2026-07-23)

Reset REMOVES (all `<table>`-scoped, PRESERVING bronze landing):

| Path | Notes |
|---|---|
| `mappings/<table>/` | the five mapping artifacts **and** its nested `dbt-evidence/` subfolder (evidence lands at `mappings/<table>/dbt-evidence/`, per `dbt/evidence.py`) |
| the silver DDL migration(s) for `<table>` | matched by the FULL token `_create_silver_<table>` followed by `_` or `.` — NOT a prefix glob (see the prefix-collision guard below) |
| the gold DDL migration(s) for `<table>` | matched the same exact-token way (`_create_gold_<table>` + `_`/`.`) |
| generated `warehouse/gold/`, `warehouse/schema/` outputs for `<table>` | build artifacts, if present |
| `dbt/models/staging/<table>/`, `dbt/models/marts/<table>/`, `dbt/models/audit/<table>/` | nested dbt models |
| the materialized dagster project under `orchestration/dagster/` | regenerable via `seshat dagster init` — see open question Q2 |

Reset PRESERVES:

- the bronze landing file `data/raw/<table>.csv` (or `SESHAT_RAW_LANDING_DIR/<table>.csv`) — reset returns you to Source, which *has* a landed source.
- everything for OTHER tables (shared dbt files like `sources.yml` must have only the
  `<table>` rows removed, not the whole file — see open question Q1).

**Prefix-collision guard (load-bearing):** the migration file-set MUST be resolved by an
exact-token match (`_create_(silver|gold)_<table>` bounded by `_` or `.`), never a bare
`<table>*` glob. When one table id prefixes another (`orders` vs `orders_archive`), a
prefix glob would sweep the OTHER table's migrations and the staging step would then
delete unrelated data. The planner enumerates candidate paths and drops any whose
table-token isn't an exact match.

Reset must also **verify/repair residual state — but NOT via `.seshat/manifest.yaml`.**
That manifest records the kit's integrity fingerprint (kit-source / compass / integration
receipts), NOT onboarded tables, so it never references a table and is a false clean-state
signal. Truthful verification inspects the actual artifacts: `mappings/<table>/` absent, no
exact-token `<table>` migration remains, the three `dbt/models/*/<table>/` folders gone,
and the shared dbt files (`dbt/models/sources/_sources.yml`, `dbt/selectors.yml`) carry no
rows for this table. The verb confirms `seshat next --table <table>` reports a fresh Source
stage (the `--table` scope is required — without it `next` reports the portfolio's most
urgent OTHER table, not the reset one).

## 4. Architecture

Reuse the *inverse* machinery already in `stage1_scaffold.py` (which creates the
mapping working set):

- **Table-name validation** — reuse `_validate_table` / `_is_unsafe_table`
  (rejects path separators, control chars, Windows-reserved names) so `reset ../../etc`
  or `reset foo/bar` fails closed, never `rm`-s outside the intended dir.
- **Containment guard** — reuse the `_guard_destination_within_root` idiom so every
  path removed resolves strictly under `--repo` (symlink-escape safe).
- **A pure planner + an executor** (mirrors the dbt-scaffold split): `plan_reset(root,
  table) -> ResetPlan` enumerates the exact paths (pure, testable, no I/O), and
  `execute_reset(plan)` performs the removals + `git add -A` staging (I/O). This keeps
  the "which files" logic unit-testable without touching disk.
- **Atomicity** — plan the FULL set first; if any removal fails midway, the operation
  must not leave a half-reset tree. Because these are deletions, "atomic" means:
  validate the whole plan is removable (paths exist, are under root, are not symlinked
  escapes) BEFORE removing anything; on a mid-removal OS error, report which paths were
  already removed so the operator can complete via git. (A true transaction over a
  filesystem is out of scope; the git-staging safety net + pre-validation is the
  pragmatic guarantee.)

## 5. Fail-closed / governance posture

- Reset never touches a live database.
- Reset **stages** the deletions (`git add -A` the removed paths) — this is the #430
  workaround made native (staged deletions drop out of `git ls-files`, so `seshat
  check` runs clean afterward).
- Reset does NOT self-grant any approval or advance readiness forward; it only tears a
  table back to Source. It is a destructive-to-derived-files operation, so it prints
  the exact plan and requires confirmation (`--yes` to skip in automation), matching
  the confirm-before-irreversible norm.
- Dry-run: `seshat reset <table> --dry-run` prints the plan and exits 0 without
  removing anything (the safe default for a first look).

## 6. Testing strategy

- **Planner unit tests** (no I/O): given a fixture tree, `plan_reset` returns exactly
  the derived set and NOT the bronze landing / other tables' files. **Prefix-collision
  test**: a fixture with both `orders` and `orders_archive` — `plan_reset("orders")` must
  NOT include any `orders_archive` migration (exact-token match, not prefix glob).
- **Executor tests** (tmp git repo, `_gitfix` helpers): after `execute_reset`, the
  derived paths are gone AND staged as deletions (`git status` shows them staged), the
  bronze landing survives, and shared dbt files retain other tables' rows.
- **The #430 seam**: after reset, `seshat check` exits 0 (no crash, no dangling
  unstaged deletion).
- **Truthfulness**: after reset, `seshat next --table <table>` reports a fresh Source
  stage; verification inspects the actual artifacts (mappings/, migrations, dbt model
  dirs, shared dbt rows), NOT `.seshat/manifest.yaml` (which never records tables).
- **Safety**: `reset ../evil`, `reset foo/bar`, a symlinked component → documented
  refusal, never a removal outside root.

## 7. Open design questions (owner to settle at ratify)

**Q1 — shared dbt files.** `dbt/models/staging/sources.yml` (and any shared
`_models.yml`) may hold rows for multiple tables. Does reset (a) surgically remove only
`<table>`'s rows from shared files, or (b) refuse when a shared file mixes tables and
tell the operator to hand-edit? Recommendation: **(a)** surgical removal, since a clean
native reset is the whole point — but it needs a careful YAML round-trip that preserves
other tables' rows exactly.

**Q2 — the materialized dagster project.** `orchestration/dagster/` is regenerated per
workspace via `seshat dagster init` and is largely table-agnostic scaffolding. Does
reset (a) remove the whole materialized project (forcing a re-`init`), or (b) remove
only `<table>`-scoped run evidence under `.seshat/dagster/runs/**` and leave the project
skeleton? Recommendation: **(b)** — the dagster *project* is workspace-level, not
table-level; only the table's run evidence is derived-from-this-table. Removing the
whole project on a single-table reset is over-broad in a multi-table workspace.

**Q3 — confirmation ergonomics.** Default to interactive confirm with `--yes` to skip,
or default to `--dry-run` requiring an explicit `--apply`? Recommendation: confirm +
`--yes`, matching adopt-pbip's assessment-digest gate style.

## 8. Relationship to shipped work in this batch

- **#439** ships the *manual* reset file-set as interim skill documentation — this verb
  is its eventual native replacement. When the verb ships, the #439 doc section is
  updated to point at `seshat reset` and keep the manual set only as a fallback.
- **#430** and **#431b** are hardened independently so the tool is robust even against a
  *partial* reset done by hand — the verb makes partial resets unnecessary, but the
  gates stay defensive.

---

*Next step (owner-gated): fire `idea-to-spec` on this brief to enter the Spec-Kit chain.
This brief is the durable input; it does not itself authorize implementation.*
