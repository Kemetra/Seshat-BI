# 0003 -- Per-table mapping-artifact location

- **Date:** 2026-06-24
- **Status:** Accepted
- **Context:** The source-mapping gate (constitution Principle IV) requires every table
  to be profiled and mapped into five committed artifacts **before** any `silver.*` SQL:
  `source-profile.md`, `source-map.yaml`, `assumptions.md`, `unresolved-questions.md`,
  `reconciliation-report.md` (the `templates/` blanks). Feature 001 deliberately left
  *where a table's filled copies live* open (research Q-2 / architecture open decision #2),
  because no table had run through the kit yet. The templates referenced this as an
  unresolved location. This ADR settles it.

## Decision

**Per-table mapping artifacts live in `mappings/<table>/`** -- a top-level directory, one
folder per source table, holding that table's five filled artifacts:

```
mappings/
`-- <table>/
    |-- source-profile.md
    |-- source-map.yaml
    |-- assumptions.md
    |-- unresolved-questions.md
    `-- reconciliation-report.md
```

`<table>` is the table id (e.g. the table's short code), `snake_case`, kept short for the
Windows MAX_PATH discipline (Principle IX). The `templates/` files remain the generic
blanks; a table's folder holds the filled copies.

## Rationale

- The five artifacts are a **cohesive per-table working set** -- the machine-and-human
  *inputs to a build* -- structurally parallel to `warehouse/migrations/`. A dedicated
  top-level dir makes the gate's inputs discoverable as a first-class thing.
- Keeps `warehouse/` **SQL-only** (the README scopes it "tool-agnostic SQL"); mapping
  prose/YAML does not belong in the migration tree.
- Keeps `docs/` for **finished design narrative** (specs, conventions, the C086 *worked
  example*, ADRs) -- not per-table working artifacts. The worked example in
  `docs/worked-examples/` *narrates* a filled set; `mappings/` *holds* one.
- One folder per table groups the set so the Phase-4 review gate reviews a table's mapping
  as a unit, and a reviewer finds everything for a table in one place.

## Alternatives rejected

- **`warehouse/<table>/` (beside the migration).** Co-locates artifact and SQL, but mixes
  prose/YAML into a tree the README defines as tool-agnostic SQL; blurs "inputs to the
  build" with "the build."
- **`docs/mappings/<table>/`.** No new top-level dir and matches where C086's worked
  example lives, but overloads `docs/` (finished narrative) with per-table working
  artifacts, and buries a first-class gate input inside the docs tree.
- **A single flat file per table** (one combined doc). Rejected: the five artifacts have
  distinct shapes (one is machine-readable YAML) and distinct review/fill cadences
  (profile first, reconciliation last/live).

## Consequence

- New top-level `mappings/` directory; `mappings/README.md` explains the per-table layout
  and points at `templates/` for the blanks and the worked example for a filled instance.
- The `templates/` files reference `mappings/<table>/` as the destination (the prior
  "location TBD / open decision #2" placeholders are replaced).
- The architecture doc's open decision #2 is marked RESOLVED; the README folder table adds
  `mappings/`.
- C086's artifacts are **not** retroactively created here -- C086 is the narrated worked
  example (`docs/worked-examples/c086-pharmacy.md`); the first table to *use* `mappings/`
  will be the next worked example. This ADR sets the convention, not a back-fill.
- Pairs with `docs/architecture/tower-bi-agent-kit.md` (Sec 5, the gate) and the
  constitution Principle IV. `retail validate`'s per-table target sourcing (feature 004,
  deferred) will read `mappings/<table>/source-map.yaml`.
