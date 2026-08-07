# Ratify ledger: Spec 144 - Integration control-plane convergence

**Branch**: `144-integration-control-plane`

**Prepared**: 2026-08-07

**Status**: RATIFIED by Ahmed Shaaban, 2026-08-07; Phase 2 implementation authorized

## Phase classification

REQUIRED. The CLI is catalog-backed, but the compatibility module still carries
a second executable installer and registry.

## Decisions requiring ratification

1. Catalog `Component.required_paths` becomes the sole required-payload
   validation authority for official GitHub skill bundles.
2. `integrations_setup.py` becomes a thin compatibility facade; operational
   clone, MCP-write, runtime-provision, and installed-state code is removed.
3. Compatibility `IntegrationResult.name` uses canonical component IDs rather
   than the seven legacy aggregate labels.
4. Direct compatibility apply requires caller-supplied exact resolvers and
   fails closed without them; it never constructs live resolvers implicitly.

## Evidence

- Five focused integration test modules: 88 passed at baseline.
- Repository search: direct legacy operational consumers are confined to the
  focused legacy test module; CLI consumers already use catalog-backed aliases.
- Required-path validation is the one behavior that must migrate before legacy
  removal.
- Active Spec Kit fence and status-vocabulary contracts: 13 passed.
- Generated Claude/Codex bundle drift check: PASS.
- `git diff --check`: PASS (Windows line-ending advisory only for the active
  feature pointer).

## Ratification record

Ratifier:

Ahmed Shaaban

Date:

2026-08-07

Decision:

Ratified; Phase 2 implementation authorized.

Recorded from Ahmed Shaaban's explicit instruction: "I, Ahmed Shaaban, ratify
Spec 144 on 2026-08-07 and authorize Phase 2 implementation."

## Authorization boundary

Ratification authorizes Spec 144 implementation only. It does not authorize
later roadmap phases, push, PR, merge, publication, or live integration apply.

## Implementation closeout

Implementation and focused validation completed locally on 2026-08-07. The
spec remains **ratified** rather than claiming a landed/completed state because
the branch has not been merged to `main`. Validation and scope evidence are in
`evidence/validation.md` and `evidence/scope-review.md`.
