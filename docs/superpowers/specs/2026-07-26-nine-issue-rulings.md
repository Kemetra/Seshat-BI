# Owner rulings for the nine open issues -- decision record

- **Date:** 2026-07-26
- **Status:** **RULINGS RECORDED.** The repository owner (Ahmed Shaaban) was
  presented with six batched decisions and ruled on all six in a single
  session. This note records those rulings so every downstream PR can cite an
  explicit decision rather than encoding a design choice silently in a patch.
- **Scope:** issues #474, #485, #488, #489, #492, #493, #494, #497, #499.
  Issue #469 (F016 slices 5-6) was explicitly excluded by the owner.
- **Why this note exists:** four of the nine issues had already shipped their
  mechanical half, and every remaining half was marked "needs an owner ruling"
  by the prior agent -- correctly, per the `never_self_grant_approval`
  hard-stop. The owner delegated those rulings for this mission. A delegated
  ruling that is written down is legitimate governance; the same ruling buried
  in a diff is the failure mode the deferral notes were avoiding.

## What had already shipped before this mission

Read from `main` history, not assumed:

| Commit | Issues | What landed |
|---|---|---|
| `b585f8f` (PR #495) | #488, #489 | Routing to the shipped `seshat scaffold-source`; adapter checkpoint in `retail-build-warehouse`. |
| `0aeb7e9` | #492, #494 | Disclaimers: both validators now state what they do **not** check. |
| `9f0a881` (PR #498) | #491 | Date dimension contributes attributes (related to #497/#499). |

The branch `fix/485-487-approval-and-tier-scoping` is a stale duplicate of
work already on `main` via PR #495; it is not a source of new work.

## The six rulings

### R1 -- #485 / #493 live-DB provenance: **B now + A2 spec**

The design note `2026-07-25-live-db-provenance-design.md` established that a
hand-authored provenance field (option A1) is **forgeable from `.env` without
opening a socket**, and is therefore strictly worse than today's honest
silence. That finding stands and A1 remains rejected.

**Ruled:** ship option B (the honest caveat) now, plus the mechanical #493
fix, and write A2 (machine-written, server-echoed digest) as a spec without
building it.

Rationale for splitting them: A2 requires `seshat validate` to write a
committed artifact for the first time -- today it deliberately writes nothing.
That is a genuine feature with a live-connection write path, and the design
note itself says it "wants its own spec and an owner decision on whether
`validate` may write a committed artifact at all."

**#493 is mechanical, not a design question.** `.gitignore:111`'s own comment
already declares the convention:

> Machine-local run output; the COMMITTED record is the rendered
> `orchestration/dagster/run-evidence/<run-id>.md`.

So the architecture already distinguishes machine-local scratch from
reviewable evidence. `portfolio_watch.py:479-521` simply reads the wrong one
of the two. Keying caveat-suppression on the committed record honours a
convention this repo already wrote down.

- #493 -> **closed** by this mission.
- #485 -> **honestly qualified**, remains open pending A2. Not claimed closed.

### R2 -- #499 placement naming: **physical name + resolution assertion**

`gold_placement` values name a *logical* dimension (`dim:dim_product`) while
`gold_star.dimensions[].name` carries the *physical* table
(`gold.dim_product_rss`). All five placements in the one real map fail to
resolve, so `_attr_silver_types` returns `{}` for every dimension.

**Ruled:** the **physical** name is canonical in placements. Fix the map's
placements to name it, and add an assertion that every `dim:` prefix resolves
to a declared dimension.

Rationale: it matches the resolver's already-documented intent
(`rules/conformed_dimension.py:156-157`), and it makes a typo fail loudly
instead of being indistinguishable from a deliberate no-op. Suffix-tolerant
matching was rejected because fuzzy matching inside a governance rule
preserves exactly the ambiguity the assertion is meant to remove.

**Hard landability constraint:** a new rule must be no-finding on `main` to
land. The assertion fires 5x on today's map, so the placement correction and
the assertion **must ship in the same commit**. Verified before push, not
after CI.

### R3 -- #492 column-set drift: **advisory finding, no ADR edit**

`schemas/dbt-run-evidence.schema.json:144-151` is a **closed** enum of four
assertion classes and `evidence.py:147` fail-closes on a fifth. Parity is
enumerated as value-only in four normative artifacts including **ratified
ADR-0009**. Adding a fifth class amends a ratified contract.

**Ruled:** surface column-set drift as a **distinct advisory finding outside
the parity enum**. ADR-0009 stays intact.

Rationale: the issue itself offers this route ("surface it as a distinct
advisory finding rather than a hard failure, since an intentional shadow-only
column may be legitimate during a migration -- but it should not be
invisible"). The obstacle was authority, not risk; routing around the ratified
enum resolves the authority problem without weakening the signal. Census
already showed the assertion would be no-finding on all six worked-example
model pairs.

### R4 -- #494 TMDL lint: **narrow lint, deliberately narrow name**

Full-fidelity TMDL validation needs the `TmdlSerializer`/TOM path that
**ADR-0001 deliberately excluded** to keep this toolchain headless.

**Ruled:** build the narrow `///`-must-attach rule that *is* buildable today,
under a deliberately narrow name -- **not** `tmdl-validate`.

Rationale: the shipped disclaimer commit warned that a partial syntax check
"risks implying coverage it lacks -- the same over-claim this commit is
correcting." A narrow name is what prevents the fix from recreating the defect
it fixes. The rule must not be presented as pre-Desktop clearance.

### R5 -- #474 narrative validation: **five criteria, migration left owner-gated**

**Ruled:** implement the five mechanical acceptance criteria (validate all
required v1 keys/types, contract-to-question linkage, reject malformed
entries, the dimension-grounding ruling, adversarial tests for every
reproduction). Leave criterion 5 -- migrating the signed `retail_store_sales`
artifact -- untouched.

Rationale: `test_real_worked_example_map_still_needs_phase_b_migration`
(`tests/unit/test_narrative_check.py:745-757`) pins the current fail-closed
state and its comment marks it explicitly owner-gated: *"an explicit
owner-gated follow-up (Option A) ... when the map is migrated, this test flips
and must be updated deliberately."* Migrating a signed artifact under a
delegated ruling would override a gate that names a *different* review
(named-owner review of the signed map). The delegation covers design rulings,
not re-signing signed artifacts.

- #474 -> validation hardening shipped; the migration criterion stays open and
  is named in the PR body.

### R6 -- #497 date-attribute source of truth: **read `attributes`, default to the migrations set**

`_DATE_COLUMNS` (`dbt/scaffold/model_plan.py:445`) hardcodes seven columns
while the migrations star (`0004_*.sql:78-88`) carries ten -- it additionally
has `month_name`, `day_name`, `is_weekend`.

**Ruled:** `_date_dimension` reads `attributes` like `_dimension_model`
already does, with a documented default when absent.

**The absent-case default is the entire fix.** Verified across all five
tracked `source-map.yaml` files: **zero** declare `date_dimension.attributes`.
So the default governs every existing map, and it must equal the **migrations
DDL set**, not today's `_DATE_COLUMNS` -- otherwise the change merely
relocates the divergence instead of removing it.

## What is NOT claimed by this mission

Stated plainly so no reader over-reads the result:

- **#485 is not closed.** A2's writer is not built. The caveat is honest
  qualification, not provenance.
- **#474's real-example migration is not done** and remains owner-gated.
- **ADR-0009 is not amended.** #492's advisory path deliberately routes around
  the ratified enum rather than editing it.
- **No full TMDL validator ships.** #494's lint is one narrow rule; ADR-0001's
  headless exclusion is untouched.
- No stage is granted, no approval is self-granted, and no confidence score is
  emitted by any change in this mission.

## Governance

Every ruling above was made by the repository owner during this session and is
recorded here before implementation. The `never_self_grant_approval` hard-stop
is intact: these are design rulings on how checks should behave, not
self-granted readiness approvals. No ruling here approves a stage, ratifies a
readiness claim, or edits a signed artifact.
