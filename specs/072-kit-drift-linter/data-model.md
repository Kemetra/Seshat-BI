# Phase 1 Data Model: Kit Projection-Drift Linter

Entities are in-memory value objects. `kit-lint` opens no DB and writes no files. (The
"correspondence table" from an earlier draft was CUT with the source-vs-constitution
check — see the spec's scope-cut note.)

## E1. `CheckResult` (immutable per-check outcome)

| Field | Type | Notes |
|-------|------|-------|
| `name` | str | which check (`yaml_projection`, `prose_projection`) or `source_parse` on a broken source |
| `ok` | bool | True = no drift |
| `details` | tuple[str, ...] | specific drift lines (which file / what mismatched); empty when ok (FR-008) |

**Invariants**: no numeric score field (FR-009) — pass/fail + specific detail lines only.

## E2. `LintReport` (aggregate)

| Field | Type | Notes |
|-------|------|-------|
| `results` | tuple[CheckResult, ...] | one per check run |
| `bootstrapped` | bool | False → not-bootstrapped case (E4) |

**Derived**:
- `ok` = `bootstrapped is False` (nothing to lint) OR all `results` ok. Maps to exit 0.
- A non-bootstrapped report carries a single informational note, no drift (FR-006).

## E3. Inputs (all EXISTING, read-only)

- `.seshat/kit-source.yaml` — the source (parsed via `compass_project.load_source`).
- `.seshat/compass.yaml` — YAML projection (checked byte-exact via
  `compass_project.check_yaml_drift`).
- `AGENTS.md` / `CLAUDE.md` `SESHAT-KIT` fenced bodies — prose projection (via
  `fence.read_fence_body` + `compass_project.check_prose_drift`).
- The constitution is NOT read at all (the source-vs-constitution check was cut, FR-010).

## E4. State: not-bootstrapped vs bootstrapped

```text
[no .seshat/ or no source]  --kit-lint-->  LintReport(bootstrapped=False, ok=True)  exit 0
[bootstrapped, all in sync] --kit-lint-->  LintReport(all results ok)               exit 0
[bootstrapped, any drift]   --kit-lint-->  LintReport(some result not ok)           exit 1
[bootstrapped, broken source] --kit-lint-> LintReport(source_parse not ok)          exit 1
```

No transition writes anything (read-only, FR-004).
