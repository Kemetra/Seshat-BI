# Adversarial plan review: Spec Kit template fork removal

**Posture**: default-refuted. Run as an independent pass against the drafted
design, per the mission's §11. Every finding below was re-verified directly
before being accepted -- the agent's report was not taken at face value.

The twelve §11 questions are answered at the end; the confirmed problems come
first.

## CONFIRMED PROBLEM 1 -- the migration's proof gate was vacuous

The draft's T008 read: "every value the old test rejected is still rejected."

`tests/unit/test_spec_status_vocabulary.py` only iterates
`_specs_claiming_implemented()`, filtered by the exact `_IMPLEMENTED` regex.
Measured over the real corpus:

```
total specs: 139 | matched by _IMPLEMENTED regex: 10
    40  OUTSIDE: Draft
    40  OUTSIDE: Ratified
    20  canonical-lowercase
    11  OUTSIDE: Implemented
     9  NO STATUS LINE
     4  OUTSIDE: Shipped
     4  OUTSIDE: **BUILT**
     3  OUTSIDE: **BUILT.**
     ...
specs OUTSIDE the vocabulary: 110
```

The old test rejects essentially nothing at spec level, so the gate was
trivially satisfiable while proving nothing. This is a verifier that does not
sit on the risk.

**Resolution**: T008 rewritten with three concrete sub-gates, including direct
unit rejection of each real out-of-vocabulary value found in the corpus, and an
explicit "count of specs failing CI is UNCHANGED at 0".

## CONFIRMED PROBLEM 2 -- US2 would have turned CI red on 110 committed specs

The draft's US2 was titled "ADR-0019 is enforced more strongly than before" and
its acceptance scenarios implied corpus-wide validation. With 110 of 139 specs
outside the vocabulary, satisfying that story literally means failing 110
committed specs -- and `tasks.md` had no back-migration step.

ADR-0019 itself only ever required the `implemented` specs to migrate; the
vocabulary was closed in principle and enforced for ~7% of the corpus.

**Resolution**: the story is re-scoped and renamed to "Every guarantee that
exists today still exists after", with the measured table published in the spec.
Split into FR-023 (this feature must not newly fail anything) and FR-024 (the
authority must be *capable* of rejecting those values, unit-tested, without a
consumer applying it corpus-wide). Corpus-wide enforcement becomes an explicit
later decision rather than an accident of relocation.

## CONFIRMED PROBLEM 3 -- the restored template seeds an invalid status

`create-new-feature.ps1:353` copies the template verbatim and rewrites nothing.
After restoration the seeded line is upstream's `**Status**: Draft` -- capital
D, outside the closed vocabulary. Every newly scaffolded spec would begin life
in a state the policy calls invalid, with no consumer saying so.

The draft asserted detection in a US2 acceptance scenario but no task
implemented it, and the obvious fix (make the template seed lowercase) is
precisely the fork being removed.

**Resolution**: FR-025 requires an explicit recorded choice between two
permitted resolutions -- accept the upstream seeded value as a pre-ratification
synonym, or normalize post-scaffold from a Seshat-owned step -- and forbids both
editing the template and silently ignoring the mismatch. Task T008-scaffold
requires proving it by actually scaffolding a spec.

## CONFIRMED PROBLEM 4 -- there are three grammars, not two

The draft's dependency table named `implement.js` as the H3 consumer.
`.claude/workflows/idea-to-spec.js` (lines ~341, ~403, ~423) independently
instructs authors to write the legacy capital `Ratified (Name, date)` form. It
is the *producer* of ratification instructions and was absent from the table.

Reconciling only `implement.js` would replace a two-way disagreement with a
two-way agreement plus an unreconciled producer -- authors would still be told
to write the wrong form.

**Resolution**: FR-026 and task T008d.

## CONFIRMED PROBLEM 5 -- the obvious H3 widening breaks ratified specs

The plan's Option A ("widen additively") has a specific wrong implementation.
Verified by execution:

```
line              : "**Status history**: draft"
current H3_DRAFT  : false   (correct: ignores history)
naive widened     : true    (WRONG: would refuse a ratified spec)
```

Widening the prefix from `\*\*Status\*\*` to `\*\*Status[^*]*\*\*` makes the
draft regex match the ADR-mandated `**Status history**:` line, which would
refuse a correctly ratified spec -- including `specs/150-dbt-evidence-consumer`,
which carries exactly that line.

**Resolution**: FR-012a and task T008a-history, pinning the case before any
regex changes.

## REFUTED -- claims that survived attack

- **"The design merely moves the fork"** (§11 Q6). Refuted. A Python module
  owning a vocabulary is not a copy of upstream's template body: it contains no
  upstream content, is not overwritten by an upgrade, and needs no reapplication.
  FR-016/FR-017 forbid the relocations that would make this true, and T015
  checks the diff for them.
- **"The design creates a second state machine"** (§11 Q7). Refuted.
  `data-model.md` explicitly disclaims transitions, approval logic, and history
  tracking; the authority validates a line against a vocabulary.
- **"The checker validates itself from the same untrusted source"** (§11 Q9).
  Refuted, and inverted deliberately: today the test derives policy FROM the
  template it validates. After migration the authority is the source and the
  template is only asserted to be clean. FR-004 forbids the old direction.
- **"Other templates are disturbed"**. Refuted. Only `create-new-feature.ps1`,
  `setup-plan.ps1`, `setup-tasks.ps1` touch templates; none of the other four
  carries Seshat content.
- **"Supposed drift is only LF/CRLF noise"** (§11 Q10). Partly TRUE and already
  recorded: five of six manifest drifts are CRLF artifacts, one is the real
  fork. FR-021 requires normalization before comparison; the general drift
  framework stays out of scope.

## The §11 questions, answered

1. **Can the template be restored while an ADR-0019 guarantee silently
   disappears?** Yes, as originally drafted -- see problems 1 and 3. Fixed by
   FR-023/FR-024/FR-025 and the rewritten T008.
2. **Can a newly generated spec bypass status governance?** Yes, as drafted --
   problem 3. Fixed by FR-025 + T008-scaffold.
3. **Can `Draft`/`draft` cause two authorities to disagree?** They already do,
   in three places. FR-010/FR-012a/FR-026.
4. **Can code and docs drift into different vocabularies?** Prevented by
   FR-001/FR-002 (one importable authority) and FR-011 (divergence contract
   test).
5. **Can implementation become authorized without human approval?** No. H3's
   git-blame provenance check is untouched; FR-012 forbids loosening it and
   FR-020 forbids making authorization reachable.
6. **Does it move the fork?** No -- refuted above.
7. **Second state machine?** No -- refuted above.
8. **Would a normal upgrade still require a manual patch?** No, once FR-013
   lands: the template holds no Seshat content, so an upgrade overwrites nothing
   of ours.
9. **Self-validating checker?** No -- FR-004, direction inverted.
10. **Is the drift only line-ending noise?** Five of six yes, one no. FR-021.

## Verdict

The design is **implementable as revised**, contingent on human ratification.
As originally drafted it was not: it would have shipped a vacuous proof gate, a
story that reddens CI on 110 committed specs, a scaffold path that produces
invalid specs by construction, an unreconciled third grammar, and a regex
widening that refuses correctly ratified specs.

Five confirmed problems, all found by an independent pass, none by self-review.
