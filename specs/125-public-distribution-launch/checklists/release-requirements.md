# Release Requirements Checklist: Seshat BI Public Beta Distribution

**Purpose**: Review whether the specification, plan, and contracts are complete, clear, consistent, measurable, and authorization-safe before implementation or release work begins.
**Created**: 2026-07-13
**Feature**: [spec.md](../spec.md)
**Depth**: Formal release gate
**Use**: Each item evaluates the quality of the written requirements, not whether future implementation has passed.

## 1. Baseline and Scope Completeness

- [x] CHK001 Is the exact completed baseline identified so implementation cannot recreate already-merged features? [Spec §Scope; FR-001; Research §Baseline Findings]
- [x] CHK002 Does the release-blocker audit enumerate every governed concern: metadata, artifacts, registry, bundles, versions, docs, and install claims? [FR-002]
- [x] CHK003 Is the `KPI-MC-15` requirement explicit about authoritative evidence, uniqueness, and no duplicate repair when already present? [FR-003; SC-002]
- [x] CHK004 Are evidence, blocker, and no-score semantics defined for every audit verdict? [FR-004; AGENTS.md hard stops]
- [x] CHK005 Is the existing-tag/publication-history contradiction required to be resolved before version approval? [FR-005; Research §Baseline Findings]
- [x] CHK006 Are specification/planning outputs clearly separated from implementation, external configuration, publication, and ratification? [Spec §Scope and Authorization Lanes]
- [x] CHK007 Are live database, Power BI execution, and unrelated product work explicitly out of scope? [Spec §Out of Scope]
- [x] CHK008 Are the conditions for a truthful partial launch defined so unavailable surfaces cannot be implied as public? [Spec US6; PAB-1 §Staged availability]

## 2. Python Artifact Requirements

- [x] CHK009 Is “exactly one wheel and one sdist from one immutable source” stated without ambiguity? [FR-006; RAC-1 §Artifact set]
- [x] CHK010 Are all required public metadata fields enumerated for both Python artifacts? [FR-007; RAC-1 §Python metadata requirements]
- [x] CHK011 Are required and prohibited wheel contents defined at a file-category level sufficient for contract tests? [FR-008; RAC-1 §Wheel contents]
- [x] CHK012 Are required and prohibited sdist contents defined, including isolated-build closure? [FR-008--FR-009; RAC-1 §Source distribution contents]
- [x] CHK013 Is the allowed normalization/parity boundary between an original wheel and sdist-rebuilt wheel specified clearly enough to avoid arbitrary exceptions? [FR-009; RAC-1 §Validation sequence]
- [x] CHK014 Are strict metadata/render validation and `twine check --strict` requirements explicit for both artifacts? [FR-010; RAC-1]
- [x] CHK015 Are clean install, first success, upgrade, uninstall, command removal, and project preservation each independently observable? [FR-010; RAC-1 §Python lifecycle matrix]
- [x] CHK016 Is Windows clearly blocking, and must every other claimed supported system have an explicit blocking/informational status? [FR-011]
- [x] CHK017 Is normal-install dependency exclusion complete for dev, test, browser, live-DB, and engine extras? [FR-012]
- [x] CHK018 Is unsupported Python/platform failure behavior defined as explicit failure rather than partial installation? [Spec US2 Acceptance 5]
- [x] CHK019 Are immutable package-version and no-overwrite rules complete for failed releases? [FR-040; RAC-1 §Immutability]

## 3. Canonical Knowledge and Allowlist

