# Seshat BI -- Claude Code marketplace (verified draft, not released)

> **Status: locally verified draft. Not publicly released.** The manifest
> schema and the end-to-end install flow were verified with the Claude Code
> CLI (v2.1.206, 2026-07): `claude plugin validate` passes for both
> manifests, and a local `marketplace add` -> `plugin install` -> component
> load succeeds. Publication still has NOT happened -- do not treat this as
> publicly available.

## Layout

This directory is the **marketplace root**: the Claude Code CLI requires
plugin `source` paths to resolve relative to the directory containing
`.claude-plugin/` and rejects `..` segments, so the marketplace manifest
lives here and points at the plugin below it.

| Path | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace manifest (validated). |
| `seshat-bi/` | The Seshat BI plugin (skill + four `/seshat-*` commands). |

## Verified install flow (local)

```bash
# from the repo root
claude plugin validate integrations/claude-code            # marketplace manifest
claude plugin validate integrations/claude-code/seshat-bi  # plugin manifest
claude plugin marketplace add ./integrations/claude-code
claude plugin install seshat-bi@seshat-bi-marketplace
claude plugin details seshat-bi   # skill + seshat-init/next/check/review load
```

## What must still happen before publication

1. Decide whether the plugin + marketplace move to a standalone repository
   (likely, so consumers do not clone the whole BI kit).
2. Re-verify against the Claude Code version current at publication time.

Until then, this stays a verified draft inside the main repo, with no badges,
links, or claims implying public availability.
