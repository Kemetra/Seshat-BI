# Implementation Plan: 086-shared-checklist-fork (I3)

**Branch**: `086-shared-checklist-fork` | **Spec**: `spec.md` | **Clarify**: `clarify.md`
**Status**: Draft (stops at ratify ledger; NOT approved, NOT implemented)

## Approach

A single static `@register`ed rule: glob `skills/**/checklists/*.md`, group by
basename, and reconcile every 2+-skill collision against a HUMAN-AUTHORED
`docs/quality/shared-spine.yaml` (`shared` = must be byte-identical; `distinct` =
may differ). Fail-closed on undeclared collisions, shared-drift, and a missing
manifest. Stdlib-only (`hashlib`/`pathlib`/`re`), `ctx.tracked_files` only, never
executes, never writes the manifest, no numeric score.

**The load-bearing precondition**: the rule is inert-then-ERROR until the owner
authors the spine manifest AND rules the one existing fork
(`aggregation-grain-checklist.md`) shared or distinct (clarify C1/C2, Principle V).
The build cannot land green before that owner artifact exists.

## Constitution / hard-principle check

| Principle | How honored |
|---|---|
| Never-execute / static-first (VIII) | stdlib hash/glob over tracked_files; no fs walk, no DB, no subprocess |
| No numeric score (#9) | categorical Findings only (FR-010) |
| No self-grant / no manifest write (V) | rule READS the spine; the owner authors it; agent never rules the fork (clarify C1/C2) |
| No resolving a human judgment call (V) | shared-vs-distinct is the owner's; the rule only enforces the recorded decision |
| Observed-not-declared severity (044) | severity per branch at the Finding site |
| ADD not REPLACE (VII) | new module + fixtures; touches no existing rule |
| Determinism (IX) | sorted basename groups, sha256, UTF-8 no BOM, MAX_PATH-safe package-relative |

## Components

1. **`src/retail/rules/rule_sf1.py`** (scaffold name; SF1 candidate):
   - `_collect(ctx) -> dict[basename, list[(path, sha256)]]`: glob
     `skills/**/checklists/*.md` from `ctx.tracked_files`, exempt test paths
     (FR-009), group by basename.
   - `_load_spine(ctx) -> dict[basename, "shared"|"distinct"]`: read
     `docs/quality/shared-spine.yaml`; ERROR if missing/malformed (FR-008).
   - `check(ctx)`: for each collision -> undeclared? ERROR (FR-004); shared+drift?
     ERROR (FR-005); distinct+identical? WARNING (FR-006). For each spine entry ->
     stale? WARNING (FR-007).
   - `@register(RULE_ID, "cross-layer checklist fork detector")`.
2. **Wiring** (adversarial-review lesson from B1/085): scaffold WRITES stub +
   test-stub + EXPECTED_RULE_IDS; PRINTS the `__init__.py` import edit (the ONLY
   discovery step -- no autodiscovery), the glossary row, and golden regen cmds.
   A post-wiring test MUST confirm the id is in `all_rules()`.
3. **Rule-count lockstep**: bump `rule-count-claims.yaml` + glossary anchor
   (52 -> 53) in the same commit.
4. **`tests/unit/test_rule_sf1.py`** + `tests/fixtures/shared_fork/` corpus.
5. **(owner, not agent)** `docs/quality/shared-spine.yaml` -- authored by the owner
   per clarify C1/C2. The agent may commit only the documented SHAPE on request.

## Path targets (single source of truth)

- `CHECKLIST_GLOB = "skills/**/checklists/*.md"`
- `SPINE_REL = "docs/quality/shared-spine.yaml"`

## Test strategy (fail-closed, mirrors test_design_*.py)

- Fixtures: undeclared-collision (ERROR); declared-shared-identical (pass);
  declared-shared-drift (ERROR); declared-distinct-differ (pass);
  declared-distinct-identical (WARNING); stale-entry (WARNING); missing-manifest
  (ERROR); unique-basename (no Finding); 3-copy shared (ERROR once).
- Format/scope: test fixtures exempt from the glob (FR-009) -- fixtures never
  self-trip.
- Mutation-verified: each ERROR/WARNING is RED before, correct after; deleting an
  assert lets a bad fixture pass.

## Sequencing (single PR; one new rule = one registry-count serialization point)

owner authors spine (BLOCKS) -> scaffold -> write check() -> fixtures/tests ->
count lockstep -> local gate -> PR. See tasks.md.

## Risks

- **No owner manifest = no green landing** (the defining risk). Mitigation: the
  ratify ledger makes the owner-authored spine + the C1 fork ruling explicit
  preconditions; the build does not start until they exist.
- **Wrong glob root** (`.claude/skills` vs `skills`): scoped to `skills/**` only
  (the reviewers' target); `.claude/skills` deferred (YAGNI).
- **Rule-count merge clash**: only this rule in flight; no other rule PR may land
  between scaffold and merge.

## Out of scope

`.claude/skills/**`; non-checklist files; auto-authoring the manifest; auto-fixing
a drift; any numeric score; any Power BI execution.
