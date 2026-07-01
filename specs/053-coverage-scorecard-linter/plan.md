# Implementation Plan: Coverage Scorecard Linter (SL1)

**Branch**: `053-coverage-scorecard-linter` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/053-coverage-scorecard-linter/spec.md`

## Summary

Add ONE static rule that fails closed on a MALFORMED committed per-table coverage
scorecard. The rule scans every filled per-table instance
(`mappings/<table>/**/*coverage-scorecard.md`), parses its four-column status table,
and asserts four structural invariants drawn verbatim from the shipped template's
own laws: (1) every Coverage status cell is a member of the closed five-value enum;
(2) a `Blocked -- ...` row names a blocker; (3) a `Covered` row cites a
`contracts/<file>.md` that resolves to a tracked file (Planned / Out of scope carry
`--` and are exempt); (4) no cell holds a number-then-`%` percentage token. Each
violation emits a `Severity.ERROR` Finding. The rule parses committed text with the
stdlib only, opens no database/network/Power BI connection, runs no query/DAX/agent,
stays import-safe at module scope, and EXCLUDES both the generic template file (its
placeholders + illustrative worked example) and committed `tests/` fixtures.
Registering the rule also adds its id to the wiring test's `EXPECTED_RULE_IDS` set
and regenerates `docs/rules/rules-manifest.json`, and a test exercises the rule
firing on a known-bad fixture. It is the CHECK sibling of the coverage-scorecard
TEMPLATE exactly as `PP1` (`src/retail/rules/publish_pack.py`) is the CHECK sibling
of the handoff-pack template, and it follows PP1's shape precisely.

## Technical Context

**Language/Version**: Python 3.11+ (matches the existing `src/retail` package and
`tests/unit` suite; CI runs 3.13, local 3.12).

**Primary Dependencies**: standard library only (`re`, `pathlib`). No new runtime or
test dependency. The rule imports `retail.core` (`Finding`, `RuleContext`,
`Severity`, `is_test_path`) and `retail.registry` (`register`). It mirrors PP1's
section-anchored positional table parse and its `<...>` placeholder-awareness idea;
the exact reuse (lift a shared helper vs re-derive the small patterns local to the
new module) is a Phase-0 decision recorded in research.md, chosen so the rule does
NOT fork a second table parser where sharing is cheap (Principle II).

**Storage**: N/A. The rule reads tracked files as text via the existing
`RuleContext` (`repo_root`, `tracked_files`); it opens no database, holds no
connection, and NEVER writes any file (in particular it never populates a status).

**Testing**: pytest, marked `pytest.mark.unit`. New unit tests for the rule over
generic/synthetic scorecard fixtures (well-formed; bad-enum; missing-blocker;
unresolved-contract-path; percentage-present), plus the existing rule-registry
snapshot / wiring tests (`tests/unit/test_rules_wiring.py`).

**Target Platform**: Local dev + CI (Windows-first per repo `CLAUDE.md`;
platform-agnostic Python).

**Project Type**: Single project (library + CLI under `src/retail`, tests under
`tests/`).

**Performance Goals**: N/A (a handful of text reads + regex scans over the small set
of committed scorecards during the static gate; ZERO exist today -- see Constraints).

**Constraints**: stdlib-only, opens no network/DB connection, requires no
credentials, never writes a file. ASCII / UTF-8 without BOM (`--` and `->`, no
glyphs). Generic status-enum + synthetic scorecard fixtures only -- no
domain-specific table, column, or KPI name, and the template's illustrative
worked-example answers are never inlined. NO filled scorecard instance exists on
main today, so the rule silent-passes by absence until an instance is committed at
the defined location (spec Q1); the rule must not crash or false-fire on an
empty-match tree.

**Scale/Scope**: One rule registration + the closed-enum constant + the wiring-test
id-set update + the regenerated manifest + new unit tests. No production artifact
(no scorecard, template, or readiness file) is modified; the rule never moves a
readiness stage to pass and never populates a status.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle V (Agent Stops at Judgment Calls)**: PASS with the load-bearing
  boundary. The rule checks a coverage STATUS is an enum member and that its
  supporting slots (blocker cell when Blocked, contract path when Covered) are
  STRUCTURALLY present; it NEVER decides whether a stated `Covered` is TRUE, grants
  any readiness stage, or populates a status. Mirrors PP1's slot-present-not-granted
  discipline. The boundary confirmation + roadmap-stage placement are Open-for-human
  items at the ratify gate (recorded in spec ## Clarifications).
- **Principle VIII (Static-First Governance, Live Deferred)**: PASS. The linter is
  part of the stdlib-only, CI-able static core; it reads committed text,
  parses-not-executes, opens no connection. It joins `retail check`, not
  `retail validate`. The template shipped first (static-first); this is the
  fail-closed check layered on top.
- **Principle II (Depend, Never Fork)**: PASS. The rule follows PP1's proven
  section-anchored positional parse shape rather than inventing a divergent parser;
  the shared-helper-vs-local-pattern seam is fixed in research.md.
- **Principle VII (C086 is an example, not the schema)**: PASS. The rule keys off the
  GENERIC template's structural vocabulary (closed status enum, four-column shape, the
  no-percentage law), table-name-agnostic. Fixtures are synthetic generic scorecards;
  c086/pharmacy is never inlined and the template's illustrative example is excluded.
- **Principle I (Agent-First, Gate-Enforced)**: PASS. The rule is a registered rule
  whose contract is the non-zero `retail check` exit; it fails closed, never advises.
- **Anti-fabricated-confidence (hard rule #9)**: PASS. The rule emits Findings only
  and produces no coverage number; indeed its no-percentage invariant ENFORCES this
  principle on the artifacts it scans.
- **Readiness System spine**: PASS. The rule adds NO new stage and moves NO stage to
  pass. Its roadmap-stage placement (unmapped idea-bank sequence vs an F-row) is an
  Open-for-human item at the ratify gate; the planner does not invent one.
- **Principle IX (Reproducibility / Windows-safe)**: PASS. Pure-Python,
  deterministic, ASCII / UTF-8 no BOM, short paths.
- **Rule-registry integrity (043 snapshot + wiring test)**: PASS. Adding the rule
  updates `EXPECTED_RULE_IDS` AND regenerates the manifest in the same change; a test
  exercises the rule firing, not merely its registration. No numeric baseline count is
  hard-coded.
- **No executor / no deferred capability**: PASS. Pure static text rule; depends on no
  Power BI execution adapter (F016), spec-only runtimes (F031-F033), or live database.

No violations. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/053-coverage-scorecard-linter/
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
```

