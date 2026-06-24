# Agent Skills (source-mapping + retail-validate) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two agent-facing skills (`source-mapping`, `retail-validate`) plus one thin profiling helper (`profile.py`) so an agent can drive a raw retail table through the source-mapping gate and validate the result live.

**Architecture:** `profile.py` is a driver-free profiling helper that mirrors `validate.py` (same `QueryRunner` Protocol, same lazy psycopg2 via the CLI seam, read-only) but with an inverted data flow -- it runs *before* a `source-map.yaml` exists and emits mechanical numbers only. The two SKILL.md files are agent verbs that wrap the existing templates/code; `source-mapping` enforces the hard gate (no silver before an approved map) and `retail-validate` runs the four live checks and maps findings to fixes.

**Tech Stack:** Python 3 (stdlib-only static core), pytest (`pytest.mark.unit`), TMDL/SQL/YAML artifacts, Claude Code skills (`.claude/skills/<name>/SKILL.md`). psycopg2 + pyyaml are OPTIONAL `db`/dev deps imported lazily, never on the static import path.

## Global Constraints

- **ASCII only** in all artifacts; UTF-8 without BOM. Use `->` for arrows, `''OR NULL` for the missingness measure. (Constitution Principle IX; checker G3.)
- **Static core stays driver-free:** `retail` package `dependencies = []`. psycopg2 and pyyaml are imported LAZILY only (in the CLI handler or inside a function body), NEVER at a module's import scope. (Principle VIII.)
- **Read-only DB posture:** any live runner is `make_psycopg2_runner` (opens `set_session(readonly=True)`). New code MUST reuse it, never open its own connection.
- **Findings shape:** `Finding(rule_id, severity, message, locator)` with `Severity.ERROR|WARNING|INFO` from `retail.core`. Live checks use `Severity.ERROR`.
- **Tests:** every test file starts `pytestmark = pytest.mark.unit`; run with `PYTHONPATH=src`. No real DB in any test -- inject a fake `QueryRunner`.
- **Skill structure:** match `.claude/skills/retail-govern/SKILL.md` and `pbip-workflow/SKILL.md` -- YAML frontmatter (`name`, `description`), then markdown body. `description` must be a precise trigger.
- **`retail check` MUST stay green** (26 rules, exit 0) after every commit.
- **Commit message types:** `feat|fix|refactor|docs|test|chore|ci` (checker P2).
- **Branch:** all work on `feat/agent-skills`.

---

## File Structure

- `src/retail/profile.py` **[CREATE]** -- the mechanical profiling helper. `ProfileResult` dataclass + `profile(runner, table, candidate_pk)`. Driver-free; reuses `retail.validate.QueryRunner`.
- `tests/unit/test_profile.py` **[CREATE]** -- unit tests with a `FakeRunner` (copy the pattern from `test_validate.py`): row/col count, `''OR NULL` missingness, cardinality, PK proof, and the driver-free guard.
- `tests/fixtures/` -- reuse existing patterns; no new fixture files needed (canned rows are inline in the test).
- `templates/source-map.yaml:96-97` **[MODIFY]** -- correct the stale namespace note.
- `.claude/skills/source-mapping/SKILL.md` **[CREATE]** -- the gate verb.
- `.claude/skills/retail-validate/SKILL.md` **[CREATE]** -- the live-check verb.

Task order: **1** (collateral fix, isolated) -> **2** (`profile.py` via TDD) -> **3** (`source-mapping` skill, depends on 2) -> **4** (`retail-validate` skill, independent of 2/3).

---

### Task 1: Fix the stale namespace note in source-map.yaml

A one-line collateral fix. Feature 002 resolved the RC-vs-checker id collision (checker is `D1-D8`, not `RC*`), but lines ~96-97 still say it is "flagged, unresolved" and that the checker uses `RC1-RC8`. This contradicts the file's own corrected note at lines ~44-49. `source-mapping` reads this file, so correct it here.

**Files:**
- Modify: `templates/source-map.yaml:96-97`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing (doc text only).

