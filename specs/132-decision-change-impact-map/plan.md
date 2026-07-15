# Implementation Plan: Decision Change Impact Map

**Branch**: `132-decision-change-impact-map` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/132-decision-change-impact-map/spec.md`

> SPECIFICATION-ONLY package. This plan describes the smallest implementation-ready slice; it does
> NOT implement it. No file outside `specs/132-decision-change-impact-map/` is created or modified.
> All source paths named below are REUSE anchors verified against `main@9ad0d9c`, not new files to
> write in this package.

## Summary

Add ONE read-only projection layer — `impact_map` — that, given an **approved** decision that is
superseded or evidence-stale, resolves the decision's scope to downstream artifacts, walks the
**existing** lineage edges to separate direct vs transitive impact (recording an evidence path per
edge), emits an incomplete-lineage warning for every unresolved scope tag / edge / dangling
supersession pointer, names the affected readiness stages, and states the next human review action.
The layer composes seven existing authorities and adds exactly one net-new seam: the
decision-scope → downstream-artifact join and the projection dict that carries it. It writes no
state, grants no approval, computes no numeric score, and needs no network/live DB.

**Technical approach**: a new pure-Python module `src/seshat/impact_map.py` (loader/composer) plus
a thin read-only surface, following the established `build_*() -> dict -> render/print` +
`scan_disclosure` + `resolve_local_output` pattern used by `passport.py` and `explorer/build.py`.
The MVP (US1+US2) is the composer producing the projection dict with direct/transitive labels and
incomplete-lineage warnings; the surface, preview/chain reading, fail-closed hardening, and dual
rendering layer on top.

## Technical Context

**Language/Version**: Python 3.11+ (matches the shipped `src/seshat/` package; `requires-python`
in `pyproject.toml`).

**Primary Dependencies**: standard library only for the core composer (mirrors the static core's
`dependencies = []` posture, Constitution Principle VIII). Reuses in-repo modules: `decision_store`,
`decision_gate`, `artifact_identity`, `readiness_projection`, `readiness_classify`,
`explorer.build` (lineage), `disclosure`, `cli.guards`. No new third-party dependency, no lockfile
change.

**Storage**: none new. Reads committed artifacts (`.seshat/*.yaml` Decision Store, cited evidence
files, `mappings/*/metrics/*.yaml`, `mappings/*/readiness-status.yaml`,
`contracts/knowledge/database-to-pbip-flow.yaml`, TMDL/binding-map files as the existing lineage
authorities already read). Writes only under the existing contained output root (`.seshat-output/`)
via `cli.guards.resolve_local_output`.

**Testing**: pytest (`tests/unit/`, `tests/integration/`) with the repo's `@pytest.mark.unit`
convention; fixtures under `specs/132-decision-change-impact-map/contracts/fixtures/` referenced by
the tasks, materialized into `tests/` fixtures at implement time.

**Target Platform**: cross-platform CLI/library (Windows-first per repo); offline, no desktop/PBI
process, no DB driver import on the module path.

**Project Type**: single project (library + thin read-only surface), Option 1 structure.

**Performance Goals**: N/A as a latency target. The only performance-shaped constraint is
**termination** — the transitive walk must be bounded (cycle-safe), not fast (FR-014, SC-006).

**Constraints**: read-only; offline-capable (NFR-002); deterministic byte-identical output modulo a
generated-at field (NFR-001); disclosure-safe fail-closed (NFR-003/004); no numeric score (FR-023);
single lineage-node vocabulary (NFR-006); minimal diff — no dependency/schema/CI/package/lockfile/
constitution change.

**Scale/Scope**: bounded by committed-tree size (a workspace's decisions × mappings × metric
contracts × model/dashboard artifacts); no scale-out concern for a per-decision projection.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | This plan |
| --- | --- | --- |
| I — Agent-First, Gate-Enforced | The agent proposes; the checker/gate disposes. Must not make the agent the authority on pass/fail. | PASS. The layer READS existing verdicts/statuses; it never grants or advances one (FR-025). It adds no rule that lowers the gate; if a static consistency check is wired later it fails closed and is `<no-finding>` on `main`. |
| II — Depend, Never Fork | No forking the execution adapter; no adapter logic. | PASS. No Power BI adapter interaction; the layer is a read model over committed text. |
| III — Medallion, Postgres-First, Gold-Only | Power BI reads gold only; no back-writes. | PASS. Lineage resolution follows the existing gold-only `binds_to` edges; a reference into `silver`/`bronze` is an incomplete-lineage warning, never an inferred edge (spec Edge Cases). No DB access. |
| IV — Source Mapping Before Silver | Mapping gate precedes silver. | N/A — this feature writes no silver/gold and gates nothing; it only reports over existing artifacts. |
| V — Agent Stops at Judgment Calls | Never self-grant approval; raise owner decisions. | PASS. The layer states the next human review action and STOPS; it supersedes/approves nothing (FR-024, FR-025). Any owner-authority item is surfaced, never actioned. |
| VI — Defaults Then Deviations | Start from ADR defaults; record deviations. | N/A — no cleaning/modeling decision is made. |
| VII — C086 Is An Example | Stay generic. | PASS. NFR-005 + SC-012 forbid worked-example specifics in generic artifacts. |
| VIII — Static-First, Live Deferred | Ship the offline core; defer live. | PASS. Core is stdlib-only and offline (NFR-002); no live DB/PBI is a trigger or input (FR-002). No driver import on the module path (mirrors HR9's `test_*_no_database_driver` guard). |
| IX — Secrets and Reproducibility | Secrets only in `.env`; reproducible; Windows-safe. | PASS. Disclosure scan blocks any secret/PII/connection-string leak before write (NFR-003, SEC-001..003); output is deterministic (NFR-001); paths repo-relative posix. |
| Readiness spine | No new stage; spine is sole stage-state authority; never a fabricated score. | PASS. Affected stages are READ from `readiness_projection` + `_FLOW_TO_SPINE` (FR-017); no `readiness-status.yaml` write; no new stage; no score (FR-023). |

**Result: Constitution Check PASSES with no violation. Complexity Tracking is empty (no
justification required).**

## Project Structure

### Documentation (this feature)

```text
specs/132-decision-change-impact-map/
├── plan.md              # This file
├── research.md          # Phase 0 — reuse-vs-new decisions, verified anchors, open questions
├── data-model.md        # Phase 1 — projection dict shape + reused record shapes
├── quickstart.md        # Phase 1 — how a reviewer runs it; fixtures walkthrough
├── contracts/
│   ├── impact-map.projection.schema.md   # the machine-readable projection contract (shape + invariants)
│   └── fixtures/                         # fixture descriptors for the tasks (direct/transitive/cycle/stale/missing/conflict/incomplete/dangling-pointer)
├── checklists/
│   └── requirements.md  # spec quality checklist (from /speckit.specify)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root) — REUSE anchors + the single new module

