# Quickstart: applying an approved Power BI change through the governed path

**Feature**: [spec.md](./spec.md) | **Contract**: [contracts/cli-contract.md](./contracts/cli-contract.md)

> **Status: this describes behavior this spec plans, not behavior that ships today.**
> Slice 5 is authorized by ADR 0018 (ratified 2026-08-18) but not yet built. Until it is, the
> only working commands are the read-only family: `doctor`, `generate-config`, `preflight`.

---

## What must already be true before you can write

The adapter cannot grant any of these. All four are prerequisites, not steps:

1. **`semantic_model_ready = pass`** for the target scope, in the committed readiness record.
2. **A named-human `publish_ready` approval whose note names your target** — by its exact
   declared identity. An approval naming `sales_model` does **not** authorize
   `sales_model_v2`.
3. **The target is on the declared allowlist.**
4. **A clean git working tree**, or an explicit `--backup-declared`.

If you are missing one, the answer is to obtain it — not to work around the tool. There is no
`--force`.

---

## Step 1 — Check before you write

```bash
seshat pbi-mcp plan-write --target sales_model
```

This mutates nothing. It reports each precondition individually.

**Cleared** looks like exit `0` and every precondition green. **Blocked** looks like exit `1`
with the specific missing authority named — for example:

```text
BLOCKED: publish_ready approval does not name target 'sales_model'
BLOCKED: working tree is dirty and no backup was declared
```

Each line is the actual thing to go fix.

---

## Step 2 — Apply

```bash
seshat pbi-mcp apply --target sales_model --operation <approved-op>
```

The pipeline runs in this order, and stops at the first refusal:

```text
bypass-flag invariant  →  four preconditions  →  target resolution
       →  git safety  →  Microsoft MCP execution
       →  post-write validation  →  evidence
```

---

## Reading the outcome

| Exit | Meaning | What to do |
|---|---|---|
| `0` | Applied and validated. | Nothing. Note that this is **not** an approval and **no stage advanced**. |
| `1` | Refused before execution. | Nothing was mutated. Fix the named precondition. |
| `2` | Applied, but validation **failed**. | Follow the printed rollback guidance. |
| `3` | Indeterminate — the runtime stalled or died mid-write. | Follow the rollback guidance; assume the artifact may have changed. |

**Exit `0` is not a sign-off.** A successful write is recorded as evidence; advancing readiness
remains a named human's separate, recorded act. This is deliberate: if a green write could
advance a stage, the tool would be granting its own approval.

---

## When validation fails (exit 2)

The output carries rollback guidance because the artifact is now in a state that does not
validate. Follow it, then re-check:

```bash
seshat check
```

The artifact should return to its pre-write validating state. If it does not, treat it as an
incident rather than retrying the write.

---

## Rolling back

The adapter refuses to write against a dirty tree precisely so that rollback is always
available. With a clean starting tree, the change you just applied is the only uncommitted
delta, so ordinary git recovery applies. If you overrode that with `--backup-declared`, your
declared backup is the rollback path — the adapter took your word for it and recorded that it
did.

---

## What you will never be able to do with this tool

Not limitations to route around — boundaries that are the point:

- **Write without a named human's target-specific approval.** No flag enables it.
- **Use `--skipconfirmation`.** Refused in every mode, including read-only, including in
  tests. Seshat replaces the vendor's per-write prompt with a stronger recorded approval; it
  does not trade one weak check for none.
- **Advance a readiness stage by writing successfully.** Evidence is not approval.
- **Author the change itself.** The adapter executes decisions made upstream; it never
  defines metrics, mappings, semantic logic, or dashboard design.
- **Reach the remote query server.** That is slice 6, still gated on ADR decision 7.

---

## Evidence you can expect afterwards

Every run — success or failure — writes exactly one derived record: what ran, in which mode,
against which target, when, and how it ended (`materialized` / `failed` / `skipped` /
`blocked` / `deferred`). It carries a fixed authority label and typed blockers, and
deliberately carries **no** score of any kind. Hosts, tenants, credentials, and user paths are
redacted before anything is committed.