- [ ] **Step 1: Read the current lines to confirm exact text**

Run: `sed -n '91,98p' templates/source-map.yaml` (or Read the file at offset 91).
Expected current text includes:
```
# NOTE: the ids below are ADR-0002 ids (RC1-RC16). They are NOT `retail check`
# rule ids (also RC1-RC8). Same prefix, different namespace -- flagged, unresolved.
```

- [ ] **Step 2: Replace the stale note**

Replace those two comment lines with:
```
# NOTE: the ids below are ADR-0002 cleaning defaults (RC1-RC16). The `retail check`
# governance checker uses a SEPARATE namespace (D1-D8) for its TMDL/DAX rules --
# distinct prefixes, no collision (disambiguated in feature 002). See lines ~44-49.
```

- [ ] **Step 3: Verify the checker stays green**

Run: `PYTHONPATH=src python -m retail.cli check`
Expected: exit 0; "26 rules" reported; no new finding (YAML is still valid; comment-only change).

- [ ] **Step 4: Commit**

```bash
git add templates/source-map.yaml
git commit -m "fix: correct stale RC/checker namespace note in source-map.yaml (resolved in 002)"
```

---

### Task 2: `profile.py` -- the mechanical profiling helper (TDD)

The helper `source-mapping` calls to get the numbers the source-profile artifact rests on. Mirrors `validate.py`: driver-free, runs against a `QueryRunner`, mechanical numbers ONLY (no semantic heuristics -- those are Principle-V judgment calls the agent proposes and a human confirms).

**Files:**
- Create: `src/retail/profile.py`
- Test: `tests/unit/test_profile.py`

**Interfaces:**
- Consumes: `from retail.validate import QueryRunner` (the `run(sql, params) -> list[tuple]` Protocol).
- Produces:
  - `ColumnProfile` (frozen dataclass): `name: str`, `missing_count: int`, `missing_pct: float`, `distinct_cardinality: int`.
  - `PkProof` (frozen dataclass): `total: int`, `distinct_pk: int`, `null_pk: int`, `is_unique: bool`.
  - `ProfileResult` (frozen dataclass): `table: str`, `row_count: int`, `column_count: int`, `columns: tuple[ColumnProfile, ...]`, `pk: PkProof`.
  - `profile(runner: QueryRunner, table: str, candidate_pk: tuple[str, ...]) -> ProfileResult`.
  - Column discovery is internal: `profile` reads column names from `information_schema.columns` via the same runner (so the helper is self-contained), then runs one missingness+cardinality query per column.

- [ ] **Step 1: Write the failing test for column discovery + row count**

Create `tests/unit/test_profile.py`:
```python
"""TDD tests for the mechanical profiling helper (profile.py).

Driver-free, mirroring test_validate.py: a scripted FakeRunner returns canned
rows so the logic is exercised with no database and no psycopg2. profile.py
computes MECHANICAL numbers only -- counts, ''OR NULL missingness, distinct
cardinality, and the candidate-PK proof. Semantic findings (code<->label, fan-out,
returns column) are NOT here -- they are Principle-V judgment calls the agent
proposes and a human confirms.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


class FakeRunner:
    """A QueryRunner whose results are scripted per-call (FIFO)."""

    def __init__(self, results: list[list[tuple]]) -> None:
        self._results = list(results)
        self.calls: list[str] = []

    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        self.calls.append(sql)
        return self._results.pop(0) if self._results else []


def test_profile_discovers_columns_and_counts_rows() -> None:
    from retail.profile import profile

    runner = FakeRunner(
        [
            [("net_amt",), ("prod_cat",)],   # information_schema.columns -> 2 cols
            [(100,)],                         # row count
            [(0, 50)],                        # net_amt: 0 missing, 50 distinct
            [(8, 12)],                        # prod_cat: 8 missing, 12 distinct
            [(100, 100, 0)],                  # pk proof: total, distinct, null
        ]
    )
    result = profile(runner, "bronze.demo_orders", ("order_no", "line_no"))
    assert result.table == "bronze.demo_orders"
    assert result.row_count == 100
    assert result.column_count == 2
    assert tuple(c.name for c in result.columns) == ("net_amt", "prod_cat")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/unit/test_profile.py::test_profile_discovers_columns_and_counts_rows -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retail.profile'`.

