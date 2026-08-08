# Feature Specification: Remove the Spec Kit template fork and externalize Seshat status governance

**Feature Branch**: `151-speckit-fork-removal`

**Created**: 2026-08-08

**Status**: draft

<!-- One of: draft | ratified | implemented | superseded (ADR 0019).
     draft       -- authored, not yet ratified by a named human
     ratified    -- a named human approved THE SPEC; record their name and the date
     implemented -- the capability exists on `main`; MUST name its artifact, e.g.
                    `**Status**: implemented -- artifact `src/seshat/foo.py``, and gets a
                    `spec-<NNN>-implemented` claim in docs/quality/status-claims.yaml
     superseded  -- replaced; name the superseding spec id
     When changing this value, move the previous text verbatim into a
     `**Status history**:` line rather than deleting it. -->

**Input**: Owner decision, 2026-08-08: Spec Kit owns Spec Kit; Seshat owns Seshat
governance. The local modification of `.specify/templates/spec-template.md` is
rejected as architecture. Its governance behavior must survive through a
Seshat-owned mechanism outside upstream-managed content, and the fork must not
be relocated under another name.

## Why this exists

Seshat's spec-status governance is currently encoded, in part, inside a file
that upstream Spec Kit owns and regenerates.

Commit `f35612f` added an eleven-line comment block to
`.specify/templates/spec-template.md`, changing the seeded value from upstream's
`**Status**: Draft` to `**Status**: draft` and documenting the closed four-value
vocabulary from ADR-0019. The change is deliberate and the ADR behind it is
owner-ratified (2026-07-30). It is nonetheless a fork of upstream-managed
content: any ordinary `specify` re-init or upgrade overwrites it and silently
reverts a ratified governance decision.

The fork exists because ADR-0019 chose documentation-and-test enforcement rather
than a shipped rule. That choice is what put Seshat policy inside an upstream
file. This feature corrects the placement without weakening the policy.

### The dependency graph, as measured

Measured on `main` at `766c0ee`, not assumed:

| Consumer | Reads the template? | Notes |
| --- | --- | --- |
| `tests/unit/test_spec_status_vocabulary.py` | **YES -- reads content** | The ONLY code that reads the file. Asserts the vocabulary block is present and the seeded value is in the vocabulary. Runs under `pytest -m unit`, which CI executes. |
| `.specify/scripts/powershell/create-new-feature.ps1` | copies bytes | Scaffolds a new spec by `Copy-Item`. Never parses status. |
| `.specify/integrations/speckit.manifest.json` | records a hash | Nothing reads this manifest at runtime. Its recorded hash no longer matches the file, and nothing noticed. |
| `src/seshat/rules/status_claims.py` (SC1) | **NO** | Generic claim reconciliation over `docs/quality/status-claims.yaml`; its own vocabulary is `{built, planned}`. |
| `.claude/workflows/implement.js` (H3 gate) | **NO** | Hardcodes its own ratification regex by design. |
| `src/seshat/fence.py` | **NO** | SESHAT-KIT fence only; explicitly never touches the SPECKIT fence. |
| `kit_lint.py`, `capability_feeders.py`, `core.py`, `doctor.py` | **NO** | No `**Status**:` parsing; grep returns zero hits. |

So exactly one consumer depends on the template's content, and it is a test. No
shipped `src/seshat` code, no `seshat check` rule, and no CLI surface reads the
vocabulary from the template or from anywhere else.

### The defect this surfaced

Two ratification grammars already exist on disk and they disagree.

`implement.js` gates implementation on `H3_RATIFIED_RE`:

```
/^\s*-?\s*\*\*Status:?\*\*:?\s*Ratified \(.+?,\s*\d{4}-\d{2}-\d{2}\)/m
```

Case-sensitive, capital `Ratified`, parenthesized name and date. ADR-0019 and
the forked template mandate lowercase `ratified`. Run against the real, merged
`specs/150-dbt-evidence-consumer/spec.md`, whose status line reads
`**Status**: ratified -- Ahmed Shaaban, 2026-08-08`:

```
H3_RATIFIED matches? false
H3_DRAFT    matches? false
=> implement.js would REFUSE (H3)
```

