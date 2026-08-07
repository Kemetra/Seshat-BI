# Quickstart: Verify public capability graph integrity

Run from the repository root with a writable temporary directory.

## 1. Focused ownership gate

```powershell
python -m pytest -p no:cacheprovider tests/unit/test_capability_inventory.py -q
```

Expected: mutation tests and the aggregate real-manifest oracle pass.

## 2. Public and generated distribution contracts

```powershell
python -m pytest -p no:cacheprovider tests/contract/test_public_command_surface.py tests/contract/test_capability_ship_classification.py tests/contract/test_generated_agent_bundles.py tests/contract/test_claude_plugin_bundle.py tests/contract/test_codex_plugin_bundle.py -q
python scripts/export_agent_bundles.py --check
```

Expected: all focused contracts pass and the exporter reports that generated
Claude and Codex bundles match reviewed inputs.

## 3. Architecture/governance check

```powershell
python -m seshat.cli check
git diff --check
git status --short
```

Expected: no new Seshat finding, no whitespace error, and only the active Phase 1
spec plus its bounded implementation files are modified.

## 4. Manual trace sample

Trace each of these names from `distribution/public-command-surface.yaml` through
`references.public_skill` in `docs/capabilities/capabilities.yaml`:

- `seshat-bi`
- `powerbi-workflows`
- `pbi-mcp-doctor`

Each must resolve once, and its canonical source must be an authored tracked file
outside the generated integration bundles.
