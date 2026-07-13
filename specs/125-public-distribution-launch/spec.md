# Feature Specification: Seshat BI Public Beta Distribution

**Feature Branch**: `125-public-distribution-launch`

**Created**: 2026-07-13

**Status**: Repository implementation authorized; external configuration and publication not authorized

**Input**: Owner-directed request for one coordinated Seshat BI Public Beta release candidate across the `seshat-bi` Python package, a Claude Code marketplace/plugin, an OpenAI Codex skills/plugin distribution, and the canonical `ahmed-shaaban-94/Seshat_BI` repository. The owner subsequently authorized reversible repository implementation while retaining every external, version, publication, and rollback gate.

## Scope and Authorization Lanes

This feature prepares a release candidate; it is not itself a release. It separates five lanes that have different authorities and completion evidence:

1. **Repository implementation** -- reversible, reviewable changes to package metadata, deterministic bundle generation, tests, documentation, manifests, and release automation definitions.
2. **PyPI and GitHub configuration** -- protected environments, named reviewers, Trusted Publishing identity, tag protection, and repository settings performed by an authorized owner.
3. **Claude publication** -- repository marketplace validation and public installation are repository work; submission to Anthropic's public catalog, if desired, is a separate owner action.
4. **Codex submission/publication** -- repository and CLI distribution are distinct from OpenAI's public plugin submission and review process; public submission requires an eligible, verified publisher.
5. **Irreversible release actions** -- version approval, release tag creation, package upload, GitHub Release publication, and public catalog submissions require a named owner and are never performed or approved by an agent.

### In Scope

- Remaining work needed to produce and verify one coordinated Public Beta release candidate.
- A single, deterministic export path from the canonical Seshat Knowledge Bases into self-contained Claude Code and Codex bundles.
- Public-install and rollback requirements for Python, Claude Code, and Codex.
- Protected, owner-approved publication boundaries and evidence.
- External acceptance from fresh workspaces that do not contain the Seshat development repository or a pre-existing `AGENTS.md`.
- A release-blocker audit of merged Spec 124 outputs, including the reported `KPI-MC-15` omission.

### Out of Scope

- Creating or changing external accounts, publishers, environments, catalog entries, or repository protections.
- Uploading to a package index, creating or moving a tag, creating a release, or submitting a public plugin.
- Ratifying a version or release through repository implementation, CI, analysis, review, merge, or agent action.
- Replacing canonical Knowledge Bases with generated copies or creating a second readiness engine.
- Power BI execution-adapter work, live database provisioning, or any bypass of the existing readiness gates.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove a release candidate is internally consistent (Priority: P1)

A release maintainer needs one evidence-backed verdict showing that the merged baseline is suitable for release preparation, that already-completed work is not recreated, and that every release-blocking inconsistency is either resolved or named as a blocker.

**Why this priority**: Publishing an inconsistent registry, version set, or artifact would make every distribution surface untrustworthy. This audit is the first release gate.

**Independent Test**: Evaluate the release-candidate source without publishing it; every required artifact, registry entry, version value, and cross-reference is either consistent or produces one concrete blocker with a named corrective action.

**Acceptance Scenarios**:

1. **Given** current `main` includes the completed Spec 124 implementation, **When** the release audit runs, **Then** it treats those merged artifacts as baseline and does not schedule their recreation.
2. **Given** the reported `KPI-MC-15` omission, **When** the authoritative KPI registry and its projections are inspected, **Then** the audit records whether the entry exists and is valid; if it already exists, no duplicate repair is planned and missing regression coverage may still be planned.
3. **Given** any mismatch among package, plugin, changelog, tag, or release versions, **When** the audit completes, **Then** publication is blocked and the exact conflicting values are reported.
4. **Given** a claimed pass with missing evidence, **When** the release audit evaluates it, **Then** the result remains blocked rather than inferring success.

---

### User Story 2 - Install and remove the Python product cleanly (Priority: P1)

A new user installs `seshat-bi` in an isolated environment, creates a fresh project, sees the truthful next governed action, can upgrade to the approved Public Beta version, and can uninstall it without leftover commands or project damage.