- [ ] **Step 3: Write the minimal implementation**

Create `src/retail/profile.py`:
```python
"""Mechanical profiling of a landed (bronze) source table.

The source-mapping gate's first artifact (source-profile.md) rests on numbers,
not adjectives. This helper computes the MECHANICAL ones -- row/col count,
per-column ''OR NULL missingness, distinct cardinality, and the candidate-PK
uniqueness proof on the landed data. Semantic profiling (code<->label 1:1,
dimension fan-out, the authoritative returns column) needs the table's MEANING
and is a Principle-V judgment call -- the agent proposes it, a human confirms it;
it is deliberately NOT computed here.

DRIVER-FREE: runs against the `retail.validate.QueryRunner` Protocol, so this
module's import path NEVER imports psycopg2. The real read-only runner is built
lazily in the CLI seam, exactly as `retail.validate` does. Inverted data flow vs
validate.py: this runs BEFORE a source-map.yaml exists (input is a bare table +
candidate PK), so it MUST NOT be routed through validate_targets.load_targets.
"""

from __future__ import annotations

from dataclasses import dataclass

from .validate import QueryRunner


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    missing_count: int
    missing_pct: float
    distinct_cardinality: int


@dataclass(frozen=True)
class PkProof:
    total: int
    distinct_pk: int
    null_pk: int
    is_unique: bool


@dataclass(frozen=True)
class ProfileResult:
    table: str
    row_count: int
    column_count: int
    columns: tuple[ColumnProfile, ...]
    pk: PkProof


def _discover_columns(runner: QueryRunner, table: str) -> tuple[str, ...]:
    """Column names for ``schema.table`` from information_schema, in order."""
    if "." in table:
        schema, name = table.split(".", 1)
    else:
        schema, name = "public", table
    rows = runner.run(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        (schema, name),
    )
    return tuple(r[0] for r in rows)


def profile(
    runner: QueryRunner, table: str, candidate_pk: tuple[str, ...]
) -> ProfileResult:
    """Profile ``table`` mechanically. Read-only; one pass of simple aggregates."""
    columns = _discover_columns(runner, table)

    row_rows = runner.run(f"SELECT count(*) FROM {table}")
    row_count = row_rows[0][0] if row_rows else 0

    col_profiles: list[ColumnProfile] = []
    for col in columns:
        # Missingness is ''OR NULL, NEVER IS NULL alone (RC5 / the load-bearing
        # trap): a faithful landing writes '' for None, so IS NULL reports 0.
        stat = runner.run(
            f"SELECT count(*) FILTER (WHERE trim({col}) = '' OR {col} IS NULL), "
            f"count(DISTINCT trim({col})) FROM {table}"
        )
        missing, distinct = (stat[0][0], stat[0][1]) if stat else (0, 0)
        pct = (missing / row_count * 100.0) if row_count else 0.0
        col_profiles.append(
            ColumnProfile(
                name=col,
                missing_count=missing,
                missing_pct=pct,
                distinct_cardinality=distinct,
            )
        )

    pk_cols = ", ".join(candidate_pk)
    null_pred = " OR ".join(f"{c} IS NULL" for c in candidate_pk)
    pk_rows = runner.run(
        f"SELECT count(*), count(DISTINCT ({pk_cols})), "
        f"count(*) FILTER (WHERE {null_pred}) FROM {table}"
    )
    total, distinct_pk, null_pk = pk_rows[0] if pk_rows else (0, 0, 0)
    pk = PkProof(
        total=total,
        distinct_pk=distinct_pk,
        null_pk=null_pk,
        is_unique=(total == distinct_pk and null_pk == 0),
    )

    return ProfileResult(
        table=table,
        row_count=row_count,
        column_count=len(columns),
        columns=tuple(col_profiles),
        pk=pk,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/unit/test_profile.py::test_profile_discovers_columns_and_counts_rows -v`
