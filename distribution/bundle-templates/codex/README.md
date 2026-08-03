# Seshat BI for Codex

This generated Codex plugin contains the `$seshat-bi` readiness router, the
governed `$dbt-workflows` transformation skill, the guarded
`$powerbi-workflows` Power BI routing skill, the ten compass verbs, and the
public knowledge skills.

It activates no app, connector, hook, or remote service. It declares one
**local, read-only** MCP server, `seshat-governor`, which the host launches over
stdio as `seshat mcp` from the separately installed `seshat-bi` CLI. The server
takes no credentials and contacts no network service; its only argument is
`--repo`, a local repository root exposed for governor reads. Without the MCP
optional extra, `seshat mcp` fails closed with a named install hint rather than
degrading silently. Install `seshat-bi` separately for CLI helpers; use the
`dbt` extra for dbt execution.

After public repository availability is verified, run
`codex plugin marketplace add https://github.com/Kemetra/Seshat-BI`
and `codex plugin add seshat-bi@seshat-bi-repository`. Start a new CLI thread or
IDE chat, then invoke `$seshat-bi` explicitly. The plugin works in a fresh
workspace without `AGENTS.md` or a development-repository clone.

Repository installation and OpenAI's public plugin submission/review process
are separate flows. A repository bundle does not imply public availability;
submission and publication remain named-owner actions.
