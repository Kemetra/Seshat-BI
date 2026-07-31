# US2 — two corrections to the ratified specification

**Found**: 2026-07-31, inspecting `docs/capabilities/capabilities.yaml` before
writing code | **HEAD**: `aa7a3e5`

Both were found by reading the inventory's own header contract and measuring its
coverage, before any implementation. Neither changes the story's goal; both
change how it is reached, and one **removes** work.

---

## Correction 1 — FR-002's `skill_dir` field is redundant. Withdrawn.

**What the spec assumed**: four `surface: skill` entries carry ids that match no
directory (`retail-govern-skill`, `run-next-readiness-skill`,
`pbir-authoring-adapter-skill`, `speckit-workflow-skills`), so a `skill_dir`
field is needed to resolve them.

**What is actually true**: every entry already carries a `references.skill` field
that resolves the directory, and it already supports a **list** for the
one-entry-covers-many case:

```text
retail-govern-skill           references.skill = "retail-govern"           resolves
pbir-authoring-adapter-skill  references.skill = "pbir-authoring-adapter"  resolves
run-next-readiness-skill      references.skill = "run-next-readiness"      resolves
speckit-workflow-skills       references.skill = [ ...14 entries... ]      resolves
```

Measured coverage: **50 of 50** skill directories covered, **0** references
pointing nowhere.

The file's header states this design explicitly: *"Completeness is
REFERENCE-COVERAGE, not entry-per-representation (data-model.md validation rule
6): one capability with a command + a same-named skill + a kit-source verb is ONE
entry whose `references` covers all three."*

**Resolution**: FR-002 is **withdrawn**. The derivation resolves directories
through the existing `references.skill`, accepting both the scalar and list
forms. Adding `skill_dir` would introduce a second way to answer a question the
file already answers — precisely the duplication FR-006a and Principle II forbid.

**Task effect**: T031 is dropped. T024 and T025 already hold against the current
file and become regression guards rather than new constraints.

---

## Correction 2 — FR-001 is a scope widening, not a repair

**What the spec asserted**: the inventory "omits the only skills that currently
ship", implying an oversight.

**What is actually true**: the inventory's declared scope excludes them. Its
header defines coverage as *"a REPO skill is a `.claude/skills/*/SKILL.md` file
tracked by git at the repo top level"*. The six reviewed knowledge bases live in
top-level `skills/`, not `.claude/skills/`, so they are **out of scope by
design**. Verified: none of the six is mentioned anywhere in the file, and no
entry references the top-level `skills/` tree.

**Why it still must change**: the inventory cannot be the single authored source
of *what ships* while its scope excludes six of the eleven skills that currently
ship. The choice is to widen the scope or to give the derivation two inputs — and
two inputs is the split-authority outcome US2 exists to remove.

**Resolution**: FR-001 stands, **reframed**. The inventory's O2 scope widens from
"a `.claude/skills/*/SKILL.md` tracked by git" to "any committed SKILL.md the kit
authors, wherever it lives", and the six knowledge roots are added under it. This
is a deliberate, reviewable change to a declared contract, recorded here rather
than performed silently — the header comment must be updated in the same change,
or the file will contradict its own stated scope.

**Task effect**: T030 additionally updates the header's O2 scope statement.

---

## Why this matters beyond the two edits

The specification was ratified describing a defect ("four ids match no
directory") that the file had already solved, and a repair ("add the six
entries") that is really a contract change. Both readings came from measuring
the file's *data* without reading its *header contract*.

The header is the file's own specification. It documents the O2 scope, the
reference-coverage rule, and the fail-closed intent — and it answered both
questions directly. Reading it first would have produced a smaller, more accurate
US2.
