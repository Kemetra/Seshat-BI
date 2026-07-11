# Contract: Read-Only Agent Governor

Protocol adapter: stable MCP v1 over local stdio. The transport-neutral service is the
authority for behavior; protocol annotations are descriptive, not security controls.

Every tool accepts an explicit local workspace root, returns structured content matching
an output schema, sanitizes errors, and sets `read_only_proof: true`. Every tool is
read-only, non-destructive, non-idempotence-sensitive, and network-independent.

| Tool | Required input | Result |
|------|----------------|--------|
| `seshat_get_status` | workspace; optional table | Seven-stage status projection with evidence and blockers. |
| `seshat_get_next_action` | workspace; optional table | One allowed action, forbidden scope, stop point, required authority. |
| `seshat_explain_blockers` | workspace; table | Concrete blockers, evidence gaps, owner, recovery action. |
| `seshat_prepare_approval_request` | workspace; table; decision ID | Derived request for a named human role; never an approval receipt. |
| `seshat_run_static_check` | workspace | Existing static findings and explicit static/live boundary. |
| `seshat_export_evidence_pack` | workspace; table(s) | In-memory evidence-pack projection; file export remains an explicit CLI operation. |

## Error contract

- Malformed protocol/request shape: protocol error.
- Invalid workspace, path escape, malformed readiness input, unsupported schema, or
  blocked business action: tool execution error with actionable structured detail.
- No raw traceback, DSN, environment secret, absolute path, or raw source value is
  returned.

## Write-proof contract

Contract tests snapshot tracked files, output directories, environment, DB writer probes,
and Power BI directories before and after every tool. Any change fails the tool suite.
