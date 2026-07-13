# Implementation Plan: Seshat BI Public Beta Distribution

**Branch**: `125-public-distribution-launch` | **Date**: 2026-07-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/125-public-distribution-launch/spec.md`

**Boundary**: This document governs repository implementation and describes later owner actions. Repository work may implement and validate the candidate, but it does not publish, tag, release, configure an external account, or record an owner approval.

## Summary

Prepare one coordinated Public Beta release candidate across the `seshat-bi` Python package, Claude Code, Codex, and the canonical repository. Keep the five existing Knowledge Bases canonical, introduce an explicit public-file allowlist plus a deterministic fail-closed exporter, and generate two separate self-contained agent bundles. Harden package metadata and artifact/install lifecycle checks, add a protected GitHub OIDC publication definition, synchronize one owner-approved version across all surfaces, and prove both agents return the same truthful next governed action in fresh external workspaces. Publication and public plugin submission remain separate named-owner gates.

The narrowest architecture is:

```text
skills/{five canonical knowledge skills} + canonical workflow sources
                         |
             distribution/public-knowledge-allowlist.yaml
                         |
               scripts/export_agent_bundles.py
                    /                     \
integrations/claude-code/seshat-bi/   integrations/codex/seshat-bi/
  Claude-native manifest/skills       Codex-native manifest/skills
```

Generated copies are disposable projections. They are never edited or used as a second source of truth.

## Technical Context

**Language/Version**: Python `>=3.13`, YAML, JSON, Markdown, GitHub Actions YAML
**Primary Dependencies**: existing Hatchling build backend; PyYAML runtime; `build`, `twine`, `pipx`, and `pytest` as release/test tooling; no new runtime service
**Storage**: version-controlled files and immutable release artifacts; no database
**Testing**: pytest unit/contract/integration tests, deterministic tree/digest comparisons, `twine check --strict`, artifact inspection, isolated sdist rebuild, pipx lifecycle smoke, Claude Code external acceptance, Codex CLI/IDE external acceptance
**Target Platform**: blocking Windows release smoke; supported Python environments; Claude Code public GitHub plugin flow; current Codex CLI, IDE, and repository/plugin surfaces
**Project Type**: Python CLI/package plus generated agent integration bundles and release automation
**Performance Goals**: two exports from identical source produce identical file lists/digests; fresh Python first-success journey completes within 15 minutes
**Constraints**: repository implementation only; no self-approval; no development-repository dependency for public users; no secrets/PII/local paths; no recursive allowlist globs; no readiness score; publication credentials confined to a protected publish job
**Scale/Scope**: one Python wheel, one sdist, two generated agent bundles, five canonical Knowledge Bases, eight normative contracts, three external distribution surfaces, and five authorization lanes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Constitutional gate | Pre-research result | Post-design result | Evidence in this package |
|---|---|---|---|
| Agent-first workflow | PASS | PASS | Claude/Codex acceptance requires the agent to inspect state and return one governed action; the CLI remains a helper. |
| No silver before Mapping Ready is cleared | PASS | PASS | Both external-agent contracts include an ambiguous-grain scenario that must stop before silver SQL. |
| No Power BI before validated gold / no dashboard before metric contracts | PASS | PASS | The synthetic journey ends at the earliest human/live gate and performs no Power BI execution. |
| Named-human approvals only | PASS | PASS | Publication authorization contract binds every irreversible action to one named owner and exact candidate. |
| Evidence, status, blockers; no fabricated score | PASS | PASS | Acceptance requires evidence-backed `next_action`/`stop_blocked` and prohibits readiness scores. |
| Secrets and live boundaries | PASS | PASS | Allowlist, artifact, and acceptance contracts reject credentials, real PII, DSNs, hosts, and client data. |
| C086 is an example, not a schema | PASS | PASS | External acceptance uses fictional generic retail fixtures and forbids inventing semantic mappings. |
| Existing merged features remain baseline | PASS | PASS | `KPI-MC-15` is verified as already present; the plan adds audit/regression evidence, not a duplicate. |

No constitutional exception or complexity waiver is required.

## Phase 0: Research Decisions

Research is recorded in [research.md](research.md). The blocking decisions are:

1. Treat `main` at `785299e` as the completed baseline. `KPI-MC-15` exists and is not re-added; explicit regression coverage is planned.
2. Reconcile the existing annotated `v0.1.0` tag with changelog and publication-history claims before choosing a Public Beta version. `0.2.0` is a proposal, never an agent decision.
3. Use one explicit allowlist and one deterministic exporter, with platform-specific bundle templates and a shared public operating contract.
4. Keep Claude's root `.claude-plugin/marketplace.json`; remove the competing nested marketplace source and make the plugin cache-safe/self-contained.
5. Add a Codex-native plugin under `integrations/codex/seshat-bi/` and a repo catalog at `.agents/plugins/marketplace.json`. Retain `.agents/skills/` for repository-scoped skills and `AGENTS.md` for repository guidance.
6. Use the current OpenAI terminology: **public plugin submission/review/listing**. A repository catalog/marketplace and OpenAI's public process are separate surfaces.
7. Build and validate without credentials; publish only validated immutable artifacts through a protected `pypi` environment using GitHub OIDC.

## Phase 1: Design

### Data and state design

[data-model.md](data-model.md) defines `ReleaseCandidate`, `ReleaseVersion`, allowlist and bundle entries, artifacts, acceptance runs, approvals, and rollback records. Release-candidate eligibility is a state transition based on evidence and blockers; it is not a numeric readiness calculation.

### Contract design

The contracts are normative inputs to tests, implementation, and review:

- [Public Knowledge Allowlist](contracts/public-knowledge-allowlist.md)
- [Generated Claude Bundle](contracts/generated-claude-bundle.md)
- [Generated Codex Bundle](contracts/generated-codex-bundle.md)
- [Release Artifact Contents](contracts/release-artifact-contents.md)
- [Version Synchronization](contracts/version-synchronization.md)
- [External Claude Acceptance](contracts/external-claude-acceptance.md)
- [External Codex Acceptance](contracts/external-codex-acceptance.md)
- [Publication Authorization Boundary](contracts/publication-authorization-boundary.md)

### Verification design

[quickstart.md](quickstart.md) defines the future no-publication release-candidate validation sequence. The sequence builds artifacts once, checks metadata/content and sdist reproducibility, exercises pipx install/upgrade/uninstall on Windows, checks generated-bundle drift, and runs both agent acceptances from external temporary workspaces. Credential-bearing and irreversible steps are explicitly excluded.

## Project Structure

### Documentation (this feature)

```text
specs/125-public-distribution-launch/
├── spec.md
├── research.md
├── plan.md
├── data-model.md
├── tasks.md
├── quickstart.md
├── analysis.md
├── checklists/
│   ├── requirements.md
│   └── release-requirements.md
└── contracts/
    ├── public-knowledge-allowlist.md
    ├── generated-claude-bundle.md
    ├── generated-codex-bundle.md
    ├── release-artifact-contents.md
    ├── version-synchronization.md
    ├── external-claude-acceptance.md
    ├── external-codex-acceptance.md
    └── publication-authorization-boundary.md
