# Rule coverage honesty — design (Phases 1+2)

**Date:** 2026-08-04
**Status:** design approved by Ahmed Shaaban (approach A, spec 1 = Phases 1+2)
**Origin:** GitHub prior-art scan 2026-08-04. Adapted from `mudassir09/pbi-enterprise-cli`,
whose Best Practice Analyzer runner reports which rules were *evaluated* vs *skipped*
"rather than silently mis-evaluating missing properties". No code was copied; the idea is
the rule-level expression of this repo's own evidence-over-scores principle.

## Problem

`seshat check` reporting no findings is ambiguous. It can mean either:

1. the rule ran against real input and found nothing wrong (**verified clean**), or
2. the rule's required input was absent, so it early-returned `[]` (**never checked**).

A human reading a clean gate cannot tell these apart. That is the same class of defect the
project exists to prevent, located inside the gate itself. The codebase already names the
problem in its own comments:

- `src/seshat/severity_posture.py:354` — `absent -> silent skip, <no-finding> (Principle V: floor key IS the opt-in)`
- `src/seshat/rules/sql.py:32` — `(no identifiers/tokens/DDL to match), so returning "" is a silent no-finding`

## Measured scope

Derived by introspecting the live registry on 2026-08-04 (`all_rules()` plus a
module-level early-return heuristic; the per-rule exact figure is Phase 1's exit
criterion). Reconciles to **79** registered rules, all ids unique:

| Class | Count | Assessment |
|---|---:|---|
| `KIT_SELF` — already emit one INFO finding on skip | 10 | **Not the gap.** `core.py:24-37` makes these skips visible already |
| `WORK_REPO` with an absent-input early return | **39** | **The gap** |
| No absent-input path detected | 30 | Fine |

The 39: `AD1 AL2 C2 CB1 DL3 DL4 DL5 DL7 DL8 DS1 DS2 DS3 DS4 DS5 G1 G2 G3 G4 G5 HR6
HR7 HR8 HR9 HR12 HR13 KP1 P1 P2 PP1 RS1 S1 S2 S3 S4a S4b S5 S6 S7 S8`

> **Method note.** An earlier grep over `@register(...)` reported 50 rules / 25 in
> the gap. Its regex broke on nested parentheses in decorator arguments and
> silently dropped 29 rules. The registry is authoritative; counts in this document
> come from runtime introspection, never from source-text matching. That a
> plausible-looking scan under-reported by 37% without erroring is itself an
> argument for the feature being built here.

`RuleTier.KIT_SELF` is the precedent this design extends: "absence is not drift" (kit_lint
FR-006) already established that a rule which cannot run should say so rather than pass
silently. What it lacks is a *machine-readable census* — you cannot reconcile "did every
rule actually run?" from findings alone.

## Coverage model

Every registered rule yields exactly one coverage record per run.

| State | Meaning | Reached when |
|---|---|---|
| `evaluated` | Rule ran to completion on present input. Empty findings = verified clean | Required inputs present |
| `unevaluable` | Required input missing or unreadable — the honesty gap | A declared requirement is absent |
| `undeclared` | Rule has not yet declared its applicability | Not migrated |
| `not_applicable` | A **human-ratified** opt-in; the rule legitimately does not apply | Declared **with a citable basis** |

### Why `undeclared` exists

Both tempting defaults fail. Defaulting unmigrated rules to `unevaluable` floods the report
with 39 false alarms; defaulting to `evaluated` silently blesses the exact behavior being
fixed. A distinct fourth state makes migration measurable (79 → 0) and converts Phase 3's
governance judgment into an objective counter.

### Why `not_applicable` is basis-gated

`not_applicable` asserts that a named human ratified this absence as intentional. An agent
assigning it would be self-granting an approval, which
`never_self_grant_approval` forbids. Therefore:

- declaring `not_applicable` **requires** a `basis` reference to a ratified source;
- declaring it **without** a basis is a schema error, not a permissive default;
- the only basis found in the tree today is Principle V for `severity_posture.py:354`
  ("floor key IS the opt-in"). Everything else stays `undeclared` until an owner rules.

### Present-but-empty input

A rule whose input exists but contains nothing to examine (`rules/sql.py:32`) is
**`evaluated`** — it ran to completion on real input. Rationale: the alternative
(`unevaluable`) would flag a SQL file that legitimately has no DDL, which is not a
governance gap. Counting examined subjects would require changing all 79 rule signatures
and is deferred; `sql.py` is the test that pins this decision.

## Components

| # | File | Responsibility |
|---|---|---|
| 1 | `src/seshat/rule_coverage.py` *(new)* | Coverage vocabulary + frozen dataclasses. Pure, no I/O |
| 2 | `src/seshat/registry.py` *(extend)* | Keyword-only `requires` / `absence` with defaults |
| 3 | Runner *(extend)* | Emit a coverage census alongside findings |
| 4 | `seshat check` + HTML report | **Phase 1** human surface |
| 5 | `status` / `next` projection | **Phase 2** additive agent-readable field |

The registry extension follows the existing `tier=` precedent (`registry.py:10-20`,
`core.py:106-108`): a keyword with a default, so all 79 current `@register(id, title)`
call sites compile untouched.

