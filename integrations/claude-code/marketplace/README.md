# Seshat BI -- Claude Code marketplace configuration (DRAFT)

> **Status: draft only. Not publicly released.** This directory documents the
> *intended* marketplace entry for the Seshat BI Claude Code plugin. The
> marketplace schema and the install flow have NOT yet been verified against
> current Claude Code documentation; both must be verified before any
> publication. Do not treat anything here as installable or available.

## What this is

`.claude-plugin/marketplace.json` is a draft marketplace manifest that points
at the **local** Seshat BI Claude Code plugin draft in
[`../seshat-bi/`](../seshat-bi/README.md). It exists so the eventual
publication step starts from a reviewed skeleton instead of from scratch.

## What must happen before publication

1. Verify the plugin manifest schema (`.claude-plugin/plugin.json`) against
   current Claude Code plugin documentation.
2. Verify the marketplace manifest schema (`.claude-plugin/marketplace.json`)
   and the `source` reference form.
3. Verify the end-to-end install flow locally (add the marketplace, install
   the plugin, confirm the skill and the four `/seshat-*` commands load).
4. Decide whether the plugin + marketplace move to a standalone repository
   (likely, so consumers do not clone the whole BI kit).

Until every step above is done, this stays a draft inside the main repo, with
no badges, links, or claims implying public availability.