- [x] CHK020 Are the five canonical Knowledge Base entrypoints named and kept as the only editable knowledge sources? [FR-013; Research §Canonical Knowledge]
- [x] CHK021 Does the allowlist contract require literal file paths and prohibit recursive/implicit inclusion? [FR-014; PKA-1 Rules 1--6]
- [x] CHK022 Are every entry's classification, target, transform, required state, notice policy, and review reason defined? [PKA-1 §Required document shape]
- [x] CHK023 Are missing files, symlinks, traversal, absolute paths, collisions, unsafe media types, and disallowed executables all fail-closed cases? [FR-015; PKA-1 §Export validation]
- [x] CHK024 Are secret, client, PII, cache, local-setting, approval-draft, and test-output exclusions explicit? [SEC-001; SEC-005; PKA-1 Rule 10]
- [x] CHK025 Is transitive-reference closure required per target so no installed skill can reference outside its bundle? [FR-018; PKA-1 Rule 5]
- [x] CHK026 Are determinism inputs/outputs defined, including ordering, transforms, digests, and forbidden environmental fields? [FR-016; PKA-1 §Determinism and provenance]
- [x] CHK027 Is the generated-origin/hand-edit rejection rule clear for formats that can and cannot carry comments? [FR-017; PKA-1]
- [x] CHK028 Is a newly added but unallowlisted canonical file's behavior specified as excluded pending explicit review? [Spec US5 Acceptance 2; PKA-1]
- [x] CHK029 Is every output required to map to either one allowlist entry or one reviewed template ID? [SC-006; PKA-1]

## 4. Claude Code Distribution

- [x] CHK030 Is the root `.claude-plugin/marketplace.json` declared the sole public Claude marketplace? [FR-019; GCB-1 §Root marketplace]
- [x] CHK031 Is the competing nested marketplace's required disposition unambiguous? [GCB-1 §Root marketplace]
- [x] CHK032 Are Claude's plugin manifest and component locations defined independently of Codex? [FR-020; GCB-1 §Required bundle shape]
- [x] CHK033 Is the installed plugin required to carry its own operating contract and knowledge rather than depend on `AGENTS.md`, `CLAUDE.md`, or a clone? [FR-021; GCB-1 §Plugin behavior]
- [x] CHK034 Are missing-Python and missing-live-DB behaviors defined without repository-local import instructions or fabricated passes? [GCB-1 Rule 4; ECA-1 §Expected semantic outcome]
- [x] CHK035 Is every Claude plugin path/reference constrained to its cached plugin root? [GCB-1 §Prohibited content and references]
- [x] CHK036 Are public marketplace add/install, refresh/cache selection, discovery, update, uninstall, and workspace preservation all covered? [FR-022; ECA-1 §Acceptance journey]
- [x] CHK037 Is optional Anthropic public-catalog submission clearly separate from repository marketplace availability and separately approved? [FR-023; PAB-1]
- [x] CHK038 Are undeclared Claude hooks, MCP servers, connectors, binaries, and network services prohibited by default? [SEC-003; GCB-1 Rule 8]

## 5. Codex Distribution

- [x] CHK039 Is root `AGENTS.md` defined as repository guidance rather than portable plugin payload? [FR-024; GXB-1 §Repository compatibility]
- [x] CHK040 Are repository-scoped `.agents/skills/<skill>/SKILL.md` and public plugin `skills/<skill>/SKILL.md` roles distinguished? [FR-025; GXB-1]
- [x] CHK041 Is `.codex-plugin/plugin.json` required and explicitly protected from Claude-manifest assumptions? [FR-026; GXB-1 §Manifest requirements]
- [x] CHK042 Is `.agents/plugins/marketplace.json` correctly scoped as a repository catalog/marketplace with paths relative to repository root? [FR-027; GXB-1 §Repository catalog]
- [x] CHK043 Does terminology use OpenAI's current **public plugin submission/review/listing** language while allowing `marketplace` only where current repository/personal CLI terminology uses it? [FR-027; GXB-1 §Repository catalog]
- [x] CHK044 Are `$seshat-bi`, `/skills`, and at least one exported Knowledge Base skill invocation required and observable? [FR-028; EXA-1 §CLI journey]
- [x] CHK045 Are both Codex CLI and IDE discovery/behavior required, including exact host-version evidence? [FR-028; EXA-1]
- [x] CHK046 Is fresh-workspace behavior with no `AGENTS.md` required independently from the repository-guidance compatibility test? [GXB-1; EXA-1 §Repository guidance check]
- [x] CHK047 Are apps, MCP servers, connectors, hooks, and network capabilities prohibited for the narrow skills-only Public Beta? [SEC-003; GXB-1 §Plugin behavior]
- [x] CHK048 Are current official validator/schema rechecks required at implementation and release time? [Spec Assumptions; GXB-1 §Manifest requirements]
- [x] CHK049 Are OpenAI public plugin eligibility, verified identity, listing, support/privacy/terms, tests, policy, and review evidence defined before submission? [FR-029; PAB-1]
- [x] CHK050 Is repository installation explicitly prevented from implying OpenAI public plugin acceptance? [Spec US4 Acceptance 5; EXA-1 §OpenAI public plugin boundary]

