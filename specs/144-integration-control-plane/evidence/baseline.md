# Phase 2 baseline evidence

**Captured**: 2026-08-07

**Revision**: `4fb3798`

| Command | Exit | Result | Classification |
| --- | ---: | --- | --- |
| Focused integration suite (`test_integrations_setup.py` plus four `test_curated_stack_*` modules) | 0 | 88 passed | BASELINE PASS |
| `git status --short` before Spec 144 creation | 0 | Clean worktree | BASELINE PASS |
| `python scripts/export_agent_bundles.py --check` | 0 | Generated Claude and Codex bundles match reviewed inputs | BASELINE PASS |
| Generated Claude/Codex root diff | 0 | No output | BASELINE PASS |
| `python -m seshat.cli check` after correcting the local Phase 1 commit subject | 0 | One unchanged RS1 freshness warning | PRE-EXISTING WARNING |

The green baseline proves both paths are tested. It does not prove that they
share membership or execution truth.
