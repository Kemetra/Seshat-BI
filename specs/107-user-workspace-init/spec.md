# Feature Specification: User workspace initializer (roadmap M3)

**Feature Branch**: `107-user-workspace-init`

**Created**: 2026-07-07

**Status**: **DRAFT — SPEC ONLY, NOT BUILT.** Authored autonomously (2026-07-07 overnight
run) and HELD for owner review before any implementation. This is net-new *runtime* —
per the overnight build discipline, net-new runtime waits for human eyes. Not gated on
the A-vs-B fork (`docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`): a workspace
scaffolder is packaging, not a capability verb. See
`docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md` M3.

**Input**: Roadmap M3 — "User Workspace Mode": a `seshat init-project <name>` command that
scaffolds a fresh, empty Retail-BI *project workspace* for a new user, distinct from the
existing `retail init` (which bootstraps `.seshat/` + fenced regions into an *already
existing* repo).

---

## Context and boundary (read first)

`retail init` today bootstraps governance scaffolding **into an existing repo** (writes
`.seshat/`, fenced `AGENTS.md`/`CLAUDE.md` regions). It does NOT create a fresh project
tree. M3 is the missing "new user, empty folder, `seshat init-project my-retail-bi`,
get a ready workspace" experience. This spec adds that WITHOUT changing `retail init`.

## User Scenarios & Testing

### User Story 1 — scaffold a fresh workspace (P1)
A new user runs `seshat init-project my-retail-bi`. The tool creates a new directory
`my-retail-bi/` containing the empty-but-correct workspace shape (below), a README
pointing at the readiness flow, and the same `.seshat/` governance bootstrap `retail init`
writes. Running it into a non-empty target refuses (no clobber) unless `--force`.

**Why P1**: this is the whole feature — the first-run container every other user-path
milestone assumes.

### Edge cases
- Target dir exists and is non-empty → refuse without `--force` (no data loss).
- Re-running into a workspace it created → idempotent (byte-identical, no duplicate rows).
- Path traversal / absolute-path target → validated, refused if outside CWD unless explicit.

## Requirements (FR)

- **FR-001** `seshat init-project <name> [--force]` creates `<name>/` with the workspace
  shape in the plan; deterministic and idempotent (re-run byte-identical).
- **FR-002** MUST NOT modify or duplicate the behavior of `retail init`; MAY reuse its
  `.seshat/` bootstrap internally.
- **FR-003** Refuses a non-empty target without `--force`; never clobbers user files.
- **FR-004** Creates only static scaffolding (empty dirs + template/README files). Writes
  NO source data, NO credentials, NO fabricated metric/readiness content. `.env` is
  git-ignored and never populated with real values.
- **FR-005** Pure local filesystem; no network, no DB, no external dependency
  (respects B1/B3 — no module-scope DB/network import).
- **FR-006** The generated workspace passes `retail check` on creation (clean baseline,
  no self-granted `pass`, no fabricated score).

## Out of scope
- Any capability *verb* (source profiling, mapping, evidence) — those are M6/M7/M9 and are
  gated on the A-vs-B ruling. M3 creates the empty container only.
- Publishing/distribution of the tool itself — that is M2/M11.

## Held-decision notes
This spec is written; it is NOT to be implemented until the owner reviews it. No `tasks.md`
is generated yet — task breakdown follows owner approval of this spec (avoids manufacturing
build momentum for unreviewed runtime).