## 6. Cross-Agent Acceptance Semantics

- [x] CHK051 Is one fictional synthetic retail fixture required for Python, Claude, and Codex without reusing a client/example schema as universal truth? [SEC-002; Research §Cross-Agent Acceptance]
- [x] CHK052 Does the fixture deliberately exercise ambiguous grain, PII-shaped data, missing approvals, and the live boundary? [Spec Edge Cases; ECA-1/EXA-1]
- [x] CHK053 Are semantic parity dimensions defined as stage, outcome class, blocker/evidence class, and named gate rather than exact prose? [SC-008; EXA-1 §Expected semantic parity]
- [x] CHK054 Is “truthful next governed action” constrained to exactly one next action or one concrete blocked stop? [Spec US3--US4; GCB-1/GXB-1]
- [x] CHK055 Are invented mappings, self-approval, silver-before-gate, early dashboard/Power BI, raw PII exposure, fabricated live pass, and readiness scores all explicit failures? [SC-008; ECA-1; EXA-1]
- [x] CHK056 Must acceptance record exact candidate/host versions, isolated workspace facts, install source, fixture digest, actions, outcome, evidence, and timestamp? [Data Model §ExternalAcceptanceRun]
- [x] CHK057 Is missing acceptance evidence a blocker rather than an inferred pass? [FR-004; ECA-1/EXA-1]
- [x] CHK058 Are pre-release immutable-ref acceptance and post-publication public-source verification distinguished? [Quickstart §§5--6, 9]

## 7. Version and Publication Authorization

- [x] CHK059 Is one machine-readable candidate version source identified while clearly remaining only a proposal before owner approval? [FR-030; VSC-1 §Candidate source and approval]
- [x] CHK060 Are all governed version projections enumerated, including schema-supported catalog fields and tag/release prefix rules? [VSC-1 §Governed projections]
- [x] CHK061 Do missing, mismatched, already-tagged-at-other-SHA, or already-published version cases all block publication? [FR-031; VSC-1 §Rules]
- [x] CHK062 Is the authorized post-decision version projection separated from the owner decision and final rebuild? [Tasks T084--T086]
- [x] CHK063 Are build/validation jobs uncredentialed and separated from the protected publish job consuming immutable validated artifacts? [FR-034; PAB-1 §Protected PyPI workflow boundary]
- [x] CHK064 Is `id-token: write` restricted to the publish job and long-lived PyPI credentials prohibited? [FR-032--FR-034; SEC-004]
- [x] CHK065 Is the Trusted Publisher identity tuple constrained to the canonical repository, exact workflow, and protected environment? [FR-032; PAB-1]
- [x] CHK066 Must the protected environment require one named eligible reviewer with no self-approval inference? [FR-033; PAB-1]
- [x] CHK067 Is each approval bound to one action, candidate, version, SHA/digests, named human, and timestamp? [FR-035--FR-036; Data Model §PublicationApproval]
- [x] CHK068 Is it explicit that CI, merge approval, configuration, a previous release, or an agent statement cannot substitute for action-specific approval? [FR-036; PAB-1]
- [x] CHK069 Are tag, PyPI upload, GitHub Release, Claude catalog submission, and OpenAI public plugin submission separately authorized? [FR-035; PAB-1 §Actions and gates]

## 8. Public Verification and Rollback

