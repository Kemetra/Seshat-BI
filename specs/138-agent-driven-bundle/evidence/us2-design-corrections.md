# US2 — corrections to the ratified specification

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

---

## Correction 3 — ownership is by `references.skill`, not by `surface`

**Found during implementation**, after corrections 1 and 2 were already recorded.

**What the spec assumed** (FR-003): the ship decision attaches to "every capability
entry whose surface is a skill".

**What is actually true**: **eight** skill directories are owned by entries whose
surface is something else — `cli`, `execution-adapter`, or `docs`:

```text
retail-validate               owned by  retail-validate            (surface: cli)
evidence-pack-generator       owned by  retail-evidence-pack       (surface: cli)
retail-init / retail-scaffold owned by  same-named entries         (surface: cli)
retail-semantic-check         owned by  retail-semantic-check      (surface: cli)
pbip-workflow                 owned by  pbip-workflow              (surface: docs)
dbt-transformation-adapter    owned by  same-named entry   (surface: execution-adapter)
dagster-orchestration-adapter owned by  same-named entry   (surface: execution-adapter)
```

`retail-validate` is a **compass verb**. Attaching the ship decision to
`surface: skill` would have shipped nine of ten compass verbs while every test
passed — the precise defect this feature exists to remove, reintroduced by the
fix for it.

The cause is the same reference-coverage design as correction 1: the inventory
groups by **capability**, not by representation, so a capability with a CLI verb
*and* a skill is one `surface: cli` entry that still owns a skill directory.

**Resolution**: ownership is by `references.skill`, whatever the entry's own
surface. Recorded in the file's header, enforced by
`tests/contract/test_capability_inventory.py`.

**Second-order consequence**: widening ownership created **duplicate authority** —
five directories acquired two owners each (`retail-govern` was owned by both
`retail-check` and `retail-govern-skill`). Collapsed to exactly one owner per
directory, preferring the `surface: skill` entry; 20 redundant field lines
removed. The contract test now fails on any directory with more than one owner.

---

## Correction 4 — `ships: true` currently describes an intention, not the artifact

**Found**: 2026-07-31, writing the T028–T029 tests | **HEAD**: `3e96af9`
**Status**: OPEN — needs an owner ruling. The agent does not pick.

**What T032 and the contract say**: T032 lands `ships: true` for *"the six
knowledge roots only and `ships: false` for everything else at this story"*, and
the contract's acceptance evidence agrees verbatim: *"The introducing change lands
with `ships: true` on **only** the six knowledge roots."*

**What is actually committed** (measured, not estimated):

```text
inventory entries with `ships: true`        38
  ship_classification: knowledge-root       6   <- the only six US2 authorises
  ship_classification: compass-verb        10   <- T057, User Story 3
  ship_classification: consumer-capability 22   <- T061, User Story 4
skill directories the committed bundle carries  11
entries marked `ships: true` that produce no bundle file  32
```

The last figure is the output of the new
`test_every_shipping_entry_produces_a_bundle_file`, not a hand count.

**Why it happened, and why it is not carelessness**: obligation 5 *forces*
`compass-verb ⇒ ships: true`, and T027 now tests that invariant. Once T032
assigned the `compass-verb` classification to the ten verbs, `ships: true`
followed **by contract**. T032's own end-state and obligation 5 are jointly
unsatisfiable once those classifications exist — both can hold only if the
classification assignment is deferred to US3/US4 along with the shipping.

The twenty-two `consumer-capability` flips have no such excuse: no obligation and
no test forces `consumer-capability ⇒ ships: true`. That is T061 landing early.

**Why it blocks T036 rather than merely annoying it**: obligation 11 is the rule
that `ships: true` must describe the artifact. It is RED against `main` with 32
offenders. T040 then requires `git diff --stat integrations/` to be **empty**
after the derivation lands — so a derivation keyed on `ships: true` would grow the
bundle from 11 skills to 40-odd and fail its own story's acceptance. The fork is
therefore not stylistic; it decides what the derivation keys on.

