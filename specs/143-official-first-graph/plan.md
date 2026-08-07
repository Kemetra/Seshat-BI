# Implementation Plan: Public capability graph integrity

**Branch**: `143-official-first-graph` | **Date**: 2026-08-07 | **Spec**: [spec.md](spec.md)

**Input**: Phase 1 of the official-first integration rationalization program.

**Status**: ratified -- Ahmed Shaaban, 2026-08-07; implementation authorized

## Summary

Close the existing public-surface-to-capability gap by adding the two missing
router capabilities, correcting the one invalid canonical source, and extending
the independent capability oracle to reconcile the public surface with ownership
metadata and authored tracked files. Runtime behavior and generated bundles stay
unchanged.

## Technical Context

**Language/Version**: Python 3.11+; YAML and Markdown control-plane data

**Primary Dependencies**: Existing PyYAML and pytest dependencies; Git for the
tracked-file truth already required by repository contracts

**Storage**: Committed YAML and Markdown only

**Testing**: Focused pytest unit/contract tests, deterministic bundle check,
`seshat check`

**Target Platform**: Repository CI and local Windows/Linux development

**Project Type**: Python CLI/library with generated agent distributions

**Performance Goals**: One bounded reconciliation over 21 public skills and
approximately 104 capabilities; no runtime path is affected

**Constraints**: Fail closed, deterministic findings, no new registry, no bundle
regeneration, no dependency changes, no router or executor behavior changes

**Scale/Scope**: Two new capability records, one corrected source path, one
oracle extension, focused mutation and aggregate tests, control-plane docs

## Repository Truth and Phase Classification

**Classification**: REQUIRED.

| Evidence on `main` | Consequence |
| --- | --- |
| `distribution/public-command-surface.yaml` ships 21 skills | This is the public-skill feeder; no second list is needed. |
| Same-name public skills resolve through unique `surface: skill` records; differing portable wrappers use `references.public_skill` | Existing reference semantics already cover 19 skills without duplicate metadata. |
| `seshat-bi` and `powerbi-workflows` match neither relationship | Two public routers have no machine-checkable capability owner. |
| `pbi-mcp-doctor` names `.claude/skills/pbi-mcp-doctor/SKILL.md`, which does not exist | The ownership graph resolves to a false canonical source. |
| The authored doctor source is `distribution/bundle-templates/shared/skills/pbi-mcp-doctor/SKILL.md` | The fix is metadata-only. |
| Existing capability/public/bundle tests pass | The current architecture is fail-open at this cross-manifest boundary. |
| Bundle check passes before changes | No pre-existing generated drift blocks the phase. |

## Constitution Check

*GATE: passed before design; re-checked after design.*

| Principle | Bearing | Verdict |
| --- | --- | --- |
| I. Agent-First, Gate-Enforced | The public ownership relationship becomes an executable contract rather than prose. | Advances the principle. |
| II. Depend, Never Fork | Canonical source validation distinguishes authored inputs from generated projections and prepares later official delegation. | Advances the principle; no upstream behavior is copied. |
| V. Agent Stops at Judgment Calls | The two router classifications are proposed in a draft spec and require named-human ratification before landing. | Respected. |
| VII. C086 Is an Example | No table- or tenant-specific value is introduced. | Respected. |
| VIII. Static-First Governance | All validation is static and network-free. | Respected. |
| IX. Secrets and Reproducibility | Only repository-relative tracked paths are accepted; no credentials or machine paths enter metadata. | Respected. |

Post-design re-check: no violation was introduced. The design adds no execution,
approval, readiness, network, dependency, or generated distribution behavior.

## Design Decisions

### D1 -- Reuse the two existing authorities

The public skill set comes from `distribution/public-command-surface.yaml`; the
ownership records come from `docs/capabilities/capabilities.yaml`. An explicit
`references.public_skill` owner wins when present; otherwise a unique same-name
`surface: skill` record is the owner. The invariant is a reconciliation between
existing semantics, not a third registry or a redundant link on every entry.

### D2 -- Extend the independent oracle

`tests/unit/_capability_oracle.py` already reads feeder sources directly and is
wired into the aggregate real-manifest test. Add the public capability integrity
and canonical-source detector there and exercise it on constructed inputs before
wiring it into the aggregate. This preserves the anti-circularity property.

