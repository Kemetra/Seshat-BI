# 0018 -- Un-park F016: the Power BI MCP execution adapter (terms of entry)

- **Date:** 2026-07-24 (drafted)
- **Status:** **Proposed -- NOT ratified.** This ADR takes effect ONLY when the
  owner replaces this line with an explicit ratification
  (`Accepted -- RATIFIED by <name> (owner) on <date>`). An agent must never
  edit this Status line (Principle V, never_self_grant_approval). Until
  ratification, F016 remains parked and every boundary below is inert: it
  authorizes nothing today.
- **Roadmap feature:** F016 (Power BI execution adapter) -- the deliberately-last,
  execution-only, `publish-capable` slot (constitution Principle II binding;
  `docs/roadmap/roadmap.md` lists it as the only parked feature). Issue #450 is
  the implementation plan; slices 1-4 (docs/contract, doctor/recommendation,
  safe config generation, mocked read-only preflight) ship WITHOUT this ADR
  because they mutate nothing. This ADR is the gate for slice 5 (approval-gated
  mutations) and the terms slice 6 (remote) must also honor.
- **Authority category (F024):** Execution Adapter, `publish-capable` --
  external, unforked, machine-local runtime (Microsoft's official Power BI MCP
  servers, public preview), consumed as a dependency, never vendored into the
  Python package (Principle II "Depend, Never Fork").
- **Context:** since 2026-06-25 the ratified preferred adapter for the F016 role
  is the official Microsoft Power BI MCP (`pbi-cli` demoted). Microsoft ships a
  local modeling server (stdio; Desktop / Fabric / PBIP-TMDL-on-disk; default
  readwrite, `--readonly` opt-in, `--skipconfirmation` bypass exists) and a
  remote query server (Fabric-hosted HTTP; published models; query-only). Both
  are PUBLIC PREVIEW with no published release. Microsoft's own docs warn that
  autonomous or misconfigured clients may perform destructive actions and that
  its safety flags are not standardized -- which is exactly why Seshat's
  approval layer must sit ABOVE the MCP rather than trusting the MCP's own
  flags. See `docs/integrations/pbi-mcp-adapter.md` (the three-MCP-senses
  disambiguation) and `templates/pbi-mcp-adapter-contract.md` (the contract this
  ADR arms).

## Decision (the terms of entry -- all binding together, none severable)

### 1. The park is lifted ONLY for one bounded adapter, only on ratification

Mutation of any Power BI artifact through an MCP runtime is permitted
exclusively through the F016 companion adapter bound by
`templates/pbi-mcp-adapter-contract.md` and a dedicated spec authored AFTER
this ADR is ratified. The DEFINE/CHECK core (`src/seshat/` rules,
`seshat check`) remains forbidden from driving any MCP mutation. Outside this
adapter, the pre-ADR posture stands unchanged.

### 2. Read-only is the resting state; every write is an armed exception

> The adapter MUST run the local server `--readonly` by default. A write-mode
> invocation MUST require, at invocation time, ALL of: (a) the target scope's
> `semantic_model_ready = pass` read via the committed gate-reader pattern
> (fail-closed on absent/unreadable state); (b) an explicit named-human
> `publish_ready` approval row in `approvals[]` whose note names the intended
> target; (c) a declared, allowlisted target artifact; (d) a clean or
> explicitly backed-up git working state. Absent ANY of these, the adapter
> refuses -- it never degrades to a warning.

### 3. `--skipconfirmation` is forbidden in every mode

Seshat's gate REPLACES the human-in-the-loop elicitation with a stronger,
recorded one; it never bypasses it. A configuration or invocation carrying
`--skipconfirmation` is a hard refusal, including in read-only mode and
including in tests.

### 4. Evidence is not approval (the governance hinge)

> A successful mutation emits a derived-evidence-only record (schema mirroring
> the dbt/Dagster run-evidence shapes: fixed authority, typed blockers, NO
> numeric score -- hard rule #9). It MUST NOT move `publish_ready` (or any
> stage) to `pass`. The readiness decision remains a named human's recorded
> act, before and after the write.

### 5. Post-write validation is a blocker, not a courtesy

Every mutation is followed by offline validation of the touched artifacts
(`seshat check` R-family; `seshat pbir-validate-bindings` where a report is in
scope; `value-check` where an expected value exists and a DB leg is available).
A failed post-write validation is a blocking finding with rollback guidance,
never a warning.

### 6. Preview drift is governed, not assumed away

Both official servers are public preview with no published release. The F032
compatibility matrix row remains the record of the supported range (UNKNOWN is
never compatible); updates ride Lane C (named-human review, never automerge,
per F031). A capability/flag/schema drift discovered at preflight is a blocker.

### 7. The remote server never becomes a gate input

Slice 6 (remote, query-only) additionally requires tenant setting + Build
permission + (for Generate Query) Copilot license, and MUST warn that RLS is
not enforced for Service Principal callers. Remote query results are advisory
context only -- never an input to any readiness stage.

### 8. Docs-first; this ADR ships no mutation code

Consistent with Principle VIII: ratifying this ADR authorizes AUTHORING the
slice-5 spec/plan/tasks under these terms; the mutation path ships only under
that spec's own tests and review.

## Consequences

- The kit gains a governed path to the last mile -- applying approved semantic
  changes to real Power BI targets -- without surrendering the approval spine
  to a preview tool's own safety flags.
- The constitutional boundary shifts from "no MCP execution, ever" to "MCP
  execution only via this bounded, read-only-by-default, doubly-gated adapter."
- The `.mcp.json.example` read-only default (PR #464) becomes load-bearing: a
  write-enabled example would now contradict a ratified decision, not just a
  preference.
- Slice-5 work cannot be scheduled until the owner ratifies; the park stays
  the honest public answer until then.

## Alternatives considered

- **Keep F016 parked indefinitely.** Honest but abandons the roadmap's own
  last-mile slot while the preferred official tooling now exists; rejected as
  the default -- though NOT ratifying this ADR preserves exactly this state,
  which is why ratification is the owner's call alone.
- **Trust the MCP's own confirmation prompts as the approval layer.** Rejected:
  Microsoft itself warns the flags are non-standard and client-dependent;
  Seshat's named-human approval spine is the system of record (Principle V).
- **Use pbi-cli as the execution path.** Rejected: demoted since 2026-06-25;
  the official MCP is the ratified preferred adapter for this role.
- **Vendor/fork the MCP runtime into the package.** Rejected: Principle II
  (external, unforked, independently upgradeable); also a 36MB+ preview binary
  is not shippable payload.
- **Let a successful publish advance `publish_ready`.** Rejected: evidence is
  not approval (decision 4; ADR 0009/0015 precedent).

## See also

- The implementation plan and slice map: issue #450 (slices 1-4 shipped
  read-only; slice 5 gated on this ADR; slice 6 gated on decision 7).
- The adapter contract this ADR arms: `templates/pbi-mcp-adapter-contract.md`.
- The three-MCP-senses disambiguation: `docs/integrations/pbi-mcp-adapter.md`.
- The compatibility record + update lane: `docs/operations/adapter-compatibility-matrix.md`
  (F032), `docs/operations/adapter-update-policy.md` (F031, Lane C).
- Park-lift precedent: ADR 0015 (PBIR authoring adapter lifts FR-008/FR-009).
- `.specify/memory/constitution.md` (Principles II, III, V, VIII, IX; hard rule #9).