A spec ratified exactly as the ADR instructs is refused by the workflow that
consumes ratification. It fails closed, which is the safe direction, but it
fails for the wrong reason and it proves the two authorities were never
reconciled. Any design that externalizes the vocabulary MUST reconcile them or
it will institutionalize the disagreement.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upstream Spec Kit content is upstream's again (Priority: P1)

A maintainer runs an ordinary Spec Kit re-init or upgrade and does not have to
reapply a Seshat patch afterwards, because no Seshat-specific content lives in
upstream-managed files.

**Why this priority**: This is the owner's decision and the whole point of the
feature.

**Independent Test**: Compare `.specify/templates/spec-template.md` against its
upstream baseline and assert no Seshat-specific content remains.

**Acceptance Scenarios**:

1. **Given** the migration is complete, **When** the template is compared to its
   upstream baseline, **Then** it carries no Seshat vocabulary block and no
   Seshat-modified seeded status value.
2. **Given** the template is restored, **When** the spec-kit manifest hash is
   recomputed, **Then** it matches the recorded upstream hash after line-ending
   normalization.
3. **Given** a future upgrade replaces the template, **When** the governance
   suite runs, **Then** it still passes without any manual patch.

---

### User Story 2 - Every guarantee that exists today still exists after (Priority: P1)

Every governance guarantee ADR-0019 *actually enforces today* still holds after
the template is clean, and is enforced by a Seshat-owned authority rather than
by a comment in someone else's file.

**Why this priority**: Equal to US1. Removing the fork is only acceptable if the
policy survives. A migration that quietly drops a guarantee is worse than the
fork.

**What is actually enforced today** (measured, 139 specs on `main` at `766c0ee`):

| Status value class | Count | Enforced today? |
| --- | --- | --- |
| canonical lowercase vocabulary | 20 | only the 10 `implemented` ones |
| `Draft` (capital) | 40 | no |
| `Ratified` (capital) | 40 | no |
| `Implemented` (capital) | 11 | no |
| `Shipped` / `**BUILT**` / `Finalized` / `Planned` / other free text | 19 | no |
| no `**Status**:` line at all | 9 | no |

Only the 10 specs matching `_IMPLEMENTED` are checked by anything. **110 of 139
specs carry a value outside the closed vocabulary and nothing rejects them.**
ADR-0019's vocabulary is therefore ~86% unenforced across the corpus.

This is decisive for scope: "externalize the policy" must NOT silently become
"enforce the policy corpus-wide for the first time." Those are different
changes with different blast radii, and conflating them would turn CI red on
110 committed specs.

**Independent Test**: Restore the upstream template in a scratch tree and assert
the governance suite still rejects exactly what it rejected before, no more and
no less.

**Acceptance Scenarios**:

1. **Given** a spec claiming `implemented` without a tracked artifact, **When**
   the authority runs, **Then** the existing SC1 claim requirement still fires --
   the one guarantee that is genuinely enforced today.
2. **Given** the 110 specs whose status is outside the vocabulary, **When** the
   migration completes, **Then** CI is exactly as green as before: this feature
   does not newly fail them (FR-023).
3. **Given** the authority is asked to validate one of those 110 lines directly,
   **When** it runs, **Then** it reports the value as outside the vocabulary --
   the capability exists and is tested, even though no consumer applies it
   corpus-wide yet (FR-024).

---

### User Story 3 - One authority, and the two grammars agree (Priority: P1)

A human who writes a status line exactly as the policy instructs is accepted by
every consumer of that line, including the implement workflow's H3 gate.

**Why this priority**: This is a live defect today, demonstrated above against a
merged spec. Externalizing the vocabulary without fixing it would give the
disagreement a permanent home.

**Independent Test**: Take the canonical ratified form emitted by the policy
authority and assert `implement.js`'s H3 gate accepts it.

**Acceptance Scenarios**:

1. **Given** a status line in the canonical ratified form, **When** H3 evaluates
   it, **Then** it matches and implementation is permitted to proceed.
2. **Given** a `draft` spec, **When** H3 evaluates it, **Then** it refuses.
3. **Given** the policy authority and the H3 grammar, **When** a contract test
   compares them, **Then** it fails if either changes without the other.

