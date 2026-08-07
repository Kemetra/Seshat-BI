# Phase 1 validation evidence

**Captured**: 2026-08-07

**Revision under test**: local unstaged implementation on `143-official-first-graph`
from base `3b7ce2a`

| Command | Exit | Result | Classification |
| --- | ---: | --- | --- |
| `python -m pytest tests/unit/test_capability_inventory.py -q` (first complete-manifest run) | 1 | 55 passed, 2 failed. The new oracle found nine fallback-owned public skills without canonical sources, one ownerless `retail-validate` public surface, and an isolated-fixture lookup defect in the new positive feeder. | NEW TEST FINDING; implementation incomplete |
| `python -m pytest tests/unit/test_capability_inventory.py -q` (after the bounded metadata repair) | 0 | 57 passed. | PASS |
| `python -m pytest tests/contract/test_public_command_surface.py tests/contract/test_capability_ship_classification.py tests/contract/test_generated_agent_bundles.py tests/contract/test_claude_plugin_bundle.py tests/contract/test_codex_plugin_bundle.py -q` | 0 | 45 passed. | PASS |
| `python scripts/export_agent_bundles.py --check` without a local temp override | 1 | `WinError 5` while creating an AppData temp directory; the script did not reach the bundle comparison. | ENVIRONMENTAL |
| `python scripts/export_agent_bundles.py --check` with `TEMP` and `TMP` set to the isolated worktree temp directory | 0 | `PASS: generated Claude and Codex bundles match reviewed inputs`. | PASS |
| `git diff --exit-code -- integrations/claude-code/seshat-bi integrations/codex/seshat-bi` | 0 | No output; neither generated root changed. | PASS |
| Independent oracle census (`load_shipped_public_skills` plus `public_capability_integrity_violations`) | 0 | `shipped_public_skills=21`; `graph_violations=0`. | PASS |
| `python -m seshat.cli check` with the local temp override | 0 | One RS1 warning: `last_checked_at 2026-06-25` predates the latest approval `2026-07-23`. The referenced readiness file is outside this phase and unchanged. | PRE-EXISTING WARNING |
| `git diff --check` | 0 | No whitespace error. Git emitted only its Windows LF-to-CRLF advisory for `.specify/feature.json`. | PASS |
| `python -m pytest tests/contract/test_dbt_documentation.py tests/unit/test_spec_status_vocabulary.py -q` after clearing the active plan | 0 | 13 passed; the no-active-plan fences agree and Spec 143 remains correctly `ratified` rather than claiming an unlanded implementation. | PASS |

The first complete-manifest failure was actionable architecture evidence, not an
unrelated regression. The follow-up changes were limited to canonical-source
metadata for the already-resolved public owners, one exact `retail-validate`
public edge, and fixture-safe behavior in the newly added oracle feeder.
