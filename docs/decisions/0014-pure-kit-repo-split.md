# 0014 -- Pure agent-driven BI kit: repo split (supersedes 076 DEC-1)

- **Date:** 2026-07-03
- **Status:** Accepted (owner directive, 2026-07-03).

## Context

Seshat_BI is being made a PURE, reusable, agent-driven BI TOOL. Spec 076
("extract-pure-kit", ratified 2026-07-02) chose **DEC-1 = "package + archive, NOT a
repo split"**, because at the time a split implied a 302-commit history rewrite and
collided with the in-flight c086 supersession work.

That calculus has changed. The owner created a SEPARATE repo
(`github.com/ahmed-shaaban-94/BI`) as the intended home for examples, analysis, and
experiments. Keeping examples intermixed here risks re-polluting the pure tool the same
way the original C086 training-data layer did -- the exact failure mode 076 was written
to correct. With a dedicated destination now available for that material, the
history-rewrite objection that justified DEC-1 no longer applies to the SPLIT question
itself (no history rewrite is required to route future example/analysis work to the new
repo); it only ever applied to purging the OLD history, which this ADR does not revisit.

## Decision

### 1. Adopt the split -- this supersedes 076 DEC-1

Seshat_BI = the pure tool (`src/seshat/`, `.claude/skills/`, `.seshat/kit-source.yaml`,
the gates, `tests/`). The BI repo (`github.com/ahmed-shaaban-94/BI`) = the
analysis/examples playground -- real client work, exploratory notebooks, one-off
dashboards, and anything that is data/analysis rather than tool. New example or analysis
material goes to the BI repo, not here. This decision REPLACES 076's DEC-1
("package + archive, not a repo split") going forward; it does not reopen 076's
DEC-2/DEC-3/DEC-4, which stand as ratified.

### 2. Keep `retail_store_sales` as the single canonical in-repo worked example

`retail_store_sales` (the public Kaggle dataset) stays as the ONE worked example
`first-hour-compass` / `retail-init` offer by name. It is not moved to the BI repo.
Removing it would reproduce the broken-reference state the C086 removal (PR #144) just
finished cleaning up -- dangling pointers, stale SC1 claims, and an orphaned
worked-example doc. A pure kit still needs one steer-by example that ships with the
tool; the BI repo is for everything BEYOND that one canonical example, not a
replacement for it.

### 3. Keep the anti-leak guardrails; "no client data/schema/instance" is the target, not a literal string match

The "Generic, not C086" guardrails and the C2 gate's client-marker check are the
mechanism that keeps the kit pure going forward, independent of which repo holds what.
They are NOT superseded by this ADR -- they stay active and now also guard against
material drifting back in from the new BI repo (e.g. a copy-paste of a real analysis
into an example). Spec 076's SC-003, as written, is scoped to "zero client/live-data
markers outside the C2 gate regex and generic placeholders" -- it already carves out
those exceptions. The target these guardrails serve was never a naive "zero `c086`
substring anywhere in the tree"; it is "no client data, no client schema, no client
instance" ships in the pure tool. Historical citations under `specs/` remain as an
honest record and are not retroactively scrubbed by this ADR.

### 4. This session closed the residual doc cleanup PR #144 deferred

PR #144 removed the C086 client data layer (mappings, powerbi models, warehouse
migrations, pipelines) and stated the doc-web cleanup was PARTIAL by design, deferring
"~30 dangling refs to the removed `c086-pharmacy.md`" and related stale-fact references.
This session completed that residual cleanup: dangling pointers to the removed
`docs/worked-examples/c086-pharmacy.md` are resolved, stale-fact references to
now-deleted artifacts are corrected, and prose that assumed "two worked examples" is
reframed to the one-example state this ADR ratifies in point 2.

## Consequences

- Adopters of Seshat_BI get the tool, one synthetic/generic worked example
  (`retail_store_sales`), and no client data, schema, or instance -- the pure-kit goal
  076 set out to achieve, now reached via a repo split rather than package + archive.
- The BI repo (`github.com/ahmed-shaaban-94/BI`) becomes the home for real analysis,
  client work, and experiments, keeping that material fully out of the tool's tracked
  tree rather than merely archived-but-adjacent.
- The dated history in `docs/releases/v0.1.md` and other historical release notes is
  left intact as an honest record of how the kit got here; this ADR does not trigger a
  history purge (076 DEC-2's tip-redaction-not-purge posture is unchanged).
- Future example or analysis contributions are routed to the BI repo by default; adding
  a second in-repo worked example to Seshat_BI itself would require its own decision,
  not a default action.
- The C2 gate and the "Generic, not C086" review posture remain permanently active,
  now serving double duty: keeping the pure kit pure, and keeping the BI repo's real
  data from leaking back in through copy-paste.

## Numbering note

ADR numbers 0001-0013 are shipped on disk and are never reused (0012 and 0013 in
particular are unrelated shipped decisions from PRs #29 and #36 -- P2 commit types and
the BI-tool-adapter shortlist -- despite the superficial "0012" collision with this
task's original working title). This ADR takes the next free slot, **0014**.

## References

- `specs/076-extract-pure-kit/spec.md` -- the spec this ADR partially supersedes
  (DEC-1 only; DEC-2/DEC-3/DEC-4 stand).
- PR #144 (`feat: extract pure kit -- remove client c086 data, redact host id`, commit
  `95faaa9`) -- the data-layer removal this ADR's point 4 closes the residual doc
  cleanup for.
- `docs/quality/status-claims.yaml` -- the SC1 manifest locking `first-hour-compass`'s
  single worked-example reference (`retail-store-sales.md`) that point 2 ratifies.
- `docs/worked-examples/retail-store-sales.md` -- the canonical in-repo worked example.
- `docs/decisions/0011-safe-auto-updates.md` -- prior ADR in this numbering sequence and
  the format this ADR mirrors.