**Why this priority**: The Python package is the common runtime used by both agent integrations and is the narrowest independent route to first success.

**Independent Test**: Use only built release artifacts in clean, throwaway environments; inspect their contents and metadata, install through the documented user path, exercise the first-success journey, simulate an upgrade, uninstall, and verify that no prohibited dependency or residue remains.

**Acceptance Scenarios**:

1. **Given** a clean supported Windows environment, **When** a user installs the wheel through the public command path, **Then** `seshat` exposes the documented commands and a new project reports Source Ready as `not_started` with evidence and blockers rather than a fabricated pass or score.
2. **Given** the wheel and source distribution, **When** their metadata and contents are inspected, **Then** each contains only declared public runtime resources, required license/readme metadata, and no secrets, caches, test-only dependencies, local paths, or development-only material.
3. **Given** a prior supported Public Beta installation, **When** the approved upgrade path is used, **Then** the installed version and command behavior advance together and user project data is preserved.
4. **Given** an installed package, **When** it is uninstalled, **Then** both public console commands are removed while the user's project remains intact.
5. **Given** an unsupported platform or Python version, **When** installation is attempted, **Then** failure is explicit and documented rather than partially installing an unusable product.

---

### User Story 3 - Use Seshat through Claude Code without the development repository (Priority: P1)

A Claude Code user adds the public GitHub marketplace, installs the `seshat-bi` plugin, opens a fresh synthetic retail project with no `AGENTS.md`, loads the required Seshat skills and Knowledge Bases from the installed plugin, and receives the truthful next governed action.

**Why this priority**: The existing draft plugin references repository-local guidance and therefore does not yet prove standalone public use.

**Independent Test**: Install the plugin from the canonical public repository into a clean external workspace with no development checkout and no `AGENTS.md`; run the declared skill/commands over synthetic source evidence and confirm the agent stops at the first named-human gate.

**Acceptance Scenarios**:

1. **Given** a reachable canonical repository, **When** the user adds its root Claude marketplace and installs `seshat-bi`, **Then** Claude Code discovers the plugin, its skills, and its supported commands using the public GitHub flow.
2. **Given** a fresh workspace without `AGENTS.md`, **When** Claude uses the installed plugin, **Then** the bundle supplies the minimum Seshat operating contract and Knowledge Bases internally and does not instruct the user to clone the development repository.
3. **Given** a synthetic source with ambiguous grain or PII policy, **When** Claude inspects it, **Then** it reports the concrete blocker, names the required human decision, and does not author silver SQL, expose the sensitive value, or grant approval.
4. **Given** a plugin bundle, **When** it is compared with the deterministic export manifest, **Then** no file outside the public allowlist is present and no allowlisted file is missing.

---

### User Story 4 - Use Seshat through Codex without the development repository (Priority: P1)

A Codex CLI or IDE user installs the Seshat Codex distribution, invokes a Seshat skill with `$`, opens a fresh synthetic retail project, and receives the same governed next action and human-gate stop as the Python and Claude routes.

**Why this priority**: Codex uses its own supported skill, plugin, catalog, and repository-guidance structures; copying the Claude manifest would create an invalid or misleading distribution.

**Independent Test**: Install the Codex plugin/skills from the canonical public source into clean CLI and IDE contexts, invoke at least one skill explicitly, and confirm that bundled knowledge and guardrails work without a development checkout.

**Acceptance Scenarios**:

1. **Given** the generated Codex bundle, **When** it is inspected, **Then** it contains the supported Codex plugin manifest and skill layout rather than a renamed Claude manifest.
2. **Given** a clean Codex CLI session, **When** the user installs the distribution and invokes `$seshat-bi`, **Then** the skill is discovered and loads only the knowledge needed for the task.
3. **Given** a clean supported IDE session, **When** the same installed distribution is used, **Then** the Seshat skills are available and produce behavior consistent with the CLI acceptance scenario.
4. **Given** a fresh repository with no Seshat-specific `AGENTS.md`, **When** Codex starts, **Then** the plugin skill carries its own guarded workflow; when a Seshat repository does contain `AGENTS.md`, the file remains compatible with Codex's repository instruction discovery.
5. **Given** a repository-installable Codex plugin, **When** an OpenAI public plugin listing is desired, **Then** submission is treated as a separate owner-approved action with its own eligibility and review evidence, not as an automatic consequence of repository availability.

