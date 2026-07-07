# Tasks: User workspace initializer (roadmap M3)

**Branch**: `feat/107-user-workspace-init` | **Spec**: `spec.md` | **Plan**: `plan.md`

**Status: BUILT.** Implemented 2026-07-07, TDD (RED -> GREEN), per an explicit build
instruction that superseded the spec's original HELD-for-owner-review status. This
record exists so the owner can review what was actually done, including a deliberate
deviation from `plan.md`'s proposed shape.

## Deviation from plan.md (owner-review item)

**All FRs are satisfied as written.** FR-002 says the workspace "MAY reuse
[`retail init`'s] `.seshat/` bootstrap internally" -- MAY, not MUST -- so the decision
below to NOT reuse it is fully compliant, not a spec violation. The actual deviation is
narrower: **plan.md step 1** (HELD/DRAFT, not itself a spec requirement) proposed
extracting `retail init`'s `.seshat/` bootstrap into a shared helper so `init-project`
could reuse it. **This was not done.** Before writing any test, a spike
(`PYTHONPATH=src python -m retail.cli check --repo <scratch-workspace>` against a real
isolated git repo, iterated in three shapes) established:

1. A workspace shape with `warehouse/{bronze,silver,gold}/`, `powerbi/`, `reports/`,
   `evidence/`, `mappings/`, `README.md` + subfolder READMEs, `.gitignore`,
   `.gitattributes`, `.env.example`, committed to git with >=2 commits, passes
   `retail check` with exit 0 -- PROVIDED `.seshat/` carries at most
   `.seshat/kit-source.yaml` and no `.seshat/compass.yaml`.
2. Calling `retail.kit_init.bootstrap()` (which writes `.seshat/compass.yaml` +
   projects the SESHAT-KIT fence) flips `retail.kit_lint.is_bootstrapped()` to `True`.
   That activates the KIT_SELF rule tier (`A1`, `A3`, `AP1`, `SC1`, `SC2`, `SF1`, `DF1`,
   `AQ1`, `DR1` -- see `src/retail/rules/*.py` `tier=RuleTier.KIT_SELF`), each of which
   requires one of the KIT's OWN internal manifests: `docs/routing/routes.yaml`,
   `docs/quality/status-claims.yaml`, `docs/quality/parked-on.yaml`,
   `docs/quality/rule-count-claims.yaml`, `docs/quality/shared-spine.yaml`,
   `docs/quality/design-stale-phrases.yaml`, a KPI domain corpus under
   `skills/retail-kpi-knowledge/domains/*.md`, and two anti-pattern-parity docs. A fresh
   user workspace has none of these and creating fabricated stand-ins would violate
   FR-004 ("no fabricated metric/readiness content") outright. This was confirmed
   experimentally: bootstrapping the spike workspace turned a clean exit-0 `retail
   check` into 10 ERROR findings (exit 1).
3. FR-006 ("the generated workspace passes `retail check` on creation") is listed under
   the task's **hard constraints, verify-before-done** section -- it is the harder,
   must-hold requirement versus plan.md's step 1 wording. Resolution: `init_project`
   does **not** call `kit_init.bootstrap()` and does **not** write
   `.seshat/compass.yaml` or project the SESHAT-KIT fence into any file. The generated
   workspace stays in the "drop-in tier" (a repo the kit was merely downloaded into,
   never bootstrapped) -- exactly the tier Spec A's KIT_SELF-skip design already
   handles, where those nine rules correctly emit `[info] ... skipped (kit-self rule;
   repo not kit-bootstrapped)` instead of erroring.

Consequence: there is no shared code between `retail init` (`src/retail/kit_init.py`,
`src/retail/cli/commands/init.py`) and `init-project`
(`src/retail/workspace_init.py`, `src/retail/cli/commands/init_project.py`) to extract
-- their outputs do not overlap (compass.yaml + SESHAT-KIT fences vs. the empty
workspace tree + `.gitignore`/`.gitattributes`/`.env.example`). `retail init` was left
completely untouched; its 16 existing tests (`tests/unit/test_cli_init.py`,
`tests/unit/test_kit_init.py`) pass unmodified.

**Owner should decide**: whether the workspace shape should eventually carry a real
`.seshat/` bootstrap once the KIT_SELF-manifest question is resolved for a
"foreign"/user repo (e.g. a lighter bootstrap tier), or whether staying
non-bootstrapped is the permanent intended behavior for `init-project`. Nothing here
forecloses that; it is what makes FR-006 pass today.

**Known consequence, out of M3 scope**: because no `.seshat/` directory is written at
all (not even a bare `kit-source.yaml`), a generated workspace cannot later run
`retail init` on itself -- `kit_init.bootstrap()` requires an existing
`.seshat/kit-source.yaml` to project from, and this task deliberately did not add one
(that would be scope creep beyond M3's "empty container only" -- adding kit substrate
is exactly the capability-verb-adjacent work M3 is scoped to exclude). Any milestone
that wants a generated workspace to later self-bootstrap will need to address this.

## Files created

- `src/retail/workspace_init.py` -- `init_project(name: str, force: bool = False) ->
  list[Path]`. Stdlib `pathlib` only. Resolves `name` against the CWD, refusing
  anything that resolves outside it (`ValueError`, path-traversal guard). Refuses a
  non-empty existing target without `force=True` (`FileExistsError`, writes nothing).
  Writes: `mappings/`, `warehouse/{bronze,silver,gold}/`, `powerbi/`, `reports/`,
  `evidence/` (each carrying a `.gitkeep` so the shape survives `git add` on an
  otherwise-empty dir), `README.md`, `warehouse/README.md`, `powerbi/README.md`,
  `.env.example` (parameter NAMES only, all credential fields empty), `.gitignore`,
  `.gitattributes`. Idempotent: re-running with the same inputs produces
  byte-identical output.
- `src/retail/cli/commands/init_project.py` -- `init_project_main(args) -> int`. Lazy
  imports `retail.workspace_init` (mirrors every sibling handler; keeps the
  stdlib-only `retail check` core import chain unaffected, rule B1). Maps
  `FileExistsError`/`ValueError` to a `[refused] ...` stderr line + exit 1; prints
  `wrote <path>` per written path + a next-step hint on success (exit 0).
- `tests/unit/test_workspace_init.py` -- 18 tests covering FR-001..FR-006 directly
  against `init_project`: fresh-scaffold shape, idempotent re-run (byte-identical, no
  duplicated `.env.example` keys), refuse-non-empty-without-force (and that `--force`
  never deletes an existing user file), path-traversal / outside-CWD guard (relative
  `../`, absolute-elsewhere, and the two allowed forms), no module-scope DB/network
  import, and two end-to-end `retail check` exit-0 assertions (one via a 2-commit
  history, one via `--commit-msg-file` to sidestep the `HEAD~1..HEAD` local-fallback
  range on a single-commit repo).
- `tests/unit/test_cli_init_project.py` -- 6 tests covering the CLI wiring: subcommand
  dispatch returns 0 and writes the shape, refuses a non-empty target without
  `--force`, `--force` scaffolds around existing files, the subparser exposes
  `name`/`--force` with the right defaults, no stdin read (no wizard), and the handler
  contract (`argparse.Namespace -> int`) directly.

## Files modified

- `src/retail/cli/parser.py` -- added the `init-project` subparser (positional `name`,
  `--force` flag) directly after the existing `init` subparser. Purely additive; every
  existing subparser's flags/help/order is untouched.
- `src/retail/cli/__init__.py` -- added one dispatch branch,
  `if args.command == "init-project": ... return init_project_main(args)`, directly
  after the existing `init` branch. Purely additive.
- `specs/107-user-workspace-init/spec.md` -- Status flipped from "DRAFT -- SPEC ONLY,
  NOT BUILT" to "BUILT"; added an owner-review flag noting the deviation above; updated
  the "Held-decision notes" section to point at this file.

## Verification (all green)

```
PYTHONPATH=src python -m pytest -m unit -q          # 1402 passed, 4 skipped, 8 deselected
PYTHONPATH=src python -m retail.cli check            # exit 0
PYTHONPATH=src python -m retail.cli semantic-check --repo .   # exit 0, "no drift"
PYTHONPATH=src python -m retail.cli kit-lint --repo .          # exit 0, "no projection drift"
ruff check src tests                                 # All checks passed!
ruff format --check src tests                        # 218 files already formatted
```

`retail init` regression: `tests/unit/test_cli_init.py` + `tests/unit/test_kit_init.py`
(16 tests) pass unmodified -- `src/retail/kit_init.py` and
`src/retail/cli/commands/init.py` were not touched.

## Out of scope (unchanged from spec.md)

No capability verb (source profiling, mapping, evidence) was added. No publishing /
distribution tooling was added. No `--repo` flag on `init-project` (the target is
always resolved relative to the CWD, matching "new user, empty folder" framing in the
spec's User Story 1 -- `retail init`'s `--repo` flag is a different command bootstrapping
an *existing* repo, not a precedent this command needed to copy).
