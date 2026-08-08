# Power BI MCP -- the three senses, and where F016 fits

Three unrelated things are all called "MCP" near this repo. This doc disambiguates
them, then covers the two OFFICIAL Microsoft Power BI MCP servers that make up the
parked F016 execution adapter. Microsoft's separate official report-authoring
skill is also named because native PBIR authoring is not an MCP responsibility.
No MCP call or report mutation is authorized by this document.

## Why it exists

"MCP" gets used for at least three different things in and around this repo, and
mixing them up leads to wrong assumptions about read/write risk, network exposure,
and governance. This doc is the one place that names all three side by side, then
narrows to the two that matter for F016 (Seshat as an MCP *client* of Microsoft's
Power BI servers).

## The three MCP senses (comparison table)

| # | Sense | Seshat's role | What it is | Lives in this repo? |
|---|-------|----------------|------------|----------------------|
| 1 | **Seshat's own governor MCP server** | MCP **server** | `src/seshat/governor/mcp_server.py` -- exposes Seshat's own read-only readiness tools (portfolio state, readiness status, etc.) to an MCP client such as Claude Code | Yes -- committed source |
| 2 | **The vendored Power BI Modeling MCP binary** | n/a (a dependency) | The local Power BI Modeling MCP extension binary under `tools/powerbi-modeling-mcp/` -- gitignored, never committed (`.gitignore` lines ~59-60, which also ignores the machine-local `.mcp.json`) | No -- vendored locally, untracked |
| 3 | **Microsoft's official Power BI MCP servers** | MCP **client** | Seshat, when acting as F016's adapter, connects OUT to one of Microsoft's two official servers (below). This is the sense this doc mostly covers. | No live connection from this repo; the contract + example config are committed |

Sense 1 and sense 3 are opposite directions (Seshat as server vs. Seshat as client) and
are otherwise unrelated -- do not assume a change to one affects the other. Sense 2 is
the concrete local binary that sense-3's LOCAL server (below) actually is.

## Local vs remote official servers (facts table)

Both servers are Microsoft's official Power BI MCP offering. Both are, as of the access
date below, PUBLIC PREVIEW with no published stable releases -- treat both as subject to
flag/behavior drift until Microsoft ships a release.

