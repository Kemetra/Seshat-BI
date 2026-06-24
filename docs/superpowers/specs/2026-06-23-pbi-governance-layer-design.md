# Retail Tower Power BI Governance Layer — Design

- **Date:** 2026-06-23
- **Status:** Draft (brainstorming — awaiting user review)
- **Scope (this pass):** The **static governance core (A)** + its CI/Claude seams. Live
  checks and full Claude orchestration are designed as seams but deferred.
- **Repo:** `Retail_Tower_analytics`
- **Supersedes (partial):** the source-layer naming in
  `2026-06-22-analytics-skeleton-design.md` — `raw`/`marts` is now medallion
  `bronze`/`silver`/`gold`; Power BI reads **gold** only.

---

## 1. Vision (one line)

> Turn Retail Tower's **advisory** Power BI conventions into **enforced, checkable
> guarantees** — a layer that *depends on* (never forks) `pbi-cli`, gates the Power BI
> model and reports as plain text, and makes the wrong modeling action fail loudly.

`pbi-cli` is maximally *capable* but *opinion-less* — it will happily let you reference
`bronze`, bake in a connection string, or flip a relationship bidirectional. The gap
between that generic tool and *this* specific data product is exactly where this layer
lives. The leap is from **prose that asks nicely** (today's `powerbi-analyst.md` /
`pbip-workflow`) to a **validator that exits non-zero**.

## 2. Decisions (settled in brainstorming)

| # | Question | Decision |
|---|----------|----------|
| 1 | Fork or depend? | **Depend.** Install `pbi-cli` via `pipx` (PyPI `pbi-cli-tool`); build the layer in *this* repo. Zero fork tax; every upstream upgrade is free. |
| 2 | Scope this pass? | **Static core (A) first**, designed so CI (C) and Claude UX (D) snap on. |
| 3 | Source layer? | **Gold-only.** Power BI reads the `gold` schema; never `bronze`/`silver` (or legacy `raw`/`marts`). |
| 4 | Time-intelligence rule? | **Static now** (date-marker must exist when TI used); **live contiguity deferred** (needs running Desktop). |
| 5 | YAGNI/scope rule? | **Document only, never gate.** A presence-scanner would false-flag sanctioned ETL (`pipelines/load_bronze.py`). |
| 6 | Language? | **Python** — matches the machine (miniforge), matches `pbi-cli`, matches global rules. |

## 3. The big picture (A → C → D)

```
   D  Claude experience      "Build the gold sales report"                  ← surface
      (retail-govern skill,  Claude orchestrates gold SQL + pbi-cli build,
       powerbi-analyst agent) runs checks, self-heals.   [ORCHESTRATION DEFERRED]
                                    │ drives & is gated by
   C  Automation / CI        pre-commit hook + GitHub Action:               ← unattended
                             run STATIC checks on commit/PR, block on
                             violation.                  [SEAM THIS PASS]
                                    │ runs
   A  Governance core        ┌─ STATIC surface ─────────┬─ LIVE surface ──┐ ← FOUNDATION
      (THE SHIPPABLE UNIT)   │ retail check             │ retail validate │   (ship A)
                             │ parses committed text    │ wraps pbi-cli   │
                             │ TMDL / PBIR / SQL / git   │ needs Desktop   │
                             │ 23 rules, CI-able         │ 1 rule, local   │
                             │ NO pbi-cli, NO model      │ [DEFERRED]      │
                             └──────────┬────────────────┴─────────────────┘
                                    │ engine for D's authoring + the live check
   ENGINE                     pbi-cli (pipx, unforked, upgradeable)
                                    │ executes against
                             Power BI Desktop  +  DigitalOcean Postgres (gold)
```

**Why this is "the most powerful":** (1) *enforced, not advised* — a non-zero exit is
categorically stronger than a paragraph; (2) *compounds* — A is the foundation, C is
"run A unattended," D is "drive A conversationally," each multiplying the last; (3) *no
fork tax* — your opinion lives in your repo, layered atop an upgradeable engine.

## 4. The enforcement split (the spine)

Every convention is sorted by **what a checker can *see***:

