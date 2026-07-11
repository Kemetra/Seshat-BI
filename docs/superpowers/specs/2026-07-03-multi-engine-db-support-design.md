# Multi-Engine DB Support (SQL Server · MySQL · Snowflake) — Design

- **Date:** 2026-07-03
- **Status:** DESIGN — pending user approval, then a Principle III constitutional amendment (human ratification required; see §9)
- **Scope (locked with the user):** the read-only **profile + validate** seam only. NOT warehouse-SQL authoring, NOT Power BI gold-read wiring (those are separate, larger surfaces — deferred).
- **Engines (locked):** SQL Server (pyodbc), MySQL (mysql-connector-python / PyMySQL), Snowflake (snowflake-connector-python) — all three now. Postgres (psycopg2) stays the default and unchanged.
- **Governance (locked):** design → build → PR, **stop at a ratify ledger**. The agent does NOT self-amend the constitution and does NOT merge to `main`.

---

## 1. Problem & why it is small in code, large in governance

Every live-DB access in this repo flows through **one Protocol**:

```python
class QueryRunner(Protocol):
    def run(self, sql: str, params: tuple = ()) -> list[tuple]: ...
```

with exactly one concrete implementation today — `make_psycopg2_runner` (`validate.py`). Three read-only modules consume it:

| Module | Stage | DB constructs used |
|---|---|---|
| `profile.py` | Stage 1 source profiling | `information_schema`, `count(*) FILTER`, `count(DISTINCT (…))`, `trim()`, `%s` params |
| `validate.py` | Stage 4 live checks (PK/date/orphan/reconcile) | `count(*) FILTER`, distinct-tuple, `%s`, `postgresql://` DSN, `set_session(readonly=True)` |
| `value_proxy.py` | L4 measure-value check | `count(DISTINCT {col})`, aggregate SQL |

The **logic** is already driver-free and dialect-agnostic (tests inject fakes; the static core stays `dependencies = []`). What is Postgres-specific is only: (1) the raw **SQL fragments**, (2) **identifier quoting**, (3) the **param placeholder**, (4) **connection + read-only** posture, (5) **secret redaction** of the connection string.

The genuine gate is **governance**: ratified **Principle III (Medallion, Postgres-First, Gold-Only)** states *"Other engines and local files are explicitly out of scope (Postgres-first) — deferred to future specs."* Adding engines requires an amendment, which is a **Principle-V human-ratification act** the agent structurally cannot perform. See §9.

---

## 2. Approach — a thin `Dialect` seam (chosen)

Three options were weighed:

- **(A) Thin `Dialect` Protocol** — a connection builder + ~7 pure fragment builders, one lazy optional driver extra per engine. Matches this repo's DNA (Protocol seams, lazy optional imports, stdlib-only static core). **CHOSEN.**
- (B) SQLAlchemy Core — one dependency for all four, but heavy (the repo deliberately avoids it) and it does **not** portablize the hand-written SQL; the fragments would still need rewriting.
- (C) Lowest-common ANSI rewrite + per-engine connect only — least dialect code, but pins the SQL to the least-capable engine and still needs paramstyle + quoting per engine.

### The two seams, kept distinct

```
QueryRunner   (UNCHANGED)  — "how do I execute": run(sql, params) -> rows
Dialect       (NEW)        — "how do I phrase it": quoting, params, fragments, connect
   ├─ PostgresDialect   (emits byte-identical SQL to today's strings — KEEPS native FILTER + row-value DISTINCT; NOT rewritten to the portable forms — zero behavior change)
   ├─ SqlServerDialect  (T-SQL, pyodbc)
   ├─ MySqlDialect
   └─ SnowflakeDialect
```

**New module:** `src/seshat/dialect.py`. It holds the `Dialect` Protocol + the four concrete dialects. It is imported by the CLI seam and by the three DB modules for fragment building. Concrete `connect()` implementations lazy-import their driver **inside the method**, never at module scope — preserving the driver-free import invariant (B1/B3) exactly as `make_psycopg2_runner` does today.

---

## 3. The `Dialect` surface (recon-verified)

Verified by a 3-engine parallel recon workflow (2026-07-03) plus authoritative-source fetches (pyodbc wiki; Snowflake official docs). Full matrix archived in the recon output; the load-bearing decisions:

