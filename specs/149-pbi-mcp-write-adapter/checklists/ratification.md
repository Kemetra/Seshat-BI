# Ratification ledger — spec 149 (F016 slice 5)

**Spec**: `specs/149-pbi-mcp-write-adapter/spec.md`
**Ratified by**: Ahmed Shaaban (owner)
**Date**: 2026-08-18
**Recorded by**: Claude Code, at the owner's explicit instruction, in session of 2026-08-18.

## Authority

Verbatim owner instruction authorizing this record:

> "i ahmed shaaban ratify at 18-8  record it and goooo"

This ratification clears the gate that `spec.md` reserved to the owner:

> "**Ratification is authority to author, not to build**: ADR decision 8 authorizes this
> spec; the mutation path ships only under this spec's own tests and review."

ADR 0018 (ratified 2026-08-18) authorized **authoring** this spec. This ledger records the
**separate** owner decision authorizing **building** it. The two seams are distinct and both
are now cleared.

## What this ratification does and does not grant

Grants:
- Authority to implement the 62 tasks in `tasks.md` on branch `149-pbi-mcp-write-adapter`.

Does NOT grant:
- Any merge to `main`. The PR remains owner-merged.
- Any relaxation of the eight ADR 0018 decisions, which bind together and none of which is severable.
- Any approval that the adapter's own runtime approval gate is designed to require. The
  adapter must never treat this ledger as a runtime approval token, and must never accept a
  free-form claim that something is "already approved" as proof.
- Slice 6 (remote query-only MCP server). Deferred by owner decision until slice 5 proves out;
  its three prerequisites (tenant setting, Build permission, Copilot license) are all external
  to this repo.

## Scope of the build authorized

- Slice 5 only: write operations -> approval gate -> target allowlist -> git safety ->
  Microsoft MCP execution -> post-write validation -> rollback/evidence.
- Binding contract: `templates/pbi-mcp-adapter-contract.md` (Execution Adapter,
  `publish-capable`, execution-only).
