# Contract: Reusable Change-Review Integration

## Inputs

- `repo`: checked-out repository root, default current workspace.
- `tables`: optional explicit table IDs; absent means all discovered readiness records.
- `seshat-version`: required immutable release selector in production examples.
- `sarif`: `auto`, `true`, or `false`; default `auto`.
- `fail-on`: default `error`; cannot be configured to ignore constitutional hard stops.

## Outputs

- Exit code: `0` only when selected gate policy has no blocking finding; `1` for findings;
  `2` for input/tool defects.
- Human job summary: checks, boundary, affected stages, blockers, next actions.
- `seshat-review.json`: stable schema-versioned review result and digest.
- `seshat-results.sarif`: optional SARIF 2.1.0 with rule IDs, severity, messages,
  repository-relative locations, and stable fingerprints.

SARIF upload failure cannot erase the JSON/job-summary result. The integration requests
read-only repository permissions by default and does not create PR comments.

## Digest

Digest input is the sorted normalized tuple of rule ID, severity, relative locator, stage,
message, blocker, and next action. Timestamps and source ordering are excluded. Identical
material results therefore have identical digests.