---

### User Story 5 - Export canonical knowledge deterministically (Priority: P1)

A maintainer updates the canonical Seshat Knowledge Bases once and regenerates both agent bundles from an explicit public allowlist, obtaining byte-stable outputs and a reviewable record of every included file.

**Why this priority**: Hand-copied knowledge would drift between agents and could accidentally ship private, development-only, or client-specific material.

**Independent Test**: Run the export twice from the same clean source; the output trees and file digests are identical, every output maps to exactly one allowlisted canonical source, and unlisted files are rejected.

**Acceptance Scenarios**:

1. **Given** unchanged canonical sources, **When** export runs twice, **Then** both Claude and Codex bundles are byte-identical and have stable manifests.
2. **Given** a new canonical Knowledge Base file not yet allowlisted, **When** export runs, **Then** it is excluded and the drift check tells the maintainer to review the allowlist explicitly.
3. **Given** a generated file edited by hand, **When** drift validation runs, **Then** the change is rejected and the maintainer is directed to edit the canonical source and regenerate.
4. **Given** a symlink, secret-shaped value, client token, absolute path, cache, or executable outside the permitted script set, **When** export evaluates it, **Then** generation fails closed.

---

### User Story 6 - Authorize, publish, verify, and roll back coherently (Priority: P2)

A named release owner reviews one evidence pack, approves the exact version and immutable source, and can authorize each public surface separately while retaining a documented rollback path if any surface fails.

**Why this priority**: Release configuration is useful only after the candidate is internally consistent and externally installable; publication itself remains a human gate.

**Independent Test**: Perform a dry-run authorization review with no publication; the pack identifies the immutable source, artifacts, version, approvals, external configuration steps, surface-specific verification, and rollback action for every channel.

**Acceptance Scenarios**:

1. **Given** a release candidate, **When** versions are compared, **Then** the Python package, Claude plugin, Codex plugin, generated bundle manifests, changelog heading, release notes, proposed tag, and proposed GitHub Release all use the exact same owner-approved version.
2. **Given** a protected publishing workflow, **When** it reaches the package publication job, **Then** a named GitHub environment reviewer must approve before short-lived trusted credentials can be requested.
3. **Given** no named approval or a source/version mismatch, **When** publication is requested, **Then** every irreversible action remains blocked.
4. **Given** one failed public surface, **When** rollback is initiated, **Then** the plan preserves evidence, withdraws or reverts only the affected surface as appropriate, restores truthful public wording, and reruns external verification before replacement publication.

### Edge Cases

- The package name is unavailable, reserved, or owned by an unexpected publisher at authorization time.
- A previously created tag exists while the package metadata or changelog still describes an unpublished state.
- A wheel passes installation but the source distribution cannot rebuild the same wheel in an isolated environment.
- The package index rejects re-upload of an immutable version during rollback; recovery must use a new owner-approved version.
- The Claude marketplace loads but a cached plugin version omits newly generated knowledge.
- A Claude plugin file reaches outside its installed plugin root.
- Codex CLI, IDE, and desktop/plugin-directory capabilities differ by installed product version.
- A public plugin submission portal or terminology changes after this plan is approved.
- The external test workspace has no Git repository, no `AGENTS.md`, no database, or no optional database driver.
- Synthetic data contains a lookalike column name but no approved semantic mapping.
- The explicit knowledge allowlist references a deleted source, omits a required transitive reference, or includes a non-public file.
- A release job is triggered from an unprotected tag, an unreviewed workflow revision, or a fork.
- Only one distribution surface succeeds; public documentation must not imply the others are available.

## Requirements *(mandatory)*

### Functional Requirements -- Release baseline and consistency

