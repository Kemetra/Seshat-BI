# Cross-Artifact Analysis: Seshat BI Public Beta Distribution

**Feature**: `125-public-distribution-launch`
**Date**: 2026-07-13
**Scope**: Final non-publishing consistency analysis across the implemented specification, plan, research, data model, contracts, tasks, generated distributions, release controls, acceptance evidence, and requirements checklists.

## Verdict

PASS for repository implementation and pull-request review.

No unresolved CRITICAL, HIGH, or MEDIUM cross-artifact defect remains. This verdict does not approve a version, external configuration, tag, upload, release, catalog entry, OpenAI submission, rollback, or replacement release.

The coordinated public release remains truthfully blocked until the owner-controlled tasks T073--T091 are completed with action-specific evidence. In particular, the existing immutable `v0.1.0` tag points to a different revision than the candidate while the package still declares `0.1.0`; the tag must not be moved or overwritten.

## Mechanical coverage

- 48 contiguous functional requirements: `FR-001`--`FR-048`.
- 5 contiguous security requirements: `SEC-001`--`SEC-005`.
- 12 contiguous success criteria: `SC-001`--`SC-012`.
- 6 independently testable user stories.
- 8 required contracts: PKA-1, GCB-1, GXB-1, RAC-1, VSC-1, ECA-1, EXA-1, and PAB-1.
- 95 unique sequential tasks.
- 76 repository-authorized tasks complete after T094; 19 external/owner-sequenced tasks remain open.
- Requirement-to-contract-to-task coverage: 100%.
- Release-requirements checklist: CHK001--CHK096 evaluated and satisfied.
- Unresolved template or clarification markers: zero.

## Requirement-to-evidence traceability

| Requirement set | Normative contracts | Evidence-producing tasks and checks | Result |
|---|---|---|---|
| FR-001--FR-005 baseline/audit | RAC-1, VSC-1 | T016--T023; candidate audit; KPI registry regression | Implemented; `KPI-MC-15` exists exactly once; version/tag conflict blocks release |
| FR-006--FR-012 Python artifacts | RAC-1 | T024--T034, T092; build, Twine strict, artifact inspector, isolated rebuild, Windows pipx lifecycle | Implemented and passing |
| FR-013--FR-018 canonical export | PKA-1, GCB-1, GXB-1 | T006--T012, T035--T043, T092; fail-closed allowlist and deterministic drift tests | Implemented and passing |
| FR-019--FR-023 Claude Code | GCB-1, ECA-1, PAB-1 | T044--T053, T065, T069, T077--T079, T092; strict manifest validator and credential-free acceptance | Repository implementation passing; public catalog actions remain owner-only |
| FR-024--FR-029 Codex | GXB-1, EXA-1, PAB-1 | T054--T063, T066, T070, T080--T083, T092; official plugin validator and CLI/IDE fixture acceptance | Repository implementation passing; OpenAI submission remains owner-only |
| FR-030--FR-036 version/publication | VSC-1, PAB-1 | T008, T013, T064, T067, T073--T076, T084--T089, T092; workflow and authorization tests | Controls implemented; external configuration/version/publication intentionally blocked |
| FR-037--FR-041 verification/rollback | RAC-1, ECA-1, EXA-1, PAB-1 | T026, T045, T055, T063--T072, T090--T092; rollback/approval rejection tests | Procedures implemented; real public evidence and any rollback remain owner-only |
| FR-042--FR-048 required contracts | all eight contracts | T006--T015 plus contract-linked story tests and T094--T095 | Complete |
| SEC-001--SEC-005 | PKA-1, GCB-1, GXB-1, RAC-1, PAB-1 | T002--T004, T006--T012, T024, T035--T043, T064--T076, T092 | Implemented; no undeclared service, credential, PII, client, cache, or local-path payload |
| SC-001--SC-012 | all eight contracts | linked story checkpoints plus T092--T095 | Repository-observable criteria pass; owner/public criteria remain explicitly gated |

## Architecture consistency

| Concern | Result |
|---|---|
| Canonical knowledge | The five existing Knowledge Base skill trees remain editable sources; generated bundles are projections only. |
| Inclusion control | The allowlist enumerates literal files and the exporter rejects recursive inclusion, unsafe paths/types, secrets, symlinks, unreviewed files, and transitive-reference escape. |
| Determinism | Both platform trees and manifests derive from the same reviewed inputs with stable ordering and SHA-256 provenance. |
| Claude structure | One root marketplace, a native Claude manifest, bundled skills/commands/knowledge, and no workspace `AGENTS.md` or development-clone dependency. |
| Codex structure | A native `.codex-plugin/plugin.json`, repository `.agents/plugins/marketplace.json`, supported skill layout, explicit `$` invocation, and no Claude-manifest assumptions. |
| Terminology | Repository Codex catalog/CLI surfaces may use marketplace terminology; OpenAI's external surface is called public plugin submission/review/listing. |
| Agent behavior | Python, Claude, and Codex use one fictional ambiguity/PII fixture and agree on stage, blocker, named gate, and allowed next-action class without exact-prose coupling. |
| Publication control | Build/test jobs are uncredentialed; only a protected, named-reviewer publish job may request OIDC and consume same-run verified artifacts. |
| Rollback | Containment is surface-specific; immutable artifacts/tags are preserved and replacement requires a new owner-approved version and full gates. |

