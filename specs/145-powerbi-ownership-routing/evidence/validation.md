# Validation evidence: Spec 145

**Date**: 2026-08-07

| Command | Exit | Result | Classification |
|---|---:|---|---|
| `python -m pytest tests/contract/test_dbt_documentation.py -q` | 0 | 6 passed | Spec lifecycle baseline |
| initial three-module red-contract run | 1 | collection refused because `read_stage_readiness` did not exist | Expected red contract |
| `pytest` over recommender, detector, and CLI | 0 | 50 passed | Phase 3 focused |
| first capability/ownership run | 1 | 2 failures rejected unbacked `publicly-released` provenance | New regression, corrected to `unrecorded` |
| corrected ownership and capability run | 0 | 61 passed | Phase 3 focused |
| routing + generated setup contracts | 0 | 22 passed | Phase 3 focused |
| complete Phase 3 focused regression command | 0 | 175 passed in 50.77s | Final focused gate |
| `python -m ruff check` on changed Python/tests | 0 | All checks passed | Static gate |
| initial `python scripts/export_agent_bundles.py --check` | 1 | Expected canonical-source drift named only changed projections | Expected generation delta |
| `python scripts/export_agent_bundles.py` | 0 | Claude and Codex bundles regenerated from reviewed inputs | Deterministic generation |
| final `python scripts/export_agent_bundles.py --check` | 0 | PASS | Drift gate |
| `python -m seshat.cli check` | 0 | No blocking finding; existing RS1 timestamp warning only | Pre-existing warning |
| `git diff --check` | 0 | PASS; Windows LF-to-CRLF advisory only | Diff integrity |

No live Microsoft, tenant, MCP, Desktop, database, installation, activation, or
publish operation was run.
