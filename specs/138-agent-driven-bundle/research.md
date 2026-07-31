# Phase 0 Research: Agent-driven bundle completion

**Feature**: 138-agent-driven-bundle | **Date**: 2026-07-31

Five unknowns were extracted from the Technical Context and the spec's
Assumptions. R1 is the only one resting on a source outside this repository and
is therefore the only one that can block User Story 1.

---

## R1 — Do both harnesses start a plugin-declared server automatically?

**Decision**: Declare the governor as a bundled server on both harnesses, using a
single shared source file projected into each bundle root, with the harness
manifest pointing at it.

**Rationale**: Each platform's current published reference describes the same
shape — a server configuration file at the plugin root, referenced from the
plugin manifest, with servers started when the plugin is enabled. One platform
additionally permits an inline declaration in the manifest; the file form is
chosen because it is the intersection of both, keeping one canonical source
rather than two divergent manifest bodies.

**Alternatives considered**:
- *Inline in each manifest*: supported on one harness only; would fork the
  declaration into two hand-maintained copies. Rejected — violates "one canonical
  source" and Principle II.
- *Keep manual registration*: the status quo. Rejected — it is the specific
  defect User Story 1 exists to remove.
- *Ship no server, serve procedure through a tool*: rejected during design; it
  re-centralises on the CLI that Option B ratified away from and forfeits the
  agent's own skill-index routing. Recorded in the spec's Assumptions.

**OPEN — must be closed before US1 implementation**: this is the one conclusion
drawn from external platform documentation rather than repository evidence. The
spec requires it be re-confirmed against the exact harness versions named in the
support matrix, and a negative result re-scopes User Story 1 rather than
prompting a workaround. Confirmation is the first task of US1, not a parallel
activity.

---

## R2 — How does a plugin-launched governor resolve the workspace?

**Decision**: Declare the server with no explicit repository argument and rely on
the existing default, subject to a startup confirmation that the resolved root is
the user's workspace and not the plugin directory.

**Rationale**: `seshat mcp` already accepts `--repo` with a default of `.`
(`src/seshat/cli/parser.py:365`), so a plugin-launched server inherits whatever
working directory the harness starts it in. That is the correct behaviour *if*
the harness starts plugin servers in the user's workspace. Passing an explicit
path is not possible from a static declaration: the plugin knows its own
installed location, not the workspace, so any literal path would be wrong.

**Alternatives considered**:
- *Pass the plugin root as the repository*: actively harmful — the governor would
  read the plugin's own files and report readiness for the wrong tree.
- *Require the user to pass a path*: reintroduces the manual step US1 removes.
- *Add a workspace-discovery flag to the CLI*: a new CLI surface, which Option B
  forbids, and unnecessary if the default already resolves correctly.

**Verification required**: the resolved root must be observed, not assumed. If a
harness starts servers in the plugin directory, US1 needs a discovery mechanism
and this decision changes — which is why it is verified alongside R1 before
implementation.

---

## R3 — Is the absent-extra failure visible to the user?

**Decision**: Rely on the existing guarded failure path, and verify that the
harness surfaces it; add no new mechanism unless verification shows the message
is swallowed.

**Rationale**: The CLI already does the right thing. `_run_mcp`
(`src/seshat/cli/__init__.py`) guards *server construction specifically* — not the
serve loop — so an absent extra produces a named two-lane install hint and exit
2, while an unrelated import failure inside a running server is not misreported
as a missing extra. That distinction was established deliberately and must not be
weakened. What is unverified is whether a harness shows a failed plugin server's
diagnostic output to the user or logs it silently.

**Alternatives considered**:
- *Bundle the extra as a hard dependency*: would make every plugin install pull
  the server SDK. Rejected — the extra is optional by design and the static core
  must stay driver-free (Principle VIII).
- *Add a preflight check skill*: a new surface for a problem the CLI already
  reports correctly. Rejected unless verification proves the message is invisible.

**Contingency**: if the diagnostic is not surfaced, the shipped router skill
states the prerequisite and the install guide leads with it, so the user has a
non-silent path even when the harness is quiet.

---

## R4 — What exactly makes a reference "dev-only"?

**Decision**: Classify per reference by *intent*, not per path prefix. A
reference fails when it instructs the agent to read a path a scaffolded workspace
does not contain; it passes when it names an output that a scaffold step
produces, or when it is scoped by an explicit "in the Seshat development
repository" condition.

**Rationale**: A prefix rule gives wrong answers in both directions.
`workspace_init._EMPTY_DIRS` scaffolds only `mappings`, `warehouse/migrations`,
`powerbi`, `reports` and `evidence` — so `templates/` is absent from a fresh
workspace and a naive prefix rule would flag every mention. But template material
does reach a workspace through an explicit scaffold step, so a skill that says
"the scaffold writes `templates/x`" is correct and must pass, while one that says
"read `templates/x`" is broken and must fail. The 23 known references span both
kinds.

**Alternatives considered**:
- *Strip offending paragraphs at export time*: rejected by FR-018. A generated
  skill that silently diverges from its source destroys the single-source
  property the whole design rests on.
- *Allowlist the prefixes*: would pass genuinely broken references that happen to
  sit under an allowed prefix.
- *Ship the dev-only files too*: would put specs, roadmap and internal quality
  documents into a customer bundle. Rejected on scope and on Principle VII.

**Consequence**: the transform reports findings by skill and path and cannot
auto-fix. Each of the 23 is a reviewed rewrite of canonical text.

---

## R5 — How is "per-session routing cost" measured?

**Decision**: Measure the material an agent must hold merely to know which skills
exist — the concatenated name and description metadata of the shipped skill set,
per bundle — and record it as a token count before and after each payload story
against a reviewed ceiling.

**Rationale**: This is the only part of a bundle that is unavoidably resident.
Skill bodies load on demand (FR-021b), so body size does not enter the budget —
which matters here because the bodies are large: `cross-table-lineage` is ~27 KB
and `consumer-data-dictionary` ~24 KB, while their descriptions are a line each.
Measuring bodies would produce an alarming number that describes nothing a user
pays for; measuring the routing metadata describes exactly what they pay per
session.

**Alternatives considered**:
- *Total bundle bytes on disk*: measures download size, not session cost. Not the
  constraint that matters.
- *Count of skills*: a proxy that ignores description length, so it could pass
  while descriptions bloat.
- *No measurement*: rejected by the Q2 clarification; leaves an unbounded growth
  path with nothing to check it.

**Constraint on interpretation**: the recorded value is a size, never a score.
Nothing may derive a confidence, health, maturity or completeness value from it
(hard rule #9), and the spec states this explicitly at SC-010.

---

## Resolved unknown summary

| Id | Unknown | State |
|---|---|---|
| R1 | Both harnesses start plugin-declared servers | Decided; **external-sourced, re-confirm before US1** |
| R2 | Workspace resolution for a plugin-launched governor | Decided; verify resolved root alongside R1 |
| R3 | Visibility of the absent-extra diagnostic | Decided; existing path reused, visibility verified |
| R4 | Definition of a dev-only reference | Decided; per-reference by intent |
| R5 | Routing-cost measurement method | Decided; routing metadata, recorded as size |

No `NEEDS CLARIFICATION` marker remains in the Technical Context.
