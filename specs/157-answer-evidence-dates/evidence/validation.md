# Validation evidence: Spec 157

**Date**: 2026-08-25

| Command | Exit | Result | Classification |
|---|---:|---|---|
| source-profile evidence RED | 1 | 3 expected failures | TDD RED gate |
| source-profile and packaging regression | 0 | 58 passed, 4 skipped | Source-profile GREEN gate |
| answerability disclosure RED | 1 | 11 expected failures | TDD RED gate |
| answerability disclosure | 0 | 11 passed | Disclosure GREEN gate |
| Publish Ready route RED | 1 | 1 expected failure | TDD RED gate |
| evidence-date focused regression | 0 | 15 passed | Route GREEN gate |
| focused final regression | 0 | 76 passed, 4 skipped | Acceptance gate |
| `python -m seshat.cli check` | 0 | no blocking finding; existing RS1 timestamp warning | Static governance gate |
| `python scripts/export_agent_bundles.py --check` | 0 | generated Claude and Codex bundles match | Drift gate |
| `git diff --check` | 0 | PASS | Diff integrity |
| full repository matrix | delegated by owner | run by PR CI | CI-delegated repository gate |

The skips are existing capability/platform cases. The static warning is the
pre-existing `retail_store_sales.last_checked_at` date preceding its latest
approval; spec 157 discloses that fact but does not recompute or soften it.

No database query, coverage inference, age threshold, freshness judgment,
traffic light, badge, verdict, readiness change, approval, or score was produced.
