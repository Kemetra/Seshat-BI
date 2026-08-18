---
name: pbi-mcp-write-adapter
description: >-
  APPLY an already-approved Power BI semantic-model change through Microsoft's official
  Power BI Modeling MCP, behind Seshat's recorded named-human approval -- closing the
  governed last mile so the change is not applied by hand in Desktop with nothing
  recorded. Use when someone asks to apply, push, or publish an approved model edit, to
  run `seshat pbi-mcp apply` / `plan-write`, or asks why a write was refused. This adapter
  EXECUTES a decision Core Authority already made: it reads COMMITTED approvals as the GO
  signal, refuses on any unmet precondition, validates the touched artifact afterwards, and
  writes derived run-evidence. It never defines a metric or a model, never moves a readiness
  stage to pass, never writes `approvals[]`, and never grants itself the authority it checks.
---

# pbi-mcp-write-adapter

- **Authority category (F024):** Execution Adapter / `publish-capable`, execution-only --
  the binding declaration is `templates/pbi-mcp-adapter-contract.md`.
- **Roadmap feature:** F016 slice 5  **On-disk spec:** `specs/149-pbi-mcp-write-adapter`
- **Authorizing decision:** `docs/decisions/0018-unpark-f016-power-bi-mcp-execution-adapter.md`
  (ratified by the owner 2026-08-18). All eight ADR decisions bind together; none is severable.

## What problem this closes

A user who has taken a semantic model all the way to an approved, signed-off state still had
to leave the governed workflow and apply the change by hand in Power BI Desktop. Nothing
recorded what was applied, to which target, on whose authority, or whether the artifact still
validated afterwards. Microsoft's official Power BI MCP *can* apply such changes, but its own
documentation warns that autonomous or misconfigured clients may perform destructive actions
and that its safety flags are non-standard and client-dependent.

So the gap was never "we lack a tool". It was "the available tool's safety model is weaker
than the approval spine we already run." This adapter puts Seshat's recorded, named-human
approval **above** the vendor tool rather than trusting the vendor's prompts.

## The rule you must not talk yourself out of

**You never supply the evidence that permits your own write.** Every precondition is
*derived* from committed state, never accepted as something you assert. If you find yourself
reasoning "the user said it was approved" or "I already checked that", stop: ask *checked
against what?* If the answer is "what I was told", the gate has not been satisfied.

This is not a style preference. Five separate versions of that exact defect were caught in
this feature's own review -- a caller-supplied allowlist, a caller-asserted operation binding,
a caller-asserted backup, a permissive git-state default, and a gate that read the working
tree (where an agent can write) instead of HEAD.

## Preconditions for a write (all required, none severable)

A write proceeds only when **every** one of these holds. Each has its own typed blocker, so a
refusal names the specific missing authority:

| # | Precondition | Blocker |
|---|---|---|
| 1 | `semantic_model_ready` is `pass` for the target, read from **HEAD** | `PBIMCP-GATE-01` |
| 2 | readiness state is readable (absent / malformed / unreadable all refuse) | `PBIMCP-GATE-02` |
| 3 | readiness state is **committed** -- tracked and identical to HEAD | `PBIMCP-GATE-03` |
| 4 | a shape-valid named-human `publish_ready` approval exists | `PBIMCP-GATE-04` |
| 5 | that approval's note names **this** target as a whole token | `PBIMCP-GATE-05` |
| 6 | the operation resolves to an approved operation for this target | `PBIMCP-GATE-06` |
| 7 | the target is in the **committed** allowlist | `PBIMCP-GATE-07` |
| 8 | the allowlisted artifact exists on disk | `PBIMCP-GATE-08` |
| 9 | the tree is clean, or a **resolvable** backup ref was named | `PBIMCP-GATE-09` |

Plus: an uncommitted allowlist (`-10`), an unprobed git state (`-11`), and an unresolvable
backup ref (`-12`) each refuse on their own.

Two of these deserve emphasis because they are the ones most likely to be argued away:

- **#3, committed state.** A passing `readiness-status.yaml` that exists only in the working
  tree is refused. An agent can write files, so a worktree read would let the agent author
  its own approval. `dagster_adapter/gate.py` guards only `unresolved-questions.md`, so
  "mirror the shipped reader" reproduces this hole -- don't.
