# Implementation Plan: Publish-pack completeness gate (PP1)

**Branch**: `049-publish-pack-completeness-gate` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/049-publish-pack-completeness-gate/spec.md`

## Summary

Add ONE static rule that fails closed on an INCOMPLETE committed BI handoff pack.
The rule scans every per-table instance at
`mappings/<table>/handoff/bi-handoff-pack.md`, confirms each required section of
the generic template is PRESENT and FILLED, and emits a Finding for every required
section that is absent or still unfilled. "Unfilled" is detected by reusing `G6`'s
angle-bracket `<placeholder>` convention with inverted polarity (in a pack a
remaining `<placeholder>` marks an UNFILLED section), plus the template's literal
`GAP` resolution token, read from the STRUCTURED required-section-index "Resolved?"
position -- never a free-text substring scan. The rule parses committed text with
the stdlib only, never opens a database/network/Power BI connection, skips the
generic template and committed test fixtures, and silent-passes on a tree with no
packs. Registering the rule also updates the wiring test's expected id set and
regenerates `docs/rules/rules-manifest.json`, and a test exercises the rule firing
on a known-bad fixture (closing the prior wiring-latent-gap). It is the
completeness sibling of `G6` (parameter hygiene) and follows the just-shipped `B3`
shape (new file-scanning rule, reuses an existing mechanism, one new id,
closed-set-at-ratify).

## Technical Context

**Language/Version**: Python 3.11+ (matches the existing `src/retail` package and
`tests/unit` suite).

**Primary Dependencies**: standard library only (`re`, `pathlib`). No new runtime
or test dependency. The rule imports `retail.core` (`Finding`, `RuleContext`,
`Severity`, `is_test_path`) and `retail.registry` (`register`). It reuses `G6`'s
placeholder-detection mechanism -- the angle-bracket `<...>` convention; the exact
reuse seam (import `g6._PLACEHOLDER_RE` vs lift the one-line pattern into a shared
helper) is a Phase-0 decision recorded in research.md, chosen so the rule does NOT
fork a second placeholder parser (Principle II).

**Storage**: N/A. The rule reads tracked files as text via the existing
`RuleContext` (`repo_root`, `tracked_files`); it opens no database and holds no
connection. It NEVER writes any file (in particular it never writes an approval).

**Testing**: pytest, marked `pytest.mark.unit`. New unit tests for the rule over
generic/synthetic filled vs placeholder/GAP handoff-pack fixtures, plus the
existing rule-registry snapshot / wiring tests (`tests/unit/test_rules_wiring.py`).

**Target Platform**: Local dev + CI (Windows-first per repo `CLAUDE.md`;
platform-agnostic Python).

**Project Type**: Single project (library + CLI under `src/retail`, tests under
`tests/`).

**Performance Goals**: N/A (a handful of text reads + regex scans over the small
set of committed handoff packs during the static gate; one pack exists today).

**Constraints**: stdlib-only, opens no network/DB connection, requires no
credentials, never writes a file. ASCII / UTF-8 without BOM. Generic section
markers and synthetic pack fixtures only -- no domain-specific table, column, KPI,
or PII rule, and the worked-example (c086) answers are never inlined.

**Scale/Scope**: One rule registration + one explicit required-section-set
constant + the wiring-test id-set update + the regenerated manifest + new unit
tests. No production artifact (no handoff pack, no readiness file) is modified; the
rule never moves a readiness stage to pass.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle V (Agent Stops at Judgment Calls)**: PASS with the load-bearing
  boundary. The rule checks the publish-approval section is present-and-non-placeholder
  ONLY; it never reads WHO signed, the date, or legitimacy, and never populates,
  grants, or self-validates an approval. The human sign-off stays a human seam. The
  exact boundary confirmation is an Open-for-human item at the ratify gate.
- **Principle VIII (Static-First Governance, Live Deferred)**: PASS. The guard is
  part of the stdlib-only, CI-able static core; it reads committed text, parses-not-
  executes, and never opens a connection. It joins `retail check`, not `retail validate`.
- **Principle II (Depend, Never Fork)**: PASS. The rule reuses `G6`'s placeholder-
  detection mechanism rather than authoring a second placeholder parser (the reuse
  seam is fixed in research.md), mirroring how `B3` reused `B1`'s AST helper.
- **Principle VII (C086 is an example, not the schema)**: PASS. The rule keys off
  the GENERIC template's structural markers (required-section index + placeholder/GAP
  convention), table-name-agnostic. Fixtures are synthetic generic packs; c086 is a
  cited filled instance only, never inlined.
- **Principle I (Agent-First, Gate-Enforced)**: PASS. The rule is a registered rule
  whose contract is the non-zero `retail check` exit; it fails closed, never merely
  advises.
- **Readiness System spine**: PASS. The rule governs Stage 7 (Publish Ready)
  completeness over the already-shipped F013 handoff pack; it adds NO new stage and
  moves NO stage to pass. The exact stage assignment + roadmap provenance row is an
  Open-for-human item at the ratify gate (the planner does not invent one).
- **Anti-fabricated-confidence**: PASS. The rule emits Findings only; it produces no
  readiness/confidence number.
- **Principle IX (Reproducibility / Windows-safe)**: PASS. Pure-Python,
  deterministic, ASCII / UTF-8 no BOM, short paths.
- **Rule-registry integrity (043 snapshot + wiring test)**: PASS. Adding the rule
  updates `EXPECTED_RULE_IDS` AND regenerates the manifest in the same change; a
  test exercises the rule firing, not merely its registration. No numeric baseline
  count is hard-coded.
- **No executor / no deferred capability**: PASS. Pure static text rule; depends on
  no Power BI execution adapter (F016), spec-only runtimes (F031-F033), live
  database, or the Publish Approval Receipt (spec 041) having shipped.

No violations. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/049-publish-pack-completeness-gate/
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
    g6.py              # G6 + the _PLACEHOLDER_RE placeholder mechanism
                       #   (the placeholder mechanism is REUSED unchanged;
                       #    the reuse seam is fixed in research.md)
    publish_pack.py    # NEW module for the PP1-family rule

templates/handoff/
  bi-handoff-pack.md   # GENERIC template -- READ to derive the required-section
                       #   set; NEVER edited by the rule; NEVER scanned at runtime

mappings/<table>/handoff/
  bi-handoff-pack.md   # per-table instance(s) the rule scans (one exists today:
                       #   mappings/retail_store_sales/handoff/bi-handoff-pack.md)

docs/rules/
  rules-manifest.json  # regenerated via `retail manifest --repo .`

tests/unit/
  test_rules_wiring.py # EXPECTED_RULE_IDS updated with the new id
  test_publish_pack.py # NEW -- direct firing tests over synthetic filled vs
                       #   placeholder/GAP generic packs
```

