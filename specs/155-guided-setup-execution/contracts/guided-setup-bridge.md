# Contract: derived-scope provisioning bridge

## Invariants

1. `derivation.py` is unmodified: it still contains no `apply_profile(`,
   `live_resolvers(`, `write_lock(`, `install(`, `pip `, `npm `, `approved`,
   `authorize`, `--yes`, or `args.yes` call site.
2. The bridge contains no component id, coordinate, version, channel, or provider
   name of its own; every one is read from the catalog through the existing
   projection.
3. The derived scope is a function of committed evidence, the projection,
   discovery state, and committed declines only. No argv value, environment
   variable, or agent instruction appears in its inputs.
4. A `not-required`, declined, satisfied, `optional`, or `undetermined` capability
   contributes zero components.
5. A blocked derived plan refuses before authorization is consulted.
6. Authorization is `approval.evaluate(root, derived_scope)` and nothing else; the
   bridge contains no approval decision of its own.
7. Execution calls the existing `installer.apply`; the bridge performs no
   subprocess, clone, package install, or MCP write.
8. `DEFAULT_PROFILE` keeps its value, `--profile` keeps its choices, and a
   profile-based run's selection, output shape, and exit code are byte-identical
   to today's.
9. Capability readiness is read from discovery/verification results, never from a
   component row's install status.
10. A derived apply preserves previously recorded state for components outside the
    derived scope, and never labels a derived scope as a curated profile.

## Mutation cases

- Add a component to a capability's projection: the derived scope widens, and a
  standing approval for the narrower scope stops authorizing it.
- Add a catalog component to no capability: the derived scope is unchanged.
- Record a decline for a `required` capability: the plan blocks; `--apply` refuses;
  the strength stays `required`.
- Remove the covering approval row: the next run refuses with a categorical reason
  and a next action, and installs nothing.
- Widen the request on the command line: the proposed scope does not change.
- Make verification fail for one installed component: that capability reports
  not-ready and the run is not successful, while the other capability's status is
  unaffected.
- Re-run an unchanged approved scope: zero reinstalls, zero new approvals.
- Run a previously locked broader profile, then a narrower derived scope: the lock
  still records the out-of-scope components.
