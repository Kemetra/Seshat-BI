# Contract: Studio Local Security Boundary

**Feature**: 139-seshat-studio-foundation | **Status**: proposed

Studio is a local single-user service, but localhost is not treated as a trusted
network. This contract is part of Foundation acceptance.

## Process Boundary

1. The launcher resolves the requested repository before importing or starting the
   web server.
2. It accepts only a recognized Seshat workspace and pins that absolute root in
   immutable process configuration.
3. Browser requests contain no workspace path parameter, header, or cookie.
4. The server binds exactly to IPv4 `127.0.0.1` on an OS-assigned port. Requests for
   `0.0.0.0`, IPv6-any, LAN, or public binding are rejected.
5. A second launch for the same workspace may reuse only a healthy instance whose
   root fingerprint matches. It never reassigns an existing process to another root.

## Bootstrap and Session

1. Startup generates at least 256 bits of cryptographically secure random token data.
2. The token is placed in the fragment or one-time bootstrap URL only long enough to
   perform `POST /api/v1/bootstrap`.
3. Studio stores a digest, compares in constant time, and invalidates the token after
   one successful exchange.
4. The response sets an unpredictable `seshat_studio_session` cookie with
   `HttpOnly`, `SameSite=Strict`, `Path=/`, and no `Domain`. `Secure` is omitted only
   because the loopback origin is HTTP; exact Host enforcement prevents widening.
5. Client code immediately calls `history.replaceState` to remove token material.
6. Session expiry, process restart, or explicit shutdown invalidates access.

The raw token and cookie value never enter logs, agent context, events, errors, or
durable files.

## Request Enforcement Order

For every protected HTTP or SSE request, middleware performs these checks before
endpoint logic:

1. connection local address and configured bind are loopback;
2. `Host` equals the selected loopback host and port;
3. `Origin`, when required, exactly equals the Studio origin;
4. session cookie is present, valid, and unexpired;
5. content type and body size satisfy the route contract;
6. opaque resource identifiers belong to this process;
7. snapshot revision and state transition are current.

Failure returns a redacted problem response and no workspace content. CORS is not
enabled. Mutating requests with a missing origin are rejected; health is the only
public endpoint and reveals no workspace identity.

## Filesystem Boundary

- Browser input is never converted into an arbitrary `Path`.
- Existing evidence references are treated as untrusted workspace-relative values.
- Before any optional file read, the backend resolves the candidate, verifies it is
  contained by the pinned root, and checks the expected file kind.
- Symlink/junction escapes and `..` traversal are rejected as input defects.
- Browser responses show a safe relative reference or label, never an absolute path.
- Foundation exposes no file-write endpoint. Agent changes flow only through Codex
  technical approvals and its configured sandbox.

## Agent and Secret Boundary

- Studio discovers and starts Codex without a shell-interpolated command string.
- Studio does not read Codex auth storage or `OPENAI_API_KEY`.
- Child-process output is untrusted and passes redaction before buffering, logging,
  exception conversion, or delivery.
- Redaction covers DSNs, passwords, bearer/basic authorization values, cookies,
  common token/key assignments, credential-bearing URLs, and environment dumps.
- When safe redaction cannot be guaranteed, Studio emits a categorical error and
  withholds the raw value.
- Hidden provider reasoning is neither persisted nor displayed.

## Browser Asset Boundary

- Production content security policy allows only self-hosted scripts, styles,
  images, fonts, API calls, and SSE connections.
- No CDN, analytics, telemetry, remote font, external image, service worker, iframe,
  or browser extension dependency is required.
- Static files are packaged with immutable hashes or equivalent cache validators.
- HTML uses no inline executable script unless represented by a nonce generated for
  that response; the preferred build uses external bundled modules.

## Security Headers

Every application response includes at least:

```text
Content-Security-Policy: default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; connect-src 'self'
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
Cache-Control: no-store
```

## Required Negative Tests

- missing, invalid, expired, and replayed bootstrap token;
- missing session and forged cookie;
- foreign and null origin on protected mutation and SSE routes;
- manipulated Host and attempted non-loopback bind;
- arbitrary path field, traversal, symlink/junction escape, and stale table id;
- oversized prompt and unsupported content type;
- repeated approval response and approval for prohibited readiness scope;
- raw credential-shaped values in provider stdout, stderr, exception, event, and
  diagnostic paths;
- browser asset request that would require a network origin.

The tests assert both the status code and that response bodies contain no workspace
identity, absolute path, token, or injected secret.