- [x] CHK070 Must public-install verification use clean external environments and public sources rather than editable/development paths? [FR-037]
- [x] CHK071 Are exact version, source, commands/actions, outcome, evidence, and timestamp required for each surface's post-publication record? [FR-038]
- [x] CHK072 Are package yank, repository plugin-pointer correction, catalog/directory correction, and truthful documentation each defined as channel-specific containment? [FR-039; Research §Rollback]
- [x] CHK073 Is overwrite/move prohibited for immutable package files and release tags? [FR-040; PAB-1 §Rollback authority]
- [x] CHK074 Must a replacement use a new owner-approved version and repeat the full validation/approval/public-verification cycle? [FR-040--FR-041]
- [x] CHK075 Is rollback evidence explicitly prevented from granting replacement-release approval? [FR-041; Data Model §RollbackRecord]
- [x] CHK076 Does failure on one surface stop later actions without falsely withdrawing already healthy surfaces? [Spec US6; Quickstart §9]
- [x] CHK077 Is user workspace/project preservation required during plugin/package uninstall and rollback? [Spec US2; ECA-1; EXA-1]

## 9. Security, Privacy, and Evidence Quality

- [x] CHK078 Are real credentials, DSNs, hosts, tokens, PII, machine paths, and client data prohibited in every artifact, bundle, log, fixture, and evidence record? [SEC-001]
- [x] CHK079 Is synthetic-data minimization and fictionality explicit even for PII-shaped test cases? [SEC-002]
- [x] CHK080 Are least privilege, protected environments, and reviewed/immutable action references required for release automation? [SEC-004]
- [x] CHK081 Are local settings, caches, worktrees, test outputs, and approval drafts excluded from both public allowlists and artifacts? [SEC-005]
- [x] CHK082 Are evidence records sanitized without removing the version/SHA/digest facts required for traceability? [Data Model; RAC-1; PAB-1]
- [x] CHK083 Do pass/fail statements cite concrete evidence while unknowns remain named blockers? [FR-004; SC-012]

## 10. Measurability and Traceability

- [x] CHK084 Does each success criterion define an observable count, parity condition, time bound, or zero-tolerance failure condition? [SC-001--SC-012]
- [x] CHK085 Are “100%” criteria tied to finite governed inventories rather than an undefined universe? [SC-001; SC-006]
- [x] CHK086 Is the 15-minute first-success criterion bounded by declared prerequisites and excludes DB/Power BI/dev clone? [SC-004]
- [x] CHK087 Is deterministic equality defined by file lists and digests rather than timestamps or host-dependent archives? [SC-007; PKA-1]
- [x] CHK088 Can each acceptance assertion trace to one contract, one task, and one evidence-producing validation step? [SC-012; Tasks §Requirement Traceability]
- [x] CHK089 Are all 48 FRs, 5 SECs, and 12 SCs represented in the task traceability model? [Analysis §Mechanical Coverage]
- [x] CHK090 Are all owner-time unknowns named as execution checks rather than hidden ambiguities or assumed approvals? [Research §Open Checks Reserved for Execution; Analysis §Known Execution-Time Checks]

## Review Outcome

- [x] CHK091 Have all critical/high requirement-quality defects been resolved before implementation authorization? [Analysis §Findings and Resolutions]
- [x] CHK092 Are any unchecked items converted into concrete blockers with an owner and next corrective action rather than a score? [Spec FR-004; AGENTS.md]
- [x] CHK093 Has the reviewer confirmed that completing this checklist does not itself approve implementation, configuration, tagging, publication, or submission? [PAB-1]

## Notes

- Leave items unchecked until a reviewer evaluates the written requirement set.
- Record defects next to the relevant artifact/requirement; do not use a readiness percentage or confidence score.
- Platform-specific facts must be rechecked against current official documentation before implementation and again before public submission.


## Implementation Re-review — 2026-07-13

- [x] CHK094 Does the package use current official OpenAI public plugin submission/review/listing terminology and keep repository marketplace terminology scoped to the supported catalog? [FR-027--FR-029; GXB-1]
- [x] CHK095 Do action-scoped approval names match the executable evidence validator and publication-boundary contract? [FR-035--FR-036; Data Model §PublicationApproval; PAB-1]
- [x] CHK096 Does checklist completion remain repository evidence only, leaving configuration, version approval, tagging, publication, submission, rollback, and replacement release owner-gated? [PAB-1]

**Evaluation result**: CHK001--CHK096 satisfied. No unresolved requirement-quality defect remains. This result does not authorize any external or irreversible action.
