# Security Policy

## Supported versions

Seshat BI is in public beta. Security fixes are applied to the latest released
version on PyPI (`seshat-bi`) and the latest marketplace plugin. Older versions
are not separately patched — please upgrade to the latest release.

| Version         | Supported          |
| --------------- | ------------------ |
| Latest release  | :white_check_mark: |
| Older releases  | :x:                |

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.** Public
disclosure before a fix is available puts every installed copy at risk.

Instead, report privately through **GitHub private vulnerability reporting**:

1. Go to the repository's **Security** tab → **Report a vulnerability**
   (this opens a private advisory only the maintainers can see).
2. Describe the issue, the affected component (PyPI package, the Claude/Codex
   marketplace plugin, or the CI/release workflow), and a minimal reproduction.

If GitHub private reporting is unavailable to you, contact the maintainer
listed in `pyproject.toml` directly and mark the message as a security report.

### What to expect

- **Acknowledgement:** within 5 business days.
- **Assessment & triage:** we will confirm the report, assess severity, and
  agree on a remediation timeline with you.
- **Fix & disclosure:** we aim to ship a fix and publish a coordinated advisory
  promptly. We will credit you unless you prefer to remain anonymous.

## Scope

This project is a **read-only BI readiness checker and agent tool**. Reports are
in scope when they describe a way for untrusted input to cause harm to a user of
the published artifacts, for example:

- **Code execution** from the CLI processing an untrusted input — e.g. a
  downloaded/adopted PBIP project, a crafted source-map, or a malformed model
  file. (The `seshat adopt-pbip` flow runs `git` against externally-authored
  project trees; git invocations there are hardened against config-driven
  execution — `core.fsmonitor` / `core.hooksPath` — but new sinks are in scope.)
- **Secret or credential leakage** into logs, tracebacks, generated output, or a
  published artifact (the DSN redaction layer is intended to prevent this).
- **Prompt-injection / instruction-smuggling** in any marketplace-distributed
  skill, command, or knowledge file that could hijack a consumer's agent.
- **Supply-chain** issues in the build/release pipeline or dependencies.

## Handling of sensitive data

Do not include real credentials, real customer data, or production connection
strings in reports, issues, pull requests, or test fixtures. Use synthetic
placeholders. Credentials belong only in a git-ignored `.env` (see
`CONTRIBUTING.md`).
