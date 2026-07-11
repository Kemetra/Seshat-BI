# Demo Harness -- `retail demo` (spec 083)

- **On-disk spec:** `specs/083-demo-harness/`  **Roadmap feature:** F083.
- **Skill/surface:** the `retail demo` CLI verb group (`src/seshat/demo/`).
- **Sample data:** `tests/fixtures/demo/demo_sample_orders.csv` (GENERIC, invented;
  not client data, not C086). Mapping-gate + readiness fixtures:
  `mappings/demo_sample_orders/`.

## What it is

A local, offline-first demo that proves the readiness spine end-to-end on a small,
invented, generic sample dataset -- so an evaluator can see the kit work on a fresh
clone without a database, secrets, or cloud. Four verbs:

```bash
retail demo init      # materialize the committed fixtures into .demo-work/ (git-ignored)
retail demo load      # offline: skip with a reason; live: write demo-scoped tables
retail demo run       # recompute per-stage readiness status (offline, or live if a DSN resolves)
retail demo report    # render status + evidence + blockers (text | json)
```

## The honest spine (what the demo demonstrates)

Offline (the default, zero network / zero DB):

- **Source Ready / Mapping Ready / Silver Ready reach `pass`** -- backed by the
  committed mapping-gate artifacts + static `retail check`.
- **Gold Ready onward is `blocked` (deferred)** -- because Gold Ready's gate is the
  LIVE `retail validate`, which needs a reachable database. The demo draws this
  line honestly; it never fakes a live pass offline.

Optional live leg (only when a local Postgres DSN already resolves): `demo load`
writes the sample into DEMO-SCOPED objects (a safety guard -- it refuses to write
into a real `silver`/`gold` table), and `demo run` lets Gold Ready advance with
real live evidence.

## What it is NOT

- **NOT a dashboard generator.** `demo report` renders status/evidence/blockers
  only -- never a chart, image, or Power BI artifact (the release-notes non-goal;
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
