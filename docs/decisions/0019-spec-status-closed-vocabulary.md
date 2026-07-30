# 0019 -- spec `**Status**:` uses a closed four-value vocabulary, and `implemented` must name its artifact

- **Date:** 2026-07-30
- **Status:** Accepted
- **Ratified by:** Ahmed Shaaban (owner), 2026-07-30 -- vocabulary shape chosen from
  three options put to the owner (four values evidence-gated / five values with a
  planning state / two values only).
- **Context:** `specs/` holds 127 spec directories whose `**Status**:` lines do not track
  reality, in **both** directions. `specs/131-portfolio-watch` read "Ratified" while
  shipping `src/seshat/portfolio_watch.py` plus tests; `specs/118-cvd-simulation-evidence`
  read "Draft" and was genuinely unbuilt; `specs/104-rename-impact-refactor-guard` read
  "Draft" while `src/seshat/rules/rename_impact_guard.py` was already on `main` -- a spec
  about stale references that was itself stale.

  Three facts established that this was unguarded rather than intentionally loose. Nothing
  read the directory at all: greps across `src/seshat/rules/`, `tests/`, and `scripts/`
  returned only docstring provenance comments. No closed vocabulary existed --
  `.specify/templates/spec-template.md` seeds `**Status**: Draft` with no enum, and values
  in the wild included `Draft`, `Approved for planning`, `Ratified (...)`,
  `Implemented (commit ...)`, `BUILT (docs-only) ...`, `Shipped (...)`, `Planned (spec
  only...)`, and `Finalized -- ...`. And no spec carried a structured field naming its
  implementing artifact; commit shas appeared inline inside free-text status values.

  The cost is concrete: establishing whether any feature was already built required a
  per-feature tree-verification pass, because the status lines could not be trusted. That
  pass is what discovered `AP1` missing from the governance fix table (ADR-adjacent, see
  `docs/rules/rule-fixes.yaml`) and that spec 118 was a fully clarified, unbuilt design.

## Decision

### 1. Four values, and only four

```
draft | ratified | implemented | superseded
```

| Value | Means | Evidence required |
|---|---|---|
| `draft` | authored, not yet ratified by a named human | none |
| `ratified` | a named human approved the spec itself | the ratifier's name and date |
| `implemented` | the described capability exists on `main` | **an artifact path that is tracked** |
| `superseded` | replaced by another spec | the superseding spec id |

`ratified` records approval of the **spec**, not of an implementation -- conflating the
two is what produced the "Ratified but actually shipped" class. A spec passes through
`ratified` on its way to `implemented`; it does not stay there once code lands.

### 2. `implemented` must name a tracked artifact, in the Status line itself

```
**Status**: implemented -- artifact `src/seshat/rules/rule_ap1.py`
```

This is the only value that is mechanically checkable, and it is the dangerous direction:
an over-claim ("implemented", artifact absent) causes work to be skipped as already-done.
An **under**-claim ("ratified" for something that shipped) is *not* mechanically detectable
without inferring implementation status, which would be a fabricated verdict about human
intent. Under-claims are prevented going forward -- a spec gains its artifact pointer when
it is implemented -- and corrected historically only by a human reading one spec at a time.

### 3. Enforcement reuses the shipped `SC1` mechanism -- no new rule

Rule `SC1` (`src/seshat/rules/status_claims.py`, spec 050) already reconciles a
human-curated manifest, `docs/quality/status-claims.yaml`, against tracked-file evidence.
A spec claiming `implemented` is exactly that shape: the spec is the claiming `doc`, its
Status line is the `anchor`, and its module or test is the `claimed-artifact`. Each
migrated spec gets one `spec-<NNN>-implemented` claim.

No new `seshat check` rule is added. The governance lane is saturated, and a newly wired
rule must be no-finding on `main` before it can land -- which a 127-spec migration is not.

### 4. Previous wording is preserved, never destroyed

Migrating a spec moves its former Status text verbatim into a sibling field:

```
**Status**: implemented -- artifact `src/seshat/rules/rule_ap1.py`

**Status history**: Ratified (Ahmed Shaaban, 2026-07-04) -- C1=align-first, id=AP1, same-PR landing
```

Seven of the nine specs in the first batch recorded a real named-human ratification event
with a date. Introducing a vocabulary must not delete that: the ratification is evidence,
and `Status history` keeps it byte-for-byte.

### 5. Migration is incremental, and the batch is bounded by evidence

The first batch is **nine** specs whose implementing artifact was verified present by
direct inspection. The remaining specs migrate as they are next touched. A big-bang rewrite
of 127 status lines would require asserting an implementation status for each one, and for
most of them that assertion is a human reading, not an observation.

## Consequences

- A spec can no longer claim `implemented` after its artifact is renamed or deleted: `SC1`
  fails closed, naming the claim id. Verified by deliberately breaking one claim's path and
  confirming the ERROR fires, then restoring byte-identically.
- The `anchor` embeds the artifact path, so `anchor` and `claimed-artifact` are coupled and
  must agree -- editing one without the other is itself caught.
- `.specify/templates/spec-template.md` now names the allowed values, so a new spec starts
  inside the vocabulary rather than inventing an eighth variant.
- Unmigrated specs remain free text. That is visible and bounded rather than silently
  trusted, and it is the honest state: nobody has read them yet.
