# Contract: Generated Claude Bundle

**Contract ID**: `GCB-1`
**Planned root**: `integrations/claude-code/seshat-bi/`
**Requirements**: FR-019--FR-023, FR-043, SEC-003

## Purpose

Produce one cache-safe, public-installable Claude Code plugin from reviewed templates and allowlisted canonical knowledge. A public user must not need the Seshat development checkout or workspace guidance.

## Required bundle shape

```text
integrations/claude-code/seshat-bi/
├── .claude-plugin/
│   └── plugin.json
├── README.md
├── LICENSE
├── skills/
│   ├── seshat-bi/SKILL.md
│   └── <exported-public-skill>/SKILL.md
├── commands/
│   ├── seshat-init.md
│   ├── seshat-next.md
│   ├── seshat-check.md
│   └── seshat-review.md
├── knowledge/
│   └── <allowlisted canonical projections>
└── bundle-manifest.json
```

Only `plugin.json` belongs inside `.claude-plugin/`. Skills and commands remain at plugin root.

## Root marketplace

- `.claude-plugin/marketplace.json` at repository root is the sole public Claude marketplace manifest.
- It contains one `seshat-bi` entry whose Git subdirectory/source resolves to this plugin root.
- A nested `integrations/claude-code/.claude-plugin/marketplace.json` MUST NOT compete as a second public source.
- Marketplace and plugin versions MUST satisfy the Version Synchronization Contract.

## Plugin behavior

1. `seshat-bi` is the public router and carries the minimum portable operating contract.
2. The plugin MUST orient from the earliest non-pass readiness stage, cite evidence/blockers, and return exactly one next action or one blocked stop.
3. It MUST enforce named-human approval gates, no silver before Mapping Ready, no dashboard before metric contracts, no Power BI execution, no fabricated readiness score, and graceful live-boundary deferral.
4. The skill/commands MAY invoke installed `seshat`/`retail` helpers, but MUST detect and explain a missing Python package rather than refer to repository-local modules.
5. Every knowledge reference MUST resolve inside the installed plugin root.
6. The plugin MUST operate when the workspace has no `AGENTS.md` and no `CLAUDE.md`.
7. A workspace's own applicable instructions remain authoritative; the plugin does not overwrite them.
8. The plugin MUST NOT declare an MCP server, hook, connector, network service, or executable unless separately added to and reviewed under this contract. The Public Beta default is none.

## Manifest requirements

The Claude manifest uses only currently supported Claude fields. At minimum it carries stable name, synchronized version, public description, author/publisher, repository/homepage, license, and component paths as required by the current schema. Codex-only fields are prohibited.

## Generated provenance

`bundle-manifest.json` MUST contain:

- schema/exporter version;
- target `claude`;
- plugin/version/source revision;
- sorted entries with source/template ID, destination, transform, and SHA-256 digests;
- one digest over the canonicalized manifest payload.

No generation timestamp or machine path is included in the deterministic payload. Runtime acceptance timestamps live in evidence, not the bundle.

## Installation contract

The documented public journey is conceptually:

1. Add `ahmed-shaaban-94/Seshat_BI` as a Claude Code marketplace.
2. Install `seshat-bi` from that marketplace.
3. Reload/refresh after version changes so the cache selects the intended version.
4. Discover the Seshat skill/commands in a fresh external workspace.

Exact commands MUST be revalidated against the supported Claude Code version at implementation/release time.

## Prohibited content and references

- `../` references leaving the plugin root;
- absolute development paths;
- instructions to clone Seshat_BI for normal use;
- dependencies on root `AGENTS.md`, `CLAUDE.md`, `.env`, tests, or specs;
- credentials, real PII, client material, or approval drafts;
- hand-edited generated knowledge;
- undeclared hooks, MCP servers, connectors, or binaries.

## Contract tests

- Validate root marketplace and plugin manifest with current Claude tooling/schema.
- Resolve every component and Markdown link from a copied plugin root after hiding the development repository.
- Compare every file with the allowlist/template manifest.
- Regenerate twice and compare paths/digests.
- Run the External Claude Acceptance Contract.
- Uninstall/update the plugin and confirm documented cache behavior does not select stale knowledge.
