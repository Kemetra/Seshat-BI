# Developer installation

This path is for contributors working from a Seshat BI source checkout. It is not the public user path and it does not imply that `seshat-bi` is published.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
seshat check
pytest -m unit
```

On macOS/Linux, activate with `source .venv/bin/activate`. The editable install exposes both `seshat` and the legacy `retail` command. The primary import package is `seshat`; `retail` is a deprecated compatibility shim.

Live checks are intentionally separate: install `.[db]`, `.[mssql]`, `.[mysql]`, `.[snowflake]`, or `.[files]` only when working on that boundary. `.[livetest]` is reserved for the optional container-backed suite. Keep credentials in `.env`.

For the governed statistical core plus change-point support, use the exact
pinned contributor environment:

```powershell
python -m pip install -e ".[dev,stats,stats-change]"
seshat analyze --help
pytest tests/unit/statistical
```

Add `db` only when exercising the PostgreSQL Gold adapter. Local CSV analysis
requires no database, and all real connection settings remain in `.env`.

For the governed dbt shadow adapter, install its exact tested pair separately:

```powershell
python -m pip install -e ".[dev,dbt]"
seshat dbt doctor --format json
seshat dbt validate --table retail_store_sales --format json
seshat dbt plan --table retail_store_sales --format json
```

The `dbt` extra pins `dbt-core==1.12.0` and `dbt-postgres==1.10.2`. Put real
`SESHAT_DBT_*` values only in the gitignored `.env`; committed
`profiles.example.yml` uses `env_var()` references. Execute only after reviewing
the immutable plan digest:

```powershell
seshat dbt build --table retail_store_sales --accept-plan <digest> --format json
seshat dbt inspect-run --table retail_store_sales --artifacts <run-directory> --format json
```

`inspect-run` revalidates an existing run offline; it is not a second build. Without a
configured database, report `[PENDING LIVE PROFILE]` and do not claim compile, build,
test, or parity success.

Release contributors install the validators explicitly and keep publication
credentials out of the build environment:

```powershell
python -m pip install build twine
python -m build --wheel --sdist --outdir dist
python -m twine check --strict dist\*
python scripts\inspect_release_artifacts.py --dist dist
```

These checks produce candidate evidence only. They do not authorize a version,
tag, upload, release, marketplace publication, or OpenAI public plugin submission.
