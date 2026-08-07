# Research: Power BI ownership and routing

## Repository truth

- `powerbi-workflows-public-router` is the shipped broad public router.
- `powerbi-dashboard-design` is an internal design-only subrouter.
- `pbi-mcp-doctor` is the existing pure execution-owner recommender/preflight.
- PBIP inspection and readiness are Seshat governance responsibilities.
- Four PBIR commands are bounded, deterministic Seshat adapters that preserve
  bindings and do not publish.
- F016 remains parked and unassigned.

## Upstream truth

Microsoft separates local semantic-model modeling MCP, remote semantic-model
query MCP, and the first-party `powerbi-report-authoring` skill. The modeling MCP
does not therefore become the report-page authoring owner. The repository's
Fabric integration already declares the official report skill as required
payload, but activation/discovery proof belongs to Phase 6.

## Conclusion

No deletion is justified. The remaining delta is explicit intent selection,
readiness gating, hierarchy wording, and stale F016 correction.
