# Feature Specification: Assumption Ledger Rule (AL1)

**Feature Branch**: `053-assumption-ledger-rule-al1`

**Created**: 2026-07-01

**Status**: Draft

**Input**: User description: "Assumption Ledger Rule (AL1)"

## Overview

A metric contract (`mappings/<table>/metrics/<Metric>.yaml`) is the committed,
reviewable DEFINITION of one metric -- its stable name, grain, plain-language
formula intent, named owner, and the `gold` column(s) it binds to (`binds_to`).
The contract also records an explicit readiness lifecycle (`readiness.status` in
`{not_started | blocked | warning | pass}` plus `blocking_reasons[]`). A metric
whose definition still rests on an UNRESOLVED human judgment call -- a business
rollup the analyst has not supplied, an unresolved grain question, a PII
publish-safety deferral -- is, by the contract's own authoring rules, supposed to
carry that open question explicitly and NOT be treated as a settled binding.

Today nothing structurally prevents a metric contract from carrying an unresolved
assumption WHILE ALSO presenting a settled measure binding (a filled `binds_to`
and/or a readiness status advanced past the draft default). A human reviewer is
expected to catch that a still-open assumption should block the binding, but that
discipline lives only in prose and human review, not in the static `retail check`
gate. A contract can be committed that quietly binds a measure on top of an
assumption no human has cleared, and no gate fails.

This feature adds ONE static rule -- the idea-bank labels it `AL1` -- that turns
that discipline into a structural check. The rule scans every committed
`mappings/<table>/metrics/*.yaml` metric contract, detects the
presence of an unresolved-assumption marker, and fails closed (ERROR) when that
marker coexists with a settled measure binding. The rule NEVER resolves the
assumption itself -- clearing an open assumption is a human judgment call
(Principle V); AL1 only SURFACES the coexistence so it is caught by the gate
rather than shipped as a silently-bound-on-an-open-question contract.