```text
src/seshat/
├── impact_map.py                 # NEW — the composer: load subject decision -> resolve scope -> walk lineage -> assemble projection dict (read-only)
├── decision_store.py             # REUSE — load_store, scope_keys, active_scope_conflicts, approval_is_valid, supersedes/superseded_by, STATUS/CRITICAL vocab
├── decision_gate.py              # REUSE — _evidence_stale (staleness signal; PROMOTE to shared, see research.md), project_to_spine + _FLOW_TO_SPINE (affected stage)
├── artifact_identity.py          # REUSE — artifact_identity(), resolve_within() (identity + sandbox-safe resolution)
├── readiness_projection.py       # REUSE — build_readiness_projection() (affected-stage source, disclosure-safe)
├── readiness_classify.py         # REUSE — classify(), CATEGORY_RANK, rank_of() (next review action + ordering)
├── explorer/build.py             # REUSE — _lineage() (runtime metric->gold edge + node vocabulary), _evidence_state()
├── disclosure.py                 # REUSE — scan_disclosure() (fail-closed pre-write scan)
└── cli/
    ├── guards.py                 # REUSE — resolve_local_output() (contained .seshat-output/ write)
    └── commands/impact_map.py    # NEW (thin) — read-only surface dispatch (US5), mirrors commands/explorer.py & commands/passport.py

.claude/skills/cross-table-lineage/SKILL.md   # REUSE (read) — hop definitions + proven/unresolved/gap tiering for transitive paths

tests/
├── unit/test_impact_map.py               # NEW — composer unit tests (direct/transitive/cycle/stale/missing/conflict/incomplete/dangling)
├── unit/test_impact_map_no_score.py      # NEW — SC-005 structural no-score guard (mirrors HR9 no-`%` test)
├── unit/test_impact_map_no_driver.py     # NEW — NFR-002 offline guard (no psycopg/sqlalchemy/.connect on module path)
└── integration/test_impact_map_surface.py # NEW — US5 dual-output + disclosure-block + contained-write, byte-determinism
```

