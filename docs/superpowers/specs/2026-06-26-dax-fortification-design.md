# DAX Fortification — L3 widening + gating, and L2 hygiene rules

- **Date:** 2026-06-26
- **Status:** Design (approved in brainstorming; pending spec review)
- **Builds on:** ADR 0007 (`docs/decisions/0007-dax-governance-layers.md`) — the layered
  DAX governance model (L1 parse / L2 best-practice / L3 contract-drift / L4 value).

## Context

DAX is the analytical backbone — the number a business user reads — and ADR 0007
records it as the least-governed layer. Today:

- **L2 (form)** is partial: 8 home-grown lexical rules (D1–D8) + C1, all in
  `src/seshat/rules/dax.py`, registered and CI-gating via `retail check`.
- **L3 (contract drift)** exists as `src/seshat/metric_drift.py` — it catches the
  "wrong denominator / wrong KPI number" class (the 50.37-vs-33.55 bug) — but is
  **advisory only** (skill-surfaced, never gating) and recognizes only **2** predicate
  spellings, escalating everything else.
- **L1 (parse)** and **L4 (value)** are deferred.

This design fortifies the two layers with the best leverage-for-effort under the repo's
hard constraints: **Phase 1** widens L3 and promotes it to a CI gate; **Phase 2** adds a
batch of stdlib-pure L2 hygiene rules. L1 and L4 remain out of scope (L1's failure mode
is largely blocked by Power BI Desktop before commit; L4 needs data access that breaks
the headless/stdlib model).

## Decisions captured in brainstorming

- **Both layers, phased** — one design doc → two implementation plans.
- **L3 gating posture:** `drift` → ERROR (fails CI); `escalate` → WARNING (never blocks);
  `pass`/`skip` → silent. Only the *confident* verdict gates.
- **Stdlib seam:** L3 runs as its own CI step (`retail semantic-check`, yaml allowed),
  separate from the stdlib-only `retail check`. The core import chain
  (`retail.cli → retail.rules`) never imports yaml.
- **Phase 2 scope:** evidence-driven — include only rules verified **low-false-positive
  AND lexically parser-ready**; cut anything needing a DAX AST (YAGNI).
- **Sequencing:** Approach A — fix the G6 wiring precondition, ship Phase 1 standalone,
  then Phase 2 as a separate plan.

## Two invariants the design must never break

1. **Stdlib-only core.** `pyproject.toml` `dependencies = []`. `retail check`
   (`cli → rules`) imports zero third-party packages. L3 needs `yaml`, so it stays a
   **lazy module + separate subcommand**, never a registered rule. Enforced by the
   subprocess test (`tests/unit/test_metric_drift.py:200-220`) asserting
   `retail.metric_drift` and `yaml` are absent from `sys.modules` after
   `import retail.rules`.
2. **Escalate ≠ drift.** `drift` = recognized mismatch → ERROR (gate fail).
   `escalate` = cannot confidently parse → WARNING (human review, never blocks).
   Never pass-on-uncertain (false negative), never drift-on-uncertain (the S8-over-broad
   false positive). This is ADR 0007's core L3 principle (lines 68-74).

## Architecture

Three work units, strictly ordered:

```
UNIT 0 — G6 wiring fix (precondition, tiny)
  test_rules_wiring.py: add "G6" to EXPECTED_RULE_IDS; add "g6" to the
  importability tuple (line ~17) AND the reload loop (line ~78).
        ↓ unblocks
PHASE 1 — L3 widen + gate (the KPI number)            → Implementation Plan #1
  metric_drift.py : +4 predicate spellings, +additive-measure escalate guard
  cli.py          : NEW `retail semantic-check` subcommand (lazy import,
                    mirrors _run_validate), Verdict→Finding mapping
  ci.yml          : NEW step, yaml-allowed, separate from stdlib core
        ↓ then
PHASE 2 — L2 hygiene D-rules (perf/clarity)           → Implementation Plan #2
  rules/dax.py    : +D9–D12 (lexical, stdlib-pure, registered, WARNING)
  CUT: AST-dependent rules (circular deps, filter-context, type-match) — YAGNI
```

### Why this structure

- Phase 1 is a **new subcommand, not a new rule** — the only way to add yaml-dependent
  gating without polluting the stdlib core. It reuses the proven `_run_validate`
  lazy-import template.
