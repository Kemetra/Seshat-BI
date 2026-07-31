# Contract: ship classification and allowlist derivation

**Feature**: 138-agent-driven-bundle | **Story**: US2 | **Enforced by**:
`tests/contract/test_capability_inventory.py` (new),
`tests/contract/test_generated_agent_bundles.py` (existing)

## Interface

The capability inventory is the **authored** source of what ships. The public
knowledge allowlist is **generated** from it and stays committed.

```text
docs/capabilities/capabilities.yaml   (authored)
            │
            │  derive
            ▼
distribution/public-knowledge-allowlist.yaml   (generated, committed, reviewed)
            │
            │  read
            ▼
scripts/export_agent_bundles.py
```

## Obligations

**The inventory MUST:**

1. Carry exactly one entry per skill directory in the repository. A directory
   with no entry is an error.
2. Give every skill-surface entry a `ships` boolean with **no default**, and a
   `ship_classification` from the closed set `compass-verb` | `knowledge-root` |
   `consumer-capability` | `development-only`.
3. Resolve every skill-surface entry to an existing directory, using `skill_dir`
   where the id differs from the directory name.
4. Mark `ships: false` for every `development-only` entry.
5. Mark `ships: true` for every `compass-verb` entry, and carry a `compass-verb`
   classification for every verb id in `.seshat/kit-source.yaml`.

**The derivation MUST:**

6. Produce the allowlist deterministically: the same inventory produces the same
   bytes, with stable entry ordering and stable `entry_id` assignment.
7. Preserve `policy.absence_means_excluded: true`.
8. Preserve every existing entry field — `entry_id`, `source`, `classification`,
   `media_type`, per-harness `targets`, `transform`, `required`,
   `generated_notice`, `review_reason` — for entries that already exist.
9. Emit the same skill set for both harnesses unless the inventory records an
   explicit divergence with a reason.

**The export MUST fail, naming the offender, when:**

10. An entry marked `ships: true` resolves to a missing directory.
11. An entry marked `ships: true` would produce no bundle file.
12. A skill directory is covered by no inventory entry.
13. The committed allowlist does not match a fresh derivation from the inventory
    (i.e. it was hand-edited).

## Prohibitions

- The export MUST NOT retain the hand-written six-name assertion in any form.
  FR-006 requires replacement, not supplementation.
- The derivation MUST NOT infer a classification from a filename, a path prefix,
  or a name pattern. Classification is authored, never guessed.
- No mechanism may suppress obligation 12 for convenience. An unclassified skill
  is a decision that has not been made, not a warning.

## Acceptance evidence

The introducing change lands with `ships: true` on **only** the six knowledge
roots. `test_committed_bundles_match_clean_regeneration` must pass with the
committed bundles unchanged. A byte-identical regeneration is the proof that a
fail-closed governance gate was refactored without altering behaviour; a
non-identical one is a failed refactor.
