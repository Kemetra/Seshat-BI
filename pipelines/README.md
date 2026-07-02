# pipelines/ — data ingestion

How source data lands in the DigitalOcean analytics Postgres **`bronze`** schema
(the medallion landing layer). See `warehouse/README.md` for the bronze/silver/gold model.

## Now: manual loads

Data is loaded by running a script by hand. `load_bronze.py` lands the C086 sales
Excel files into `bronze.sales_c086_raw`. No automated/scheduled job runs yet.

### `load_bronze.py`

Lands Excel files into bronze as **faithful raw text + lineage** — every source
column as `TEXT`, plus `_source_file` and `_loaded_at`. No cleaning or typing
(that's the silver layer). Loads via PostgreSQL `COPY`, and reconciles each file
(Excel data rows == bronze rows) before continuing.

Secrets are never hardcoded: the DB connection is read from `doctl` at runtime.
Configure via flags or env vars:

| Flag | Env | Meaning |
|------|-----|---------|
| `--cluster-id` | `DO_DB_CLUSTER_ID` | DigitalOcean DB cluster id (for `doctl databases connection`) |
| `--database` | `ANALYTICS_DB_NAME` | target logical database (no default; supply via env/flag) |
| `--src-dir` | `SALES_SRC_DIR` | folder of `.xlsx` files to load |

\`\`\`bash
# create bronze/silver/gold schemas + the bronze table, then load all files
python pipelines/load_bronze.py \
  --cluster-id "$DO_DB_CLUSTER_ID" --database "$ANALYTICS_DB_NAME" \
  --src-dir "/path/to/sales/c086" --all

# load a single file (idempotent — replaces that file's prior rows)
python pipelines/load_bronze.py --cluster-id "$DO_DB_CLUSTER_ID" \
  --src-dir "/path/to/sales/c086" --file C086_Sales_2024_Full_Year.xlsx
\`\`\`

> The source `.xlsx` files are **not** in this repo (they're data, not code). Point
> `--src-dir` at wherever they live. As of the first load, all 4 C086 files
> (2023 H1/H2, 2024, 2025 — ~249k rows) are landed in `bronze.sales_c086_raw`.

## The contract (so manual + future automation stay compatible)

Whatever loads data — a person today or the automated service later — MUST:

- Write into the `bronze` schema only (never `silver`/`gold`).
- Preserve source values as landed (text + lineage); transformations happen in
  `silver`/`gold`, not at ingestion.
- Be re-runnable: a reload of the same source replaces, not duplicates, its rows
  (`load_bronze.py` deletes a file's prior rows by `_source_file` before COPY).

## Future: automated "flowing" service

A scheduled feed will replace manual loads, targeting the **same `bronze` contract**
above. When added, its code lives here; nothing downstream (`silver`, `gold`,
Power BI) should need to change.
