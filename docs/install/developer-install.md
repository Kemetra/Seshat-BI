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