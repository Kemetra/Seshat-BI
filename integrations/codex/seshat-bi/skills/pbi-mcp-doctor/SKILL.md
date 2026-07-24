---
name: pbi-mcp-doctor
description: >-
  Use when a user asks whether or how to wire Microsoft's official Power BI
  MCP servers into a Seshat BI workspace: run the read-only environment
  doctor, map a task to the governed Power BI surface, generate a safe
  read-only config template, or run the mocked read-only preflight.
---

# Power BI MCP doctor (read-only)

Read `../../portable-operating-contract.md` before acting. Use only the
installed `seshat pbi-mcp` verbs; never launch an MCP server directly, never
edit `.mcp.json` by hand when the generator can produce it, and never treat
any output of this family as an approval. F016 (the Power BI execution
adapter) is PARKED: no mutation path exists anywhere in this family.

## Fixed workflow

1. Map the user's task to the governed surface, read-only:

   `seshat pbi-mcp doctor --intent <task> [--json] [--write-advisory]`

   `--intent` is a closed vocabulary: `model-edit`, `published-query`,
   `report-formatting`, `desktop-verification`, `db-connectivity`,
   `ci-validation`, `sensitive-production`. Report the recommendation, its
   missing prerequisites, and the next HUMAN step verbatim. A blocked
   recommendation (exit 2) names the gate -- stop there; never route around
   it. `--write-advisory` records the result once at
   `.seshat/powerbi-mcp-recommendation.yaml` (write-once; it refuses to
   overwrite) and is never a side effect.

2. Generate config only through the safe generator:

   `seshat pbi-mcp generate-config [--transport local|remote|both] [--setup-doc] [--out <path>]`

   Output is placeholder-only and read-only (`--readonly`); it is
   secret-scanned before emission and refuses to overwrite an existing file.
   If it refuses because output would be secret-shaped, stop and report --
   never bypass the scan by writing the file yourself.

3. Preflight the runtime read-only (graceful when absent):

   `seshat pbi-mcp preflight [--target <t> --allow <t>] [--require-tool <name>] [--json] [--write-artifact]`

   It refuses a write-mode config, hard-refuses `--skipconfirmation`
   anywhere, fails closed while `semantic_model_ready` has not passed, and
   reports "runtime not present -- preflight skipped" when no MCP runtime is
   installed (that is a graceful skip, exit 0, not a failure).
   `--write-artifact` records the result at
   `.seshat/powerbi-mcp-preflight.json` -- derived evidence only, the shape
   the adapter-compatibility matrix's F016 row references.

## The recommendation matrix in plain language

- Create or modify a PBIP/TMDL semantic model -> the official LOCAL Power BI
  Modeling MCP, and only when `semantic_model_ready` has passed; read-only
  until the owner-ratified ADR lifts the F016 park.
- Query an already-published semantic model -> the official REMOTE Power BI
  MCP server, only once its tenant-side prerequisites are verified (tenant
  preview setting, Build permission, Copilot license for Generate Query);
  otherwise stop and name the missing prerequisite.
- Theme, page layout, geometry, or visual formatting -> the existing
  PBIR-authoring adapter (`powerbi-workflows` skill), not MCP at all.
- Live Desktop verification or screenshots -> the Power BI Desktop Bridge, a
  separate optional integration; never in CI.
- Database connectivity or scheduled refresh -> the Power BI Gateway +
  Service; neither MCP server touches these.
- Semantic readiness not passed -> everything Power BI-mutating is BLOCKED;
  report the gate and the named next human step.
- CI / Linux / no Desktop -> deterministic PBIP/TMDL file validation only;
  Power BI Desktop is never required; an unavailable remote server is a
  graceful skip.
- Sensitive / production environment -> read-only plus stricter named-human
  approval; never a Service-Principal query path where row-level security
  matters.

## How to read the advisory records

- `.seshat/powerbi-mcp-recommendation.yaml` -- detected facts + one
  categorical recommendation. Its `generated_note` is binding: it grants
  nothing.
- `.seshat/powerbi-mcp-preflight.json` -- `authority` is fixed at
  `derived-evidence-only` and `readiness_effect` at `none; named-human
  approval required`. `status: skipped` means the runtime was absent;
  `blocked` lists categorical blockers by id. There is no numeric score and
  never will be.

## What this family will NEVER do

- Never mutate a semantic model, a report, or any file other than the two
  advisory records above (each behind an explicit flag).
- Never grant, imply, or record an approval; never advance a readiness
  stage; never emit a numeric score.
- Never contact a live tenant, database, or network endpoint -- the real MCP
  transport is deliberately absent in this slice.
- Never run or recommend `--skipconfirmation`, `--readwrite`, or any
  write-mode invocation; mutations are slice-5 territory behind an
  owner-ratified ADR and a named-human `publish_ready` approval.
- Never write a credential, tenant id, hostname, or user path into any
  generated output -- the secret scan refuses, and the refusal is final.
