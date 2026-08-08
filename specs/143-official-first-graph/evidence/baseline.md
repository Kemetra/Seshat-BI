# Phase 1 baseline evidence

**Captured**: 2026-08-07, before implementation

**Revision**: `3b7ce2a`

| Command | Exit | Result | Classification |
| --- | ---: | --- | --- |
| `python scripts/export_agent_bundles.py --check` | 0 | `PASS: generated Claude and Codex bundles match reviewed inputs` | BASELINE PASS |
| `python -m pytest -p no:cacheprovider tests/unit/test_capability_inventory.py tests/contract/test_public_command_surface.py tests/contract/test_generated_agent_bundles.py -q` | 0 | 67 passed | BASELINE PASS |
| `git diff --name-only -- integrations/claude-code integrations/codex .claude-plugin .agents/plugins` | 0 | No output | BASELINE PASS |
| `git status --short` before Spec Kit preparation | 0 | Clean isolated worktree | BASELINE PASS |

The primary worktree's previously acknowledged untracked `uv.lock` is outside
this isolated worktree and was not read, modified, or staged.
