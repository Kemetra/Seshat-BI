# Validation evidence: Spec 146

**Date**: 2026-08-07

| Command | Exit | Result | Classification |
|---|---:|---|---|
| `python -m pytest tests/contract/test_dbt_documentation.py -q` in the sandbox | 1 | Windows temp directory was inaccessible | Environmental; rerun elevated |
| elevated lifecycle rerun | 0 | 6 passed | Spec lifecycle gate |
| first ownership/public/capability run before generation | 1 | 73 passed; generated dbt skill differed from its changed canonical template | Expected generation delta |
| `python scripts/export_agent_bundles.py` | 0 | Claude and Codex bundles regenerated from reviewed inputs | Deterministic generation |
| complete focused Phase 4 regression command | 0 | 138 passed in 47.64s | Final focused gate |
| `python -m ruff check tests/contract/test_dbt_ownership_routing.py` | 0 | All checks passed | Static gate |
| initial bundle check in restricted sandbox | 1 | Temporary comparison directory was inaccessible | Environmental; rerun elevated |
| elevated `python scripts/export_agent_bundles.py --check` | 0 | PASS | Drift gate |
| `python -m seshat.cli check` | 0 | No blocking finding; existing RS1 timestamp warning only | Pre-existing warning |
| `git diff --check` | 0 | PASS; Windows LF-to-CRLF advisory only | Diff integrity |
| final lifecycle and ownership closeout | 0 | 12 passed in 5.01s | Spec retirement gate |

The focused regression command covered the new ownership contract, public dbt
surface, dbt project/package/docs contracts, CLI unit tests, capability
inventory, and generated-agent-bundle contracts.

No live database, dbt execution, official-skill activation, MCP activation,
installation, dependency change, readiness mutation, deletion, or external
publication operation was performed.
