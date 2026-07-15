# Phase 0 Research: Decision Change Impact Map

**Feature**: `132-decision-change-impact-map` | **Date**: 2026-07-15

> All source anchors below were verified against `main@9ad0d9c` (line numbers as of that commit).
> This document records reuse-vs-new dispositions and resolves the residual risks the ground-truth
> pass surfaced. It makes no code change.

## Decision 1 — The single net-new seam

**Decision**: Build exactly ONE net-new thing: the *decision-scope → downstream-artifact join* and
the projection dict that carries it (`src/seshat/impact_map.py`). Everything else is reuse.

**Rationale**: An adversarial reviewer instructed to prove the boundary already exists (defaulting
to "duplicate") could not: no shipped code walks from a decision to the artifacts derived from it.
`decision_gate` reads only a decision's *own* cited evidence; `explorer._lineage` starts at a metric
contract (decision-blind); `cross-table-lineage` starts at a source-map (decision-blind, prose-only);
HR9 resolves TMDL *names* with no decision concept at all. The join is unclaimed in both
`capabilities.yaml` and `roadmap.md`.

**Alternatives rejected**:
- *Extend `decision_gate`* → would overload the pass/warn/blocked classifier with traversal it was
  explicitly built NOT to do ("never traverses to any downstream artifact"). Rejected: violates its
  single responsibility and risks a second verdict authority.
- *Extend the `cross-table-lineage` skill* → it is decision-blind prose producing one markdown file
  per run, not a queryable composer, and adding a decision node to it would fork the lineage design.
  Rejected: reuse its *hop definitions*, not its surface.
- *A new graph engine / graph DB* → explicitly a Non-Goal (spec) and unjustified for a per-decision
  bounded walk over committed text.

## Decision 2 — Staleness signal: PROMOTE, don't copy

**Decision**: Promote `decision_gate._evidence_stale(repo_root, approval) -> list[str]`
(`src/seshat/decision_gate.py:80`, currently module-private) to an importable shared helper and call
it from `impact_map.py`. Do NOT copy-paste its sha256-compare logic.

**Rationale**: Residual risk #2 — if the projection re-implements staleness, staleness truth forks
between the gate and the impact view. Promotion is a visibility-only, behavior-preserving refactor of
one function; its existing in-module callers (`compute_verdict` path) keep working unchanged. A guard
test pins that the promoted helper's output equals the pre-promotion behavior.

**Why `_evidence_stale` alone is promoted (promotion asymmetry, decided)**: `impact_map.py` also
imports three other leading-underscore symbols as-is — `explorer._lineage` (`build.py:80`),
`explorer._evidence_state` (`build.py:38`), and `decision_gate._FLOW_TO_SPINE` (`decision_gate.py:279`).
Only `_evidence_stale` is *promoted* (its visibility changed); the other three are *imported private*.
The distinction is deliberate, not an oversight:
- `_evidence_stale` is the one whose *behavior* two authorities (the gate and the impact view) must
  compute identically — a fork here is a correctness split, so it earns a shared public helper + a
  guard test (T004) pinning byte-equal behavior.
