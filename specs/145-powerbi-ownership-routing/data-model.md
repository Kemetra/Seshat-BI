# Data model: Power BI routing

## Routing decision

- `intent`: closed Power BI intent.
- `pre_gate`: readiness/approval fact required before execution.
- `executor`: Seshat bounded adapter or official Microsoft surface.
- `blocked`: categorical fail-closed result.
- `reason`: evidence-backed explanation.
- `post_validation`: Seshat validation/evidence action.

## New fact

`dashboard_ready` is target-scoped and true only when the governed readiness
artifact proves `dashboard_ready: pass`. Absence, malformed state, or another
status cannot authorize report authoring.
