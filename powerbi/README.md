# powerbi/ — Power BI projects (PBIP)

The only tool-specific folder. Power BI reports + semantic models are saved here
in **PBIP** (Power BI Project) format — plain-text TMDL/PBIR that git can diff.

## One-time setup

1. Power BI Desktop → **File > Options and settings > Options > Preview features**
   → enable **Power BI Project (.pbip) save option**. *(PBIP is in preview as of
   2025-12; without this, "Save as PBIP" won't appear.)*
2. Save reports here via **File > Save as > Power BI Project (.pbip)**.

## What gets committed

- `*.SemanticModel/definition/**` (TMDL — tables, relationships, **DAX measures**)
- `*.Report/definition/**`, `definition.pbir`, `.platform`, the `*.pbip` file

## What is ignored (see root .gitignore)

- `**/.pbi/localSettings.json`, `**/.pbi/cache.abf`

## Rules

- Connect to the analytics DB via **parameters** (host/db/user/password/sslmode
  from `.env`), never a baked-in connection string.
- Read from the `marts` schema, not `raw`.
- Measures `PascalCase` with display folders; one semantic model per subject area.

## Windows gotchas

- **260-char path limit:** keep project/table names short (repo already at a short root).
- Edit PBIP files externally only as **UTF-8 without BOM**.
- Line endings handled by root `.gitattributes` + `core.autocrlf=true`.
