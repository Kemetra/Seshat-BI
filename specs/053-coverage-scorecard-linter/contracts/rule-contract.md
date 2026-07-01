# Rule Contract: Coverage Scorecard Linter (SL1)

The checkable contract for the new rule. Each clause is a test obligation. Fixtures
are generic synthetic scorecards; NO domain-specific table / column / KPI name and NO
inlined worked-example answers appear anywhere (Principle VII / hard rule #7).

- **C1 -- bad enum**: a committed instance whose Coverage status cell (col 3) holds a
  value outside the closed five-value enum -> exactly one ERROR Finding naming the
  file + row/KPI and the invalid status.
- **C2 -- missing blocker**: a row whose status is `Blocked -- missing field` or
  `Blocked -- needs business definition` and whose Blocker cell (col 4) is empty or a
  bare `--` -> exactly one ERROR Finding for the missing named blocker.
- **C3 -- unresolved contract (Covered)**: a row whose status is `Covered` and whose
  Contract cell cites a `contracts/<file>.md` that is not a tracked file -> exactly
  one ERROR Finding for the unresolved contract path.
- **C3b -- Planned / Out of scope carry `--`**: a row whose status is `Planned` or
  `Out of scope` with a `--` Contract cell -> NO Finding (exempt from
  contract-path-resolves).
- **C4 -- percentage present**: an instance with a number-then-`%` token (e.g. `70%`)
  in any status-table cell -> exactly one ERROR Finding for the fabricated-confidence
  percentage.
- **C4b -- `%` in a KPI name**: a KPI name containing a literal `%` with NO adjacent
  digit -> NO Finding (the no-percentage law targets a score token, not the glyph).
- **C5 -- well-formed passes**: an instance where every row has a valid status, every
  Blocked -- row names a blocker, every Covered row cites a resolving contract path,
  and no cell holds a percentage token -> NO Finding.
- **C6 -- template + fixtures excluded**: the generic template file at
  `skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md` (with
  its `<placeholder>` tokens and illustrative worked example) and committed `tests/`
  fixtures -> NO Finding.
- **C7 -- empty tree**: a tracked-file set containing zero scorecard instances -> NO
  Finding, no crash (silent pass by absence).
- **C8 -- unreadable instance**: a tracked-but-unreadable selected instance -> a
  fail-loud ERROR Finding rather than a crash (PP1 precedent).
- **C9 -- anchored parse**: a stray four-column table elsewhere in the same document
  contributes no rows and masks no malformed row (the status table is anchored by the
  `> Table:` title / the four-column header).
- **C10 -- Principle-V structure-only**: no code path decides whether a stated
  `Covered` is TRUE, grants any readiness stage, or populates/modifies a status; the
  rule verifies STRUCTURE only.
- **C11 -- wired AND exercised**: the live registry id set equals `EXPECTED_RULE_IDS`
  (with `SL1` added), `len(all_rules()) == len(EXPECTED_RULE_IDS)`, the regenerated
  `docs/rules/rules-manifest.json` contains the id, AND at least one test invokes the
  rule directly on a known-bad fixture and asserts a non-empty Finding set (closes the
  wiring-latent-gap).
- **C12 -- generic-only**: the rule, its enum constant, and every fixture contain no
  domain-specific schema artifact; the template's illustrative answers are never
  inlined as fixture content.
- **C13 -- severity**: every Finding uses one uniform severity (RECOMMENDED
  `Severity.ERROR`; the final posture is confirmed at human ratification).
- **C14 -- stdlib-only / no execution**: the rule imports only `re` / `pathlib` +
  `retail.core` / `retail.registry`, opens no network/DB/Power BI connection, runs no
  query/DAX/agent, stays import-safe at module scope, and writes no file (SC-008 /
  Never-Execute B1/B3 family).