### D3 -- Classify current responsibility, not the roadmap's desired future

`seshat-bi` is a Seshat orchestrator: it selects readiness, knowledge, and
integration routes. `powerbi-workflows` is also currently a Seshat orchestrator:
it selects Seshat design, inspection, PBIR, and adoption helpers but does not yet
invoke Microsoft official skills. Calling it a Microsoft adapter in Phase 1
would fabricate an execution relationship. Phase 3 may reclassify it after the
official route actually exists.

### D4 -- Canonical means tracked authored file

Every declared capability source must be repository-relative, remain inside the
repository, be a regular file, and be tracked by Git. A public capability is
additionally required to declare one. Paths under generated Claude/Codex
integration bundles are explicitly invalid as canonical sources. The
bundle-template source remains valid because it is reviewed authored input.

### D5 -- Preserve all projections

No public wrapper, allowlist, command map, plugin manifest, or generated bundle
is edited. The deterministic bundle check must pass without regeneration.

## Project Structure

### Documentation for this feature

```text
specs/143-official-first-graph/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/public-capability-integrity.md
├── quickstart.md
├── tasks.md
├── analysis.md
├── plan-review.md
├── ratify-ledger.md
└── checklists/requirements.md
```

### Repository files in implementation scope

```text
docs/capabilities/
├── capabilities.yaml
└── README.md

tests/unit/
├── _capability_oracle.py
└── test_capability_inventory.py

distribution/public-command-surface.yaml  # read-only feeder
integrations/{claude-code,codex}/           # generated, validation only
```

**Structure Decision**: Extend the existing manifest and independent oracle.
No production module or new validator authority is needed.

## Implementation Sequence

1. Add failing mutation tests for missing, duplicate, stale, missing-source,
   untracked-source, escaping-source, and generated-source cases.
2. Implement the independent detector and wire it into `oracle_all_clear`.
3. Add current-responsibility capability records with explicit public ownership
   links for the two public routers.
4. Correct the doctor canonical source.
5. Document the cross-manifest invariant.
6. Run focused tests, public/bundle/plugin contracts, bundle drift, and
   `seshat check`; review the diff and close the active spec fence only after all
   tasks are complete.

## Risks

### R1 -- False ownership for `powerbi-workflows`

**Mitigation**: Record its current Seshat orchestration behavior. Do not claim an
official Microsoft execution link until Phase 3 implements and validates it.

### R2 -- Path validation becomes platform-dependent

**Mitigation**: Require manifest paths to be repository-relative POSIX-style
strings, resolve containment explicitly, and compare normalized Git-tracked
paths. Exercise Windows-relevant escaping and generated prefixes in tests.

### R3 -- Reference semantics become ambiguous

**Mitigation**: Load shipped skill names from the public surface on every run;
prefer explicit public ownership, otherwise accept only a unique same-name
`surface: skill` candidate. Internal CLI-to-skill references never become owners.

### R4 -- Metadata changes churn bundles

**Mitigation**: Do not touch bundle inputs. Run `export_agent_bundles.py --check`
before and after implementation and compare Git diff under generated roots.

## Complexity Tracking

No constitutional violation or additional subsystem is justified. A production
validator, new CLI rule, JSON schema, dependency, and general-purpose graph
engine were considered and rejected because the existing independent oracle and
contract gates cover the phase exit condition directly.

## Verification

Run after the focused red/green cycle:

```powershell
python -m pytest -p no:cacheprovider tests/unit/test_capability_inventory.py -q
python -m pytest -p no:cacheprovider tests/contract/test_public_command_surface.py tests/contract/test_capability_ship_classification.py tests/contract/test_generated_agent_bundles.py tests/contract/test_claude_plugin_bundle.py tests/contract/test_codex_plugin_bundle.py -q
python scripts/export_agent_bundles.py --check
python -m seshat.cli check
git diff --check
git status --short
```

## What this plan will not do

- Implement Phase 2 or later roadmap work.
- Change Power BI, dbt, Dagster, GitHub, Claude, or Codex routing.
- Regenerate bundles or treat generated output as canonical.
- Add, remove, merge, or rename public skills.
- Grant its own ratification or record an implementation status before landing.