- **STATIC** — a violation is detectable by parsing committed text (TMDL, PBIR JSON,
  SQL, git metadata) with **no running Power BI Desktop and no `pbi-cli`**. CI-able,
  OS-independent. **This is the powerful core.**
- **LIVE** — detection genuinely needs a running Desktop model via `pbi-cli`
  (materialized data, real DAX compilation). Local-only, **not** CI-able.

> **Verified against `pbi-cli`'s README:** there is **no offline/file-only DAX syntax
> check** — `dax validate` and every semantic-model read require a live `pbi connect`.
> So even "real DAX validity" is a *live* concern. The static surface relies on parsing
> committed TMDL text directly, never on `pbi-cli`.

## 5. Static rule catalog (the shippable core — 23 rules)

> Count: S1·S2·S3·S4a·S4b (5) + D1–D8 (8) + R1 (1) + C1·C2 (2) + G1–G5 (5) + P1·P2 (2) = **23**.
> (Was "22" in an earlier draft, before the adversarial review split S4 into S4a + S4b.)

Each rule names the committed artifact it parses and the violation signal. Grouped by
domain. These are the spec for `retail check`.

### 5.1 SQL (`warehouse/**/*.sql`)
- **S1 snake_case identifiers** — declaration-position identifiers must match
  `^[a-z_][a-z0-9_]*$`; flag quoted/bracketed identifiers with uppercase/spaces.
- **S2 medallion schemas** — schema identifiers must be `bronze`/`silver`/`gold`; flag
  stale `raw`/`marts` *schema* tokens. **Match only in schema-qualifying positions:**
  `CREATE SCHEMA <id>`, the schema part of a `schema.object` qualifier, M `Schema="…"`,
  and native-SQL `FROM <schema>.<obj>`. This avoids false positives on identifiers that
  merely contain the substring (`raw_amount`, `silver_threshold`). Parameterized/aliased
  sources are an accepted false-negative. **Docs exemption (concrete):** files that
  authoritatively quote legacy names are exempt from the content scan — currently
  `warehouse/README.md`. Files that should be *rewritten now* (not exempt) are listed in
  §12.
- **S3 `vw_` view prefix** — `CREATE VIEW` carries the object kind, so the `vw_` prefix
  is checkable. *(The `fct_`/`dim_` table prefix is NOT mechanically decidable — see Gaps.)*
- **S4a migration filename/numbering (deterministic)** — filenames must match
  `^\d{4}_.+\.sql$`; numbering must be contiguous and unique across `warehouse/migrations/`.
- **S4b migration guard-form (heuristic, WARNING)** — accepted guarded forms are
  `CREATE TABLE … IF NOT EXISTS`, `CREATE OR REPLACE VIEW`, `ALTER TABLE … IF [NOT] EXISTS`,
  `DROP … IF EXISTS`. Any bare `CREATE`/`ALTER` outside that set is a **warning** (true
  semantic idempotency and apply-order are out of static scope).

### 5.2 TMDL / DAX (`*.SemanticModel/definition/**/*.tmdl`)
- **D1 PascalCase measures** — measure names must match `^[A-Z][A-Za-z0-9]*$`.
- **D2 displayFolder required** — each measure block must carry a `displayFolder`.
- **D3 no duplicated measure logic (provable core)** — normalize measure bodies (strip
  comments, collapse whitespace, canonicalize case/refs), hash, flag exact collisions and
  bodies that inline another measure's full body instead of referencing `[Name]`.
  Semantic "same concept" is advisory (Gaps).
- **D4 `DIVIDE()` not `/`** — lex each measure expression, strip comments and string
  literals, flag **any** surviving `/`. *(Future refinement, not this pass: exempt a
  numeric-literal RHS like `/100`. Decided against now to keep the rule deterministic.)*
- **D5 explicit over implicit aggregation (WARNING)** — flag **any** numeric column with
  `summarizeBy != none` as a warning, with an annotation/allow-list escape for intentional
  implicit aggregations. *(The "fact-table only" scoping is dropped — no static fact/dim
  signal exists; see Gaps. The VAR/RETURN-readability half also has no signal — dropped.)*
