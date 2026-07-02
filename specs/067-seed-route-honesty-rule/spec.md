# Feature Specification: Seed-Layer Route Honesty Rule

**Feature Branch**: `067-seed-route-honesty-rule`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "I1. Seed-Layer Route Honesty Rule (a route that points at an initial-seed surface must be marked seed, not built)"

## Overview

The route registry `docs/routing/routes.yaml` makes the two-hop knowledge-routing
contract (AGENTS.md -> COMPASS.md -> knowledge-map -> skill SKILL.md -> INDEX.md ->
artifact) machine-checkable. Each route declares its `targets` and a `status`, and
the existing `A1` rule (`src/retail/rules/routes.py`) fails the `retail check` gate
when a route's declared status contradicts the tracked-file evidence.

Today `A1` recognizes exactly two status values -- `_VALID_STATUS = {built,
planned}`:

* `built`   -> EVERY target MUST resolve as a tracked file (a missing target is a
  broken route, ERROR).
* `planned` -> the target is deferred and MUST NOT resolve yet (a resolving
  `planned` target is a stale marker, ERROR).

This binary vocabulary cannot express a third, real state that the knowledge layer
already declares in prose: a route whose target file EXISTS on disk but is only an
INITIAL-SEED surface -- a first, deliberately-incomplete cut of a knowledge layer,
not a complete/built layer. `docs/knowledge-map.md` already declares two such
surfaces in human prose (the Retail KPI layer described as an "initial seed ... not
complete", and the Python layer described as an "initial seed"), and warns readers
against "treating the Retail KPI layer as complete". The KPI-contract layer even
carries a `Seeded` status vocabulary of its own.

Because `A1` has no `seed` status, a route pointing at one of these seed surfaces
must today be marked `built` (its target does resolve) -- which OVERSTATES the
surface's completeness. The route claims a complete layer where only an initial
seed exists. `A1`'s file-EXISTS check cannot mechanically tell a seed surface from a
complete one, so the overstatement passes the gate silently. This is the exact
dishonesty `A1` was built to prevent in the other direction (a `planned` marker that
overstates incompleteness is already an ERROR).

This feature EXTENDS the existing `A1` rule in place to recognize a third honesty
state, `seed`, so a route can honestly declare "this target exists but is only an
initial seed, not a complete layer." It adds NO new rule id and triggers NO wiring
seam (see Scope decision). `A1` VERIFIES the declared `seed` status against the
tracked-file evidence exactly as it already verifies `built` and `planned`; it
NEVER promotes a `seed` route to `built` and NEVER self-grants a status -- deciding
that a seed surface has become complete is a human judgment call (Principle V).

### Scope decision (load-bearing): EXTEND A1 in place, no new rule id

This feature adds the `seed` status by EXTENDING the existing `A1` rule and the
`docs/routing/routes.yaml` manifest vocabulary. It deliberately does NOT introduce
a new rule id. That choice is load-bearing because it determines which files are
touched:

* Because the rule id stays `A1`, the 5-place new-rule wiring seam is NOT triggered:
  `EXPECTED_RULE_IDS` in `tests/unit/test_rules_wiring.py` is UNCHANGED, the rule
  count is UNCHANGED, `docs/rules/rules-manifest.json` needs NO regen, and the
  severity-posture golden fixture needs NO regen. `A1` already exists in all of
  these; extending its accepted-status set does not add or remove an id.
* This is the conservative, YAGNI reading (CLAUDE.md scope discipline: add the seam,
  not the implementation): a third honesty STATE on an existing honesty rule is a
  vocabulary extension of that rule, not a new rule.

The alternative -- a distinct new rule id -- would trigger all five wiring places
plus two golden-file regens for no added expressive power, and is rejected as
over-scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A seed surface can be honestly declared and is verified (Priority: P1)

A knowledge-layer maintainer marks a route whose target is an initial-seed surface
with `status: seed` in `docs/routing/routes.yaml`. When `retail check` runs, `A1`
verifies the `seed` route the same way it verifies `built`: every target MUST
resolve as a tracked file (a seed surface exists on disk). A `seed` route whose
target does NOT resolve is a broken route (ERROR), symmetric to `built`. The `seed`
status adds honesty without weakening the existence guarantee.

**Why this priority**: This is the entire purpose of the feature -- give the
routing layer a truthful way to say "exists but is only an initial seed" instead of
being forced to overstate it as `built`. Without it the registry cannot express a
state the knowledge layer already declares in prose.

**Independent Test**: Author a fixture manifest with a `seed` route whose target IS
a tracked file; assert `A1` emits NOTHING. Author a second fixture with a `seed`
route whose target does NOT resolve; assert `A1` emits exactly one ERROR Finding
naming the route.

**Acceptance Scenarios**:

1. **Given** a route in `docs/routing/routes.yaml` with `status: seed` whose every
   target resolves as a tracked file, **When** `retail check` runs, **Then** `A1`
   emits no Finding for that route.
2. **Given** a route with `status: seed` whose target does NOT resolve as a tracked
   file, **When** `retail check` runs, **Then** `A1` emits exactly one ERROR
   Finding whose locator names the route, symmetric to the `built`-broken case.
3. **Given** a route with `status: seed` that lists NO targets, **When** `retail
   check` runs, **Then** `A1` emits an ERROR (a `seed` route, like `built`, points
   at an existing surface and must name at least one target -- it is not a
   deferred/empty `planned` route).

---

### User Story 2 - The unknown-status guard still fails closed (Priority: P1)

A maintainer mistypes a status (for example `seeded` or `partial`) that is not in
the accepted set. `A1` continues to reject any status outside `{built, planned,
seed}` with an ERROR, so the extension does not silently accept typos or invent
further states.

**Why this priority**: `A1` today fails closed on any status not in `_VALID_STATUS`.
Widening the set to three values must preserve that fail-closed guard exactly -- the
extension adds one accepted value, it does not relax the unknown-status check.

**Independent Test**: Author a fixture route with `status: partial`; assert `A1`
emits one ERROR naming the invalid status and listing the three accepted values.

**Acceptance Scenarios**:

1. **Given** a route with a `status` value not in `{built, planned, seed}`, **When**
   `retail check` runs, **Then** `A1` emits an ERROR whose message lists the three
   accepted statuses.
2. **Given** the accepted-status set is `{built, planned, seed}`, **When** the
   existing `built` and `planned` acceptance scenarios run, **Then** their behavior
   is UNCHANGED (no regression to the two established states).

---

### User Story 3 - No new rule id, no wiring drift, coverage rule unregressed (Priority: P1)

A maintainer confirms the extension adds no rule id: `EXPECTED_RULE_IDS`,
`docs/rules/rules-manifest.json`, and the severity-posture golden fixture are all
UNCHANGED, and the `A3` route-coverage bijection (`src/retail/rules/routes_coverage.py`,
which reconciles knowledge-map ids against `routes.yaml` ids) does not regress when
a route's status is `seed`.

**Why this priority**: The whole point of extending `A1` in place (rather than
adding a rule) is to avoid the 5-place wiring seam and two golden regens. If the
change accidentally drifted the rule set, or if `A3`'s id-set reconciliation broke
on the new status, the scope decision would be violated. `A3` reads status only
indirectly (it reconciles ids, not statuses), so a `seed` status MUST be verified
as a non-regression, not assumed.

**Independent Test**: Run `test_rules_wiring.py`; assert `EXPECTED_RULE_IDS` is
unchanged and `A1` remains present exactly once. Run the `A3` coverage rule against
a manifest containing a `seed` route; assert its id-set bijection still holds.

**Acceptance Scenarios**:

1. **Given** the `seed` extension is applied, **When** the registry is enumerated,
   **Then** the registered rule ids are UNCHANGED (`A1` present once; no id added or
   removed) and `EXPECTED_RULE_IDS` is UNCHANGED.
2. **Given** a `routes.yaml` route carries `status: seed`, **When** the `A3`
   route-coverage rule runs, **Then** `A3`'s knowledge-map-id vs manifest-id
   bijection produces the same result it would for the same route marked `built`
   (status does not affect `A3`'s id set).
3. **Given** the extension is applied, **When** `docs/rules/rules-manifest.json` and
   the severity-posture golden fixture are checked, **Then** neither requires
   regeneration (no new id, no severity change).

---

### Edge Cases

- **Seed route with a non-resolving target**: fails LOUD (ERROR) exactly like a
  broken `built` route -- a `seed` surface must exist on disk; a `seed` marker is
  not a licence for a missing file.
- **Seed route with no targets**: ERROR -- like `built`, a `seed` route points at an
  existing surface and must name at least one target; only `planned` legitimately
  has no resolving target.
- **Malformed / missing manifest**: unchanged from today -- a missing or untracked
  `docs/routing/routes.yaml`, or YAML that fails to parse, fails LOUD (ERROR), never
  a vacuous green (Principle VIII).
- **Unknown status typo (`seeded`, `partial`, ...)**: ERROR listing the three
  accepted values -- the extension does not silently accept near-misses.
- **A seed target that has actually become complete**: `A1` does NOT detect this and
  does NOT auto-promote. Deciding a seed surface is now complete (and flipping its
  route to `built`) is a human judgment call; the promotion criterion is out of
  scope and deferred (see Clarifications / [NEEDS CLARIFICATION]).
- **Zero seed routes on main at ship time**: if no committed route uses `seed` when
  the extension ships, `A1` behaves exactly as today for the existing `built`
  routes -- a genuine pass, not vacuous, because the accepted-status guard and the
  `built`/`planned` checks still run over all 29 existing routes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST extend the existing `A1` rule
  (`src/retail/rules/routes.py`) to accept a third `status` value, `seed`, by adding
  it to `_VALID_STATUS` (making the accepted set `{built, planned, seed}`).
- **FR-002**: The system MUST add the `seed` status value to the
  `docs/routing/routes.yaml` manifest vocabulary (its header-comment documentation
  of accepted `status` values) so the manifest and the rule agree on the accepted set.
- **FR-003**: For a route with `status: seed`, `A1` MUST require that EVERY target
  resolves as a tracked file (identical existence guarantee to `built`). A `seed`
  route whose target does NOT resolve MUST produce an ERROR Finding whose locator
  names the route.
- **FR-004**: For a route with `status: seed` that lists NO targets, `A1` MUST emit
  an ERROR (like `built`, a `seed` route points at an existing surface and must name
  at least one target; unlike `planned`, it is not a deferred/empty route).
- **FR-005**: `A1` MUST continue to reject any `status` value not in `{built,
  planned, seed}` with an ERROR whose message lists the three accepted values (the
  fail-closed unknown-status guard is preserved, not relaxed).
- **FR-006**: The behavior of the existing `built` and `planned` statuses MUST be
  UNCHANGED by this extension (no regression to the two established honesty states).
- **FR-007**: `A1` MUST NOT auto-promote, self-grant, or otherwise change a route's
  status; it only VERIFIES a declared status against tracked-file evidence.
  Promoting a `seed` route to `built` is a human judgment call the rule is
  structurally forbidden to make (Principle V).
- **FR-008**: The extension MUST add NO new rule id. `EXPECTED_RULE_IDS` in
  `tests/unit/test_rules_wiring.py` MUST be UNCHANGED, the rule count MUST be
  UNCHANGED, `docs/rules/rules-manifest.json` MUST NOT require regeneration, and the
  severity-posture golden fixture MUST NOT require regeneration.
- **FR-009**: The `A3` route-coverage rule (`src/retail/rules/routes_coverage.py`)
  MUST NOT regress in the presence of a `seed` route: its knowledge-map-id vs
  manifest-id bijection MUST behave identically whether a given route's status is
  `seed`, `built`, or `planned` (status does not affect the id set).
- **FR-010**: `A1` MUST continue to parse the manifest with a LAZY `import yaml`
  inside the handler (preserving the stdlib-only invariant of the `retail check`
  core chain) and MUST continue to read only committed text -- it MUST NOT execute
  anything, open a database/network/Power BI connection, or leave the static plane
  (Principle VIII).
- **FR-011**: A missing/untracked or unparseable `docs/routing/routes.yaml` MUST
  continue to fail LOUD with an ERROR Finding, never a vacuous green (unchanged from
  today).
- **FR-012**: `A1` MUST remain categorical (a Finding is emitted when the checked
  condition holds and nothing when it does not); the extension MUST introduce no
  numeric score, confidence, or threshold (hard rule #9).
- **FR-013**: The rule, the manifest vocabulary, and any test fixtures MUST be
  GENERIC routing/knowledge-layer machinery. NO C086/pharmacy-specific route target,
  KPI name, or dataset path may be baked into the rule or its fixtures; C086 may be
  CITED as an external filled instance only (Principle VII).
- **FR-014**: The extension MUST advance no readiness stage, grant no approval, and
  touch no DEFERRED capability (F016 Power BI Execution Adapter; F031-F033 spec-only
  runtimes). It is an idea-bank sequence rule with no roadmap F-number.
- **FR-015**: All authored artifacts MUST be ASCII + UTF-8 without BOM (use `--` and
  `->`, no non-ASCII glyphs; rule IX).
- **FR-016**: The machine-checkable criterion that PROMOTES a route target from
  `seed` to `built` -- i.e. what tracked evidence establishes that a seed surface
  has become a complete layer -- is [NEEDS CLARIFICATION: promotion criterion is a
  human judgment call (Principle V); undefined today; the rule MUST NOT invent it].
  Until a human rules on it, `A1` verifies the DECLARED `seed` status against file
  existence only and NEVER promotes; this FR records the deferral, it does not
  license the rule to self-decide promotion.

### Scope boundaries (explicit non-goals)

- **OUT**: Extending the shared binary `_VALID_STATUS` in
  `src/retail/rules/status_claims.py` (SC1) to a third `seed` state. SC1 shares the
  identical `{built, planned}` vocabulary, but whether SC1 also needs `seed` for
  consistency is an OPEN scope question recorded to open_for_human; this feature is
  limited to `A1` + `routes.yaml`.
- **OUT**: Any executor, Power BI connection, or live-surface completeness probe.
  `A1` remains a static file-existence check; it cannot and does not measure whether
  a surface's CONTENT is complete.
- **OUT**: Adding a new rule id, wiring seam, manifest regen, or golden-fixture regen.
- **OUT**: Marking any specific existing route `seed` as part of this feature. The
  feature adds the CAPABILITY (the accepted status + verification); WHICH routes are
  seed surfaces is a per-route human declaration, not part of the rule change.

### Key Entities *(include if feature involves data)*

- **Route registry manifest** (`docs/routing/routes.yaml`): the committed list of
  routes, each with `id`, `task`, `targets`, and `status`. This feature widens the
  accepted `status` vocabulary to `{built, planned, seed}`. `A1` reads it; it never
  writes it.
- **A1 rule** (`src/retail/rules/routes.py`): the existing `@register("A1", ...)`
  L2 route-resolution check. Extended to accept and verify the `seed` status. Reads
  committed text, imports `yaml` lazily, emits categorical ERROR Findings, executes
  nothing.
- **A3 route-coverage rule** (`src/retail/rules/routes_coverage.py`): the existing
  id-set bijection between the knowledge-map "Route by task" ids and `routes.yaml`
  ids. Reads status only indirectly; MUST NOT regress on the new value.
- **Seed surface**: a knowledge-layer target file that EXISTS on disk but is only an
  initial-seed cut, not a complete layer (declared in `docs/knowledge-map.md` prose
  and mirrored by the KPI-contract `Seeded` vocabulary). A `seed` route points at
  such a surface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A `seed` route whose targets all resolve produces zero `A1` Findings;
  a `seed` route with a non-resolving target produces exactly one `A1` ERROR naming
  the route.
- **SC-002**: A route with a status outside `{built, planned, seed}` produces one
  `A1` ERROR listing the three accepted values; the existing `built` and `planned`
  acceptance scenarios pass unchanged.
- **SC-003**: The rule-wiring test passes with `EXPECTED_RULE_IDS` UNCHANGED and
  `A1` present exactly once; no new rule id appears.
- **SC-004**: `docs/rules/rules-manifest.json` and the severity-posture golden
  fixture are byte-identical before and after the extension (no regen required).
- **SC-005**: The `A3` route-coverage rule yields the same result over a manifest
  whether a given route is marked `seed` or `built` (no bijection regression).
- **SC-006**: `A1` still fails LOUD on a missing/untracked or unparseable manifest
  (no vacuous green), and the import-boundary checks pass (the `yaml` import remains
  lazy; no module-scope DB/network import is added).
- **SC-007**: No C086/pharmacy literal appears in the `A1` rule, the `routes.yaml`
  vocabulary docs, or any test fixture added by this feature.

## Assumptions

- The `seed` state is HONEST and human-declared, not invented: `docs/knowledge-map.md`
  already declares the Retail KPI and Python layers as "initial seed ... not
  complete", and the KPI-contract layer already uses a `Seeded` vocabulary. This
  feature mirrors an existing human-declared fact into the routing layer; it does
  not fabricate a state.
- The authoritative status TOKEN at the route layer is `seed` (lowercase), matching
  the existing lowercase `built`/`planned` route vocabulary. The KPI-contract layer's
  `Seeded` (capitalized) is a sibling vocabulary in a different layer; aligning the
  exact spelling ACROSS layers is a naming decision recorded to open_for_human, not
  resolved here.
- All ~29 existing routes are `status: built` today; `planned` appears only in
  header-comment docs, never as a live route status; no `seed`/`seeded`/`partial`
  value exists yet -- so the third state is added from scratch, and the extension
  starts from a clean, known manifest.
- The core read-only helpers (`ctx.tracked_files`, `ctx.repo_root`) and the
  `@register` decorator exist and are reused as-is; the lazy-`yaml` pattern already
  in `A1` is preserved.
- This feature belongs to the idea-bank execution sequence (siblings A1/A3/SC1); it
  carries NO roadmap F-number (`f_number: none`) and advances NO readiness stage
  (`roadmap_stage: unmapped`). "Seed-Layer Route Honesty Rule" is a fresh
  idea-engine candidate, absent from `roadmap.md`, `idea-backlog.md`, and
  `shipped-ideas.yaml`.
- No DEFERRED capability is assumed to exist (F016 Power BI Execution Adapter;
  F031-F033 spec-only runtimes). This feature is a static-check vocabulary extension;
  it ships no executor.

## Dependencies

- **Existing seams (reused / extended in place)**: `A1`
  (`src/retail/rules/routes.py`) `_VALID_STATUS` + `check_routes_resolve()`;
  `docs/routing/routes.yaml` (the manifest + its status vocabulary docs);
  `@register` + `RuleContext.tracked_files` / `repo_root` (read-only helpers).
- **Non-regression targets (read-only, must not break)**: `A3`
  (`src/retail/rules/routes_coverage.py`) id-set bijection;
  `tests/unit/test_rules_wiring.py` `EXPECTED_RULE_IDS`;
  `docs/rules/rules-manifest.json`; the severity-posture golden fixture.
- **DEFINE-layer source of truth (read-only)**: `docs/knowledge-map.md` "initial
  seed" prose declarations; the `skills/retail-kpi-knowledge` `Seeded` vocabulary --
  the human-declared facts the `seed` route status mirrors.

## Clarifications

### Session 2026-07-02

Four answerable ambiguities drove the extension semantics. Each is resolved by
advisor ruling (the advisor holds recorded decision authority for
engineering/convention calls). The single Principle-V judgment call -- the seed ->
built promotion criterion -- is deliberately NOT answered; it is carried below to
the carve-out and left as a `[NEEDS CLARIFICATION]` marker in FR-016.

- **C1 -- Does a `seed` route require resolving targets (like `built`) or allow
  none (like `planned`)?**
  Decision: a `seed` route MUST have EVERY target resolve as a tracked file, exactly
  like `built`; a `seed` route with zero targets or a non-resolving target is an
  ERROR (FR-003, FR-004).
  Reasoning: a seed surface is defined as a file that EXISTS on disk but is only an
  initial cut. The distinguishing fact of `seed` vs `planned` is precisely that the
  target EXISTS; the distinguishing fact of `seed` vs `built` is a completeness
  claim the rule cannot mechanically check. So the only mechanical guarantee `A1`
  can and must enforce for `seed` is existence -- identical to `built`. Making `seed`
  target-optional would collapse it toward `planned` and lose the "exists but
  incomplete" meaning. Reversible: easy.
- **C2 -- What is the authoritative status token: `seed` or `Seeded`?**
  Decision: `seed` (lowercase), matching the existing lowercase route-layer
  vocabulary (`built`, `planned`).
  Reasoning: the route layer's tokens are all lowercase; `A1` compares against them
  literally. The KPI-contract layer's `Seeded` (capitalized) is a sibling vocabulary
  in a DIFFERENT layer. Aligning the exact spelling across layers is a naming
  decision, not a mechanical one, and is recorded to open_for_human. Reversible: easy.
- **C3 -- Does the sibling rule SC1 (`status_claims.py`) also gain the third
  `seed` state?**
  Decision: NO -- scope is limited to `A1` + `docs/routing/routes.yaml`. SC1 shares
  the identical `{built, planned}` vocabulary, but extending it is a separate concern
  recorded to open_for_human.
  Reasoning: SC1 reconciles PROSE status claims, a different manifest and a different
  failure mode. Bundling it in would widen scope past the one idea (YAGNI) and risk
  an SC1 golden-fixture disturbance. Keeping this feature to A1+routes.yaml is the
  minimal, most-reversible cut. Reversible: easy.
- **C4 -- Extend `A1` in place, or add a distinct new rule id?**
  Decision: EXTEND `A1` in place -- add `seed` to `_VALID_STATUS`; add NO new rule
  id, trigger NO wiring seam, require NO manifest/golden regen (FR-008).
  Reasoning: a third honesty STATE on an existing honesty rule is a vocabulary
  extension of that rule, not a new rule. A new id would trigger the 5-place wiring
  seam plus two golden regens for no added expressive power (over-scope). Reversible:
  costly -- if a future ruling wants an independently-severitied `seed` rule, that
  is an additive new-id change, but the vocabulary choice here is the baked default.

### Principle-V carve-out (recorded to open_for_human -- NOT resolved here)

- **The seed -> built promotion criterion** (FR-016): what machine-checkable tracked
  evidence establishes that a `seed` surface has become a COMPLETE layer and may be
  promoted to `built` (candidates: a declared "complete" marker, a contract count,
  INDEX completeness). This is a human judgment call and is undefined today. The rule
  MUST NOT invent it. This carve-out is BUILD-SAFE: `A1` verifies the DECLARED `seed`
  status against file existence without needing the promotion criterion, so the
  feature can ship while this remains open. Left as a `[NEEDS CLARIFICATION]` marker
  in FR-016 for the clarify stage / human ruling.
