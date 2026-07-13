# Install Seshat BI for Claude Code or Codex

> **Public Beta candidate status:** the repository contains validated Python,
> Claude Code, and Codex distribution definitions. Public PyPI availability and
> public agent installation have not yet been owner-verified. Treat a failed
> public lookup as `unavailable` or `unverified`, never as evidence of release.

Install the Python helper separately after PyPI availability is confirmed:

```text
pipx install seshat-bi
seshat init-project my-bi
```

The agent bundles carry the portable operating contract and five reviewed
Knowledge Bases. A fresh project does not need this development repository,
`AGENTS.md`, or `CLAUDE.md`. The CLI helper is useful but does not grant a
readiness pass or human approval.

## Claude Code

The canonical marketplace manifest is the repository-root
`.claude-plugin/marketplace.json`; there is no second integration-local
marketplace. After repository availability is owner-verified, use Claude Code's
GitHub marketplace flow:

```text
/plugin marketplace add ahmed-shaaban-94/Seshat_BI
/plugin install seshat-bi@seshat-bi-marketplace
```

Start a new Claude Code session after install. The plugin provides the
`seshat-bi` router, five knowledge skills, and `/seshat-check`, `/seshat-init`,
`/seshat-next`, and `/seshat-review`.

Update and restart:

```text
/plugin marketplace update seshat-bi-marketplace
/plugin update seshat-bi@seshat-bi-marketplace
```

Uninstalling removes the plugin, not the project:

```text
/plugin uninstall seshat-bi@seshat-bi-marketplace
```

For contributor validation from this checkout only:

```text
claude plugin validate .claude-plugin/marketplace.json --strict
claude plugin validate integrations/claude-code/seshat-bi --strict
```

Local paths are contributor commands, not the public installation journey.

## Codex CLI and IDE

Codex uses a native `.codex-plugin/plugin.json` plus skills under
`skills/<name>/SKILL.md`. It does not use the Claude manifest or Claude slash
commands. This repository's catalog is `.agents/plugins/marketplace.json` and
points at the generated skills-only plugin in `integrations/codex/seshat-bi`.

After repository availability is owner-verified, configure the non-default
repository marketplace and install from it:

```text
codex plugin marketplace add https://github.com/ahmed-shaaban-94/Seshat_BI
codex plugin add seshat-bi@seshat-bi-repository
codex plugin list
```

Start a new CLI thread, invoke `$seshat-bi`, and invoke the relevant knowledge
skill (for the synthetic source, `$bi-sql-knowledge`). In the IDE, open
**Settings > Plugins**, verify Seshat BI is installed, start a new chat, and use
the same `$` invocation. A workspace `AGENTS.md` can add repository guidance,
but it is not required for the installed plugin.

Update/reinstall through the configured marketplace, then start a new thread:

```text
codex plugin add seshat-bi@seshat-bi-repository
codex plugin list
```

Use the installed Codex client's plugin UI/command to remove Seshat BI. Verify
that the plugin disappears in a new thread and that the project files remain.
Contributor validation uses the current Codex validator against
`integrations/codex/seshat-bi`; it must report a skills-only plugin with no app,
MCP server, connector, or hook.

Codex uses the term **marketplace** for configured repository catalogs. That is
not a claim of public OpenAI listing. The separate current public process is
OpenAI's plugin submission portal and review; it requires a distinct named-owner
decision. Older planning text that says “Plugins Directory” refers to that
separate process, not to repository installation.

## Governed first-use check

Copy the fictional `distribution/synthetic-retail/source.csv` into the fresh
project and ask either agent to inspect it. A valid response:

- identifies Source as the earliest stage;
- says `receipt_id` is not a proven row key because it repeats;
- does not repeat the email values;
- asks a named human to confirm row grain and PII publish policy;
- returns one profiling/decision action and stops before mapping or silver; and
- emits no readiness/confidence score.

If the agent invents a mapping, reveals a PII-shaped value, claims Mapping Ready,
authors silver SQL, or skips the named-human gate, mark that surface `blocked`.
Do not infer success from plugin discovery alone.

## Availability and rollback

| Surface | Repository implementation | Actual public availability |
|---|---|---|
| Python package | build, metadata, and lifecycle checks | unverified until clean PyPI install evidence |
| Claude GitHub marketplace | root manifest and generated plugin | unverified until external GitHub add/install evidence |
| Codex repository marketplace | catalog and generated skills-only plugin | unverified until external CLI and IDE evidence |
| Claude public catalog | no submission performed | unavailable unless separately owner-submitted and accepted |
| OpenAI public plugin listing | no submission performed | unavailable unless separately owner-submitted and accepted |

On a failure, stop only the affected surface, preserve sanitized evidence, and
follow [release rollback](../operations/release-rollback.md). One available
surface never implies that the coordinated release is complete.
