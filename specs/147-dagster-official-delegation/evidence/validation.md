# Validation evidence: Spec 147

**Date**: 2026-08-07

| Command | Exit | Result | Classification |
|---|---:|---|---|
| focused Dagster/integration/capability/bundle baseline | 0 | 265 passed, 1 skipped in 48.44s | Phase 5 baseline |
| `python scripts/export_agent_bundles.py --check` before changes | 0 | PASS | Baseline drift gate |
| lifecycle contract after ratification | 0 | 6 passed | Spec lifecycle gate |
| first catalog/ownership/generated run | 1 | 123 passed; one router phrase mismatch and expected generated drift | New test mismatch corrected; expected generation delta |
| `python scripts/export_agent_bundles.py` | 0 | Claude and Codex bundles regenerated from reviewed inputs | Deterministic generation |
| complete focused Phase 5 regression command | 0 | 278 passed, 1 skipped in 51.36s | Final focused gate |
| `python -m ruff check` on changed Python/tests | 0 | All checks passed | Static gate |
| `python scripts/export_agent_bundles.py --check` | 0 | PASS | Drift gate |
| `python -m seshat.cli check` | 0 | No blocking finding; existing RS1 timestamp warning only | Pre-existing warning |
| post-review ownership contract | 0 | 7 passed in 4.23s | Scope-review gate |
| final lifecycle and ownership closeout | 0 | 13 passed in 5.08s | Spec retirement gate |
| `git diff --check` | 0 | PASS; Windows LF-to-CRLF advisory only | Diff integrity |
| official upstream payload-path verification | 0 | Microsoft, dbt Labs, and Dagster required files resolved at their current official repository commits; three stale paths corrected | External ownership gate |

The focused regression covered catalog composition/resolution/install/lock,
the compatibility facade, integration setup, Dagster CLI/doctor/runner/gates/
evidence/source modes, capability ownership, lifecycle, and generated bundles.

No live Dagster job, database operation, official-skill activation, dependency
change, graph change, readiness mutation, deletion, or external publication was
performed.