- `_lineage` / `_evidence_state` / `_FLOW_TO_SPINE` are *data/derivation* the impact view only *reads*;
  reusing them as-is (rather than promoting) keeps the diff minimal and, critically, guarantees the
  impact map uses the *exact same* lineage edges, evidence-state tri-value, and flow→spine mapping the
  explorer/gate already produce — promoting them would invite a second call site to drift. Importing a
  private symbol is accepted coupling here precisely *because* re-deriving it would be worse (it would
  risk the fourth-vocabulary / divergent-traversal traps of residual risks #1 and #3).

So "one visibility refactor" is accurate for the *promotion* count (exactly one); the other three are
read-only private imports, documented here so the minimal-diff narrative is honest about the coupling
it accepts. If a reviewer prefers, promoting all four to public is an acceptable alternative at
implement time (it does not change behavior); the guard-test discipline (T004-style) would then extend
to each.

**Anchor**: `_evidence_stale` compares each `approval.evidence_identity[path]` (sha256 recorded at
approval) against the current `artifact_identity(repo_root, path, kind='evidence')` sha256; a mismatch
is a staleness reason. This is the ONLY staleness authority and must stay singular.

**Alternative rejected**: leave it private and copy the compare → forks the authority (rejected).

## Decision 3 — Lineage vocabulary: ADOPT explorer's node ids; TIER per the skill

**Decision**: Adopt the explorer's node-id vocabulary — `metric:<table>:<name>`,
`warehouse:<gold_table>`, edge `{from, to, relation:'binds_to', evidence}`
(`src/seshat/explorer/build.py:_lineage`, line 80) — and extend its `mappings/*/metrics/*.yaml`
globber for the metric→gold hop. For hops beyond metric→gold (source-map → SQL → contract → TMDL
measure → dashboard visual), follow the `cross-table-lineage` SKILL's hop definitions and its
**proven / unresolved / gap** tiering.

**Rationale**: Residual risk #1 — three incompatible metric-identity vocabularies already coexist
unreconciled in shipped code (`artifact_identity` `kind:path`, explorer `metric:<table>:<name>`, the
additivity rule's prose-derived metric-name strings). Adding a fourth would deepen the mess. Picking
explorer's runtime vocabulary (the only *shipped runtime* graph edge) and mapping the others to it is
NFR-006. Tiering per the skill (residual risk #3) guarantees the impact map never claims a hop is
"proven" that the shipped lineage design treats as "unresolved" or "gap."

**Alternatives rejected**:
- *Invent a fresh node id scheme* → violates NFR-006 (rejected).
- *Reimplement the skill's 5-hop compose in Python from scratch with new tiering* → would produce a
  divergent second traversal that could disagree with the shipped lineage (residual risk #3,
  rejected). Reuse the definitions/tiering; do not re-adjudicate.

## Decision 4 — Transitive walk: bounded, cycle-safe

**Decision**: Implement the transitive walk as a bounded DFS/BFS over the composed edge set with an
explicit `visited` set. On re-encountering a node, record a named cycle condition and stop that
branch.

**Rationale**: FR-014 / SC-006. HR9 is single-hop (no traversal) and cross-table-lineage is linear
prose, so cycle handling is genuinely net-new and must be specified. A visited-set guard is the
minimal, deterministic cycle-safety mechanism; no transitive-closure library is needed.

**Alternative rejected**: unbounded recursion / trusting the graph to be acyclic → risks an infinite
loop on a cyclic committed set (rejected).

## Decision 5 — "No reference found ≠ unaffected" (the correctness core)

**Decision**: Every `decision_store.scope_keys(scope)` entry that resolves to zero artifacts, every
lineage edge whose target is missing/unreadable, and every dangling `supersedes`/`superseded_by`
pointer becomes an explicit `IncompleteLineageWarning` — never a silent drop, never an inferred edge.
The `affected[]` and `incomplete_lineage[]` sets are disjoint and both always present (FR-015).

**Rationale**: Residual risk #5 — this is simultaneously the biggest correctness trap and the net-new
proof. `scope_keys` emits bare `kind:value` strings (`decision_store.py:293`) that are NOT resolved
against real files anywhere in shipped code; the resolution (and its honest failure mode) is exactly
the new work. Mirrors the explorer's tri-state `available/missing/deferred` evidence discipline
(`_evidence_state`, line 38) and the passport's `verified/unavailable` discipline — fail-closed, name
the gap, never hide it.

**Alternative rejected**: treat an unresolved scope tag as "no downstream artifact → unaffected" →
the exact dangerous false negative the spec forbids (rejected).

## Decision 6 — Never mutate / never grant

**Decision**: Mirror `decision_gate`'s documented "never store state, only classify" and
`project_to_spine`'s "a contribution the spine may fold in, NOT a readiness-status file." No
`supersede()` writer, no `readiness-status.yaml` write, no approval grant, no re-validate.

**Rationale**: Residual risk #4 + Constitution Principles I & V + FR-024/FR-025. Supersession is a
human YAML edit (no writer exists in `decision_store.py` — confirmed); the impact map only *reads* the
pointer chain. The readiness spine stays the sole stage-state authority.

## Decision 7 — Determinism

**Decision**: Sort every collection by a stable key and exclude a `generated_at` field from any
content digest, mirroring `passport.build_passport`'s `passport_id` (content digest excludes
`generated_at`). Ordering: `affected[]` by `(direct-first, artifact_id)`, with each entry's
`evidence_paths` in traversal order (the map is single-subject; edge provenance lives inside
`evidence_paths`; no separate top-level `edges[]`);
`incomplete_lineage[]` by `(kind, locator)`; `supersession_chain[]` in pointer order.

**Rationale**: NFR-001 / SC-010 / residual risk #6. Determinism is what makes the machine form
diffable and the human form stable; the passport already proves the pattern.

## Decision 8 — Offline, stdlib-only core

**Decision**: The composer imports only stdlib + in-repo modules; no DB driver on the module path. A
guard test asserts absence of `import psycopg`, `import sqlalchemy`, `.connect(`, `DSN` in the module
source (mirroring HR9's `test_hr9_module_imports_no_database_driver`).

**Rationale**: Constitution Principle VIII + NFR-002 + FR-002. Live DB / Power BI is never a trigger
or input, so the module must not even be able to reach one.

## Decision 9 — Surface: one thin read-only command (or skill), smallest addition

**Decision**: Expose the composer through ONE thin read-only surface modeled on
`cli/commands/explorer.py` + `cli/commands/passport.py` (build dict → disclosure-scan → render
human + write machine form under `.seshat-output/`). The precise choice (a narrow `impact-map` verb
vs a skill wrapper) is confirmed at implement time to be the smallest addition consistent with D8;
either satisfies FR-021/FR-022 identically.

**Rationale**: D8 — no broad CLI family, no web UI, no new stage. The two nearest siblings already
establish the exact pattern; matching it minimizes diff and reuses `resolve_local_output` +
`scan_disclosure` verbatim.

## Resolved open questions

- *Does supersession history exist to "preserve"?* No richer substrate than the `supersedes`/
  `superseded_by` scalar pointer pair (+ DS4 referential integrity). "Preserve history" = read and
  present that chain (spec D2/FR-006). Confirmed against `decision_store.py` + `rules/decision_store.py`.
- *Machine wire format (YAML vs JSON)?* Plan-level, format-independent for every FR/NFR/SC; defer to
  implement. Recorded in spec Assumptions and the clarify scan.

## Residual-risk → mitigation traceability

| Residual risk (ground-truth pass) | Mitigation (this plan) |
| --- | --- |
| #1 fourth lineage vocabulary | D3 — adopt explorer node ids; NFR-006 |
| #2 forked staleness authority | D2 — promote `_evidence_stale`, don't copy; guard test |
| #3 divergent transitive traversal | D3/D4 — reuse skill hop defs + proven/unresolved/gap tiering |
| #4 mutation/approval drift | D6 — never-write/never-grant contract; FR-024/025 |
| #5 "no reference = unaffected" false negative | D5 — explicit incomplete-lineage warning; FR-012/013/015; the net-new proof |
| #6 non-deterministic output | D7 — stable sort + generated-at excluded from digest; NFR-001 |