## Findings and resolutions

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| A1 | HIGH | The planning package still described OpenAI's current external plugin process as “Plugins Directory.” | Fixed across spec, plan, research, contracts, tasks, checklists, and public docs; repository marketplace terminology remains correctly scoped. |
| A2 | MEDIUM | Approval action names drifted between the data model, tasks, publication contract, and executable validator. | Fixed around `create_release_tag`, `publish_pypi`, `submit_claude_catalog`, and `submit_openai_plugin`; obsolete Codex-directory actions were removed. |
| A3 | MEDIUM | The spec/plan still said implementation was out of scope after the owner later authorized reversible repository implementation. | Fixed: repository work is authorized, while external configuration and irreversible actions remain prohibited without fresh named-owner decisions. |
| A4 | MEDIUM | The original analysis described only the pre-implementation planning state and obsolete environment limits. | Replaced by this implementation-era analysis with executed evidence and current blockers. |
| A5 | LOW | Ruff reported five overlong lines plus unused imports/variables in new files. | Fixed and revalidated across all 399 repository Python files. |
| A6 | ENVIRONMENT | A full local test run initially lacked the declared optional `mcp` extra, causing three MCP contract import failures. | Installed the existing optional test dependency in the isolated local environment; the unchanged suite then passed completely. |
| A7 | HIGH | The PyPI publish action pointed at a staging directory that also contained evidence JSON, checksums, and source metadata. | Isolated the wheel and sdist under `release-staging/dist/`, asserted an exact count of two distributions, and pointed the trusted-publishing action only at that directory. |
| A8 | HIGH | Publication approvals were action-scoped but did not bind the exact source SHA and artifact digests. | Made full `source_revision` and exact `artifact_digests` mandatory in approval validation and added changed-revision/digest rejection tests. |
| A9 | MEDIUM | Rollback actions were allowed globally instead of being enforced against the affected public surface. | Added a surface-to-action map for all five public surfaces and cross-surface rejection coverage. |
| A10 | MEDIUM | The optional real Claude CLI acceptance path passed the development repository's plugin directory directly to Claude. | Removed the development path; the isolated Claude config must now contain an independently installed plugin, with command-construction regression coverage. |
| A11 | MEDIUM | The knowledge allowlist could redefine canonical roots and did not reject a symlinked parent component. | Hard-coded the canonical source roots and reject symlinks in every source-path component, with negative contract tests. |
| A12 | LOW | CI linted `src` and `tests` but omitted release/export/acceptance scripts. | Expanded both Ruff gates to `src tests scripts`, fixed the exposed import/format drift, and revalidated the full set. |
| A13 | HIGH | The release workflow interpolated the workflow-dispatch candidate ref directly into Bash commands. | Pass all ref/repository/protection contexts through quoted step environment variables and added a contract test prohibiting direct input interpolation in shell bodies. |

Final finding count: 0 unresolved CRITICAL, HIGH, or MEDIUM issues.

## Executed repository evidence

- Full pytest suite: 2,235 passed, 9 skipped on Windows/Python 3.13.
- Ruff format and lint: pass across 399 repository Python files, including all release scripts.
- `seshat check`, `seshat semantic-check --repo .`, and `seshat kit-lint`: pass.
- Deterministic Claude/Codex exporter drift check: pass.
- Claude Code strict marketplace and plugin validation: pass.
- Codex plugin validation: pass.
- Credential-free Claude/Codex bundle acceptance and semantic parity: pass.
- Exactly one wheel and one sdist: built; Twine strict, content inspection, and isolated sdist rebuild pass.
- Windows isolated pipx install, first success, upgrade, uninstall, command removal, dependency exclusion, and project preservation: pass.
- Primary install/rollback local-link scan: pass; development-only command scan of public journeys: clean.
- Credential-free candidate audit: repository checks pass; coordinated release status remains blocked for the exact version/tag and owner/public-evidence reasons above.

## Constitution and authorization check

- Agent-first interface and the seven-stage readiness order remain unchanged.
- Ambiguous grain/PII cases stop before silver and name the human decision.
- No dashboard or Power BI execution path is introduced.
- No readiness/confidence score is created.
- No test, workflow, merge, agent statement, or checklist grants an approval.
- No external account, repository protection, tag, upload, release, catalog submission, OpenAI submission, or rollback was performed.

Result: PASS with no constitutional exception.

## Remaining owner-controlled dependency chain

```text
repository PR + CI + merge
        |
        +--> T073--T076  external PyPI/GitHub configuration
        +--> T077--T079  Claude public-catalog decision/submission
        +--> T080--T083  OpenAI public-plugin eligibility/submission
        |
        +--> T084 version decision
                 -> T085 authorized version projection
                 -> T086 final immutable candidate evidence
                 -> T087 action-approved tag
                 -> T088/T089 separately approved PyPI/GitHub publication
                 -> T090 public-source verification
                 -> T091 surface-specific containment only if needed
```

These branches do not authorize one another. T085 is reversible repository work but cannot begin until the owner records T084 for the exact version and source.

## Final analysis conclusion

The repository implementation is internally consistent, contract-complete, test-backed, and ready for independent pull-request review. The Public Beta itself is not approved or released. The remaining open tasks are intentionally external or owner-sequenced and must retain their named-human gates.