Expected: PASS.

- [ ] **Step 5: Write the failing test for the ''OR NULL missingness trap**

Append to `tests/unit/test_profile.py`:
```python
def test_missingness_uses_empty_or_null_not_is_null_alone() -> None:
    from retail.profile import profile

    # A faithful landing wrote '' for missing values. The missingness query must
    # COUNT those '' rows; IS NULL alone would (wrongly) report 0 missing.
    runner = FakeRunner(
        [
            [("city",)],          # one column
            [(200,)],             # 200 rows
            [(30, 5)],            # city: 30 ''OR NULL missing, 5 distinct
            [(200, 200, 0)],      # pk proof
        ]
    )
    result = profile(runner, "bronze.demo", ("id",))
    city = result.columns[0]
    assert city.missing_count == 30
    assert city.missing_pct == pytest.approx(15.0)
    # Prove the query text uses the ''OR NULL measure, not IS NULL alone.
    missingness_sql = runner.calls[2]
    assert "= ''" in missingness_sql and "IS NULL" in missingness_sql
```

- [ ] **Step 6: Run it -- it should already PASS (implementation done in Step 3)**

Run: `PYTHONPATH=src pytest tests/unit/test_profile.py::test_missingness_uses_empty_or_null_not_is_null_alone -v`
Expected: PASS (this test guards the trap; the Step-3 implementation already satisfies it).

- [ ] **Step 7: Write the failing test for the PK uniqueness proof (both branches)**

Append to `tests/unit/test_profile.py`:
```python
def test_pk_proof_unique_when_distinct_equals_total_and_no_nulls() -> None:
    from retail.profile import profile

    runner = FakeRunner(
        [[("id",)], [(100,)], [(0, 100)], [(100, 100, 0)]]
    )
    pk = profile(runner, "bronze.demo", ("id",)).pk
    assert pk.is_unique is True


def test_pk_proof_not_unique_when_duplicates_or_nulls() -> None:
    from retail.profile import profile

    # 100 rows, 98 distinct -> 2 dupes -> not unique
    dupes = FakeRunner([[("id",)], [(100,)], [(0, 100)], [(100, 98, 0)]])
    assert profile(dupes, "bronze.demo", ("id",)).pk.is_unique is False

    # 100 rows, 100 distinct, but 3 NULL pk -> not unique
    nulls = FakeRunner([[("id",)], [(100,)], [(0, 100)], [(100, 100, 3)]])
    assert profile(nulls, "bronze.demo", ("id",)).pk.is_unique is False
```

- [ ] **Step 8: Run the new PK tests**

Run: `PYTHONPATH=src pytest tests/unit/test_profile.py -k pk_proof -v`
Expected: both PASS.

- [ ] **Step 9: Write the driver-free guard test**

Append to `tests/unit/test_profile.py`:
```python
def test_profile_imports_without_psycopg2() -> None:
    import importlib

    # If psycopg2 were imported at module scope this would already have failed at
    # the test's `from retail.profile import profile`. Re-import to lock it in.
    mod = importlib.import_module("retail.profile")
    assert hasattr(mod, "profile")
    assert "psycopg2" not in repr(getattr(mod, "__dict__", {}).get("profile"))
```

- [ ] **Step 10: Run the full profile test file**

Run: `PYTHONPATH=src pytest tests/unit/test_profile.py -v`
Expected: all PASS (5 tests).

- [ ] **Step 11: Run the whole suite + the checker to confirm no regression**

Run: `PYTHONPATH=src pytest tests/ -q && PYTHONPATH=src python -m retail.cli check`
Expected: all tests green; checker exit 0, 26 rules.

- [ ] **Step 12: Commit**

```bash
git add src/retail/profile.py tests/unit/test_profile.py
git commit -m "feat: add mechanical profiling helper (profile.py) for the source-mapping gate"
```

---

### Task 3: `source-mapping` skill (the gate verb)