**Structure Decision**: Single-project layout. The feature adds exactly one
registered rule in a new `src/retail/rules/publish_pack.py` (auto-wired by the
registry's `pkgutil` discovery -- no `registry.py` edit), plus its tests, updates
the wiring-test id set, and regenerates the manifest. It modifies NO committed
handoff pack, template, or readiness file.

## Phase 0 -- Research (research.md)

Resolve and record (all grounded against the repo; no open technical unknowns):

1. The exact reusable placeholder mechanism in `g6.py`
   (`_PLACEHOLDER_RE = re.compile(r"<[^>]+>")`) and the polarity inversion PP1 needs
   (G6: placeholder = safe; PP1: remaining placeholder = unfilled = flag). Decide
   the reuse seam (import `g6._PLACEHOLDER_RE` directly vs lift it into a tiny shared
   helper module both rules import) so no second parser is forked -- record decision
   + rejected alternative.
2. The required-section set derivation from `templates/handoff/bi-handoff-pack.md`:
   the six required-section-INDEX rows a-f and the structured "Resolved?" cell that
   carries the `<path / GAP>` / `<recorded / GAP>` marker. Record the exact, generic,
   table-agnostic anchors the rule keys off (section headings / index rows) and that
   the GAP/placeholder signal is read from the structured "Resolved?" position, not
   free-text.
3. The file-location + exemption pattern: how `G6` enumerates `ctx.tracked_files`
   and applies `is_test_path()`; confirm PP1 selects only
   `mappings/*/handoff/bi-handoff-pack.md`, excludes the `templates/...` generic
   template, and excludes `tests/` fixtures.
4. The registration / wiring contract: how `EXPECTED_RULE_IDS` keys off its own
   length (never a literal count), and how `retail manifest --repo .` regenerates
   `docs/rules/rules-manifest.json` guarded by the 043 snapshot test.
5. The recorded wiring-latent-gap: the new rule must be exercised firing on a
   known-bad fixture, not merely listed -- record the test obligation.
6. The Principle-V boundary: confirm the approval-slot check is presence-and-non-
   placeholder ONLY and record that no code path reads/validates/writes the sign-off.

## Phase 1 -- Design

- **data-model.md**: Describe the required-section-set constant (entity), the reused
  placeholder mechanism (referenced, not redefined), the incompleteness markers
  (`<placeholder>` + `GAP`), the pack-selection predicate (instance paths only,
  template + tests excluded), the registration record (id + title), and the Finding
  shape emitted per missing/unfilled section.
- **contracts/rule-contract.md**: Restate the asserted rule contract as a checkable
  list -- (C1) a required section left as `<placeholder>` -> one Finding naming the
  pack + section; (C2) a required section's structured "Resolved?" cell = `GAP` ->
  one Finding; (C3) a missing required-section heading -> one Finding; (C4) a fully
  filled pack -> no Finding; (C5) the generic template + `tests/` fixtures -> no
  Finding; (C6) empty tree (no packs) -> no Finding; (C7) unreadable pack ->
  fail-loud Finding; (C8) the approval-slot check is presence-and-non-placeholder
  only -- no read/validate/write of the sign-off; (C9) registry id set + regenerated
  manifest + a firing test all agree; (C10) no domain-specific artifact anywhere;
  (C11) severity is uniform (recommended ERROR, confirmed at ratify).
- **quickstart.md**: How to run the rule's tests and the snapshot/wiring tests, what
  each proves, and how to regenerate the manifest.

### Post-Design Constitution Re-Check

Unchanged from above -- the design adds one rule, its tests, the id-set update, and
the regenerated manifest; it reuses `G6`'s placeholder mechanism and introduces no
new violation, dependency, executor, or severity tier, and writes no committed
artifact.

## Complexity Tracking

No constitution violations. Section intentionally empty.
