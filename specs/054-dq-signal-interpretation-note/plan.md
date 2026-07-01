# Implementation Plan: DQ-Signal Interpretation Note (-1 unknown-member counts as business caveat)

**Branch**: `054-dq-signal-interpretation-note` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/054-dq-signal-interpretation-note/spec.md`

## Summary

Author ONE new generic authoring template,
`templates/handoff/dq-signal-interpretation.md`, that turns an already-recorded
`-1` unknown-member count (the RC14-default consequence, read by reference from a
table's `data-issues.md`) into an analyst-confirmed
`signal -> affected KPI -> direction-of-distortion -> plain-language caveat`
mapping, which then feeds the Stage-7 Publish Ready handoff pack Known-gaps/caveats
section (`templates/handoff/bi-handoff-pack.md` L59-73). This is a docs/template
artifact ONLY: no executor, no new validator, no rule registration, no live query,
no new number. The template is the interpretive SOURCE feeding the shipped Stage-7
Known-gaps requirement; `data-issues.md` remains the single source of truth for the
count. The KPI + direction cells and any PII publish-safety are Principle-V
analyst/governance fill-ins the template presents but never auto-decides. It mirrors
the "generic, composes-never-invents, no-fake-confidence, C086-by-reference-only"
discipline of the existing handoff templates (`bi-handoff-pack.md`,
`reconciliation-report.md`, `data-issues.md`).

## Technical Context

**Language/Version**: N/A -- this feature adds NO code. It authors one Markdown
template file plus wiring cross-references in existing docs. No Python, no module,
no test suite change.

**Primary Dependencies**: None. No runtime, no test dependency, no new package. The
template composes text that already exists in `data-issues.md` (upstream count) and
feeds `bi-handoff-pack.md` (downstream caveat). It leans on NO deferred capability
(F016 Power BI execution adapter verified absent; not referenced as a live
consumer).

**Storage**: N/A. The template is a committed, hand-filled Markdown document. It
opens no database, holds no connection, imports no DB driver, and runs no query.
The `-1` count is transcribed by reference from `data-issues.md`; nothing is
measured here.

**Testing**: N/A for automated tests -- there is no code to test. Verification is by
inspection against the spec Success Criteria (SC-001..SC-005): the template is
generic (no C086/pharmacy specifics), carries no number of its own, presents KPI +
direction as unfilled owner-gated prompts, records "none recorded" when there is no
signal, and does not duplicate the count. A grep for pharmacy/C086 tokens
(`salesperson`, `ezaby`, `71`, a fixed measure list) over the new template must
return zero hits.

**Target Platform**: Documentation in the repo tree (Windows-first per `CLAUDE.md`;
keep the path short -- `templates/handoff/dq-signal-interpretation.md` is within
MAX_PATH).

**Project Type**: Docs/templates only (no runtime code path added). Same family as
the existing `templates/handoff/` bundle.

**Performance Goals**: N/A (a static document).

**Constraints**: ASCII / UTF-8 without BOM; use `--` and `->`, no glyphs (rule IX).
Generic-only -- zero pharmacy/C086 specifics (rule 7); C086 cited by reference to
`docs/worked-examples/c086-pharmacy.md` + `docs/c086-adr0002-compliance.md`. No
fabricated confidence / readiness score (rule 9). No executor, no validator, no rule
id. Never self-grant a readiness pass. Introduces no new number (reads
`data-issues.md`).

## Constitution Check

- **Principle V (Agent Stops at Judgment Calls)**: SATISFIED by construction. The
  `signal -> KPI -> direction` mapping and the PII publish-safety decision are
  presented as unfilled, owner-named fill-ins; the template auto-decides none of
  them. The two load-bearing rulings (direction-of-distortion correctness claim;
  stage-of-record/roadmap ownership) are left OPEN in spec ## Clarifications for a
  human, not answered by this plan.
- **Principle VI (Defaults Then Deviations)**: SATISFIED. The template interprets an
  accepted RC14 default (`-1` unknown member + FK COALESCE, constitution L324-340);
  it cites the default, does not re-litigate it, and invents no new number.
- **Scope discipline / YAGNI (CLAUDE.md)**: SATISFIED. Adds the seam (a template),
  not the implementation -- no executor, no validator, no live query.
- **Anti-fabricated-confidence (bank invariant)**: SATISFIED. Reads a recorded
  count; for a table with no recorded signal the note has no content (FR-004).
- **Generic-not-C086 (CLAUDE.md + template-header discipline)**: SATISFIED. Zero
  domain specifics; C086 is a linked filled instance only.

## Phase 0: Research

See [research.md](./research.md). Key resolved decisions:

1. **Where the `-1` count lives** -- CORRECTED premise: NOT emitted by
   `validate.py` / `run_live_checks` (those tally hard orphan FKs at Severity.ERROR
   and reconciliation gaps only; rows COALESCE'd to `-1` pass silently). The count's
   real home is a hand-filled `warning` row in `data-issues.md` (L12/L28-30). The
   template therefore READS `data-issues.md`, never assumes a tooling-emitted tally.
2. **Integration surface** -- CORRECTED premise: the caveat/stakeholder surface is
   Stage 7 Publish Ready (`bi-handoff-pack.md` Known-gaps L59-73 / `publish-ready.md`
   L30,L57), NOT "Stage 4 GOLD" as the idea's synthesis said. The count is PRODUCED
   at Stage 4 (Gold Ready live validate) and CONSUMED at Stage 7. The template is the
   interpretive SOURCE feeding the shipped Stage-7 section, not a replacement for it.
3. **Non-duplication** -- the `signal -> affected KPI -> direction-of-distortion`
   mapping exists nowhere today (confirmed by grounding grep); `data-issues.md` stops
   at count+disposition, `bi-handoff-pack.md` surfaces the count but not the KPI /
   direction. This is the genuinely-new layer.
4. **Template shape** -- mirror the header discipline of `reconciliation-report.md`
   and `bi-handoff-pack.md`: a GENERIC banner (copy per table; C086 by reference
   only; ASCII; no fake confidence), a structured per-signal table with owner-gated
   fill-in cells, an explicit "none recorded" path, and a "See also" cross-reference
   block. No new mechanism is invented.

## Phase 1: Design & Contracts

No code contracts (no code). The single artifact contract is the template's own
structure, specified in [contracts/template-contract.md](./contracts/template-contract.md):

- **Header banner**: GENERIC discipline (copy per table to `mappings/<table>/handoff/`;
  C086 cited by reference; ASCII/UTF-8 no BOM; no numeric confidence score; the count
  is sourced from `data-issues.md`, never re-measured here).
- **Per-signal interpretation table**: one row per recorded `-1` signal, columns:
  `dim (from data-issues.md)`, `count (by reference)`, `affected KPI (analyst fill-in)`,
  `direction: understate / overstate / none (analyst fill-in)`, `plain-language caveat`,
  `owner (named)`, `PII review (governance, if person/customer dim)`.
- **"None recorded" path**: an explicit statement + zero caveats when no `-1` signal
  is recorded (FR-004).
- **Feeds-not-duplicates note**: states that the confirmed caveat is carried verbatim
  into the Stage-7 pack Known-gaps section and that `data-issues.md` is the single
  source of truth for the number.
- **See also**: links to `data-issues.md`, `bi-handoff-pack.md`, `publish-ready.md`,
  `gold-ready.md`, the constitution (Principle V / VI, RC14), and C086 as a filled
  instance.

## Progress Tracking

- [x] Phase 0 research complete (premise corrections captured)
- [x] Phase 1 design/contract captured
- [ ] Tasks generated (see tasks.md)

## Complexity Tracking

No constitutional deviations. No new dependency, no executor, no rule, no code path.
Single new documentation file + cross-reference wiring in existing docs.
