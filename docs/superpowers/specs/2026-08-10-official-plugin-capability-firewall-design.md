# Official Plugin Capability Firewall Design

- **Status:** Approved design (2026-08-10)
- **Scope:** Official analytics skill/plugin discovery and governed Power BI
  routing. No Power BI execution adapter is unparked by this design.

## Goal

Make Seshat BI official-first without allowing an official bundle to introduce
undeclared skills, MCP servers, agents, hooks, moving versions, conflicting
routers, or readiness bypasses. Seshat owns governance and integration;
official upstreams own native product competence and mechanics; Seshat authors
a replacement skill only for a recorded upstream capability gap.

## Decision

Adopt a closed-world capability firewall for governed integrations.

An upstream component is usable only when the active harness payload exactly
matches a reviewed manifest. Presence of selected `SKILL.md` files is necessary
but insufficient. Discovery must also prove the active revision and enumerate
all activated skills, MCP servers, agents, and hooks. An undeclared capability,
moving coordinate, unsafe MCP argument, missing identity, or provenance mismatch
is a blocker.

The policy is intentionally asymmetric by harness:

- Codex keeps provenance-preserving projections of individually declared skill
  directories from the locked checkout.
- Claude native plugins are accepted only when their complete active plugin
  manifest matches the reviewed closed-world declaration. If the host cannot
  constrain a bundle and the bundle contains an incompatible capability, the
  plugin is unavailable in governed mode. Seshat does not emulate it.

## Ownership model

Seshat remains the one public orchestration front door. Ownership is split into
four non-overlapping layers:

1. **Seshat pre-gate:** exact target, committed readiness evidence, metric and
   design prerequisites, named-human approvals, environment policy, and the
   allowed operation.
2. **Official owner:** native product knowledge or mechanics from a declared,
   discoverable, compatible upstream skill or MCP surface.
3. **Seshat post-validation:** binding, blueprint, static, evidence, and
   readiness checks. A successful executor never grants a readiness pass.
4. **Gap-owned Seshat capability:** local authoring is permitted only when a
   capability-gap record names the missing upstream function, evidence checked,
   review date, scope, and retirement trigger.

For Power BI:

- Microsoft `powerbi-report-design` owns Power BI-specific visual design
  guidance and the implementation design contract.
- Microsoft `powerbi-report-authoring` owns native PBIR/PBIP mechanics.
- Seshat owns business meaning, metric contracts, readiness, target selection,
  named-human approval, and post-validation.
- Microsoft `powerbi-report-planning` is not a governed lifecycle owner because
  its broader approval/build/publish sequence conflicts with the Seshat
  readiness spine. It remains blocked unless a later reviewed integration
  constrains it to a non-conflicting role.
- Microsoft `powerbi-report-management` and all publish operations remain
  outside this change.
- The Power BI Modeling MCP remains read-only and F016 remains parked. A plugin
  that activates a default-write modeling MCP is incompatible with governed
  mode even when the desired report skill itself is safe.

## Closed-world manifest

Extend integration metadata with an explicit active-capability declaration for
each harness activation. The declaration includes:

- exact component id and resolved upstream ref;
- exact native plugin id and expected plugin version when applicable;
- allowed skill names and source paths;
- allowed MCP server names, transports, package coordinates, and arguments;
- allowed agent and hook identities (normally empty);
- policy for undeclared capabilities: always `block`;
- incompatible capabilities with a concrete reason;
- update policy and human review boundary.

The catalog remains the single authored authority. Lock data records the exact
resolved coordinate. Discovery observes the active harness and returns
categorical evidence; it never updates the declaration or grants compatibility.

### Claude discovery

Claude discovery must read the native plugin inventory and the installed
plugin manifest. It must verify:

- enabled plugin id and version match the declaration;
- the installed plugin payload corresponds to the locked upstream revision or
  an exact reviewed release identity;
- the complete sets of skills, MCP servers, agents, and hooks equal the allowed
  sets;
- MCP configurations contain no moving package coordinate such as `@latest`;
- Power BI local modeling MCP arguments include `--readonly` and exclude
  write/confirmation-bypass flags.

Any inability to enumerate one capability class is `failed`, not discoverable.

### Codex discovery

Keep the existing `samefile` proof for each projected skill. Add exact set
validation at the governed projection root so an undeclared same-name or extra
upstream projection cannot be mistaken for an approved activation. Codex does
not inherit a plugin MCP server merely because an official skill is projected.

## Governed routing decision

Replace loosely related advisory facts with one target-scoped decision input:

```text
GovernedRouteFacts
  target: exact table id
  operation: closed vocabulary
  readiness: stages for that target only
  approvals: approvals for that target and operation only
  integration: component + harness + resolved ref + discovery status
  environment: read-only/write policy and local configuration verdict
```

