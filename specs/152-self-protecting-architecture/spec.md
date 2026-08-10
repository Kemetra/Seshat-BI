# Feature Specification: Self-Protecting Official-First Architecture

**Feature Branch**: `152-self-protecting-architecture`

**Created**: 2026-08-10

**Status**: ratified -- Ahmed Shaaban, 2026-08-10

**Status history**: draft

**Implementation**: Phase 11 tasks complete and locally validated on branch
`152-self-protecting-architecture`, 2026-08-10. Final Architecture Audit not
started in this state transition.

**Input**: Phase 11 protection audit at `85d3e96`. Protect only the two
demonstrated official-first regressions that current guards permit: an
upstream-backed Seshat capability with no declared Seshat delta, and undetected
drift in the five vendored `speckit-git-*` skills.

## Why this exists

The architecture is substantially protected already. Capability ownership,
public-skill uniqueness, official dbt/Dagster/Power BI delegation, route
resolution, generated bundle drift, execution/readiness separation, and
named-human approval all have executable negative tests. Adding parallel guards
for those invariants would create ceremony and duplicate authority.

Two narrow regressions can still pass.

1. `ownership_violations()` requires a delta only when
   `capability_owner: seshat-adapter`. A future upstream-backed Seshat
   orchestrator, governance layer, authoring layer, domain-knowledge layer, or
   product module can omit `seshat_delta` and pass. A constructed
   `seshat-orchestrator` entry with `upstream_project` and no delta currently
   returns no violations.
2. The capability `speckit-workflow-skills` owns fourteen vendored upstream
   skills, but `.specify/integrations/claude.manifest.json` hashes only nine.
   The five git-extension skills (`commit`, `feature`, `initialize`, `remote`,
   `validate`) are covered by neither provenance manifest. During the audit, a
   representative edit to `speckit-git-commit/SKILL.md` passed
   `export_agent_bundles.py --check` and all 68 relevant ownership/bundle tests.

This feature closes those two holes by strengthening the existing authorities.
It does not add a new runtime, CLI verb, `seshat check` rule, manifest family,
or architecture phase.

## User Scenarios and Testing

### User Story 1 - Every upstream-backed Seshat layer states its delta (P1)

A maintainer cannot register a Seshat-owned layer over an official upstream
without stating the concrete responsibility Seshat retains.

**Independent test**: Pass constructed upstream-backed entries for each
Seshat-owned owner class to the ownership oracle with a missing or blank
`seshat_delta`; each must fail and name the capability.

**Acceptance scenarios**:

1. Given a Seshat-owned capability with a nonblank `upstream_project`, when its
   delta is absent or blank, then the ownership oracle fails.
2. Given the same capability with a concrete nonblank delta, then the new check
   is clean.
3. Given an `official-upstream` or `vendored-upstream` capability, then the
   guard does not demand that upstream itself provide a Seshat delta.
4. Given an internal Seshat capability with no upstream project, then existing
   ownership rules remain unchanged.

### User Story 2 - All fourteen vendored Spec Kit skills are provenance-pinned (P1)

A maintainer can re-run or review the sanctioned Spec Kit installation and
detect drift in every vendored skill claimed by the capability manifest.

**Independent test**: Derive the fourteen skill paths from the
`speckit-workflow-skills` capability, reconcile them exactly with the Claude
integration manifest, and compare each normalized file hash.

**Acceptance scenarios**:

1. Given the clean repository, the capability references, manifest paths,
   version metadata, and normalized hashes all agree.
2. Given one referenced skill is missing from the manifest, the contract fails
   and names the path.
3. Given one vendored skill's bytes drift, the contract fails and names the
   path.
4. Given CRLF-only checkout differences, comparison normalizes line endings and
   does not report semantic drift.
5. Given the two Spec Kit manifests and init options claim different versions,
   the contract fails rather than accepting ambiguous provenance.

### User Story 3 - Existing architecture guards remain singular (P2)

The protection change does not duplicate already-effective routing, bundle,
readiness, approval, or official-delegation machinery.

**Independent test**: The implementation diff contains no new registered rule,
CLI command, route manifest, runtime module, CI workflow, or generated-bundle
mechanism.

## Requirements

### Ownership and Seshat delta

- **FR-001**: The existing ownership oracle MUST reject a capability when its
  owner is a Seshat-owned token, its `upstream_project` is nonblank, and its
  `seshat_delta` is absent, non-string, empty, or whitespace-only.
- **FR-002**: The Seshat-owned token set for FR-001 MUST be derived from the
  existing closed ownership vocabulary by selecting `seshat-*` tokens. No
  second manually maintained owner vocabulary may be introduced.
- **FR-003**: The existing rule requiring every `seshat-adapter` to declare a
  delta MUST remain intact, including adapters that do not declare an upstream
  project.
