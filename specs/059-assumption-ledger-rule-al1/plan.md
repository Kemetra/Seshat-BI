# Implementation Plan: Assumption Ledger Rule (AL1)

**Branch**: `053-assumption-ledger-rule-al1` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/053-assumption-ledger-rule-al1/spec.md`

## Summary

Add ONE static rule -- id `AL1`, module `src/retail/rules/assumptions.py` -- that
fails closed (ERROR) when a committed metric contract presents a SETTLED gold
binding ON TOP OF a self-declared UNRESOLVED assumption. Per the ratified
Clarifications (Session 2026-07-01): the unresolved-assumption marker is the
EXISTING open-state field mechanism the contract already defines --
`readiness.status == "blocked"` with a non-empty `readiness.blocking_reasons[]`
(C1/FR-015); the coexisting settled binding is a FILLED, non-placeholder
`binds_to.gold_table` (a real `gold.<...>`, not the `<...>` angle-bracket
placeholder) plus a non-empty, non-placeholder `binds_to.columns` list (C2/FR-016).
AL1 emits exactly one ERROR Finding per offending contract; an honest blocked draft
whose binding is still a placeholder, a fully-resolved (`pass`) contract, and a tree
with no metric contracts all yield no Finding. AL1 ships STANDALONE (C3/FR-017):
because it keys on an existing field, it has a real convention to check on day one
and is not gated on the unshipped T1.2 define-half.

AL1 is the structural sibling of PP1/SC1/DF1: a `@register` retail-check rule that
scans per-table instances under `mappings/<table>/metrics/*.yaml` via
`ctx.tracked_files`, EXCLUDES the generic `templates/metric-contract.yaml`, imports
`yaml` LAZILY (preserving the stdlib-only `retail check` core invariant), reads only
committed text, is categorical (no numeric score), and returns Findings without
executing anything (never evaluates DAX, never opens a connection). Registering the
rule also adds `AL1` to `EXPECTED_RULE_IDS` in the same change and regenerates
`docs/rules/rules-manifest.json` (043 snapshot), and a unit test exercises the rule
FIRING on a known-bad synthetic fixture (closing the wiring-latent-gap class).

## Technical Context

**Language/Version**: Python 3.11+ (matches the existing `src/retail` package and
`tests/unit` suite; note CI runs 3.13 -- authored code stays version-neutral).

**Primary Dependencies**: standard library only in the import-time core (`pathlib`;
`re` if used for placeholder detection). `yaml` is imported LAZILY inside the rule
function (never at module scope), exactly as `metric_drift.load_definition()` and
the sibling reconciler rules do -- this keeps `retail.rules.assumptions` out of the
stdlib-only core import chain (B1/B3). The rule imports `retail.core` (`Finding`,
`RuleContext`, `Severity`, `is_test_path`) and `retail.registry` (`register`).

**Storage**: N/A. The rule reads tracked files as text via the existing
`RuleContext` (`repo_root`, `tracked_files`); it opens no database and holds no
connection. It NEVER writes any file (in particular it never writes/clears an
assumption or a readiness state).

**Testing**: pytest, marked `pytest.mark.unit`. New unit tests over generic /
synthetic metric-contract fixtures (blocked+bound, blocked+unbound, pass+bound,
malformed), plus the existing rule-wiring test (`test_rules_wiring.py`) and the 043
manifest snapshot test (`test_rules_manifest_snapshot.py`).

**Target Platform**: Local dev + CI (Windows-first per repo `CLAUDE.md`;
platform-agnostic Python).

**Project Type**: Single project (library + CLI under `src/retail`, tests under
`tests/`).

**Performance Goals**: N/A (a handful of small YAML reads over the committed metric
contracts during the static gate; five contracts exist today).

**Constraints**: stdlib-only core (yaml lazy), opens no network/DB connection,
requires no credentials, never writes a file, never executes DAX. ASCII / UTF-8
without BOM (`--`, `->`). Generic contract SHAPE only -- no domain-specific table,
column, KPI, or PII rule; the worked-example (c086) is a cited filled instance,
never inlined.

**Scale/Scope**: One rule registration + the coexistence-condition logic + the
wiring-test id-set update + the regenerated manifest + new unit tests. No production
artifact (no metric contract, template, or readiness file) is modified; the rule
advances no readiness stage.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS. AL1 is a registered rule whose
  authority is the non-zero `retail check` exit; it fails closed, never merely advises.
- **Principle V (Agent Stops at Judgment Calls)**: PASS with the load-bearing
  boundary. AL1 SURFACES an unresolved assumption (a `blocked` contract) that carries
  a settled binding; it NEVER resolves, clears, populates, or auto-answers the
  assumption, and never edits the readiness state. Clearing an assumption stays a
  human seam. The governance MEANINGS of C1/C2 (what an unresolved assumption is, and
  whether binding-atop-blocked is always a defect) are recorded to open_for_human for
  optional human override; the build proceeds on the advisor default.
- **Principle VII (C086 Is An Example)**: PASS. AL1 keys off the GENERIC contract
  SHAPE (`readiness.status`/`blocking_reasons`/`binds_to`), table-name-agnostic.
  Fixtures are synthetic generic contracts; c086 is a cited filled instance only,
  never inlined. No pharmacy dataset path, measure name, or discount-status ruling
  appears in the rule.
- **Principle VIII (Static-First Governance, Live Deferred)**: PASS. AL1 is part of
  the stdlib-only static core; it reads committed text, parses-not-executes (lazy
  yaml), and never opens a connection. It joins `retail check`, not `retail validate`.
- **Principle II (Depend, Never Fork)**: PASS. AL1 reuses the existing lazy-yaml
  contract-read pattern (`metric_drift.load_definition`) and the shared
  `is_test_path()` exemption rather than forking a second contract parser or path
  filter; the exact reuse seam is fixed in research.md.
- **Principle IX (Reproducibility / Windows-safe)**: PASS. Pure-Python,
  deterministic, ASCII / UTF-8 no BOM, short paths.
- **ADR 0007 (DAX governance layers)**: PASS. AL1 is an L2 `@register` rule adding
  exactly ONE rule id (33 -> 34). It is NOT hung off `semantic.py` (L3, zero
  `@register`, adds no rule id).
- **Anti-fabricated-confidence (rule #9)**: PASS. AL1 emits Findings only; it
  produces no readiness/confidence number or threshold.
- **Rule-registry integrity (043 snapshot + wiring test)**: PASS. Adding AL1 updates
  `EXPECTED_RULE_IDS` AND regenerates the manifest in the same change; a test
  exercises the rule FIRING on a known-bad fixture, not merely its registration. No
  numeric baseline count is hard-coded (the wiring test keys off set length).
- **Readiness spine / no stage advance**: PASS. AL1 is an idea-bank sequence rule
  with NO roadmap F-number; it advances no stage and moves nothing to `pass`.
- **No executor / no deferred capability**: PASS. Pure static text rule; depends on
  no Power BI execution adapter (F016), spec-only runtimes (F031-F033), live
  database, or the unshipped T1.2 ledger define-half.

No violations. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/053-assumption-ledger-rule-al1/
  plan.md              # This file
  research.md          # Phase 0 output
  data-model.md        # Phase 1 output
  quickstart.md        # Phase 1 output
  contracts/
    rule-contract.md   # Phase 1 output (the checkable rule contract)
  checklists/
    requirements.md    # Spec quality checklist (from /speckit-specify)
  spec.md              # Feature specification
  tasks.md             # Phase 2 output (/speckit-tasks)
  analysis.md          # /speckit-analyze output (repo convention)
  plan-review.md       # adversarial plan-review output (repo convention)
```

### Source Code (repository root)

```text
src/retail/
  core.py              # Finding, RuleContext, Severity, is_test_path (READ ONLY -- imported)
  registry.py          # register decorator                          (READ ONLY -- used)
  metric_drift.py      # load_definition() lazy-yaml contract loader  (READ ONLY -- reuse pattern)
  rules/
    assumptions.py     # NEW module for the AL1 rule

templates/
  metric-contract.yaml # GENERIC template -- EXCLUDED from AL1's scan; NEVER edited,
                       #   NEVER scanned at runtime (placeholders by design)

mappings/<table>/metrics/
  <Metric>.yaml        # per-table instances AL1 scans (five exist today under
                       #   mappings/retail_store_sales/metrics/)

docs/rules/
  rules-manifest.json  # regenerated via `retail manifest --repo .`

tests/unit/
  test_rules_wiring.py       # EXPECTED_RULE_IDS updated with "AL1" (33 -> 34)
  test_rules_manifest_snapshot.py  # snapshot re-asserted after manifest regen
  test_assumptions.py        # NEW -- direct firing tests over synthetic generic
                             #   contracts (blocked+bound / blocked+unbound /
                             #   pass+bound / malformed)
```

**Structure Decision**: Single-project layout. The feature adds exactly one
registered rule in a new `src/retail/rules/assumptions.py` (auto-wired by the
registry's package discovery -- no `registry.py` edit), plus its tests, updates the
wiring-test id set, and regenerates the manifest. It modifies NO committed metric
contract, template, or readiness file.

## Phase 0 -- Research (research.md)

Resolve and record (all grounded against the repo; no open technical unknowns):

1. The lazy-yaml contract-read seam: how `metric_drift.load_definition()` imports
   `yaml` INSIDE the function and reads the contract text; decide AL1's reuse
   (call `load_definition`-style read vs a private lazy read) so no module-scope
   yaml import is introduced (B1/B3) and no second parser is forked (Principle II).
2. The contract SHAPE anchors AL1 keys off: `readiness.status` (string in
   `{not_started|blocked|warning|pass}`), `readiness.blocking_reasons` (list), and
   `binds_to` (`gold_table` string + `columns` list). Record the exact, generic,
   table-agnostic field paths and the placeholder form (`<...>` angle brackets) that
   marks an UNFILLED binding -- reusing the same placeholder polarity PP1 established.
3. The instance-selection + exemption pattern: how the sibling rules enumerate
   `ctx.tracked_files`; confirm AL1 selects only `mappings/*/metrics/*.yaml`,
   EXCLUDES `templates/metric-contract.yaml`, and excludes `tests/` fixtures via
   `is_test_path()`.
4. The registration / wiring contract: how `EXPECTED_RULE_IDS` keys off its own
   length (never a literal count) and how `retail manifest --repo .` regenerates
   `docs/rules/rules-manifest.json` guarded by the 043 snapshot test.
5. The wiring-latent-gap obligation: AL1 must be exercised FIRING on a known-bad
   fixture, not merely listed in the id set -- record the test obligation.
6. The Principle-V boundary: confirm AL1 only READS the readiness/binding fields and
   emits a Finding; no code path writes, clears, or resolves the assumption or the
   readiness state. Record the standalone-vs-gated resolution (standalone) and the
   genuine (not vacuous) on-main baseline evidence (on-main contracts are `pass`).

## Phase 1 -- Design

- **data-model.md**: Describe the marker predicate (a `blocked` status + non-empty
  `blocking_reasons`), the settled-binding predicate (a filled non-placeholder
  `binds_to.gold_table` + non-empty non-placeholder `binds_to.columns`), the
  coexistence trigger (marker AND binding on the same contract -> one ERROR), the
  contract-selection predicate (instance paths only; template + tests excluded), the
  registration record (id + title), and the Finding shape emitted per offending
  contract. Reference the reused lazy-yaml read (not a redefined parser).
- **contracts/rule-contract.md**: Restate the asserted rule contract as a checkable
  list -- (C1) a `blocked` contract with non-empty `blocking_reasons` AND a filled
  `binds_to` -> one ERROR Finding naming the contract; (C2) a `blocked` contract
  with a placeholder/empty `binds_to` -> no Finding (honest open draft); (C3) a
  `pass`/`warning`/`not_started` contract with a filled binding -> no Finding;
  (C4) the generic template + `tests/` fixtures -> no Finding; (C5) empty tree (no
  metric contracts) -> no Finding; (C6) an unreadable/unparseable contract ->
  fail-loud ERROR Finding; (C7) AL1 never writes/clears the assumption or readiness
  state (Principle-V read-only boundary); (C8) registry id set + regenerated manifest
  + a firing test all agree (33 -> 34, AL1 the sole addition); (C9) no domain-specific
  artifact anywhere; (C10) severity is uniform ERROR.
- **quickstart.md**: How to run the rule's tests and the wiring/snapshot tests, what
  each proves, and how to regenerate the manifest.

### Post-Design Constitution Re-Check

Unchanged from above -- the design adds one rule, its tests, the id-set update, and
the regenerated manifest; it reuses the existing lazy-yaml read pattern and the
placeholder polarity, introduces no new violation, dependency, executor, or severity
tier, and writes no committed production artifact.

## Complexity Tracking

No constitution violations. Section intentionally empty.
