# Phase 0 Research: Publish-pack completeness gate (PP1)

All findings grounded against the live repo (read-only). No open technical unknowns
remain; the two contract questions have advisor recommendations (spec ## Clarifications)
and the two Principle-V items are recorded for the human ratify gate.

## 1. The reusable placeholder mechanism (Principle II -- Depend, Never Fork)

`src/retail/rules/g6.py` defines:

```python
_PLACEHOLDER_RE = re.compile(r"<[^>]+>")
```

G6 treats a value CONTAINING a `<...>` token as the safe PLACEHOLDER form and flags
a value with NO `<...>` token (a real leaked value). PP1 needs the SAME detection
with INVERTED polarity: in a committed handoff pack a required-section value that
STILL matches the `<...>` placeholder form is UNFILLED, and is exactly what PP1
flags.

**Decision**: reuse the one-line placeholder regex rather than authoring a second
placeholder parser. Two seam options:

- (A) `from .g6 import _PLACEHOLDER_RE` and reuse the compiled pattern directly.
- (B) lift the single pattern into a tiny shared helper (e.g. `rules/_placeholder.py`
  exposing `PLACEHOLDER_RE` / `is_placeholder(text)`) that both `g6.py` and
  `publish_pack.py` import.

**Chosen (recommended)**: (B) -- a tiny shared helper. Rationale: importing a
sibling rule module's NAME-MANGLED private (`_PLACEHOLDER_RE`) couples PP1 to G6's
internals; a shared helper makes the "one placeholder definition, two rules" intent
explicit and is the cleaner expression of Principle II (mirrors how `B3` imports
B1's PUBLIC `module_scope_violations` helper, not a private). (A) is acceptable and
strictly smaller if the human prefers minimal churn; either way NO second regex is
authored. This is a build-time refactor decision, recorded here, with G6's behavior
unchanged (the pattern is identical). **Rejected**: re-deriving a new placeholder
regex in `publish_pack.py` (forks the parser -- violates Principle II).

## 2. Required-section set derivation from the generic template

`templates/handoff/bi-handoff-pack.md` carries a "Required-section index" table
(lines ~43-52) with six rows, each pointing at an existing committed artifact and a
structured "Resolved?" cell:

| # | Section | Resolved? marker |
|---|---------|------------------|
| a | Metric contracts | `<path / GAP>` |
| b | Readiness scorecard | `<path / GAP>` |
| c | Reconciliation evidence | `<path / GAP>` |
| d | Known data issues / caveats | `<path / GAP>` |
| e | Data dictionary | `<below / GAP>` |
| f | Publish approval | `<recorded / GAP>` |

The template states (lines ~54-57): "A section that points at an UNFILLED or FAIL
artifact ... is a GAP -> the pack cannot reach 'complete'". This is the authoritative
generic source of PP1's "incomplete" definition.

**Recommended required-section set** (advisor-resolved; confirmed at ratify): the
six index rows a-f, checked at INDEX granularity -- for each row, (i) the section is
present and (ii) its structured "Resolved?" cell is FILLED (not a remaining
`<placeholder>`, not the literal `GAP`). The four MANDATORY caveats (PII / returns /
known-gaps / out-of-scope) are NOT decomposed individually in this first step;
per-caveat enforcement is a later, separate increment (YAGNI).

**GAP/placeholder location**: the marker is read from the STRUCTURED "Resolved?"
position of the required-section index, NEVER by a free-text substring scan, so the
word "gap" in a caveat sentence cannot trip the rule. The exact parse anchor (the
index table rows vs the section headings) is fixed in data-model.md.

**Genericity**: PP1 keys only off the template's section labels and the
placeholder/GAP convention -- never off any specific table's columns, caveat
wording, billing codes, segments, or PII (Principle VII).

## 3. File-location + exemption pattern

`G6` enumerates `ctx.tracked_files` and selects by suffix
(`.SemanticModel/definition/expressions.tmdl`), skipping `is_test_path(p)` (paths
under `tests/`). PP1 mirrors this:

- SELECT: tracked files matching `mappings/*/handoff/bi-handoff-pack.md` (per-table
  instances). One exists today:
  `mappings/retail_store_sales/handoff/bi-handoff-pack.md` (filled, 7021 bytes).
- EXCLUDE: `templates/handoff/bi-handoff-pack.md` (the generic template -- it is
  deliberately full of `<placeholder>` tokens by design; scanning it would guarantee
  a false-positive flood). The `mappings/*/handoff/` path filter already excludes it
  (it lives under `templates/`).
- EXCLUDE: `tests/` fixtures via `is_test_path()` (synthetic fixtures deliberately
  carry unfilled sections to exercise PP1).
- EMPTY TREE: if no instance packs exist, PP1 produces no Finding (silent pass --
  consistent with G6 scanning only files that exist).

## 4. Registration / wiring contract

- `tests/unit/test_rules_wiring.py` holds `EXPECTED_RULE_IDS` (a frozenset; current
  members include S/D/R/A1/A3/B1/B3/C/G1-G6/P1/P2). The snapshot count keys off
  `len(EXPECTED_RULE_IDS)`, never a literal -- so adding the new id + the rule in the
  same change keeps the drift test green. The idea-backlog's recurring 33/34 baseline
  is STALE; the live set is the source of truth.
- A new `src/retail/rules/publish_pack.py` decorated with `@register(...)` auto-wires
  with NO `registry.py` edit -- the wiring test re-registers every `rules` submodule
  via `pkgutil.iter_modules`, so the new module is discovered automatically.
- `docs/rules/rules-manifest.json` is regenerated by `retail manifest --repo .`
  (CLI subcommand `manifest`, `src/retail/cli.py` `_run_manifest`), guarded by the
  043 golden-snapshot test.

**Registry id**: the idea-bank label is `PP1`. Like `B3`, the exact registry id is
a closed-set-at-ratify decision; `PP1` does not collide with any registered id today
(no `P`-prefixed family beyond `P1`/`P2`, and `PP1` is distinct). A non-colliding
working id (`PP1`) is used at build time with a comment that the official id is
confirmed at ratify.

## 5. The recorded wiring-latent-gap

Repo memory records a prior gap where a registered rule was LISTED but never
validated to fire. PP1's tests MUST therefore include at least one test that invokes
the rule directly on a known-bad synthetic pack and observes a non-empty Finding set
(not merely assert the id is registered). Recorded as a test obligation (FR-011 /
SC-005, contract C9).

## 6. Principle-V boundary (publish-safety)

The template's "Publish approval" section (lines ~87-111) is the never-self-grant
gate: "the agent verifies the recorded approval exists and CITES it, but never
self-grants it." PP1's approval check is therefore presence-and-non-placeholder of
the approval slot ONLY. No code path reads the approving owner, the date, or the
sign-off legitimacy; no code path writes any approval. This boundary is the single
most-scrutinized eligibility point and is recorded as an Open-for-human confirmation
at the ratify gate.

## Open questions deferred to the human ratify gate

- Readiness-stage assignment + roadmap provenance row (Principle V -- not guessed).
- Confirmation of the publish-safety boundary above (Principle V).
- Final confirmation of the recommended required-section set + severity = ERROR
  (advisor recommendations; reversible).
