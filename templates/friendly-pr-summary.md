<!--
=============================================================================
 friendly-pr-summary.md  --  the GENERIC rendered shape of the Friendly PR
 Reviewer's plain-language summary / sticky comment (spec 130).
=============================================================================
 GENERIC template -- the stable OUTPUT SHAPE `seshat.pr_summary.render_summary`
 (+ `compose_comment`) produces for ONE pull request. See
 `docs/tools/friendly-pr-reviewer.md` (when to run, field meanings, the F025
 boundary) and `.claude/skills/friendly-pr-reviewer/SKILL.md` (the procedure).

 NARRATIVE, NOT A VERDICT. This is a plain-language presentation over the
 already-shipped `retail check --format review` envelope + readiness truth. It
 renders NO `merge_ready` boolean (that stays F025 pr-readiness-reviewer's
 surface) and NO numeric score/percentage/tally anywhere (hard rule #9). Every
 line traces to a field of the review envelope, the readiness truth, or a
 fingerprint -- a line with no traceable source is a defect.

 RENDERED, sticky comment when opted in. A filled copy MAY be posted as one
 sticky PR comment (update-in-place by a stable marker) only when the
 repository has opted in via the additive CI step; otherwise it is rendered
 ephemerally to the operator. Either way it writes no repo-tracked file.

 GENERIC, not an instance. Placeholders only; `retail_store_sales` is a filled
 instance CITED as a reference (docs/worked-examples/), never inlined
 (Principle VII). ASCII only, UTF-8 no BOM; `--` and `->` only.
=============================================================================
-->

<!-- seshat:friendly-pr-summary:v1 -->

# Friendly PR Summary

(as of `<YYYY-MM-DDTHH:MM:SSZ>` -- an explicit argument, never the wall clock)

This is a plain-language NARRATIVE over already-shipped review results, not a
merge-safety verdict (see F025 pr-readiness-reviewer for that). It renders no
merge-ready boolean and no score.

Overall: this change is currently `<BLOCKED | NOT blocked | outcome reported as
'<outcome>' (verbatim from the review envelope)>`.

## What changed

- This change touches the following readiness stage(s): `<stage_1, stage_2, ...>`.
  *(or: "No readiness stage was identified as affected by this change.")*
- `<N>` file(s) changed.
- The change includes an update to readiness-status.yaml for: `<path, ...>`.
  *(present only when `changed_readiness_state` is non-empty)*
- *(when there are no findings at all)* This change introduced no governance findings.

## Readiness stage status

- `<stage>`: `<status verbatim: not_started | blocked | warning | pass | unknown>`
  (source: `<readiness-status.yaml | readiness-status.yaml: absent | readiness-status.yaml: stage entry absent>`)
- ...

## Findings

*(with a base fingerprint set supplied -- US2)*

### NEW in this PR
- `[<rule_id>] <masked message> -- <locator, in words>`
- ... *(capped at a stable, documented count; a truncation always states how many were omitted)*

### RESOLVED by this PR
- a finding present at the base branch (fingerprint `<prefix>...`) is no longer
  present at head -- RESOLVED by this PR
- ...

### Pre-existing / carried over
- `[<rule_id>] <masked message> -- <locator, in words>`
- ...

*(without a base fingerprint set -- the honest fallback, US1)*

new-vs-pre-existing could not be determined (no base fingerprint set was
supplied); findings are listed as 'present':
- `[<rule_id>] <masked message> -- <locator, in words>`
- ...

## Worth a look (not blocking)

- `[<rule_id>] <masked message> -- <locator, in words>` *(WARNING-severity findings only)*
- ... *(or: "- none")*

## Required approval authority

- `<stage>`: route to `<next_surface>` (category: `<approval | grain | live_validation | artifact | readiness>`)`<
   -- approvals[] names <masked owner> on record, but the stage is still blocked (a
   fresh named human approval is required) | -- no owner is recorded yet in
   approvals[]; a named human must approve (this summary cannot self-grant it)>`
- ... *(or: "- no blocked stage requires naming an authority here")*

## Next action (exactly one)

- `<the single next action selected by the refutation-first rank, or "no next
  action was produced by the review">`

## Conflicts (surfaced, not resolved)

*(present only when two consumed sources disagree, e.g. readiness reports a
stage `pass` while the review envelope reports it blocked -- never resolved
here; a human judgment call)*

- conflict: readiness-status.yaml reports stage '`<stage>`' as 'pass', but the
  review envelope outcome is 'blocked' with findings affecting it -- surfaced,
  not resolved (a human judgment call)

## Could not determine

*(present only when a required input was missing or unreadable -- each line
names the missing source; never silently assumed `pass`, never a fabricated
blocker)*

- `<e.g. "review envelope: absent or could not be produced ...">`
- `<e.g. "next action: no next action was produced by the review">`
- `<e.g. "new-vs-pre-existing distinction: could not be determined -- no base
  fingerprint set was supplied; ...">`