- **FR-001**: The release plan MUST treat the current merged `main` as the completed baseline and MUST NOT recreate already-merged features.
- **FR-002**: The plan MUST define one release-blocker audit covering package metadata, distribution contents, registry integrity, generated bundles, versions, documentation, and public-install claims.
- **FR-003**: The audit MUST explicitly evaluate `KPI-MC-15`; when it is already present and valid, the plan MUST record the issue as resolved in baseline and MUST NOT create a duplicate entry.
- **FR-004**: Every pass/fail claim MUST cite concrete evidence; missing evidence MUST remain a blocker and MUST NOT be expressed as confidence or a numeric readiness score.
- **FR-005**: Existing tags and release statements MUST be reconciled with the package's actual publication history before a Public Beta version is approved.

### Functional Requirements -- Python distribution

- **FR-006**: The release candidate MUST produce exactly one wheel and one source distribution from the same immutable source.
- **FR-007**: Both Python artifacts MUST carry complete, consistent public metadata, including name, version, description, supported Python range, license, readme, project URLs, and runtime dependency declarations.
- **FR-008**: Artifact-content policy MUST explicitly list required inclusions and prohibited development, cache, secret, local-path, and client-specific content.
- **FR-009**: The source distribution MUST rebuild the release wheel in an isolated environment without relying on untracked repository files.
- **FR-010**: Release validation MUST include strict metadata/render checks, artifact inspection, clean isolated installation, first-success behavior, upgrade, uninstall, and command-removal checks.
- **FR-011**: Windows MUST remain a blocking release smoke; other documented supported systems MUST have declared blocking or explicitly non-blocking status.
- **FR-012**: A normal install MUST exclude developer, test, browser, live-database, and optional engine dependencies.

### Functional Requirements -- Knowledge export

- **FR-013**: The existing Knowledge Bases MUST remain canonical; generated agent bundles MUST never become editable sources of truth.
- **FR-014**: A public knowledge allowlist MUST enumerate every permitted canonical source file explicitly, without recursive wildcards or implicit directory inclusion.
- **FR-015**: The exporter MUST fail closed on missing allowlisted sources, unexpected generated files, unsafe file types, symlinks, absolute paths, path traversal, secrets, client tokens, and disallowed executables.
- **FR-016**: Export output MUST be deterministic across repeated runs from the same source and MUST include a stable source-to-output digest manifest.
- **FR-017**: Generated files MUST carry a machine-detectable generated-origin notice where their format permits it, and drift validation MUST reject hand edits.
- **FR-018**: Both agent bundles MUST include every transitive reference needed by their exported skills so no installed skill references a file outside its bundle.

### Functional Requirements -- Claude Code distribution

- **FR-019**: The canonical repository root MUST contain the one public Claude marketplace manifest and MUST not require users to add a development-only subdirectory marketplace.
- **FR-020**: The Claude `seshat-bi` plugin MUST be self-contained within its install root and MUST use Claude Code's supported plugin manifest and component locations.
- **FR-021**: The Claude bundle MUST provide Seshat operating guidance, required Knowledge Bases, and supported skills/commands without depending on a workspace `AGENTS.md` or a clone of the development repository.
- **FR-022**: Claude external acceptance MUST cover public GitHub marketplace add, plugin install, plugin refresh/reload, component discovery, fresh-workspace behavior, synthetic-source inspection, truthful next action, and human-gate stop.
- **FR-023**: Repository publication and any optional submission to Anthropic's public plugin catalog MUST be documented as separate actions with separate owner authorization.

### Functional Requirements -- Codex distribution

- **FR-024**: The repository MUST retain a Codex-compatible `AGENTS.md` for repository work and MUST not treat that file as the portable plugin knowledge payload.
- **FR-025**: Repository-scoped Codex skills MUST use the supported `.agents/skills/<skill>/SKILL.md` structure, and public reusable distribution MUST use a first-class Codex plugin when current official guidance supports it.
- **FR-026**: The Codex plugin MUST have its own supported manifest and component layout; Claude manifest fields MUST NOT be assumed compatible.
- **FR-027**: The repository-scoped Codex plugin catalog MUST use current Codex terminology and supported location; documentation MUST distinguish a repository marketplace/catalog from OpenAI's public plugin submission, review, and listing process.
- **FR-028**: Codex acceptance MUST cover CLI and IDE skill discovery, explicit `$` invocation, fresh-workspace behavior, generated Knowledge Base access, synthetic-source inspection, truthful next action, and human-gate stop.
- **FR-029**: OpenAI public plugin submission MUST be a separate owner-approved action and MUST name the required publisher eligibility, verification, listing, test, policy, and review evidence.

