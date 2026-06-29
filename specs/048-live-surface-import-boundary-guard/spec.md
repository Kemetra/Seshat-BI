# Feature Specification: Live-Surface Import Boundary Guard (B3)

**Feature Branch**: `048-live-surface-import-boundary-guard`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "Live-Surface Import Boundary Guard (B3)"

## Overview

The live-validator surface -- the modules that talk to a real database only
through the `QueryRunner` Protocol (`validate.py`, `value_proxy.py`,
`semantic.py`, `dax_gen.py`) -- carries a deliberate, load-bearing discipline:
none of them imports a connection-capable driver (psycopg2, requests, a raw
socket, ...) at module scope. Every such import is done LAZILY, inside the CLI
handler that actually connects, so merely importing one of these modules opens
nothing. This keeps the static core's driver-free import path intact even though
these modules ARE the live surface (constitution Principle VIII).

Today that discipline is enforced only by PROSE: each of the four modules states
it in a docstring and an inline `# lazy` comment. There is no structural check
that fails closed if a future edit moves one of those imports to module scope.
A developer could regress the invariant and the gate would stay green.

This feature adds ONE static rule that turns the prose into a structural error.
It is the static import-boundary SIBLING of the existing `B1` never-execute
guard and of the shipped runtime conformance test in
`specs/044-live-surface-protocol/`:

- `B1` (`src/retail/rules/never_execute.py`) already forbids module-scope
  connection-capable imports in the STATIC-CORE modules
  (`cli`, `runner`, `core`, `registry`, and everything under `rules/`).
- `044` asserts at RUNTIME that the live surface talks only through the Protocol
  (a fake `QueryRunner` exercises it while opening nothing).
- THIS rule (the idea-bank labels it "B3") extends the SAME static AST check to
  the LIVE-SURFACE modules -- a non-overlapping module set B1 deliberately does
  not govern.

The rule reuses B1's existing `module_scope_violations` AST helper and its
forbidden-root set UNCHANGED (constitution Principle II "Depend, Never Fork").
The policy difference is purely WHICH files are scanned, not which imports are
forbidden. Like B1, the rule parses source text with stdlib `ast` and NEVER
imports or executes the target modules -- the guard is itself part of the
stdlib-only, CI-able static core.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A regressed live-surface import fails the gate (Priority: P1)

A maintainer edits a live-surface module and (by mistake or convenience) adds a
module-scope `import psycopg2` (or any connection-capable import) instead of
keeping it lazy inside the handler. When the static checker runs, the new rule
flags that module so the regression is caught in CI rather than discovered when
`import retail.validate` unexpectedly pulls a live driver.

**Why this priority**: This is the entire value of the feature -- converting a
prose invariant into an enforced one. Without it, nothing here delivers value.

**Independent Test**: Feed the rule a synthetic source string for a live-surface
module path that contains a module-scope forbidden import; assert exactly one
Finding is produced with the rule's id and the offending module's locator. Feed
it the same import placed lazily inside a function body; assert no Finding.

**Acceptance Scenarios**:

1. **Given** a live-surface module with a module-scope `import psycopg2`,
   **When** the static checker runs, **Then** the rule emits a Finding naming
   that module and the offending import, and the gate's exit reflects the rule's
   ratified severity.
2. **Given** a live-surface module that imports `psycopg2` lazily inside a
   function (the approved pattern), **When** the static checker runs, **Then**
   the rule emits NO Finding for that module.
3. **Given** a live-surface module whose only connection-capable import sits in
   an `if TYPE_CHECKING:` block, **When** the static checker runs, **Then** the
   rule emits NO Finding (type-only imports never run at runtime; same exemption
   B1 already applies).

### User Story 2 - The new rule is genuinely wired, not just listed (Priority: P1)

A reviewer needs confidence that adding the rule actually closed the gap rather
than merely registering an id. The rule appears in the live registry, in the
regenerated `docs/rules/rules-manifest.json`, and in the wiring test's expected
id set -- AND the wiring test exercises the rule so it cannot silently no-op.

**Why this priority**: The repo's memory records a prior "wiring latent gap"
where a registered rule was listed but never actually validated to fire. This
story exists to prevent repeating that gap. A registered-but-inert rule delivers
zero protection.