The output remains categorical:

```text
GovernedRouteDecision
  status: allowed | blocked
  executor: one exact official or Seshat surface
  blockers: concrete facts
  evidence: target readiness and integration discovery identities
  post_validators: exact validators required after execution
```

There is no repo-wide readiness or approval shortcut. A prerequisite appearing
in `blockers` always means `status: blocked` and a non-zero CLI exit. Advisory
prose cannot contradict the machine result.

### Power BI operation gates

- `model-edit`: exact target required; that target's
  `semantic_model_ready = pass` required; remains blocked because F016 is
  parked. Read-only inspection is a separate operation, not an edit loophole.
- `report-authoring`: exact target, target semantic readiness, target dashboard
  design approval, and discoverable compatible official authoring skill are
  required. The official skill is then the sole native authoring owner.
- `report-formatting`: exact target, target semantic readiness, and a committed
  approved design/blueprint reference are required before any PBIR writer is
  recommended. The existing command allow-lists still constrain the mutation.
- `published-query`: tenant setting, permission, authentication, and required
  license are explicit externally supplied attestations. Unknown prerequisites
  block; remote results never affect readiness.
- `ci-validation`: remains offline, deterministic, and non-mutating.

`dashboard_ready = pass` is not required to build a dashboard because the build
and validation are evidence for that stage. The pre-gate instead requires the
preceding semantic stage plus a named design/blueprint approval. This avoids a
circular gate while preserving the hard stop against designing before metric
contracts exist.

## Compatibility migration

The migration is fail-closed but staged so existing safe paths remain useful:

1. Add the closed-world schema and pure validator with tests.
2. Declare current dbt, Dagster, and Power BI upstream capabilities.
3. Mark the Claude Power BI authoring bundle incompatible while it exposes the
   default-write `@latest` modeling MCP and ungoverned planning/management
   skills.
4. Keep selected locked Codex projections available when their exact capability
   set passes.
5. Connect discovery evidence to the Power BI route decision.
6. Gate bounded PBIR mutators with target and approved-design evidence.
7. Remove stale ownership prose and add drift tests covering every public
   authority document.

No installer automatically changes or disables a user's external plugin. It
reports the incompatibility and refuses governed delegation. Installation and
activation remain explicit human actions.

## Error handling

All failures use categorical statuses and concrete blockers. Important blocker
classes include:

- active plugin revision differs from the locked/reviewed revision;
- undeclared skill, MCP server, agent, or hook;
- unsafe or moving MCP package coordinate;
- missing `--readonly`, explicit write mode, or confirmation bypass;
- target missing or another table owns the observed readiness/approval;
- official discovery absent, stale, failed, or conflicting;
- approved design/blueprint evidence absent;
- official upstream now owns a Seshat gap capability.

No failure degrades to a warning when it affects activation or execution
eligibility. Blockers do not create readiness records or approvals.

## Tests and acceptance criteria

The implementation is accepted only when test-first coverage proves:

1. A Claude plugin containing every expected skill plus one extra skill blocks.
2. An extra MCP server, agent, or hook blocks.
3. A plugin version/ref mismatch blocks even when expected skill files exist.
4. `@latest`, missing `--readonly`, `--readwrite`, and
   `--skipconfirmation` block the Power BI plugin.
5. A locked Codex projection containing exactly the selected skills passes;
   provenance mismatch or an extra projection blocks.
6. Power BI design and authoring capabilities name Microsoft as official owner;
   planning/management are explicitly incompatible or deferred.
7. A semantic pass or publish approval for table A cannot authorize any table B
   operation.
8. Missing official discovery keeps report authoring blocked; compatible
   discovery plus target gates allows the delegation decision without a manual
   override.
9. Formatting against an unready target or without approved-design evidence is
   blocked before a PBIR writer is recommended.
10. Any listed prerequisite produces a blocked decision and non-zero exit.
11. Ownership documentation and the capability manifest agree about active
    official executors.
12. Existing dbt/Dagster governed adapters, readiness hard stops, bundle drift
    checks, and static governance tests remain green.

## Non-goals

- Ratifying ADR 0018 or implementing F016 mutation.
- Publishing a Power BI report or changing a tenant.
- Installing, updating, disabling, or deleting a user's external plugins.
- Forking or copying official upstream guidance into Seshat.
- Replacing dbt Core, Dagster, or Microsoft executors.
- Inventing a numeric trust or compatibility score.

## Consequences

Governed Claude Power BI delegation may be unavailable until the upstream
bundle can be constrained or its complete contents are explicitly reviewed and
made compatible. That is an intentional blocker, not a fallback invitation.
Codex can continue using individually projected locked official skills. Future
upstream capability additions become visible review events instead of silent
changes to Seshat's effective architecture.
