# Research: Dagster official delegation

## Repository truth

- The shipped `seshat dagster` runtime is a real Dagster asset graph with
  Seshat-specific gate, closed-argv, redaction, fail-closed, and evidence seams.
- `dagster-workflows` is the public Seshat router and is a legitimate bundled
  capability, not an official Dagster skill copy.
- The integration catalog currently calls that bundled router
  `dagster-skills`, creating a stale identity collision.
- No official Dagster skill repository is cataloged today.

## Upstream truth

- Dagster's official repository is `dagster-io/skills`.
- Its `dagster-expert` skill owns generic project scaffolding, asset patterns,
  schedules, sensors, CLI use, project structure, debugging, and validation.
- The official README supports Claude Code and OpenAI Codex and documents
  marketplace, `npx skills`, and manual installation paths.
- Sources verified 2026-08-07:
  - https://github.com/dagster-io/skills
  - https://dagster.io/blog/dagster-1-13-octopuss-garden

## Decision

Add the official integration without copying it into Seshat canonical
ownership. Keep Seshat's router and runtime adapter only for the governed BI
delta. Leave supported-harness activation and discovery to Phase 6.