| Method | Portable form / per-engine behavior |
|---|---|
| `count_where(pred)` | **`COUNT(CASE WHEN <pred> THEN 1 END)`** — one form, all four. **NOT** `SUM(CASE WHEN pred THEN 1 ELSE 0 END)`: `SUM` over an empty/all-non-matching ungrouped set returns **NULL**, while `COUNT(*) FILTER` returns **0**. `COUNT(CASE…)` is the exact equivalent with no `COALESCE`. General rule for a non-count FILTER (`agg(x) FILTER (WHERE p)`): push the predicate *inside* → `agg(CASE WHEN p THEN x END)`. |
| `distinct_tuple_count(cols, table, where?)` | **`(SELECT COUNT(*) FROM (SELECT DISTINCT … FROM <table> [WHERE …]) AS sub)`** — one form, all four. Postgres accepts only the row-value form, SQL Server accepts *neither* multi-col form, MySQL/Snowflake accept the comma form — the derived-table subquery is the sole universal. The `AS sub` alias is **required** by Snowflake, harmless elsewhere. |
| `trim_empty(col)` | **`LTRIM(RTRIM(col)) = '' OR col IS NULL`** — universal; sidesteps the SQL Server ≤ 2016 `TRIM()` gap (space-equivalent to `TRIM` for the whitespace case). `'' ≠ NULL` on all four (no Oracle trap); the explicit `OR col IS NULL` disjunct is required everywhere. |
| `quote_ident(name)` / `quote_qualified(name)` | **per-engine** — `"…"` (PG, Snowflake) · `[…]` (SQL Server, unconditional; escape `]`→`]]`) · `` `…` `` (MySQL). **Folding-aware** (see §4, HARD RISK). |
| `placeholder()` + `translate_params(sql)` | **per-engine** — `%s` (psycopg2, mysql, snowflake-default) · `?` (pyodbc, qmark). A translation seam is unavoidable. **`%%` trap:** a literal `%` in SQL must be doubled for the three pyformat engines and left single for qmark. (Snowflake *can* be forced to qmark per-connection, but psycopg2/mysql cannot — the seam stays.) |
| `columns_query()` → `(sql, params)` + `is_text_type(dt)` | portable SELECT (`information_schema.columns`), but **three per-engine config axes**: (a) result-key casing (SQL Server/Snowflake return UPPERCASE labels — alias explicitly or read case-insensitively), (b) `_TEXT_TYPES` set differs (PG `character varying`; MySQL `varchar`/`text`/…; SQL Server `varchar`/`nvarchar`/…; **Snowflake collapses all char types to `TEXT`**), (c) filter-literal casing (**Snowflake stores unquoted identifiers UPPERCASE → a lowercase table/schema literal returns zero rows *silently*** — see §4). |
| `connect(config) -> QueryRunner` | **per-engine** driver + read-only posture. The read-only *guarantee* is a **SELECT-only DB account** (only Postgres has a driver toggle). Universal posture: `autocommit=True` + least-privilege reader + SELECT-only statements. Optional belt-and-suspenders: PG `set_session(readonly=True)`, MySQL `SET SESSION TRANSACTION READ ONLY`. |

**Verified paramstyle table (cited):**

| Engine | Driver | paramstyle | Placeholder | Source |
|---|---|---|---|---|
| Postgres | psycopg2 | `pyformat` | `%s` | existing code |
| SQL Server | pyodbc | `qmark` | `?` | pyodbc wiki (fetched 2026-07-03) |
| MySQL | mysql-connector-python / PyMySQL | `pyformat` | `%s` | recon (imported live) |
| Snowflake | snowflake-connector-python | `pyformat` (default; `qmark` selectable) | `%s` (or `?`) | Snowflake docs (fetched 2026-07-03) |

---

## 4. HARD RISKS — the silent-failure class (each gets a dedicated test)

These fail **silently-wrong** (bad data, no exception) — the dangerous class for a profiler. Each is a named requirement, not a footnote.

### R1 — Identifier case-folding on the profile *input* path (the deepest bug)
`profile.py` takes a **user-supplied** `schema.table` + candidate PK, introspects `information_schema`, then quotes and queries. On **Snowflake**, unquoted names are stored UPPERCASE; if a user passes `bronze.my_table` and the layer emits `"my_table"`, Snowflake **matches nothing and returns 0 rows with no error** — the profiler would report *"0 rows, PK unique"* on a table it never actually read. This is upstream of the Dialect quote-char swap.

