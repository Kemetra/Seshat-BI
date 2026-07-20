# Post-Idea-Bank Capability State

A stable snapshot of what Seshat BI can do **now**, after the Idea Bank feature
sequence (#62–#66) and the integration smoke test (#68). It exists so the repo is
easy to navigate and future work does not drift before the next proof (the Net
Sales end-to-end trace).

This is a **state report**, not implementation. It builds nothing, claims no
runtime execution that does not exist, grants no readiness, and adds no feature.
Every capability below is cited to a real file; anything that could not be
confirmed from the repo is marked **Not verified**.

## What works now

- A **static governance gate**, `seshat check`, with its full registered rule set
  (catalog: `docs/glossary.md`; live count via `retail.registry.all_rules()`,
  pinned by `tests/unit/test_rules_wiring.py` `EXPECTED_RULE_IDS`). It reads
  committed files only; it is stdlib-only at import.
- **Route integrity** — Idea A1, a **registered rule** (`A1`):
  `docs/routing/routes.yaml` mirrors the knowledge-map routes; the A1 rule fails
  on a `built` route whose target is missing, or a `planned` target that now
  resolves. Read-only.
- **Structured findings** — Idea B2, a **CLI rendering feature, not a rule**:
  `seshat check --format json` is an opt-in JSON rendering (`run_json` in
  `src/seshat/runner.py`); the default text output is unchanged. (There is no
  registered rule id `B2`.)
- **Never-execute guard** — Idea B1, a **registered rule** (`B1`): a static `ast`
  scan blocks module-scope DB/network imports in the core; lazy in-handler imports
  stay allowed.
- **Five knowledge layers** under `skills/` (SQL, DAX, Python, Retail KPI,
  Big-data) — all **reasoning/review only**, routed two-hop (`SKILL.md` →
  `INDEX.md` → named file → artifact). Note the Python and Big-data layers are
  **initial seeds** (many routes are planned/deferred), unlike the fuller SQL/DAX
  and Retail KPI layers.
- **KPI discoverability**: F7 decision-question sections in all 11 KPI domain docs;
  F8 coverage scorecard template (statuses/blockers, never a score).
- **The readiness spine** as docs: the model + pipeline + seven stage docs under
  `docs/readiness/`.
- Additional static commands beyond `check`: `semantic-check` (L3 contract↔DAX
  drift) and `value-check` (L4 value proxy) and `generate` (DAX from a contract).

## What is planned / deferred

- **Live validation depth** (`retail validate`): the surface is **built and
  fixture-tested**, but a real run needs a running Postgres, the optional `db`
  extra (psycopg2), and a filled `source-map.yaml`; without those it reports the
  **deferred state** (verified: `src/seshat/cli.py` validate handler).
- **F016 Power BI execution adapter**: NOT built — gated and deliberately last
  (verified: `docs/roadmap/roadmap.md`).
- **Planned KPI contracts**: KPIs beyond the 10 seeded contracts are marked
  Planned in the KPI domains and return planned/deferred notes (verified:
  `skills/retail-kpi-knowledge/domains/*.md`, F7 markers).
- **Big Data capability**: not present as a runtime; the `bi-bigdata-knowledge`
  layer is reasoning-only. (Scale strategy is the subject of a later planned PR;
  see `docs/planning/post-integration-stabilization-plan.md`.)

## What is explicitly forbidden

(verified against `docs/roadmap/roadmap.md` hard rules and `COMPASS.md` hard stops)

- No source straight to silver; no silver without profile + map + declared grain +
  reviewed unresolved questions.
- No dashboard design before metric contracts; no Power BI execution before
  semantic-model readiness (F016 gated/last).
- Knowledge layers never execute (no running SQL/DAX/Python, no DB/network).
- No self-granted human approval; no readiness `pass` without evidence + a named
  human.
- No fake confidence scores; readiness is status + evidence + blockers.
- No Big Data tooling before proven need.

## What requires human ruling

- KPI policy decisions (VAT included/excluded, returns handling, cost method,
  same-store rule, snapshot date) — a contract is **Needs business definition**
  until the owner decides (verified:
  `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md`,
  `skills/retail-kpi-knowledge/knowledge/metric-contracts.md`).
- Every readiness stage `pass` — a named human action the agent cannot self-grant.

## What requires real data

- Any `retail validate` live check (PK/coverage/orphans/reconcile) — needs a DB +
  the `db` extra + a filled source-map.
- The L4 `value-check` value proxy — needs a live runner.
- Reconciliation of actual gold totals to source.
- Any "covered" cell in an F8 scorecard that asserts a field is present — must be
  confirmed against the real source, not assumed.

## Capability table by layer

| Layer | Owns (works now) | Must not own | Status |
|-------|------------------|--------------|--------|
| Route / gate integrity | Machine-checkable routes (A1); the static `seshat check` gate | Executing the routes/commands it references; granting readiness | Works now (static) |
| Structured findings | Opt-in JSON rendering of findings (Idea B2 — a CLI flag, not a rule) | Changing default output; altering rule behaviour | Works now |
| Never-execute guard | Static `ast` block on module-scope DB/network imports (B1) | Opening a real connection; blocking legitimate lazy imports | Works now |
| SQL knowledge | Grain/keys/joins/fan-out, COUNT/NULL semantics, transform & reconciliation reasoning | Running SQL; defining KPI meaning | Reasoning only |
| DAX knowledge | Measure shape, filter context, time-intelligence, model prerequisites — for a **ready** contract | Running DAX; redefining a KPI's business meaning | Reasoning only |
| Python knowledge | Single-node dataframe source-prep/cleaning/aggregation-grain reasoning | Running Python; distributed execution; defining KPI meaning | Reasoning only (seed) |
| Retail KPI knowledge | **Business meaning** of KPIs + metric contracts (10 seeded) | Writing SQL/DAX/Python; approving readiness; designing dashboards | Owns meaning |
| Readiness spine | Stage model + per-stage docs + status vocabulary (status/evidence/blockers) | Self-granting a `pass`; fabricating a score | Docs (human-gated) |
| Dashboard / Power BI boundary | Design **from approved contracts** (skill); the F016 boundary | Designing before contracts; executing/publishing before semantic-model readiness | Design skill present; **execution (F016) not built, gated** |

## Known limitations

- This snapshot is a **static read** of the repo; it asserts no live run. `retail
  check` / the test suite were not executed to produce this document.
- Live validation, the L4 value proxy, and any real reconciliation are **deferred
  on real data** (built surfaces, not exercised here).
- KPI coverage beyond the 10 seeded contracts is planned/deferred; coverage
  "covered" claims still require confirming fields against a real source.
- **Not verified** in this snapshot: any end-to-end agent routing walk, and any
  claim that a specific KPI path reconciles against real data — that is exactly
  what the next proof should establish.

## Recommended next proof

The first end-to-end proof is the **Net Sales end-to-end readiness trace**
(`docs/demo/net-sales-end-to-end-readiness-trace.md`, shipped): a single KPI path
walked from business question → contract → required fields → source/table coverage
→ blockers → SQL/gold expectation → DAX/semantic readiness → dashboard usage →
readiness gates, with an explicit "proven on paper vs needs real data" split. One
honest end-to-end proof should land before any broader (scale) capability work.
