---
name: retail-build-warehouse
description: >-
  Author the silver + gold migration SQL for a mapped retail table from its
  APPROVED source-map, then STOP before executing. Use after a table's mapping
  gate is CLEARED in the Seshat BI repo and someone asks to build the
  silver/gold SQL, write the migration, or fill the retail-orchestrate build seam.
  Author-and-stop: it writes warehouse/migrations/*.sql FILES only, never connects
  to a database, never applies the SQL, and HARD-STOPS at any judgment call the map
  does not already answer.
---

# retail-build-warehouse

Turns an APPROVED `mappings/<table>/source-map.yaml` into the two migration `.sql`
files -- `silver` (typed/cleaned flat table) then `gold` (Kimball star) -- in the
order the medallion playbook proves load-bearing. It fills the silver/gold
`[SEAM]` the `retail-orchestrate` conductor parks at.

The agent is the runtime: this is a procedure you follow, authoring SQL by adapting
the proven `warehouse/migrations/0003`/`0004` shape. There is NO codegen engine, NO
`.sql.tmpl` template, and NO `retail build` CLI -- by design (the source-map cannot
carry the transform logic; an engine would emit only boilerplate). That is a
recorded design decision, not an omission to be fixed.

## Author vs execute (read first)

- **You AUTHOR `.sql` files. That is in-scope** -- writing reviewable migration text,
  no side effects, the same category as `source-mapping` authoring `mappings/`.
- **You NEVER execute.** Do not open a DB connection, do not run the migration, do
  not run the Phase-5 PK dry-run or the Phase-6 orphan/reconcile checks -- those need
  live data and are the deferred DB-write seam (creds + the `db` extra, Principle
  VIII). Authoring -> static `seshat check` -> a HUMAN applies the SQL -> only then
  `retail-validate`. Never claim the silver/gold tables exist or were validated.

## Preconditions (STOP unless all hold)

1. **Canonical gate signal:** `mappings/<table>/readiness-status.yaml` ->
   `stages.mapping_ready.status == pass` WITH a matching `approvals[]` entry (RS1).
   Its human-readable mirror `mappings/<table>/unresolved-questions.md`
   `Gate status: CLEARED` (ZERO open rows) MUST agree. A missing readiness-status
   file, `mapping_ready != pass`, or a mismatch between the two -> STOP (Principle
   IV). Never self-grant.
2. `mappings/<table>/source-map.yaml` parses and carries grain, primary_key, per
   column type/rename/drop/pii/gold_placement, the gold_star, derived_columns.
3. Read `assumptions.md` (the business literals the YAML cannot hold: junk-filter
   list, CASE maps, is_return value set, sentinels, mojibake range) and
   `source-profile.md` (row counts to annotate, the date span for the calendar).
4. Pick the next contiguous migration number `NNNN` over `warehouse/migrations/` (S4a).
5. **Adapter checkpoint -- surface the choice before writing SQL by hand.** Run
   `seshat orchestration-assess` and REPORT its verdict to the human before
   authoring migrations. This repo ships two transformation/orchestration
   adapters (dbt, Dagster); hand-written migrations are the default path, so
   without this step they get bypassed silently rather than declined on purpose
   (issue #489). The assessor is read-only: it emits a categorical verdict
   (`consider` / `not_recommended` / `already_adopted`), never a numeric score,
   and it never adopts anything. If it says `already_adopted`, prefer the adapter
   over new hand-written SQL. If it says `consider`, state that and let the human
   choose -- do NOT adopt an adapter on your own, and do NOT treat `consider` as
   permission to skip authoring. If it says `not_recommended`, proceed here and
   say so.

## Silver: the load-bearing Phase-5 order (NUMBERED -- do NOT reorder)

Author `warehouse/migrations/NNNN_create_silver_<table>.sql`. The order is
load-bearing; a reordering passes `seshat check` (the gate is order-blind) yet is
WRONG. Transcribe in this exact sequence, adapting the proven `0003`:

1. **`src` CTE -- TRIM every text column** (kills whitespace-variant phantom distincts).
2. **Encoding/mojibake whitelist** on display columns (e.g. `regexp_replace(... keep
   chr 32-126 + the domain's needed ranges ...)`), sourced from `assumptions.md`.
3. **`filtered` CTE -- junk-row filters BEFORE `''`->NULL** (`WHERE col NOT IN (...,
   '')`). MUST come before step 4 -- once `''` becomes NULL, `IN ('')` stops matching.
4. **`''`->NULL** via `NULLIF(trim(x), '')` (folded into the casts below).
5. **Casts** via `NULLIF(trim(x), '')::type` -- money/qty `numeric`, dates `date`,
   leading-zero ids stay `TEXT`, ordinals `smallint` (RC7).
6. **Numeric-based row filters on the CAST value, not text** (`'0.0' <> '0'`).
7. **Derived columns** -- is_return from the AUTHORITATIVE column (never the measure
   sign), business rollups with `ELSE 'UNMAPPED'`.
8. **Sentinel UPDATEs** after the SELECT -- fill grouping-dim text NULLs with the
   `assumptions.md` sentinel; leave fact NULLs as NULL.

Wrap: `SET client_encoding TO 'UTF8'; BEGIN; CREATE SCHEMA IF NOT EXISTS silver;
DROP TABLE IF EXISTS silver.<t>; CREATE TABLE silver.<t> AS WITH ... SELECT ...;`
then the sentinel UPDATEs, then `ALTER TABLE ... ADD PRIMARY KEY (...)`, then
`CREATE INDEX ...`, then `COMMIT;`. Bare DROP+CREATE in one txn (S4b layer-aware
allows this for derived silver/gold). UTF-8 no BOM. Write the file in ONE Write call.

Flag `ADD PRIMARY KEY` as **UNVERIFIED-UNTIL-APPLIED**: PK uniqueness is only
provable on transformed data (the live dry-run), which is the deferred seam.

## Gold: the Kimball star (Phase 6)

Author `warehouse/migrations/NNNN+1_create_gold_<table>_star.sql`, adapting `0004`:
- One fact at silver grain + one conformed dim per business entity.
- Surrogate `_sk` (`GENERATED BY DEFAULT AS IDENTITY`); keep natural keys as attrs.
- **Unknown member at `_sk = -1`** in every ENTITY dim (`INSERT ... OVERRIDING
  SYSTEM VALUE VALUES (-1, ...)`), then real rows collapsed 1:1 by natural key
  (`GROUP BY`). The DATE dim is the EXCEPTION -- see the `dim_date` bullet below;
  S6 (ERROR) requires the member on entity dims, S8 (ERROR) FORBIDS it on the date
  dim, so "every dim" without the carve-out authors SQL the gate rejects.
- Fact FK columns `COALESCE(d.x_sk, -1)` via LEFT JOIN -- for ENTITY dims only.
  NEVER `COALESCE(dd.date_sk, -1)`: a real out-of-span date would be silently
  bucketed to Unknown while the coverage checks stay green (RC19). Leave the date
  FK bare and let `NOT NULL` reject the unmatched row.
- Transaction ids with no attributes -> **degenerate dims on the fact**, not a dim.
- **`dim_date` = contiguous `generate_series(from, to, '1 day')`** over the map's
  date span -- NEVER `SELECT DISTINCT date` (S7; missing days break time-intel).
  It carries **NO `-1`/NULL unknown member** (S8, ERROR): it becomes a marked date
  table (`dataCategory: Time`), which Power BI validates as unique/contiguous/no-
  nulls, so a `-1` member breaks refresh and time-intelligence even though the SQL
  succeeds and every other check stays green.
- FK constraints + FK indexes AFTER load (so `-1` members and rows exist first).
- Idempotent: drop fact before dims (FK order), recreate all in one txn.

## Judgment stops (fail LOUD -- never satisfy with a silent default)

STOP and raise an `unresolved-questions.md` row (do not guess) if:
- `stages.mapping_ready.status` != `pass` (or its `approvals[]` entry is absent), or
  the `Gate status: CLEARED` mirror does not agree, or any open row remains.
- A column's `silver_type` / `missing_policy` / `gold_placement` is missing or
  ambiguous -> never guess a type or invent a placement.
- The junk-filter `NOT IN (...)` values are not pinned in `assumptions.md`.
- The authoritative returns column / the `is_return` value list is absent -> never
  derive is_return from a measure sign (RC8).
- A categorical/billing CASE map or business rollup is incomplete -> only
  `ELSE 'UNMAPPED'` is an allowed sentinel; never invent an arm.
- A sentinel is requested but its 0-collision safety was not verified (RC6).
- The `dim_date` span is absent -> never hardcode a guessed calendar range.
- A `pii: true` column is not `decision: drop`.
- A dim `max()`/`GROUP BY` 1:1 collapse where the map did not confirm id->attribute
  is 1:1 (max() silently picks one value if it is actually 1:many).

## After authoring (the handoff)

1. Run `seshat check` (static, local, no DB) -- the authored SQL must exit 0. The
   SQL family is S1, S2, S3, S4a, S4b, S5, S6, S7, S8 (there is no bare "S4", and
   S8 is real -- do not cite the family as a "S1-S7" range).
2. **Self-review the order:** diff your silver SQL against the numbered checklist
   above. The checker is order-blind; this manual step is the only catch for a
   reordering bug (e.g. `''`->NULL before the junk filter).
3. Print the apply command and the sequence, then STOP:
   `psql "$DATABASE_URL" -f warehouse/migrations/NNNN_create_silver_<table>.sql`
   then the gold file, in numeric order. Then `retail validate --source-map
   mappings/<table>/source-map.yaml`.

**`seshat check` exit 0 is NECESSARY, not SUFFICIENT.** It proves form (snake_case,
schemas, idempotent shape, `-1` member present, generate_series used). It does NOT
prove correctness -- right row count, no sentinel collision, complete enums, penny
reconciliation. That is proven ONLY by the live `retail-validate` after a human
applies the SQL. Say this in your handoff; do not let green read as "correct".

## Orchestration

`retail-orchestrate` invokes this skill at its silver/gold build phase (the `[SEAM]`
it previously only parked at). This skill still STOPS at the execute boundary -- the
conductor does not apply SQL either; a human applies, then the conductor resumes at
`retail-validate`. The self-heal loop lives in `retail-orchestrate`, not here.

## See also

- The conductor: the `retail-orchestrate` skill.
- The method + skeletons: the medallion playbook, Phase 5/6 + Appendix A/B.
- The proven reference: `warehouse/migrations/0003_create_silver_retail_store_sales.sql`,
  `0004_create_gold_retail_store_sales_star.sql`.
- The approved input: `mappings/<table>/` (e.g. the filled `mappings/retail_store_sales/`).
- The live half (after a human applies): the `retail-validate` skill.
