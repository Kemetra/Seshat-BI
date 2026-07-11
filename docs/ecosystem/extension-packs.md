# Extension Packs

Extension packs let contributors add **supported knowledge** to Seshat BI —
KPI templates, source vocabularies, warehouse-dialect notes, regional policy
guidance, accessibility checklists, dashboard blueprints — without touching
core code and without acquiring any authority the core does not already
grant to prose.

A pack is a directory holding one `seshat-pack.yaml` manifest plus the
declarative content files it declares. The manifest contract is published at
`schemas/seshat-extension-pack.schema.json`.

## Categories

| Category | What it contributes |
|----------|--------------------|
| `kpi` | Declarative KPI templates a team adapts into metric contracts. |
| `source_vocabulary` | Raw-header spellings with suggested canonical names. |
| `warehouse_compatibility` | Dialect renderings for the silver/gold SQL conventions. |
| `regional_policy` | Region-specific guidance (currency, fiscal calendar, privacy defaults). |
| `accessibility` | Design-review checklists and guidance. |
| `dashboard_blueprint` | Layout suggestions whose visual slots bind to approved contracts. |

## Trust boundary

Packs are **data and prose, never code**:

- Content files must be declarative (`.yaml`, `.yml`, `.md`, `.csv`, `.json`,
  `.txt`, `.svg`); executable artifacts and hook-style manifest keys are
  rejected.
- A pack cannot declare or reorder readiness stages, claim or grant approval
  authority, or claim a universal schema (Principle VII).
- Manifests are disclosure-scanned: secret material, connection strings, and
  PII-bearing fields are rejected.
- Loading is explicit: only manifests the user names are read. There is no
  directory discovery, no remote registry, and no install/activate state —
  a validated selection is an input to one projection, nothing more.
- The core operates identically with zero packs (FR-031).

## Authoring

```console
$ retail pack scaffold --id acme.retail-kpis --category kpi --owner "Casey Analyst"
written: packs/local/retail-kpis/seshat-pack.yaml
written: packs/local/retail-kpis/artifacts/kpi-template.yaml
written: packs/local/retail-kpis/fixtures/synthetic-example.csv
```

The scaffold validates cleanly out of the box; replace the starter content
and keep `retail pack validate` green. Pack ids are owner-qualified
lowercase namespaces (`acme.retail-kpis`); every provided id is qualified as
`<pack_id>:<local_id>`, so packs cannot collide through the namespace.

## Validating

```console
$ retail pack validate --repo . \
    --pack packs/reference/kpi-basic/seshat-pack.yaml \
    --pack packs/reference/accessibility-basic/seshat-pack.yaml
packs: seshat.reference.kpi-basic, seshat.reference.accessibility-basic
result: pass
```

Validation has two layers, both fail-closed:

1. **Per pack** — schema conformance, namespace discipline, declarative
   content, secrets, stage/authority/universal-claim rejection, artifact
   containment and existence, core compatibility.
2. **Selection graph** — duplicate ids, missing dependencies, dependency
   cycles, and declared conflicts, reported **before** any pack content
   contributes to a readiness output (FR-032).

Exit codes: `0` clean, `1` findings, `2` unreadable/schema-invalid manifest.

## Compatibility

`core_compatibility` declares the pack↔core contract line as `MAJOR.x` (or
`MAJOR.MINOR`). This core supports contract major `1`; any other major is
reported as `pack_incompatible_core` and the pack is not used.

## Reference packs

Three generic, synthetic reference packs demonstrate the full contributor
path (SC-006) without any client schema:

- `packs/reference/kpi-basic/` — KPI templates (net sales, AOV).
- `packs/reference/source-vocabulary-basic/` — retail raw-header vocabulary.
- `packs/reference/accessibility-basic/` — design-review checklists.

## Deferred: remote registry

There is no pack registry, download verb, or remote discovery. Distribution
is ordinary file sharing (git, archives); the explicit local path is the
only way a pack enters a validation or projection. A registry remains out of
scope until explicitly requested.
