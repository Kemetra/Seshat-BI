# Demo Harness -- `seshat demo` (spec 083)

- **On-disk spec:** `specs/083-demo-harness/`  **Roadmap feature:** F083.
- **Skill/surface:** the `seshat demo` CLI verb group (`src/seshat/demo/`).
- **Sample data:** `tests/fixtures/demo/demo_sample_orders.csv` (GENERIC, invented;
  not client data, not C086). Mapping-gate + readiness fixtures:
  `mappings/demo_sample_orders/`.

## What it is

A local, offline-first demo that proves the readiness spine on a small, invented,
generic sample dataset -- so an evaluator can see the kit work from an installed
wheel or a fresh clone without a database, secrets, or cloud. Four verbs:

```bash
seshat demo init      # materialize the committed fixtures into .demo-work/ (git-ignored)
seshat demo load      # offline: skip with a reason; live: create the demo-scoped table shape (no rows)
seshat demo run       # recompute per-stage readiness status (records whether a DSN is reachable)
seshat demo report    # render status + evidence + blockers (text | json | html)
```

The deprecated `retail` alias is equivalent. The shortest visual proof is:

```bash
seshat demo init
seshat demo run
seshat demo report --format html
```

HTML defaults to `.seshat-output/demo/index.html`. Use `--output` only for another
path below `.seshat-output/`; the command refuses arbitrary filesystem writes.
The report is self-contained, deterministic, responsive, and usable without a
server. It embeds the packaged brand asset and contains no external requests.

## The honest spine (what the demo demonstrates)

Offline (the default, zero network / zero DB):

- **Source Ready / Mapping Ready / Silver Ready reach `pass`** -- backed by the
  committed mapping-gate artifacts + static `seshat check`.
- **Gold Ready onward is `blocked` (deferred)** -- because Gold Ready's gate is the
  LIVE `seshat validate`, which needs a reachable database. The demo draws this
  line honestly; it never fakes a live pass.

Optional live leg (only when a local Postgres DSN already resolves): `demo load`
creates the DEMO-SCOPED table shape (a safety guard -- it refuses to write into a
real `silver`/`gold` table, and it inserts no sample rows), and `demo run` records
that the database is reachable. Neither runs `seshat validate`, so **Gold Ready
stays blocked even on the live leg** -- a reachable connection is not live
validation. To take a real table past Gold, start a workspace with
`seshat init-project`, follow `seshat next` through source mapping and silver, then
pass `seshat validate --source-map <path>` against a live database.

## What it is NOT

- **NOT a dashboard generator.** `demo report` renders a readiness proof only --
  never a business chart or Power BI artifact (the release-notes non-goal;
  Principle II). Dashboards are designed from approved metric contracts, not
  auto-invented.
- **NOT a second state engine.** `demo run` recomputes from committed artifacts +
  gate outputs every time; there is no persisted run-state beyond a throwaway
  snapshot under `.demo-work/` (git-ignored). It never writes a tracked file.
- **NOT a numeric readiness score.** The four statuses (`not_started` / `blocked` /
  `warning` / `pass`) + evidence + blockers are the authority (hard rule #9).

## Relationship to the worked example

The demo is a *runnable* proof on generic data; the worked example
(`../worked-examples/retail-store-sales.md`, and its reading tour
`retail-store-sales-demo.md`) remains the richer reference for the fuller judgment
calls (PII, returns, discount) the small demo deliberately leaves out. See those
docs rather than duplicating them here.
