# DAX Calculation Groups and Precedence

> Diagnose supplied calculation-group metadata and measure behavior. Calculation groups transform
> measures; they do not authorize metric definitions, time policies, or display policies.

## Required evidence

- approved metric contract and base-measure definition;
- calculation groups, items, precedence values, expressions, format-string expressions;
- model compatibility/configuration relevant to calculation groups;
- active item selections and a reproducible query/visual context.

### DX-CG-001 -- SELECTEDMEASURE is the transformation input

A calculation item evaluates against the selected measure. Establish the base measure result before
attributing a defect to the calculation item.

### DX-CG-002 -- Precedence orders interacting groups

When multiple calculation groups apply, precedence controls transformation order. Record all
applicable groups and values; never infer order from display names or creation sequence.

### DX-CG-003 -- Equal or undocumented precedence is ambiguous evidence

If interacting groups have equal or missing precedence, return a blocked diagnostic until the
intended order is documented and tested.

### DX-CG-004 -- Selection expressions need multi/no-selection tests

Model behavior can differ when one, none, or multiple items are selected. Test the supplied
selection expressions and their fallback semantics rather than assuming a single selection.

### DX-CG-005 -- Dynamic format strings must preserve value type

A format-string expression changes presentation, not the numeric result. Converting the measure to
text inside the value expression breaks numeric behavior and should be diagnosed separately.

### DX-CG-006 -- Time transformations require date policy

Time-intelligence calculation items require the approved calendar/date role and comparable-period
policy. Stop if fiscal/calendar or incomplete-period policy is undecided.

### DX-CG-007 -- Scope guards prevent unintended measure transformation

Use supplied scope logic such as `ISSELECTEDMEASURE` only when the intended measure set is known.
An unguarded item can transform counts, ratios, or semi-additive measures incorrectly.

### DX-CG-008 -- Test composition, not items only in isolation

An item can pass alone and fail when composed with currency, time, scenario, or formatting groups.
Reconcile the supported combinations named by the contract.

## Diagnostic sequence

1. Establish the untransformed base-measure result and policy.
2. Inventory applicable groups, items, precedence, scope guards, and formats.
3. Evaluate each group alone, then in the supported combinations.
4. Test zero/one/multiple selection behavior.
5. Compare numeric result and format-string result separately.
6. Return `blocked` if order or time/display policy is not approved.
7. End on `../checklists/dax-diagnostic-checklist.md`.