- Phase 2 rules are **registered** lexical checks — they belong in the existing gated
  `retail check` chain, following the D1–D8 pattern.
- **Unit 0 first** because Phase 2 edits `EXPECTED_RULE_IDS` and the reload loop; doing
  that on top of the latent G6 gap would break the suite.

## Unit 0 — G6 wiring fix (precondition)

**Verified latent gap:** G6 is registered (`src/seshat/rules/g6.py:49`,
`@register("G6", "No real host/value in committed PBIP parameters")`) and imported
(`src/seshat/rules/__init__.py:14`), so the live registry has **28 rules**. But
`tests/unit/test_rules_wiring.py`:

- `EXPECTED_RULE_IDS` (lines ~35-65) does **not** list `"G6"`.
- The importability tuple (line ~17) and the reload loop (line ~78) both omit `"g6"`
  (they cover only `git_meta, sql, dax, pbir`).

The suite passes today only by **omission symmetry** — `g6` is never reloaded against
the cleared registry, so `G6` never enters `actual`, so `actual == EXPECTED_RULE_IDS`
holds. Adding `g6` to the reload loop (the natural move when adding any rule) breaks the
test unless `G6` is also added to the expected set.

**Fix:** add `"G6"` to `EXPECTED_RULE_IDS`; add `"g6"` to both submodule tuples (lines
~17 and ~78). After the fix the wiring test validates all 28 rules. Run the full suite to
confirm green.

## Phase 1 — L3 widen + gate

### 1a. Widen the predicate whitelist (`metric_drift.py`)

Current: only `NOT(ISBLANK(col))` → `is_not_null` and `col = TRUE()` → `is_true`
(lines 69-75). Add **4** tight, type-knowledge-free equivalents. Every column capture is
routed through the existing `_strip_column_qualification` safety valve (lines 78-88,
`re.fullmatch` of bracket notation, `""` → escalate), so a loose `(?P<col>.+?)` capture
cannot admit a function call or measure ref as a "column." All patterns inherit
`re.IGNORECASE | re.DOTALL` (DOTALL is adversary-hardening: `.` matches newlines, blocking
newline-insertion attacks).

| New DAX spelling | maps to | regex (IGNORECASE \| DOTALL) |
|---|---|---|
| `col <> BLANK()` | `is_not_null` | `^(?P<col>.+?)\s*<>\s*BLANK\s*\(\s*\)$` |
| `ISBLANK(col)=FALSE()` | `is_not_null` | `^ISBLANK\s*\(\s*(?P<col>.+?)\s*\)\s*=\s*FALSE\s*\(\s*\)$` |
| `TRUE() = col` | `is_true` | `^TRUE\s*\(\s*\)\s*=\s*(?P<col>.+?)$` |
| `col <> FALSE()` | `is_true` | `^(?P<col>.+?)\s*<>\s*FALSE\s*\(\s*\)$` |

**Explicitly NOT added (stay escalating):** `LEN(col)<>0`, `COALESCE(...)`, `HASVALUE`,
`col = 1` (all need type inference); order-flipped / conditional forms (low frequency);
new ops `is_false`, `value_equality`, `in_set` (require contract-schema changes —
deferred). New ops, if ever added, must be widened at **both** whitelist sites: the DAX
regexes (lines 69-75) **and** `_contract_filters` (line 200,
`op not in ("is_not_null", "is_true")`), or contracts using them escalate at load time
before any DAX is read.

### 1b. Additive-measure escalate guard (`metric_drift.py`)

**Verified gap:** `check_measure_drift` (lines 206-254) never reads
`definition['additive']`, so a measure marked `additive: true` would be run through
ratio/denominator logic. Add an early guard after the existing `skip` check:

```python
if definition.get("additive") is not False:
    return Verdict("escalate",
                   "additive measure; denominator filter-set logic does not apply")
```

Non-breaking — both shipped measures (`DiscountedTransactionRate`, `AvgTransactionValue`)
set `additive: False`.

### 1c. Recognized measure shapes (no change; documented for clarity)