**The fork**:

1. **Defer the classifications** — revert the 32 premature flips, keeping US2 the
   zero-payload refactor its independent test describes ("regenerate both bundles
   and get byte-identical output"). The ten `compass-verb` and twenty-two
   `consumer-capability` classifications land with T057 and T061, behind the
   portability audit (T047–T056) and the routing-cost ceiling (T059/T064).

   **This means reverting the `ship_classification`, not only the `ships` boolean.**
   Obligation 5 forces `compass-verb ⇒ ships: true`, and the already-green
   `test_classification_invariants_hold` enforces it — so setting the ten verbs to
   `ships: false` while they retain `ship_classification: compass-verb` produces an
   immediately failing tree. The ten must return to unclassified (no `ships`, no
   `ship_classification`), which is what T032's stated end-state implies for
   "everything else at this story".

2. **Collapse US2+US3+US4** — ship all 38 now. This bypasses the portability audit
   (T047–T056), discards T040's empty-diff safety rail, and — measured, not
   asserted — **breaches the ceiling the owner ruled on the same day**:

   | | tokens_approx | vs ceiling 6,000 |
   |---|---:|---|
   | today, 11 skills | 579 | — |
   | all 43 shipped, untrimmed | **7,253** | **over by 1,253** |
   | all 43, seven descriptions trimmed to the bundle norm | 5,629 | meets, ~370 headroom |

   Source: `evidence/routing-cost.md`, T006 **RULED** 2026-07-31 (Ahmed Shaaban),
   ceiling **6,000 `tokens_approx`**, option A+. So option 2 does not merely skip a
   checkpoint — it commits a state that T064 must fail, unless the seven
   description trims land in the same change.

**Recommended**: option 1. Option 2 makes the gate wider and the evidence weaker
in the same change, which is the combination the feature exists to prevent — and
it would land 1,253 tokens over a ceiling ruled hours earlier.

### RULED — option 2, collapse US2+US3+US4

- **ruled_by**: Ahmed Shaaban (owner)
- **ruled_on**: 2026-07-31
- **recorded_by**: the agent transcribed an owner-directed ruling after presenting
  both options with the measured consequences of each; it did not self-grant
  (Principle V). The agent's recommendation was option 1 and was not adopted.

**Ruled**: the 32 flips stand. The derivation keys on `ships: true`, and the
payload of US3 and US4 lands inside US2.

**What the ruling waives**: T040's empty-diff acceptance, and with it the
"byte-identical regeneration" independent test of US2. The `integrations/` diff
will be large and must be reviewed as a payload change, not compared to zero.

**What the ruling does NOT waive** — neither was put to the owner, so both stand:

1. **The 6,000 `tokens_approx` ceiling** (T006, CLOSED). Option 2 lands at 7,253
   untrimmed, so the seven description trims are now in scope *inside this change*.
   T064 remains authoritative and remains a hard fail.
2. **The portability audit** (T047–T056). The 32 skills carry read-instructions to
   `templates/`, `docs/worked-examples`, `specs/`, `.claude/skills/` and other
   development-repository paths. Shipping them before the audit ships instructions
   that cannot resolve in a `seshat init-project` workspace — the defect FR-017
   exists to prevent. **No bundle regeneration may be committed until the audit
   passes.**

**Resulting order of work** (dependency, not preference):

```text
derivation (T036-T038)            code only, no regeneration
   -> portability audit (T047-T049) + canonical rewrites (T050-T056)
      -> the seven description trims
         -> regenerate + measure (T039, T058, T063, T059/T064)
```

`test_committed_bundle_carries_every_shipping_entry` stays RED for the whole
middle of that sequence by design: the inventory is correct and the bundle is not
yet regenerated. It goes green at the final step, and it is the check that proves
the regeneration actually happened.

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