---

### User Story 4 - The stale audit line tells the truth (Priority: P2)

A reader of the ownership audit is not told the vendored copy is provably
unmodified when a modification exists.

**Why this priority**: Documentary accuracy on a governance record. Lower than
the migration itself, but it must not be skipped -- the false line is the stated
justification for closing the vendoring question.

**Independent Test**: The corrected passage names the modification, the chosen
architecture, and this spec.

**Acceptance Scenarios**:

1. **Given** `docs/capabilities/ownership-audit.md`, **When** the "provably
   unmodified" passage is read, **Then** it records that a local template
   modification exists, that the decision is to remove rather than
   institutionalize it, and that spec 151 tracks the migration.
2. **Given** the audit's other claims, **When** the correction lands, **Then**
   the historical audit is otherwise unchanged.

## Requirements

### The authority

- **FR-001**: Seshat's spec-status policy MUST have exactly ONE canonical
  executable owner inside `src/seshat/`. It defines the closed vocabulary, the
  canonical case, the accepted line grammar, and the evidence each value
  requires.
- **FR-002**: The authority MUST be importable by tests and by any future
  consumer, so no consumer needs to restate the vocabulary.
- **FR-003**: The authority MUST NOT be a new state machine. It declares a
  vocabulary and validates a line; it does not track transitions, own approvals,
  or duplicate the readiness spine.
- **FR-004**: The authority MUST NOT read `.specify/templates/spec-template.md`,
  nor any other upstream-managed Spec Kit file, to determine policy. A checker
  that derives its expectations from the artifact it validates proves nothing.

### Behavior that must survive

- **FR-005**: The closed four-value vocabulary (`draft`, `ratified`,
  `implemented`, `superseded`) MUST remain enforced.
- **FR-006**: Values outside the vocabulary MUST be rejected. This rule carries
  NO exception list. The seeded upstream `Draft` is handled by normalizing it at
  scaffold time (FR-025), not by excusing it here -- which is what keeps this a
  single testable rule.
- **FR-007**: `implemented` MUST continue to require a named tracked artifact
  and a corresponding SC1 claim in `docs/quality/status-claims.yaml`. SC1 is
  reused, not replaced (ADR-0019 §3).
- **FR-008**: `ratified` MUST continue to require a named human and a date, and
  MUST NOT be self-grantable by an agent. The existing `implement.js` git-blame
  provenance check remains the authority on human authorship; this feature does
  not weaken it.
- **FR-009**: The status-history convention (previous value preserved verbatim
  on a `**Status history**:` line) MUST survive as policy, expressed by the
  authority rather than by the template comment.

### The grammar reconciliation

- **FR-010**: The canonical ratified form emitted or described by the authority
  MUST be accepted by `implement.js`'s H3 gate. Today it is not; the feature
  MUST close that gap. **Resolution (agent recommendation, 2026-08-08): WIDEN
  ADDITIVELY.** H3 accepts the ADR lowercase form IN ADDITION to the legacy
  parenthesized form. Rejected alternative: making the ADR form the only form
  and migrating every committed status line -- that touches ~40 `Ratified`
  specs, risks refusing a spec mid-flight, and pulls corpus migration into a
  feature that FR-023 deliberately keeps out. Additive widening cannot
  invalidate an already-ratified spec; FR-011's divergence test is what stops
  the two forms drifting apart afterwards.
- **FR-011**: A contract test MUST fail if the authority's grammar and the H3
  grammar diverge, so the two verifiers cannot drift apart again.
- **FR-012**: Reconciliation MUST NOT be achieved by loosening H3 into accepting
  anything. H3's fail-closed posture and its human-provenance requirement are
  preserved; only the grammar is aligned.
- **FR-012a**: The reconciled draft-detection grammar MUST NOT match a
  `**Status history**:` line. Demonstrated regression: widening the prefix from
  `\*\*Status\*\*` to `\*\*Status[^*]*\*\*` makes `**Status history**: draft`
  match `H3_DRAFT_RE`, which would refuse a correctly ratified spec that carries
  the ADR-mandated history line -- including `specs/150-dbt-evidence-consumer`.
  A test MUST pin this exact case. (Added by adversarial review round 1.)

