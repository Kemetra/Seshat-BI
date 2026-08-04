# Codex app-server protocol probe

**Captured:** 2026-08-03  
**Runtime:** Windows, `codex-cli 0.146.0`  
**Scope:** read-only feasibility evidence for Studio Foundation; no feature
ratification, business approval, release approval, or implementation claim.

## Method

The installed Codex CLI generated its version-specific JSON Schema bundle into a
temporary directory with:

```text
codex app-server generate-json-schema --out <temporary-directory> --experimental
```

The bundle was inspected but not copied into the repository. A temporary Node
client then started the installed app-server through its direct npm entry point,
because Windows cannot spawn the PowerShell command shim as a native executable.
The client sent only:

1. `initialize` with `clientInfo.name: seshat_studio_probe` and no capabilities;
2. `initialized` after the initialization response;
3. `account/read` with `refreshToken: false`; and
4. `account/rateLimits/read`.

It printed only categorical facts. It did not print the account object, identifiers,
email, plan, token, rate-limit values, or child-process stderr. It did not read or
copy an auth file, inspect API-key environment variables, start a thread, start a
turn, invoke a model, modify Codex configuration, or consume a plugin installation.

## Sanitized result

```text
initialize=pass
account_read=pass
signed_in=true
auth_type=chatgpt
requires_openai_auth=true
rate_limits_read=true
probe=pass
```

`signed_in=true` means the returned `account` value was non-null;
`auth_type=chatgpt` is the account variant. The separate
`requiresOpenaiAuth` protocol boolean is recorded verbatim and is not treated as a
sign-out signal when a ChatGPT account is present.

## What this proves

- The mandatory stable handshake works on the installed version without enabling
  `experimentalApi`.
- The app-server can reuse the existing Codex-managed ChatGPT login without Studio
  receiving a credential.
- Account and rate-limit health surfaces are available for categorical health
  mapping.

## What remains unproven

- A Studio implementation does not yet exist.
- No thread, streamed turn, event normalization, interruption, or technical
  approval relay was exercised.
- This single-version result is not compatibility evidence for another Codex CLI
  version.
- Full signed-in Studio acceptance remains T036 and may run only after spec 139 is
  named-human ratified, active, implemented, and locally verified.
