# Quickstart: Spec 144 implementation verification

Use the isolated writable temp directory on Windows:

```powershell
$env:TEMP='C:\Users\user\Documents\GitHub\Seshat-BI\.worktrees\.tmp-official-first'
$env:TMP=$env:TEMP
python -m pytest tests/unit/test_integrations_setup.py tests/unit/test_curated_stack_cli.py tests/unit/test_curated_stack_resolution.py tests/unit/test_curated_stack_lock.py tests/unit/test_curated_stack_install.py -q
python -m pytest tests/unit/test_capability_inventory.py tests/contract/test_public_command_surface.py tests/contract/test_generated_agent_bundles.py -q
python scripts/export_agent_bundles.py --check
python -m seshat.cli check
git diff --check
```

Do not use real live resolvers or `--apply` during repository validation. Apply
tests use injected resolvers and runners inside temporary workspaces.
