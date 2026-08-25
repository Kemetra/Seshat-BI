# Validation evidence: Spec 156

**Date**: 2026-08-25

| Command | Exit | Result | Classification |
|---|---:|---|---|
| binding validator RED | 2 | expected collection error: module absent | TDD RED gate |
| binding validator + import guard | 0 | 20 passed | Validator GREEN gate |
| inventory/CLI RED | 1 | 4 expected failures; 58 passed, 1 skipped | TDD RED gate |
| binding, inventory, generator, and drift regression | 0 | 124 passed, 1 skipped | Caller GREEN gate |
| template RED | 1 | 2 expected failures, 1 passed | TDD RED gate |
| template contract | 0 | 3 passed | Template GREEN gate |
| focused final regression | 0 | 133 passed, 1 skipped | Acceptance gate |
| `python -m seshat.cli check` | 0 | no blocking finding; existing RS1 timestamp warning | Static governance gate |
| `python scripts/export_agent_bundles.py --check` | 0 | generated Claude and Codex bundles match | Drift gate |
| `git diff --check` | 0 | PASS | Diff integrity |
| `pytest -m unit` | interrupted by owner | no failures through 57%; full run delegated to PR CI | CI-delegated repository gate |

The skipped focused test requires Windows symlink privilege. The static warning
is the pre-existing `retail_store_sales.last_checked_at` date preceding its
latest approval; it is unrelated to spec 156 and does not block `seshat check`.

No database, DAX execution, Power BI write, target value, grain ruling, RAG
threshold, missing-target ruling, or approval was produced by this feature.
