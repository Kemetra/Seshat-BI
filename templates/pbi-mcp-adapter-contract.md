<!--
=============================================================================
 pbi-mcp-adapter-contract.md  --  the F016 specialization of templates/adapter-contract.md
=============================================================================
 Specializes the GENERIC Execution Adapter contract for the Power BI Modeling
 MCP integration (F016). Authored as Slice 1 of issue #450 (docs and contract
 only). ADR 0018 was RATIFIED 2026-08-18, so the park is LIFTED and these terms
 are BINDING -- but ratification armed the terms, not a build: no MCP MUTATION
 is authorized by this file alone. The write path ships only under
 specs/149-pbi-mcp-write-adapter (slice 5) with its own tests and review.

 Read alongside: docs/integrations/pbi-mcp-adapter.md (the three-MCP-senses
 disambiguation), docs/operations/adapter-compatibility-matrix.md (F016's
 tracked status row), .specify/memory/constitution.md Principle II
 (Depend, Never Fork -- binds the adapter ROLE, not any one tool).
=============================================================================
-->

# Adapter Contract -- Power BI Modeling MCP (F016)

- **Authority category:** Execution Adapter / publish-capable (park LIFTED 2026-08-18)
- **Connectivity level:** `publish-capable` *(the strongest it uses; also DB/host-adjacent via the on-disk PBIP/TMDL it edits and, for the remote server, the published-model query path)*
- **Product layer:** `6` *(Publish -- see docs/roadmap/roadmap.md; orthogonal to category)*
- **Roadmap feature:** `F016`  **On-disk spec:** `specs/149-pbi-mcp-write-adapter` (slice 5)
- **Owner:** `UNASSIGNED`
- **Status:** `Authorized, not yet built` -- ADR 0018 was RATIFIED by Ahmed Shaaban (owner)
  on 2026-08-18, so the park is LIFTED and this contract's terms are BINDING. Ratification
  armed the terms, not a build: the mutation path ships only under `specs/149-*`'s own tests
  and review, so **no write path exists in the shipped package today**. The read-only family
  (`pbi-mcp doctor|generate-config|preflight`) is what currently runs.

## What it does (one line)

> Drives Microsoft's official Power BI Modeling MCP server (local, stdio) or the
> remote Power BI MCP server (published-model queries) to materialize or query an
> already-approved Power BI semantic model -- never to author metrics, mappings, or
> semantic logic itself.

## Gate it is DOWNSTREAM of

An adapter only runs after a readiness gate has passed. Name the stage and the approval
it requires; the adapter fails closed if that approval/evidence is absent.

- **Gated on stage:** `Semantic Model Ready = pass`
- **Required approval / evidence:** a named-human `publish_ready` approval recorded for
  any mutating (write/publish) call. Read-only/query calls still require Semantic Model
  Ready = `pass`; they do not additionally require `publish_ready`.
- **Fail-closed behavior:** refuses to run and reports the missing stage/approval as a
  blocker. It never infers or self-grants the approval, and never runs ahead of the gate
  because a human is "probably fine with it."

## Boundaries it CROSSES (connectivity)

Enumerate EVERY external boundary this adapter touches. `publish-capable` implies the
publish gate applies. Record the strongest connectivity above; list all here.

- Opens a local stdio process to the official Power BI Modeling MCP, invoked through
  `npx` as an external, unforked, independently upgradeable dependency, which in turn
  reads/writes the local Power BI Desktop / Fabric / on-disk PBIP-TMDL project
  (`local-file` + `local-service` boundary).

  > **Corrected 2026-08-18.** This clause previously described a *vendored* binary at
  > `tools/powerbi-modeling-mcp/`. That contradicted ADR 0018, which rejects vendoring
  > outright (the preview binary is not shippable payload, and Principle II requires
  > external consumption), and it described an execution shape slice 5 does not use:
  > `pbi_mcp_adapter/runner.py` invokes `npx --yes @microsoft/powerbi-modeling-mcp`.
  >
  > **Still open, owner-gated:** the `VENDORED_RUNTIME_DIR` constant at
  > `src/seshat/pbi_mcp/detect.py` remains live and feeds
  > `DetectedFacts.vendored_runtime`, which the shipped `seshat pbi-mcp doctor` reports
  > in both its text and `--json` output. Retiring it therefore changes slices 1-4
  > behaviour, so it is deliberately NOT removed here (spec 149, T053).
- For the remote server: opens a Streamable HTTP connection to the published Power BI
  MCP endpoint, which queries an already-published semantic model in the Power BI
  Service (`external-service-connected` boundary; query-only, no local file writes).
