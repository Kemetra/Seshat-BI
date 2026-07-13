# Cross-Artifact Analysis: Seshat BI Public Beta Distribution

**Feature**: `125-public-distribution-launch`
**Date**: 2026-07-13
**Scope**: Read-only consistency and quality analysis across `spec.md`, `plan.md`, `research.md`, `data-model.md`, `tasks.md`, `quickstart.md`, `contracts/`, and `checklists/requirements.md`. This file captures the analysis result requested by the owner; no implementation or external action was performed.

## 1. Owner-Directed Scope Coverage

| Owner direction | Realization | Status |
|---|---|---|
| One coordinated Python/Claude/Codex/Public GitHub Beta | US1--US6; FR-001--FR-041; plan delivery sequence | COVERED |
| Treat current `main` as completed baseline | FR-001; research Baseline Findings; T016--T023 | COVERED |
| Verify reported `KPI-MC-15` omission | FR-003; SC-002; research baseline evidence; T016/T022 | COVERED -- present, no duplicate repair planned |
| Harden metadata, wheel/sdist, Twine, pipx lifecycle, Windows smoke | FR-006--FR-012; RAC-1; T024--T034 | COVERED |
| Protected PyPI Trusted Publishing with named-owner approval | FR-032--FR-034; PAB-1; T064/T067/T073--T076 | COVERED |
| Finalize root Claude marketplace/plugin | FR-019--FR-023; GCB-1/ECA-1; T044--T053 | COVERED |
| Add first-class Codex integration | FR-024--FR-029; GXB-1/EXA-1; T054--T063 | COVERED |
| Deliver Knowledge Bases without development clone | FR-013--FR-022/FR-024--FR-028; both bundle/acceptance contracts | COVERED |
| Keep existing Knowledge Bases canonical; deterministic allowlist exporter | FR-013--FR-018; PKA-1; T006--T012/T035--T043 | COVERED |
| Synchronize every release version surface | FR-030--FR-031; VSC-1; T008/T013/T084--T086 | COVERED |
| Define verification and rollback for all surfaces | FR-037--FR-041; RAC-1/ECA-1/EXA-1/PAB-1; T063--T072/T090--T091 | COVERED |
| Separate five authorization lanes | spec Scope; plan sequence; PAB-1; Tasks Phases 8--12 | COVERED |
| Stop after validated specification package | spec Out of Scope; plan boundary; tasks future-work boundary | COVERED |

## 2. Mechanical Coverage

- Functional requirements: 48 unique contiguous IDs (`FR-001`--`FR-048`).
- Security requirements: 5 unique contiguous IDs (`SEC-001`--`SEC-005`).
- Success criteria: 12 unique contiguous IDs (`SC-001`--`SC-012`).
- User stories: 6; each has priority, rationale, independent test, and acceptance scenarios.
- Planning contracts: 8 of 8 requested, each with a unique contract ID.
- Tasks: 95 sequential unique IDs (`T001`--`T095`), all conforming to the Spec Kit checkbox/ID/parallel/story format.
- User-story task references: US1 8, US2 11, US3 13, US4 14, US5 9, US6 21.
- Requirement-to-task coverage: 100% by the `tasks.md` traceability matrix and linked story checkpoints.
- Required local Markdown links: all resolve.
- Unresolved specification placeholders: zero. The only marker scan hit is the quality-checklist sentence asserting that no such marker remains.

## 3. Contract and Architecture Consistency

| Concern | Result |
|---|---|
| Canonical source | Exactly five existing Knowledge Base entrypoints remain canonical under `skills/`; generated copies are projections. |
| Inclusion control | PKA-1 requires literal tracked files, no recursive globs, path traversal, symlinks, or implicit inclusion. |
| Determinism | PKA-1 plus both bundle contracts require stable paths, transformations, ordering, and SHA-256 provenance. |
| Claude format | Root `.claude-plugin/marketplace.json`; plugin `.claude-plugin/plugin.json`; root `skills/` and `commands/`; cache-safe internal references. |
| Codex format | Repo `.agents/plugins/marketplace.json`; plugin `.codex-plugin/plugin.json`; `skills/<name>/SKILL.md`; `$` invocation; no Claude-field assumption. |
| Repository guidance | `AGENTS.md` and `.agents/skills/` remain repository-scoped and are not used as portable plugin payloads. |
| Public terminology | OpenAI public review is consistently called the **Plugins Directory**; marketplace terminology is limited to the repo/personal catalog file and `codex plugin marketplace` command. |
| Agent parity | ECA-1 and EXA-1 use one fictional source/outcome matrix and compare stage/action/gate classes, not exact prose. |
| Release identity | VSC-1 projects one approved SemVer across package, both plugins/catalogs where supported, bundle manifests, changelog/note, tag, and GitHub Release. |
| Credentials | PAB-1 gives OIDC only to the protected publish job after artifact validation and named-environment approval. |
| Approval | Data model and PAB-1 bind each approval to one named human, action, candidate, version, SHA/digests, and timestamp. |
| Rollback | Immutable package/tag identity is preserved; containment is surface-specific and replacement requires a new version and full gates. |

