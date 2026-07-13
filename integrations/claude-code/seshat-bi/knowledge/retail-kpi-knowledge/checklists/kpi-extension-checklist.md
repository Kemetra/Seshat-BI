# Generic KPI Extension Checklist

Use this bounded checklist to propose one future generic KPI. It validates structure and
traceability only. It does not approve business meaning, publish a KPI, or grant
readiness.

- [ ] Confirm the request is a materially distinct business formula, not a slice by
  branch, product, category, channel, or another grouping dimension.
- [ ] Obtain the named-human review required for a new generic contribution; do not
  promote a project custom KPI automatically.
- [ ] Allocate one unused stable `KPI-MC-NN` id and one unique kebab-case slug.
- [ ] Add exactly one registry entry with every required field, lifecycle, logical
  concepts, decision types, source roles, and derivation references.
- [ ] Add a generic knowledge contract for a seeded KPI, or an explicit concrete
  blocker for a planned KPI; never invent an owner policy.
- [ ] Keep generic content free of project bindings, client names, raw PII, credentials,
  worked-example values, and named individuals.
- [ ] Reference only logical concepts and source roles; put physical bindings in the
  project metric contract after mapping and Gold validation.
- [ ] Update only consumer projections that need the new route: INDEX, packs, field
  requirements, aliases, and derivation lineage. Do not create a second registry.
- [ ] Add RED and GREEN fixtures for the registry and provenance consistency rules.
- [ ] Run the no-leak and secret scans, UTF-8-no-BOM and ASCII checks, `git diff --check`,
  focused tests, and `seshat check`.
