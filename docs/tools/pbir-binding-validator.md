# PBIR binding validator — `seshat pbir-validate-bindings`

Offline, read-only resolution of every bound field reference in a report
against its semantic model — the pre-Desktop check that converts
"open Desktop → see error cards → guess which field → repeat" into one
deterministic command (issue #454).

```
seshat pbir-validate-bindings --report <path/to/X.Report> --model <path/to/X.SemanticModel>
```

No blueprint or binding map is required — unlike `pbir-validate-blueprint`,
this validator serves the common real-world case: a Desktop-owned report over a
Get-Data model, scaffolded outside the governed compiler.

## What it checks

The validator walks **every** JSON document under `<report>/definition/`
(visual.json, page.json, report.json, bookmarks) with one recursive walker —
queryState projections, filters, and sorts alike — and resolves each
`Column`/`Measure` field reference (`Entity` + `Property`, including
`From`-alias indirection used by filter expressions) against a symbol table
parsed from `<model>/definition/**/*.tmdl`.

| Finding | Class | Meaning |
|---|---|---|
| `unknown_entity` | blocked | the reference names a table the model doesn't have |
| `unresolved_field` | blocked | the property is neither a column nor a measure on its table; the message names the nearest model field — a governed rename / PII mask is the common cause |
| `unparseable_json` | blocked | a corrupt definition file (itself an error-card source) |
| `unreadable_source` | blocked | fail-closed guards: unreadable files, zero visuals under the report, or zero TMDL tables under the model |
| `unresolved_alias` | blocked | the reference sources its entity through a `From` alias no declaration in that document defines — Desktop shows an error card for it |
| `malformed_binding` | blocked | a `Column`/`Measure` wrapper is declared but cannot be classified (no string `Property`, no `Expression` object, no `SourceRef`, or a `SourceRef` naming neither `Entity` nor `Source`) |
| `unparseable_model_file` | blocked | a file under `definition/tables/` produced no table symbol, which would silently shrink the model symbol table |
| `projection_kind` | warning | a model **column** bound under a `Measure` wrapper (or vice versa) — renders by luck, semantically wrong (the detection side of #456) |

Resolution is **case-insensitive** (Power BI object names are);
`HierarchyLevel`/variation wrappers are out of scope for this increment.

A wrapper counts as a **declared binding** once it carries an `Expression` or a
`Property`: such a wrapper is always classified or blocked, never omitted. A
visual carrying no `Column`/`Measure` wrapper at all is intentionally unbound (a
card, shape, or text box) and stays silent — that is what keeps a `pass` with
"0 field references" honest rather than vacuous. Outside `definition/tables/`,
TMDL files that declare no table (`model.tmdl`, `relationships.tmdl`,
`expressions.tmdl`, `cultures/*.tmdl`) remain legal.

## Exit codes

- `0` — `pass`, or `warning` (kind mismatches only; the authoring fix for
  those lives in the generator, not the report)
- `1` — `blocked`: at least one unresolved binding or fail-closed guard

## Posture

Read-only. Writes nothing, never mutates the Decision Store, never sets a
readiness stage; the highest status it reports is `pass` on resolution, which
is evidence for a named human, never an approval. Never a silent "0 findings"
pass over empty inputs — pointing it at the wrong directory is an error, not a
clean run.
