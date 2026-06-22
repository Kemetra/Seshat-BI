# pipelines/ — data ingestion

How raw data lands in the DigitalOcean analytics Postgres (`raw` schema).

## Now: manual loads

Data is loaded manually into the `raw` schema (e.g. `psql \copy`, a CSV import,
or a one-off script run by hand). No automated job runs yet, so this folder holds
no executable pipeline code — only this contract.

## The contract (so manual + future automation stay compatible)

Whatever loads data — a person today or the automated service later — MUST:

- Write into the `raw` schema only (never `marts`).
- Preserve source column names/types as landed; transformations happen in
  `warehouse/marts/`, not at ingestion.
- Be re-runnable: a reload of the same source replaces, not duplicates, its rows.

## Future: automated "flowing" service

A scheduled feed will replace manual loads, targeting the **same `raw` contract**
above. When added, its code lives here; nothing downstream (`marts`, Power BI)
should need to change.