The agent-facing verb that drives profile -> author the five artifacts -> stop-and-ask -> HARD-GATE before silver. Calls `profile.py` for mechanical numbers; instructs the agent to PROPOSE semantic findings for human confirmation; never writes silver.

**Files:**
- Create: `.claude/skills/source-mapping/SKILL.md`

**Interfaces:**
- Consumes: `retail.profile.profile(...)` (Task 2); the five templates in `templates/`; the live seam `retail.validate.resolve_dsn` / `make_psycopg2_runner`.
- Produces: nothing code-level (it is agent procedure text). Output artifacts land in `mappings/<table>/`.

- [ ] **Step 1: Write the SKILL.md**

Create `.claude/skills/source-mapping/SKILL.md`:
````markdown
---
name: source-mapping
description: >-
  Drive a raw retail source table through the source-mapping gate before any
  silver SQL exists. Use when someone asks to map, model, profile, or onboard a
  new bronze table toward Power BI in the Retail_Tower_analytics repo -- profile
  the source, decide grain/PK, fill the five mapping artifacts into
  mappings/<table>/, and stop at the gate. This skill ENFORCES the rule that no
  silver.* SQL is written until the map is reviewed and approved. It profiles and
  authors and stops; it does NOT write silver/gold SQL and does NOT build the
  Power BI model.
---

# source-mapping

The source-mapping gate is the kit's one load-bearing rule (constitution
Principle IV): **before any `silver.*` SQL is written, the source MUST be
profiled and mapped into committed, reviewed artifacts.** This skill runs that
gate: profile -> author the five artifacts -> stop at judgment calls -> hard-stop
before silver. It formalizes Phases 1-4 of `docs/medallion-playbook.md`; the
playbook stays authoritative on HOW to decide, the templates on WHAT to record.

## Scope boundary (read first)

This skill profiles a source and authors the mapping artifacts, then STOPS. It
does NOT write `silver.*` or `gold.*` SQL, does NOT call pbi-cli or Power BI
Desktop, and does NOT decide the judgment calls Principle V reserves for a human.
Silver is downstream of an APPROVED map -- approval is the reviewer's action, not
this skill's.

## The five artifacts (copy blanks from templates/ into mappings/<table>/)

Per [ADR 0003](../../../docs/decisions/0003-mapping-artifact-location.md), a
table's filled set lives in `mappings/<table>/`:

1. `source-profile.md` -- Phase 1 numbers (this skill fills the mechanical ones).
2. `source-map.yaml` -- the machine-readable spine (grain+PK first, per-column
   keep/drop/rename/type/PII/gold-placement, the gold star, derived columns).
3. `assumptions.md` -- which RC1-RC16 defaults were ADOPTED vs DEVIATED (each
   deviation cites its triggering data fact).
4. `unresolved-questions.md` -- the build-blocking judgment calls + who answers.
5. `reconciliation-report.md` -- the blank the later live run fills (RC16).

## Procedure

### 1. Locate
Confirm the bronze `schema.table` exists. Ask the analyst/agent for the candidate
PK column(s) to test (grain is decided FIRST, Phase 2.0 / RC1).

### 2. Profile (mechanical) -- via profile.py
Run the mechanical profiler over a read-only connection and record the numbers
into `mappings/<table>/source-profile.md`:

```python
import os
from retail.validate import resolve_dsn, make_psycopg2_runner
from retail.profile import profile

dsn = resolve_dsn(dict(os.environ))     # DATABASE_URL or ANALYTICS_DB_* parts
runner = make_psycopg2_runner(dsn)      # read-only; needs the `db` extra
result = profile(runner, "bronze.<table>", ("<pk_a>", "<pk_b>"))
```

`result` gives: `row_count`, `column_count`, per-column `missing_count` /
`missing_pct` (measured `''OR NULL`, NEVER `IS NULL` alone -- the load-bearing
trap, RC5) / `distinct_cardinality`, and the candidate-PK proof (`total`,
`distinct_pk`, `null_pk`, `is_unique`). Write each into the source-profile table
and the Candidate grain & PK section.

