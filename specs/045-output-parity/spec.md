# Feature Specification: Text/JSON Output Equivalence Property Test

**Feature**: none (no roadmap F-number -- this idea is from the exploratory idea-bank, `docs/roadmap/idea-backlog.md`; the backlog "V7 / F8" tag is the scoring panel's value/feasibility score per the Legend, NOT a roadmap feature number -- roadmap F8 is the "KPI Coverage Scorecard", unrelated. Promotion + F-numbering is a human decision) | **Spec directory**: `045-output-parity` (next free on-disk slot; the create-new-feature script proposed `044` but four concurrent sibling workflows had already claimed `044-*` branch names, so this feature took `045` via the script's `--number` escape hatch)

**Feature Branch**: `045-output-parity` (located via `.specify/feature.json`)

**Created**: 2026-06-29

**Status**: Ratified (Ahmed Shaaban, 2026-06-29)

**Input**: User description: "Text/JSON Output Equivalence Property Test"

**Readiness stage advanced**: none -- this is meta-infrastructure that hardens the static `retail check` governance core itself; it does NOT advance any source/table/report readiness stage (Source -> Mapping -> Silver -> Gold -> Semantic -> Dashboard -> Publish). Consistent with the prior idea-bank B-series (B1/B2) and feature 043, idea-bank items advance no readiness stage. This work adds NO new registered rule and NO new `EXPECTED_RULE_ID`.

## Clarifications

This block records the load-bearing ambiguities. Items marked Principle-V are deliberate
judgment calls the agent did NOT answer (constitution Principle V); they are reserved for the
human owner to rule at ratification. Ordinary ambiguities resolved by the advisor during
clarification are recorded under the dated session below.

### Owner judgment calls (Principle V -- NOT answered by the agent; for the owner at ratification)

- **[RESOLVED -- Principle V] Roadmap promotion + feature number.** Should this internal
  governance-core hardening test be promoted to a roadmap F-row (and given an F-number), or stay
  an unmapped repo-hygiene item like the prior B-series? **OWNER RULING (2026-06-29): stay
  unmapped repo-hygiene item** -- no roadmap F-row, no F-number; advances no readiness stage,
  matching the prior idea-bank B-series (B1/B2) precedent. Promotion remains available later as a
  fresh human decision. (Ruling supplied by the repo owner via Session 1; recorded here verbatim.)

### Session 2026-06-29

> Session date filled at ratification by the repo owner (Ahmed Shaaban, 2026-06-29).
>
> The advisor recommendations below were integrated into the spec body during clarification
> (highest Impact*Uncertainty first). The Principle-V item above was REFUSED by the agent and
> reserved for the human owner.

- **Q1 (fixture scope: synthetic vs. real registry) -- RESOLVED.** Should the parity property run
  over the REAL registered rule set (`all_rules()` driven over a committed tmp-repo fixture) or
  over SYNTHETIC `RegisteredRule` stubs? RECOMMENDED: **synthetic `RegisteredRule` stubs**
  (the pattern `tests/unit/test_runner.py` already uses). Reasoning: the property under test is
  the agreement of the `run()`/`run_json()` PLUMBING (text-render path vs. `_collect`/`_exit_code`
  path), which is fully exercised by synthetic findings; a real-registry fixture is not confirmed
  to exist (grounding flagged it as unconfirmed), would couple the test to the live rule set, and
  would risk dragging C086/pharmacy locators into the fixtures (Principle VII). The synthetic
  approach is buildable today, keeps the test C086-agnostic, and does not depend on any
  unconfirmed artifact. Reversible: a later spec could add a real-registry variant on top without
  removing the synthetic property.
- **Q2 (parser robustness: inverse-of-`_format` ambiguity) -- RESOLVED.** `_format` renders
  `"[{sev}] {rule_id} {message} ({locator})"`; a free-text message containing `") ("` or brackets
  makes a naive inverse parser ambiguous. How does the test compare the two paths without a
  brittle parser? RECOMMENDED: **the test CONTROLS its synthetic fixtures so every finding's
  text line is unambiguously parseable** (messages and locators in the fixtures contain no
  embedded `") ("`, no unescaped brackets) AND the comparison reconstructs a multiset (Counter)
  of structured `(rule_id, severity, message, locator)` tuples from the text lines, comparing it
  to the same multiset built from `run_json()`'s findings. Reasoning: the property's job is to
  prove the two PATHS agree on the SAME inputs, not to prove a general-purpose stdout parser is
  robust against adversarial messages; pinning the fixtures to parseable shapes keeps the test
  deterministic and avoids re-implementing a fragile reverse-renderer. The fixtures MUST include
  at least one finding per severity and at least one rule yielding multiple findings, so the
  multiset comparison is non-trivial. Reversible.