### Functional Requirements -- Version and publication control

- **FR-030**: One owner-approved release version MUST be the source for Python, Claude, Codex, generated manifests, changelog, release notes, tag, and GitHub Release versions.
- **FR-031**: A deterministic version-sync check MUST fail before publication when any governed version or tag value differs.
- **FR-032**: Package publication MUST use short-lived trusted identity credentials bound to the canonical repository, one narrowly scoped release workflow, and a protected environment.
- **FR-033**: The package publication environment MUST require approval from a named eligible owner and MUST grant identity-token permission only to the publish job.
- **FR-034**: Build and validation MUST be separated from the credential-bearing publish job; the publish job may consume only previously validated immutable artifacts.
- **FR-035**: Tag creation, package upload, GitHub Release publication, Claude public-catalog submission, and OpenAI public plugin submission MUST remain blocked until their specific named-owner approval is recorded.
- **FR-036**: No agent, test, workflow, or repository merge may self-ratify the release or infer approval from a passing static check.

### Functional Requirements -- Verification and rollback

- **FR-037**: Public-install verification MUST use clean external environments and public sources, never editable installs or files from the development checkout.
- **FR-038**: Every distribution surface MUST have a post-publication verification procedure that records the exact version, source, commands, outcomes, and evidence timestamp.
- **FR-039**: Rollback MUST define channel-specific actions for yanking/withdrawing a package, reverting marketplace/plugin pointers, correcting public catalog listings, and restoring truthful documentation.
- **FR-040**: Because published package files and tags are immutable, replacement publication after a defective release MUST use a new owner-approved version rather than overwrite the broken artifact.
- **FR-041**: Rollback and replacement release MUST repeat the full authorization and external acceptance gates; a rollback record grants no new approval.

### Required Planning Contracts

- **FR-042**: The plan MUST include a **Public Knowledge Allowlist Contract**.
- **FR-043**: The plan MUST include a **Generated Claude Bundle Contract**.
- **FR-044**: The plan MUST include a **Generated Codex Bundle Contract**.
- **FR-045**: The plan MUST include a **Release Artifact Contents Contract**.
- **FR-046**: The plan MUST include a **Version Synchronization Contract**.
- **FR-047**: The plan MUST include separate **External Claude Acceptance** and **External Codex Acceptance** contracts.
- **FR-048**: The plan MUST include a **Publication Authorization Boundary Contract** that distinguishes all five authorization lanes.

### Security and Privacy Requirements

- **SEC-001**: No release artifact, bundle, manifest, log, acceptance fixture, or evidence record may contain a real credential, DSN, host, token, raw PII value, machine-specific path, or named-client data.
- **SEC-002**: Synthetic retail acceptance data MUST be fictional, minimal, and intentionally include ambiguity/PII-shaped cases without containing real personal data.
- **SEC-003**: External plugin installation MUST not silently enable network services, connectors, MCP servers, hooks, or executable scripts beyond those declared and reviewed in the plugin contract.
- **SEC-004**: Release workflows MUST use least privilege, immutable action references or approved release channels, protected environments, and no long-lived package-index credential.
- **SEC-005**: The public allowlist and generated bundles MUST exclude `.env`, local settings, caches, worktrees, test outputs, approval drafts, and any client-specific or development-only artifact.

### Key Entities