### 3. Profile (semantic) -- PROPOSE, do not invent (Principle V)
The semantic rows -- code<->label 1:1 rate, dimension fan-out (`id -> name`),
hierarchy multi-parent, the AUTHORITATIVE returns column, money-relationship
identities, cross-file drift -- need the table's MEANING. profile.py does NOT
compute these. PROPOSE each from the data + column names, then raise it as an
`unresolved-questions.md` entry for human confirmation. Never invent a business
rollup, a PII ruling, or the returns column.

### 4. Author the map and assumptions
Starting from the RC1-RC16 defaults, fill `source-map.yaml` (grain+PK first, then
per-column decisions, the gold star, derived columns) and `assumptions.md`
(adopted vs deviated, each deviation citing its triggering data fact). Keep all
text ASCII, snake_case silver names, short paths (Windows 260 limit).

### 5. Stop-and-ask (Principle V)
Raise `unresolved-questions.md` entries, each with a who-must-answer owner, for:
business-rollup mapping (analyst supplies the full value->group table), PII
publish-safety (governance sign-off; default drop), grain ambiguity (candidate PK
not unique on the data), sentinel-vs-null choice, and any build-blocking question.

### 6. GATE -- hard stop (Principle IV)
Emit the `reconciliation-report.md` blank and STOP. State plainly: no `silver.*`
SQL may be written until the map is reviewed and approved. Hand the filled set to
the reviewer; do not proceed to silver.

## Deferred/live-boundary mode (no DSN or no `db` extra)

If `resolve_dsn(...)` returns None or psycopg2 is not installed, do NOT traceback
and do NOT pretend a profile ran. The live boundary is deferred BY DESIGN:
credentials + the optional `db` extra are user-supplied under constitution
Principle VIII. In this mode:

- Report the boundary and print the exact enable steps:
  `pip install 'retail[db]'`, then set `DATABASE_URL` (or the `ANALYTICS_DB_*`
  vars) in the gitignored `.env`. Never commit a real DSN.
- STAY USEFUL: copy the five template blanks into `mappings/<table>/`, fill their
  STRUCTURE, mark the mechanical profile numbers `[PENDING LIVE PROFILE]`, still
  drive the semantic stop-and-ask (Step 3) and the gate (Step 6).

## See also

- Gate + principles: `docs/architecture/tower-bi-agent-kit.md` Sec 5;
  `.specify/memory/constitution.md` Principles IV, V.
- Method / defaults: `docs/medallion-playbook.md`;
  `docs/decisions/0002-retail-cleaning-defaults.md` (RC1-RC16).
- Live half (after silver/gold exist): the `retail-validate` skill.
- A filled instance: `docs/worked-examples/c086-pharmacy.md` (an example, never
  the universal schema).
````

- [ ] **Step 2: Verify the skill file is ASCII + has valid frontmatter**

Run: `PYTHONPATH=src python -c "import pathlib; b=pathlib.Path('.claude/skills/source-mapping/SKILL.md').read_bytes(); assert b[:3]!=b'\xef\xbb\xbf','BOM!'; assert all(c<128 for c in b),'non-ASCII'; print('ascii+no-BOM OK')"`
Expected: `ascii+no-BOM OK`.

- [ ] **Step 3: Verify cross-linked paths resolve**

Run: `ls docs/architecture/tower-bi-agent-kit.md docs/medallion-playbook.md docs/decisions/0002-retail-cleaning-defaults.md docs/decisions/0003-mapping-artifact-location.md .specify/memory/constitution.md docs/worked-examples/c086-pharmacy.md`
Expected: all six paths listed (no "No such file"). If `0003` differs, correct the link.

- [ ] **Step 4: Run the checker (skill files are under .claude/, not model artifacts)**