## 4. Baseline Evidence Consistency

- `skills/retail-kpi-knowledge/registry.yaml` contains one `KPI-MC-15` entry with slug `average-basket-size-units` and the matching knowledge-contract reference.
- `skills/retail-kpi-knowledge/references/id-conventions.md` projects `KPI-MC-15`.
- The plan therefore adds explicit regression/audit coverage and does not recreate the entry.
- `pyproject.toml` contains version `0.1.0`.
- An annotated repository tag `v0.1.0` exists and is titled “Seshat BI v0.1.0 -- first tagged release.”
- `CHANGELOG.md` states there is no prior tag. The specification correctly treats this as a blocker to reconcile rather than silently choosing or moving a version.
- `0.2.0` appears only as a likely proposal based on additive history; T084 reserves ratification to a named owner.

## 5. Constitution Check

- Agent-first interface preserved; release scripts/CLI remain helpers.
- Both agent acceptances stop before silver when grain/mapping approval is absent.
- No dashboard/Power BI execution is introduced.
- Named-human approvals remain explicit; no task or workflow self-grants them.
- Readiness and release verdicts use status, evidence, blockers, and one next action; no confidence/readiness score is introduced.
- Live-database absence produces deferred guidance rather than a fabricated pass.
- Synthetic fixtures are generic and fictional; C086 is not reused as a schema.
- Secrets, DSNs, hosts, client material, and raw PII are prohibited from artifacts/evidence.

Result: PASS before and after design; no constitutional exception is requested.

## 6. Findings and Resolutions

The first detection pass found two planning-package defects. They were corrected before the final pass.

| ID | Category | Severity | Finding | Resolution |
|---|---|---|---|---|
| A1 | Coverage/actionability | MEDIUM | Owner version approval flowed directly to rebuild without a standalone reversible task to project the approved value into all governed locations and create the release note. | FIXED -- T085 now performs the authorized repository projection after T084 and before T086 rebuild. |
| A2 | Traceability typo | LOW | Contract task range used `T006–T15`, which was not a canonical three-digit task reference. | FIXED -- corrected to `T006–T015`; downstream shifted ranges were rechecked after T085 insertion. |

Final pass: 0 CRITICAL, 0 unresolved HIGH, 0 unresolved MEDIUM.

## 7. Known Execution-Time Checks (Not Specification Defects)

1. PyPI `seshat-bi` ownership/availability and actual index publication history require the named owner's authenticated recheck before configuration (T073).
2. GitHub environment-reviewer eligibility depends on current repository plan/ownership and is an external configuration check (T074).
3. Claude Code and Codex schemas, CLI/IDE behavior, and directory submission requirements are time-sensitive; research uses current official documentation and tasks require a release-time recheck.
4. `retail check` could not be run in this shell because neither `python` nor a Python launcher installation is available. The failure was explicit (“No installed Python found”) and is not represented as a pass. Static artifact checks below still completed.

## 8. Validation Results

- Template-marker scan: clean except the self-referential quality-checklist assertion.
- Requirement/task/contract ID uniqueness and sequencing: clean.
- Task format scan: clean.
- Local Markdown link validation: clean.
- `git diff --check`: clean (Git only reports its normal future LF-to-CRLF warning for `.specify/feature.json`).
- Working-tree boundary: only `.specify/feature.json` and `specs/125-public-distribution-launch/` are changed.
- No implementation file, account, tag, release, publication, commit, push, or pull request was created or changed.

## 9. Verdict

The Spec Kit package is internally consistent, fully covers the owner's distribution and authorization boundary, distinguishes Claude and Codex formats/terminology, has complete requirement-to-contract-to-task traceability, and has no unresolved critical/high/medium artifact issue. It is ready for owner review as a **Draft specification and plan**, not ratified and not authorized for implementation or publication by this analysis.

## Stop

This workflow stops after the validated specification package. Do not run `/speckit-implement`, create a tag/release, configure external publishing, submit a plugin, or infer approval from this verdict.
