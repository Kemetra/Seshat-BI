# Tasks: Agent-control status surface (roadmap M4, under Option B)

**Branch**: `feat/109-agent-control-status-surface` | **Spec**: `spec.md`

**Status: BUILT.** Implemented 2026-07-07, TDD (RED -> GREEN), per an explicit build
instruction that superseded the spec's original HELD-for-owner-review status. This
record exists so the owner can review what was actually done. All five FRs
(FR-001..FR-005) are satisfied as written; nothing out of scope was added -- no
`next-action`/`blockers`/`doctor --format json` verbs (those remain listed only as
"proposed" in `docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md`, not
built here).

## Approach

1. **RED first**: wrote `tests/unit/test_status_surface.py` (the pure projection) and
   `tests/unit/test_cli_status.py` (the CLI wrapper) against a module and a subcommand
   that did not yet exist -- confirmed `ModuleNotFoundError` / non-zero exit before any
   implementation.
2. **GREEN**: added `src/retail/status_surface.py`, `schemas/agent-status.schema.json`,
   `src/retail/cli/commands/status.py`, and wired `status` into the existing
   `_DISPATCH` table (`cli/__init__.py`) + `parser.py`.
3. **CodeScene delta check**: `analyze_change_set(base_ref="main")` initially flagged
   `_build_parser` as `degraded` (Large Method, 355 -> 356 LOC; already over its
   70-line threshold before this change, per the task brief's warning). Fixed by
   extracting four more subparser blocks (`check`, `validate`,
   `semantic-check`+`value-check`, `demo`) into named helper functions, mirroring the
   existing `_add_init_project_parser` pattern -- the same fix applied to `status`
   itself (`_add_status_parser`). Net effect: `_build_parser` shrank well below its
   prior size even with the new subcommand added. Re-ran `analyze_change_set` ->
   `quality_gates: "passed"`, zero findings. `main()` was never touched (it already
   dispatches through `_DISPATCH`, per the prior CodeScene split) and stays unflagged.

## Files created

- `src/retail/status_surface.py` -- `build_status_projection(repo_root: Path | str =
  ".") -> dict`. Stdlib-only at module scope (`yaml` imported lazily inside the
  function, B1/B3). Globs `mappings/*/readiness-status.yaml` under `repo_root`,
  projects each into `{table, source_path, current_stage, stages, blocking_reasons,
  next_action}` (stages keyed by name, each `{status, evidence, blocking_reasons}`).
  Read-only: no writes, no DB, no network. No new readiness logic -- every field is
  copied verbatim from the committed YAML; never derives, grants, or upgrades a stage.
  Never emits a numeric score. Best-effort: a malformed source file is skipped (not
  fatal) -- RS1 (`rules/readiness_status.py`) is the fail-loud static gate for that;
  this projection's job is to stay non-crashing for a polling host. Deterministic:
  results sorted by `source_path`. An absent/empty `mappings/` projects as
  `{"tables": []}`, never an error.
- `schemas/agent-status.schema.json` -- the committed JSON Schema (FR-002), the stable
  contract. Draft 2020-12. Defines `tableStatus` (required: `table`, `source_path`,
  `current_stage`, `stages`, `blocking_reasons`, `next_action`) and `stageStatus`
  (required: `status` restricted to the four enum values `not_started|blocked|
  warning|pass`, `evidence`, `blocking_reasons`). `additionalProperties: false`
  throughout so an accidental extra field (e.g. a fabricated score) fails schema
  validation, not just review.
- `src/retail/cli/commands/status.py` -- `status_main(args) -> int`. Mirrors
  `runner.run_json`'s style: `--format json` prints one `json.dumps(...)` document;
  `--format text` (default) renders a human-readable per-table status/evidence/
  blockers/next_action summary (never a score), matching `demo/report.py`'s posture.
  Exit 0 in every case -- an empty projection is success, not an error (FR-004).
- `tests/unit/test_status_surface.py` -- 11 tests against `build_status_projection`
  directly: empty-repo -> `{"tables": []}`; schema validation (empty AND populated,
  via a ~90-line stdlib-only mini JSON-Schema validator scoped to exactly this
  schema's constructs -- no `jsonschema` dependency exists in this repo's `dev` extra,
  and hardcoding expected keys in the test would make "validates against the
  committed schema" vacuous); per-table field projection (current_stage, evidence[],
  blocking_reasons[], next_action); deterministic sort order; no banned scoring term
  (`score`/`confidence`/`health`/`maturity`) anywhere in the output; malformed YAML is
  skipped, not fatal; missing `current_stage`/`next_action` project as `null`;
  determinism across repeated calls; read-only (no file created/modified/deleted).
- `tests/unit/test_cli_status.py` -- 8 tests against `retail.cli.main(["status",
  ...])`: empty-repo JSON exits 0; `--repo` default is `.` (matches every sibling
  subcommand's convention); populated JSON projection; text is the default format and
  is not raw JSON; text on an empty repo is non-error, non-silent; no scoring term in
  output; read-only; the JSON output is exactly one parseable document (mirrors
  `run_json`'s single-document contract).

## Files modified

- `src/retail/cli/parser.py` -- added `_add_status_parser` (mirrors
  `_add_init_project_parser`) and wired it into `_build_parser` right after
  `_add_init_project_parser(sub)`. Also extracted `_add_check_parser`,
  `_add_validate_parser`, `_add_semantic_and_value_check_parsers`, and
  `_add_demo_parser` out of `_build_parser` (the CodeScene Large-Method fix described
  above) -- every extracted block's flags/help/metavar/order is byte-for-byte
  unchanged; `retail --help`'s subcommand list and order is unchanged except for the
  new `status` entry appearing after `init-project` (its add-order position).
- `src/retail/cli/__init__.py` -- added one `_DISPATCH` row, `"status": _lazy(
  ".commands.status", "status_main")`, using the existing lazy-import factory (same
  pattern as `kit-lint`/`manifest`/`scaffold`/...). `main()` itself was not touched.
- `specs/109-agent-control-status-surface/spec.md` -- Status flipped from "DRAFT --
  SPEC ONLY, HELD" to "BUILT"; points at this file for the build record.

## Verification (all green)

```
python -m pytest -m unit -q                                    # 1420 passed, 4 skipped, 8 deselected
PYTHONPATH=src python -m retail.cli check                       # exit 0
PYTHONPATH=src python -m retail.cli semantic-check --repo .      # exit 0
PYTHONPATH=src python -m retail.cli kit-lint --repo .            # exit 0, "no projection drift"
PYTHONPATH=src python -m retail.cli status --format json         # exit 0, valid JSON, 2 committed tables projected
ruff check src tests                                             # All checks passed!
ruff format --check src tests                                    # 222 files already formatted
```

CodeScene `analyze_change_set(base_ref="main")`: `{"results": [], "quality_gates":
"passed"}` -- zero findings, no file degraded.

## Confirmed guarantees

- **Read-only**: no writes, no DB connection, no network call anywhere in
  `status_surface.py` or `cli/commands/status.py`; a dedicated test
  (`test_does_not_write_any_file` / `test_status_json_is_read_only`) asserts the
  repo-under-test's file set is byte-identical before/after a run.
- **No score**: every projected field is a categorical status string or a named
  evidence/blocker string; `score`/`confidence`/`health`/`maturity` never appear in
  output (asserted by test, and structurally impossible given the schema's
  `additionalProperties: false`).
- **Graceful-empty**: an absent or empty `mappings/` directory (a fresh repo) projects
  as `{"tables": []}` and exits 0 -- never an error. (This repo, on this branch,
  actually has two committed `mappings/*/readiness-status.yaml` fixtures already --
  `demo_sample_orders` and `retail_store_sales` -- so the live `retail status --format
  json` run exercises the POPULATED path; the empty-repo path is covered by the
  `tmp_path`-based unit tests instead.)
- **`main()` not degraded**: `main()` was not modified in this change; it already
  dispatches through `_DISPATCH` from the prior CodeScene hotspot split, and the
  CodeScene delta confirms zero degradation anywhere in the change set.

## Out of scope (unchanged from spec.md)

No `next-action`/`blockers` verbs; no `doctor --format json`; no
`seshat source profile`/`mapping review`/`evidence build` CLI verbs (specs 110-113
stay skill-driven per Option B); no write/mutate/approval-granting command.