- **Q3 (comparison key: full tuple vs. id-only) -- RESOLVED.** What is the equivalence key the
  parity asserts over? RECOMMENDED: **the full structured tuple** `(rule_id, severity, message,
  locator)` -- the same four fields `Finding.to_dict()` / `FindingDict` pin -- compared as an
  ORDER-INSENSITIVE multiset (`collections.Counter`), per the idea. Reasoning: `run()` emits in
  inline rule order and `run_json()` in `_collect` order; both are rule order today, but the
  property must NOT depend on ordering (it is testing equivalence of CONTENT, not of sequence),
  so a Counter over the full tuple is the correct, immutability-respecting comparison (Finding is
  a frozen dataclass; the test never mutates or re-sorts in place). The exit-code half of the
  property is asserted separately and directly (`run()` return value == `run_json()` return
  value). Reversible.

> Clarify-pass confirmation: a dedicated clarification pass reviewed the spec for further
> underspecified areas (max 5, highest Impact*Uncertainty first). The three load-bearing
> ambiguities above (fixture scope, parser robustness, comparison key) were the only substantive
> ones and are resolved. No open-clarification placeholders remain in this section. The single
> Principle-V item (roadmap promotion / F-numbering) was ruled by the repo owner at ratification
> (stay unmapped -- recorded above). No grain/uniqueness, PII publish-safety,
> business-rollup/segment, or product-identity question applies (this is a test-only
> governance-core artifact over synthetic in-memory findings -- it touches no data grain, no
> published PII, no business segment, and no product identity).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The two output paths are proven to agree on findings content (Priority: P1)

A maintainer changes the rendering of one of the two `retail check` output paths -- the default
human-readable text path (`run()`, which iterates rules inline and prints one `_format(finding)`
line each) or the opt-in structured JSON path (`run_json()`, which routes through `_collect` and
emits a single JSON document). Today the only thing keeping these two SEPARATE code paths in
agreement is a docstring convention about rule purity. A property test now runs both paths over the
same synthetic fixtures and asserts that the multiset of findings reconstructed from the text
output equals the multiset of findings in the JSON output -- so a divergence between the two paths
is caught as a test failure rather than discovered in the field.