## Data flow

```
inputs (present / absent / unreadable)
  -> runner evaluates each registered rule
  -> CoverageRecord(rule_id, state, requirement, reason, basis)   # one per rule, always
  -> census aggregate
       |- Phase 1 -> seshat check output + HTML report section
       \- Phase 2 -> agent readiness projection field (additive only)
```

## Error handling

**Unreadable is not absent.** A parse error or permission denial is `unevaluable`, never
`not_applicable`. This repo genuinely produces unreadable-path conditions (sandbox-owned
`.pytest_cache` directories), so misclassifying them would rebuild the silence being
removed.

## Phase boundaries

**Phase 1** — coverage model, registry extension, census, human surface. Adds no rule and
changes no verdict, so it is `<no-finding>` on main by construction.

**Phase 2** — expose the census to the agent as an **additive projection field only**.
Stage verdicts must be byte-identical. "An unevaluated stage cannot read as cleared" is
deliberately *excluded*: that changes verdicts and therefore belongs to Phase 3.

> **RESOLVED 2026-08-04 (owner delegated the decision) — implemented as option (c),
> live-computed and opt-in.** `build_status_projection(root, include_coverage=True)` and
> `seshat status --coverage` compute the census on demand; the default projection keeps no
> `coverage` key and stays byte-identical. The schema gained an optional `coverage`
> property (required list untouched), so `additionalProperties: false` still rejects
> anything undeclared.
>
> Option (c) was preferred over both (a) and (b) because it makes the governance question
> disappear rather than answer it: nothing is persisted, so there is no staleness to define.
> Rules are pure by contract (`core.Rule`), so evaluating the registry keeps the projection
> read-only; opt-in keeps the registry evaluation off the default path, which a glob-only
> projection otherwise never does.
>
> The two facts that ruled out the original "additive field" premise:
>
> 1. `status_surface.build_status_projection` never runs rules. It globs
>    `mappings/*/readiness-status.yaml` and projects committed evidence; there is no rule
>    execution to attach a census to.
> 2. `schemas/agent-status.schema.json` sets `additionalProperties: false` at the root and
>    on every `$def`. A new field is a versioned-schema change, not an addition.
>
> Options considered and rejected:
>
> - **(a) status always runs the registry** — couples a read-only evidence projection to
>   executing all 79 rules on the default path. Rejected for that unconditional cost.
> - **(b) `check` persists a census artifact that `status` reads** — rejected because it
>   creates a readiness-adjacent committed artifact and with it a governance question
>   (*what does a STALE census mean?*), the same staleness problem `decision_gate.py:94-99`
>   solves for evidence refs via sha256 pinning. Computing live avoids needing an answer.
>
> **Authorization boundary.** The owner delegating this architecture choice did NOT
> authorize marking any rule `not_applicable`. That state still requires a per-rule ratified
> basis; a general authorization is not a ratification of 39 absence semantics, and the
> `Requirement` constructor still refuses a basis-less opt-in.

**Phase 3 (NOT this spec)** — fail-closed CI. Preconditions: `undeclared == 0` **and**
every `not_applicable` carries a basis. Needs an owner ruling, because a fail-closed rule
must be `<no-finding>` on main to land and 39 rules are currently in scope.

## Testing

- **Unit** — each state derivable; frozen dataclasses; `undeclared` is the default for
  unmigrated rules; `not_applicable` without a basis raises.
- **Contract (load-bearing)** — the census covers exactly `registry.all_rules()` by **set
  equality**, never a hardcoded count. Catches any rule dropping out of the census, and
  does not break when rule 80 is added.
- **Invariance** — `seshat status` / `next` verdict fields unchanged before vs after
  Phase 2. Asserted by test, not documented as a note.
- **Regression** — existing findings byte-identical; coverage is purely additive.

## Risks

| Risk | Handling |
|---|---|
| A new fail-closed rule must be `<no-finding>` on main | Phases 1+2 add no rule |
| `skills/**` edits break `test_committed_bundles_match_clean_regeneration` | Phases 1+2 do not touch `skills/`; regenerate via `scripts/export_agent_bundles.py` if `docs/capabilities/` is reached |
| CodeScene delta gate fails PRs on new smells | Methods <70 lines, nesting <4; run `analyze_change_set` before pushing |
| `test_doctor` reads the live working tree | Do not edit files during a `pytest -m unit` run |
| Local `git commit` fails (exit 128, 1Password SSH signing) | Scratch `GIT_CONFIG_GLOBAL` for pytest only |

## Governance

This work does **not** enter the Spec Kit fence. `test_active_spec_kit_markers_agree_and_resolve`
reads only the `<!-- SPECKIT START/END -->` blocks in `CLAUDE.md` / `AGENTS.md` and the plan
path they name; adding no `specs/NNN-*/plan.md` and not editing the fence leaves it green.
`specs/138-agent-driven-bundle/plan.md` keeps the active slot.

## Out of scope

Phase 3 fail-closed CI; the grandfathering ruling; the ratified opt-in allowlist; migrating
the 39 `WORK_REPO` rules' declarations (each needs its module's logic read, which is
judgment, not a mechanical pass).