**Requirement:** a **folding-normalization rule at the identifier boundary**. Today `identifiers.py` (`quote_identifier` / `quote_qualified_identifier`) and `profile.py._safe_identifier` hardcode `"…"` and are shared by validate + value_proxy. The design **splits the two concerns cleanly**:
- **Validation stays shared + engine-agnostic** — the `[A-Za-z_][A-Za-z0-9_]*` grammar and the SQL-injection guard do not move; they are engine-independent safety.
- **Quoting + folding moves to the Dialect** — `dialect.quote_ident()` applies the engine's quote char AND normalizes case to the engine's stored-case convention (upper for Snowflake, lower for Postgres, preserved for SQL Server/MySQL) OR emits unquoted to let the engine fold. The `information_schema` filter literal is normalized by the same rule so introspection and querying agree.

### R2 — Param binding: `%s`↔`?` translation + `%%` literal-percent
The seam that rewrites `%s`→`?` for pyodbc, and doubles `%`→`%%` for the pyformat engines (and NOT for qmark), is easy to get subtly wrong (e.g. a `LIKE '%x%'` fragment). **Requirement:** one canonical author style (`%s`), translated per engine in `translate_params`; literal-% handled per target style.

### R3 — Empty-input conditional count returning NULL not 0
Covered by the `count_where` = `COUNT(CASE…)` decision (§3). **Requirement:** tested against (i) an empty table and (ii) a table where the predicate matches zero rows; assert `0`, not `None`.

### R4 — Secret redaction across 4 non-URL connection shapes (secret-hygiene, C1/C2)
`resolve_dsn` and `_redact_dsn` (`validate.py` / `cli.py`) are **Postgres-URL-shaped** — `_redact_dsn` does `urlsplit` on a `postgresql://` string. They do **not** redact:
- SQL Server's **ODBC keyword string** (`DRIVER={…};SERVER=…;PWD=secret;…`),
- Snowflake's **`connect()` kwargs** (`password=`, `token=`, `private_key=`),
- the **driver-reformatted error text** (each driver reformats differently).

This repo's whole posture is secret-hygiene (C2 secret-scan; the deliberate scheme-splitting at `validate.py:87`). **Requirements:**
- A **per-engine redaction** step (`dialect.redact(message, config)`) that scrubs that engine's credential fields from any error text before it is printed — mirroring `_redact_dsn`'s component-level scrub, generalized past URLs.
- Confirm **C1 (parameterized-connection) and C2 (secret-scan)** recognize the new connection-string shapes as scannable, so an accidentally-committed ODBC string or Snowflake kwargs literal is caught, not missed.
- Redaction gets **explicit tests** per engine (the current design's omission, now closed).

---

## 5. Engine selection — one authoritative rule

**`ANALYTICS_DB_ENGINE` is the single authority.** Values: `postgres` (default), `sqlserver`, `mysql`, `snowflake`. **No URL-scheme-prefix fallback** — two mechanisms that can disagree is a bug. Config resolution per engine:

| Engine | Config source |
|---|---|
| Postgres | UNCHANGED — `DATABASE_URL` or `ANALYTICS_DB_*` → DSN (backward-compatible; `resolve_dsn` untouched for the default path) |
| SQL Server | `ANALYTICS_DB_*` → ODBC keyword string (+ `ANALYTICS_DB_ODBC_DRIVER`, default `ODBC Driver 18 for SQL Server`; note Driver-18 `Encrypt=yes` default → `TrustServerCertificate=yes` for dev/self-signed) |
| MySQL | `ANALYTICS_DB_*` → `connect()` kwargs (host/port 3306/user/password/db, `charset=utf8mb4`) |
| Snowflake | `ANALYTICS_DB_*` + `ANALYTICS_DB_ACCOUNT` (+ optional `_WAREHOUSE`/`_ROLE`) → `connect()` kwargs |

**100% backward-compatible:** with `ANALYTICS_DB_ENGINE` unset, everything behaves exactly as today. Secrets stay in gitignored `.env` (Principle IX / C2); no real values in tracked files, ever.

---

## 6. Data flow (control flow unchanged; new indirection)

```
CLI validate / profile / value-check handler
  → engine = env['ANALYTICS_DB_ENGINE']  (default 'postgres')
  → dialect = get_dialect(engine)                 # NEW
  → config  = dialect.resolve_config(env)         # NEW (PG path == today's resolve_dsn)
  → runner  = dialect.connect(config)             # was make_psycopg2_runner(dsn)
  → profile/validate/value_proxy build SQL via dialect.<fragment>()   # was hardcoded PG strings
  → runner.run(sql, params) → rows                # QueryRunner Protocol — UNCHANGED
  (on error) → print(dialect.redact(exc, config)) # was _redact_dsn
```

---

## 7. Packaging — one lazy optional extra per driver

```toml
[project.optional-dependencies]
db        = ["psycopg2-binary>=2.9"]              # UNCHANGED (Postgres, default)
mssql     = ["pyodbc>=5.0"]                       # + OS prereq: MS ODBC Driver 18 (non-pip)
mysql     = ["mysql-connector-python>=9.0"]       # pure-Python, no OS prereq
snowflake = ["snowflake-connector-python>=3.0"]   # pure-Python, no OS prereq; needs account id + HTTPS egress
```

Each driver is imported **lazily inside `connect()`** only. CI installs none of them; the suite passing proves the logic stays driver-free (the existing invariant, extended). The only non-pip prerequisite is SQL Server's OS-level ODBC driver — documented as a prerequisite, never a code dependency (exactly how psycopg2's binary wheel is treated today).

