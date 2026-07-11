# Top Idea Bank Integration Smoke Test

## 1. Purpose

This document verifies the **integration** of the five merged top Idea Bank
features — **A1, B2, B1, F7, F8** (PRs #62–#66) — both with each other and with
the wider Seshat BI governance context.

What this is and is not:

- This **is** a smoke test artifact: a cheap, repeatable check that the five
  features cohere and still respect the project's boundaries.
- This is **not** an implementation, and it implements no idea.
- This is **not** another feature.
- This does **not** grant any readiness, dashboard, or publish approval.
- This does **not** promote the Idea Bank into the roadmap. The Idea Bank
  (`docs/roadmap/idea-backlog.md`) stays exploratory; this artifact authorizes
  no new work.
- It checks **both** feature-to-feature integration **and** governance / context
  alignment.

This is a **manual / static** smoke test, the same kind as
`docs/quality/agent-routing-smoke-test.md`. It is read (by a human or an agent)
against the current tree; it runs no database, no DAX, no Power BI, and asserts no
runtime behaviour. Everything below was verified by **static inspection of the
repository** (source, docs, and test source) — **not** by executing the CLI, the
pytest suite, or a live end-to-end agent walk. Where a claim could only be checked
statically, that is stated; nothing here is presented as an executed run.

## 2. Features Under Review

| PR | Idea | Feature | Integration responsibility |
|----|------|---------|----------------------------|
| #62 | A1 | Route Registry Manifest (`docs/routing/routes.yaml` + `src/seshat/rules/routes.py`) | Routes are machine-checkable and honest — a `built` target resolves to a real tracked file; a `planned` target must not yet exist. |
| #63 | B2 | Structured Findings Output (`retail check --format {text,json}`) | Findings can be emitted in structured form (opt-in JSON) without changing the default text output. |
| #64 | B1 | Never-Execute Invariant Guard (`src/seshat/rules/never_execute.py`) | Module-scope DB/network import creep is blocked; legitimate lazy in-handler imports are allowed. |
| #65 | F7 | KPI Decision-Question Index (`skills/retail-kpi-knowledge/domains/*.md`) | Business questions route to a real KPI contract or an honest planned/deferred marker. |
| #66 | F8 | KPI Coverage Scorecard (`skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`) | Table-to-KPI support is status/blocker-based, never score-based. |

## 3. Integration Model

The five features are expected to **reinforce each other, not bypass each other**:

- **A1** makes the routing / `retail check` surface **auditable**: every route in
  the registry resolves to a real file or is honestly marked planned. The shipped
  manifest mirrors the `docs/knowledge-map.md` "Route by task" rows (ids 1–22,
  including the KPI routes 12 / 12a / 12b that point at `retail-kpi-knowledge`).
- **B2** makes findings from the static checks **easier to consume**: A1's
  route-resolution failures and B1's never-execute violations are ordinary
  `Finding` objects, so the same opt-in JSON output represents them without any
  special-casing.
- **B1** protects the **non-execution invariant** of the agent-first system: it
  fails closed on a module-scope DB/network import in the static core while leaving
  the deliberate lazy-import pattern intact. A1 itself is a sibling of this
  invariant — it resolves references and runs nothing.
- **F7** improves how users **discover** KPI contracts by the business question
  each domain answers, always landing on an existing contract or a planned note —
  never inventing meaning.
- **F8** summarises **analytical coverage** for a source table using explicit
  statuses and named blockers, never a numeric score, and grants no readiness.

The throughline: A1 keeps the map honest, B2 makes the map's findings legible,
B1 keeps the whole system non-executing, and F7/F8 make the KPI meaning layer more
navigable — all without crossing a governance boundary or self-granting approval.

## 4. Smoke Test Scenarios

`Result` is the manual outcome cell. Each cell records what was **verified
statically at the docs/rule level**, not an executed end-to-end agent run (see the
note under each PASS).

| ID | Scenario | Touches | Expected route / behavior | PASS criteria | BLOCKED if | Result |
|----|----------|---------|---------------------------|---------------|------------|--------|
| IT-001 | "Which KPI answers: are discounts hurting margin?" | A1, F7 | Route via knowledge-map / route registry into `retail-kpi-knowledge` (routes 12/12a/12b); use the F7 question index; end at an existing contract or a planned note; do not open DAX first; do not invent a contract. | Lands in `retail-kpi-knowledge`; ends on a real `contracts/*.md` or planned marker; DAX not opened first. | Routing opens DAX first, invents a contract, or lands outside the KPI layer. | PASS (verified at docs/rule level) |
| IT-002 | A route points to a missing file. | A1, B2 | A1 route rule flags it as an ERROR `Finding`; B2 `--format json` can represent that finding with its `rule_id` / `severity` / `message` / `locator`; no runtime execution needed. | A1 emits an ERROR finding for the broken route; the finding serialises under `--format json`. | A1 cannot flag it, or the finding cannot be represented in structured output. | PASS (verified at docs/rule level) |
| IT-003 | A CLI/handler imports optional DB/YAML functionality **lazily** inside a handler. | B1 | B1 does **not** flag the lazy import; module-scope DB/network imports remain blocked; no DB/network connection is attempted. | Lazy in-handler imports pass; module-scope DB/network imports fail; no connection occurs. | B1 blocks a legitimate lazy import, or attempts a real connection. | PASS (verified at docs/rule level) |
| IT-004 | "What metric answers whether baskets are shrinking?" | F7 | F7 routes to the basket/transaction KPI domain; points to an existing or planned contract; invents no formula; does not move meaning into DAX/SQL/Python. | Lands in the basket/transaction domain; routes to a real or planned contract; no formula introduced. | A formula is invented, or meaning is pushed to an implementation layer. | PASS (verified at docs/rule level — routes to a **planned** marker; see note) |
| IT-005 | A source table has sales amount and quantity but no cost field. | F8 | F8 marks sales-related KPIs whose fields are present as Covered/reviewable; margin KPIs as **Blocked — missing field**; no percentage score; no readiness granted. | Sales KPIs with present fields Covered; margin KPIs Blocked on the named missing field; no number; no readiness. | A percentage/score appears, or coverage implies readiness, or a missing field is treated as silent coverage. | PASS (verified at docs/rule level) |
| IT-006 | "Write the DAX measure for Net Sales Growth." | A1, F7, governance | DAX may implement only after a KPI contract exists; if the comparison baseline is unresolved, route back to the KPI meaning layer / owner ruling; invent no DAX before contract completion. | Request routes back to the KPI layer when no ready contract exists; no DAX invented first. | A DAX formula is produced with no upstream contract. | PASS (verified at docs/rule level) |
| IT-007 | "Build an executive dashboard for branch performance." | F7, F8, governance | Dashboard is not the first stop; KPI pack / metric contracts required first; semantic-model readiness required before Power BI execution; F7/F8 grant no dashboard/publish readiness. | Dashboard gated behind contracts + `semantic_model_ready`; F7/F8 grant no readiness. | A dashboard/publish step proceeds without contracts or readiness, or F7/F8 implies readiness. | PASS (verified at docs/rule level) |
| IT-008 | A table supports many KPI fields. | F8 | F8 reports statuses/blockers only; produces no confidence/percentage/readiness/publish score; coverage is analytical reach, not readiness approval. | Output is statuses + blockers only; no numeric score; no readiness. | A numeric/percentage/readiness score appears. | PASS (verified at docs/rule level) |
| IT-009 | A route points to a CLI command or check. | A1, B1 | A1 resolves references only; runs no command; opens no DB or Power BI. | A1 only reads tracked files; no execution. | A1 executes a command, connects to a DB, or runs Power BI. | PASS (verified at docs/rule level) |
| IT-010 | A future idea appears in the Idea Bank or plan. | governance | Treated as exploratory unless promoted by the normal spec/feature process; the smoke test approves no new work; no next feature is implicitly authorized. | Idea stays exploratory; this artifact authorizes nothing. | This artifact is read as approving or scheduling new work. | PASS (verified at docs/rule level) |

### IT-001 — Route registry resolves KPI knowledge routes

A KPI / business-meaning question routes through `docs/knowledge-map.md` (routes
12 / 12a / 12b) and the A1 registry (`routes.yaml` ids 12 / 12a / 12b) into
`skills/retail-kpi-knowledge/` **first** (`SKILL.md` → `INDEX.md` → a
metric-contract / KPI-pack checklist), all of which are tracked and resolve. The
knowledge-map cross-layer guard states a metric-meaning request routes to Retail
KPI, **not** DAX, and that DAX must route back if no upstream contract exists — so
DAX is not opened first. "Are discounts hurting margin?" is answered **across two
domains** rather than a single row: `discounts-and-promotions.md` ("How much value
did we give away in discounts?" → `contracts/discount-amount.md`; "What share of
gross sales is discounted?" → `contracts/discount-rate.md`) and
`margin-profitability.md` ("How much profit did we make after cost of goods?" →
`contracts/gross-margin.md`; "What share of net sales is gross profit?" →
`contracts/gross-margin-percent.md`). All four targets are real seeded contracts;
no formula is implied.

### IT-002 — Structured findings can represent route failures

A `built` route pointing at a missing file is flagged by the A1 rule as a
`Severity.ERROR` `Finding` ("…points at … which is not a tracked file — the route
is broken"); the missing-manifest case also fails loud. Under `--format json`,
that finding serialises via `Finding.to_dict()` into a structured record. The
fields are `rule_id`, `severity`, `message`, and **`locator`** — note the path/line
is carried in the single `locator` string (e.g. `docs/routing/routes.yaml:<id>`),
**not** as separate `file` / `path` keys. No runtime execution is needed: the rule
reads tracked files only.

### IT-003 — Never-execute guard does not break legitimate lazy imports

B1's AST walker recurses into module-scope `Import` / `ImportFrom`, `try`/`except`,
and non-`TYPE_CHECKING` `if` nodes, but **never descends into `def` / `async def` /
`class` bodies** — so the deliberate lazy imports pass (e.g. `import psycopg2`
inside the CLI's driver handler and inside the live validator; `import yaml` inside
`dax_gen` / `metric_drift` / the A1 handler). Module-scope DB/network imports in the
governed static core remain blocked. The guard never opens a connection — it parses
source text with stdlib `ast` only and never imports or runs the scanned module; an
unparseable module becomes a `Finding` rather than a crash. A static scan of the
real governed modules (cli, runner, core, registry, and every `rules/*.py`) found
**zero** module-scope DB/network imports today — the invariant currently holds.

### IT-004 — KPI question index does not redefine metric meaning

"Are baskets shrinking?" routes to `basket-and-transactions.md`. The closest
question, "How many units are in a typical basket?", routes to a **planned**
marker (`—`, "Average Basket Size (Units)") — an honest deferred note, **not** a
fabricated contract. The related seeded rows in the same domain route to real files
(`contracts/transactions-count.md`, `contracts/average-transaction-value.md`). No
question implies a DAX/SQL/Python formula, and the domain's additivity guidance is
prose, so no metric meaning is pushed into an implementation layer.

### IT-005 — KPI coverage scorecard uses blockers, not scores

The scorecard template's worked example (`raw.sales`) is exactly this case: a
sales fact with quantity and transaction id but **no cost field**. KPIs whose
required fields are present are **Covered** (Quantity Sold, Transactions Count);
margin KPIs are **Blocked — missing field** ("cost amount (COGS) absent"). Other
sales KPIs in the example are correctly **Blocked** on an undecided VAT/returns
policy rather than silently covered — so coverage is not "all sales KPIs covered,"
it is per-KPI status + named blocker. No percentage appears, and no readiness stage
is granted.

### IT-006 — DAX request without KPI contract routes back to KPI layer

The DAX layer can implement only after a KPI contract exists. The knowledge-map
DAX route (12c) serves a *ready* business contract, and the cross-layer guard
states "DAX must stop and route back to Retail KPI if no upstream business contract
exists — it does not invent the meaning." For "Net Sales Growth," the comparison
baseline is an open policy in the time-intelligence domain (routed to a planned
marker), so the request routes back to the KPI meaning layer / owner ruling rather
than inventing a measure. (This DAX-before-contract ordering is encoded in the
knowledge-map route 12c + cross-layer guard and `COMPASS.md`, not in roadmap hard
rule #5 — see §5.)

### IT-007 — Dashboard request cannot bypass metric contracts

A dashboard request is not the first stop. Hard rule #5 ("No dashboard design
before metric contracts") and the `COMPASS.md` hard stop ("Stop if metric
contracts do not exist before dashboard design") gate it behind KPI contracts; the
existing routing smoke test (RT-007) gates the dashboard verb on "metric contracts
+ `semantic_model_ready: pass`." Power BI execution is separately gated behind
semantic-model readiness (hard rule #6, F016). **F7 and F8 grant no dashboard or
publish readiness** — F7 is pure KPI-meaning docs, and F8 explicitly grants no
readiness stage.

### IT-008 — Coverage scorecard does not become readiness score

F8 reports the fixed status set (Covered / Blocked — missing field / Blocked —
needs business definition / Planned / Out of scope) with named blockers. The
template states "never a number or percentage," "Never write a number," and "it
fabricates confidence (hard rule #9)." It grants no readiness ("a scorecard grants
no readiness stage and no dashboard/publish approval"); the KPI `INDEX.md` stop rule
repeats "Never grant readiness or dashboard-readiness from this layer." Coverage is
analytical reach, not readiness approval.

### IT-009 — Route registry does not execute routes

A1 resolves references only: it checks `target in ctx.tracked_files` and reads the
manifest's text. It contains no `os` / `subprocess` / `socket` / DB / network /
`exec` use; its only non-trivial import is a lazy `yaml`. It runs no command and
opens no DB or Power BI connection — consistent with the never-execute invariant
B1 protects.

### IT-010 — Idea Bank features remain separate from roadmap commitment

The Idea Bank banner states it is "not a roadmap and not a commitment … an idea
moves forward only through the normal spec/feature process, with a human decision."
The roadmap's idea-bank section confirms even the shipped A1/B2/B1/F7/F8 sequence
"remains exploratory; selection there was not a commitment." This smoke test is
docs-only: it changes no roadmap state, commits no Idea Bank item, and authorizes
no next feature.

## 5. Governance Alignment Checks

Each rule below was confirmed to be **actually written down** in the repo, so the
scenarios above can cite it honestly.

| Governance rule | Covered by | Expected result |
|-----------------|------------|-----------------|
| Agent-first, not CLI-first | hard rule #1 (`roadmap.md`); `COMPASS.md` ("the CLI gates … are helpers it calls, never the product") | The agent is the interface; `retail check` / `retail validate` are gates it calls. **Aligned.** |
| No execution during routing | `COMPASS.md` ("never executors … never run a query/DAX/Python or touch a database"); `knowledge-map.md` ("a router, not the knowledge base"; do-not list); A1 & B1 code | Routing/knowledge layers reason and resolve references; they execute nothing. **Aligned.** |
| Metric contracts before DAX | `knowledge-map.md` route **12c** ("for a *ready* business contract") + cross-layer guard ("DAX must stop and route back to Retail KPI if no upstream contract exists"); `COMPASS.md` DAX route | DAX implements only a ready contract; otherwise it routes back. **Aligned.** (Cite the knowledge-map route/guard, **not** hard rule #5.) |
| KPI meaning stays in `retail-kpi-knowledge` | `SKILL.md` ("owns the business meaning … governs meaning; other layers govern code"); `knowledge-map.md` cross-layer guard | KPI meaning is owned by one layer. **Aligned.** |
| SQL/DAX/Python do not redefine KPI meaning | `SKILL.md` boundary list; `knowledge-map.md` ("implement meaning, they do not redefine it"; do-not list) | Implementation layers consume a contract; they never redefine it. **Aligned.** |
| Readiness uses status/evidence/blockers | hard rule #9 (`roadmap.md`); readiness spine table | Readiness is `status` + `evidence` + `blocking_reasons`, not a fake score. **Aligned.** |
| Coverage is not a readiness score | F8 template ("never a number or percentage"; "grants no readiness"); `INDEX.md` stop rule | Coverage is statuses + blockers only. **Aligned.** |
| Dashboard does not bypass contracts | hard rule #5 (`roadmap.md`); `COMPASS.md` hard stop; RT-007 | Dashboard gated behind contracts + semantic-model readiness. **Aligned.** |
| Power BI execution remains gated | hard rule #6 (`roadmap.md`); `COMPASS.md`; F016 "NOT BUILT — gated, by design" | Execution adapter is last and gated on semantic-model readiness. **Aligned.** |
| Human approvals are not self-granted | constitution Principle V; `COMPASS.md` hard stops; roadmap Tier-5 binding rule | A stage's approval is a named human action the agent cannot self-grant. **Aligned.** |

## 6. Evidence Checklist

Each item was confirmed by static inspection (file:line cited in §8); none was
confirmed by executing the CLI or the test suite.

- [x] Route registry references resolve or use planned/deferred markers — all 26
  `routes.yaml` entries are `built` and every one of the 22 unique targets is a
  tracked file; an in-process resolution check returned 0 findings.
- [x] Structured findings output remains opt-in and does not change default
  behavior — default is `--format text` → the unchanged `run()`; JSON is opt-in.
- [x] No-execute guard blocks module-scope DB/network imports — `_FORBIDDEN_ROOTS`
  + `_FORBIDDEN_DOTTED`, flagged as ERROR findings in governed modules.
- [x] Lazy imports inside handlers remain allowed — the AST walker never descends
  into `def` / `async def` / `class` bodies.
- [x] KPI questions point to existing contracts or planned/deferred notes — every
  Seeded row maps 1:1 to one of the 10 real `contracts/*.md`; every Planned row
  uses the `—` marker.
- [x] KPI coverage scorecard uses statuses/blockers only — five enumerated
  statuses with named blockers.
- [x] No numeric confidence score appears — F8 states "never a number or
  percentage" / "Never write a number"; the only `%` occurrences are KPI names and
  the prohibition example.
- [x] No readiness/dashboard/publish gate is granted — F7/F8 grant no readiness;
  the dashboard/publish/F016 gates are intact.
- [x] No Power BI execution path is touched — A1/B1 are static; this artifact adds
  no execution.
- [x] Idea Bank remains exploratory — banner + roadmap idea-bank section confirm it.

## 7. PASS / BLOCKED Rules

**PASS if:**

- all smoke scenarios are satisfied by the current docs / rules / templates;
- no feature conflicts with another;
- no feature violates a governance boundary;
- missing future work is marked planned/deferred honestly.

**BLOCKED if any of:**

- any route points to a missing file without a planned/deferred marker;
- findings cannot represent route / no-execute issues;
- the no-execute guard blocks legitimate lazy imports;
- KPI question routes invent non-existing contracts;
- KPI coverage uses numeric confidence or a coverage percentage;
- any item implies readiness/dashboard/publish approval;
- any runtime/execution behavior is added by this PR.

## 8. Final Smoke Test Verdict

**Smoke test result: PASS**

This is PASS because the current `main` (after #62–#66) can be truthfully described
as coherent: an independent verification pass (six grounding checks + one
adversarial cross-check) found **no integration conflict** and **no governance
violation**, and every load-bearing claim resolved to exact file:line evidence. No
BLOCKED condition is triggered — all routes are `built` and resolve, A1/B1 findings
flow through the same structured-output chokepoint, B1 allows the real lazy imports
and itself executes nothing, F7 references only the 10 real contracts (planned rows
use markers), and F8 is status/blocker-only with no readiness granted. The
verification is **docs/source/static only**, which is the correct depth for a
docs-only smoke test.

### Evidence reviewed

- **A1:** `docs/routing/routes.yaml`; `src/seshat/rules/routes.py`;
  `tests/unit/test_routes.py`; `docs/knowledge-map.md`; wiring in
  `src/seshat/rules/__init__.py` + `tests/unit/test_rules_wiring.py`. An in-process
  run of `check_routes_resolve` over `git ls-files` returned 0 findings.
- **B2:** `src/seshat/runner.py` (`run`, `run_json`, `_collect`, `_exit_code`);
  `src/seshat/cli.py` (`--format` flag + dispatch); `src/seshat/core.py`
  (`Finding.to_dict`, `FindingDict`); `tests/unit/test_runner.py`,
  `tests/unit/test_cli.py`.
- **B1:** `src/seshat/rules/never_execute.py`; `tests/unit/test_never_execute.py`;
  wiring; a static scan of the 12 governed modules returned zero offenders.
- **F7:** all 11 `skills/retail-kpi-knowledge/domains/*.md`; `INDEX.md`; the
  `contracts/` directory (10 files).
- **F8:** `skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`
  and its `INDEX.md` route.
- **Governance:** `COMPASS.md`; `docs/knowledge-map.md`; `docs/roadmap/roadmap.md`
  (hard rules 1–9, F016 gating); `skills/retail-kpi-knowledge/SKILL.md`;
  `docs/roadmap/idea-backlog.md`; the existing `docs/quality/agent-routing-smoke-test.md`.

### Known limitations (not verified in this smoke test)

- The full `retail check` CLI was **not** invoked (text or `--format json`); B2's
  JSON shape, matching exit codes, and unchanged default output are verified from
  source + unit-test assertions read statically — **not** from a live CLI run.
- The pytest suite was **not** executed here; unit-test outcomes are described as
  *asserted in source*, **not** as passing runs.
- A1 was run in-process against `git ls-files`, **not** through a live end-to-end
  agent routing session; IT-001/IT-002/IT-009 are verified at the
  docs/routing/manifest/rule-code level.
- A1's **stale-planned-marker** path is verified by rule logic + one synthetic unit
  test only; the live manifest contains **zero** `planned` routes, so that path is
  **not** exercised by any shipped data.
- F7/F8 checks are static doc reads (filename existence + table-text inspection);
  the F8 scorecard's prescribed field-presence checks are documented via an
  explicitly *illustrative* worked example, not run against a live table.
- All governance / scenario findings are text + file:line alignment only; no
  runtime or agent walk was performed (this smoke test is manual by design).
- `yaml` is a lazy/optional dependency for A1; it imported successfully in the
  verification environment, but in a stripped stdlib-only environment A1 would raise
  `ImportError` at run time rather than emit a `Finding`. (Not verified in a
  stripped environment.)

### Follow-up recommendations (optional, not authorized here)

- A future PR could add an **execution record** (run `retail check --format json`
  and the pytest suite, cite exact output) to upgrade the docs-level PASS to an
  executed PASS — mirroring how `agent-routing-smoke-test.md` reserves a real run
  for a later PR.
- If a `planned` route is ever added to `routes.yaml`, re-confirm the
  stale-planned-marker path against real shipped data (currently logic/test-only).

> Per the repo's smoke-test discipline, this PASS is a **docs/static-level**
> result. It must not be read as an executed end-to-end run, and it does not
> fabricate a runtime PASS. It grants no readiness and authorizes no new work.
