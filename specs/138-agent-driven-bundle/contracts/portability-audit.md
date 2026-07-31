# Contract: `portability-audit-v1` export transform

**Feature**: 138-agent-driven-bundle | **Story**: US3 (applies to US4) |
**Enforced by**: `tests/unit/test_portability_audit.py` (new), and the export
itself

## Interface

A third entry in the export's allowed-transform set, alongside
`copy-normalized-v1` and `template-substitute-version-v1`. It is a **gate**, not
a rewriter: it inspects shipping skill text and either permits it unchanged or
fails the export.

```text
shipping skill text ──▶ portability-audit-v1 ──▶ permitted unchanged
                                     │
                                     └──▶ EXPORT FAILS
                                          (skill, path, line, reason)
```

## Obligations

1. The transform MUST fail the export when a shipping skill instructs the agent
   to **read** a path that a scaffolded workspace does not contain.
2. It MUST report the skill, the path, the line, and the reason — enough to fix
   without re-deriving the finding.
3. It MUST permit a reference that names an **output a scaffold step produces**.
4. It MUST permit a reference explicitly scoped by an "in the Seshat development
   repository" condition.
5. It MUST treat the scaffolded workspace shape as authoritative: today
   `mappings`, `warehouse/migrations`, `powerbi`, `reports`, `evidence`. If that
   set changes, the transform's notion of "present" changes with it — it MUST NOT
   carry its own duplicate list.
6. It MUST apply to every shipping skill, not only to the ten compass verbs, so
   US4's additions are gated by the same rule.

## Prohibitions

- **It MUST NOT modify content.** Removing or rewriting a paragraph at export
  time would let a generated skill diverge silently from its canonical source,
  destroying the single-source property the design rests on (FR-018).
- **It MUST NOT classify by path prefix.** A prefix rule is wrong in both
  directions: `templates/` is absent from a fresh workspace, so a prefix rule
  flags legitimate scaffold-output references; and a genuinely broken reference
  under a permitted prefix would pass.
- **It MUST NOT offer a suppression list or an inline ignore.** A suppression
  mechanism recreates the silent-divergence failure this transform exists to
  prevent. A finding is resolved by rewriting canonical text or by not shipping
  the skill.
- It MUST NOT weaken, reword, or drop any hard stop, gate, or refusal in the
  skill it inspects.

## Known scope at authoring time

23 distinct dev-only references across the ten compass verb skills, spanning
`templates/`, `docs/worked-examples`, `specs/`, `.claude/skills/`,
`docs/roadmap`, `docs/quality/`, `scripts/`, `src/seshat/` and `tests/`. Each is
resolved by a reviewed rewrite of canonical text, verified in **both** contexts:
unchanged behaviour in this repository, and every instructed path resolvable in a
scaffolded workspace.

## Acceptance evidence

The transform rejects before it permits: run the export against the current
canonical text and confirm it fails, naming findings. Then confirm, after the
rewrites, that it passes and that no shipped skill instructs an agent to read a
path a scaffolded workspace lacks.
