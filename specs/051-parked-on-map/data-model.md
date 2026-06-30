# Phase 1 Data Model: DF1 Parked-On Map

No database. The "data model" is the YAML manifest schema and the in-memory finding
shape. All paths are repo-relative strings resolved against `RuleContext.tracked_files`.

## Manifest: `docs/quality/parked-on.yaml`

```yaml
edges:
  - id: "<stable-edge-handle>"        # required; named in findings
    blocked: "<blocked target id/name>"   # required; the feature parked on the blocker
    parked_on: "<shared blocker id>"      # required; e.g. "F016"
    doc: "docs/roadmap/roadmap.md"        # required; the doc asserting the park (must be tracked)
    anchor: "<literal sentence in doc>"   # required; must be present byte-for-byte in `doc`
    evidence: "<tracked deferred-spec/spec path>"  # required; must be a tracked file
    shipped_when_tracked: "<artifact path>"        # OPTIONAL; if present in tracked set -> parked-but-shipped ERROR
```

### Field rules

| Field | Required | Constraint | Violation -> finding |
|---|---|---|---|
| `id` | yes | non-empty string | missing-field ERROR |
| `blocked` | yes | non-empty string | missing-field ERROR |
| `parked_on` | yes | non-empty string | missing-field ERROR |
| `doc` | yes | must be in `tracked_files` | untracked-doc ERROR |
| `anchor` | yes | literal substring of `doc` text | absent-anchor ERROR |
| `evidence` | yes | must be in `tracked_files` | unresolved-blocker ERROR |
| `shipped_when_tracked` | no | if present AND in `tracked_files` | parked-but-shipped ERROR |

`shipped_when_tracked` is the only optional field. Omitting it means "this park has no
machine-checkable ship-signal yet" -- the edge is reconciled on doc/anchor/evidence
only. Including it lets a future ship of the target be caught automatically: when that
artifact lands in the tracked set, the still-asserted park becomes a contradiction.

### Top-level shape

`edges:` MUST be a list. A mapping without an `edges` list -> wrong-shape ERROR. An
`edges:` value that is an empty list is VALID and passes clean (spec Q4) -- "nothing
parked-on declared yet" is honest, not a defect. A list entry that is not a mapping ->
not-a-mapping ERROR.

## Seeded v1 edges (the F016 bottleneck cluster, spec Q3)

Five edges, each `parked_on: "F016"`, `doc: "docs/roadmap/roadmap.md"`, citing the
tracked evidence verified in research.md:

1. `id: pbi-tools-extract` -> `evidence: docs/superpowers/specs/2026-06-26-pbi-tools-extract-spike-deferred.md`
2. `id: l3-new-operators` -> `evidence: docs/superpowers/specs/2026-06-26-l3-new-operators-deferred.md`
3. `id: f031-maintenance-policy` -> `evidence: specs/025-adapter-maintenance-policy/spec.md`
4. `id: f032-compatibility-matrix` -> `evidence: specs/026-adapter-compatibility-matrix/spec.md`
5. `id: f033-release-maturity` -> `evidence: specs/027-release-maturity-management/spec.md`

Each edge's `anchor` is a literal sentence from `docs/roadmap/roadmap.md` asserting the
park (selected at build time from the verified roadmap lines; must be byte-identical).
None declares `shipped_when_tracked` in v1 (all targets remain parked), so the seeded
manifest reconciles to zero findings (FR-013, SC-005). Generic kit features only -- no
C086/pharmacy facts (Principle VII).

## Finding shape (reused from `core.py`, no new type)

```python
Finding(
    rule_id="DF1",
    severity=Severity.ERROR,
    message="<edge id> <specific contradiction>",
    locator="docs/quality/parked-on.yaml:<edge id or index>",
)
```

One finding per defective edge (independent evaluation; one bad edge does not suppress
others). Manifest-level failures (missing/untracked/malformed/wrong-shape) emit a single
finding located at the manifest path.