**Structure Decision**: Option 1 (single project). The feature is one new library module
(`src/seshat/impact_map.py`) plus one thin read-only surface (`src/seshat/cli/commands/impact_map.py`),
following the exact shape of the two nearest shipped siblings (`explorer/build.py` +
`commands/explorer.py`; `passport.py` + `commands/passport.py`). No new package, no new top-level
directory, no schema/CI/lockfile change.

## Phase 0 — Research (see research.md)

Resolves the reuse-vs-new dispositions against verified source anchors and the residual risks the
ground-truth pass surfaced. Key decisions recorded there:

1. **Staleness signal**: PROMOTE `decision_gate._evidence_stale` (currently module-private, line 80)
   to an importable shared helper rather than copy-pasting its sha256-compare — avoids a forked
   staleness authority (residual risk #2). This is a minimal, behavior-preserving refactor of one
   function's visibility, not a logic change; its existing callers keep working.
2. **Lineage vocabulary**: ADOPT the explorer's `metric:<table>:<name>` / `warehouse:<gold_table>`
   node-id vocabulary (`explorer/build.py:_lineage`, line 80) and extend its `mappings/*/metrics/*.yaml`
   globber for the metric→gold hop; for hops beyond metric→gold, follow the `cross-table-lineage`
   SKILL's hop definitions + proven/unresolved/gap tiering. Do NOT introduce a fourth metric-identity
   vocabulary (NFR-006, residual risk #1).
3. **Transitive walk**: implement as a bounded DFS/BFS over the composed edge set with an explicit
   visited-set for cycle detection (FR-014); tier each hop proven/unresolved/gap per the skill so the
   impact map never disagrees with shipped lineage on which hops resolve (residual risk #3).
4. **Never-mutate contract**: mirror `decision_gate`'s "never store state, only classify" and
   `project_to_spine`'s "contribution, not a write" — no `supersede()` writer (none exists;
   supersession is a human YAML edit), no `readiness-status.yaml` write, no approval grant (residual
   risk #4).
5. **"No reference ≠ unaffected"**: the correctness core. Every `scope_keys` entry that resolves to
   zero artifacts, and every edge whose target is missing, becomes an explicit incomplete-lineage
   warning — never a silent drop, never an inferred edge (FR-012/013, residual risk #5, doubles as
   the net-new proof).
6. **Determinism**: sort every collection by a stable key (artifact identity `kind:path`, decision
   id, edge from→to) and exclude the generated-at field from the content digest, mirroring
   `passport.build_passport`'s `passport_id` treatment (NFR-001, residual risk #6).

## Phase 1 — Design (see data-model.md, contracts/, quickstart.md)

- **data-model.md**: the `ImpactMapProjection` dict shape and each reused input record shape
  (ChangedDecision, supersession pointers, AffectedArtifact, DependencyEdge,
  IncompleteLineageWarning, AffectedReadinessStage, NextReviewAction), with field-level provenance
  (reused-as-is vs new-projection-field) and the deterministic ordering rule per collection.
- **contracts/impact-map.projection.schema.md**: the machine-readable projection contract —
  required keys, the disjoint `affected[]` vs `incomplete_lineage[]` invariant (FR-015), the
  no-score invariant (FR-023/SC-005), the byte-determinism rule (NFR-001), and the disclosure-scan
  precondition (NFR-003).
- **contracts/fixtures/**: descriptors for the eight fixture families the tasks require
  (direct, transitive, cycle, stale-evidence, missing-ref, active-scope conflict, incomplete-lineage,
  dangling supersession pointer) plus a generic no-leak fixture (SC-012).
- **quickstart.md**: how a reviewer produces a preview and a post-supersession map, reads the
  human/machine forms, and interprets incomplete-lineage warnings.

## Migration & Compatibility Posture

- **Additive only**: one new module + one thin surface + tests. No existing decision record,
  readiness-status file, metric contract, or lineage output changes shape.
- **The one refactor** (promoting `_evidence_stale` to public) is visibility-only and
  behavior-preserving; its current in-module callers are unaffected. A guard test asserts the promoted
  helper's behavior is identical to the pre-promotion path (no staleness-truth fork). Three other
  private symbols (`explorer._lineage`, `explorer._evidence_state`, `decision_gate._FLOW_TO_SPINE`) are
  imported *as-is* (read-only), not promoted — see research.md Decision 2 for why only the
  behavior-shared helper earns promotion while read-only derivations are reused private to keep the
  diff minimal and avoid a divergent second derivation.
- **No schema/CI/package/lockfile/constitution change.** If a narrow static consistency rule is ever
  wired (optional, tasks mark it as such), it must be `<no-finding>` on `main` before landing
  (repo convention) and fail closed.
- **Backward compatible**: absent an impact-map invocation, nothing in the kit behaves differently.

## Security / Privacy Behavior

- Disclosure scan (`disclosure.scan_disclosure`) runs on the projection dict BEFORE any write; any
  `secret_field` / `connection_string` / `absolute_path` / `pii_value` / `raw_value_array` finding
  blocks the write (NFR-003, SEC-001..003).
- Only repo-relative posix paths + `kind:path` identities are recorded; raw evidence content is never
  embedded (SEC-003).
- No DB driver is imported on the module path (offline guard test, NFR-002).

## Deterministic Ordering & Cycle Handling

- **Ordering**: `affected[]` sorted by `(direct-before-transitive, artifact_id)`; within each entry,
  `evidence_paths` in traversal order; `incomplete_lineage[]` sorted by `(kind, locator)`;
  `supersession_chain[]` in pointer order from the subject decision. Byte-identical across runs modulo
  `generated_at` (NFR-001). (The map is single-subject; edge provenance lives inside
  `affected[].evidence_paths`; there is no separate top-level `edges[]` collection.)
- **Cycles**: a visited-set-guarded walk; on re-encountering a node, record a named cycle condition
  and stop that branch — never re-traverse, never emit the cycle as a completed transitive path
  (FR-014, SC-006).

## Test Strategy

- **Unit** (`test_impact_map.py`): one test per correctness property — direct labeling, transitive
  labeling with edge evidence-path chain, cycle termination, evidence-stale trigger, missing-ref
  warning, active-scope conflict surfacing, incomplete-lineage disjointness, dangling-pointer warning,
  preview-no-mutation.
- **Unit guards**: `test_impact_map_no_score.py` (no digit-then-`%`, no `score`/`confidence`/
  `risk`/`blast_radius` key — SC-005); `test_impact_map_no_driver.py` (offline — NFR-002).
- **Integration** (`test_impact_map_surface.py`): dual human/machine output identity (SC-009),
  disclosure-block-before-write (SC-011), contained write (FR-022), byte-determinism double-run
  (SC-010).
- **No-duplicate verification task**: asserts no new Decision Store / readiness engine / lineage
  authority / approval system / status model / stage / score / broad CLI family / web UI is created
  (SC-013), and that every reused authority is imported, not re-implemented.

## Complexity Tracking

*No Constitution Check violations. This section is intentionally empty.*