AL1 is the structural SIBLING of the existing publish/status/dependency
reconciler rules `PP1` (`src/retail/rules/publish_pack.py`), `SC1`
(`src/retail/rules/status_claims.py`), and `DF1`
(`src/retail/rules/parked_on.py`). Like those rules, AL1 fires the `@register`
decorator, adds exactly one new rule id (`AL1`) to the `EXPECTED_RULE_IDS`
drift-guard, scans per-table instances via `ctx.tracked_files` while EXCLUDING
the generic template, imports `yaml` LAZILY (preserving the stdlib-only invariant
of the `retail check` core chain), is categorical (present/absent -- no numeric
score, hard rule #9), reads only committed text, and returns Findings without
executing anything: it never evaluates DAX and never opens a database/network/Power
BI connection (Principle VIII; the B1/B3 invariant). It skips committed test
fixtures via the shared `is_test_path()` exemption.

### Define-then-check dependency (load-bearing)

Unlike PP1/SC1/DF1, AL1 has a DEFINE prerequisite the other siblings did not: the
"unresolved-assumption marker" AL1 keys on does NOT yet exist as a settled
convention on metric contracts. The generic template
(`templates/metric-contract.yaml`) has no explicit open-assumption token; its
current open-state mechanism is `readiness.status: blocked` with a non-empty
`blocking_reasons[]`. Whether AL1 keys on that EXISTING mechanism or on a NEW
literal token added to the GENERIC template is an unresolved human ruling (see
Clarifications). AL1 must first DEFINE the marker convention (in the generic
template) before it can CHECK it. If a new token is chosen, the convention is
added ONLY to `templates/metric-contract.yaml` -- never to a per-table (C086)
contract (Principle VII).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A still-open assumption blocks a bound metric (Priority: P1)

A governance reviewer runs the `retail check` gate over a committed metric
contract that carries an unresolved-assumption marker AND a settled measure
binding. AL1 emits an ERROR Finding naming the contract and the coexistence, so
the reviewer must either resolve the assumption (a human ruling) or withdraw the
binding before the contract can pass the gate.

**Why this priority**: This is the entire purpose of the rule -- catch a metric
that binds on top of an uncleared human judgment call. Without it the gate is
silent on exactly the failure mode the metric-contract authoring rules warn about.

**Independent Test**: Author a fixture metric contract with an open-assumption
marker and a filled binding; assert AL1 emits one ERROR Finding with the contract
path in its locator. Author a second fixture with the same open marker but NO
settled binding; assert AL1 emits NOTHING (an openly-blocked draft is legitimate).

**Acceptance Scenarios**:

1. **Given** a committed `mappings/<table>/metrics/<Metric>.yaml` carrying an
   unresolved-assumption marker AND a settled measure binding, **When** `retail
   check` runs, **Then** AL1 emits exactly one ERROR Finding whose locator is the
   contract path.
2. **Given** a committed contract carrying the open-assumption marker but with NO
   settled binding (a legitimately-open draft), **When** `retail check` runs,
   **Then** AL1 emits no Finding for that contract.
3. **Given** a committed contract with a settled binding and NO open-assumption
   marker (a normal, fully-resolved contract), **When** `retail check` runs,
   **Then** AL1 emits no Finding for that contract.

---

### User Story 2 - The rule is registered and drift-guarded (Priority: P1)

A maintainer adds AL1 to the rule family. The `@register` decorator wires it into
the gate, and the same change adds `AL1` to `EXPECTED_RULE_IDS` in
`tests/unit/test_rules_wiring.py`. The wiring test fails closed if the registered
set and the expected set drift apart.

**Why this priority**: The registration + drift-guard seam is a hard invariant of
this rule family (ADR 0007): a new `@register` rule that does not add its id to
`EXPECTED_RULE_IDS` in the same change breaks the wiring test. Without this the
rule is either unregistered (silent) or drifts the count.

**Independent Test**: Run the wiring test; assert the registered rule ids equal
`EXPECTED_RULE_IDS` and that the count moved from 33 to 34 with `AL1` the sole
addition.

**Acceptance Scenarios**:

1. **Given** the AL1 rule module is added, **When** the registry is enumerated,
   **Then** `AL1` appears exactly once in the registered rule ids.
2. **Given** `EXPECTED_RULE_IDS` includes `AL1`, **When** `test_rules_wiring.py`
   runs, **Then** the registered set equals the expected set (no missing, no
   unexpected) and `len(EXPECTED_RULE_IDS)` is 34.

---

### User Story 3 - The rule stays generic and static (Priority: P2)

AL1 scans only the GENERIC per-table metric-contract instances and excludes the
generic template. It reads committed text with the stdlib only and never executes
DAX, never opens a connection, and bakes in no C086/pharmacy specifics.

**Why this priority**: Generic-only (Principle VII), static-first (Principle
VIII), and stdlib-only-core are hard invariants of the `retail check` family. A
rule that hard-codes a dataset path, a C086 measure name, or that imports a DB
driver at module scope would violate the family's design and other gate rules
(B1/B3).

**Independent Test**: Confirm AL1 excludes `templates/metric-contract.yaml` from
its scan; confirm the module has no module-scope DB/network import (B1/B3 hold);
confirm no C086/pharmacy literal (dataset path, measure name, discount-status
ruling) appears in the rule or in any generic artifact it edits.

**Acceptance Scenarios**:

1. **Given** the generic template `templates/metric-contract.yaml` is a tracked
   file, **When** AL1 scans, **Then** the template is EXCLUDED (it is placeholders
   by design, exactly as PP1 excludes its generic template).
2. **Given** the AL1 module, **When** the B1/B3 import-boundary rules run, **Then**
   AL1 has no module-scope database/network import (the `yaml` import is lazy).

---

### Edge Cases

- **Malformed / unreadable contract**: A tracked-but-unparseable metric contract
  fails LOUD with an ERROR Finding (naming the file + parse error), never a
  vacuous green -- mirroring PP1's read-error handling.
- **Missing field**: A contract missing the field the marker keys on is treated
  per the marker ruling (see Clarifications), never assumed resolved.
- **No metric contracts on disk**: If no per-table metric contracts exist, AL1
  emits nothing (a genuine silent pass, mirroring the no-instances behavior of the
  sibling rules) -- NOT an error.
- **Zero-findings-on-main baseline**: If, at ship time, no committed contract
  carries the open-assumption marker coexisting with a binding, AL1 passes on
  main. Whether that pass is genuine or vacuous depends on the standalone-vs-gated
  decision (see Clarifications) and MUST be recorded as a genuine pass, not glossed.
- **Open marker on a legitimately-blocked draft**: A contract that carries the
  open marker AND is honestly `readiness.status: blocked` with NO settled binding
  must NOT trip AL1 -- blocking a draft on an open question is the correct
  behavior, not a defect. The coexistence CONDITION (see Clarifications) must be
  drawn so it fires only on binding-atop-open, never on honest-open-draft.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST add exactly one new static check rule, identified as
  `AL1`, registered via the existing `@register` decorator, in a new module
  `src/retail/rules/assumptions.py`.
- **FR-002**: The same change MUST add `AL1` to `EXPECTED_RULE_IDS` in
  `tests/unit/test_rules_wiring.py`, moving the count from 33 to 34, with `AL1`
  the sole addition; the wiring test MUST pass.
- **FR-003**: AL1 MUST scan committed per-table metric-contract instances located
  under `mappings/<table>/metrics/*.yaml`, discovered via `ctx.tracked_files`.
- **FR-004**: AL1 MUST EXCLUDE the generic template
  `templates/metric-contract.yaml` from its scan (it is placeholders by design),
  and MUST skip committed test fixtures via the shared `is_test_path()` exemption.
- **FR-005**: AL1 MUST import `yaml` LAZILY (inside the rule function, not at
  module scope), preserving the stdlib-only invariant of the `retail check` core
  chain and satisfying the B1/B3 import-boundary rules.
- **FR-006**: AL1 MUST be categorical -- it emits a Finding when the checked
  condition holds and nothing when it does not. It MUST NOT emit any numeric score,
  confidence, or threshold (hard rule #9).
- **FR-007**: AL1 MUST read only committed text and MUST NOT execute DAX, open a
  database/network/Power BI connection, or otherwise leave the static plane
  (Principle VIII).
- **FR-008**: AL1 MUST NEVER resolve, clear, populate, or auto-answer an
  unresolved assumption; it only SURFACES it. Clearing an assumption is a human
  judgment call the rule is structurally forbidden to make (Principle V), so AL1
  fails closed (ERROR) rather than self-resolving.
- **FR-009**: AL1 MUST emit an ERROR Finding, whose locator names the offending
  contract, when an unresolved-assumption marker coexists with a settled measure
  binding on the same contract.
- **FR-010**: A tracked-but-unreadable or unparseable metric contract MUST produce
  a loud ERROR Finding (file + reason), never a silent pass.
- **FR-011**: AL1 MUST bake in no C086/pharmacy specifics (dataset path, measure
  name, or discount-status ruling); it keys only on the generic contract SHAPE.
  C086 is CITED as a filled instance, never inlined (Principle VII).
- **FR-012**: AL1 MUST advance no readiness stage, grant no approval, and touch no
  F016 (Power BI Execution Adapter) or any deferred runtime; it is an idea-bank
  sequence rule with no roadmap F-number.
- **FR-013**: The marker convention AL1 keys on MUST be DEFINED before it is
  CHECKED. If the convention is a NEW literal token, it MUST be added to the
  GENERIC template `templates/metric-contract.yaml` ONLY -- never to a per-table
  contract. [Resolution of WHICH convention is a Clarification below.]
- **FR-014**: All authored artifacts MUST be ASCII + UTF-8 without BOM (use `--`
  and `->`, no non-ASCII glyphs; rule IX).

*Requirements deferred to Clarifications (Principle V -- human judgment calls the
agent MUST NOT self-answer):*

- **FR-015**: What EXACTLY counts as an "unresolved-assumption marker" on a metric
  contract: [NEEDS CLARIFICATION: (a) an EXISTING field state --
  `readiness.status: blocked` with a non-empty `blocking_reasons[]` -- or (b) a NEW
  literal token added to the generic `templates/metric-contract.yaml`. These are
  materially different specs; the whole check hinges on this and it is a human
  ruling, not an agent default.]
- **FR-016**: What EXACTLY counts as a coexisting "settled measure binding" that,
  together with the marker, triggers the ERROR: [NEEDS CLARIFICATION: e.g. a filled
  `binds_to.gold_table` + non-empty `binds_to.columns`, and/or a
  `readiness.status` advanced past the `not_started` default. The coexistence
  condition must be drawn so AL1 fires on binding-atop-open but NEVER on an honest
  blocked draft -- a Principle-V judgment call, not an agent default.]
- **FR-017**: Whether AL1 ships standalone against the template-defined marker, or
  is gated on its unshipped DEFINE half (backlog item T1.2, "Per-Contract
  Ambiguity Decision Ledger"): [NEEDS CLARIFICATION: if standalone with no marked
  contracts on main, confirm the zero-findings-on-main baseline is a genuine pass,
  not a vacuous one; if gated, AL1 waits for T1.2's define half to ship first.]

### Key Entities *(include if feature involves data)*

- **Metric contract**: the committed `mappings/<table>/metrics/<Metric>.yaml`
  DEFINITION of one metric. Relevant fields for AL1: the marker field (per FR-015),
  the `binds_to` block (`gold_table`, `columns`), and `readiness` (`status`,
  `blocking_reasons[]`). AL1 reads these; it never writes them.
- **Generic metric-contract template**: `templates/metric-contract.yaml` -- the
  copy-me placeholder template. EXCLUDED from AL1's scan; the sole place a new
  marker-convention token (if chosen) is added.
- **AL1 rule (`src/retail/rules/assumptions.py`)**: the new `@register` L2 check.
  Reads contracts, emits categorical ERROR Findings, executes nothing.
- **Rule-id drift guard (`EXPECTED_RULE_IDS`)**: the frozenset in
  `tests/unit/test_rules_wiring.py` that must include `AL1` (33 -> 34).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running the `retail check` gate over a contract that carries the
  open-assumption marker coexisting with a settled binding produces exactly one
  AL1 ERROR Finding naming that contract; a fully-resolved contract and an
  honestly-open (unbound) draft each produce zero AL1 Findings.
- **SC-002**: The rule-wiring test passes with `AL1` present exactly once and the
  registered rule-id count equal to `EXPECTED_RULE_IDS` at 34 ids.
- **SC-003**: The generic template `templates/metric-contract.yaml` is never
  flagged by AL1 (it is excluded), and no committed test fixture is flagged
  (via `is_test_path()`).
- **SC-004**: The existing import-boundary checks (B1/B3) pass with the new module
  present -- AL1 introduces no module-scope database/network import.
- **SC-005**: On the ship branch, `retail check` on `main`'s tracked contracts
  yields zero AL1 Findings, and that zero is recorded as a genuine (not vacuous)
  pass per the FR-017 resolution.
- **SC-006**: No C086/pharmacy literal appears in the AL1 module or in any generic
  artifact it edits.

## Assumptions

- AL1 belongs to the idea-bank execution sequence (siblings A1/B1/PP1/SC1/DF1),
  which carries NO roadmap F-number and advances NO readiness stage. `f_number`
  stays `none`; `roadmap_stage` is `unmapped`. (The idea's original "V7 / F7" tag
  is a mislabel: roadmap F7 is the already-shipped "KPI Decision-Question Index".)
- AL1 ships as the next on-disk spec in that sequence (feature 053), a small
  single-family PR adding one rule, with zero AL1 findings on `main` at ship time.
- The structural template is PP1/SC1/DF1: a `@register` retail check rule scanning
  per-table instances via `ctx.tracked_files`, excluding the generic template,
  reading only committed text, importing `yaml` lazily, categorical (no score),
  returning Findings without executing.
- The core read-only helpers `RuleContext.tracked_files`, `repo_root`, and
  `is_test_path()` exist and are reused as-is; `@register` and the
  `EXPECTED_RULE_IDS` drift guard exist and are reused as-is.
- Starting rule-id count is 33 (verified against the in-tree `EXPECTED_RULE_IDS`
  frozenset); AL1 makes 34. (Panel prose citing 33/34/38 refers to different
  count bases; the authoritative number is the in-tree frozenset.)
- AL1 does NOT hang off `src/retail/semantic.py` (L3): L3 has zero `@register` and
  adds no rule id (ADR 0007). AL1 is an L2 `@register` rule; the first step (add an
  `EXPECTED_RULE_ID` + wiring test) is authoritative for placement.
- No DEFERRED capability is assumed to exist (F016 Power BI Execution Adapter;
  F031-F033 spec-only runtimes). AL1 is docs/static-check only; it ships no executor.

## Dependencies

- **Existing seams (reused read-only)**: `@register` + `EXPECTED_RULE_IDS`
  (registration + drift guard); PP1/SC1/DF1 (structural template);
  `RuleContext.tracked_files` / `repo_root` / `is_test_path()`;
  `mappings/<table>/metrics/*.yaml` + `templates/metric-contract.yaml`
  (contracts + their generic template);
  `src/retail/metric_drift.py` `load_definition()` (lazy-yaml contract loader,
  reusable).
- **DEFINE prerequisite**: the unresolved-assumption marker convention does not
  exist on metric contracts today; it must be defined (in the generic template)
  before AL1 can check it (see FR-013, FR-015).
- **Open dependency question**: gating on the unshipped T1.2 define-half
  (see FR-017).

## Clarifications

The following are Principle-V human judgment calls and/or the highest-impact
ambiguities. Items carved out under Principle V are recorded here for a human
ruling and MUST NOT be self-answered by the agent.

### Principle-V carve-outs (recorded for human ruling)

- **What counts as the "unresolved-assumption marker"** (FR-015): (a) an existing
  `readiness.status: blocked` + non-empty `blocking_reasons[]`, or (b) a NEW
  literal token added to the generic template. This convention does not exist yet
  and defines the entire check.
- **What coexisting "settled measure binding" triggers the ERROR** (FR-016): a
  filled `binds_to` and/or a `readiness.status` past `not_started`. The condition
  must fail closed on binding-atop-open but never on an honest blocked draft.
- **Standalone vs gated on T1.2** (FR-017): does AL1 ship against the
  template-defined marker now, or wait for its unshipped define-half? If standalone
  with no marked contracts, confirm the zero-findings-on-main baseline is genuine.

<!-- Clarify session entries are appended below by /speckit-clarify. -->