**Independent Test**: Run the rule-registry snapshot test and the wiring test;
assert the new id is present in both the live registry and the regenerated
manifest, AND that a test directly invokes the rule against a known-bad fixture
and observes a Finding (the rule fires, not merely registers).

**Acceptance Scenarios**:

1. **Given** the rule is registered, **When** the rule-registry snapshot test
   runs, **Then** the live registry id set equals the expected id set and the
   regenerated manifest contains the new id.
2. **Given** a synthetic known-bad live-surface source, **When** the rule is
   invoked directly in a test, **Then** it returns a non-empty Finding set
   (proving the rule fires, not just that its id is listed).

### User Story 3 - The live-surface set is an explicit, closed, schema-agnostic set (Priority: P2)

An auditor confirms the rule scans a defined, ratified set of module paths and a
generic forbidden-root list -- with no reference to any specific business
domain, table, column, or KPI. The set lives in one named place so its scope is
neither silently under- nor over-broad.

**Why this priority**: Correct scope is what makes the rule trustworthy, but the
P1 stories already deliver the protective value; this story hardens it.

**Independent Test**: Inspect the rule's module set definition; assert it is an
explicit named collection of repo-relative module paths and that neither the set
nor any rule fixture names a domain-specific table, column, or KPI.

**Acceptance Scenarios**:

1. **Given** the rule's live-surface module set, **When** it is inspected,
   **Then** it is a single explicitly-defined collection of repo-relative module
   paths, disjoint from B1's static-core governed set.
2. **Given** the rule and all its test fixtures, **When** they are reviewed,
   **Then** they reference only generic module paths and library names, never a
   domain-specific schema artifact.

### Edge Cases

- A live-surface module that does not parse (syntax error): the rule MUST fail
  loud as a Finding rather than crash the gate or pass vacuously (mirrors B1's
  SyntaxError-to-Finding behavior).
- A connection-capable import inside a module-level `try/except ImportError`
  optional-dependency guard at module scope: this still executes on import, so
  it MUST be flagged (consistent with `module_scope_violations`, which visits
  module-level `try`/`if` bodies).
- A live-surface module is renamed or a new live-surface module is added: the
  rule's scope is only as correct as its explicit set; an unlisted live-surface
  module is silently unscoped. (Closed-set membership is a ratify decision --
  see Clarifications.)
- `urllib.parse` (pure stdlib string work used for DSN escaping) MUST NOT be
  flagged; only connection-capable roots/dotted modules are forbidden (the same
  discrimination B1 already encodes).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single registered static rule that scans
  a defined set of live-surface module paths for module-scope imports of
  connection-capable libraries and emits a Finding for each violation.
- **FR-002**: The rule MUST reuse the existing `module_scope_violations` AST
  helper and the existing forbidden-root / forbidden-dotted sets from the
  never-execute module UNCHANGED; it MUST NOT fork a parallel parser or a
  parallel forbidden-library list.
- **FR-003**: The rule MUST parse source text only (stdlib AST) and MUST NEVER
  import or execute any scanned module -- the guard is part of the stdlib-only,
  network-free, CI-able static core.
- **FR-004**: The rule MUST treat lazy (in-function / in-class) imports and
  `if TYPE_CHECKING:` imports as compliant (no Finding), matching the existing
  helper's semantics.
- **FR-005**: The rule MUST flag a module-scope forbidden import even when it
  sits inside a module-level `try`/`except`/`if` block, because such imports
  execute on import.
- **FR-006**: When a scanned module fails to parse, the rule MUST emit a Finding
  (fail loud) rather than crash the gate or silently pass.
- **FR-007**: The live-surface module set MUST be defined explicitly in one named
  place, MUST be disjoint from B1's static-core governed set, and MUST be
  expressed as generic repo-relative module paths with no domain-specific schema
  reference.
- **FR-008**: Adding the rule MUST update the wiring test's expected rule-id set
  AND regenerate `docs/rules/rules-manifest.json` in the same change, so the
  rule-registry snapshot stays consistent. The change MUST NOT hard-code any
  numeric baseline rule count (the snapshot keys off the length of the expected
  id set, not a literal number).
- **FR-009**: The wiring/validation coverage MUST exercise the rule firing
  against a known-bad fixture, not merely assert that its id is registered
  (close the prior wiring-latent-gap).
