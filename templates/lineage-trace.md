# Lineage / impact trace -- <starting-point>

<!--
  GENERIC TEMPLATE (roadmap rule 7). Copy this blank into
  mappings/<table>/lineage-column-<column>.md (column-rooted) or
  mappings/<table>/lineage-metric-<Metric>.md (metric-rooted) and fill the
  placeholders. Authored by the `cross-table-lineage` skill.

  C086 / retail_store_sales IS AN EXAMPLE, NEVER INLINED HERE. Do NOT copy any
  worked-example specifics into this file -- placeholders only
  (`<schema.table.column>`, `<Metric>`). ASCII, UTF-8 no BOM. Short paths
  (Windows 260-char budget).

  This is a GENERATED artifact: it reflects current committed repository text
  at generation time, and carries no memory of any prior run (see
  `generated_note` below). It is read-only apart from writing this one file --
  it never edits any artifact it cites.
-->

## Starting point

- kind: `<column | metric>`
- identifier: `<schema.table.column>` (column-rooted) OR
  `mappings/<table>/metrics/<Metric>.yaml` (metric-rooted)
- resolved: `<true | false>`
- resolution_blocker: `<null, or: name the missing source-map row / contract path>`

> If `resolved: false`, STOP here. No downstream chain is produced from an
> unresolved starting point (FR-015) -- the section below is omitted entirely,
> not filled with placeholders.

## Hops (fixed forward order; a metric-rooted run starts at hop 3)

Three evidence states only, non-overlapping:

- `proven` -- a committed artifact contains an EXPLICIT, machine-readable
  reference connecting this hop to its neighbor.
- `unresolved` -- committed artifacts exist on BOTH sides of the hop, but the
  link between them is not an explicit machine-readable reference (name-
  similarity alone never promotes a link to `proven` -- FR-010 is an OPEN
  owner ruling; until it is answered, every such link stays candidate-only).
- `gap` -- no committed artifact exists yet at this hop.

### Hop 1 -- source_map

- evidence_state: `<proven | unresolved | gap>`
- citation:
  - path: `<mappings/<table>/source-map.yaml, or null if gap>`
  - anchor: `<the column's source_name key, or null>`
  - quoted_reference: `<the literal column entry matched, or null>`
- note: `<required when evidence_state is gap -- name the missing artifact;
  optional otherwise>`

### Hop 2 -- migration_sql

- evidence_state: `<proven | unresolved | gap>`
- citation:
  - path: `<warehouse/migrations/*.sql, or null if gap>`
  - anchor: `<the SQL column identifier referenced, or null>`
  - quoted_reference: `<the literal SQL fragment matched, or null>`
- note: `<required when evidence_state is gap; optional otherwise>`

### Hop 3 -- metric_contract

- evidence_state: `<proven | unresolved | gap>`
- citation:
  - path: `<mappings/<table>/metrics/<Metric>.yaml, or null if gap>`
  - anchor: `<the contract's required-field key, or null>`
  - quoted_reference: `<the literal field/column name matched, or null>`
- note: `<required when evidence_state is gap; when unresolved, MUST say why
  this was not promoted to proven -- e.g. "contract field name does not
  textually match the gold column name; no explicit cross-reference exists;
  FR-010 has not authorized a promotion method">`

### Hop 4 -- tmdl_measure

- evidence_state: `<proven | unresolved | gap>`
- citation:
  - path: `<powerbi/*.SemanticModel/definition/tables/*.tmdl, or null if gap>`
  - anchor: `<the measure name, or null>`
  - quoted_reference: `<the literal DAX expression or comment matched, or null>`
- note: `<required when evidence_state is gap; when unresolved, MUST say why
  this was not promoted to proven>`

### Hop 5 -- dashboard_visual

- evidence_state: `<proven | unresolved | gap>`
- citation:
  - path: `<a filled templates/visual-contract-binding-map.md copy, or null if gap>`
  - anchor: `<the visual_id row, or null>`
  - quoted_reference: `<the bound_contract cell matched, or null>`
- note: `<required when evidence_state is gap -- e.g. "no filled binding map
  copy exists yet for this table"; optional otherwise>`

> Add or omit hop rows above as the starting point's natural entry hop
> dictates (a metric-rooted run has no Hop 1/Hop 2 rows of its own to report
> as its OWN starting evidence, but still traces backward far enough to cite
> the contract's upstream origin as proven/unresolved/gap per Hop 1/Hop 2).

## Downstream set (candidate list -- no obligation verb)

A plain restatement of which hops above are `proven`/`unresolved` downstream
of the starting point. Use only "is downstream of" / "cites" language.
NEVER use "must", "should", "needs to", or "requires re-review" here or
anywhere else in this artifact.

- `<hop_name>` -- `<evidence_state>` -- cites `<path>`
- `<hop_name>` -- `<evidence_state>` -- cites `<path>`

> Deciding what to re-review from this candidate list is a human/reviewer
> action -- or a separate drift-detector run -- taken OUTSIDE this artifact.
> This module supplies the candidate set only.

## Net-Sales consistency note (OPTIONAL -- fill only when applicable)

<!-- Delete this whole section when the starting point does not resolve to a
     Net-Sales-equivalent contract. When it does, state only that the hops
     above do not CONTRADICT the hand-authored trace's cited evidence --
     never restate or replace that trace, never claim a different gold table
     or TMDL measure than the trace already cites. -->

- net_sales_consistency_note: `<null, or a statement that these hops do not
  contradict docs/demo/net-sales-end-to-end-readiness-trace.md's cited
  evidence>`

## Generated-artifact note

- generated_note: "This artifact reflects the current committed state of the
  repository files it cites, generated at run time. It carries no memory of
  any prior run of this trace and makes no claim about what changed since a
  previous generation -- that comparison is a separate drift-detection
  concern, not this artifact's job."

## Boundary footer (fixed -- do not edit per-instance)

- No numeric blast-radius score, completeness count, or confidence/health/
  maturity value is computed or implied anywhere in this artifact.
- No verb of obligation ("must", "should", "needs to", "requires re-review")
  is applied to any downstream item.
- No readiness stage is moved, and no approval is granted or implied by this
  artifact.
- This artifact is read-only apart from writing itself: no source artifact it
  cites is modified, appended to, or reinterpreted.

<!--
  Forbidden fields (explicitly absent from this shape -- hard rule #9):
  no blast_radius_score, no confidence, no health, no maturity, no
  artifacts_affected_count, no priority, no risk_level, no
  recommended_action. A future filled copy of this template MUST NOT
  reintroduce any of these fields.
-->
