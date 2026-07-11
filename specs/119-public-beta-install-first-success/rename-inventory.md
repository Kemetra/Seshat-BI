# Rename inventory: `retail` to `seshat`

Captured for Spec 119 task T002 before the implementation follow-through. The inventory command is intentionally reproducible:

```powershell
rg -n "import retail|from retail|python -m retail|src/retail|packages = \[\"src/retail\"\]" src tests docs integrations pyproject.toml
```

## Disposition

- **Primary code and tests:** imports, module invocations, generated path strings, static-rule prefixes, and test fixtures now use `seshat` / `src/seshat`.
- **Packaging:** the distribution is `seshat-bi`; both console scripts target `seshat.cli:main`; Hatch includes `src/seshat` and the deliberately thin `src/retail` shim.
- **Intentional compatibility references:** `python -m retail.cli` remains only in the shim contract and plugin fallback documentation for one deprecation cycle. It resolves through `src/retail/cli.py` to `seshat.cli:main`.
- **Historical records:** old release/planning records may mention prior command names where they describe a past state; they are not live import paths.

Post-migration verification is `rg -n "^(from|import) retail|src/retail" src tests`, which must return only the intentionally retained shim-package files, if any.