- **D6 single-direction relationships** — parse `relationships.tmdl`; flag any
  `crossFilteringBehavior: bothDirections` for human justification (the many-to-many
  escape clause is surfaced, not auto-resolved).
- **D7 time-intelligence date marker (static half)** — if any TI function in the **closed
  trigger set** appears, at least one table must carry a date-table marker.
  Trigger set (closed; extend only by versioned constant): `TOTALYTD`, `TOTALQTD`,
  `TOTALMTD`, `DATESYTD`, `DATESQTD`, `DATESMTD`, `SAMEPERIODLASTYEAR`, `DATEADD`,
  `DATESINPERIOD`, `DATESBETWEEN`, `PARALLELPERIOD`, `PREVIOUSYEAR`, `PREVIOUSQUARTER`,
  `PREVIOUSMONTH`, `PREVIOUSDAY`, `NEXTYEAR`, `NEXTQUARTER`, `NEXTMONTH`, `NEXTDAY`,
  `OPENINGBALANCEMONTH`/`QUARTER`/`YEAR`, `CLOSINGBALANCEMONTH`/`QUARTER`/`YEAR`,
  `STARTOFYEAR`/`QUARTER`/`MONTH`, `ENDOFYEAR`/`QUARTER`/`MONTH`, `FIRSTDATE`, `LASTDATE`.
  Necessary-not-sufficient; contiguity is the live half (§6).
  **Implementation note:** the exact "Mark as Date Table" TMDL literal is *not yet pinned*
  — in TMDL it is typically a table-level annotation/property, not column-level
  `dataCategory: Time` alone. Before building D7, capture one real "Mark as Date Table"
  TMDL fixture, pin the marker to the verified literal(s), and lock it as the passing test.
- **D8 gold-only sourcing** *(central rule)* — parse every partition `source` and shared
  `expression` block (M + embedded native SQL); flag any schema token `!= gold`
  (matching `bronze|silver|raw|marts`). **Match only in schema-qualifying positions**
  (same mechanism as S2): M `Schema="…"` and native-SQL `FROM <schema>.<obj>`.
  Parameterized/aliased sources are an accepted false-negative.

### 5.3 PBIR / report (`*.Report/definition.pbir`, report JSON)
- **R1 relative model reference** — in `*.Report/definition.pbir`,
  `datasetReference.byPath.path` must be relative; flag absolute paths (`^[A-Za-z]:`, `^\\`,
  `^/`) or an unexpected `byConnection`. Locator: `definition.pbir` + JSON pointer. (The
  "one model per subject area" sub-clause is not enforceable — Gaps.)

### 5.4 Connection / secrets
- **C1 parameterized connection** — in TMDL partition source M and parameter expression
  defaults, the server/database args of `PostgreSQL.Database`/`Sql.Database`/
  `Odbc.DataSource` must be parameter identifiers, not string literals; flag connection-
  string literals (`Host=`/`Server=`/`Database=`/`User Id=`/`Password=`). Argument-
  position-sensitive, so legit literals (schema `gold`, sslmode) are not flagged.
- **C2 no committed secrets** — assert `.env` is gitignored and absent from `git
  ls-files`; assert `.env.example` has the six `ANALYTICS_DB_*` keys with
  HOST/NAME/USER/PASSWORD empty; regex-scan tracked files for
  `postgres(ql)?://[^@]+@…` and a **real** DigitalOcean endpoint shape — a concrete
  subdomain label followed by `.db.ondigitalocean.com`, **excluding angle-bracket
  placeholders** like `<your-db-host>.db.ondigitalocean.com`. The content scan **excludes
  `docs/` and `*.example` files** (they hold documentation placeholders, not secrets).
  *(Verified false-positive this fix prevents: `docs/powerbi-connection.md` placeholder.)*
  Recall is best-effort, intrinsic to all secret scanning — do not claim completeness.

### 5.5 PBIP / git hygiene
- **G1 `.gitignore` correctness** — (a) **MUST-contain subset:**
  `**/.pbi/localSettings.json`, `**/.pbi/cache.abf`, `.env`. (b) **MUST-NOT-ignore
  predicate:** no pattern may match any `definition/` path — verify with `git check-ignore`
  on synthesized PBIP paths. **Any other ignore entries are permitted** (the repo's
  Python/OS/editor blocks are fine); this is a subset assertion, not an exact match.
