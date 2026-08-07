# Adversarial plan review: Spec 144

**Performed**: 2026-08-07

**Posture**: Default-refuted.

**Verdict**: READY FOR HUMAN RATIFICATION.

## Challenges

### Does this merely rename the second installer?

No. The facade may only derive catalog metadata, call canonical plan/apply, and
project canonical rows. A structural contract rejects operational installer
logic and component registries in the facade.

### Is required validation being deleted to reduce line count?

No. It moves to the canonical `Component` and installer, where both presence and
staged activation consume it.

### Does compatibility apply silently reach the network?

No. Missing injected resolvers is a categorical failure with no writes.

### Is the CLI being redesigned?

No. Current flags, prompt, JSON, exit codes, workspace gate, planner, and apply
path remain. The active document is corrected to describe already-shipped truth.

### Does the plan perform Phase 6 activation?

No. It validates installed payload content only. Installed, activated, and
discoverable remain separate future concepts.

### Is destructive cleanup proven?

Yes. The exact current responsibility is legacy clone/MCP/runtime behavior; its
replacement is the already-shipped catalog installer. Required validation
survives via the migrated metadata. Direct callers retain imports and receive a
canonical projection. Focused tests cover routing, safety, installation, locks,
and rollback is a bounded code revert.
