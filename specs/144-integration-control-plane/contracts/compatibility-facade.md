# Contract: Catalog-backed integration compatibility facade

## Invariants

1. `integrations_setup.py` contains no subprocess invocation, clone, package
   installation, MCP config write, component membership tuple, or installed-state
   detector.
2. `setup_integrations(..., apply=False)` calls canonical `plan_profile`.
3. `setup_integrations(..., apply=True, resolvers=None)` writes nothing and
   returns a categorical failure.
4. `setup_integrations(..., apply=True, resolvers=R)` calls canonical
   `apply_profile` with `R`.
5. Every projected row uses the canonical component ID, status, and detail.
6. Compatibility bundle constants are derived from catalog components and their
   required paths.
7. Official GitHub payload validation reads only `Component.required_paths`.
8. The CLI retains its existing approval and `--refresh` gates.

## Mutation cases

- Add a catalog component: facade planning reflects it without a facade edit.
- Change a required path: presence and staged-clone validation both change.
- Remove a required file from staging: activation fails.
- Remove a required file from a marked target: plan no longer says present.
- Request compatibility apply without resolvers: no runner or filesystem write.