- Any call that would materialize/publish a semantic model change is `publish-capable`
  and MUST clear the publish gate above.

## Approved artifact it MATERIALIZES / PUBLISHES

The definition MUST already exist in Core Authority. The adapter executes it; it does not
author it.

- Materializes an already-approved PBIP/TMDL semantic model edit (e.g. a parameter
  definition or partition repoint already decided upstream -- see
  `docs/powerbi-connection.md`'s parameterize-before-commit flow).
- Publishes an already-approved semantic model to the Power BI Service (mutating calls
  only, gated on `publish_ready`).
- Queries an already-published semantic model (remote server, read-only; no publish
  gate needed, but still downstream of Semantic Model Ready).

## Derived run-evidence it WRITES

An adapter may write a RUN RECORD (what ran, when, with what result) as derived evidence.
This is never a new truth or approval.

- A run record (tool called, mode -- readonly/readwrite --, target, timestamp, result)
  committed as derived evidence, redacted of any host/tenant/credential value.

## Secrets handling (Principle IX)

- **Credentials:** Entra ID (interactive) / Service Principal / access-token env var, all machine-local (never committed); the live-Desktop mode rides the local session. No separate DSN.
  Any local launcher config lives in the git-ignored `.mcp.json` (copied from the
  committed `.mcp.json.example`), never inline in a tracked file. The remote server's
  auth (tenant setting + Build permission + Copilot license for Generate Query) is
  configured outside this repo.
- **Committed example only:** `.mcp.json.example` (placeholder command path, no real
  host/tenant/user path), read-only (`--readonly`) by default.

## Forbidden operations (the matrix says NO)

These hold for EVERY Execution Adapter regardless of connectivity level:

- MUST NOT define metrics, mappings, semantic logic, or dashboard design (execution-only).
- MUST NOT create truth or grant approval / move a stage to `pass` (named-human / Core
  Authority only).
- MUST NOT execute when its required approval/evidence is absent -- it fails closed.
- MUST NOT publish unless its connectivity level is `publish-capable` AND `publish_ready`
  is recorded.
- MUST NOT emit a numeric / maturity / confidence score (hard rule #9).
- MUST NOT commit real hostnames / DSNs / credentials (Principle IX).
- MUST NOT run the local server with `--skipconfirmation` -- that flag bypasses the
  server's own per-write confirmation and is forbidden outright, in every mode.
- MUST NOT default to `--readwrite` -- the committed example and every invocation this
  contract authorizes default to `--readonly`; a write mode is an explicit, reviewed
  opt-in gated on `publish_ready`, never the default.
- MUST NOT rely on the remote server for RLS-sensitive access under a Service Principal
  -- the remote server does not enforce RLS for Service Principal callers, so any query
  that depends on row-level security MUST go through a path that does enforce it.

## How it handles a missing definition or approval

When the artifact it would execute is undefined, or the gate it is downstream of is not
`pass`, the adapter SURFACES it as a blocker and fails closed -- it never invents the
definition, self-approves, or executes past the missing gate (Principle V; stop-and-ask).
The park is LIFTED (ADR 0018 ratified 2026-08-18), so a missing gate or approval is no longer
reported as "parked" — it is reported as the specific missing authority (stage not `pass`,
approval absent or not naming the target, operation not bound to an approved definition, target
not allowlisted, or an unsafe working tree). Until the slice-5 mutation path ships under
`specs/149-pbi-mcp-write-adapter`, a WRITE invocation is refused because no write path is
built, not because F016 is parked. Read-only invocations run as they always have.

## See also

- The normative reference: `docs/architecture/product-modules.md`.
- The seam (Adapter vs Module): `docs/architecture/core-vs-modules-and-adapters.md`.
- The generic skeleton this specializes: `templates/adapter-contract.md`.
- The three-MCP-senses disambiguation: `docs/integrations/pbi-mcp-adapter.md`.
- The tracked status row (`unknown`, `UNASSIGNED` -- both correct: the servers are public
  preview with no published release to pin, and `unknown` is never compatible):
  `docs/operations/adapter-compatibility-matrix.md`.
- The ratified authority and its eight binding terms:
  `docs/decisions/0018-unpark-f016-power-bi-mcp-execution-adapter.md`.
- The Lane C update governance for this adapter: `docs/operations/adapter-update-policy.md`.
- The constitution's Depend-Never-Fork binding for the adapter role:
  `.specify/memory/constitution.md` Principle II.
- The committed example launcher config (read-only default): `.mcp.json.example`.
