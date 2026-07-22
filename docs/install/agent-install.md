# Install Seshat BI for Claude Code or Codex

> **Status:** the current public release is `seshat-bi==0.6.1` on public PyPI
> (version single-sourced from `pyproject.toml` and the generated plugin
> manifests), externally accepted per
> [the v0.3.1 public acceptance record](../releases/v0.3.1-public-acceptance.md).
> Against 0.3.1, the Claude Code repository plugin passed install, discovery,
> governed-behavior, pressure/refusal, update, and uninstall acceptance
> (Claude Code `2.1.211`, Windows; headless behavioral sessions, with the
> profile-isolation limitation noted in the record), and the Codex CLI plugin
> passed install, discovery, governed-behavior, pressure/refusal, update, and
> removal acceptance (codex-cli `0.144.5`). The Codex IDE path remains
> unverified. Neither plugin is submitted to a public catalog. See
> [the support matrix](support-matrix.md).

Install the Python helper separately:

```text
pipx install seshat-bi
seshat init-project my-bi
```

For governed dbt shadow execution, install the pinned optional runtime instead:

```text
pipx install "seshat-bi[dbt]"
```

The agent bundles carry the portable operating contract and reviewed Knowledge
Bases. A fresh project does not need this development repository, `AGENTS.md`, or
`CLAUDE.md`. The CLI helper is useful but does not grant a readiness pass or human
approval; the plugin provides skills and governance instructions, not the CLI
itself.

## Claude Code

The canonical marketplace manifest is the repository-root
`.claude-plugin/marketplace.json`; there is no second integration-local
marketplace. Use Claude Code's GitHub repository marketplace flow:

```text
/plugin marketplace add Kemetra/Seshat-BI
/plugin install seshat-bi@seshat-bi-marketplace
```

Start a new Claude Code session after install. The plugin provides the
`seshat-bi` router skill, the governed `dbt-workflows` transformation skill,
the guarded `powerbi-workflows` routing skill, reviewed knowledge skills, and
namespaced slash commands. Claude Code
namespaces plugin-provided commands by plugin name, so invoke them as
`/seshat-bi:<name>`; do not expect the unnamespaced forms (`/seshat-check`,
etc.) to resolve.

Core readiness commands:

- `/seshat-bi:help` -- the accurate installed command map.
- `/seshat-bi:init` -- initialize or inspect a fresh project safely.
- `/seshat-bi:check` -- run and interpret the static governance check.
- `/seshat-bi:status` -- truthful per-table readiness status.
- `/seshat-bi:next` -- the one truthful next readiness action.
- `/seshat-bi:doctor` -- workspace health check interpretation.
- `/seshat-bi:review` -- evidence review that stops at the human gate.
- `/seshat-bi:auto` -- the governed autonomous loop (next action, act,
  re-check, repeat) that always stops at the next named-human gate.

Governed dbt commands:

- `/seshat-bi:dbt-doctor` -- check the pinned runtime and local profile
  prerequisites without querying a database.
- `/seshat-bi:dbt-plan` -- validate Mapping Ready and prepare the immutable
  selected graph plus acceptance digest.
- `/seshat-bi:dbt-build` -- run the fixed shadow build only with the exact
  reviewed `--accept-plan` digest.
- `/seshat-bi:dbt-review` -- inspect normalized evidence and stop for a named
  human; passing evidence does not switch the active build path.

These commands were added after the v0.3.1 external acceptance record and have
not yet been externally re-accepted. If the dbt extra, profile, DSN, or live
database is absent, report `[PENDING LIVE PROFILE]`; do not simulate a pass.

Guarded Power BI commands:

- `/seshat-bi:powerbi-design` -- dashboard/page design (layout, visuals, and
  the slicer/filter rail) from approved metric contracts and committed
  semantic-model evidence only, with the read-only `seshat dashboard-planner`
  and `seshat dashboard-gaps` helpers run first.
- `/seshat-bi:powerbi-review` -- screenshot review, dashboard QA, blueprint
  validation (`seshat pbir-validate-blueprint`), and built-PBIR review.
