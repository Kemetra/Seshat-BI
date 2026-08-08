# Research: Public capability graph integrity

## Decision 1 -- Phase status

**Decision**: REQUIRED.

**Evidence**: Nineteen of 21 shipped public skills resolve through existing
semantics: same-name `surface: skill` references, or explicit
`references.public_skill` for differently named portable wrappers. Two have no
candidate, and one linked capability names a nonexistent canonical source.
Existing gates remain green, proving the boundary is not currently enforced.

**Alternatives rejected**: Treating the phase as already satisfied would rely on
directory presence and generated bundle convergence, neither of which declares a
responsibility owner.

## Decision 2 -- Validation location

**Decision**: Extend `tests/unit/_capability_oracle.py` and its aggregate gate.

**Rationale**: It is already the independent feeder-reading authority for
capability truthfulness and deliberately does not import production readers.

**Alternatives rejected**:

- A new production validator would create a second control plane for a static CI
  invariant.

## Decision 2a -- Ownership edge resolution

**Decision**: Prefer exactly one explicit `references.public_skill` owner. If no
explicit owner exists, require exactly one `surface: skill` capability whose
`references.skill` includes the public name.

**Rationale**: This matches repository truth without duplicating the public name
on 19 already-resolvable capability records. It also prevents a CLI capability
that merely calls a skill from competing with the skill capability itself.
- Adding only a one-off contract assertion would not provide mutation-tested
  fail-closed behavior.
- A new `seshat check` rule would alter runtime governance for repository-wide
  distribution metadata that is already guarded in tests.

## Decision 3 -- Router ownership

**Decision**: Classify both missing routers as `seshat-orchestrator` for current
truth.

**Rationale**: `seshat-bi` selects Seshat readiness and domain routes.
`powerbi-workflows` currently selects Seshat helpers; it does not yet route to an
official Microsoft skill or executor. Phase 3 owns that future transition.

**Alternative rejected**: Declaring `powerbi-workflows` a `seshat-adapter` now
would make upstream ownership metadata claim behavior that is not implemented.

## Decision 4 -- Source validity

**Decision**: For a public capability, accept only a repository-relative tracked
regular file outside generated integration roots.

**Rationale**: Existence alone accepts untracked scratch files; Git tracking is
the stable review and distribution boundary. Generated projections remain valid
outputs but cannot be the authored source.

## Decision 5 -- No bundle input changes

**Decision**: Add manifest records and validation only.

**Rationale**: The existing public wrappers already ship correctly. Phase 1 is
about graph integrity, not content or executor ownership convergence.

## Baseline evidence

| Command | Exit | Result | Classification |
| --- | ---: | --- | --- |
| `python scripts/export_agent_bundles.py --check` | 0 | Generated Claude and Codex bundles match reviewed inputs. | BASELINE PASS |
| Focused capability/public/bundle tests | 0 | 67 passed. | BASELINE PASS |
| `git status --short` in isolated worktree | 0 | Clean before spec creation. | BASELINE PASS |

No external network verification is required for Phase 1 because it changes no
claim about upstream execution ownership.
