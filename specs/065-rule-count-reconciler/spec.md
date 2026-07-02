# Feature Specification: Rule-Count Claim Reconciler (SC2)

**Feature Branch**: `065-rule-count-reconciler`

**Created**: 2026-07-02

**Status**: Ratified (Ahmed Shaaban, 2026-07-02)

> Ratified under the recorded ADOPT-batch autonomous authority dated 2026-07-02
> (owner directive: build+ratify+merge the entire ADOPT bucket; the advisor
> exercises the delegated per-spec ratify authority). A recorded per-spec override
> within that batch, not a standing waiver. No OPEN carve-out remains. The load-
> bearing design fork is resolved in Clarifications Q1: the authoritative count
> source is the committed `docs/rules/rules-manifest.json` read with stdlib json --
> NOT an `all_rules()` import -- preserving the stdlib-only never-execute core
> (matches SC1's discipline). The two reserved items are roadmap-placement only and
> resolved conservatively: SC2 is governance-internal test/CHECK infrastructure in
> the SC1/DF1 family and takes NO roadmap F-row here (YAGNI; a human may add one
> later). SC2 is manifest-only, fail-loud, categorical (no score), CHECK-never-fix.
> analyze: clean (0/0); plan-review: PASS-WITH-NOTES.

**Input**: User description: "F4. Rule-Count Claim Reconciler (SC2)"

## Overview

The retail check kit already keeps *prose status claims* honest: rule SC1
(spec 050) reconciles a hand-curated manifest of "this artifact is built /
planned" prose claims against tracked-file evidence and fails the gate on any
contradiction. SC1 deliberately scoped itself to the file-exists-vs-status
class and, in its own docstring, delegated the *rule-COUNT facet* -- a document
asserting a specific number of static-check rules that no longer matches the
live set -- to "a separate future sibling". SC2 is that sibling.

Governance and glossary prose in this repo repeatedly restates a count of the
form "N rules". The live rule registry is the single source of truth for that
count, but the prose drifts: a document can keep asserting an old number long
after rules were added or removed. This is not hypothetical -- at authoring
time the glossary declares itself "the single source of truth for the rule
count" yet its prose says a number that no longer matches the authoritative
registry.

SC2 closes that gap for the *live-state integer-count prose-claim class*. A
human-curated manifest declares, per claim, which document makes the count
claim, the verbatim sentence that anchors it, and the integer the prose
asserts. SC2 parses each claimed integer and reconciles it against the
authoritative rule count, failing the gate on any mismatch -- the same
fail-closed, manifest-only, categorical shape SC1 uses for status claims.

SC2 is a static governance rule, not a runtime feature. It maps to no roadmap
readiness stage; it is an idea-bank integrity rule in the same family as the
shipped SC1 / DF1 rules, recorded outside the seven-stage Source -> ... ->
Publish readiness spine.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Catch a stale rule-count claim (Priority: P1)

A governance maintainer runs the retail check gate. A tracked document still
asserts an old rule count ("N rules") even though rules have been added since
the prose was last touched, so the live authoritative count is now a different
number. SC2 reports an ERROR naming the document, the claimed integer, and the
authoritative count, so the maintainer can correct the prose before the change
merges.

**Why this priority**: This is the core value -- the named, confirmed seed
defect (the glossary asserting a rule count that no longer matches the live
registry) is exactly this case. Catching a drifted count is the reason the rule
exists.

**Independent Test**: Construct a manifest entry whose `anchor` sentence
(present in the named doc) asserts an integer that differs from the
authoritative count; run SC2; assert exactly one ERROR finding naming that
entry. Delivers value on its own: the gate now fails on stale count claims.

**Acceptance Scenarios**:

1. **Given** a manifest entry `{doc, anchor, claimed-count}` where the anchor text is present in the doc and `claimed-count` differs from the authoritative rule count, **When** SC2 runs, **Then** it emits one ERROR finding stating the claimed count is stale and naming both the claimed integer and the authoritative count.
2. **Given** the same entry but `claimed-count` equals the authoritative rule count and the anchor is present, **When** SC2 runs, **Then** SC2 emits no finding for that entry (an accurate count claim is honest).

### User Story 2 - Fail loud on a moved anchor or an unparseable count (Priority: P1)

A maintainer edits a document and removes or reshapes the exact sentence the
manifest anchors on, or the manifest declares a `claimed-count` that is not a
parseable non-negative integer. SC2 must fail loud in every such case rather
than silently passing, so the manifest can never quietly stop checking a claim.

**Why this priority**: The other half of honest-in-both-directions. Without a
present-anchor guard, a manifest entry could silently point at a sentence that
has moved, and the count would go unchecked while the gate stayed green -- the
false-confidence failure the no-fake-confidence rule forbids.

**Independent Test**: (a) manifest entry whose `anchor` text is absent from the
named doc -> one ERROR; (b) manifest entry whose `claimed-count` is not a
non-negative integer -> one ERROR.

**Acceptance Scenarios**:

1. **Given** a manifest entry whose `anchor` text is not found in the named `doc`, **When** SC2 runs, **Then** it emits one ERROR finding that the anchor is stale or misplaced for that entry.
2. **Given** a manifest entry whose `claimed-count` is missing, non-integer, or negative, **When** SC2 runs, **Then** it emits one ERROR finding that the claimed count is malformed for that entry.
3. **Given** a manifest entry whose `doc` path is not a tracked file, **When** SC2 runs, **Then** it emits one ERROR finding that the claiming document is missing/untracked.

### User Story 3 - Fail loud on a missing/malformed manifest or an unreadable count source (Priority: P2)

The manifest file is missing, untracked, or malformed, or the authoritative
count source cannot be read or parsed. SC2 must fail loud in every such case
rather than silently passing, so a count reconciler can never go vacuously
green.

**Why this priority**: Fail-closed integrity. A count reconciler that can pass
with nothing to check, or that silently gives up when it cannot read the
authoritative number, is worse than none because it manufactures false
confidence.

**Independent Test**: (a) manifest absent/untracked -> one ERROR; (b) manifest
not valid YAML or wrong shape -> one ERROR; (c) authoritative count source
absent/untracked or unparseable -> one ERROR.

**Acceptance Scenarios**:

1. **Given** the manifest file is missing or not tracked, **When** SC2 runs, **Then** it emits one ERROR finding that the manifest is missing/untracked and SC2 cannot reconcile count claims.
2. **Given** the manifest is present but not valid YAML, or is not a mapping with a `claims` list, **When** SC2 runs, **Then** it emits one ERROR finding that the manifest is malformed.
3. **Given** the authoritative count source is missing, untracked, or not parseable into a count, **When** SC2 runs, **Then** it emits one ERROR finding that the count source cannot be read and no count claim can be reconciled.

### Edge Cases

- **Anchor matches more than once**: the anchor is a presence check (is the claiming sentence still in the doc), so multiple matches are treated the same as one match -- present is present. No line/offset is recorded (avoids a brittle positional matcher). The integer that SC2 reconciles comes from the manifest's `claimed-count` field, not from re-parsing the doc text, so a repeated anchor does not create an ambiguous parse.
- **Empty manifest** (`claims: []`): not an error in itself -- an explicitly empty list is honest. (Manifest *completeness* is explicitly NOT SC2's job; see Out of Scope.)
- **Entry missing a required field** (`id` / `doc` / `anchor` / `claimed-count`): ERROR for that entry; SC2 never guesses a missing field.
- **A dated / as-of snapshot count** (e.g. an ADR that recorded "28 rules" on a past date): NOT an SC2 target. Such claims were correct as-of-then and MUST NOT be listed in the manifest. SC2 only checks the live-state claims the manifest author lists; it never free-scans the repo for "N rules" strings, so a dated record is never touched.
- **Anchor under `tests/`**: tracked-file resolution uses the same tracked-files set the other rules use; SC2 does not apply a test-fixture content exemption because it reconciles declared claims, not scans the tree. The manifest author is responsible for anchoring only on a live-state governance document, not a throwaway fixture.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a registered static rule, id `SC2`, that the retail check gate runs as an enforced rule (a contradiction produces a finding at ERROR severity, which fails the build with a non-zero exit). SC2 MUST NOT be advisory-only prose.
- **FR-002**: SC2 MUST read its claims from a single human-curated manifest at a fixed repo-relative path (`docs/quality/rule-count-claims.yaml`). The manifest MUST be parsed only when SC2 runs (not at module import).
- **FR-003**: SC2 MUST treat the manifest as a mapping containing a list of claim records under a top-level key (`claims`). Each record declares: `id` (stable handle), `doc` (repo-relative POSIX path of the claiming document), `anchor` (a verbatim text snippet expected to be present in that document), and `claimed-count` (the non-negative integer the prose asserts).
- **FR-004**: SC2 MUST fail loud if the manifest is absent or not a tracked file: emit one ERROR finding and verify nothing further. It MUST NOT pass vacuously when it has nothing to check.
- **FR-005**: SC2 MUST fail loud (ERROR) if the manifest is not valid YAML, or is not a mapping with a `claims` list.
- **FR-006**: SC2 MUST derive the authoritative rule count from the committed rule-count source of truth (`docs/rules/rules-manifest.json`), read as committed repository text and parsed with a standard-library data reader. It MUST fail loud (ERROR) if that source is missing, untracked, or cannot be parsed into a count. SC2 MUST NOT import the rules package (or any governed application code) at module scope to obtain the count. (See Clarifications Q1.)
- **FR-007**: For each claim record, SC2 MUST verify the claiming `doc` is itself a tracked file; if not, emit an ERROR for that entry.
- **FR-008**: For each claim record, SC2 MUST verify the `anchor` text is present (substring presence) in the claiming document's committed text; if absent, emit an ERROR that the anchor is stale or misplaced. SC2 MUST read the document text via the repository root provided in its run context, not from any live source.
- **FR-009**: For each claim record, SC2 MUST verify `claimed-count` is a parseable non-negative integer; if it is missing, non-integer, or negative, emit an ERROR that the claimed count is malformed for that entry.
- **FR-010**: For a well-formed record whose anchor is present, SC2 MUST emit an ERROR if `claimed-count` does not equal the authoritative rule count. The finding MUST name both the claimed integer and the authoritative count. A record whose `claimed-count` equals the authoritative count produces no finding.
- **FR-011**: SC2 MUST emit an ERROR for any record missing any required field (`id` / `doc` / `anchor` / `claimed-count`), rather than guessing or skipping silently.
- **FR-012**: Every SC2 finding MUST carry the rule id `SC2`, ERROR severity, a human-readable message naming the offending document and the claimed vs authoritative count (or the specific fault), and a locator that points at the manifest entry (and/or the claiming doc) so the maintainer can find it.
- **FR-013**: SC2 MUST remain strictly CATEGORICAL: a count either equals the authoritative count or it does not. SC2 MUST NOT compute, emit, or infer any numeric confidence score, readiness percentage, or other graded value. (The claimed integer and the authoritative integer named in a finding are the reconciled counts themselves, not a confidence measure.)
- **FR-014**: SC2's rule module MUST carry no module-scope database, network, or Power BI import, and no module-scope import of the rules package. Any YAML parsing dependency MUST be imported lazily inside the handler; the JSON count source MUST be read with the standard library. SC2 MUST read only committed repository text and the tracked-files set -- no database, no network, no live Power BI surface.
- **FR-015**: The rule MUST self-register through the existing rule-registration mechanism (a decorator side effect on import of its submodule). Registering SC2 requires the established rule-wiring steps: adding the new submodule to the rule package's side-effecting import list and `__all__`, adding `SC2` to the single-source-of-truth expected-rule-id set in the rule-wiring test, and regenerating the golden rule-count manifest and the severity-posture snapshot so their committed contents match the live registry. Every such wiring surface MUST be updated in the same change so the wiring/drift and golden-snapshot tests continue to pass.
- **FR-016**: The manifest MUST be GENERIC count-claim machinery. Neither the rule code nor any kit-level seed manifest entry may hardcode or special-case a worked-example-specific (C086 / pharmacy) document path or value. The rule schema must be applicable to any live-state document making an integer rule-count claim.
- **FR-017**: The manifest MUST scope only LIVE-STATE count claims (current-state governance/glossary/roadmap prose). Dated as-of-then snapshots (ADR / decision / audit records that recorded a count on a past date) MUST NOT be listed. This scope is a manifest-authoring discipline; SC2 enforces it structurally by being manifest-only (it never free-scans prose for "N rules" strings).
- **FR-018**: The seed manifest MUST include the confirmed generic seed defect: the glossary line that asserts a rule count no longer matching the live registry. The change that introduces SC2 MUST also CORRECT the seeded stale prose (update the glossary count claim to the live count) in the SAME change, so the gate is green on the feature branch at merge. Because adding SC2 increases the registry by one, the corrected glossary count and the seed manifest's `claimed-count` MUST both equal the post-SC2 authoritative count (the count AFTER SC2 is registered), NOT the pre-SC2 count. Rationale: an enforced rule that ships RED on main would block every subsequent change; the seed defect and its fix land together (a tracked-document text correction, not a re-decision). See Clarifications (Q2).
- **FR-019**: SC2 MUST be accompanied by unit tests that exercise: a stale count claim (ERROR), an accurate count claim (no finding), a moved/absent anchor (ERROR), a malformed/missing `claimed-count` (ERROR), a missing/untracked claiming doc (ERROR), a missing/untracked manifest (ERROR), a malformed manifest (ERROR), and an unreadable/unparseable authoritative count source (ERROR).

### Out of Scope

- **Family-count claims.** Prose that asserts a number of rule *families* (for example "N families") is explicitly NOT covered by SC2's first step. SC2 reconciles only the integer *rule* count. A family-count facet, if wanted, is an optional future extension -- not part of SC2. See Clarifications (Q3).
- **Auto-resolving / self-editing a doc to fix a count.** SC2 CHECKs a count a human wrote; it MUST NEVER edit a document to "fix" a drifted count. Correcting stale prose is a human edit. The one glossary correction in the seed change (FR-018) is a human-authored text correction made once as part of introducing the rule, not an SC2 runtime behaviour.
- **Manifest completeness / coverage.** Nothing in SC2 verifies that the manifest enumerates every count claim in the repo. SC2 checks only the claims that are listed. This leaves a known drift gap (a count claim no one added to the manifest is not checked). The spec records this gap; it does NOT build a coverage rule. The gap is ACCEPTED for SC2's first step, mirroring how SC1 shipped without a completeness sibling. A coverage check, if wanted, is a separate future idea. See Clarifications (Q4).
- **Re-parsing the count out of the doc text.** SC2 reconciles the manifest's declared `claimed-count` field against the authoritative source; it does NOT extract an integer from the anchor sentence itself. The anchor is a presence check only. This keeps the parse unambiguous and avoids a brittle in-prose number scanner.
- **Any live capability.** No database provisioning, no ingestion, no Power BI execution adapter (F016), no spec-only runtimes (F031-F033). SC2 is static-only.
- **Amending any ratified decision.** Fixing the stale glossary count is a tracked-document text correction, not a re-decision or version bump of any ratified principle.

### Key Entities *(include if feature involves data)*

- **Rule-count-claim manifest**: a committed, human-curated YAML file. Holds a list of count-claim records. Single source of truth for what SC2 checks. Generic -- not tied to any worked example, and scoped to live-state claims only.
- **Rule-count-claim record**: one declared claim. Attributes: `id` (stable handle), `doc` (claiming document path), `anchor` (verbatim snippet that must still be present in the doc), `claimed-count` (the non-negative integer the prose asserts).
- **Authoritative count source**: the committed rule-count source of truth (the golden rule-count manifest), read as committed text and already golden-tested to equal the live registry count. SC2 derives the authoritative integer from it without importing governed code.
- **Finding**: the existing rule-output value (rule id, severity, message, locator). SC2 produces ERROR findings only.
- **Run context**: the existing read-only context handed to every rule -- provides the repository root (to read committed document and count-source text) and the tracked-files set (to resolve file existence). SC2 consumes both; it adds no new context field.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When the manifest contains the seeded stale-count defect (a claimed count that does not equal the authoritative count), running the gate fails with a non-zero exit and a finding that names the offending document, the claimed integer, and the authoritative count -- demonstrated by a unit test.
- **SC-002**: Every fault class -- stale count, moved/absent anchor, malformed/missing count, missing/untracked doc, missing/untracked manifest, malformed manifest, unreadable/unparseable count source -- produces at least one ERROR finding; every honest claim (an accurate count with a present anchor) produces zero findings. 100% of the enumerated cases are covered by passing unit tests.
- **SC-003**: After SC2 lands, the rule-wiring/drift test passes with the expected-id set containing `SC2` and the registered-rule count equal to the size of that set, and the golden rule-count manifest and severity-posture snapshot match the live registry.
- **SC-004**: SC2 emits zero numeric confidence/readiness values in any finding (verifiable by inspecting finding messages -- they are categorical statements naming the reconciled integer counts only).
- **SC-005**: SC2 performs no database, network, or Power BI access, and no module-scope rules-package import, during a gate run (verifiable: the never-execute import rule reports no forbidden module-scope import in SC2's module, and the rule runs with only the repo checkout present).
- **SC-006**: After the seed change, the retail check gate is GREEN on the feature branch: the seeded glossary claim, its manifest `claimed-count`, and the authoritative post-SC2 count are all equal.

## Assumptions

- SC2 reuses the existing rule abstraction (a pure function: read-only context in, findings out) and the existing finding/severity value types; it introduces no new core types.
- SC2 reuses the existing tracked-files population mechanism (derived from the version-control file list, repo-relative POSIX paths) -- the same source SC1 resolves paths against -- so file-existence resolution behaves identically to SC1.
- The YAML parsing dependency already used lazily by sibling rules (SC1, the contract loader) is available as a development/optional dependency and is imported the same lazy way. The authoritative count source is read with the standard library (no third-party dependency).
- The committed rule-count source of truth is already golden-tested elsewhere to equal the live registry count, so reconciling prose against it is equivalent to reconciling against the live registry, without importing governed application code. (See Clarifications Q1.)
- The manifest is authored and maintained by humans; SC2 does not generate or auto-populate it, and never edits a claiming document. Ownership of keeping the manifest current, and of scoping it to live-state claims only, is a human responsibility (see the accepted completeness gap).
- SC2 maps to no roadmap F-number and advances no readiness stage; it is recorded as an idea-bank integrity rule (sibling to SC1 / DF1), OUTSIDE the seven-stage Source -> ... -> Publish readiness spine. This is the confirmed home: SC2 is governance/observability-integrity machinery, structurally identical to SC1/DF1, none of which sit on the readiness spine. See Clarifications (Q5).

## Clarifications

### Session 2026-07-02

Five build-relevant ambiguities were resolved by the advisor against the
constitution, the readiness spine, the retail-check stdlib-only invariant, and
how the shipped SC1 sibling was decided. None is a Principle-V carve-out (SC2
touches no data grain, PII, business rollup, or product identity -- it
reconciles a prose integer against a committed count source), so none is
deferred to a human ruling.

- **Q1 (authoritative count source)**: Should SC2 obtain the live count by
  importing the rules registry (`len(all_rules())`), or by reading the committed
  golden rule-count manifest (`docs/rules/rules-manifest.json`) with the standard
  library? **Recommended answer**: Read the golden manifest with the standard
  library; do NOT import the rules package at module scope. **Reasoning**: The
  retail check core is stdlib-only (SC1 keeps it dependency-free, using only a
  lazy `import yaml` inside its handler). The golden rule-count manifest is
  already golden-tested to equal the live registry count, so reading it is
  equivalent to reading the registry -- but without pulling governed application
  code into the gate core, preserving the invariant. **Reversible**: costly (the
  count-source choice shapes the module's import surface and the never-execute
  guarantee; switching later would be a design change, not a text edit).
  Integrated into FR-006, FR-014, and Assumptions.

- **Q2 (delivery sequencing of the seed fix and its target value)**: Should
  introducing SC2 also correct the seeded stale glossary count in the same
  change, and to what value? **Recommended answer**: Correct it in the same
  change, to the POST-SC2 count. **Reasoning**: An enforced ERROR rule that ships
  RED on main would block every later change until someone fixes the prose, so
  the seed defect and its correction must land together. Because adding SC2
  itself increments the registry by one, the corrected glossary count -- and the
  seed manifest's `claimed-count` -- must equal the count AFTER SC2 is
  registered, not the pre-SC2 count; otherwise the gate would be red the moment
  SC2 registers. **Reversible**: easy (the prose fix is a small text edit).
  Integrated into FR-018 and SC-006.

- **Q3 (family-count scope)**: Should SC2 also reconcile family-count claims
  (for example "N families"), or only the integer rule count? **Recommended
  answer**: Only the integer rule count for v1. **Reasoning**: The idea's
  first-step names only the integer count; a family count is a distinct claim
  class with its own source of truth and is optional. Adding it now is scope
  creep (YAGNI). **Reversible**: easy (a family-count facet can be added later as
  a sibling extension without changing SC2's core). Integrated into Out of Scope.

- **Q4 (manifest-completeness drift gap)**: Accept that nothing checks the
  manifest is complete, or pair SC2 with a coverage rule now? **Recommended
  answer**: Accept the gap for SC2's first step. **Reasoning**: SC1 shipped its
  claim-reconciler without a completeness sibling; the same staged path applies
  here. Building a coverage rule now is scope creep and a separate idea.
  **Reversible**: easy (a coverage rule can be added later as a sibling without
  changing SC2). Integrated into Out of Scope.

- **Q5 (readiness-spine placement)**: Is SC2 correctly outside the seven-stage
  readiness spine, recorded as an idea-bank integrity rule? **Recommended
  answer**: Yes -- outside the spine, sibling to SC1/DF1. **Reasoning**: SC2 is
  governance/observability-integrity machinery with no roadmap F-number and
  advances no Source->...->Publish stage, structurally identical to the SC1/DF1
  integrity rules that are all recorded off-spine. **Reversible**: easy (a future
  roadmap edit could map it if ever wanted). Integrated into Assumptions.

### Deferred to human ruling (Principle V)

None. SC2 surfaces no grain/uniqueness, PII publish-safety, business
rollup/segment, or product-identity question. The rule reconciles a declared
integer count claim against a committed count source and committed document text
only.

Two decisions remain a human's to make at ratify time (they are the roadmap
owner's call, not a spec ambiguity, and the workflow must not assign them): the
roadmap readiness stage SC2 advances (recorded here as off-spine) and the
roadmap F-number / spec-number a human assigns for SC2 (SC1=050, DF1=051; SC2
would be a new number). These are recorded for the human, not answered by this
workflow.