- **#5, whole-token naming.** An approval naming `sales_model` does **not** authorize
  `sales_model_v2`. A substring check would let a loosely worded note widen its own scope,
  which is self-granted authority.

## The standing invariant

`--skipconfirmation` is refused in **every** mode -- including read-only, including in test
fixtures -- and the check runs before any invocation. It is not a branch inside write mode.
`seshat.pbi_mcp.detect.refuse_if_bypass_flag` **raises**; there is no verdict to ignore.

Read-only is the resting state. Write mode is never reached by omission, and `--readwrite` is
never a default.

## How to drive it

```bash
# 1. ALWAYS dry-run first. Evaluates every precondition, mutates nothing.
seshat pbi-mcp plan-write --target <target_id> --operation <operation_id> --json

# 2. Only once plan-write reports no blockers:
seshat pbi-mcp apply --target <target_id> --operation <operation_id> --json

# When the tree is legitimately dirty, name a backup ref that RESOLVES:
seshat pbi-mcp apply --target <t> --operation <o> --backup-ref refs/tags/pre-write
```

Both legs accept identical arguments, so `plan-write` is a truthful preflight for `apply`.

**Exit codes** -- 2 and 3 are deliberately distinct:

| Code | Meaning |
|---|---|
| 0 | applied and confirmed by validation (`materialized`), or a clean dry run (`deferred`) |
| 1 | refused; nothing was mutated |
| 2 | applied, then post-write validation FAILED -- rollback guidance is printed |
| 3 | **indeterminate** -- the runtime stalled or died; the artifact may be half-written |

Never treat 3 as 1. A clean failure and a possibly-corrupted artifact are different problems.

## What a write does NOT do

- **It does not move any readiness stage.** A successful write leaves `publish_ready` exactly
  as it found it (FR-018). A green write is not an approval and never becomes one.
- **It does not write `approvals[]`.** Approval and readiness records are read-only inputs.
- **It does not define anything.** No metrics, no mappings, no semantic logic, no dashboard
  design. It executes a decision made upstream; if the definition is absent, it refuses
  rather than inventing one.
- **It does not vendor the runtime.** The official MCP is invoked through `npx` -- external,
  unforked, independently upgradeable (ADR 0018 rejected vendoring).

## Evidence

Every run -- success, failure, and refusal -- writes exactly one record to
`.seshat/pbi-mcp-write-evidence.json`: what ran, in which mode, against which target, when,
and how it ended. The record carries a fixed authority label (`derived-evidence-only`), typed
blockers, and **no numeric, maturity, or confidence score** of any kind.

`mutation_attempted` tells a refusal apart from an indeterminate run -- both can read
`blocked`, and only that field distinguishes "nothing was touched" from "state unknown".

An **intent** record lands *before* the mutation, so a process killed mid-write still leaves a
trace naming what was attempted.

## Post-write validation

A zero exit from the vendor runtime is not confirmation. Validation runs
`seshat semantic-check --require-inputs` against the touched artifact:

- the **semantic-model** family, not the report-layer R-family (which iterates
  `*.Report/definition.pbir` and contains no TMDL, so it would examine zero bytes of what
  changed);
- `--require-inputs` because `semantic-check` otherwise exits 0 on an empty corpus while
  printing "nothing was verified ... This is NOT a clean result";
- and "validated" is structurally unrepresentable when zero artifacts were examined.

A validation failure is **blocking with rollback guidance**, never a warning.

## Known blocked scope

- **FR-011b (approval-time content hash) is EXTERNALLY BLOCKED**, by owner decision
  2026-08-18. Verifying a definition against a hash recorded at sign-off needs a producer
  written by a named human at approval time, and this feature is forbidden to write
  approvals. Operation *resolution* and target-match still apply. Do **not** "fix" this by
  writing the hash yourself -- that is the adapter authorizing its own mutation.
- **Slice 6 (the remote query-only server) is out of scope** (ADR decision 7). Nothing here
  may make remote query results an input to any readiness stage.

## When to hard-stop and ask

- The approval note does not name the target → the owner records a fresh approval. **Never
  reword an existing note.** A missing approval is closed by a human deciding, not by an
  agent editing prose.
- The target is not in the committed allowlist → adding it is a reviewed, committed change.
- Any Principle-V judgment call (what the change should be, whether it is correct, whether a
  stage may advance) → not yours. Stop.
