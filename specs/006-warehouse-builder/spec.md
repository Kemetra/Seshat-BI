# Feature Specification: warehouse builder -- the silver/gold SQL-authoring verb

**Feature Branch**: `006-warehouse-builder` (work on `main` per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Shipped (retail-build-warehouse authoring skill landed)

**Input**: "Build the silver/gold SQL-authoring builder -- the middle-of-loop seam the retail-orchestrate conductor parks at. It reads an APPROVED source-map (mappings/<table>/, Gate status: CLEARED) and AUTHORS the numbered migration .sql files into warehouse/migrations/ in the load-bearing Phase 5/6 order, then STOPS. Authoring .sql FILES is in-scope (same category as source-mapping authoring mappings/); EXECUTING the SQL against Postgres is the deferred DB-write seam."

## Why this feature exists

The `retail-orchestrate` conductor (feature 005) sequences the medallion phases but
parks at a `[SEAM]` for "build silver" and "build gold" -- there is no verb that
turns an approved source-map into migration SQL. This feature fills the largest
middle-of-loop hole with a **pure authoring skill**: it writes the two migration
`.sql` files an analyst would otherwise hand-write, in the order the playbook proves
load-bearing, then stops at the execute boundary.

It closes the gap between the mapping gate (an approved `source-map.yaml`) and the
live validator (`retail validate`, which needs materialized rows): builder authors
the SQL -> a human applies it -> `retail validate` proves it.

## The author/execute boundary (the load this feature respects)

- **AUTHORING `.sql` files is in-scope.** Writing reviewable migration text is the
  same category as `source-mapping` authoring `mappings/` artifacts -- no side
  effects, no DB connection. Feature 001's Scope Boundaries ("NO new warehouse
  tables, NO database writes") was scoped to that Phase 0/1 docs/templates slice and
  bans *tables/writes*, not *files*; this feature writes FILES only and records that
  distinction. **This is the amendment: file authoring of `warehouse/migrations/*.sql`
  is in-scope; executing them is not.**
- **EXECUTING is the deferred DB-write seam.** Opening a connection, running the
  migration, the Phase-5 PK dry-run (`COUNT(*)=COUNT(DISTINCT pk)` on transformed
  data), and the Phase-6 0-orphan-FK / penny-reconciliation checks ALL require live
  data -- they belong to the deferred seam (needs creds + the `db` extra, Principle
  VIII). The builder authors, runs static `retail check`, prints the apply command,
  and STOPS. It never claims the silver/gold tables exist or were validated.

## Architecture (a pure skill; no codegen, no templates, no CLI)

The builder is `.claude/skills/retail-build-warehouse/SKILL.md` -- agent-procedure
text, the agent is the runtime (same posture as the other verbs). **Decision: pure
skill, no codegen helper, no `.sql.tmpl` templates, no `retail build` CLI subcommand.**

Deciding reason (verified): the `source-map.yaml` schema **deliberately does not
carry the transform logic** -- `templates/source-map.yaml` states "Phase 2.6 row
filters and the build ORDER live in the migration, not here." The proven
`warehouse/migrations/0001_create_silver_sales_c086.sql` depends on exactly that
excluded content (the division junk `NOT IN` list, the compound numeric-zero filter,
the mojibake whitelist codepoints, the 10-arm Arabic->English billing CASE, the
11-arm business-segment rollup, the `is_return` Z-code set, five sentinel UPDATEs) --
none of which has a YAML field; all live as prose in `assumptions.md`. So a codegen
helper or template could only emit boilerplate while the judgment-laden ~80% stays
hand-authored -- adding the repo's first maintained codegen surface for ~zero gain at
one-table volume (YAGNI), and breaking the all-skills verb architecture. The agent
authoring SQL by adapting the proven `0001`/`0002` (as it hand-wrote the RetailGold
model) is the right grain.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author silver from an approved map (Priority: P1)

Given a `mappings/<table>/` with `Gate status: CLEARED`, the builder authors
`warehouse/migrations/NNNN_create_silver_<table>.sql` in the load-bearing Phase-5
order, and `retail check` stays exit 0 on the new file.

**Why this priority**: silver is the foundation the gold star and the live validator
both depend on; authoring it correctly (right order, right idiom) is the core value.

**Independent Test**: the c086 replay -- given the CLEARED `mappings/c086/` map
(back-authored in this feature), the builder reproduces SQL structurally equivalent
to the committed `0001` (same 7-step order, same `NULLIF(trim(x),'')::type` idiom,
same CASE arms sourced from `assumptions.md`, same sentinel UPDATEs), and `retail
check` stays exit 0.

**Acceptance Scenarios**:

1. **Given** `Gate status: CLEARED` + zero open rows, **When** the builder runs,
   **Then** it writes one silver migration in the Phase-5 order and prints the psql
   apply command, and STOPS (no DB connection).
2. **Given** `Gate status: OPEN` (or any open row), **When** the builder runs,
   **Then** it STOPS without authoring silver (Principle IV mapping gate).
3. **Given** the authored silver file, **When** `retail check` runs, **Then** it
   exits 0 (S1-S7 satisfied) -- a NECESSARY-not-sufficient gate (see SC note).

### User Story 2 - Author the gold Kimball star (Priority: P2)

After silver, the builder authors `NNNN+1_create_gold_<table>_star.sql`: one fact at
silver grain + conformed dims (`_sk`, `-1` unknown member), degenerate dims on the
fact, a contiguous `generate_series` date dim, FK constraints after load.

**Independent Test**: the c086 gold replay reproduces SQL structurally equivalent to
the committed `0002`; `retail check` exits 0 (S6 `-1` member, S7 generate_series).

### User Story 3 - Judgment calls hard-stop, never auto-filled (Priority: P1)

The builder authors only what the map + `assumptions.md` state. Any missing or
ambiguous judgment input HARD-STOPS for a human -- it never invents a junk-filter
list, a CASE arm, a sentinel, or a date span.

**Independent Test**: present a map missing the `is_return` value list (or the junk
`NOT IN` set); assert the builder STOPS and raises it, rather than guessing.

**Acceptance Scenarios**:

1. **Given** a column with no `silver_type`, **Then** STOP -- never guess a type.
2. **Given** no analyst-supplied CASE map for a categorical, **Then** STOP -- only
   `ELSE 'UNMAPPED'` is an allowed sentinel; never invent an arm.
3. **Given** `pii: true` on a column not marked `decision: drop`, **Then** STOP.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add `.claude/skills/retail-build-warehouse/SKILL.md` (ASCII, UTF-8 no
  BOM, valid frontmatter). No new Python, no `.sql.tmpl`, no CLI subcommand.
- **FR-002**: The skill reads `mappings/<table>/{source-map.yaml, assumptions.md,
  source-profile.md, unresolved-questions.md}` and proceeds only on `Gate status:
  CLEARED` with zero open rows (never self-grants approval).
- **FR-003**: The skill embeds the load-bearing Phase-5 order as a NUMBERED immutable
  checklist (TRIM -> encoding whitelist -> junk filters BEFORE ''->NULL -> ''->NULL
  -> NULLIF casts -> numeric filters on CAST value -> derived columns -> sentinel
  UPDATEs), then ADD PRIMARY KEY + CREATE INDEX, all in one idempotent
  DROP+CREATE-in-txn (S4b), `SET client_encoding UTF8`, UTF-8 no BOM.
- **FR-004**: The skill authors the gold star per Phase 6 (fact at silver grain;
  dims with `_sk` + `-1` member; degenerate dims on the fact; contiguous
  `generate_series` date dim; FK constraints after load).
- **FR-005**: The authored SQL MUST satisfy `retail check` S1-S7 (snake_case;
  bronze/silver/gold schemas; `vw_` prefix; layer-aware DROP+CREATE-in-txn; type
  discipline; gold `-1` member; date dim from generate_series).
- **FR-006**: The skill carries a fail-loud judgment-stop table (gate not CLEARED;
  missing/ambiguous type/filter/CASE/returns/sentinel/span; `pii:true` not dropped;
  unconfirmed 1:1 collapse). Each is a HARD-STOP, not satisfiable by a silent default.
- **FR-007**: Author/execute honesty: the skill writes FILES only, never opens a DB
  connection; it prints the apply sequence (author -> `retail check` -> human applies
  via psql in numeric order -> then `retail validate`) and STOPS. It flags `ADD
  PRIMARY KEY` as UNVERIFIED-UNTIL-APPLIED (uniqueness is only provable on
  transformed data -- the live seam).
- **FR-008**: The skill includes a mandatory Phase-5-order self-review step (diff the
  authored SQL against the numbered checklist) because the checker is order-blind.
- **FR-009**: Append a `## Orchestration` pointer to the skill; `retail-orchestrate`
  references it at the silver/gold `[SEAM]` rows (the conductor's seam is now filled
  by an authoring verb that still stops before execution).
- **FR-010**: Back-author `mappings/c086/` (the prerequisite fixture) -- the first
  real `mappings/<table>/` instance -- so the c086 replay has an input to build from.

### Key Entities

- **Builder skill** (`retail-build-warehouse`): the authoring verb; agent is runtime.
- **`mappings/c086/`**: the first filled mapping-gate instance, back-authored from
  the committed `0001`/`0002` SQL + the worked example; `Gate status: CLEARED`.
- **Authored migrations**: `warehouse/migrations/NNNN_create_silver_<table>.sql` and
  `NNNN+1_create_gold_<table>_star.sql` -- reviewable text, not executed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `.claude/skills/retail-build-warehouse/SKILL.md` exists, ASCII + no
  BOM, registered by the harness; `mappings/c086/` holds the five filled artifacts.
- **SC-002**: `retail check` stays exit 0 (26 rules) with the new skill + mappings;
  full unit suite green; no new Python; `dependencies = []` unchanged.
- **SC-003**: The c086 replay reproduces silver+gold SQL structurally equivalent to
  the committed `0001`/`0002`, and `retail check` exits 0 on the reproduced files.
- **SC-004**: `retail check` exit 0 is documented in the skill as
  NECESSARY-not-sufficient -- semantic correctness (row counts, sentinel collisions,
  enum completeness) is proven only by the live `retail validate` after a human
  applies the SQL.

## Assumptions

- Pure skill (no codegen/templates/CLI) -- the source-map schema cannot drive the
  transforms, so an engine buys ~zero at one-table volume (YAGNI).
- The builder authors FILES and stops; execution is the deferred DB-write seam.
- `mappings/c086/` must be back-authored first (the prerequisite the design panel
  surfaced) -- `mappings/` currently holds only `README.md`.
- The c086 replay is the acceptance test; green is necessary-not-sufficient.

## Deferred decisions (future specs / issues -- recorded, not built)

- **Executing the migrations** (the DB-write seam): apply via psql/runner, the live
  PK dry-run, 0-orphan-FK and penny-reconciliation checks -- needs creds + the `db`
  extra (Principle VIII). Authored here, applied + validated later.
- **A `G6` static rule: "no real host / secret in PBIP parameters"** -- C2 already
  catches a committed DigitalOcean endpoint, but Power BI Desktop re-writes the real
  host into the tracked `expressions.tmdl` on every "Edit Parameters -> save". A `G6`
  rule that fails closed when a PBIP parameter default is a real host (not the
  `<placeholder>`) would also catch non-DO hosts and make the intent explicit,
  moving enforcement fully onto the gate. Recorded here; a checker change for a later
  slice. (For now: C2 + CI block an actual commit; the human reverts the local
  Desktop write.)
- **A `source-map.yaml` schema extension** carrying `row_filters[]`, parseable CASE
  `mapping[]` pairs, mojibake ranges, the `is_return` list -- would let a future
  gold-star emitter be partly codegen'd; a larger schema change, deferred. Until
  then `assumptions.md` prose + the fail-loud stops are the contract.
- **A `G6`/order checker for the load-bearing Phase-5 order** -- the order is
  currently invisible to the gate (S5/S6/S7 are WARNINGs); a rule asserting filter
  order would harden it. Deferred.

## See also

- The conductor that parks at this seam: `.claude/skills/retail-orchestrate/SKILL.md`;
  `specs/005-layer-d-orchestration/spec.md`.
- The method: `docs/medallion-playbook.md` Phase 5/6 + Appendix A/B.
- The proven reference: `warehouse/migrations/0001_create_silver_sales_c086.sql`,
  `0002_create_gold_star.sql`; `docs/worked-examples/c086-pharmacy.md`.
- The map spine + GO signal: `templates/source-map.yaml`,
  `templates/unresolved-questions.md` (`Gate status`).
- The live half (after a human applies the SQL): the `retail-validate` skill.
