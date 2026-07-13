# Contract: Generated Codex Bundle

**Contract ID**: `GXB-1`
**Planned root**: `integrations/codex/seshat-bi/`
**Requirements**: FR-024--FR-029, FR-044, SEC-003

## Purpose

Produce one Codex-native, skills-only plugin from reviewed templates and the same public allowlist used by Claude. Do not translate Claude manifest fields by analogy.

## Required bundle shape

```text
integrations/codex/seshat-bi/
├── .codex-plugin/
│   └── plugin.json
├── README.md
├── LICENSE
├── skills/
│   ├── seshat-bi/SKILL.md
│   ├── bi-sql-knowledge/SKILL.md
│   ├── bi-dax-knowledge/SKILL.md
│   ├── bi-python-knowledge/SKILL.md
│   ├── bi-bigdata-knowledge/SKILL.md
│   └── retail-kpi-knowledge/SKILL.md
├── knowledge/
│   └── <allowlisted canonical projections>
└── bundle-manifest.json
```

Each skill follows the supported `skills/<name>/SKILL.md` structure and has valid `name`/`description` frontmatter. The router is explicitly invocable as `$seshat-bi`; knowledge skills may also be explicitly invoked by name.

## Repository compatibility

- Root `AGENTS.md` remains the operating contract for work inside Seshat_BI and must remain compatible with Codex root-to-current-directory instruction discovery.
- Repository-scoped authoring skills remain discoverable under `.agents/skills/<skill>/SKILL.md`.
- Neither `AGENTS.md` nor `.agents/skills/` is treated as the installed plugin payload.
- In a fresh external workspace with no `AGENTS.md`, the installed `$seshat-bi` skill supplies the portable guarded workflow.

## Repository catalog

`.agents/plugins/marketplace.json` is the repository-scoped Codex plugin catalog. It MUST:

- use the current Codex catalog schema and terminology;
- point to `./integrations/codex/seshat-bi` relative to repository root;
- include required installation/authentication policy and category fields;
- carry synchronized visible metadata; and
- stay distinct from OpenAI's public plugin submission, review, and listing process.

Documentation may call this file/CLI source a repository marketplace or catalog because current tooling uses `codex plugin marketplace ...`. It MUST call OpenAI's public process **public plugin submission/review/listing** unless official terminology changes and the contract is deliberately updated.

## Plugin behavior

1. Package skills only for Public Beta; no app, MCP server, connector, hook, or remote service is required.
2. `$seshat-bi` MUST orient from readiness evidence and return one truthful next action or blocked stop.
3. It MUST enforce the same Seshat hard stops as the Claude bundle.
4. It MUST load only task-relevant knowledge progressively; the five skills remain separately identifiable to avoid overloading initial context.
5. All knowledge/resource references MUST resolve inside the plugin root.
6. A missing Python package or live DSN MUST produce enable/defer guidance, not a repository-clone instruction or fabricated pass.

## Manifest requirements

`.codex-plugin/plugin.json` MUST use the current official Codex schema. At minimum the planned skills-only manifest has stable kebab-case name, synchronized version, public description, and a `skills` path. Only the manifest belongs in `.codex-plugin/`. Claude-only `commands`, manifest keys, or marketplace assumptions are prohibited.

The release implementation MUST run the current official validator/scaffolding check rather than freezing this planning document as an eternal schema definition.

## Generated provenance

`bundle-manifest.json` follows the same provenance rules as the Claude manifest but uses target `codex`. The two bundles may differ in template files and destinations; their allowlisted canonical content digests must agree when the same transform is declared.

## Installation and invocation contract

- Add/resolve the canonical repository catalog using the current `codex plugin marketplace` flow.
- Install the `seshat-bi` plugin through supported Codex CLI/desktop behavior.
- Verify skill discovery in Codex CLI and IDE.
- Explicitly invoke `$seshat-bi` and at least one exported knowledge skill.
- Restart/refresh the relevant host after plugin updates as current product behavior requires.

Exact syntax and host-version support MUST be rechecked at implementation/release time.

## OpenAI public plugin boundary

Repository installation does not imply an OpenAI public listing. Submission is a separate owner-approved process. Current planned evidence includes:

- eligible submitter with Apps Management Write access;
- verified developer/business identity matching listing details;
- plugin listing, support, privacy, terms, availability, and policy attestations;
- bundled-skill inventory, starter prompts, and acceptance tests;
- review result and any requested remediation.

## Prohibited content and references

- Claude manifest copied/renamed as Codex;
- reliance on a Seshat-specific workspace `AGENTS.md`;
- parent/absolute/development-repository paths;
- undeclared app/MCP/connector/hook/network capability;
- secrets, real PII, client material, or local settings;
- hand-edited generated knowledge;
- the term “public marketplace” or “Plugins Directory” for OpenAI's submission/review process unless official terminology supports it at execution time.

## Contract tests

- Validate catalog, plugin manifest, and every `SKILL.md` with current Codex tooling/schema.
- Compare bundle tree with allowlist/template provenance.
- Resolve references from a copied plugin root with the development repository unavailable.
- Discover and invoke skills in clean Codex CLI and IDE sessions.
- Run the External Codex Acceptance Contract.
- Confirm no extra app, MCP, connector, hook, or executable capability is activated.