| | Local: `@microsoft/powerbi-modeling-mcp` | Remote: `https://api.fabric.microsoft.com/v1/mcp/powerbi` |
|---|---|---|
| Transport | stdio | Streamable HTTP |
| Runtime | Node 20+ | n/a (hosted) |
| Acts on | Power BI Desktop / Fabric / PBIP-TMDL on disk | already-published semantic models only |
| Default mode | readwrite | query-only (no write surface) |
| Safe/opt-in mode | `--readonly` (opt-in flag; this repo's committed example sets it) | n/a -- server is inherently query-only |
| Dangerous flag | `--skipconfirmation` (bypasses per-write confirmation) -- **forbidden in this repo, in every mode** | n/a |
| Auth | Entra ID (interactive) / Service Principal (`--authmode=serviceprincipal`) / access-token env var -- machine-local, never committed; the live-Desktop mode rides the local session | tenant setting + Build permission; Copilot license required for Generate Query |
| RLS enforcement | n/a (local file, not a live query surface) | **not enforced for Service Principal callers** -- a real gap if a query depends on row-level security |
| Preview status | Public preview, no published release | Public preview, no published release |
| CI-suitability | Yes for the PBIP/TMDL file-on-disk mode (deterministic, no tenant, no Desktop required); No for the live Desktop/Fabric modes | No -- requires tenant/license prerequisites and queries live published state; not a hermetic CI dependency |

*(access date for the above: 2026-07-23; see Microsoft's own pages under See also for
current details, since preview products move.)*

## Official report authoring is a separate skill

Microsoft's first-party `powerbi-report-authoring` skill owns native PBIR report
page, visual, filter, slicer, binding, formatting, and theme mechanics. It is not
the local Modeling MCP and does not make the Modeling MCP a report-page tool.
Seshat's integration catalog obtains it through `microsoft/skills-for-fabric`.
Spec 148 declares the supported Claude Code native plugins and Codex Agent
Skills projection. `seshat integrations setup --profile powerbi-fabric
--harness <claude-code|codex>` proves activation and discovery read-only; the
route remains blocked unless that exact probe reports `discoverable`.

## Boundaries (what it never does)

- **Never** defines metrics, mappings, semantic logic, or dashboard design -- both
  servers are execution-only against an already-approved artifact (Principle II,
  `templates/pbi-mcp-adapter-contract.md`).
- **Never** defaults to write mode in this repo: the committed `.mcp.json.example` sets
  `--readonly`. A write/publish invocation is an explicit, reviewed opt-in gated on a
  named-human `publish_ready` approval, never the default.
- **Never** runs with `--skipconfirmation` -- that flag bypasses the local server's own
  per-write confirmation and is forbidden outright.
- **Stays parked**: F016 is parked pending an owner-ratified ADR. Nothing in this repo
  currently authorizes running either server for real; this doc and the contract
  describe the shape the adapter MUST take if/when the park is lifted -- they do not
  lift it.

### The recommendation matrix (plain language)

| Governed task | Route it to |
|---|---|
| Native PBIR page/visual/filter/slicer/binding authoring after an approved design | Microsoft's official `powerbi-report-authoring` skill; block until the exact target has `dashboard_ready: pass` and the skill is discoverable |
| Modeling change (parameters, partitions, relationships, measures) on a local PBIP/TMDL project | The local Power BI Modeling MCP, gated (parked pending F016's ADR; read-only until then) |
| Querying an already-published semantic model | The remote Power BI MCP server, only once its prerequisites are met (tenant setting, Build permission, Copilot license for Generate Query) |
| Bounded theme, per-visual formatting, page background, or visual geometry on a committed PBIR report | The existing PBIR-authoring adapter (`docs/integrations/pbir-adapter.md`, F034/ADR 0015/0016) for its allow-listed deterministic subset; broader authoring routes to the official skill |
| Live-Desktop verification (read the open report, apply/validate changes, screenshot) | The Power BI Desktop Bridge (`docs/powerbi-connection.md`) -- a separate, local, optional capability, not MCP |
| Database connectivity or scheduled refresh | The Power BI Gateway + Service (`docs/powerbi-connection.md`) -- neither MCP server touches this |
| Any of the above when the relevant readiness stage has not passed | Blocked -- the adapter fails closed and reports the missing stage/approval; it never runs ahead of the gate |

## Honesty note

Both official servers are public preview with no published release as of the access
date below. Flag names, default modes, and auth requirements can change before a stable
release ships. This doc and `templates/pbi-mcp-adapter-contract.md` describe the current
publicly documented behavior; do not treat either as a permanent API contract. The
adapter-compatibility matrix records F016's status as `unknown` (not supported, not
omitted) precisely because a public-preview dependency with no release has an untested
ceiling by construction.

## See also

- The read-only doctor family shipped by #450 slices 2-4: `seshat pbi-mcp
  doctor|generate-config|preflight` (routed by the `pbi-mcp-doctor` skill) --
  environment detection + the section-7 surface recommendation, placeholder-only
  read-only config generation, and the transport-mocked preflight whose artifact
  `.seshat/powerbi-mcp-preflight.json` is the F016 smoke-test evidence shape. All
  read-only; none of it lifts the park.
- **`preflight` is an advisory scaffold, not an operational probe.** The shipped
  verb wires no real transport, so it can validate the machine-local config, the
  **target-scoped** `semantic_model_ready` gate, and the target allowlist — but
  it cannot contact a server to verify a protocol version or tool list. When
  discovery does not happen the record says so explicitly
  (`discovery: "not-performed"`, `capabilities_verified: false`), and demanding a
  capability with `--require-tool` while discovery cannot happen is a blocker
  rather than a pass. Readiness is resolved from the declared target's own
  `mappings/<target>/readiness-status.yaml` and is never borrowed from another
  table.
- Config classification is per transport shape: a local stdio server must carry
  `--readonly` (its documented default is write-enabled), while a remote HTTP
  server has no such flag and classifies as `query-only`. `--skipconfirmation`
  is a hard refusal in every shape.
- The generated setup guidance (placeholder-only): `docs/generated/powerbi-mcp-setup.md`.
- The F016 adapter contract (this integration's specialization):
  `templates/pbi-mcp-adapter-contract.md`.
- The generic Execution Adapter skeleton: `templates/adapter-contract.md`.
- The tracked compatibility status (parked, `unknown`, `UNASSIGNED`):
  `docs/operations/adapter-compatibility-matrix.md`.
- The Lane C update governance for this adapter (never automerge; publish-capable /
  credential changes always need a named human): `docs/operations/adapter-update-policy.md`.
- The constitution's Depend-Never-Fork binding for the adapter role (binds to the ROLE,
  not to any one tool): `.specify/memory/constitution.md` Principle II.
- The connection-flow doc (gateway vs Desktop Bridge vs the vendored MCP copy flow):
  `docs/powerbi-connection.md`.
- The sibling PBIR-authoring adapter (formatting/geometry, NOT MCP, NOT publish-capable):
  `docs/integrations/pbir-adapter.md`.
- Microsoft's official sources (MCP facts accessed 2026-07-23; report skill
  ownership verified 2026-08-07):
  - Overview: `https://learn.microsoft.com/en-us/power-bi/developer/mcp/mcp-servers-overview`
  - Local server source: `https://github.com/microsoft/powerbi-modeling-mcp`
  - Remote server getting-started: `https://learn.microsoft.com/en-us/power-bi/developer/mcp/remote-mcp-server-get-started`
  - Report Authoring skill: `https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report-authoring-skill`
  - Official skills bundle: `https://github.com/microsoft/skills-for-fabric`