```

### Planned repository implementation

```text
.agents/
├── plugins/marketplace.json                # Codex repository catalog
└── skills/                                 # repository-scoped Codex skills (existing)
.claude-plugin/marketplace.json              # sole root Claude marketplace
.github/workflows/
├── ci.yml
└── release.yml                              # build/validate then protected OIDC publish
distribution/
├── public-knowledge-allowlist.yaml          # explicit source/destination policy
├── bundle-templates/
│   ├── shared/
│   ├── claude/
│   └── codex/
└── synthetic-retail/                        # fictional external-acceptance fixture
integrations/
├── claude-code/seshat-bi/
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   ├── commands/
│   ├── knowledge/
│   └── bundle-manifest.json
└── codex/seshat-bi/
    ├── .codex-plugin/plugin.json
    ├── skills/
    ├── knowledge/
    └── bundle-manifest.json
scripts/
├── export_agent_bundles.py
├── check_release_versions.py
├── inspect_release_artifacts.py
├── install_smoke_test.py
└── external_agent_acceptance.py
tests/
├── contract/
│   ├── test_public_knowledge_allowlist.py
│   ├── test_generated_agent_bundles.py
│   ├── test_release_artifact_contents.py
│   └── test_release_version_sync.py
├── integration/
│   ├── test_python_release_lifecycle.py
│   └── test_external_agent_acceptance.py
└── unit/test_rule_kr1.py                    # explicit KPI-MC-15 regression
docs/
├── install/{user-install.md,agent-install.md}
├── operations/{release-acceptance-checklist.md,release-rollback.md,versioning-policy.md}
└── releases/                                # owner-approved release note only
```

**Structure Decision**: Preserve the existing single Python project and `integrations/claude-code` layout. Add distribution policy/templates centrally and a sibling Codex integration. Generated bundles are committed for public Git-backed installation but verified against the canonical exporter in CI. The Codex catalog stays in the official repo-scoped `.agents/plugins/marketplace.json` location; the plugin source may remain under `integrations/codex/` because the catalog path is explicitly relative to repository root.

## Delivery and Authorization Sequence

1. **Repository implementation**: fix baseline release claims; add metadata, exporter, bundles, tests, docs, and inert workflow definitions; review and merge normally.
2. **PyPI/GitHub configuration**: a named owner confirms package ownership/availability, creates the protected `pypi` environment and reviewer rule, registers Trusted Publishing identity, and confirms tag protection.
3. **Claude publication**: repository marketplace installation becomes usable when merged; a named owner separately decides whether to submit to Anthropic's public catalog.
4. **Codex publication**: repository catalog/plugin installation becomes usable when merged; an eligible verified publisher separately prepares and submits through OpenAI's public plugin process.
5. **Irreversible release**: a named owner approves the exact version and immutable candidate, creates the tag, authorizes upload/GitHub Release, then records external verification. Each public-catalog submission has its own approval.

These lanes may not be collapsed into one inferred approval. A partial launch must be described truthfully by surface.

## Complexity Tracking

No constitution violations require justification.
