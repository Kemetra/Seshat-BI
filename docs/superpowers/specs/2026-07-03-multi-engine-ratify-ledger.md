# Ratify Ledger — Multi-Engine DB Support (Principle III amendment)

- **Date:** 2026-07-03
- **Branch:** `worktree-multi-engine-db`
- **Status:** ✅ **RATIFIED** by Ahmed Shaaban (repo owner), 2026-07-04. Applied to `.specify/memory/constitution.md` as amendment 1.7.0. This was a named human's explicit Principle-V act; the agent transcribed the decision and did not self-grant it.
- **Design:** `docs/superpowers/specs/2026-07-03-multi-engine-db-support-design.md`
- **Plan:** `docs/superpowers/plans/2026-07-03-multi-engine-db-support.md`

> **This document is a DECISION REQUEST, not a decision.** The agent has NOT edited
> `.specify/memory/constitution.md`, has NOT merged to `main`, and emits NO numeric
> confidence score (hard rule #9). Ratification is a named human's explicit act.

---

## 1. The decision being requested

Amend ratified **Principle III (Medallion, Postgres-First, Gold-Only)** to allow the
**read-only profile + validate seam** to connect to SQL Server, MySQL, and Snowflake
(in addition to the default Postgres), via the `Dialect` abstraction built on this
branch. Postgres remains the default and the only engine for which behavior is unchanged.

**Why an amendment is required:** the current Principle III text (below) states other
engines are "explicitly out of scope (Postgres-first) — deferred to future specs." This
branch is that future spec. Adopting it changes a ratified constitutional principle, so
per **Principle V (Agent Stops at Judgment Calls)** and repo memory
(`ratify-seam-not-auto-cleared`), only a named human — or an explicitly-delegated owner —
may ratify it. "Do recommended / go / without stop" does **not** clear this seam.

---

## 2. Current Principle III text (verbatim, unchanged on disk)

From `.specify/memory/constitution.md` §III:

> ### III. Medallion, Postgres-First, Gold-Only
> One substrate, one read surface, one source of truth.
> - The data substrate is the DigitalOcean Postgres medallion warehouse with schemas `bronze` -> `silver` -> `gold`. Data flows in that direction only.
> - Power BI MUST read the `gold` schema only. …
> - The MVP is Postgres-first. There MUST NOT be a DuckDB/Parquet-first ADR … 
> - `gold` MUST be a Kimball star …

And §VIII: *"Connection is host-agnostic: any Postgres (local / remote / DigitalOcean / other) via a DSN from env. Other engines and local files are explicitly out of scope (Postgres-first, Principle III) — deferred to future specs."*

---

## 3. Proposed amendment text (for the human to apply, NOT applied by the agent)

Add a bullet to Principle III and update the §VIII "out of scope" sentence:

**Principle III — add:**
> - The **read-only profile + validate seam** MAY connect to additional engines
>   (SQL Server, MySQL, Snowflake) through the `Dialect` abstraction, each behind an
>   optional lazy driver extra (`retail[mssql|mysql|snowflake]`). Postgres remains the
>   **default** and the only engine whose behavior is guaranteed byte-identical.
>   **Warehouse-SQL authoring** (`retail-build-warehouse`) and **Power BI's `gold`
>   read** remain Postgres-only until separately specified. The gold-only rule and the
>   `bronze -> silver -> gold` flow-direction rule are unchanged.

**Principle VIII — replace the "out of scope" sentence with:**
> - Connection is engine-aware via `ANALYTICS_DB_ENGINE` (default `postgres`): any
>   Postgres via DSN, plus SQL Server / MySQL / Snowflake for the read-only
>   profile+validate seam (optional lazy driver extras). Live per-engine runs remain
>   deferred (need the extra + credentials). Local files remain out of scope.

---

## 4. Evidence the human should weigh before ratifying

| Claim | Evidence |
|---|---|
| Postgres behavior unchanged | `PostgresDialect` emits byte-identical SQL (FILTER + row-value DISTINCT kept); independently verified by reconstructing + diffing the pre-refactor SQL strings (Opus review, Tasks 3-5). |
| Full suite green | 964 passed, 1 skipped (897 baseline + 67 new tests). |
| Static core stays driver-free | No module-scope driver import; each driver lazy inside `connect()`; B1 guards mysql/snowflake roots, B3 covers `dialect.py`. Verified by pytest (the live gate runs main's ruleset — see limitation below). |
| Secret hygiene | Per-engine `redact()` scrubs credentials from error text; **three** credential leaks (`;`-password, bare host, `KEYWORD=`-in-password) were found by adversarial Opus review and fixed. C2 secret-scan extended to ODBC/MySQL/Snowflake shapes without weakening detection. |
| `retail check` | exit 0 (static gate clean). |

## 5. Honest limitations (Principle VIII — the human should know)

- **CI cannot verify live per-engine behavior.** The suite proves the *generated SQL and
  translation/redaction logic* are correct; it does NOT prove SQL Server / MySQL /
  Snowflake *execute* it (no live instances in CI; drivers not installed). Live
  per-engine validation is deferred under Principle VIII — same bucket as the existing
  deferred Postgres live run.
- **The branch predates `main`'s design-governance wave.** It branched at `275e455`;
  `main` later added rule DR1 + manifests (PR #158). The DR1 manifest was synced in
  (`chore: 451fee2`); full reconcile happens at merge. Rule-code edits (B1/B3/C2) were
  verified by pytest because the editable `retail` install points at the **main**
  checkout, so the live gate runs main's rule copies, not these edits.
- **Governance-adjacent change flagged:** this branch also **extends what C2 catches**
  (new connection-string shapes). Changing gate coverage is part of what is being
  ratified here — call it out explicitly.

## 6. What the agent did NOT do (the seam it stopped at)

- Did NOT edit `.specify/memory/constitution.md`.
- Did NOT merge to `main`.
- Did NOT mark any readiness stage `pass`.
- Did NOT emit a numeric confidence/health score.

## 7. To ratify (the human's action)

1. Review §3 (proposed text), §4 (evidence), §5 (limitations).
2. If accepted: apply the §3 edits to `.specify/memory/constitution.md` (a human edit),
   bump the constitution version + amendment log per the repo's amendment convention,
   and record the ratifier + date.
3. Then the branch may merge. Until step 2 is a named human's committed act, the branch
   stays open and unmerged.