`_normalize_denominator` (lines 145-169) recognizes bare `[Measure]`,
`CALCULATE([Measure])` (empty wrapper → bare), and
`CALCULATE([Measure], p1, p2, …)`. These stay. The following **stay escalating** (do not
widen): `CALCULATE([M], TRUE())` (semantic no-op keeps its predicate), nested
`CALCULATE`, `VAR/RETURN`, `DIVIDE(num, SUM(...))` (aggregation denominator).

### 1d. New `retail semantic-check` subcommand (`cli.py`)

Mirrors the `_run_validate` lazy-import template exactly:

- **Parser:** add `sub.add_parser("semantic-check", help="L3 contract<->DAX denominator
  drift on committed metric contracts")` after the `validate` block, with the repo arg and
  a contracts-glob/path arg.
- **Dispatch:** add `if args.command == "semantic-check": return _run_semantic_check(args)`
  after the existing dispatch branches.
- **Handler `_run_semantic_check(args)`:** `from .metric_drift import load_definition,
  check_measure_drift` **inside the function only** (never module scope) → iterate metric
  contracts, pair each with its measure's DAX (sourced from the model TMDL), call
  `check_measure_drift`, map verdicts → `Finding`, print via the runner formatter, return
  the exit code.

### 1e. Verdict → Finding → exit code

| `Verdict.status` | Severity | Gate effect |
|---|---|---|
| `drift` | `Severity.ERROR` | fails CI (exit 1) — the wrong number |
| `escalate` | `Severity.WARNING` | surfaced, does NOT block — human review |
| `pass` | none | silent |
| `skip` | none | silent (contract has no `definition` block yet) |

`Finding` fields per `core.py:15-20`: `(rule_id, severity, message, locator)`. For L3,
`rule_id` is a stable tag (e.g. `"L3"`), `locator` is the contract path (POSIX
`path:line`). Exit code 1 iff any ERROR, mirroring `runner.py:72` and `_run_validate`.

### 1f. CI step (`.github/workflows/ci.yml`)

Add a **new step after** the existing `retail check` step (after line ~53) running bare
`retail semantic-check` (no `--commit-range`; it reads committed TMDL + contracts, not
git diffs). It runs where `yaml` is installed, kept **separate** so the stdlib-only
`check` job never imports yaml. Both steps must pass to merge.

## Phase 2 — L2 hygiene D-rules

Registered, stdlib-pure, **lexical** rules in `rules/dax.py`, following the D1–D8 pattern
(scan via `iter_model_files`, which auto-exempts `tests/`; yield `Finding`). Final IDs
assigned contiguously at plan time (D9 onward). All **WARNING** severity (hygiene/perf,
not correctness — making them ERROR would block valid-but-imperfect DAX, repeating the
S8-over-broad lesson; promotion to ERROR is a later owner decision).

| candidate | intent | severity | lexical signal | status |
|---|---|---|---|---|
| Dn | No hardcoded date literals in measures (use the date table) | WARNING | `DATE\s*\(\s*\d{4}` or quoted ISO date on a `measure` line | INCLUDE |
| Dn | Every measure carries a description/doc annotation | WARNING | `measure X = …` block lacks a following `///` doc or `description` property | INCLUDE |
| Dn | No `FILTER(ALL(...))` full-table-scan anti-pattern | WARNING | `FILTER\s*\(\s*ALL\s*\(` in a measure expression | INCLUDE |
| Dn | Division-hygiene reinforcement beyond D4 | WARNING | bare `/` in measure contexts D4 does not already cover | INCLUDE **only if** it catches signal D4 misses; else FOLD into D4 |

**CUT under YAGNI (need a DAX AST the repo deliberately lacks):**

- Circular measure-dependency detection (needs a dependency graph).
- CALCULATE filter-context correctness (a real DAX engine; this is L3 escalate territory,
  not a lexical rule).
- Return-type / format-string match (needs type inference).

Naming the cuts explicitly prevents future maintainers from re-litigating them: the repo
has no DAX AST by design, and L3's escalate-by-default already covers "can't lexically
prove this."

## Data flow

**Phase 1 (`retail semantic-check`):**

```
metric contracts (mappings/**/metrics/*.yaml)
  → load_definition(path)  [lazy import yaml]
  → definition.denominator.filter ┐
  measure DAX (from TMDL)          ├→ check_measure_drift(dax, definition)
                                   ┘     → Verdict(pass|drift|escalate|skip)
  → _run_semantic_check maps Verdict → Finding(severity) → runner format → exit code
```