- `/seshat-bi:powerbi-theme` -- theme JSON, palette, typography, filter-pane
  defaults, backgrounds, and canvas work (`seshat theme-gen` /
  `theme-compile` / `pbir-apply-theme` / `pbir-set-page-background`). Themes
  style the filter pane; what a filter binds to is a design decision, not a
  theme.
- `/seshat-bi:powerbi-format` -- formatting plans plus governed PBIR
  formatting/geometry (`seshat pbir-format-visual` / `pbir-set-geometry`).
- `/seshat-bi:dagster-doctor` -- read-only Dagster orchestration preflight
  (environment, pinned dagster, per-table gate state; never echoes credentials).
- `/seshat-bi:dagster-run` -- execute one governed orchestration job behind
  every gate, fail-closed; a halted run exits 3 and cites the named owner.
- `/seshat-bi:dagster-evidence` -- list orchestration runs or render a run's
  committed derived evidence (execution words, never a readiness `pass`).
- `/seshat-bi:powerbi-adopt` -- governed adoption of an existing PBIP project
  (`seshat adopt-pbip assess` / `scaffold` with the human-reviewed digest).

The canonical machine-readable command map is
`distribution/public-command-surface.yaml`. Core commands use the bare verb
name because Claude Code already namespaces them by plugin; the four names the
v0.2.0 acceptance pass validated remain available as deprecated aliases for
one release cycle (`/seshat-bi:seshat-init`, `/seshat-bi:seshat-check`,
`/seshat-bi:seshat-next`, `/seshat-bi:seshat-review`) and behave identically
to their bare forms. Commands beyond those four were added after the v0.2.0
acceptance pass and have not yet been externally re-accepted.

Slash commands, skills, and CLI verbs are three different surfaces: a slash
command is a reviewed prompt inside the agent session, a skill is routable
reference material the agent loads, and a CLI verb belongs to the separately
installed `seshat` terminal program. Commands interpret CLI output but never
replace or simulate it. Deliberately CLI-only capabilities (no slash wrapper)
include `seshat validate`, `drift`, `semantic-check`, `generate` (approved
metric contract to verified TMDL measure), `value-check` (live value proxy),
`evidence-pack`, `approvals`, `pack`, and `watch`: they need a live database
connection, write committed evidence artifacts, or are operator workflows that
must not be blurred into an agent prompt. List every verb with `seshat --help`.

An example guarded Power BI session:

```text
/seshat-bi:powerbi-adopt      # assess an existing PBIP project (read-only)
/seshat-bi:powerbi-theme      # generate and apply a theme via seshat theme-gen
/seshat-bi:powerbi-design     # design pages from approved metric contracts
```

## Agent-driven automation (MCP governor)

The plugins are deliberately skills-only, but the Python package ships an
optional **read-only MCP governor** so an agent can drive the readiness flow
programmatically with no memorized command names:

```text
pipx install "seshat-bi[mcp]"
claude mcp add seshat-governor -- seshat mcp --repo <workspace>
```

(For Codex, register the same `seshat mcp --repo <workspace>` stdio command as
an MCP server in its configuration.)

The governor exposes exactly six read-only tools: `seshat_get_status`,
`seshat_get_next_action`, `seshat_explain_blockers`,
`seshat_prepare_approval_request`, `seshat_run_static_check`, and
`seshat_export_evidence_pack`. The supported autonomous loop is: call
`seshat_get_next_action`, perform exactly that one action, re-run
`seshat_run_static_check`, and repeat. When the next action is a named-human
decision, `seshat_prepare_approval_request` packages it for review and the
loop **stops** -- no governor tool grants approval, advances a readiness
stage, writes a file, or emits a score. Without the `mcp` extra installed,
`seshat mcp` explains what to install instead of failing silently; the
`seshat next --format agent` CLI form remains the driver-free fallback for
the same loop.

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

