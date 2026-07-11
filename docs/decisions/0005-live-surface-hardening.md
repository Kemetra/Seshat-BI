# 0005 -- Live-surface hardening (first real-DB end-to-end exposed four tool defects)

- **Date:** 2026-06-25
- **Status:** Accepted
- **Context:** The kit is static-first (Principle VIII): `retail check` and the
  unit suite are CI-able with no database, and the LIVE surfaces -- `retail
  profile` (the mechanical profiler), `retail validate` (the four live checks),
  and the source-map -> validate-targets loader -- were unit-tested with scripted
  fake runners but **deferred** and never exercised against a real materialized
  Postgres until the first true end-to-end run (the `training` DB, the dirty
  Kaggle `retail_store_sales` CSV driven bronze -> silver -> gold -> validate ->
  semantic model, 2026-06-25). That run surfaced FOUR defects -- none caught by
  the green unit suite, because each only manifests against a real DB / real
  invocation. This ADR records the class of defect and the hardening, so the tool
  is robust for ANY data, not just this worked instance.

## The four defects (each fixed TDD on `feat/training-e2e-and-tool-maturity`)

| # | Defect | Why the unit suite missed it | Generalized prevention |
|---|--------|------------------------------|------------------------|
| 1 | `profile()` ran `trim()` on EVERY discovered column; crashed `btrim(timestamp with time zone) does not exist` on a `_loaded_at` TIMESTAMPTZ lineage column. | Fakes returned text-only columns; the live bronze carries a non-text lineage column. | Type-aware profiling: `_discover_columns` returns `(name, data_type)`; TEXT -> `''OR NULL`+trim (RC5), non-text -> plain `IS NULL`. A tool that applies a text-only function to auto-discovered columns MUST branch on type. |
| 2 | `python -m seshat.cli` was a silent no-op (no `__main__` guard) -- imported the module and exited 0 without running; `retail validate` "passed" while doing nothing. | Tests call `main()` directly; no test invoked the `-m` entry. | `if __name__ == "__main__": sys.exit(main())`. RULE: never accept a live-check exit 0 as a pass without its evidence (the "running live checks" banner + per-check result). An exit code is not proof a check ran. |
| 3 | `load_targets` qualified silver as `silver.<id>` but passed gold fact/dim names BARE; the check SQL uses them verbatim, so a bare `fct_sales` -> `UndefinedTable`. | The one fixture used qualified gold names; the real c086 map uses bare names. | `_gold_qualify`: a bare gold_star name -> `gold.<name>`; an already-qualified name untouched. A name read from an artifact and spliced into SQL MUST be schema-resolved at the read boundary. |
| 4 | `S1` (snake_case identifiers) scanned raw SQL lines and flagged a double-quoted phrase inside a `--` comment (e.g. a `"retail store sales"` comment) as a bad identifier. | Fixtures had no quoted prose in comments; S3/S5/S6/S7 already strip comments, S1 (older) did not. | `strip_sql_comments()` (preserves line numbers + quoted identifiers); S1 routes through it. RULE: any identifier/token rule MUST run over comment-stripped text. |

## Decision

1. **The live/profile/loader surfaces are hardened** as above (4 commits, each with
   a RED-then-GREEN regression test). The unit suite grew 250 -> 256.
2. **Exercising a live surface against a real DB is part of "done" for any feature
   that touches it** -- a green static suite is necessary, not sufficient (mirrors
   the F010 "green `retail check` is necessary-not-sufficient" property, now applied
   to the tool itself). The first table through a new live path is a deliberate test
   of that path, and defects it finds are deliverables.
3. **The canonical CLI entry is the `retail` console script**, not `python -m
   retail.cli`. Both now work, but the console script is the documented invocation;
   `.env` must be exported into the environment (the CLI does not auto-load it).
4. **Two robustness conventions are ratified for any source going forward:** (a)
   bronze lineage columns (`_source_file` TEXT, `_loaded_at` TIMESTAMPTZ) are
   first-class and the profiler tolerates them; (b) a filled `source-map.yaml`'s
   `gold_star` names may be bare OR schema-qualified -- the loader resolves both, and
   a star sharing the `gold` schema disambiguates with a suffixed qualified name
   (e.g. `gold.fct_sales_rss` alongside c086's `gold.fct_sales`).

## Consequences

- The tool is materially more robust for arbitrary retail data: a clean-ish CSV with
  a non-text lineage column, a second star in the shared `gold` schema, and quoted
  prose in migration comments all now flow through without a false failure or a
  silent no-op.
- The generalized RULES (type-branch auto-discovered columns; never bank a live exit
  code without its evidence; schema-resolve artifact names at the read boundary;
  comment-strip before token rules) are recorded in `docs/medallion-playbook.md`
  Appendix A (the reusable trap-checklist) so they apply to every future table.
- No new dependency, no new `retail check` rule (count stays 27); all fixes are
  stdlib edits guarded by tests.

## See also

- The worked instance that surfaced them: `mappings/retail_store_sales/` (the
  `training` DB end-to-end run); the cross-project log entries in
  `~/.claude/global-lessons.md` (2026-06-25).
- The static-first posture this hardens: `.specify/memory/constitution.md`
  Principle VIII; the live surface: `specs/004-retail-validate/spec.md`.
- The generalized traps: `docs/medallion-playbook.md` Appendix A.
