# Agent Skills -- `source-mapping` + `retail-validate` (Design)

- **Status:** Design (approved in brainstorming; pre-implementation)
- **Date:** 2026-06-24
- **Branch:** `feat/agent-skills`
- **Repo:** `Retail_Tower_analytics`
- **Scope:** add the two **buildable** Layer-D / Layer-A-live agent skills whose
  inputs already exist. Defers Layer-D orchestration (the runtime) -- that remains
  the seam the constitution parks as open decision #3.

> **ASCII only.** Use `->` for arrows, `''OR NULL` for the missingness measure.
> No unicode. UTF-8 without BOM (constitution Principle IX; G3).

---

## 1. Why -- the gap this closes

The kit's architecture is a 5-layer stack `D -> C -> A -> ENGINE -> substrate`.
Skills (the *verbs* an agent runs) exist for the static gate (`retail-govern`) and
the substrate (`pbip-workflow`). Two layers have shipped artifacts/code but **no
skill teaching an agent to use them**:

| Layer | Artifact / code that exists | Missing skill |
|-------|-----------------------------|---------------|
| D -- source-mapping gate | 5 templates, `mappings/<table>/` (ADR 0003), playbook | **`source-mapping`** |
| A -- live validate | `src/seshat/validate.py` (built, fixture-tested) | **`retail-validate`** |

This design adds those two skills (+ one thin helper, `profile.py`). It does **not**
build the Layer-D orchestration runtime (open decision #3) -- `source-mapping` is the
act of *exercising* the gate on one table, which is the prerequisite that unblocks
orchestration later.

**Product posture (agent-first, Impeccable-style).** The installed skills are the
agent-facing interface; the agent selects and launches the relevant skill based on
its analysis of the task and repo state. Humans are not expected to operate a
CLI-first tool by hand. `retail check`, `retail validate`, and the new `profile.py`
are **gates/helpers the agent calls**, not the product. This is constitution
Principle I: the agent is the interface; the checker exit code is the authority;
Layer D is the primary surface; Layers A/C are the enforced gates.

---

## 2. Architecture -- two skills, one helper, one shared seam

```
NEW SKILL                       NEW CODE              REUSES (existing, unchanged)
-----------------------------------------------------------------------------------
.claude/skills/
  source-mapping/SKILL.md  -->   src/seshat/           src/seshat/validate.py
    (verb: profile -> author        profile.py [NEW]     - QueryRunner Protocol
     5 artifacts -> stop-and-ask    (mechanical          - resolve_dsn()
     -> HARD-GATE before silver)     profiling queries    - make_psycopg2_runner (read-only)
                                      over QueryRunner)   templates/*.{md,yaml} (the 5 blanks)
                                                          mappings/<table>/ (ADR 0003 dest)
                                                          docs/medallion-playbook.md (method)
                                                          docs/decisions/0002-*.md (RC1-RC16)
  retail-validate/SKILL.md -->   (no new code)          src/seshat/validate.py (run_live_checks)
    (verb: run 4 live checks        reuses validate.py   src/seshat/validate_targets.py (load_targets)
     -> read V-findings -> fix)                          retail validate CLI (cli.py handler)
```

- **Skill text = the agent verb/workflow.** Thin helpers = reusable deterministic
  logic.
- **`profile.py` mirrors `validate.py`'s shape** (same `QueryRunner` Protocol, same
  lazy psycopg2 via the `db` extra, same `resolve_dsn`) but with an **inverted data
  flow** (see Sec 3).
- **One live-connection seam:** both skills reach the DB only through `resolve_dsn`
  + `make_psycopg2_runner`. The static core's `dependencies = []` invariant holds --
  psycopg2 is imported lazily, only on a real live run, never on `profile.py`'s or
  `validate.py`'s module import path.
- **Read-only by posture:** `make_psycopg2_runner` opens
  `set_session(readonly=True)`. Profiling and validation **cannot mutate** any
  connected DB. `profile.py` MUST reuse this runner, never open its own writable one.

---

## 3. Data flow -- the two skills are inverses around the gate

```
                          +--------------- source-mapping skill ----------------+
 bronze.<table>           |  agent picks skill from repo state (agent-first)    |
 + candidate PK    ------>|  1. PROFILE  profile.py(runner, table, candidate_pk)|
 (agent supplies)         |       -> row/col count, ''OR NULL missingness,      |
                          |          distinct cardinality, PK-uniqueness proof  |
                          |       [live boundary: resolve_dsn + lazy db extra]  |
                          |  2. AUTHOR   fill 5 templates -> mappings/<table>/   |
                          |  3. STOP     raise unresolved-questions for grain/  |
                          |              PII/rollup/sentinel (Principle V)       |
                          |  4. GATE     -- HARD STOP: no silver until the map  |
                          +-------------------|  is reviewed & approved --------+
                                              |
                            (human writes silver+gold per the approved map)
                                              |
                          +--------------- retail-validate skill ---------------+
 mappings/<table>/        |  agent picks skill once silver+gold materialized    |
 source-map.yaml   ------>|  load_targets(map) -> ValidationTargets             |
 (now filled)             |  run_live_checks(runner, targets)  [same live seam] |
                          |  -> V-RC2 / V-RC15 / V-RC16 findings -> map to fix  |
                          +-----------------------------------------------------+
```