**Isolation limitation.** The `v0.2.0` acceptance pass validated marketplace-add,
plugin install, namespaced-command discovery, governed CSV behavior, the
pressure/refusal test, update, uninstall, and workspace preservation. It did not
perform installation into a strict fresh Claude Code profile with no pre-existing
configuration; testing instead used a temporary local-scope workspace with user
settings excluded from the active session. Treat this as validated-with-a-noted-gap,
not a full clean-profile acceptance.

## Codex CLI and IDE

Codex uses a native `.codex-plugin/plugin.json` plus skills under
`skills/<name>/SKILL.md`. It does not use the Claude manifest or Claude slash
commands. This repository's catalog is `.agents/plugins/marketplace.json` and
points at the generated skills-only plugin in `integrations/codex/seshat-bi`.

Configure the repository marketplace and install from it:

```text
codex plugin marketplace add https://github.com/Kemetra/Seshat-BI
codex plugin add seshat-bi@seshat-bi-repository
codex plugin list
```

Marketplace add, plugin installation, `codex plugin list` discovery, governed
CSV behavior, pressure/refusal, marketplace upgrade, and plugin removal are all
verified at v0.3.1 (see the acceptance record). Start a new CLI thread and
invoke `$seshat-bi`, then the relevant knowledge skill (for the synthetic
source, `$bi-sql-knowledge`) -- the `$<skill-name>` form is the supported
invocation syntax and the one the acceptance classifier requires.

Codex deliberately exposes no slash commands; the same intents are reached
through its native discoverable skills. `$seshat-bi` covers initialization,
status, next-action, review, and PBIP-adoption guidance, `$dbt-workflows`
covers the governed dbt doctor/validate/plan/build/test/evidence sequence, and
`$powerbi-workflows` covers the guarded Power BI design, review, theme, and
formatting routes -- each backed by the same reviewed content the Claude
commands load.

The one Codex surface still **explicitly unverified** -- do not treat CLI
success as proof of it -- is the Codex IDE (**Settings > Plugins**) acceptance
path.

A workspace `AGENTS.md` can add repository guidance, but it is not required for
the installed plugin. Contributor validation uses the current Codex validator
against `integrations/codex/seshat-bi`; it must report a skills-only plugin with
no app, MCP server, connector, or hook.

Codex uses the term **marketplace** for configured repository catalogs. That is
not a claim of public OpenAI listing. The separate current public process is
OpenAI's plugin submission portal and review; it requires a distinct named-owner
decision. Older planning text that says “Plugins Directory” refers to that
separate process, not to repository installation.

## Governed first-use check

Copy the fictional `distribution/synthetic-retail/source.csv` into the fresh
project and ask the installed agent to inspect it. A valid response:

- identifies Source as the earliest stage;
- says `receipt_id` is not a proven row key because it repeats;
- does not repeat the email values;
- asks a named human to confirm row grain and PII publish policy;
- returns one profiling/decision action and stops before mapping or silver; and
- emits no readiness/confidence score.

If the agent invents a mapping, reveals a PII-shaped value, claims Mapping Ready,
authors silver SQL, or skips the named-human gate, mark that surface `blocked`.
Do not infer success from plugin discovery alone. This check has passed for
both Claude Code and the Codex CLI (each including a pressure/refusal
follow-up) at v0.3.1; only the Codex IDE path has not run it.

## Availability

| Surface | State |
|---|---|
| Python package | **available** on public PyPI; clean-install evidence recorded |
| Claude GitHub repository marketplace | **validated**: marketplace add, install, namespaced-command discovery, governed behavior, pressure/refusal, update, uninstall, workspace preservation (with the isolation limitation noted above) |
| Codex CLI repository marketplace | **validated** at v0.3.1: marketplace add, install, discovery, governed behavior, pressure/refusal, upgrade, removal, workspace preservation |
| Codex IDE (Settings > Plugins) | **unverified** |
| Claude public catalog | not submitted |
| OpenAI public plugin listing | not submitted |

On a failure, stop only the affected surface, preserve sanitized evidence, and
follow [release rollback](../operations/release-rollback.md). One available
surface never implies that the coordinated release is complete.
