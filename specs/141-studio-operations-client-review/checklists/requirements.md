# Requirements checklist: spec 141

Review gate for the specification itself, before ratification. Each item is checked
against the written package, not against intentions.

## Completeness

- [x] Every user story from the outline carried forward (US1-US4), plus US5 promoted from
      the outline's support-bundle requirements to a story in its own right
- [x] Every outline FR carried forward or explicitly corrected
- [x] New FRs added where the outline was silent (FR-141-021, FR-141-022)
- [x] Success criteria testable, each naming the proof
- [x] Key entities defined with field-level shapes
- [x] Assumptions stated rather than left implicit
- [x] Out-of-scope list retained, plus the no-second-decision-path exclusion

## Claims about shipped code (verified against the tree, not against this package)

The lesson from spec 140's promotion: internal consistency across a package cannot catch
an invented external fact. Each claim below was read from the file.

- [x] `doctor.py` returns `list[Finding]`; `Finding` is `rule_id`/`severity`/`message`/
      `locator` (`core.py:44`)
- [x] `Severity` is only `error`/`warning`/`info` -- **there is no six-state component
      vocabulary in the tree**, so US1's states are introduced by this spec
- [x] `doctor.repair_hint`, `group_by_rule`, `collect_findings`, `next_allowed_action`
      exist and are reused
- [x] `studio/events.py` provides `StudioEvent`, `ThreadEvents`, `ThreadStore`
- [x] `studio/redaction.py` provides `scrub_payload`, `redact_credentials`,
      `redact_paths`, `redact_for_boundary`
- [x] `studio/review_scope.review_for` refuses an absent scope
- [x] `decision_write.decisions_at_head` reads committed state
- [x] `evidence_pack.py` exists as the export precedent
- [x] Test helpers named in tasks.md exist (`_workbench_fixtures.py`,
      `_studio_workspace_fixtures.py`)

**The correction this promotion produced**: the outline implied Operations could read
component health from the diagnostic engine. It cannot -- the vocabulary does not exist.
FR-141-004 therefore forbids a second *probe set*, not a mapping layer, and Task A1 builds
that mapping as new code with its own tests.

## Consistency

- [x] No requirement contradicts another
- [x] FR-141-004 reconciled with the absent vocabulary
- [x] Entity names match across spec, data-model, contract, and tasks
- [x] The three-state decision model matches spec 140's exactly
- [x] Dependency claim (139 and 140 accepted) verified against both status lines

## Ambiguity

- [x] `deferred` defined once, distinguished from failure everywhere it appears
- [x] `ephemeral` vs `durable` defined by where a record lives, not by preference
- [x] `ComponentState` is a closed enum, not an open string
- [x] Allowlist vs denylist stated as a structural requirement, not a preference

## Placeholders

- [x] No TBD, TODO, or unresolved bracket
- [x] Deferred structural choices named and routed to the plan
- [x] No fabricated example: the `Finding` shape comes from the source

## Governance

- [x] Status says `draft`, not `ratified` -- no agent-written ratification
- [x] Status history records promotion and the direction ruling separately
- [x] The prerequisite is documented as satisfied, with what satisfied it
- [x] FR-141-020 retained; its promotion note states which condition is met
- [x] Promotion Gate says expansion delivered, ratification pending
- [x] No second decision-recording path, diagnostic engine, or redaction path authorized
- [x] Acknowledgement-is-not-approval expressed as a type constraint

## Verification discipline

- [x] Every contract obligation has a named proof
- [x] Every negative assertion paired with its positive twin (O1/O7 called out as the
      load-bearing pair)
- [x] The aggregate-score test searches for a numeric roll-up, not a field name
- [x] The bundle test scans the produced archive, not the intention
- [x] Cross-platform fixture warning carried (issue #691)
- [x] `pytest.importorskip("fastapi")` required on web-touching modules; lazy-import
      hoisting warning carried

## Scope

- [x] One coherent feature: two surfaces plus their shared export path
- [x] Spec 140 territory (proposals, decision recording, apply) left to 140
- [x] Phasing puts the disclosure primitives first, before anything discloses
- [ ] **Owner judgement**: is five user stories across three surfaces right for one
      ratification, or should US5 (support bundle) split into a follow-on spec? It shares
      only the scrubber with the rest, so the split is clean. Raised for the ratifier;
      the package is written whole.
