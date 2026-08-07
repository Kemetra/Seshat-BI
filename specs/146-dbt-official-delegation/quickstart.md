# Quickstart: validate Spec 146

1. Run focused dbt public-surface, project, package, and CLI tests.
2. Run capability and generated-bundle contracts.
3. Run `python scripts/export_agent_bundles.py --check`.
4. Confirm dbt activation status remains blocked and no runtime/pin changed.
5. Run lifecycle, lint, `seshat check`, and diff integrity gates.
