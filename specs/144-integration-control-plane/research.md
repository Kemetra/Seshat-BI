# Research: Integration control-plane convergence

## Current call graph

```text
seshat integrations setup
  -> cli/commands/integrations.py
  -> integrations_setup re-exports
  -> integrations.catalog + installer.plan/apply + render

direct legacy Python call
  -> integrations_setup.setup_integrations
  -> independent clone/MCP/runtime implementation
```

The CLI is already on the desired path. The remaining delta is the second path.

## Consumer evidence

Repository search finds `setup_integrations`, `FABRIC_SKILLS`, `DBT_SKILLS`, and
legacy implementation internals only in `tests/unit/test_integrations_setup.py`.
The CLI imports `confirm` and catalog-backed aliases through the facade. No
active documentation tells users to call the Python API, but `__all__` records
an intentional import surface, so symbols should not be removed casually.

## Behavior that must migrate

The legacy implementation verifies specific official skill files after clone.
The canonical installer currently trusts a `.seshat-installed` marker for
GitHub components. Required paths therefore belong on catalog `Component`
records and must be enforced by the canonical installer before the legacy code
can be retired.

## Rejected alternatives

- **Delete the facade**: rejected; import compatibility lacks replacement proof.
- **Keep both and document one preferred**: rejected; this preserves two truths.
- **Have the facade create live resolvers for apply**: rejected; that silently
  widens a library call into network access.
- **Copy required paths into installer conditionals**: rejected; it would create
  another component-specific registry.
- **Solve activation now**: rejected; cloned versus discoverable is Phase 6.

## Baseline

On 2026-08-07, the five focused integration modules passed 88 tests. This is a
green architectural consolidation, not defect triage.
