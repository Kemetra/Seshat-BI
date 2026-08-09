# Known findings recorded during spec 142 (T005)

This file discharges **FR-010's affirmative half**: record the pre-existing
fail-open, do **not** fix it. Fixing is deferred to OD-3 as its own spec.

---

## KF-1 -- Five axis constants in `capability_inventory.py` are dead

**Location**: `src/seshat/capability_inventory.py:35-43`

```python
_LIFECYCLE_STATES: frozenset[str] = frozenset({"shipped", "spec-only", "deferred"})
_AUTHORITIES: frozenset[str] = frozenset({"agent-runnable", "advisory", "human-gated"})
_SURFACES: frozenset[str] = frozenset(
    {"cli", "skill", "execution-adapter", "plugin", "docs", "human-artifact"}
)
_REQUIREMENTS: frozenset[str] = frozenset({"database", "optional-dependency"})
_PROVENANCES: frozenset[str] = frozenset(
    {"locally-verified", "publicly-released", "unrecorded"}
)
```

### Evidence they enforce nothing

**1. Each name appears exactly once in the module -- at its own definition.**
`grep -n` for all five in `capability_inventory.py` returns only lines 35, 36,
37, 40, 41. No comparison, no membership test, no validation call anywhere else
in the file.

**2. A live manifest value violates one of them with no consequence.**
`docs/capabilities/capabilities.yaml` contains an entry with
`surface: product-module` (`governed-statistical-core`). `product-module` is
**absent** from `_SURFACES` above. The manifest loads, `capability_inventory`
renders, `seshat check` exits 0, and every contract test passes. Nothing fires.

That is the definition of a fail-open: a declared constraint that silently
accepts violating data.

### Why it is NOT fixed here

Making these live is a behavior change across **five unrelated axes**
(`state`, `authority`, `surface`, `requirements`, `provenance`) and would fail
immediately on the live `product-module` value -- so the fix is not a tightening,
it is a tightening *plus* a data migration or a widened token set, for axes this
spec does not own.

Recorded as **OD-3**, resolved 2026-08-07 as *record, do not fix*.

### Guard against accidental repair

**FR-010** forbids reviving them as a side effect. This matters concretely:
**FR-011 / T016 edits `_RECORD_FIELDS` in the same module**, a few lines below
these constants. An implementer tidying "unused" constants while in the
neighborhood would smuggle a five-axis behavior change into a metadata
migration. Leave lines 35-43 untouched.

---

## KF-2 -- No re-vendor or upgrade path is recorded for vendored spec-kit content

**Surfaced by**: OD-1's investigation (spec 142, resolved 2026-08-07).

The repo contains **14** `speckit-*` skills under `.claude/skills/`, plus
`.specify/templates/`, `.specify/scripts/`, and the extensions framework. All were
written by upstream's own installer (`specify init --here --integration claude
--script ps`, spec-kit `0.8.10`) in commit `1eb0c98`, hash-verified against
`.specify/integrations/claude.manifest.json`, with zero local drift.

**This is not a Principle II violation.** Principle II is scoped to the Power BI
execution adapter (`.specify/memory/constitution.md:271-275`), and constitution
amendment v1.1.0 -- made in the same commit -- explicitly permits this state
(`:556-563`).

**The residual gap is real and narrower**: nothing records how to *update* the
vendored content. There is no lockfile, no `specify upgrade` record, and no re-run
instructions. Today's copy is provably unmodified, but nothing preserves that, and
an upstream improvement can only be adopted by a fresh manual `specify init`.

That is precisely the "fork tax" the Principle II *rationale* warns about --
unpaid so far. It is out of scope for this spec, which only records it (T042a).
It deserves its own decision.

**CLOSED 2026-08-09 by spec 151.** The decision this finding asked for was taken,
and the re-vendor path is now recorded on disk:

- `.specify/init-options.json` pins the reproducible invocation
  (`speckit_version` `0.8.10`, `integration` `claude`, `script` `ps`,
  `branch_numbering` `sequential`), so a re-vendor is a re-run of a recorded
  command rather than a reconstructed one.
- `.specify/integrations/speckit.manifest.json` hash-pins all ten vendored
  `.specify/scripts/` + `.specify/templates/` files with an `installed_at`
  stamp, so drift after a re-vendor is detectable.

The paragraph above also understated the drift at the time of writing: commit
`f35612f` had already modified `.specify/templates/spec-template.md` (an 11-line
ADR-0019 vocabulary block), so the copy was **not** provably unmodified. Spec 151
resolved that by REMOVING the modification rather than institutionalizing it --
Spec Kit owns Spec Kit, and Seshat status governance moved to
`src/seshat/spec_status_policy.py`. The `capability_owner: vendored-upstream`
entry's `update_policy` in `docs/capabilities/capabilities.yaml` now carries this
same path; the two surfaces agree.

---

## Note on scope

Both findings are **recorded, not fixed**. Spec 142's Non-goals forbid fixing
either: KF-1 is OD-3, KF-2 is a tooling decision outside a metadata axis.
