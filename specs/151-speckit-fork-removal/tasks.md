# Tasks: Remove the Spec Kit template fork and externalize Seshat status governance

**Status**: draft; NOT ratified. No task below may begin until a named human
records ratification in `spec.md`.

Order is load-bearing. The template is restored at T009 -- after the replacement
authority exists, is proven, and every consumer is migrated. Restoring it
earlier is the failure mode this ordering exists to prevent.

## Phase 1 -- establish the baseline

- [ ] T001 Re-verify the dependency table in `spec.md` against the tree at
      implementation time. If a new consumer of the template has appeared, stop
      and amend the spec before continuing.
- [ ] T002 Baseline the governance suites and record results, so any later
      failure is classified against a known-good baseline rather than guessed at:
      `pytest tests/unit/test_spec_status_vocabulary.py`, `tests/unit/test_fence.py`,
      and the SC1 rule tests.

## Phase 2 -- build the authority (TDD)

- [ ] T003 Write failing tests for the authority: each of the four values is
      accepted in canonical form; a value outside the vocabulary is rejected; a
      correct value in the wrong case is rejected and the canonical form is
      named.
- [ ] T004 Write failing fail-closed tests: absent `**Status**:` line,
      unparseable line, and unreadable file each produce a named defect and
      never a pass (FR-018, FR-019).
- [ ] T005 Write the failing anti-circularity test: the authority must not read
      `.specify/templates/spec-template.md`. Assert the module neither imports
      nor opens that path, so it cannot derive its expectation from the artifact
      it validates (FR-004).
- [ ] T006 Implement the authority in `src/seshat/`: vocabulary, canonical case,
      line grammar, per-value evidence requirement. No state machine, no
      approval logic, no readiness import (FR-003).

## Phase 3 -- migrate consumers

- [ ] T007 Migrate `tests/unit/test_spec_status_vocabulary.py` to import the
      authority. Delete its local `VOCABULARY` tuple. It may still read the
      template to assert the template is CLEAN, but must no longer read it to
      learn what the policy IS.
- [ ] T008 Prove equivalent governance before touching the template. NOTE: the
      naive form of this gate is VACUOUS -- the old test inspects only the ~10
      specs matching `_IMPLEMENTED`, so "every value it rejected is still
      rejected" is trivially true over an almost-empty set. The real gate is:
      (a) the SC1 `implemented` requirement still fires; (b) the authority
      rejects, in direct unit tests, each of the real out-of-vocabulary values
      found in the corpus -- `Draft`, `Ratified`, `Implemented`, `Shipped`,
      `**BUILT**`, `Finalized`, `Planned`, absent line (FR-024); and (c) the
      count of specs failing CI is UNCHANGED at 0 (FR-023).
- [ ] T008a-pre Record the corpus census as a committed fixture or test
      constant, so a later corpus-wide enforcement decision starts from measured
      numbers rather than re-derivation: 139 specs, 20 canonical, 110 outside,
      9 with no status line, 10 matching `_IMPLEMENTED`.
- [ ] T008-scaffold Implement the FR-025 resolution: a Seshat-owned
      post-scaffold normalization step that rewrites the seeded status line to
      canonical `draft`. It must be idempotent, must fail closed on an
      unparseable line (FR-025a), and must normalize whatever it finds rather
      than restoring a known string. Test end to end by actually scaffolding a
      spec from the restored upstream template. Do NOT resolve this by editing
      the template, and do NOT add a `Draft` exception to the authority --
      FR-006 carries no exception list.

## Phase 4 -- reconcile the two grammars

- [ ] T008a Write the failing reconciliation test FIRST: the canonical ratified
      form is accepted by `implement.js`'s H3 grammar, and the real merged line
      from `specs/150-dbt-evidence-consumer/spec.md`
      (`**Status**: ratified -- Ahmed Shaaban, 2026-08-08`) is accepted. It is
      refused today; that refusal is the red state.
- [ ] T008a-history Write the failing history-line regression test FIRST
      (FR-012a): `**Status history**: draft` must NOT match the draft grammar.
      Verified today: the current regex correctly ignores it, but the naive
      widening `\*\*Status[^*]*\*\*` matches it and would refuse a correctly
      ratified spec. Pin this before changing any regex.
- [ ] T008b Reconcile the H3 grammar (plan §"reconciliation", option A bias:
      widen additively). Must keep requiring a name and a date, must stay
      fail-closed, must not accept an undated or unnamed ratification (FR-012),
      and must not match a history line (FR-012a).
- [ ] T008d Reconcile `.claude/workflows/idea-to-spec.js`, the THIRD grammar
      (FR-026): it instructs authors to write the legacy capital
      `Ratified (Name, date)` form. Its instruction text and the authority must
      agree, and it must remain structurally forbidden from emitting a ratified
      status itself.
- [ ] T008c Add the divergence contract test: if the authority's grammar and the
      H3 grammar stop agreeing, the test fails (FR-011). Assert against the real
      H3 regex, not a copy of it.

## Phase 5 -- restore the template (only now)

- [ ] T009 Restore `.specify/templates/spec-template.md` to its `1eb0c98`
      upstream baseline. Net effect: the Seshat block is deleted and the seeded
      value returns to upstream's. `git diff 1eb0c98 -- <path>` must be empty.
- [ ] T010 Prove nothing was lost: with the template clean, the governance suite
      is green AND an invalid status is still rejected. This is the test that
      distinguishes a real migration from a deletion.
- [ ] T011 Reconcile the `speckit.manifest.json` entry for the template using
      LF-normalized comparison (FR-021). Do not touch the five entries whose
      apparent drift is a CRLF artifact.

## Phase 6 -- documentation and gates

- [ ] T012 Correct `docs/capabilities/ownership-audit.md` lines 217-218 only:
      record that a local template modification existed after the audit, that
      the architecture chosen is removal rather than institutionalization, and
      that spec 151 tracks it. Do NOT edit line 178, whose narrower
      `claude.manifest.json` claim is still true. Do not rewrite the history.
- [ ] T013 Add a pointer in ADR-0019 noting the policy's executable home; the
      decision itself is unchanged and is NOT superseded.
- [ ] T014 Run the repository gates and report each with command, exit code, and
      classification: `pytest -m unit`, `python -m seshat.cli check`,
      `python scripts/export_agent_bundles.py --check`, `ruff format --check`,
      `ruff check`.
- [ ] T015 Review the full diff file-by-file; every changed file must have a
      stated reason. Confirm no new file contains a copy of upstream template
      content (FR-016/FR-017), and confirm `src/seshat/fence.py`, SC1, and the
      SPECKIT fence are absent from the diff.

Marking a task complete requires the verified deliverable in hand. Do not sweep
checkboxes.

Explicitly excluded: Spec Kit upgrade, re-vendor automation, a general
provenance registry, the five `speckit-git-*` skills, a broad drift checker,
repository-wide line-ending normalization, git configuration changes, CI
changes, dependency changes, Phase 9+, upstreaming to GitHub Spec Kit, and any
push, PR, merge, or publication.
