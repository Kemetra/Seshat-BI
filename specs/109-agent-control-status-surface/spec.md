# Feature Specification: Agent-control status surface (roadmap M4, under Option B)

**Feature Branch**: `109-agent-control-status-surface`

**Created**: 2026-07-07

**Status**: **BUILT.** Authored after the A-vs-B ratification (Option B, owner
2026-07-07, `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`). Under B this is
NOT a broad verb surface — it is the ONE deliberate CLI addition B allows: a small
machine-readable status surface. Implemented TDD on `feat/109-agent-control-status-
surface`: `src/retail/status_surface.py` (the pure, read-only projection),
`schemas/agent-status.schema.json` (the committed contract), `src/retail/cli/
commands/status.py` + the `status` subcommand (wired into the existing dispatch
table / parser, `main()` unchanged). All FRs verified; see `tasks.md`.

**Input**: Roadmap M4 "Agent Control Protocol" — a stable machine-readable way for an
agent/host to read readiness state (`status`, `next-action`, `blockers`).

---

## Context (Option B framing)

The *concept* of status/next-action already ships as skills (`readiness-viewer`,
`run-next-readiness`) and as fields in the readiness-status schema
(`docs/readiness/readiness-model.md`: `next_action`, `blocking_reasons`). Under B we do
NOT re-implement those as verbs. M4 adds only a **thin, stable JSON projection** of the
already-committed readiness state, so a non-agent host (CI, a wrapper) can read it
deterministically.

## Requirements (FR)

- **FR-001** A single command surface `retail/seshat status --format json` that emits the
  current readiness state (per-table `current_stage`, `evidence[]` presence,
  `blocking_reasons[]`, `next_action`) as validated JSON — a projection of the committed
  `readiness-status.yaml`, not a new computation.
- **FR-002** A committed JSON **schema** (`schemas/agent-status.schema.json`) the output
  validates against; the schema is the stable contract.
- **FR-003** Reuses the existing `Finding`/readiness data shapes (like `check --format
  json` already does via `runner.run_json`); introduces no new readiness *logic*.
- **FR-004** Read-only, no DB, no network, no score fabrication, never self-grants a stage
  (Principle V). Pure projection of committed evidence.
- **FR-005** The text default is unchanged / additive; `--format json` is the new path.

## Out of scope (Option B boundary)
- `seshat source profile`, `mapping review`, `evidence build` as CLI VERBS — B keeps those
  skill-driven (see specs 110–113). M4 is the sole sanctioned CLI addition.
- Any write/mutate command; any approval-granting command.

## Held-decision notes
Spec only, no `tasks.md`, no code — net-new runtime + a public JSON schema (a compatibility
contract) deserve owner review first. Coordinate with the shipped `cli/` package layout
(the `status` command would be a new `cli/commands/status.py`).
