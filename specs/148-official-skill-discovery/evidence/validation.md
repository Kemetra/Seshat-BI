# Validation evidence: Spec 148

**Date**: 2026-08-07

| Command | Exit | Result | Classification |
|---|---:|---|---|
| focused discovery implementation tests | 0 | 35 passed | Phase 6 implementation gate |
| final focused integration/routing regression | 0 | 131 passed in 23.72s | Final focused gate |
| capability/plugin/bundle contracts | 1 | 46 passed; closed ship-classification set omitted the existing `upstream-integration` class | Pre-existing contract gap exposed by architecture gate |
| corrected capability ship-classification contract | 0 | 15 passed in 18.55s | Final ownership gate |
| final Spec retirement, discovery, and ownership contracts | 0 | 21 passed in 20.98s | Lifecycle closeout gate |
| `python -m ruff format --check src tests scripts` | 0 | 896 files already formatted | Formatting gate |
| `python -m ruff check src tests scripts` | 0 | All checks passed | Static gate |
| `python scripts/export_agent_bundles.py --check` | 0 | Claude and Codex bundles match reviewed inputs | Drift gate |
| `python -m seshat.cli check` | 0 | No blocking finding; existing RS1 timestamp warning only | Pre-existing warning |
| source-tree integration plan without `--harness` | 1 | Discovery rows report `not-checked`; missing workspace lock/payload requires action | Expected fail-closed local state |
| source-tree integration plan with `--harness codex` | 1 | All three official packages report checked `not-installed`; no activation inferred | Expected fail-closed local state |
| `git diff --check` | 0 | PASS; Windows LF-to-CRLF advisory only | Diff integrity |

The focused regression covered catalog resolution/install/lock/CLI behavior, the
compatibility facade, Power BI/dbt/Dagster ownership routes, official skill
discovery, and Spec Kit lifecycle agreement. Tests used isolated fake harness
roots and did not mutate the operator's global Claude Code or Codex configuration.

The reviewed scope adds no dependency, MCP/runtime behavior, readiness mutation,
upstream instruction copy, deletion, merge, release, or publication.
