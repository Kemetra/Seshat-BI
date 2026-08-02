# @kemetra/seshat-bi

The **Seshat BI agent skills bundle** for Claude Code — 21 skills, the slash
commands, and the reviewed public Knowledge Bases, packaged for npm.

Seshat BI is an agent-first Retail BI readiness system. It answers one question
safely — *is this retail source ready to become trusted Power BI analytics?* —
through a governed seven-stage readiness flow (Source → Mapping → Silver → Gold
→ Semantic Model → Dashboard → Publish Ready), static and live governance gates
over SQL/TMDL/PBIR/DAX, and metric contracts that stop work when business
meaning is unresolved. Readiness is never a faked score: it is status +
evidence + blocking reasons held by a gate.

## Read this first

**This package ships content, not a runtime.** It contains Markdown, JSON, and
YAML. It executes nothing, has zero dependencies, and runs no install scripts.

**The `seshat` CLI is a Python program and is NOT installed by npm.** It lives
on PyPI as [`seshat-bi`](https://pypi.org/project/seshat-bi/). The bundle's
`mcp-servers.json` declares a `seshat-governor` MCP server whose command is that
CLI, so the governor tools stay unavailable until you install it:

```sh
pipx install "seshat-bi[mcp]"
```

Without it the server fails **closed** with a named install hint — it never
degrades silently or simulates a governor.

## Which install do you actually want?

For most people the answer is **not npm**. Use the Claude Code marketplace:

```
/plugin marketplace add Kemetra/Seshat-BI
/plugin install seshat-bi@seshat-bi-marketplace
```

That is the supported path and it self-updates. This npm package exists for
programmatic consumers — build tooling, vendoring the bundle into another
distribution, or diffing skill content across versions — where reaching for a
tarball from the npm registry is more convenient than cloning the repository.

## Install

```sh
npm install @kemetra/seshat-bi
```

## Usage

```js
import {
  bundlePath,
  bundleManifest,
  cliInstallCommand,
} from "@kemetra/seshat-bi";

console.log(bundlePath);              // .../integrations/claude-code/seshat-bi
console.log(bundleManifest.version);  // the generated bundle version
console.log(cliInstallCommand);       // pipx install "seshat-bi[mcp]"
```

The bundle manifest is also importable directly:

```js
import manifest from "@kemetra/seshat-bi/bundle" with { type: "json" };
```

## What is inside

| Directory | Contents |
|---|---|
| `skills/` | 21 agent skills (readiness verbs, dbt and Power BI routing, knowledge bases) |
| `commands/` | `/seshat-bi:*` slash commands |
| `knowledge/` | Reviewed public knowledge (SQL, DAX, retail KPI, analyst judgment) |
| `templates/` | Scaffolding templates |
| `contracts/`, `design/` | Contract and design references |

`bundle-manifest.json` is the authored record of what ships, with per-file
digests and the source revision it was generated from.

## Versioning

The version **mirrors the PyPI release** (`0.8.1` here matches
`seshat-bi==0.8.1`). The bundle is generated from the repository at that
release, so an npm version and a PyPI version with the same number describe the
same content.

## Governance boundaries

These hold for the shipped skills regardless of how you install them:

- Never self-grant an approval — approvals are named-human actions.
- Never fabricate readiness — status + evidence + blockers, never a number.
- No silver work before the mapping gate clears; no dashboard work before
  metric contracts are approved.

## Links

- **Repository:** <https://github.com/Kemetra/Seshat-BI>
- **Python CLI:** <https://pypi.org/project/seshat-bi/>
- **Issues:** <https://github.com/Kemetra/Seshat-BI/issues>

Apache-2.0 © Ahmed Shaaban
