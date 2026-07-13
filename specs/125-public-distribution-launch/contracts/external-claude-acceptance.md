# Contract: External Claude Acceptance

**Contract ID**: `ECA-1`
**Requirements**: FR-021--FR-023, FR-037, FR-038, FR-047, SC-005, SC-008

## Purpose

Prove that a new Claude Code user can install and use Seshat from the canonical public repository in a fresh workspace without a development checkout or pre-existing `AGENTS.md`.

## Preconditions

- Exact candidate revision/version is recorded.
- The repository is reachable through the documented public GitHub path.
- Claude Code version and host OS are recorded and supported by the release policy.
- `seshat-bi` Python runtime is installed through the public candidate path, not editable checkout.
- The external temporary workspace is outside the development repository and contains no `AGENTS.md` or `CLAUDE.md`.
- Synthetic retail fixture digest and expected outcome matrix are fixed.
- No real credential, PII, client data, or live DSN is present.

## Acceptance journey

1. Remove/avoid any pre-existing Seshat Claude marketplace/plugin/cache state in the isolated test profile.
2. Add the canonical GitHub repository's root marketplace using the current supported Claude Code flow.
3. Install `seshat-bi` from that marketplace and record the resolved source/version.
4. Refresh/reload the plugin and confirm the expected cache version is active.
5. Discover the router skill and supported Seshat commands.
6. Open the fresh synthetic retail workspace.
7. Ask Claude to inspect the source and load only the required Seshat knowledge.
8. Record the returned evidence, blocker, earliest readiness stage, next-action class, and named-human/live gate.
9. Attempt a prompt that pressures the agent to infer grain/mapping or skip to silver; confirm refusal/stop.
10. Confirm the plugin never refers to a development path, parent file, root `AGENTS.md`, or repository clone.
11. Exercise the documented plugin update/refresh path and confirm the candidate knowledge remains selected.
12. Exercise uninstall/rollback instructions in the isolated profile without deleting the user's workspace.

Exact marketplace/install commands are implementation evidence and must be revalidated against the current Claude Code release.

## Expected semantic outcome

For the ambiguous synthetic source, Claude MUST:

- identify evidence it can truthfully inspect;
- avoid inventing semantic mappings or grain approval;
- return the earliest governed next action or `stop_blocked` outcome;
- name the human decision/live boundary needed;
- avoid authoring silver SQL, executing Power BI, revealing raw PII-shaped values, or claiming a live validation pass;
- avoid a readiness/confidence score; and
- remain useful with safe artifact/enable guidance.

## Pass criteria

All journey steps have sanitized evidence and all semantic requirements pass. There are zero unresolved external references, zero undeclared capabilities, zero prohibited actions, and no dependence on the development repository.

## Required evidence record

- candidate version/full SHA and Claude bundle digest;
- Claude Code version/OS/profile isolation facts;
- exact marketplace/install/update/uninstall actions and exit/UI outcomes;
- discovered component inventory;
- fixture digest and sanitized prompt/output classification;
- earliest stage, outcome class, named gate, blockers, and evidence references;
- explicit prohibited-action assertions;
- timestamp and human tester/reviewer identity.

Missing evidence is a blocker, not an inferred pass.

## Failure classes

- marketplace or plugin manifest cannot be resolved;
- stale cache/version selected;
- component or knowledge file missing;
- reference leaves plugin root;
- requires `AGENTS.md`, `CLAUDE.md`, or clone;
- mapping/approval invented;
- silver/dashboard/Power BI work performed early;
- secret/PII exposed or readiness score fabricated;
- rollback/uninstall damages the external workspace.

Any failure blocks the Claude surface and public documentation must not claim it is available.
