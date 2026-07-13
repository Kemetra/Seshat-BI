# Contract: External Codex Acceptance

**Contract ID**: `EXA-1`
**Requirements**: FR-024--FR-029, FR-037, FR-038, FR-047, SC-005, SC-008

## Purpose

Prove that new Codex CLI and IDE users can install the Codex-native Seshat distribution, invoke `$seshat-bi`, load canonical public knowledge, and stop at the same governed gate as Claude without a development checkout.

## Preconditions

- Exact candidate revision/version and Codex bundle digest are recorded.
- Current official Codex docs/schema are rechecked and supported CLI/IDE versions recorded.
- `seshat-bi` Python runtime is installed through the public candidate path, not editable checkout.
- Isolated Codex homes/profiles contain no prior Seshat plugin or skills.
- The external workspace is outside Seshat_BI and has no `AGENTS.md`.
- The same synthetic fixture/outcome matrix used by Claude is present.
- No real credential, PII, client data, or live DSN is present.

## CLI journey

1. Add/resolve the canonical repository Codex catalog using the current supported `codex plugin marketplace` flow.
2. Install `seshat-bi` and record resolved source/version.
3. Start a clean CLI session and verify skill discovery.
4. Use `/skills` or equivalent discovery and explicitly invoke `$seshat-bi`.
5. Explicitly invoke at least one exported Knowledge Base skill.
6. Inspect the synthetic retail source and record the governed outcome.
7. Pressure the agent to invent mappings or skip to silver; confirm a guarded stop.
8. Update/refresh/restart as required and confirm the candidate version remains active.
9. Uninstall/rollback in the isolated profile and confirm the user workspace remains.

## IDE journey

1. Open the same fresh workspace in a supported Codex IDE extension session with the isolated profile.
2. Verify `seshat-bi` and exported Knowledge Base skills are discoverable.
3. Invoke `$seshat-bi` explicitly.
4. Run the same synthetic scenario and outcome classification.
5. Confirm no development repository, parent path, or Seshat-specific workspace `AGENTS.md` is needed.

Exact commands/UI actions are implementation evidence and must be revalidated against current product versions.

## Expected semantic parity

CLI and IDE MUST agree with each other and the Claude contract on:

- earliest governed stage;
- `next_action` versus `stop_blocked` class;
- concrete blocker/evidence class;
- named-human or live boundary;
- refusal to invent mapping/approval;
- refusal to create silver SQL, skip readiness gates, execute Power BI, expose PII, claim a live pass, or emit a readiness score.

Natural-language phrasing need not be identical.

## Repository guidance check

As a separate compatibility test inside a clean Seshat_BI checkout, Codex MUST discover root `AGENTS.md` according to current precedence and use repository-scoped `.agents/skills`. This does not replace the fresh external test and is not counted as plugin portability evidence.

## Pass criteria

- Current Codex validator accepts catalog, manifest, and skills.
- CLI and IDE both discover and explicitly invoke the plugin skill.
- Every bundle reference resolves internally.
- All semantic parity and prohibited-action assertions pass.
- No undeclared app, MCP server, connector, hook, or network capability becomes active.
- Update/uninstall behavior is documented and workspace-safe.

## Required evidence record

- candidate version/full SHA and bundle digest;
- Codex CLI/IDE/host versions and OS;
- isolated profile/workspace facts;
- exact catalog/install/update/uninstall actions and outcomes;
- skill inventory plus `$` invocation evidence;
- fixture digest and sanitized output classification;
- parity matrix against Claude;
- explicit prohibited-capability/action assertions;
- timestamp and human tester/reviewer identity.

Missing evidence blocks the affected Codex surface.

## Public plugin-submission boundary

Passing this contract makes the repository-distributed plugin a candidate for owner review. It does not submit, list, or authorize the plugin through OpenAI's public plugin process.
