# Phase 2 validation evidence

**Captured**: 2026-08-07

| Command | Exit | Result | Classification |
| --- | ---: | --- | --- |
| `python -m pytest tests/unit/test_integrations_setup.py tests/unit/test_curated_stack_cli.py tests/unit/test_curated_stack_resolution.py tests/unit/test_curated_stack_lock.py tests/unit/test_curated_stack_install.py -q` | 0 | 78 passed | PASS |
| `python -m pytest tests/unit/test_capability_inventory.py tests/unit/test_capability_plugin_shipped.py tests/contract/test_capability_ship_classification.py tests/contract/test_public_command_surface.py tests/contract/test_generated_agent_bundles.py tests/contract/test_claude_plugin_bundle.py tests/contract/test_codex_plugin_bundle.py -q` | 0 | 105 passed | PASS |
| `python -m pytest tests/unit/test_integrations_setup.py -q` | 0 | 15 passed after final formatting | PASS |
| `python -m pytest tests/contract/test_dbt_documentation.py -q` | 0 | 6 Spec Kit lifecycle/documentation contracts passed after clearing the active pointer | PASS |
| `ruff format --check` on the six changed Python/test files | 0 | 6 files already formatted | PASS |
| `ruff check` on the six changed Python/test files | 0 | All checks passed | PASS |
| `python scripts/export_agent_bundles.py --check` | 0 | Generated Claude and Codex bundles match reviewed inputs | PASS |
| `git diff --exit-code -- distribution integrations/claude-code/seshat-bi integrations/codex/seshat-bi .claude-plugin .agents/plugins` | 0 | No generated-root changes | PASS |
| `python -m seshat.cli check` | 0 | Static gate passed; unchanged RS1 freshness warning only | PRE-EXISTING WARNING |
| `git diff --check` | 0 | No whitespace error; Windows line-ending advisory for `.specify/feature.json` only | PASS WITH ADVISORY |

## Environmental retry

The first pytest and bundle-check attempts could not create directories below
the Windows user temp root (`WinError 5`). They were rerun with an explicit
pytest base temp and the approved process boundary. This was an environmental
sandbox restriction; the reruns above are the substantive results.

The RS1 warning predates Spec 144: `last_checked_at 2026-06-25` is older than
the latest approval `2026-07-23` in
`mappings/retail_store_sales/readiness-status.yaml`. Phase 2 does not modify
readiness truth or self-ratify that metadata.
