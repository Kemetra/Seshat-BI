# Phase 0 Research: Coverage Scorecard Linter (SL1)

All decisions are grounded against the repo; there are no open technical unknowns.
Governance placement (roadmap stage) and the Principle-V boundary confirmation are
Open-for-human items, not technical unknowns, and are NOT resolved here.

## R1 -- The PP1 shape to mirror, and the reuse seam

**Finding**: `src/retail/rules/publish_pack.py` (PP1) is the near-exact structural
precedent. It: iterates `ctx.tracked_files`; excludes an explicit template path and
`is_test_path()` fixtures (`_iter_packs`); anchors its parse to a heading and stops
at the next heading (`_index_section_lines`); parses rows POSITIONALLY with
non-greedy `[^|]*` middle cells so an extra trailing column cannot shift the captured
cell (`_INDEX_ROW_RE`); reads with `encoding="utf-8-sig"`; converts an `OSError` into
a fail-loud `Severity.ERROR` Finding; and emits ERROR Findings only. Its module
docstring records the Principle-V "slot present, never grant" posture.

**Decision**: `scorecard.py` re-derives the small regex patterns it needs LOCAL to
the module (the status-table header/row patterns, the `> Table:` title anchor, the
`contracts/<file>.md` and number-then-`%` patterns), matching PP1's own style
(PP1 keeps its patterns local; it does not import from another rule). A shared helper
is NOT extracted because the patterns are rule-specific (PP1 parses a
required-section INDEX; SL1 parses a KPI status table) and premature sharing would
couple two rules with different table shapes.

**Rejected alternative**: import PP1's `_INDEX_ROW_RE` / `_PLACEHOLDER_RE`. Rejected
because the scorecard table is a different shape (four columns keyed by KPI name, not
a-f index rows) and the placeholder polarity differs; reuse would misfit. The em-dash
`--` (not `<...>`) is the scorecard's "empty" placeholder, so PP1's angle-bracket
regex does not apply.

## R2 -- Status enum + table shape (from the template)

**Finding** (from `skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`):

- Closed status enum (use exactly these five): `Covered`,
  `Blocked -- missing field`, `Blocked -- needs business definition`, `Planned`,
  `Out of scope`. (The template renders the dash as an en-dash glyph; SL1 authored
  artifacts and matching normalize to ASCII `--` per rule IX, and the matcher must be
  dash-normalizing so an en-dash or `--` both parse -- recorded as a matching note.)
- Table header (four columns):
  `| KPI | Contract | Coverage status | Blocker (named field / undecided policy) |`.
- Per-table title line: `> Table: \`<schema.table>\` -- <one-line grain>`.
- Contract cell form: `contracts/<file>.md` OR the em-dash `--` (Planned / Out of
  scope legitimately carry `--`).
- The no-percentage law: "Coverage is expressed as an explicit status + blocker,
  never a number or percentage ... if tempted to compute a percentage, stop."

**Decision**: SL1 keys off the four-column header + the `> Table:` title as the
anchor, parses the status (col 3) and blocker (col 4) and contract (col 2)
positionally with non-greedy middle cells (PP1 precedent), and validates against the
closed enum. Dash normalization (en-dash / em-dash / `--`) is applied before enum
comparison so a template-styled instance is not falsely flagged.

## R3 -- Instance glob + exclusion (spec Q1 / Q2)

**Finding**: `glob mappings/**/*scorecard*.md` returns NOTHING on main today; only the
generic template exists (under `skills/retail-kpi-knowledge/references/`, NOT under
`templates/`).

**Decision** (spec Q1/Q2): the rule selects tracked files matching the suffix
`coverage-scorecard.md` under `mappings/` (the PP1 per-table instance home),
EXCLUDES the one explicit template path
`skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`, and
excludes `is_test_path()` fixtures. Because the template is a REFERENCES doc, PP1's
`templates/` directory-prefix exclusion does not transfer -- an explicit-path
exclusion is used. With zero instances committed, the rule reports zero Findings by
absence (a silent pass), not by clean instances; it must not crash on an empty match.

**Rejected alternative**: scanning ANY `*scorecard*.md` anywhere. Rejected because it
would risk scanning the template (already excluded) and any unrelated doc; pinning to
`mappings/` + the `coverage-scorecard.md` suffix keeps the target the per-table
artifact kind.

## R4 -- Conditional contract-path semantics (spec Q3)

**Decision**: only `Covered` requires a `contracts/<file>.md` that resolves to a
tracked file. `Planned` and `Out of scope` legitimately carry `--` and are EXEMPT.
`Blocked -- missing field` and `Blocked -- needs business definition` are checked for
a named BLOCKER (col 4 non-empty and not bare `--`), NOT for a resolving contract
path. This mirrors the template's "Covered = contract Seeded AND fields present"
semantic without adjudicating whether the contract is truly Seeded (Principle V).

## R5 -- No-percentage token definition (spec Q4)

**Decision**: the forbidden token is a NUMBER immediately followed by `%` (regex
`\d%`, i.e. a digit adjacent to `%`, e.g. `70%`, `70 %` is out of scope as a single
token -- the score signature is digit-then-`%`). A literal `%` inside a KPI name with
no adjacent digit (e.g. a KPI named "Returns Rate % (Value)") does NOT trip the rule.
This enforces hard rule #9 (no fabricated numeric coverage score) without a false
positive on `%`-named KPIs.

## R6 -- Registration / wiring / manifest contract

**Finding**: `tests/unit/test_rules_wiring.py` holds `EXPECTED_RULE_IDS` (currently 38
ids: S/D/R/A/B/C/G/P + PP1/SC1/DF1); `test_registered_rule_ids_match_expected_set`
asserts `actual == EXPECTED` and `len(all_rules()) == len(EXPECTED_RULE_IDS)` (no
literal count). Rule submodules are auto-discovered via `pkgutil.iter_modules`, so a
new `rules/scorecard.py` needs NO `registry.py` edit. `docs/rules/rules-manifest.json`
is regenerated via `retail manifest --repo .` (CLI `manifest` subcommand) and guarded
by the 043 snapshot test.

**Decision**: add the working id `SL1` to `EXPECTED_RULE_IDS` (one-line comment) in
the same change, regenerate the manifest, and include a test that invokes the rule
directly on a known-bad fixture and asserts a non-empty Finding set (closing the
recorded wiring-latent-gap: registered AND exercised firing). The id `SL1` is a
RECOMMENDATION pending human ratification (spec ## Clarifications); do not treat it as
final. The live baseline is 38 ids -> 39 after this change; the spec/tasks key off the
live set length, never the stale "33/34" backlog-panel prose.
