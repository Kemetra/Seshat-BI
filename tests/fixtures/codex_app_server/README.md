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
| `approvals.jsonl` | command + file-change approval requests and `serverRequest/resolved` |
| `incompatible.jsonl` | unknown required request method, experimental-required method |
| `malformed.jsonl` | invalid JSON, missing `jsonrpc`, unknown id, wrong-typed id, null params |
| `stderr_secrets.txt` | provider stderr containing secret-shaped values (negative fixture) |
| `quota.jsonl` | rate-limit exhaustion + reset detail |

`.jsonl` = one JSON-RPC frame per line, the same newline-delimited framing the
app-server uses on stdio.