Run: `PYTHONPATH=src python -m retail.cli check`
Expected: exit 0, 26 rules (no new finding).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/source-mapping/SKILL.md
git commit -m "feat: add source-mapping skill (the gate verb: profile -> author -> stop -> gate)"
```

---

### Task 4: `retail-validate` skill (the live-check verb)

The agent-facing verb for the live surface -- the sibling of `retail-govern`, but
for `retail validate` instead of `retail check`. Runs the four live checks via the
existing code and maps each `V-*` finding to its fix.

**Files:**
- Create: `.claude/skills/retail-validate/SKILL.md`

**Interfaces:**
- Consumes: `retail.validate_targets.load_targets`, `retail.validate.run_live_checks`, `resolve_dsn`, `make_psycopg2_runner`; the `retail validate --source-map` CLI handler.
- Produces: nothing code-level (agent procedure text).

- [ ] **Step 1: Write the SKILL.md**

Create `.claude/skills/retail-validate/SKILL.md`:
````markdown
---
name: retail-validate
description: >-
  Run the LIVE data checks against a materialized retail table and interpret the
  findings. Use after silver + gold exist for a mapped table in the
  Retail_Tower_analytics repo, when someone asks to validate or reconcile a
  table, or when a V-RC2 / V-RC15 / V-RC16 finding appears. Invoke-and-interpret
  only: this skill runs `retail validate` against a live Postgres DB and maps each
  finding id to its fix. It does NOT build models, write SQL, or auto-fix.
---

# retail-validate

`retail check` proves everything provable from committed text. `retail validate`
proves the four things only a running database can show, on the MATERIALIZED rows
(constitution Principle VIII; `src/retail/validate.py`). This skill runs it and
maps each finding to the one place to fix it -- the live sibling of
`retail-govern`.

## Scope boundary (read first)

Invoke-and-interpret only. This skill runs the live checks and explains findings;
it does NOT write or fix silver/gold SQL, does NOT call pbi-cli, and does NOT
auto-loop. The live run needs a DB and is the user's call; you report and stop.

## Prerequisites

- silver + gold are materialized for the table.
- A reviewed `mappings/<table>/source-map.yaml` exists (the targets are derived
  from it -- table, PK, FK, measures).
- The optional `db` extra is installed (`pip install 'retail[db]'`) and a DSN is
  configured (`DATABASE_URL` or the `ANALYTICS_DB_*` vars in the gitignored
  `.env`). Never commit a real DSN.

## Run it

```
retail validate --source-map mappings/<table>/source-map.yaml
```

The connection is host-agnostic (any Postgres: local / remote / DigitalOcean /
other) and READ-ONLY (the session is opened read-only; the checks only SELECT).
Exit is non-zero iff any check finds a defect.

## Read a finding

Each is a `Finding(rule_id, severity, message, locator)`. Live findings are
`ERROR` (proven defects -- a real PK duplicate, a real orphan, a real penny
mismatch), unlike the static rules' `WARNING` (suspect patterns). Start at the
locator; the id tells you which fix applies.

## Finding id -> meaning -> where to fix

| Finding | Means | Fix at |
|---------|-------|--------|
| `V-RC2`  | PK not unique, or has a NULL, on the materialized silver table (RC2). | Fix the grain or dedup in the silver SQL; re-verify the map's PK on the TRANSFORMED output (landed uniqueness is not enough). |
| `V-RC15` | The date dimension does not span every fact date -- the calendar has gaps (RC15 coverage; the live half of static rule `S7`). | Widen the `generate_series` bounds in the date-dim build to cover min..max fact date. |
| `V-RC16` (orphan) | A fact FK points outside its dimension (RC16; 0 orphans required). | Fix the FK COALESCE to the `-1` unknown member, or fix the dimension load so the key exists. |
| `V-RC16` (reconcile) | A measure total differs between silver and gold (RC16; must reconcile to the penny). | Fix the gold aggregation (a join fan-out or filter is dropping/duplicating rows) until silver and gold totals match exactly. |

`V-RC15` is the live complement of static `S7`: `S7` proves `dim_date` is BUILT
from `generate_series` (the pattern); `V-RC15` proves the calendar SPANS the data
(coverage). Both halves of RC15 must hold.

## Deferred/live-boundary mode (no DSN or no `db` extra)

If no DSN is configured or the `db` extra is absent, `retail validate` does NOT
traceback and does NOT pretend a run happened -- the live boundary is
user-supplied by design (Principle VIII). Without `--source-map` it reports the
surface is built and how to target a table; without a DSN/driver it prints the
enable steps: `pip install 'retail[db]'`, then set `DATABASE_URL` (or
`ANALYTICS_DB_*`) in the gitignored `.env`. Report that state; do not fake a pass.

## What to do after interpreting

Report the failing ids, their locators, and the one fix each needs. Hand silver
fixes to `warehouse/` SQL and gold/star fixes to the gold build; DAX/PBIP issues
go to the `powerbi-analyst` agent. Then STOP -- re-running `retail validate` to
confirm green is the user's next call, not a loop this skill performs.

## See also

- The checks: `src/retail/validate.py`; target sourcing:
  `src/retail/validate_targets.py`.
- Principle VIII (static-first, live deferred): `.specify/memory/constitution.md`.
- The static sibling: the `retail-govern` skill.
- The blank the run fills: `templates/reconciliation-report.md`.
````

- [ ] **Step 2: Verify the skill file is ASCII + no BOM**

Run: `PYTHONPATH=src python -c "import pathlib; b=pathlib.Path('.claude/skills/retail-validate/SKILL.md').read_bytes(); assert b[:3]!=b'\xef\xbb\xbf','BOM!'; assert all(c<128 for c in b),'non-ASCII'; print('ascii+no-BOM OK')"`
Expected: `ascii+no-BOM OK`.

- [ ] **Step 3: Verify cross-linked paths resolve**

Run: `ls src/retail/validate.py src/retail/validate_targets.py .specify/memory/constitution.md templates/reconciliation-report.md .claude/skills/retail-govern/SKILL.md`
Expected: all five paths listed.

- [ ] **Step 4: Run the checker + full suite**

Run: `PYTHONPATH=src python -m retail.cli check && PYTHONPATH=src pytest tests/ -q`
Expected: checker exit 0 (26 rules); all tests green.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/retail-validate/SKILL.md
git commit -m "feat: add retail-validate skill (the live-check verb, sibling of retail-govern)"
```

