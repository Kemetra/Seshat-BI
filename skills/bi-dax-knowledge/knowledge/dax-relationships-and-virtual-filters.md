# DAX Relationships and Virtual Filters

> Diagnose filter propagation only after the approved metric contract and model relationship
> metadata are available. This resource does not decide business meaning or alter the model.

## Required evidence

- metric contract: grain, additivity, filter behavior, and approved exclusions;
- table/column roles, relationship cardinality, direction, active state, and key uniqueness;
- measure DAX and the visual/filter context that reproduces the symptom;
- for virtual filters, source/target column types, lineage, and value-domain evidence.

If any business filter policy is undecided, stop and route it to the KPI owner. Do not treat a DAX
propagation technique as permission to define the metric.

### DX-REL-001 -- Draw every active filter path

Start from each slicer/axis table and trace active relationship paths to the measure's fact table.
Multiple valid paths can produce ambiguity or unexpected intersection.

### DX-REL-002 -- Cardinality is a correctness prerequisite

A many-to-one relationship assumes uniqueness on the one side. Verify it from model metadata and
data evidence; a declared relationship is not proof that the data obeys it.

### DX-REL-003 -- Direction is behavior, not business policy

Single- and bidirectional propagation describe model behavior. Whether a filter *should* affect a
metric comes from the approved contract.

### DX-REL-004 -- Bidirectional filters expand the reachable graph

Bidirectional relationships can create ambiguous paths and make unrelated slicers constrain one
another. Record the exact path; never recommend bidirectional filtering as a generic fix.

### DX-REL-005 -- Inactive relationships require explicit activation

`USERELATIONSHIP` activates a modeled path for one calculation. Confirm the contract selects that
date/key role and that no competing active path changes the intended intersection.

### DX-REL-006 -- CROSSFILTER is a scoped override

`CROSSFILTER` changes direction or disables a relationship for one calculation. Use it only when
the contract and model evidence justify the scoped behavior.

### DX-REL-007 -- TREATAS creates a virtual relationship

`TREATAS` applies a table of values to target column(s). Confirm compatible types, column order,
grain, and value domain. Missing target values are ignored, which may require reconciliation.

### DX-REL-008 -- Lineage affects propagation

Set operations and projections can preserve or lose lineage. Diagnose the table expression feeding
`TREATAS`; equal-looking values do not guarantee equivalent filter behavior.

### DX-REL-009 -- Composite virtual filters preserve tuple semantics

For multi-column `TREATAS`, source column order must match targets and tuples must represent the
intended key. Independent single-column filters can admit combinations that never existed.

### DX-REL-010 -- Reconcile the filtered population

End with population counts and control totals before/after the filter. A visually plausible result
does not prove correct propagation.

## Diagnostic sequence

1. Confirm the contract's filter policy and result grain.
2. Map active, inactive, and bidirectional paths.
3. Verify one-side keys and source/target data types.
4. Reproduce the filter context and isolate one path at a time.
5. For virtual filters, inspect lineage, tuple order, and unmatched values.
6. Reconcile population and amount controls.
7. End on `../checklists/dax-diagnostic-checklist.md`.
