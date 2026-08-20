# Specification Quality Checklist: Capability-oriented setup ("Seshat Setup")

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-20
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Delta-spec specific checks

- [x] Does not restate requirements owned by specs 143-150
- [x] Names the owning spec for every reused concern
- [x] Introduces no second capability registry, installer, resolver, verifier, or state store (FR-011, FR-017)
- [x] Does not inherit or restate the provisioning approval defect (FR-018, issue #671)
- [x] FR count within the 14-18 target band for a delta (20 FRs -- see Notes)
- [x] Capability strength vocabulary does not collide with the readiness status values

## Notes

- **FR count is 20, slightly above the 14-18 target.** FR-017 through FR-020 are
  boundary requirements (what this feature must NOT do) rather than added
  behavior. Behavioral FRs number 16, inside the band. The boundary four are
  retained because each prevents a specific documented failure mode: a second
  registry, inheriting the #671 approval defect, inferring readiness from install
  success, and requiring journey changes per new provider. Collapsing them would
  make the delta boundary implicit, which is the failure this spec exists to
  avoid.
- **FR-002 narrowed after review.** It originally claimed derivation *replaces*
  union-of-all-profiles default selection. Spec 144 FR-010 requires "the current
  CLI flags ... MUST survive"; whether that binds flag existence or observable
  default behavior is genuinely ambiguous. Claiming the replacement would have
  silently amended a ratified requirement -- the same defect class that pushed the
  approval fix out to issue #671. FR-002 now states derivation is *available* as
  the basis, and the default question is owner decision 1.
- **Owner decisions: two resolved by evidence, one genuinely open.** Decision 1
  (may derivation displace the default?) was settled by spec 144 **FR-006**:
  `DEFAULT_PROFILE` is an exported public constant, so its value is contract, and
  FR-006 protects exported constants -- the FR-010 ambiguity did not need
  resolving. Decision 2 (must derivation always commit to a strength?) was settled
  by `constitution.md:523-527` -- a positive state must carry evidence and must not
  be a fabricated confidence. Decision 3 (sequencing vs #671) was ruled by the
  owner on 2026-08-20: **SEQUENTIAL** -- #671 lands first, and it blocks all spec
  153 implementation including the read-only stories.
- **Implementation is BLOCKED pending issue #671.** This spec is complete and
  reviewable; it is not buildable yet. Any later session picking this up must
  verify #671 has landed before writing code.
- **Method note:** both resolutions came from reading the *full* requirement rather
  than a grep line. FR-006 sits three lines above the FR-010 originally grepped,
  and the constitution's rule is worded "fabricated confidence number", not the
  "NO FAKE CONFIDENCE" heading first searched for.
- **Zero implementation performed.** No source file was modified; no plan.md or
  tasks.md was created.
- Sequencing dependency on issue #671 is recorded in Dependencies and Assumptions.
  The spec is written to permit read-only Stories 1-3 in parallel with that fix,
  but that sequencing is owner decision 3.