### Source Code (repository root)

```text
src/retail/
  core.py              # Finding, RuleContext, Severity, is_test_path (READ ONLY -- imported)
  registry.py          # register decorator                            (READ ONLY -- used)
  rules/
    publish_pack.py    # PP1 -- the near-exact structural precedent (READ ONLY -- modeled on)
    scorecard.py       # NEW module for the SL1-family rule

skills/retail-kpi-knowledge/references/
  kpi-coverage-scorecard-template.md
                       # GENERIC template -- READ to derive the status enum + table
                       #   shape; NEVER edited; NEVER scanned at runtime (excluded)

mappings/<table>/
  *coverage-scorecard.md
                       # per-table filled instance(s) the rule scans (NONE exist today;
                       #   the location is the spec Q1 decision so the rule can fire)

docs/rules/
  rules-manifest.json  # regenerated via `retail manifest --repo .`

tests/unit/
  test_rules_wiring.py # EXPECTED_RULE_IDS updated with the new id
  test_scorecard.py    # NEW -- direct firing tests over synthetic well-formed vs
                       #   bad-enum / missing-blocker / unresolved-contract / percentage
```

**Structure Decision**: Single-project layout. The feature adds exactly one
registered rule in a new `src/retail/rules/scorecard.py` (auto-wired by the
registry's `pkgutil` discovery -- no `registry.py` edit), plus its tests, updates the
wiring-test id set, and regenerates the manifest. It modifies NO committed scorecard,
template, or readiness file.

## Phase 0 -- Research (research.md)

Resolve and record (all grounded against the repo; no open technical unknowns):

1. The PP1 shape to mirror (`src/retail/rules/publish_pack.py`): `tracked_files`
   iteration, `is_test_path()` exemption, explicit template-path exclusion,
   section-anchored positional table parse (`[^|]*` non-greedy middle cells so a
   trailing column cannot shift a captured cell), fail-loud-on-unreadable, and the
   "slot present, never grant" Principle-V posture. Decide the reuse seam (a tiny
   shared table-parse/`--`-detection helper vs local patterns) so no divergent parser
   is forked where sharing is cheap; record decision + rejected alternative.
2. The status-enum + table shape derivation from the template
   (`skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`): the
   closed five-value enum, the four-column header
   `| KPI | Contract | Coverage status | Blocker ... |`, the per-table `> Table:` title
   line, the em-dash `--` as the "no contract / no blocker" placeholder, and the
   `contracts/<file>.md` contract-cell form. Record the exact generic anchors.
3. The instance-glob + exclusion (spec Q1/Q2): confirm the rule selects tracked
   `mappings/<table>/**/*coverage-scorecard.md`, EXCLUDES the explicit template path
   (a REFERENCES doc, so PP1's `templates/` prefix does not transfer), and excludes
   `tests/` fixtures. Record that ZERO instances exist today -> silent pass by absence.
4. The conditional contract-path semantics (spec Q3): only `Covered` requires a
   resolving `contracts/<file>.md`; `Planned` / `Out of scope` carry `--`; `Blocked --`
   rows are checked for a named blocker, not a contract path.
5. The no-percentage token definition (spec Q4): a number-then-`%` sequence is the
   forbidden score token; a literal `%` inside a KPI name is NOT a violation.
6. The registration / wiring contract: how `EXPECTED_RULE_IDS` keys off its own length
   (never a literal count), and how `retail manifest --repo .` regenerates
   `docs/rules/rules-manifest.json` guarded by the 043 snapshot test. Record the
   wiring-latent-gap obligation: the new rule must be exercised FIRING on a known-bad
   fixture, not merely listed.

## Phase 1 -- Design

- **data-model.md**: Describe the closed status-enum constant (entity), the
  four-column positional row shape, the per-table title anchor, the em-dash `--`
  placeholder, the percentage-token pattern, the instance-selection predicate
  (instance glob + template + tests exclusion), the registration record (id + title),
  and the Finding shape emitted per violation.
- **contracts/rule-contract.md**: Restate the asserted rule contract as a checkable
  list -- (C1) a status outside the enum -> one Finding naming file+row; (C2) a
  `Blocked -- ...` row with an empty/`--` blocker cell -> one Finding; (C3) a `Covered`
  row citing a non-resolving `contracts/<file>.md` -> one Finding; (C3b) a `Planned` /
  `Out of scope` row with `--` contract -> no Finding; (C4) any cell with a
  number-then-`%` token -> one Finding; (C4b) a `%` inside a KPI name with no
  number-then-`%` token -> no Finding; (C5) a fully well-formed scorecard -> no
  Finding; (C6) the generic template + `tests/` fixtures -> no Finding; (C7) empty
  tree (no instances) -> no Finding (silent pass by absence); (C8) an unreadable
  selected instance -> a fail-loud Finding; (C9) a stray four-column table outside the
  anchored status table contributes no rows; (C10) the rule verifies structure only --
  no adjudication of coverage truth, no readiness grant, no status write
  (Principle V); (C11) registry id set + regenerated manifest + a firing test all
  agree; (C12) no domain-specific artifact anywhere; (C13) severity is uniform
  (recommended ERROR, confirmed at ratify).
- **quickstart.md**: How to run the rule's tests and the snapshot/wiring tests, what
  each proves, and how to regenerate the manifest.

### Post-Design Constitution Re-Check

Unchanged from above -- the design adds one rule, its tests, the id-set update, and
the regenerated manifest; it mirrors PP1's shape and introduces no new violation,
dependency, executor, or severity tier, and writes no committed artifact.

## Complexity Tracking

No constitution violations. Section intentionally empty.
