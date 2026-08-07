# Quickstart: validate Spec 145

1. Run focused Power BI recommender/preflight tests.
2. Run capability, public-surface, and generated-bundle contracts.
3. Run `python scripts/export_agent_bundles.py --check`.
4. Run `python -m seshat.cli check` and `git diff --check`.
5. Confirm F016 remains parked and no activation/live execution was added.
