# Power BI Connection Flow

How this repo expects Power BI to reach the analytics data **later**. This is a
documentation contract only — there is no live connection, no credentials, and no
gateway machine config in this repository. Real values live outside git, in the
user's Power BI settings and gateway/credential store.

> Status: the DigitalOcean PostgreSQL analytics database and the Power BI **gateway**
> are configured **outside this repo**. Nothing here connects to a live database.
> When a report is built, the steps below describe how it should be wired.

## Three things that are easy to confuse

These are distinct surfaces. Only the **gateway** is the data-refresh path; the
**Desktop Bridge** is unrelated to database connectivity.

| # | Thing | What it is | Proves DB connectivity? |
|---|-------|------------|--------------------------|
| 1 | **Power BI Desktop Bridge** (IPC Bridge) | A *local* named-pipe API (`pbi-desktop-bridge-${processId}`) hosted inside a running Power BI Desktop process, for automating/verifying Desktop authoring (read report definition, apply changes, screenshot). JSON-RPC over a pipe — **not** a cloud service, **not** REST. Preview feature. | ❌ No — it talks to Desktop, not to any database. |
| 2 | **Power BI Gateway** | The cloud/Service refresh path. Holds the data-source credentials and bridges the Power BI Service to an on-network/managed database. | ✅ Yes — a successful gateway refresh is the real connectivity test. |
| 3 | **DigitalOcean PostgreSQL** | The remote analytics database itself (`bronze` → `gold`). The actual data source. | — it *is* the source. |

See [the Desktop Bridge section](#power-bi-desktop-bridge-optional-future-local-verification)
below for how (and whether) this repo uses #1.

## The shape of the connection

```
Power BI (dataset / PBIP semantic model)
        │  parameters only (no secrets)
        ▼
Power BI data gateway                 ← holds the real credentials
        │  TLS (sslmode=require)
        ▼
DigitalOcean managed PostgreSQL
        └─ reads the  gold  schema only (never bronze)
```

The model carries **parameters**; the gateway carries the **secret**. These never
mix. A committed PBIP semantic model must contain no host, username, password, or
database name — only parameter definitions whose values are supplied at refresh
time by the gateway/credential store.

## Where each piece of configuration lives

| Configuration | Lives where | In git? |
|---------------|-------------|---------|
| Connection parameter **names** | PBIP semantic model + `docs` | ✅ yes |
| Connection parameter **values** (host, db, user) | Power BI gateway data-source config | ❌ no |
| **Password / secret** | Gateway credential store | ❌ never |
| TLS requirement (`sslmode=require`) | Documented convention | ✅ (the rule, not a secret) |
| Local SQL tooling connection (psql, migrations) | developer's local `.env` | ❌ (`.env` is git-ignored) |

`.env` / `.env.example` exist for **local SQL tooling** (applying migrations,
ad-hoc psql) — not for Power BI. Power BI's credentials come from the gateway, not
from `.env`. See [`../.env.example`](../.env.example).

## Parameter naming convention

When the PBIP semantic model defines connection parameters, name them to match the
documented environment variables so the two stay legible together:

| Power BI parameter | Purpose | Example value (placeholder) |
|--------------------|---------|------------------------------|
| `AnalyticsDbHost`  | Postgres host | `<your-db-host>.db.ondigitalocean.com` |
| `AnalyticsDbPort`  | Postgres port | `<port>` |
| `AnalyticsDbName`  | Database name | `<analytics-db-name>` |
| `AnalyticsDbSchema`| Schema to read | `gold` |

Parameters use `PascalCase` (Power BI convention); the matching env vars use
`ANALYTICS_DB_*` (shell convention). User and password are **not** Power BI
parameters — they are supplied as the gateway data-source credentials.

> All values above are placeholders. Do not commit real host names, ports,
> database names, or machine paths.

## Expected connection flow (later, when a report is built)

1. In the PBIP semantic model, define the parameters above (names only; values
   resolved at refresh time).
2. Point the data source at PostgreSQL, selecting the **`gold`** schema. Apply
   transformations in `warehouse/gold/`, not in Power Query.
3. Publish to the Power BI Service.
4. In the Service, bind the dataset's data source to the **existing gateway**, and
   set the credentials **there** (TLS / `sslmode=require`).
5. Schedule refresh through the gateway.

## Remaining manual setup (user, inside Power BI — outside this repo)

These steps are intentionally NOT automated here; they touch credentials and
machine/gateway config that must stay out of git:

- [ ] Confirm the **gateway** is online and can reach the DigitalOcean Postgres.
- [ ] Add the DigitalOcean Postgres as a **data source on the gateway**, with TLS
      enabled (`sslmode=require`), entering the real host/db/user/password there.
- [ ] When a dataset is published, **map it to that gateway data source**.
- [ ] Verify a test refresh succeeds from the Service (this is the real
      connectivity test — performed in Power BI, not from this repo).

## Power BI Desktop Bridge (optional, future local verification)

The **Power BI Desktop Bridge** (IPC Bridge) is a separate, optional capability —
unrelated to the gateway and to database connectivity. It is a local named-pipe API
hosted inside a running Power BI Desktop process, intended for *agentic* local
authoring/verification of reports.

- **Local only.** Power BI Desktop exposes the pipe `pbi-desktop-bridge-${processId}`
  (one per open Desktop window). Communication is strictly local — no remote access,
  no REST. Protocol is JSON-RPC 2.0.
- **Enable it** in Power BI Desktop → File > Options and Settings > Options >
  Preview Features → *Enable external tool access to Power BI Desktop through secure
  local APIs*. (Preview feature; API surface may change.)
- **Discover capabilities** by calling `bridge.manifest` first — it lists the methods
  the installed Desktop version supports (calling an unsupported method returns
  `-32601 MethodNotFound`).
- **What it could do later:** read the open report definition, apply/validate report
  changes, reload Desktop, and capture screenshots — a fast local edit→verify loop.

What it does **not** do: it does **not** connect to the DigitalOcean Postgres and
does **not** prove database connectivity. That remains a gateway concern (above).

Constraints for this repo:

- The Bridge is an **optional, future, local** path. The skeleton does not require
  it, and nothing in CI or any remote environment should assume it exists (it only
  exists when Power BI Desktop is running locally with the preview feature enabled).
- The repo's source of truth stays the **PBIP/PBIR/TMDL files in git** — not anything
  the Bridge produces at runtime.

## Rules (recap)

- No secrets in any committed file — ever.
- Power BI model holds parameters; the gateway holds credentials.
- Read `gold`, never `bronze`.
- TLS is required for DigitalOcean managed Postgres.
- The Desktop Bridge is local/optional and proves nothing about DB connectivity.