**Why this priority**: This is the core value -- it converts an untested docstring convention
("rule purity is what keeps the text and JSON outputs in agreement") into a tested invariant. The
two paths are genuinely separate code (the `run()` docstring explicitly says it "iterates inline
rather than reusing `_collect`"), so nothing structurally forces them to stay in sync; this test is
that structural force.

**Independent Test**: Construct a tuple of synthetic `RegisteredRule` stubs whose rules yield a
known set of findings (covering every severity, including a rule that yields several findings).
Run `run()` capturing stdout and run `run_json()` capturing stdout; reconstruct a `Counter` of
`(rule_id, severity, message, locator)` tuples from each; assert the two Counters are equal.
Delivers value as a standalone CI guard with no DB, network, or Power BI dependency.

**Acceptance Scenarios**:

1. **Given** a fixture rule set yielding findings across all three severities, **When** both
   `run()` and `run_json()` are invoked over it, **Then** the multiset of `(rule_id, severity,
   message, locator)` tuples reconstructed from the text output equals the multiset from the JSON
   `findings` array.
2. **Given** a single fixture rule yielding multiple findings, **When** both paths run, **Then**
   the parity holds regardless of within-rule or cross-rule ordering (the comparison is
   order-insensitive).
3. **Given** an empty fixture rule set (no findings), **When** both paths run, **Then** both
   produce an empty finding multiset and the parity holds trivially.

---

### User Story 2 - The two output paths are proven to agree on exit code (Priority: P1)

A maintainer relies on the process exit code as the governance contract (Principle I: the exit code
IS the gate). The default text path computes the exit code inline (sets `exit_code = 1` on any
`Severity.ERROR`); the JSON path computes it through `_exit_code(findings)`. These are two
implementations of the same rule. The property test asserts that, for the same fixtures, `run()`
and `run_json()` return the IDENTICAL exit code -- hardening (never weakening) the non-zero-exit
gate.

**Why this priority**: The exit code is the enforced contract; if the two paths could ever disagree
on it, a consumer choosing JSON output could see a different pass/fail verdict than a consumer using
the default text output. This is the second half of the equivalence property and is equally
load-bearing as the findings half.

**Independent Test**: For each fixture rule set (error-present, warning-only, info-only, empty),
assert `run(rules, ctx) == run_json(rules, ctx)` as integers, and assert the value matches the
expected gate semantics (1 iff any ERROR present, else 0). The existing `test_runner.py` already
proves single cases of this; this generalizes it into a property over shared fixtures.

**Acceptance Scenarios**:

1. **Given** a fixture set containing at least one ERROR finding, **When** both paths run, **Then**
   both return exit code 1.
2. **Given** a fixture set containing only WARNING and/or INFO findings, **When** both paths run,
   **Then** both return exit code 0.
3. **Given** an empty fixture set, **When** both paths run, **Then** both return exit code 0.

---

### User Story 3 - The test is C086-agnostic and changes no production output (Priority: P2)

A reviewer reading the new test confirms it uses only generic synthetic findings (no billing codes,
no insurance/PII columns, no pharmacy rule ids, no C086 locators), reads `run()`/`run_json()`
output without modifying it, and adds no new registered rule -- so the test exercises the governance
core without altering it or leaking a worked-example's specifics into a generic artifact.

**Why this priority**: It is the guardrail on the guardrail -- it ensures the parity test stays
within scope (test-only, generic-only, no executor, no gate enlargement) per Principles VII and
VIII and hard rules #7 and #9. Lower priority than the two property halves because it is a
constraint on HOW they are built, not a separate behavior.

**Independent Test**: Inspect the test file: it imports only stdlib + `retail.core` / `retail.runner`
(no `psycopg2`, no network, no `retail.rules`); its fixtures use placeholder ids/messages/locators
(e.g. `R1`, `R2`, generic strings); and `tests/unit/test_rules_wiring.py`'s `EXPECTED_RULE_IDS` set
is unchanged after this work.

**Acceptance Scenarios**:

1. **Given** the new test file, **When** its imports and fixtures are reviewed, **Then** it
   contains no C086/pharmacy-specific ids, billing codes, insurance columns, or PII locators.
2. **Given** the change set, **When** `EXPECTED_RULE_IDS` in `tests/unit/test_rules_wiring.py` is
   compared before and after, **Then** it is identical (no rule added or removed).
3. **Given** the change set, **When** `src/retail/runner.py` is diffed, **Then** `run()` and
   `run_json()` are unchanged (the test reads their output; it does not alter it -- B2 byte-for-byte
   text contract preserved).

### Edge Cases

- **Message or locator containing `") ("` or brackets**: a naive inverse-of-`_format` parser would
  be ambiguous. The test CONTROLS its synthetic fixtures so every finding renders to an
  unambiguously parseable text line (no embedded `") ("`, no unescaped brackets); the property
  proves the two paths agree on the SAME inputs, not that a general-purpose stdout parser is robust
  against adversarial free text (that robustness is out of scope; see Q2).
- **Empty finding set**: both paths produce an empty multiset and exit code 0; the parity holds
  trivially and the test asserts it explicitly (no silent skip).
- **Multiple findings from one rule / multiple rules**: the comparison is an order-insensitive
  multiset (`Counter`), so it holds regardless of inline vs. `_collect` iteration order. The
  fixtures MUST include a multi-finding rule so the multiset comparison is non-trivial.
- **Duplicate findings (same tuple emitted twice)**: a multiset (not a set) is required so a
  legitimately duplicated finding is not collapsed; the Counter preserves multiplicity.
- **Trailing newline / whitespace in text output**: the text reconstruction MUST split on line
  boundaries and ignore a trailing blank line so a final newline does not produce a spurious empty
  finding.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST add a property test at `tests/unit/test_runner_output_parity.py`
  (greenfield -- the file does not exist today) that, for shared synthetic fixtures, asserts the
  multiset of findings reconstructed from `run()`'s text stdout equals the multiset of findings in
  `run_json()`'s JSON `findings` array.
- **FR-002**: The comparison MUST be order-insensitive: it MUST use a multiset
  (`collections.Counter`) over the full four-field tuple `(rule_id, severity, message, locator)` --
  the same fields `Finding.to_dict()` / `FindingDict` pin -- never a sequence/list equality that
  depends on iteration order.
- **FR-003**: The test MUST separately assert that `run()` and `run_json()` return the IDENTICAL
  integer exit code for the same fixtures, and that the value matches the gate semantics (1 iff any
  `Severity.ERROR` is present, else 0).
- **FR-004**: The fixtures MUST be SYNTHETIC `RegisteredRule` stubs (the pattern
  `tests/unit/test_runner.py` already uses), NOT the real `all_rules()` registry and NOT a
  committed real-registry tmp-repo fixture. The property targets the `run()`/`run_json()` plumbing,
  not the live rule set (Q1).
- **FR-005**: The fixtures MUST cover every `Severity` (ERROR, WARNING, INFO) and MUST include at
  least one rule yielding multiple findings, so the multiset parity comparison is non-trivial.
- **FR-006**: The fixtures' synthetic findings MUST render to unambiguously parseable text lines:
  messages and locators MUST NOT contain the substring `") ("` or unescaped brackets that would
  make the inverse-of-`_format` reconstruction ambiguous (Q2). The test reconstructs structured
  tuples by parsing the stable `"[{sev}] {rule_id} {message} ({locator})"` shape under that
  constraint.
- **FR-007**: The test MUST treat `Finding` as immutable (it is a frozen dataclass): it MUST NOT
  mutate or re-sort findings in place; the order-insensitive comparison MUST be achieved by
  building a new `Counter`, not by re-ordering existing objects.
- **FR-008**: This work MUST NOT add a new `@register`-ed rule and MUST NOT add a new
  `EXPECTED_RULE_ID`. The parity test is a test-only assertion; it is NOT a registered governance
  rule and does not run inside `retail check`. The wiring-test invariant
  (`tests/unit/test_rules_wiring.py` `EXPECTED_RULE_IDS`) MUST be unchanged.
- **FR-009**: This work MUST NOT modify `src/retail/runner.py` (`run`, `run_json`, `_collect`,
  `_format`, `_exit_code`) or `src/retail/core.py`. It reads their behavior; it does not change it.
  The B2 byte-for-byte default text-output contract MUST be preserved.
- **FR-010**: The test MUST be stdlib-only with NO dependency on a database, the network, Power BI
  Desktop, or the Power BI execution adapter (F016). It MUST import only the standard library plus
  `retail.core` and `retail.runner`; it MUST NOT import `psycopg2` and MUST NOT import the
  `retail.rules` package (Principle VIII, static-first).
- **FR-011**: The test fixtures MUST be C086-agnostic: generic placeholder rule ids, messages, and
  locators only; NO billing codes, insurance/PII columns, pharmacy rule ids, or other
  worked-example specifics (Principle VII, hard rule #7).
- **FR-012**: The test MUST capture `run()` / `run_json()` stdout via the existing `capsys` pattern
  (the mechanism `tests/unit/test_runner.py` already uses), and MUST handle a trailing newline so a
  final blank line does not produce a spurious empty finding.

### Key Entities *(include if feature involves data)*

- **Synthetic finding**: a generic `Finding(rule_id, severity, message, locator)` used only in the
  test fixtures, with placeholder values (e.g. `R1`, generic message/locator strings) and no
  worked-example specifics.
- **Finding multiset**: a `collections.Counter` keyed on the four-field tuple `(rule_id, severity,
  message, locator)`, built independently from the text path and the JSON path; equivalence of the
  two Counters is the findings half of the property.
- **Parity property**: the conjunction of (a) finding-multiset equality and (b) exit-code equality
  between `run()` and `run_json()` over the same fixtures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any divergence introduced between the `run()` text path and the `run_json()` JSON path
  on either findings content or exit code is caught by a failing test 100% of the time (no silent
  divergence).
- **SC-002**: The test passes deterministically on a clean checkout with no DB, network, or Power BI
  dependency, and on repeated runs (no flakiness).
- **SC-003**: The feature adds zero new registered rules and zero new `EXPECTED_RULE_ID` entries
  (verified against `tests/unit/test_rules_wiring.py`), and `src/retail/runner.py` /
  `src/retail/core.py` are byte-for-byte unchanged, confirming it neither enlarges nor alters the
  gate.
- **SC-004**: The test file contains zero C086/pharmacy-specific identifiers, billing codes,
  insurance/PII columns, or worked-example locators (generic-only).
- **SC-005**: The multiset comparison correctly distinguishes order (passes regardless of ordering)
  from content (fails if any finding tuple differs), demonstrated by the fixtures including a
  multi-finding rule and at least one finding per severity.

## Assumptions

- The four load-bearing seams the idea names are CONFIRMED present in `src/retail/runner.py`:
  `run()` (lines 84-98, inline text path), `run_json()` (101-117, JSON path via `_collect`),
  `_collect()` (68-76), `_format()` (61-65), `_exit_code()` (79-81); and `Finding.to_dict()` /
  `FindingDict` / `Severity` in `src/retail/core.py`. The text render format
  `"[{sev}] {rule_id} {message} ({locator})"` is stable and is the shape the inverse parser reads.
- `tests/unit/test_runner_output_parity.py` does NOT exist yet; this spec creates it (greenfield,
  not a regression).
- A committed real-registry tmp-repo fixture (driving `all_rules()` through `run()`) is NOT
  confirmed to exist; the spec deliberately scopes the property to SYNTHETIC fixtures (Q1) so it
  does not depend on an unconfirmed artifact.
- An inverse-of-`_format` parser does not exist anywhere in `src/` or `tests/`; the test hand-writes
  a minimal one, made unambiguous by constraining the fixtures (Q2) rather than by handling
  adversarial free-text messages.
- This spec is the PLAN only. Implementation (writing the test) is downstream work, not performed by
  the spec author.
- No deferred capability is assumed to exist: the test requires no Power BI Execution Adapter (F016)
  and no spec-only runtime (F031-F033).
