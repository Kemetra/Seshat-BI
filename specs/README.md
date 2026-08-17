# specs/ -- reference conventions and known provenance caveats

This directory holds the per-feature spec dirs. Two facts about how they are named
and referenced are load-bearing; read them before you cite a spec by number.

## 1. The full-slug directory name is the canonical reference -- NOT the bare number

Some spec numbers are DUPLICATED across two different directories. A bare "spec NNN"
reference is therefore ambiguous and unreliable. Always cite a spec by its full slug
directory name (e.g. `specs/067-seed-route-honesty-rule`) -- or by the commit SHA / PR
number that shipped it -- never by the bare number alone.

## 2. Duplicate-numbered directory pairs

| Number | Directory A | Directory B |
| --- | --- | --- |
| 044 | `specs/044-kpi-derivation-lineage` | `specs/044-live-surface-protocol` |
| 067 | `specs/067-bi-python-cleaning-artifacts` | `specs/067-seed-route-honesty-rule` |
| 087 | `specs/087-decision-aid-layer` (shipped, PR #185, ratified) | `specs/087-conformed-dimension-readiness` (PR #194, draft) |
| 088 | `specs/088-drill-nav-periods` (shipped, PR #186, ratified) | `specs/088-scd-dimension-history-policy` (PR #194, draft) |

Both members of each pair are real, committed spec dirs about different features. The
bare number does not disambiguate them. For 087/088 the two members also differ in
STATUS: the `decision-aid-layer` / `drill-nav-periods` members are ratified and shipped;
the `conformed-dimension-readiness` / `scd-dimension-history-policy` members arrived as
draft specs in the parallel readiness-gap batch (PR #194) and share the number by
coincidence. Cite by the full slug (never a bare "087"/"088"). Renumbering the draft
members is an owner call, not done here.

## 3. Some shipped rules cite a bare number that matches NO committed spec dir

A bare "spec NNN" tag in a commit message is not a guarantee that a matching spec dir
exists. Confirmed example:

- Rule **AL2** (assumption-coherence) shipped in **PR #129 / commit cc606b8**, whose
  message reads `feat: AL2 cross-contract assumption-coherence rule (067, H2)`. That
  bare "067" matches NEITHER committed 067 dir -- neither `067-bi-python-cleaning-artifacts`
  nor `067-seed-route-honesty-rule` is about assumption-coherence. AL2 was hand-built
  (not spec-driven) and has no committed spec. See the provenance note in the docstring
  of `src/retail/rules/assumption_coherence.py`. This is acknowledged provenance debt.

Takeaway: bare "spec NNN" references cannot be trusted. Always resolve a spec by its
full slug directory or by the commit / PR that shipped it.

## 4. Unchecked `- [ ]` boxes in most tasks.md files are historical, not a backlog

As measured 2026-08-17 by `grep -lE '^- \[ \]' specs/*/tasks.md`, 93 spec dirs contain
at least one unchecked checkbox in their `tasks.md`. The set is those 93 specific
directories -- it is NOT a date or number range, so do not read it as "everything before
spec N". Several dirs interleaved among them (`132-`, `134-`, `135-`, `136-`, `138-`)
have zero unchecked boxes, the highest with a gap happens to be `137-` only incidentally,
and per section 1 the bare numbers here are not reliable references anyway: 8 of the 93
are the duplicate-numbered pairs section 2 warns about (both `044-`, both `067-`, both
`087-`, both `088-`). Re-run the grep rather than trusting a remembered boundary.

Read naively, 93 dirs looks like a large open backlog. It is not: these
are append-only historical records of task lists as they were written, and most of the
described features already shipped. Nobody goes back to tick the boxes once work lands,
so the checkbox state drifts from reality and stays stale indefinitely.

To judge whether one spec's work landed, inspect that spec: `seshat spec-status
<path-to-spec.md>` is the purpose-built surface, and the decisive check is whether the
spec's own named deliverables exist on disk. Do NOT reach for `readiness-status.yaml`
here. `CLAUDE.md` scopes it to a different question -- *"What readiness stage am I
serving? State lives in `readiness-status.yaml` (per TABLE, recomputed)"* -- which is
per-table DATA readiness, and it cannot say whether a tool feature such as a linter or
an adapter shipped. For per-table data work, `seshat next` / `seshat status` remain the
authority.

Verified examples, checked against each spec's own named deliverables rather than
against unrelated CLI surface -- note that 020 lists "any new `retail check` rule,
Python module, or CLI verb" among its NON-goals (`020-readiness-viewer/spec.md:440`), so
a responding `seshat` verb would prove nothing about it either way:

- `specs/020-readiness-viewer/tasks.md` -- 24 unchecked, yet `templates/readiness-view.md`,
  `docs/tools/readiness-viewer.md`, and `.claude/skills/readiness-viewer/SKILL.md` all exist.
- `specs/021-approval-console/tasks.md` -- 27 unchecked, yet `templates/approval-request.md`,
  `templates/approval-decision.md`, `docs/tools/approval-console.md`, and
  `.claude/skills/approval-console/SKILL.md` all exist.
- `specs/022-evidence-pack-generator/tasks.md` -- 27 unchecked, yet
  `templates/evidence-pack-index.md`, `docs/tools/evidence-pack-generator.md`, and
  `.claude/skills/evidence-pack-generator/SKILL.md` all exist.

`specs/139-seshat-studio-foundation/` is the documented exception, not part of this
stale class: its tasks.md ledger was actively curated, every box carries a written
rationale, and it closed 38/38 with named-human approval by Ahmed Shaaban on
2026-08-16. Do not lump `139-` in with the checkbox noise described above, and do not
treat an unticked box elsewhere as evidence of missing work on its own. Ticking those 93
dirs' boxes retroactively is an owner call, not done here.
