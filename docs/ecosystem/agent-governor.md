# Agent Governor

The Seshat BI Agent Governor exposes six local, read-only governance tools to MCP v1
hosts. It is a companion to execution tools, not an execution tool: it can inspect
status, identify the next allowed action, explain blockers, prepare a human approval
request, run static checks, and assemble an in-memory evidence pack. It cannot write a
file, connect to a database, operate Power BI, record an approval, or advance readiness.

## Install and register

```bash
pip install "seshat-bi[mcp]"
seshat mcp --repo /path/to/one/local/repository
```

Configure the host to launch that command over stdio. Each call must pass the same
explicit workspace path selected by `--repo`; a different root or a path escape fails
closed. The SDK is imported only for `seshat mcp`, so normal CLI and governance use do
not require the optional extra.

## Tools

| Tool | Boundary |
|---|---|
| `seshat_get_status` | Projects committed seven-stage state. |
| `seshat_get_next_action` | Returns one allowed action and refuses premature requested scope. |
| `seshat_explain_blockers` | Explains recorded blockers for one table. |
| `seshat_prepare_approval_request` | Prepares a request for a named human; never creates a receipt. |
| `seshat_run_static_check` | Runs existing pure rules; live validation remains `not_run`. |
| `seshat_export_evidence_pack` | Returns an in-memory preview; performs no export write. |

## Threat model

The transport-neutral service is the enforcement boundary. MCP annotations advertise
`readOnlyHint=true`, `destructiveHint=false`, and `openWorldHint=false`, but annotations
are not trusted as controls. The service binds one resolved root, rejects table path
syntax, sanitizes errors, and returns structured blocked or input-defect outcomes. It
does not return DSNs, environment secrets, absolute server paths, raw source values, or
tracebacks.

Execution MCPs may consume the governor response, but they must stop at its
`forbidden_scope`, `required_authority`, and `next_action` boundary. The governor never
authorizes a downstream tool to cross a readiness gate.
