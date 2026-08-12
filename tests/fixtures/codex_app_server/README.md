# Codex app-server protocol fixtures (T019)

Minimal **sanitized** JSON-RPC frames for the Codex app-server surface Studio
speaks. Every frame here was derived from the schema bundle the installed CLI
generates itself:

```
codex app-server generate-json-schema --out <TEMPORARY DIR>
```

**The generated bundle is deliberately NOT committed.** It is 3.4 MB of
version-specific audit input across 39 top-level schemas, and committing it
would turn a protocol probe into a vendored copy of someone else's contract.
What is committed is the small hand-derived subset below, each frame carrying
the protocol version it was derived from, per the bridge contract's
"Fixtures identify their source protocol version and are safe to commit."

## Provenance

| Field | Value |
|---|---|
| CLI | `codex-cli 0.147.0` |
| Derived on | 2026-08-11 |
| Generator | `codex app-server generate-json-schema` (no `--experimental`) |
| Contract mapping verified against | 0.146.0 (spec) and 0.147.0 (this run) |

The bridge contract records a verified provider mapping for 0.146.0. Re-deriving
on 0.147.0 confirmed all 19 methods that mapping depends on are still present,
which is what makes 0.147.0 *tested* rather than merely semver-adjacent. The
contract is explicit that proximity alone is not compatibility evidence.

## Why these frames and not a recorded session

A recorded live session would embed a real account, real paths, and a real
token refresh. These are synthesised from the schemas instead, so every value
is fictional while every *shape* is authoritative. The risk that replaces is a
fixture that agrees with the client because both were written from the same
misreading — so the shapes here are asserted against the generated schema in
`test_codex_fixture_provenance.py` rather than trusted by eye.

## Known divergence: these fixtures carry a `jsonrpc` field the provider does not

Every frame here declares `"jsonrpc":"2.0"`. **The real app-server never sends
it, and the generated schema never declares it** — `JSONRPCResponse` requires
only `id` and `result`, `JSONRPCNotification` only `method`. The field was
hand-written into these fixtures from an assumption about what JSON-RPC "should"
look like, and the client was written from the same assumption, so the two
agreed with each other while both diverged from the provider.

That went unnoticed because `test_every_fixture_method_exists_in_the_generated_schema`
checks METHOD NAMES, not payload fields. Only the T021 task 6 integration test —
the one that asks the installed CLI — could see it.

`CodexProtocolReader` now accepts a frame whose `jsonrpc` is **absent** and still
rejects one whose value is **wrong**, so both the fixtures and real provider
output parse. The fixtures are left as-is rather than rewritten: the provenance
table above records a specific derivation run, and silently editing eight files
would invalidate that record for a field that changes no behaviour. Treat the
provider's shape, not this field, as authoritative.

## Sanitization rules applied

- No real account identifiers, emails, or plan names — `user@example.invalid`.
- No real filesystem paths — workspace-relative or `/workspace/...` only.
- `stderr_secrets.jsonl` intentionally CONTAINS secret-shaped strings: it is the
  negative fixture proving the redactor removes them. Those values are fake and
  are the only place a credential shape may appear.
- No `apiKey` or `chatgptAuthTokens` request variants are modelled as an
  outbound frame. Studio never sends them (FR-013); the token-refresh frame
  appears only as an inbound server request Studio must refuse to satisfy.

## Files

| File | Covers |
|---|---|
| `handshake.jsonl` | `initialize` → response → `initialized` |
| `account.jsonl` | `account/read`, `account/rateLimits/read`, signed-out, quota-limited |
| `login.jsonl` | managed ChatGPT `account/login/start`, completion notification, `account/logout` |
| `thread_turn.jsonl` | `thread/start`, `turn/start`, visible message deltas, plan, tool items, `turn/completed` |
| `file_change_turn.jsonl` | a `propose_changes` turn: a `fileChange` ITEM notification (write intent) through `turn/completed` |
| `approvals.jsonl` | command + file-change approval requests and `serverRequest/resolved` |
| `incompatible.jsonl` | unknown required request method, experimental-required method |
| `malformed.jsonl` | invalid JSON, missing `jsonrpc`, unknown id, wrong-typed id, null params |
| `stderr_secrets.txt` | provider stderr containing secret-shaped values (negative fixture) |
| `quota.jsonl` | rate-limit exhaustion + reset detail |

`.jsonl` = one JSON-RPC frame per line, the same newline-delimited framing the
app-server uses on stdio.

### Why `file_change_turn.jsonl` is separate from `approvals.jsonl`

They look similar and are not interchangeable. `approvals.jsonl` holds
server→client **requests** (`item/fileChange/requestApproval`, each carrying an
`id`); answering those is the approval surface T024–T027 owns, and
`normalize_notification` deliberately maps none of them to events today.
`file_change_turn.jsonl` holds a `fileChange` **item notification**
(`item/started`), which is the only shape that reaches `_file_change_event` and
so the only one that yields `file_change_proposed`.

It also cannot be folded into `thread_turn.jsonl`: `read_only` drives that
fixture, and `test_read_only_mode_never_proposes_a_file_change` would then fail.
One fixture per mode is what lets that test and its `propose_changes` twin both
mean something.

Every method here already appears in `thread_turn.jsonl` and is therefore
covered by `test_every_fixture_method_exists_in_the_generated_schema`; only the
item payload `type` (`fileChange`) is new, and that type is already rendered by
`codex_protocol`.
