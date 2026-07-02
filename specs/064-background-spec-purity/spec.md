# Feature Specification: Background-Spec Forbidden-Dynamic-Content Assertion Rule

**Feature Branch**: `064-background-spec-purity`

**Created**: 2026-07-02

**Status**: Ratified (Ahmed Shaaban, 2026-07-02)

> Ratified under the recorded ADOPT-batch autonomous authority dated 2026-07-02
> (owner directive: build+ratify+merge the entire ADOPT bucket; the advisor
> exercises the delegated per-spec ratify authority). A recorded per-spec override
> within that batch, not a standing waiver. The one Principle-V convention item is
> resolved conservatively in Clarifications: filled background specs are discovered
> by the frozen generic suffix `*.background.yaml` (analogue of DL1's `.theme.json`),
> exempting templates/ and test fixtures; the rule is inert-and-green on today's
> empty corpus and activates when a filled spec is committed. A8 is DL1's surface-2
> sibling: a static YAML CHECK (lazy `import yaml` inside the check to keep the
> retail-check core stdlib-only per B1/B3), categorical true==false contract, no
> score. analyze: clean (0/0); plan-review: PASS-WITH-NOTES.

**Input**: User description: "A8. background-spec forbidden_dynamic_content Assertion Rule"

## Overview

A Power BI page background is "surface 2" of the four design surfaces. Its only
job is STATIC STRUCTURE -- layout containers, safe zones, grid, chrome. It is
never data: a KPI value, a dynamic title, a measure result, a data label, a
refresh stamp, a filter/slicer state, or a screenshot of a live visual must
never be baked into the static background image. Live Power BI visuals sit
editable ABOVE the background; baking a number into the image creates a value
that never refreshes -- the exact failure mode this surface exists to prevent.

The blank template `templates/background-spec.yaml` already commits this
contract as a declared, machine-shaped block: `forbidden_dynamic_content` is a
set of boolean keys documented "Every check below MUST be false to pass. A true
entry is a defect," and `qa_checklist` is a set of items documented "Each MUST
be true to pass; a false entry is a blocking reason or a recorded warning +
reason." A human fills a copy of that template per page.

Today, once a page's background spec is filled, nothing checks that the declared
contract actually holds. A filled spec that sets a `forbidden_dynamic_content`
key to `true` -- or leaves a `qa_checklist` item `false` with no recorded reason
-- silently claims a compliant background while declaring a defect. This feature
turns that declared boolean contract into a static, CI-enforced governance rule:
a new registered rule that discovers committed filled background specs, asserts
the declared boolean contract (forbidden keys false; qa items true-or-reason),
and fails the contract check (non-zero exit) when a filled spec declares a
defect. The rule asserts the spec's OWN declared booleans; it never inspects an
image binary, never renders, never guesses free-text meaning.

This rule is the surface-2 sibling of the shipped surface-3 theme-JSON purity
rule (DL1, spec 060). It reuses the same static-governance seams and differs
only in reading YAML (via a lazy in-function import to keep the check core
stdlib-only) and asserting a DECLARED boolean contract rather than key-name
tokens.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A filled background spec that declares a defect fails the contract check (Priority: P1)

A contributor fills a page's background spec from the template and, by mistake or
because the background actually bakes in dynamic content, sets a
`forbidden_dynamic_content` key to `true` (for example `contains_kpi_value:
true`). When the contract check runs (locally or in CI), the check reports an
ERROR that names the offending file and the exact key, and the check exits
non-zero so the change cannot pass silently.

**Why this priority**: This is the whole point of the feature -- catching a
background that declares baked-in dynamic content. Without it, the feature
delivers nothing. It is a viable MVP on its own: a single ERROR finding on a
defect-declaring filled spec is the complete value.

**Independent Test**: Point the rule at a fixture background spec whose
`forbidden_dynamic_content` block sets one key to `true`; confirm it emits
exactly one ERROR finding for that key, carrying the file path and a location
pointer, and that the contract check exits non-zero.

**Acceptance Scenarios**:

1. **Given** a committed filled background spec whose `forbidden_dynamic_content`
   block sets a key to `true`, **When** the contract check runs, **Then** it
   emits an ERROR finding that identifies the file and the location of the true
   forbidden key, and the overall check exits non-zero.
2. **Given** a filled background spec whose `forbidden_dynamic_content` block sets
   two distinct keys to `true`, **When** the contract check runs, **Then** two
   separate ERROR findings are emitted (one per true key), so no violation is
   masked by another.
3. **Given** a filled background spec whose `qa_checklist` records an item as
   `false` with no accompanying reason, **When** the contract check runs, **Then**
   it emits a finding for that item, while an item recorded `false` WITH a reason
   is accepted (matching the template's "blocking reason or recorded warning +
   reason" wording).

### User Story 2 - A clean, compliant filled background spec passes (Priority: P1)

A contributor fills a background spec correctly: every `forbidden_dynamic_content`
key is `false` and every `qa_checklist` item is `true` (or `false` with a
recorded reason). When the contract check runs, the rule produces no findings for
that file, so legitimate background-design work is never blocked.

**Why this priority**: A rule that flags a compliant filled spec is worse than no
rule -- it trains contributors to ignore it. The compliant-pass boundary is as
essential as the defect catch; the two together define the rule's correctness
boundary.

**Independent Test**: Point the rule at a fixture filled spec whose forbidden
keys are all `false` and whose qa items are all `true`; confirm the rule emits
zero findings.

**Acceptance Scenarios**:

1. **Given** a filled background spec whose `forbidden_dynamic_content` keys are
   all `false` and whose `qa_checklist` items are all `true`, **When** the
   contract check runs, **Then** the rule emits zero findings for that file.
2. **Given** a filled background spec whose `qa_checklist` records an item `false`
   WITH a recorded reason, **When** the contract check runs, **Then** the rule
   emits zero findings for that item (a reasoned warning is accepted).
3. **Given** the repository's committed corpus in its current state (no filled
   background spec exists yet), **When** the contract check runs, **Then** the
   rule emits zero findings (the rule does not break the existing green build and
   is inert on an empty corpus).

### User Story 3 - The rule is generic, inert-until-filled, and self-registering (Priority: P2)

A maintainer fills a background spec for any page or subject area. The rule scans
it automatically because it discovers filled background specs by a generic file
pattern, not by an enumerated list, and it applies the same generic boolean
vocabulary derived from the shared template contract -- never a tenant-specific
or example-specific path or key. The rule also exempts the blank template itself
(its values are `<true|false>` placeholders, not real booleans) and appears in
the project's governance records (the rule registry and its golden records) so
its presence is verifiable.

**Why this priority**: Generality, inert-until-filled behavior, and
self-registration are what make the rule durable and trustworthy, but the rule
delivers its core value (US1 + US2) as soon as one filled spec exists. This story
protects against the rule silently missing new filled specs, flagging the blank
template, or hardcoding one tenant's path.

**Independent Test**: Add a second fixture filled spec (outside the
test-exemption path) and confirm the rule scans it without any code change;
confirm the blank template is not flagged; confirm the rule's identifier appears
in the registry and the governance golden records; confirm no
tenant/example-specific path or key appears anywhere in the rule's vocabulary.

**Acceptance Scenarios**:

1. **Given** more than one committed filled background spec, **When** the contract
   check runs, **Then** the rule scans every committed filled spec discovered by
   the generic pattern, not a hardcoded list.
2. **Given** the blank template `templates/background-spec.yaml` (whose values are
   `<true|false>` placeholders), **When** the contract check runs, **Then** the
   template is not treated as a filled spec and produces no findings.
3. **Given** the rule is registered, **When** the governance records are generated
   and the wiring test runs, **Then** the rule's identifier is present in the
   registry, the rule manifest, and the severity-posture record, and the wiring
   test passes.
4. **Given** a filled spec that lives under the test-fixture exemption path,
   **When** the contract check runs against the live corpus, **Then** the fixture
   is not treated as a live filled spec (fixtures may deliberately declare defects
   to exercise the rule).

### Edge Cases

- **No filled background spec exists**: The rule emits no findings and does not
  error -- it is deliberately inert until a page spec is filled. (See FR-011.)
- **Malformed YAML**: A committed filled spec that is not valid YAML cannot be
  scanned. The rule must not crash the whole contract check on a parse failure; it
  surfaces a finding that the file could not be parsed rather than silently
  passing it. (See FR-009.)
- **Placeholder still present**: A file discovered as a filled spec that still
  carries the `<true|false>` placeholder in a `forbidden_dynamic_content` or
  `qa_checklist` value has been mistaken for filled or was left half-filled. This
  is neither a real `true` nor a real `false`; a discovered filled spec that still
  carries the `<true|false>` placeholder in a contract value is treated as a
  half-filled defect and surfaced as a finding (resolved in Clarifications, Q1).
- **A forbidden key or qa item is missing entirely**: A filled spec that omits a
  key the contract declares cannot have its boolean asserted; whether a missing
  contract key is a finding or ignored is a parse-contract detail resolved in
  Clarifications.
- **Non-boolean value where a boolean is expected**: A `forbidden_dynamic_content`
  key set to a string or number (not `true`/`false`) is malformed against the
  declared boolean contract and is surfaced as a finding, never silently passed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a governance rule that scans committed
  filled background specs and asserts the declared boolean contract of the
  `forbidden_dynamic_content` block (every key MUST be `false`) and the
  `qa_checklist` block (every item MUST be `true`, or `false` with a recorded
  reason), per the contract declared in `templates/background-spec.yaml`.
- **FR-002**: The system MUST discover the filled background specs it scans by a
  generic file pattern, never by an enumerated or tenant-specific list, and MUST
  exempt the blank template `templates/background-spec.yaml` itself (whose values
  are `<true|false>` placeholders, not real booleans).
- **FR-003**: When a `forbidden_dynamic_content` key is declared `true` in a
  filled spec, the system MUST emit an ERROR finding that identifies the file and
  the location of the offending key within that file, using the existing
  file-plus-pointer locator convention already used by the project's
  structure-scanning rules.
- **FR-004**: The system MUST emit one distinct finding per contract violation
  (per true forbidden key, and per un-reasoned false qa item) so that no violation
  is masked by another.
- **FR-005**: The rule MUST decide violations by a categorical check on the
  declared boolean values and the presence/absence of a recorded reason. It MUST
  NOT inspect an image binary, MUST NOT render, MUST NOT interpret free-text
  meaning beyond detecting whether a reason string is present, and MUST NOT
  adjudicate a borderline design question -- any genuinely ambiguous case is
  surfaced for a human, never auto-resolved (Principle V).
- **FR-006**: A filled background spec whose `forbidden_dynamic_content` keys are
  all `false` and whose `qa_checklist` items are all `true` (or `false` with a
  recorded reason) MUST produce zero findings.
- **FR-007**: The asserted boolean vocabulary -- the set of
  `forbidden_dynamic_content` keys and `qa_checklist` items -- MUST be derived
  verbatim from the generic template contract in `templates/background-spec.yaml`,
  and MUST NOT contain any tenant-specific, example-specific, or brand-specific
  path or key (Principle VII).
- **FR-008**: A contract violation (a true forbidden key, or an un-reasoned false
  qa item) MUST cause the contract check to fail closed per the severity resolved
  in Clarifications, not be dropped silently.
- **FR-009**: The rule MUST handle a committed filled spec that cannot be parsed
  as YAML by surfacing a finding rather than crashing the whole contract check or
  silently passing the file.
- **FR-010**: The rule MUST exempt committed test fixtures from the live scan, so
  fixtures that deliberately declare defects (used to exercise the rule) do not
  fail the live contract check, following the existing file-scanning-rule
  exemption pattern.
- **FR-011**: The rule MUST be inert on an empty corpus: when no filled background
  spec exists (only the blank template), the rule MUST emit zero findings and MUST
  NOT flag the absence of a filled spec. Latent value until content lands is
  intended.
- **FR-012**: The rule MUST NOT execute the model, render an image, open an image
  binary, or perform any network/database access. Any YAML parsing dependency MUST
  be a lazy, in-function import so the never-execute static check core stays
  free of module-scope non-stdlib imports (consistent with existing YAML-reading
  rules).
- **FR-013**: The rule MUST declare a single freshly-allocated rule identifier
  that does not collide with any already-registered rule identifier. The exact
  literal id is finalized against the TRUE live registry at wiring time
  (reconcile against the real registered set, not a count claim). A
  design-lint-namespaced identifier is preferred so the design-lint family (DL1
  theme purity and this surface-2 rule) shares a legible namespace. Its severity
  is OBSERVED per branch from its emitted findings, not declared as a governed
  per-rule severity table (ratified 044).
- **FR-014**: The rule MUST be wired into the five governance records so its
  presence is verifiable and drift fails closed: the rule module, the
  side-effecting import registration and public export list, the expected-rule-id
  set the wiring test asserts, the generated rule manifest, and the generated
  severity-posture record.
- **FR-015**: The rule MUST NOT compute a numeric confidence or readiness score,
  MUST NOT self-grant a readiness or dashboard-ready pass, and MUST NOT advance
  any readiness stage. It packages and flags a declared-contract violation; it
  never approves (Principle V). Any readiness verdict remains the design-review
  verb owner's recorded human review.
- **FR-016**: The exact contract vocabulary (the frozen set of
  `forbidden_dynamic_content` keys asserted false and `qa_checklist` items
  asserted true-or-reason), the parse contract for distinguishing a real boolean
  from the `<true|false>` placeholder and from a recorded reason, the
  file-discovery convention that marks a committed filled spec, and the severity
  of a violation, are SETTLED in the Clarifications block. The golden records
  freeze exactly that resolved vocabulary and convention.

### Key Entities *(include if feature involves data)*

- **Filled background spec**: A committed copy of the template, filled per page
  (surface 2). The unit the rule scans. Attributes relevant here: its file
  location, and the real boolean values under `forbidden_dynamic_content` and
  `qa_checklist`.
- **Background-spec template**: The generic blank contract
  (`templates/background-spec.yaml`) whose `forbidden_dynamic_content` and
  `qa_checklist` blocks declare the boolean vocabulary. Its values are
  `<true|false>` placeholders, so it is EXEMPT from the scan. The source of the
  rule's asserted vocabulary.
- **Forbidden-dynamic-content contract**: The declared boolean block
  ("every check MUST be false; a true entry is a defect"). The core of what the
  rule asserts.
- **QA checklist contract**: The declared items block ("each MUST be true; a
  false entry is a blocking reason or a recorded warning + reason"). The
  true-or-reason concern the rule asserts.
- **Finding**: A single reported violation, carrying the rule identifier, a
  severity, a human-readable message, and a location that names the file and the
  position of the offending key/item within it.
- **Governance records**: The registry plus the golden records (import
  registration and export list, the expected-rule-id set, the rule manifest, the
  severity-posture record) that make the rule's presence verifiable and fail
  closed on drift.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of committed filled background specs that declare a
  `forbidden_dynamic_content` key `true` produce at least one ERROR finding and
  cause the contract check to fail closed.
- **SC-002**: 100% of committed filled background specs that are compliant (all
  forbidden keys false, all qa items true-or-reason) produce zero findings (zero
  false positives on legitimate background design).
- **SC-003**: With no filled background spec on disk (the current state, only the
  blank template committed), the rule produces zero findings -- the rule does not
  break the current green build and is inert on an empty corpus.
- **SC-004**: When two forbidden keys are declared true in one filled spec,
  exactly two findings are produced (one per occurrence), so no violation is
  masked.
- **SC-005**: A qa item recorded `false` WITH a reason produces zero findings,
  while the same item recorded `false` with NO reason produces exactly one
  finding.
- **SC-006**: A newly added committed filled spec is scanned with no change to the
  rule's code (generic discovery), and no tenant/example-specific path or key
  appears anywhere in the rule's vocabulary; the blank template is never flagged.
- **SC-007**: The rule's identifier is present in the registry and all governance
  golden records, and the wiring test passes (drift fails closed).

## Assumptions

- The template `templates/background-spec.yaml` is the authoritative, generic
  source of the asserted boolean vocabulary; the rule asserts exactly that
  declared contract and no tenant-specific extension of it.
- Scope is the DECLARED-BOOLEAN concern only. The rule asserts what the filled
  spec DECLARES about its background; it does NOT open, render, or verify the
  actual image binary against those declarations (that would require execution /
  image rendering -- out of scope, Principle VIII static-first, Principle II
  execution-only deferred).
- The rule runs entirely over committed text using the project's existing static
  governance mechanism; it requires no Power BI Desktop, no live service, no image
  library, and no network access (Principle VIII, static-first).
- The rule declares one identifier and observes its severity per branch; it does
  not introduce a governed per-rule severity table (ratified 044).
- The rule reads a declarative spec that carries no secrets; all authored
  artifacts are ASCII, UTF-8 without BOM, with short paths (Principle IX).
- The existing file-scanning rules' test-fixture exemption behavior is reused so
  fixtures may deliberately declare defects.
- This is an idea-bank governance-lint rule with no roadmap F-number; it advances
  no readiness stage (consistent with the sibling DL1 / A2 and the A1/B1
  idea-bank rules). Confirmation is recorded in Clarifications.

## Clarifications

### Session 2026-07-02

Advisor-resolved ambiguities (recommended answers integrated into the spec):

- **Q1 -- Placeholder still present in a discovered filled spec.** A file discovered
  as a filled background spec that still carries the template placeholder
  `<true|false>` in a `forbidden_dynamic_content` or `qa_checklist` value is
  neither a real `true` nor a real `false`. **Recommended answer**: treat a
  still-present placeholder in a value of a DISCOVERED filled spec as a half-filled
  defect and surface a finding ("value not filled: still the `<true|false>`
  placeholder"). The blank template itself is exempt from discovery entirely
  (Q3), so this only ever fires on a file the discovery convention says is filled.
  **Reasoning**: fail-closed is the conservative default -- a discovered filled
  spec that silently keeps a placeholder is a value nobody asserted, which is
  exactly the "silently claims compliance while declaring nothing" gap the rule
  exists to close. Silently skipping it would let a half-filled spec pass as
  clean. **Reversible**: easy (a parse-contract detail; loosening to "skip
  placeholder rows" later is a message/behavior change, not a golden-record
  contract).

- **Q2 -- Boolean vocabulary freeze.** Which exact keys does the rule assert?
  **Recommended answer**: freeze the vocabulary VERBATIM from the two declared
  blocks in `templates/background-spec.yaml`. The `forbidden_dynamic_content`
  keys asserted MUST be `false`: `contains_kpi_value`, `contains_dynamic_title`,
  `contains_measure_or_metric`, `contains_data_label_or_axis_value`,
  `contains_date_or_refresh_stamp`, `contains_filter_or_slicer_state`,
  `baked_in_screenshot_of_a_visual` (7 keys). The `qa_checklist` items asserted
  MUST be `true`-or-recorded-reason: `is_static_structure_only`,
  `no_forbidden_dynamic_content`, `exported_at_canvas_size_1to1`,
  `safe_zones_align_to_grid`, `whitespace_preserved`,
  `not_dark_behind_dense_charts`, `contrast_sufficient_for_visuals`,
  `consistent_aspect_ratio`, `branding_is_chrome_not_data` (9 items). **Reasoning**:
  deriving the vocabulary verbatim from the template's OWN declared contract (not
  from any tenant example) is the Principle-VII-clean reading and mirrors DL1. A
  future template key addition becomes a reviewed vocabulary change, not silent
  drift. **Reversible**: costly (the frozen list is encoded in the golden records;
  changing it is a reviewed vocabulary change across the wiring places).

- **Q3 -- Parse contract: real boolean vs placeholder vs recorded reason.**
  How does the rule distinguish the three value shapes? **Recommended answer**:
  a `forbidden_dynamic_content` value is a violation only when it parses to the
  real boolean `true`; a real `false` passes; the placeholder string
  `<true|false>` (or any non-boolean value) in a forbidden key is a finding
  (Q1 / malformed-value edge case). A `qa_checklist` item passes when it parses
  to real boolean `true`, OR when it is `false` accompanied by a recorded reason
  string; a bare `false` with no reason is a finding; the placeholder or a
  non-boolean value is a finding. The "recorded reason" is detected as a present,
  non-empty, non-placeholder reason string associated with that item; the rule
  detects PRESENCE of a reason, never judges the reason's adequacy (Principle V).
  **Reasoning**: this is the smallest categorical parse that honors the template's
  "each MUST be true; a false entry is a blocking reason or a recorded warning +
  reason" wording without the rule reading meaning into free text. **Reversible**:
  easy (parse-contract detail, not a golden-record contract).

- **Q4 -- Severity of a violation.** Is a declared defect an ERROR or a WARNING?
  **Recommended answer**: ERROR (fail closed), matching the sibling DL1 posture
  and the template's own "a true entry is a defect" / "a false entry is a blocking
  reason" wording. Severity is OBSERVED per branch from the emitted findings, not
  declared in a governed per-rule severity table (ratified 044). **Reasoning**: a
  declared baked-in KPI value is a substantive defect the surface exists to
  prevent; treating it as advisory would defeat the rule. Conservative and
  consistent with the design-lint family. **Reversible**: costly (severity posture
  is observed into the golden severity-posture record; a later downgrade is a
  reviewed posture change).

- **Q5 -- Readiness stage advanced.** Does A8 advance any readiness stage?
  **Recommended answer**: it advances NO readiness stage. A8 has no roadmap
  F-number; it is an idea-bank governance-lint rule (like DL1 / A2 and the A1 / B1
  idea-bank rules), a static checker that flags and never approves. **Reasoning**:
  self-granting a stage would violate Principle V (the rule packages, it never
  approves) and there is no roadmap mapping to advance. **Reversible**: easy (a
  human can later map it to a stage; the rule asserts nothing about stages today).

Principle-V convention RESOLVED (under the ADOPT-batch autonomous authority,
2026-07-02; conservative default, analogue of DL1's frozen `.theme.json`):

- **RESOLVED -- File-discovery convention for committed FILLED background specs.**
  The rule discovers committed files matching the generic suffix
  **`*.background.yaml`** (any path), and EXEMPTS `templates/` (the blank copy-me
  template with `<true|false>` placeholders) and the test-fixture path (via the
  existing `is_test_path()` seam). This is the direct analogue of DL1's frozen
  `.theme.json` suffix: a single generic, tenant-neutral naming convention that
  fixes where every future page's filled background spec lives, discovered by
  glob over `ctx.tracked_files`, never an enumerated or C086-specific list
  (Principle VII). The suffix is the frozen discovery convention the golden
  records encode. Day-one behavior is inert-and-green (FR-011): with zero
  committed `*.background.yaml` files today the rule emits zero findings -- it
  activates automatically the first time a page's background spec is filled and
  committed under that suffix. Widening/renaming the convention later is a
  deliberate follow-on rule change, not a silent edit. **Rationale**: reuses the
  proven DL1 discovery pattern verbatim; narrowest choice that lets the rule work
  without inventing a per-page directory layout the repo has not yet adopted.

All advisor-resolved items (Q1-Q5) are ANSWERED, and the file-discovery
convention (the one Principle-V item) is RESOLVED above under the ADOPT-batch
autonomous authority (frozen `*.background.yaml` suffix). No open item remains for
this spec; it is buildable and inert-safe on today's empty corpus.