- **FR-004**: `official-upstream`, `vendored-upstream`, `human-deliverable`,
  `specified-not-built`, and `unclassified` MUST NOT be forced to invent a
  Seshat delta.
- **FR-005**: The real 110-entry capability manifest MUST remain clean under the
  strengthened oracle. This feature records architecture; it does not rewrite
  valid current deltas.

### Spec Kit provenance / KF-2

- **FR-006**: `.specify/integrations/claude.manifest.json` MUST cover exactly
  the fourteen `.claude/skills/speckit-*/SKILL.md` paths referenced by the
  `speckit-workflow-skills` capability.
- **FR-007**: The five previously uncovered paths MUST be added to that existing
  manifest with SHA-256 hashes of LF-normalized content. No new manifest family
  may be created.
- **FR-008**: A contract test MUST derive the expected paths from
  `docs/capabilities/capabilities.yaml`, not restate a fourteen-item list.
- **FR-009**: The contract MUST reject missing, unexpected, duplicate, blank,
  absolute, traversal, symlink, untracked, or non-file provenance targets.
- **FR-010**: The contract MUST compare LF-normalized SHA-256 values so Windows
  checkout line endings do not create false drift.
- **FR-011**: The contract MUST require
  `.specify/init-options.json:speckit_version`,
  `.specify/integrations/claude.manifest.json:version`, and
  `.specify/integrations/speckit.manifest.json:version` to agree.
- **FR-012**: Missing or malformed manifests, capability references, hashes, or
  versions MUST fail closed with a path-specific message.
- **FR-013**: The guard MUST sit in the existing CI-run test surface. It MUST NOT
  become a new shipped CLI, runtime service, or `seshat check` rule.

### Truthful closeout

- **FR-014**: After implementation, the `speckit-workflow-skills` update policy
  and `docs/capabilities/ownership-audit.md` MUST say KF-2 is closed, name the
  fourteen-file coverage, and cite the enforcing contract.
- **FR-015**: Documentation MUST NOT claim Spec Kit was upgraded, reinstalled,
  or fetched. The pinned baseline remains the sanctioned 0.8.10 install from
  commit `1eb0c98`.
- **FR-016**: Implementation MUST preserve the distinctions execution !=
  validation != readiness != approval != next action and MUST not change any
  readiness or approval behavior.

## Clarifications

### Session 2026-08-10

- Q: Is Phase 11 already satisfied? -> A: No. Two representative violations
  pass current guards, so the gaps have demonstrated detection value.
- Q: Should a new `seshat check` rule own these contracts? -> A: No. Ownership
  is already enforced by the independent capability oracle and provenance is a
  repository-internal vendoring contract. A new shipped rule would duplicate
  authority and affect adopters.
- Q: Should the five git skills get a third manifest? -> A: No. They were
  created by the same sanctioned Claude Spec Kit init as the other nine skills.
  Extending the existing Claude integration manifest closes coverage without a
  parallel source of truth.
- Q: Does advance authorization ratify this spec? -> A: No. The completed draft
  must be reviewed and explicitly ratified by a named human after it exists.
- Q: Was the completed draft ratified? -> A: Yes. Ahmed Shaaban explicitly
  ratified Spec 152 by name on 2026-08-10 and authorized its approved journey.

## Success Criteria

1. A representative upstream-backed Seshat wrapper without a delta fails the
   ownership oracle.
2. All current upstream-backed Seshat capabilities remain valid without data
   rewrites.
3. The manifest contract covers and verifies all fourteen vendored Spec Kit
   skills claimed by the capability inventory.
4. A missing manifest entry and a one-file content drift each fail the intended
   guard; clean restoration passes.
5. No new source of ownership truth, provenance manifest family, runtime,
   command, route, check rule, dependency, or CI workflow is introduced.
6. KF-2 is truthfully closed only after the enforcing tests pass.
7. All pre-existing targeted architecture guards remain green.

## Out of Scope

Spec Kit upgrade or re-installation; network fetches; modifying any vendored
`speckit-*` skill body; full extension-tree provenance; general-purpose
provenance tooling; new CLI or `seshat check` rules; route redesign; bundle
export redesign; dbt, Dagster, Power BI, Fabric, readiness, approval, or evidence
behavior changes; dependency or CI changes; Phase 9/10 redesign; Final
Architecture Audit; implementation of this draft.

## Assumptions

- Commit `1eb0c98` and the two existing manifests are the recorded baseline for
  the sanctioned Spec Kit 0.8.10 initialization.
- `pytest -m unit` continues to collect the contract and ownership tests in CI.
- The capability manifest remains the authored owner/scope authority; the
  provenance manifest records bytes and does not become an owner registry.