**The inversion is the key insight:**
- `source-mapping` runs **before** the map exists. Input = a bare bronze
  `schema.table` + a *candidate* PK to test. Output *is* the map. It cannot read
  targets from a `source-map.yaml` (that's what it produces).
- `retail-validate` runs **after** silver+gold exist. Input = the *filled* map
  (`load_targets` parses table/PK/FK/measure targets out of it). Output = pass/fail
  on materialized rows.

So `profile.py` is **not** a clone of `validate.py`; it is a sibling with an opposite
data flow. It MUST NOT be threaded through `load_targets`.

---

## 4. `source-mapping` skill internals

**Trigger (SKILL.md `description`):** when an agent needs to take a raw/bronze retail
source toward Power BI -- profile a new source table, decide grain/PK, fill the
mapping-gate artifacts, or when a user asks to "map/model table X." Scoped like
`retail-govern`'s description.

**Procedure the skill encodes:**
1. **Locate** -- confirm the bronze `schema.table` exists; the agent supplies the
   candidate PK column(s) to test.
2. **Profile (mechanical)** -- call `profile.py`; record the **mechanical** numbers
   into `mappings/<table>/source-profile.md`: landed row/col count, per-column
   missingness (`trim(col)='' OR col IS NULL` -- NEVER `IS NULL` alone; this is the
   load-bearing trap, RC5), distinct cardinality, and the candidate-PK uniqueness
   proof (`COUNT(*)` vs `COUNT(DISTINCT pk)`, `0` NULL PK on landed data).
3. **Profile (semantic) -- agent proposes, human confirms.** The semantic profile
   rows (code<->label 1:1 rate, dimension fan-out, hierarchy multi-parent, returns
   authoritative column, money-relationship identities, cross-file drift) require
   knowing the table's *meaning* and are NOT mechanically derivable. The skill
   instructs the agent to PROPOSE each from the data + column names and raise it as a
   Principle-V stop-and-ask for human confirmation -- never to invent it.
4. **Author** -- starting from the RC1-RC16 defaults, fill `source-map.yaml`
   (grain+PK first, then per-column keep/drop/rename/type/PII/gold-placement, the
   gold star, derived columns) and `assumptions.md` (defaults ADOPTED vs DEVIATED,
   each deviation citing its triggering data fact) into `mappings/<table>/`.
5. **Stop-and-ask (Principle V)** -- raise `unresolved-questions.md` entries for the
   five classes: business-rollup mapping (analyst supplies the full value->group
   table; never invented), PII publish-safety (governance sign-off; default drop),
   grain ambiguity (candidate PK not unique on data), sentinel-vs-null choice, and
   any build-blocking question. Each entry names a who-must-answer owner.
6. **GATE (Principle IV)** -- emit the `reconciliation-report.md` blank and
   **HARD-STOP**: state that no `silver.*` SQL may be written until the map is
   reviewed and approved. The skill does not write silver.

**Deferred/live-boundary mode (no DSN/driver).** The skill MUST NOT traceback and
MUST NOT pretend a profile ran. It reports the live boundary is deferred because
credentials + the optional `db` extra are user-supplied under Principle VIII, prints
the exact enable command/env, and stays useful: it fills the *structure* of all five
artifacts, marks the mechanical profile numbers `[PENDING LIVE PROFILE]`, still
drives the semantic stop-and-ask, and still stops at the gate.

### `profile.py` contract

```
profile(runner: QueryRunner, table: str, candidate_pk: tuple[str, ...]) -> ProfileResult
```

- `ProfileResult` is a frozen dataclass: `row_count`, `column_count`, per-column
  `missingness` (count + pct, measured `''OR NULL`), per-column
  `distinct_cardinality`, and the candidate-PK proof (`total`, `distinct_pk`,
  `null_pk`, `is_unique`).
- **Column discovery:** the caller passes the column list explicitly (the agent
  already has it from the bronze landing / `information_schema`), OR `profile.py`
  reads it from `information_schema.columns` for the given `schema.table` via the
  same read-only runner. Pick the `information_schema` read so the helper is
  self-contained; the per-column queries then iterate that list. State this so
  implementation does not invent a column source.
- **Mechanical only.** No semantic heuristics (no name-similarity code<->label
  guessing) -- those are the human judgment calls Principle V reserves.
- Read-only `QueryRunner` only. stdlib + Protocol; psycopg2 stays lazy in the CLI.
- Mirrors `validate.py`: a fake runner in tests, the real lazy psycopg2 runner via
  the CLI seam on a live run.

---

## 5. `retail-validate` skill internals

A near-sibling of `retail-govern`, for the **live** surface instead of the static one.

**Trigger:** after silver + gold are materialized for a mapped table, when a user
asks to validate / reconcile a table, or when a `V-*` finding appears.

**Procedure:** `load_targets(mappings/<table>/source-map.yaml)` -> `run_live_checks`
-> print findings -> map each to its fix. No DSN/driver -> deferred mode (name the
four checks it would run, print the enable command, cite Principle VIII; never
traceback).

**Rule id -> meaning -> fix:**

| Finding | Means | Fix at |
|---------|-------|--------|
| `V-RC2` | PK not unique / has NULL on materialized silver (RC2). | Fix grain or dedup in the silver SQL; re-verify the map's PK on transformed data. |
| `V-RC15` | Date dim does not span the fact dates (live half of static `S7`; RC15 coverage). | Widen the `generate_series` bounds in the date-dim build to cover min..max fact date. |
| `V-RC16` (orphan) | A fact FK points outside its dimension (RC16, 0 orphans required). | Fix FK COALESCE / the `-1` unknown member, or the dimension load. |
| `V-RC16` (recon) | A measure total differs silver -> gold (RC16, penny-exact). | Fix the gold aggregation; reconcile to the penny. |

**Relationship to static rules:** `V-RC15` coverage is the live complement of static
`S7` (S7 proves dim_date is BUILT from `generate_series`; `V-RC15` proves the
calendar SPANS the data -- the two halves of RC15). Validate emits ERROR (proven
defects); static rules WARN (suspect patterns). Suspect -> WARN, proven -> ERROR.

---

## 6. Error handling

The existing CLI posture (`cli.py` lines ~166-198), applied to both skills:

- No DSN/driver -> actionable text naming Principle VIII + the enable command, never
  a raw traceback.
- Read-only sessions: profiling/validation cannot mutate a connected DB.
- `load_targets` already raises `ValueError` naming the missing field (never a raw
  `KeyError`); the skill surfaces it verbatim.
- Credentials never echoed: connection messages show host only (`dsn.split("@")[-1]`),
  never the userinfo (C2 / Principle IX).

---

## 7. Testing (TDD, >= 80%)

- **`profile.py`** -- unit tests inject a fake `QueryRunner` and assert the profile
  numbers from canned rows; no real DB. A dedicated test proves the missingness
  measure is `''OR NULL` (canned rows with `''` values -> nonzero missingness, where
  `IS NULL` alone would report 0). A guard test proves importing `profile.py` does
  NOT import psycopg2 (the static-core driver-free invariant, mirroring the existing
  validate guard test).
- **Skills (`SKILL.md`)** -- authored with `superpowers:writing-skills`; validated by
  the repo's doc-quality discipline (ASCII/UTF-8-no-BOM, cross-links resolve) and by
  `retail check` staying green (26 rules, exit 0).
- **Fixtures** -- add canned-row fixtures under `tests/fixtures/` as needed for the
  profiling cases.

---

## 8. Collateral fix (in this branch)

`templates/source-map.yaml` lines ~96-97 carry a **stale namespace note** that says
the RC-vs-checker id collision is "flagged, unresolved" and that the checker uses
`RC1-RC8` -- both untrue since feature 002 (the checker is `D1-D8`; the collision is
resolved). This contradicts the file's own corrected note at lines ~44-49. Because
`source-mapping` reads this file, correct lines ~96-97 to match the resolved state in
this branch. One-line doc fix; no behavior change; `retail check` stays green.

---

## 9. Out of scope (explicit boundaries)

- **Layer-D orchestration runtime** -- the agent that *drives* the full playbook and
  self-heals against the gate (open decision #3). These skills are the prerequisite,
  not the runtime.
- **A `retail profile` CLI subcommand** -- profiling stays a helper the skill calls,
  not a new committed command (that would warrant its own spec).
- **`pbi-cli` integration** -- still the later adapter, not wired (Principle II).
- **Other DB engines / local-file sources** -- Postgres-first (Principle III).
- **Semantic profiling automation** -- the agent proposes, the human confirms; the
  skill does not invent business/PII/grain judgment calls (Principle V).

---

## 10. See also

- **Constitution:** `.specify/memory/constitution.md` -- Principles I (agent-first,
  gate-enforced), IV (mapping before silver), V (stop at judgment calls), VIII
  (static-first, live deferred), IX (secrets/reproducibility).
- **Architecture:** `docs/architecture/tower-bi-agent-kit.md` -- the 5-layer stack;
  Sec 5 (the source-mapping gate), Sec 7 (validator categories).
- **Existing skills (the shape to match):** `.claude/skills/retail-govern/SKILL.md`,
  `.claude/skills/pbip-workflow/SKILL.md`.
- **Templates (the 5 blanks):** `templates/source-profile.md`, `source-map.yaml`,
  `assumptions.md`, `unresolved-questions.md`, `reconciliation-report.md`.
- **Live surface (the code reused):** `src/seshat/validate.py`,
  `src/seshat/validate_targets.py`.
- **Method / defaults / worked example:** `docs/medallion-playbook.md`,
  `docs/decisions/0002-retail-cleaning-defaults.md` (RC1-RC16),
  `docs/worked-examples/c086-pharmacy.md`.