- **ReleaseCandidate**: An immutable source revision plus proposed version, validated artifacts, bundle manifests, audit results, and approval state.
- **ReleaseVersion**: The single owner-approved semantic version projected into every governed surface.
- **PublicKnowledgeAllowlistEntry**: One explicit canonical source path, public classification, permitted destination(s), expected type, and digest policy.
- **GeneratedAgentBundle**: A self-contained Claude or Codex plugin tree generated from canonical workflow sources and allowlisted Knowledge Base files.
- **BundleManifestEntry**: A canonical source path, generated destination path, content digest, transformation identifier, and bundle target.
- **DistributionArtifact**: A wheel, source distribution, Claude plugin bundle, Codex plugin bundle, or release evidence file with required/prohibited contents.
- **ExternalAcceptanceRun**: One clean-environment execution record for a distribution surface, including product version, agent version/surface, inputs, actions, outcomes, and evidence.
- **PublicationApproval**: A named human decision scoped to one irreversible action, one exact candidate, one version, and one timestamp.
- **RollbackRecord**: Evidence of a defective surface, containment action, truthful public status, replacement version decision, and re-verification status; it grants no approval.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of governed release-version locations match the one owner-approved version before any publication action becomes eligible.
- **SC-002**: The release audit reports zero unresolved release blockers, zero duplicate KPI registry IDs, and explicitly confirms the status of `KPI-MC-15` from authoritative evidence.
- **SC-003**: Exactly one wheel and one source distribution pass strict metadata checks, declared-content inspection, isolated rebuild, clean installation, upgrade, and uninstall acceptance.
- **SC-004**: A new Windows user completes install, project creation, synthetic-source inspection, and receives the first truthful governed action within 15 minutes, without a database, Power BI Desktop, or development-repository clone.
- **SC-005**: Both Claude Code and Codex complete their external acceptance journeys in fresh workspaces with zero references to files outside the installed bundle and zero dependency on a pre-existing `AGENTS.md`.
- **SC-006**: 100% of generated Claude and Codex files map to explicit public allowlist entries or reviewed bundle-only templates; zero unexpected files appear in either bundle.
- **SC-007**: Two consecutive exports from the same source produce identical file lists and digests for both bundles.
- **SC-008**: In every synthetic ambiguity, PII, grain, or approval scenario, both agents return the same allowed next-action class and stop at the same named-human gate; neither produces silver SQL, exposes sensitive values, skips a stage, or emits a readiness score.
- **SC-009**: Every irreversible action is protected by a named-owner approval bound to the exact candidate and version; zero actions accept an agent-generated or inferred approval.
- **SC-010**: Each of the Python, Claude, and Codex surfaces has one independently executable rollback procedure and one clean public re-verification procedure documented before release authorization.
- **SC-011**: Public-install documentation contains zero development-only install commands in the primary user journeys and clearly labels any contributor-only path.
- **SC-012**: Reviewers can trace every acceptance assertion to one contract, one task, and one evidence-producing validation step without consulting an external private document.

## Assumptions

- The canonical repository remains `ahmed-shaaban-94/Seshat_BI` and stays publicly reachable for repository-backed agent distribution.
- The Python distribution name remains `seshat-bi`, subject to an owner re-check of package-index availability immediately before configuration.
- A prior `v0.1.0` repository tag exists while `pyproject.toml` still carries `0.1.0`; a likely next Public Beta proposal is `0.2.0` because merged additive capabilities have accumulated, but the version remains a named-owner decision.
- `KPI-MC-15` is present in the current authoritative registry and points to the Average Basket Size Units contract; this feature plans verification/regression hardening, not duplication, unless later baseline evidence changes.
- The five canonical Knowledge Base roots are the SQL, DAX, Python, Big-data, and Retail KPI skills under `skills/`; the implementation plan must enumerate public files explicitly rather than export entire directories implicitly.
- Claude Code and Codex platform formats and submission requirements can change; implementation must re-check current official documentation at execution time and fail closed on unsupported fields.
- Repository marketplace/catalog availability is not equivalent to acceptance into Anthropic's public catalog or OpenAI's public plugin listing.
- Public Beta may launch repository/Python distribution before either official catalog review completes, provided documentation states each surface's actual availability truthfully and the owner approves that staged availability.
- Live database acceptance remains deferred unless a DSN and the relevant optional dependency are explicitly supplied; offline acceptance must stop truthfully at the live boundary.