### The template restoration

- **FR-013**: `.specify/templates/spec-template.md` MUST be returned to its
  upstream baseline content, with no Seshat vocabulary block and no
  Seshat-modified seeded value.
- **FR-014**: Restoration MUST happen only AFTER the authority exists and the
  consumers are migrated. At no point may an invalid status or a missing
  approval become temporarily acceptable.
- **FR-015**: The spec-kit manifest entry for the template MUST agree with the
  restored file after line-ending normalization.

### Anti-relocation

- **FR-016**: The fork MUST NOT be relocated. Specifically forbidden: copying
  the modified template into a Seshat directory; maintaining a patch file
  reapplied after upgrades; creating a second template carrying upstream content
  plus Seshat edits; duplicating upstream Spec Kit behavior in Seshat; or
  creating a second status state machine.
- **FR-017**: Seshat MUST NOT own a copy of the upstream template's body. If
  Seshat needs to show an author what a good status line looks like, it emits
  its own short guidance from the authority -- not a mirrored upstream file.

### Fail-closed

- **FR-018**: A spec file with no `**Status**:` line, an unparseable line, or a
  value outside the vocabulary MUST be reported as a defect. Absence is never
  treated as valid.
- **FR-019**: If the authority cannot read a spec file it was asked to check, it
  MUST report the failure rather than skipping the file silently.
- **FR-020**: The migration MUST NOT make implementation authorization
  reachable without the human approval it requires today.

### Corpus reality (added by adversarial review round 1)

- **FR-023**: This feature MUST NOT newly fail any currently-green spec. 110 of
  139 committed specs carry a status value outside the closed vocabulary; they
  are not rejected today and MUST NOT begin being rejected as a side effect of
  relocating the policy. Corpus-wide enforcement and the back-migration of those
  110 specs are a SEPARATE, later decision, explicitly out of scope here.
- **FR-024**: The authority MUST nonetheless be *capable* of rejecting those
  values, and that capability MUST be unit-tested directly. Capability without
  corpus-wide application is the deliberate end state of this feature: it is
  what makes a later enforcement decision a small, reviewable change rather than
  another migration.
- **FR-025**: Restoring the upstream template reintroduces `**Status**: Draft`
  (capital) as the seeded value for every newly scaffolded spec, because
  `create-new-feature.ps1` copies the template verbatim and rewrites nothing.
  **Resolution (agent recommendation, 2026-08-08): NORMALIZE.** A Seshat-owned
  post-scaffold step rewrites the seeded status line to the canonical `draft`
  once, at spec-creation time. The upstream template is not modified and no
  Seshat content is placed in it.

  Rejected alternative: treating the seeded `Draft` as a recognized synonym.
  That would contradict FR-006 -- capital `Draft` IS outside the closed
  vocabulary -- and would turn FR-006 from one testable rule into a rule plus a
  permanent exception list. Normalization keeps FR-006 unqualified: an authored
  status value outside the vocabulary is always rejected, with no carve-out.

  This is NOT the fork relocated (FR-016/FR-017). The step contains no upstream
  template content, reapplies no patch, and does not need to be re-run after an
  upgrade: it acts on the scaffolded OUTPUT, not on the upstream input. If the
  upstream template later changes its seeded value, the step keeps working
  because it normalizes whatever it finds rather than restoring a known string.

  FORBIDDEN: modifying the template to change what it seeds, and silently
  ignoring the mismatch.
- **FR-025a**: The normalization step MUST be idempotent and MUST fail closed:
  if it cannot parse the scaffolded status line, it reports the defect rather
  than leaving a spec in an unknown state.
- **FR-026**: `.claude/workflows/idea-to-spec.js` is a THIRD ratification
  grammar: it instructs authors to write the legacy capital
  `Ratified (Name, date)` form. It MUST be reconciled with the authority in the
  same change as `implement.js`, or the feature replaces a two-way disagreement
  with a two-way disagreement plus an unreconciled producer.

### Scope discipline

- **FR-021**: Comparison of vendored content against a recorded hash MUST
  normalize line endings before comparing. Raw-byte difference alone is not
  proof of semantic drift: five of six apparent drifts in the current tree are
  CRLF checkout artifacts. This requirement applies to any comparison this
  feature performs; it does NOT authorize building a general drift framework.
