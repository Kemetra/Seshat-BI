# Phase 1 Data Model: Publish-pack completeness gate (PP1)

No persistent storage. These are the in-memory entities the static rule operates on.

## Required-section set (the closed, explicit constant)

The explicit, named collection of required sections PP1 enforces, derived from the
GENERIC template. Recommended membership (advisor-resolved; confirmed at ratify):
the template's six required-section-index rows, expressed generically.

| Key | Section label (generic, from template) | Resolution marker form |
|-----|----------------------------------------|------------------------|
| a   | Metric contracts                       | `<path / GAP>`         |
| b   | Readiness scorecard                    | `<path / GAP>`         |
| c   | Reconciliation evidence                | `<path / GAP>`         |
| d   | Known data issues / caveats            | `<path / GAP>`         |
| e   | Data dictionary                        | `<below / GAP>`        |
| f   | Publish approval                       | `<recorded / GAP>`     |

- Expressed as one explicit constant in `publish_pack.py` (mirrors B3's single
  `_LIVE_SURFACE` constant), with generic labels only -- no specific table, column,
  KPI, or PII rule.
- The constant is the single named place the section set lives; widening/narrowing
  it is a one-line edit, confirmed at ratify.

## Incompleteness markers (reused mechanism + the GAP token)

- **Placeholder marker**: the angle-bracket `<...>` form, detected via the REUSED
  `G6` mechanism (`re.compile(r"<[^>]+>")`). A required section whose resolution
  value still matches this form is UNFILLED.
- **GAP marker**: the literal token `GAP` appearing in the STRUCTURED "Resolved?"
  position of the required-section index. Read structurally (the index row's
  resolution cell), never as a free-text substring of narrative prose.
- A required section is COMPLETE iff it is present AND its resolution marker is
  neither a remaining placeholder nor `GAP`.

## Pack-selection predicate

Selects the files PP1 scans from `ctx.tracked_files`:

- INCLUDE: repo-relative POSIX paths matching `mappings/<table>/handoff/bi-handoff-pack.md`.
- EXCLUDE: the generic template `templates/handoff/bi-handoff-pack.md` (not under
  `mappings/`, so excluded by the include filter).
- EXCLUDE: committed test fixtures, via the shared `is_test_path()` predicate
  (`src/retail/core.py`).
- EMPTY: when the include set is empty, the rule returns no Finding (silent pass).

## Registration record

- **id**: working id `PP1` (official id confirmed at the ratify gate, mirroring B3).
- **title**: a short generic description, e.g. "Committed BI handoff pack is
  complete (no unfilled required section)".
- Auto-wired by `@register("PP1", ...)` in `src/retail/rules/publish_pack.py`; the
  registry's `pkgutil` discovery picks it up with no `registry.py` edit.

## Finding (emitted per missing/unfilled section)

Reuses the existing immutable `Finding` value object (`src/retail/core.py`):

| Field    | Value for PP1                                                        |
|----------|----------------------------------------------------------------------|
| rule_id  | `"PP1"` (the working id)                                             |
| severity | `Severity.ERROR` (recommended; confirmed at ratify)                  |
| message  | names the unfilled/missing required section and why it is incomplete |
| locator  | the offending pack path (optionally with the section/row)            |

- Findings are new immutable objects; the rule mutates no shared state and writes no
  file (in particular, never an approval).

## Invariants

- The rule NEVER opens a database/network/Power BI connection and imports no DB
  driver (Principle VIII); stdlib-only (`re`, `pathlib`).
- The rule NEVER reads, validates, or writes the publish sign-off owner/date/
  legitimacy -- only presence-and-non-placeholder of the approval slot (Principle V).
- The rule references no domain-specific schema artifact; fixtures are synthetic
  generic packs (Principle VII).
- The rule adds no readiness stage and moves no stage to pass.
