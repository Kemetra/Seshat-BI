# T050 -- ownership census (SC-001)

Built from the RAW manifest, never from the rendered inventory: the
renderer defaults an absent mapping to `unclassified` for display, so a
census taken from its output could not tell *undeclared* from
*declared unclassified*.

- total entries: **102**
- undeclared (no capability_owner at all): **0**
- declared `unclassified` sentinel: **0**

**Every entry is declared.** FR-002a is satisfied with no undeclared entry.

**No entry needed the `unclassified` sentinel** -- every capability was
classified on evidence read from its own manifest summary.

## Distribution

| `capability_owner` | Entries |
| --- | --- |
| `seshat-governance` | 50 |
| `seshat-orchestrator` | 15 |
| `seshat-authoring` | 12 |
| `seshat-adapter` | 9 |
| `seshat-domain-knowledge` | 7 |
| `specified-not-built` | 5 |
| `seshat-product-module` | 1 |
| `vendored-upstream` | 1 |
| `official-upstream` | 1 |
| `human-deliverable` | 1 |