---

## 8. Testing strategy — and an honest limit

- **Dialect-fragment unit tests** — each dialect's builders assert exact SQL strings per engine (no DB). Fast; in the stdlib-only suite.
- **Silent-failure regression tests** — R1 (folding round-trip: introspect → quote → query resolves non-empty), R2 (`LIKE '%x%'` + bound param round-trips per paramstyle), R3 (empty-table conditional count = 0 not None), R4 (redaction scrubs each engine's credential fields from error text). These assert **generated SQL and the translation/redaction logic**, injected against fake runners.
- **Backward-compat guard** — the existing tests stay green; `PostgresDialect` emits byte-identical SQL to today's exact strings (it **keeps** the native `FILTER` and row-value `DISTINCT` forms — it is **not** rewritten to the portable `COUNT(CASE)`/derived-table forms; only the three new dialects use those). Postgres behavior is byte-identical, so the suite remains a true regression oracle.
- **Driver-free invariant** — extend the existing guard tests: `retail.cli` / `retail.validate` / `retail.profile` / `retail.value_proxy` / `retail.dialect` import path must NOT import psycopg2, pyodbc, mysql.connector, or snowflake.connector.

**Honest limit (Principle VIII — live-deferred):** CI **cannot** verify that SQL Server actually returns 0 on an empty conditional count, or that Snowflake resolves a folded identifier — the recon agents could not even import pyodbc/snowflake, and CI installs no engine. Per-engine **live** validation is therefore **deferred under Principle VIII**, the same bucket as the already-deferred Postgres live run (needs the extra + real credentials). The suite proves the *generated SQL and translation logic* are correct; it does not prove each engine *executes* it — that is an explicit, governed deferral, not an omission.

---

## 9. Governance — the ratify ledger (STOP here)

This design **contradicts ratified Principle III** ("Postgres-first; other engines explicitly out of scope"). Per the user's locked decision and repo memory (`ratify-seam-not-auto-cleared`), the amendment is a **Principle-V human-ratification act** the agent cannot self-grant, and "do recommended / without stop" does **not** clear it.

**The agent WILL:** design, build, test, and open a PR on the `worktree-multi-engine-db` branch; draft the Principle III amendment as a `speckit-constitution` artifact; and present a **ratify ledger** naming the decision, the amended principle text, and the required human owner.

**The agent WILL NOT:** edit `.specify/memory/constitution.md` to ratify, mark any readiness stage `pass`, merge to `main`, or emit any numeric confidence score (hard rule #9).

**Proposed Principle III amendment (for human ratification — not self-applied):**
> The data substrate is **primarily** a Postgres medallion warehouse (`bronze`→`silver`→`gold`). The read-only profile + validate seam MAY connect to additional engines (SQL Server, MySQL, Snowflake) via a Dialect abstraction, each behind an optional lazy driver extra. Postgres remains the default; warehouse-SQL authoring and Power BI gold-read remain Postgres-only until separately specified. Gold-only and flow-direction rules are unchanged.

---

## 10. Out of scope (YAGNI — explicitly deferred)

- Warehouse-SQL authoring (`retail-build-warehouse`) for non-Postgres engines — a separate large dialect surface (MERGE, DDL, type mapping).
- Power BI reading `gold` from non-Postgres engines — doc + report-layer work (`docs/powerbi-connection.md`, M parameters).
- Live per-engine validation runs (Principle VIII deferral, §8).
- Oracle, DuckDB, BigQuery, or any engine beyond the three named.
- Connection pooling, retries, async — the seam stays a single read-only connection, as today.
```

