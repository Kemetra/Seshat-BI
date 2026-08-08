# Adversarial plan review: spec 143

**Performed**: 2026-08-07

**Posture**: Default-refuted review. The plan is considered unsafe until its
ownership semantics, scope, validation locus, and rollback are supported by
repository evidence.

**Verdict**: READY FOR HUMAN RATIFICATION.

## Questions tested

### 1. Does the plan invent a second public-skill registry?

No. The skill set is loaded from `distribution/public-command-surface.yaml` on
every run. Constructed test inputs exercise the detector but do not become a
production list.

### 2. Does it misinterpret a caller reference as ownership?

No after revision. Explicit `references.public_skill` has precedence. The
fallback accepts only a same-name capability whose own surface is `skill`, so
`retail-check -> retail-govern` remains a caller relation rather than a second
owner.

### 3. Does it claim future Microsoft behavior as current truth?

No. `powerbi-workflows` is proposed as a Seshat orchestrator because its current
body routes only Seshat knowledge and helpers. Phase 3 may change that ownership
relationship after official delegation exists.

### 4. Can a generated projection become canonical?

No. The contract rejects the two generated integration roots, while allowing
reviewed `distribution/bundle-templates/` inputs.

### 5. Can an untracked scratch file satisfy the gate?

No. The path must be a contained, tracked, non-symlink regular file.

### 6. Does the phase modify runtime or distribution behavior?

No planned file edits affect public skill bodies, allowlists, MCPs, CLI dispatch,
dependencies, or generated destinations. Focused bundle and plugin gates prove
that boundary.

### 7. Is rollback bounded?

Yes. Revert two capability records, the doctor path correction, the oracle/tests,
and the directly related README paragraph. There is no migration, generated
artifact baseline, external registration, or data state to unwind.

## Residual judgment for the owner

The remaining decision is architectural rather than technical: approve or reject
the current-responsibility classification of the two routers and the explicit
source-integrity contract. The agent cannot ratify those classifications itself.

## Recommendation

Ratify Phase 1 as written. Do not authorize Phase 2 or later through this ledger.
