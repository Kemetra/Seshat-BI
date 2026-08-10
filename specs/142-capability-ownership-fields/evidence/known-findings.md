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

**NARROWED 2026-08-09 by spec 151 -- still OPEN for five skills.** The decision
this finding asked for was taken and most of the re-vendor path is now recorded
on disk:

- `.specify/init-options.json` pins the reproducible invocation
  (`speckit_version` `0.8.10`, `integration` `claude`, `script` `ps`,
  `branch_numbering` `sequential`), so a re-vendor is a re-run of a recorded
  command rather than a reconstructed one.
- `.specify/integrations/speckit.manifest.json` hash-pins all ten vendored
  `.specify/scripts/` + `.specify/templates/` files with an `installed_at`
  stamp; `.specify/integrations/claude.manifest.json` hash-pins nine of the
  fourteen `speckit-*` skills.

**The residual gap, restated precisely.** Five skills -- `speckit-git-commit`,
`speckit-git-feature`, `speckit-git-initialize`, `speckit-git-remote`,
`speckit-git-validate` -- are pinned by NEITHER manifest, and
`specs/151-speckit-fork-removal/spec.md` lists them under Out of Scope. So a
re-vendor following the recorded path can verify 9 of 14 skills plus the ten
scripts/templates, and drift in the remaining five stays undetectable. The fork
tax is mostly paid, not fully paid, and this finding stays OPEN at that reduced
scope until the five are pinned or a documented decision retires them.

The paragraph above also understated the drift at the time of writing: commit
`f35612f` had already modified `.specify/templates/spec-template.md` (an 11-line
ADR-0019 vocabulary block), so the copy was **not** provably unmodified. Spec 151
resolved that by REMOVING the modification rather than institutionalizing it --
Spec Kit owns Spec Kit, and Seshat status governance moved to
`src/seshat/spec_status_policy.py`. The `capability_owner: vendored-upstream`
entry's `update_policy` in `docs/capabilities/capabilities.yaml` now carries this
same path; the two surfaces agree.

**CLOSED 2026-08-10 -- at skill scope; the five are pinned.** *Recorded by an
agent under owner instruction. No ratification was re-signed and no approval was
self-granted: this note asserts only that the finding's own stated condition is
satisfied on the evidence below, leaving the 2026-08-07 ratification perimeter
(`ratify-ledger.md`) untouched.* This finding admitted two resolutions: pin the
five, or take a documented decision retiring them. The **pinning** branch was taken -- nothing was retired, deleted,
reclassified, or rerouted. `.specify/integrations/claude.manifest.json` now
hash-pins **14 of 14** `speckit-*` skills, meeting the condition this finding
stated ("until the five are pinned"). Together with
`speckit.manifest.json`'s ten scripts/templates, **24** vendored files are
pinned.

Two checks ran before the hashes were written:

- **Provenance decided the remedy.** All five `speckit-git-*` skills were added
  in `1eb0c98` -- the same upstream-installer commit as the nine already pinned
  -- with **zero** commits touching them since, and the git blobs at `1eb0c98`
  hash to exactly the pinned values (checked at blob level, so no checkout
  artifact can contaminate the result). They are therefore genuine vendored
  bytes, and pinning records upstream truth. Had they entered in a different
  commit they would not have been vendored content at all, and the correct fix
  would have been reclassification under a Seshat owner rather than
  hash-pinning.
- **The hash convention was fixed empirically -- and is per-manifest.** The nine
  pre-existing hashes were confirmed to reproduce byte-for-byte against the
  working tree *before* any entry was added, establishing sha256 over raw
  checked-out bytes **for `claude.manifest.json`**, whose entries are all `.md`
  pinned `eol=lf` by `.gitattributes`. This does **not** generalize:
  `speckit.manifest.json`'s five `.ps1` entries verify only after normalizing
  CRLF to LF (`specs/151-speckit-fork-removal/research.md`), so a reader
  applying one convention across both manifests will see five spurious drift
  reports. All 14 entries verify with zero drift under the correct convention.

**What is NOT fixed -- the successor gap.** Pinning is complete for *skills*, not
for the *capability*. `.specify/extensions/` (18 tracked files: the
git-extension framework, whose `speckit.git.*.md` command files are upstream's
**source** for the five skills just pinned, plus bash/PowerShell scripts),
`.specify/extensions.yml`, `.specify/workflows/`, and `.specify/integration.json`
are pinned by neither manifest. This finding's own founding text above names "the
extensions framework" among the vendored content, so that surface -- executable,
and therefore higher-risk than skill prose -- stays unverifiable on re-vendor. It
is the natural successor to KF-2 and is deliberately **not** claimed closed:
tracked as **issue #603**, which carries the full unpinned inventory and the
per-file-type normalization caveat that any pinning there must resolve.

The root cause is also upstream's: its installer emits the five `speckit-git-*`
skills but does not record them in the manifest it writes. Since that installer
owns the file and rewrites it wholesale, a re-vendor will drop both the five
entries and the `seshat_added_entries` key that marks them as Seshat-authored.
That key carries its own `on_revendor` procedure. Upstreaming the omission to
GitHub Spec Kit was Out of Scope for Spec 151 and remains unattempted -- a
standing, documented cost, not an open finding.

---

## Note on scope

Both findings were **recorded, not fixed, by spec 142**. Spec 142's Non-goals
forbade fixing either: KF-1 is OD-3, KF-2 is a tooling decision outside a
metadata axis. That remains an accurate statement about spec 142's own scope.

Later work outside this spec has since acted on KF-2 -- spec 151 recorded most
of the re-vendor path, and the 2026-08-10 change above pinned the last five
skills, CLOSING it. **KF-1 remains open and untouched.** This file stays the
canonical home for both findings' status; the spec whose non-goals are quoted
above is not the spec that resolved them.