- **FR-022**: This feature MUST NOT upgrade Spec Kit, change dependencies,
  change CI configuration, alter git configuration, or normalize repository line
  endings.

## Clarifications

### Session 2026-08-08

- Q: Should the Seshat status block be preserved by machinery that reapplies it
  after upgrades? -> A: **No -- rejected by the owner.** Spec Kit owns Spec Kit;
  Seshat owns Seshat governance. The behavior moves to a Seshat-owned seam and
  the template goes back to upstream. The fork is not relocated (FR-016).
- Q: Does anything actually depend on the template's content? -> A: Exactly one
  consumer: `tests/unit/test_spec_status_vocabulary.py`, which reads the file
  and runs in CI. No shipped code does. Measured, not assumed.
- Q: Is the vocabulary defined anywhere in shipped code today? -> A: No. Its only
  code declaration is a tuple inside that test module, which is why the test is
  currently both the authority and the checker -- the exact self-validation
  problem FR-004 forbids.
- Q: Do the existing ratification grammars agree? -> A: No, and it is
  demonstrable: `implement.js` H3 refuses the merged, correctly-ratified
  `specs/150-dbt-evidence-consumer/spec.md`. Recorded as US3 / FR-010-012.
- Q: Adversarial round 1 -- how much of the corpus does ADR-0019 actually
  govern? -> A: Measured: 110 of 139 specs are outside the vocabulary and
  nothing rejects them; only the 10 `implemented` claims are checked. The
  original US2 ("enforced more strongly") would have turned CI red on 110
  committed specs with no migration task. Split into FR-023 (do not newly fail
  anything) and FR-024 (capability, unit-tested, not applied corpus-wide).
- Q: Adversarial round 1 -- what does the restored template seed? -> A:
  `**Status**: Draft` (capital), copied verbatim by `create-new-feature.ps1`.
  Every newly scaffolded spec would start outside the vocabulary. Now FR-025,
  with two permitted resolutions and the fork explicitly excluded from both.
- Q: Adversarial round 1 -- are there only two grammars? -> A: No, three.
  `idea-to-spec.js` independently instructs the legacy capital form and was
  missing from the dependency table. Now FR-026.
- Q: Adversarial round 1 -- is widening H3 safe? -> A: Not naively. Verified:
  widening the prefix makes `**Status history**: draft` match the draft regex,
  wrongly refusing a ratified spec. Now FR-012a with a pinned test.

## Success Criteria

1. Seshat-specific governance no longer modifies an upstream-managed Spec Kit
   template.
2. ADR-0019's behavior remains enforced, by a Seshat-owned authority.
3. Exactly one Seshat-owned policy authority exists for status semantics.
4. Missing or invalid governance state fails closed.
5. Human approval requirements remain intact and un-self-grantable.
6. The existing SPECKIT / SESHAT-KIT fence behavior is unchanged.
7. Existing readers and validators keep working through the new seam.
8. A normal Spec Kit upgrade no longer requires reapplying a Seshat patch.
9. No equivalent replacement fork is created anywhere.
10. The canonical ratified form is accepted by the H3 gate, and a contract test
    prevents the two grammars from diverging again.
11. The behavior above is protected by tests, not by prose.

## Out of Scope

Full re-vendor automation. A general upstream-provenance registry. The five
`speckit-git-*` skills absent from `claude.manifest.json`. A broad drift
checker. Any Spec Kit version upgrade. Repository-wide CRLF/LF normalization.
Git configuration changes. Phase 9 skill rationalization. Unrelated CodeScene
cleanup. Upstreaming anything to GitHub Spec Kit. Rewriting the historical
ownership audit beyond the minimal factual correction in US4. Implementation of
this spec.

## Assumptions

- The upstream baseline for the template is the content committed by the
  sanctioned installer run in `1eb0c98`, which is available in git history.
- ADR-0019 remains a governing decision; this feature changes where its policy
  is executed, not what it decides.
- `implement.js` may be edited: it is Seshat-owned harness content under
  `.claude/workflows/`, not upstream-managed Spec Kit content.