- **FR-010**: Each Finding MUST be a new immutable value object identifying the
  rule id, the severity, the offending module path (locator), and the offending
  import name; the rule MUST NOT mutate shared state.
- **FR-011**: The rule's emitted severity MUST be a single ratified posture
  applied uniformly (see Clarifications -- severity posture is a governance
  decision recorded for human ratification, not chosen here).

### Key Entities *(include if feature involves data)*

- **Live-surface module set**: the explicit, closed collection of repo-relative
  module paths the rule scans. Candidate membership named by the idea source:
  `validate.py`, `value_proxy.py`, `semantic.py`, `dax_gen.py`. Final membership
  is a ratify decision (see Clarifications).
- **Forbidden import roots / dotted modules**: the existing connection-capable
  library set reused from the never-execute module (e.g. psycopg2, requests,
  socket; `urllib.request`/`urllib.error` but NOT `urllib.parse`). Reused
  unchanged -- not redefined here.
- **Rule registration record**: the rule's registry id + title, mirrored into
  the wiring test's expected id set and the generated rules manifest.
- **Finding**: an immutable result object (rule id, severity, message, locator)
  emitted per violation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A module-scope connection-capable import introduced into any module
  in the live-surface set causes the static checker to report at least one
  Finding for that module (the regression is caught).
- **SC-002**: The same import expressed lazily (in-function) or under
  `if TYPE_CHECKING:` produces zero Findings (no false positives on the approved
  pattern).
- **SC-003**: The live registry id set, the regenerated manifest, and the wiring
  test's expected id set agree exactly after the rule is added (the snapshot test
  passes), with no hard-coded numeric baseline.
- **SC-004**: At least one test invokes the rule directly and observes it fire on
  a known-bad fixture (the rule is exercised, not merely listed).
- **SC-005**: The rule, its module set, and every fixture contain no
  domain-specific schema artifact (no specific table, column, or KPI names).
- **SC-006**: Running the static checker with the rule added introduces no new
  third-party dependency and performs no network or database access.

## Clarifications

The following are governance / scope decisions deliberately NOT decided in this
spec. Items marked **[HUMAN RATIFY]** are reserved for a named human (constitution
Principle V -- the agent does not self-grant these). Stage clarify records a
recommended answer for the advisor-decidable ones and leaves the human-reserved
ones open.

- **Severity posture**: Should the rule emit ERROR or WARNING? The idea source's
  first-step suggests ERROR (a module-scope driver import in a live surface is a
  proven invariant breach, like B1). Principle VIII's default posture is WARN for
  static "suspect pattern" rules and ERROR for "proven defect" live checks. This
  is a governance posture call. See Session 2026-06-30.
- **[HUMAN RATIFY] Live-surface set membership**: Is the closed set exactly
  `{validate, value_proxy, semantic, dax_gen}`, or should other modules with a
  lazy-driver pattern (e.g. `metric_drift.py`) or future live surfaces be
  included? Under- or over-broad scope changes what the rule protects; the closed
  set must be ratified by a human.
- **[HUMAN RATIFY] Registered rule id**: "B3" is the idea-bank label, not
  necessarily the registry id. The actual B-family id must be chosen so it does
  not collide with or mislead about existing ids; this naming is reserved for
  human ratification.
- **[HUMAN RATIFY] Readiness stage**: Neither this rule nor B1 occupies a roadmap
  F-row. Does this advance a readiness stage, or is it a hardening rule that
  advances none (like the post-integration stabilization items)? A human assigns
  the stage or accepts "advances no stage."

### Session 2026-06-30

(Populated by `/speckit-clarify`.)

## Assumptions

- The four candidate live-surface modules already exist and already keep their
  driver imports lazy today; this feature does not change their behavior, only
  adds a guard that fails closed if a future edit regresses them.
- The existing `module_scope_violations` helper and forbidden-root sets are the
  correct, complete definition of "connection-capable module-scope import"; this
  feature reuses them rather than re-deriving the policy.
- The rule-registry snapshot test and wiring test are the authoritative
  consistency gate for adding a rule; satisfying them (id set + regenerated
  manifest + a firing test) is sufficient to consider the rule wired.
- No deferred capability is assumed: this is a pure static-text rule and does not
  depend on any Power BI execution adapter, live database, or spec-only runtime.
- The rule is generic governance infrastructure; it carries no business-domain
  schema knowledge (constitution Principle VII).