**Phase 2 (`retail check`, existing path):**

```
tracked TMDL → iter_model_files (exempts tests/) → parse_tmdl
  → Dn lexical scan → Finding(WARNING) → runner → report
```

## Error handling

- **L3:** escalate-by-default for unbalanced parens, unknown predicate, non-DIVIDE
  measure, malformed contract, additive measure. Never crashes, never silently passes.
- **Phase 2:** malformed TMDL → `parse_tmdl` returns `None` → skipped (existing
  behavior); no rule raises.
- **Locators:** repo-relative POSIX `path:line` (forward slashes; Windows backslashes
  break downstream tooling).

## Testing

- **Each Phase 2 rule:** mandatory 4-test pattern — `flags_*` (count, rule_id, severity,
  message substring), `passes_clean`, locator (`endswith(":N")`), `exempts_tests_prefix`.
  Fixtures in `tests/fixtures/tmdl/` named `bad_*`/`clean_*`, staged via `_ctx`.
- **Phase 1:** a `pass` test per new recognized spelling; an `escalate` test for the
  additive guard; existing pass/drift/escalate/skip tests stay green.
- **Wiring test:** Unit 0 fixes G6 symmetry; each new D-id is then added to
  `EXPECTED_RULE_IDS` together with its `@register` decorator (3 coordinated edits).
- **Stdlib invariant (non-negotiable):** keep the subprocess test green
  (`retail.metric_drift`/`yaml` absent after `import retail.rules`); add a cli-side
  source-scan asserting no module-scope `import yaml`/`from .metric_drift` in `cli.py`
  (mirrors `test_validate_targets.py:270-280`).

## Units summary

| Unit | File(s) | Purpose | Depends on |
|------|---------|---------|------------|
| 0 | `tests/unit/test_rules_wiring.py` | Fix G6 wiring symmetry | — |
| 1a | `src/seshat/metric_drift.py` | +4 predicates, +additive guard | — |
| 1b | `src/seshat/cli.py` | `semantic-check` subcommand + Verdict→Finding | 1a |
| 1c | `.github/workflows/ci.yml` | separate gated step | 1b |
| 2 | `src/seshat/rules/dax.py`, `tests/unit/test_dax.py`, `tests/unit/test_rules_wiring.py` | Dn hygiene rules | 0 |

## Consequences

- The wrong-KPI-number class becomes **CI-gated**, contract-anchored, deterministically,
  with no DAX engine and no dependency in the stdlib core (yaml stays in a separate gated
  step). L3 graduates from advisory to enforced for the `drift` verdict.
- L3 recognizes 6 predicate spellings instead of 2 — fewer false escalations, more
  confident verdicts — while keeping the escalate-by-default safety bias.
- A latent wiring bug (G6) is fixed; the wiring test now validates all 28 rules.
- L2 gains a batch of stdlib-pure hygiene rules (WARNING), CI-gating via `retail check`.
- The design under-claims by design (escalate the unrecognized, WARNING the hygiene)
  rather than over-claims — the correct bias for a governance layer.

## Out of scope (explicit)

- **L1 (parse):** deferred — Power BI Desktop blocks unparseable DAX before save.
- **L4 (value):** deferred — needs data access, breaks the headless/stdlib model.
- **New L3 ops** (`is_false`, `value_equality`, `in_set`): deferred — require
  contract-schema changes (a `value` field; a `values` set with order-independent
  frozenset compare and a cardinality cap).
- **Promoting Phase 2 rules or L3 escalate to ERROR:** a later owner decision.

## See also

- ADR 0007: `docs/decisions/0007-dax-governance-layers.md`
- The module + tests: `src/seshat/metric_drift.py`, `tests/unit/test_metric_drift.py`
- Existing rules + tests: `src/seshat/rules/dax.py`, `tests/unit/test_dax.py`
- Wiring test: `tests/unit/test_rules_wiring.py`
- Stdlib-pure precedent: `src/seshat/validate_targets.py`,
  `tests/unit/test_validate_targets.py:270-280`
- CLI + runner: `src/seshat/cli.py`, `src/seshat/runner.py`, `src/seshat/core.py`