- **G2 definition artifacts committed** — `git ls-files` + `git check-ignore`: fail if any
  `*.SemanticModel/definition/**`, `*.Report/definition/**`, `definition.pbir`,
  `.platform`, or `*.pbip` is untracked/ignored, or any `.pbi/localSettings.json`/
  `cache.abf` is tracked. **Empty-case:** if *no* PBIP project exists yet (current repo
  state), G2 emits an **informational** "no PBIP project present" signal — it must NOT
  silently pass as if a model were verified.
- **G3 UTF-8 without BOM** — first 3 bytes of each committed `*.tmdl`/`*.pbir`/`*.json`/
  `*.pbism`; flag a leading `EF BB BF`.
- **G4 `.gitattributes` EOL policy (MUST-contain subset)** — each *required* glob must map
  to its required eol/binary (TMDL/PBIR/PBISM/JSON=CRLF; SQL/MD/PY=LF; pbix/abf/png=binary);
  cross-check with `git ls-files --eol`. **Extra benign entries are permitted** (the repo's
  `* text=auto` catch-all and `*.svg text eol=lf` are allowed, not flagged). This is a
  subset check, not exact. (`core.autocrlf` is local config, not committed — out of scope.)
- **G5 Windows MAX_PATH discipline** — `git ls-files`; fail any **repo-relative** path
  whose length is **> 200 chars** (reserving headroom under the 260 absolute limit; the
  true absolute overflow depends on clone root, so a relative budget is what's enforceable).

### 5.6 Repo structure / process
- **P1 Approach-A layout** — assert required dirs/READMEs exist; flag any PBIP signature
  not under `powerbi/`, or any `*.sql` not under `warehouse/`.
- **P2 commit-message convention** — fail subjects not matching
  `^(feat|fix|refactor|docs|chore): .+`. The 5-type set is authoritative per
  `conventions.md:25-26` (narrower than the global set — by design, not a defect).
  **Scan range (not all history):** in CI, the PR's `BASE..HEAD` range; in the commit-msg
  hook, the single incoming message. **Merge commits are exempt** (auto-generated subjects).

## 6. Live rule (deferred — the only one)
- **L1 date-dimension contiguity** — verify the marked date column has contiguous, gap-free
  dates. Needs **materialized rows**, so it requires a running Desktop via `pbi connect`
  + `pbi dax execute`. Built as `retail validate` later; **designed as a seam now, not
  built this pass.** This is the *single* genuinely live-surface requirement in the layer.

## 7. Not enforceable (document as human-judgment, never gate)
- **PBIP preview toggle** — lives in Desktop's local app settings; no committed artifact.
- **Don't hand-edit Desktop-owned files / restart Desktop** — a sanctioned save and a
  forbidden hand-edit are textually identical; no provenance signal.
- **YAGNI / scope discipline** — "no ETL/provisioning unless requested": the
  authorization fact lives only in conversation/PR history. `pipelines/load_bronze.py` is
  sanctioned ETL a presence-scanner would false-flag. **Document in the agent prompt;
  the checker stays silent** (keeps the gate trustworthy).

## 8. Known gaps (stated conventions with no clean checker)
- `fct_`/`dim_` table prefix — `CREATE TABLE` carries no fact/dim signal; only `vw_` is
  checkable. *(This is why D5 is scoped model-wide as a warning, not "fact tables only".)*
- "One measure per business concept" beyond exact duplicates — semantic equivalence has no signal (advisory).
- "One semantic model per subject area" — no committed artifact defines subject-area groupings.
- "Shape problems fixed in `warehouse/`, not DAX" — design-intent norm, no parse signal.
- "VAR/RETURN for readability" — no textual signal (dropped).
- `core.autocrlf=true` — local config, not committed.
- **No offline DAX validation in `pbi-cli`** — any real DAX compilation gate is live-only.

## 9. The shippable unit (this pass)

A `retail/` Python package providing a `retail check` command. **The checker package has
NO runtime dependency on `pbi-cli`** — it parses committed files and git metadata, so it
runs anywhere with plain Python and no Power BI Desktop. `pbi-cli` is only touched by the
deferred live surface (L1) and D-orchestration. (The shippable core sits *beside* pbi-cli
checking the same files, not *on top of* it — do not add a `pbi-cli` dependency to this
package.) Decomposed into **ordered milestones along the parser-surface cut** so each
checker builds and tests independently — the runner contract first:

0. **Golden PBIP fixture + parser search-first** *(gates all model rules — do this first)*.
   The repo has **zero committed PBIP today**, so D1–D8, R1, and C1 are currently specified
   against an *assumed* TMDL/PBIR/M token shape (this caveat is not D7-only — it applies to
   every model-layer rule). Before pinning any model-rule pattern: (a) generate one real
   PBIP (`pbi report create` + a minimal semantic model, or Save-as-PBIP from Desktop once),
   commit it as a **golden fixture**, and pin every model token (`byPath.path`,
   `crossFilteringBehavior: bothDirections`, `Schema="…"`, `summarizeBy`, the date-table
   marker, the C1 parameter-default position) against the *observed* literals; (b)
   **search-first**: confirm whether a pure-Python TMDL/PBIR parser exists before
   hand-rolling a lexer (TOM reads TMDL but only via the Windows/.NET live path, which
   defeats CI — so it's not an option for the static checker).
1. **Runner contract + package skeleton** — the rule-registry/runner: each rule declares an
   `id`, `severity` (`error`/`warning`/`info`), a `locator` emitter, and a finding message;
   the runner aggregates findings and sets the exit code (non-zero iff any `error`).
2. **Git-metadata rules** — C2, G1, G2, G5, P1, P2 (operate on `git ls-files` /
   `check-ignore` / `log`, not file contents). *These 8 have real artifacts to check today.*
3. **SQL rules** — S1, S2, S3, S4a, S4b (lexer over `warehouse/**/*.sql`).
4. **TMDL + M rules** — D1–D8, C1 (TMDL block parser + M/native-SQL source parser; needs
   the milestone-0 fixture).
5. **PBIR rule** — R1 (PBIR JSON; needs the milestone-0 fixture).
6. **C-seam** — pre-commit hook + CI workflow stub that run `retail check`.
7. **D-seam** — point the `powerbi-analyst` agent at the checker, and author a new
   `retail-govern` skill. **Bounded scope:** the skill *references/invokes the checker and
   its rule ids only* — **NO orchestration or self-heal**, which remain the deferred D work.
8. **Doc reconciliation** (see §12) — fix stale `marts` references so S2/D8 are green on the
   current repo; this is a *deliverable*, not incidental.

**Build all 23 rules this pass.** Spec 2 (medallion warehouse) is imminent, so the SQL +
model rules (milestones 3–5) will have real `gold` SQL and a `.pbip` to gate within weeks —
they are built now, not deferred. *(Had Spec 2 been months out, the immediately-live subset
would be milestones 1–2 + C2 only, deferring 3–5 with the fixture. It is not.)*

Per-rule acceptance: each rule has a passing and a failing fixture and emits its locator +
rule id on violation. Warnings (S4b, D5) do not fail the build.

**Deferred (seams documented, not built):** `retail validate` (live surface, L1), full
CI enforcement tuning, full D orchestration ("build the report" end-to-end), auto-fix.

## 10. Out of scope (YAGNI, this pass)
- Forking `pbi-cli`. Live DAX execution in CI (impossible — no Desktop).
- Auto-fixing violations (detect first; fix later).
- Real `gold`-schema SQL content or actual `.pbip` projects beyond what the repo already has.
- Orchestrator / contract-boundary integration.
- **The medallion warehouse itself** — the `bronze`→`silver`→`gold` transformations
  (cleaning, typing, mart-building SQL) are a **separate product** (future *Spec 2 —
  Medallion Warehouse*). This governance layer only *verifies* the contract that warehouse
  produces (D8: the model reads `gold`; S1–S4: medallion naming) — it does not *build* the
  layers. `pipelines/load_bronze.py` (the bronze load) already exists; silver/gold SQL is
  Spec 2's job, built later under this gate. Build order: **this spec first, Spec 2 next.**

## 11. Success criteria
- `retail check` runs with **no `pbi-cli` and no Power BI Desktop**, on any OS, in CI.
- Each of the **23 static rules** has a stable id, a unit test with a passing **and** a
  failing fixture, and emits its **rule id + most specific locator** on violation —
  `file:line` for in-file violations; otherwise a file path, git ref, or commit SHA (the
  git-metadata rules C2/G1/G2/G5/P2 have no natural line number).
- **Empty-repo distinction (important):** "rule unit tests pass" (bullet 2) is the real
  gate this pass. The *repo baseline* is currently **vacuously clean** — the repo has no
  committed SQL or PBIP text, so S1–S4, D1–D8, R1, C1 have nothing to parse and G2 reports
  "no PBIP project present". The baseline must be **re-asserted once real `gold` SQL and a
  committed `.pbip` land** — passing today does not mean the model rules are exercised.
- After the §12 doc reconciliation, `retail check` is **green on the current repo** (no
  C2/S2/D8 false positives) — verified, not assumed.
- The pre-commit hook and CI stub invoke it; an `error`-severity violation blocks the commit/PR.
- `powerbi-analyst.md` and the new `retail-govern` skill reference the checker and rule
  ids rather than duplicating the rules in prose.
- The gold-only rule (D8) supersedes the old marts-only language everywhere (see §12).

## 12. marts→gold reconciliation (a declared deliverable, §9 step 8)

Verified by grepping the repo. The stale surface splits three ways; getting this wrong is
how `retail check` would flag the repo's own docs on day one.

**Rewrite now (genuinely stale `marts`/`raw` as the schema):**
- `docs/conventions.md:16` — "read from `marts` only" → "read from `gold` only".
- `docs/powerbi-connection.md` — schema parameter `marts` → `gold` (`:68`), and the
  "reads marts only (never raw)" lines (`:21`, `:36`, `:81-82`, `:134`).
- `docs/data-dictionary.md:3,5,13,15` — `raw`/`marts` section headers → `bronze`/`gold`.
- `powerbi/README.md:26` — "Read from `marts`, not `raw`" → "Read from `gold`".
- **Directory:** `warehouse/marts/.gitkeep` → `warehouse/gold/.gitkeep` (gold-only implies a
  `gold/` folder). Update `warehouse/README.md:22` which already calls it "marts/ … for the
  `gold` schema".

**Exempt from S2 (authoritative legacy quote — keep as-is):**
- `warehouse/README.md:15-17` — deliberately documents "earlier drafts used `raw`/`marts`;
  the deployed DB uses bronze/silver/gold." A correct historical note; S2 must whitelist it.

**Do NOT flag (false alarms — confirm the checker is silent here):**
- `pipelines/load_bronze.py`, `pipelines/README.md` — use the *English* "raw text"
  (faithful source data), not a schema identifier. S2's schema-position matching must pass these.
- `docs/conventions.md:6-7` — already correct medallion (`bronze`/`silver`/`gold`).
- `docs/superpowers/specs/2026-06-22-*.md` and `plans/2026-06-22-*.md` — **frozen historical
  artifacts**, superseded (this spec's header says so). Not rewritten; out of the content scan.

## 13. Other open items (for the implementation plan)
- **Golden PBIP fixture first** (§9 milestone 0) — *all* model rules (D1–D8, R1, C1), not
  just D7, are pinned against an assumed format until a real PBIP is captured and committed.
  This was the key finding of the external (advisor) review; it gates milestones 4–5.
- **D7/L1 split** confirmed: ship the static date-marker conjunct; defer contiguity to a
  documented live seam. Pin the "Mark as Date Table" TMDL literal from the milestone-0 fixture.
- **Secret-scan recall** is best-effort by nature — document the limitation; don't claim
  completeness.
- Also reconcile the `powerbi-analyst` agent prompt and `pbip-workflow` skill, which state
  the conventions in prose — point them at the rule ids (the §9 step-7 D-seam).