---

## Self-Review

**1. Spec coverage** -- every spec section maps to a task:
- Sec 2/3 architecture + inverted data flow -> Task 2 (`profile.py` contract + docstring states the inversion).
- Sec 4 `source-mapping` (6-step procedure, mechanical/semantic split, deferred mode, gate) -> Task 3.
- Sec 4 `profile.py` contract (mechanical only, column discovery via information_schema) -> Task 2 Steps 1/3.
- Sec 5 `retail-validate` (run, V-RC2/V-RC15/V-RC16 table, deferred mode) -> Task 4.
- Sec 6 error handling (no traceback, read-only, host-only echo) -> Task 3/4 deferred-mode sections.
- Sec 7 testing (fake runner, ''OR NULL test, driver-free guard) -> Task 2 Steps 5/9.
- Sec 8 collateral fix -> Task 1.
- Sec 9 out-of-scope (no `retail profile` CLI, no orchestration) -> respected: no CLI task added.

**2. Placeholder scan** -- the `<table>` / `<pk_a>` tokens in the skill bodies are intentional template syntax shown to the agent, not plan gaps. Every code/step shows real content. No TBD/TODO. PASS.

**3. Type consistency** -- `profile(runner, table, candidate_pk) -> ProfileResult`; `ProfileResult.columns: tuple[ColumnProfile, ...]`, `.pk: PkProof`; `ColumnProfile.missing_count/missing_pct/distinct_cardinality`; `PkProof.total/distinct_pk/null_pk/is_unique`. Used identically in Task 2 tests (Steps 1/5/7) and Task 3 Step 1. `QueryRunner` consumed from `retail.validate`. PASS.

**Note for the implementer:** Task 2's `FakeRunner` scripts results in FIFO call order -- the order in `profile()` is: discover columns, row count, then per-column (missingness+cardinality), then the PK proof. If you reorder the queries in the implementation, update the canned-row order in the tests to match.
