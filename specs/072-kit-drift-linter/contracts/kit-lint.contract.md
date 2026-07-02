# Contract: `retail kit-lint`

The CI-runnable drift gate for the Compass-Driven kit. Defines what a CONSUMER (CI, a
maintainer) can rely on and what the PRODUCER (`kit_lint` + the CLI handler) guarantees.

## CLI

```bash
retail kit-lint [--repo PATH]
```

- Exit 0: no drift (or repo not bootstrapped — nothing to lint).
- Exit 1: at least one drift found, OR the source is unparseable/misshapen.
- Output: one line per check (pass/fail) + specific drift detail lines; a
  "not bootstrapped" note when `.seshat/` is absent.

## Producer guarantees (MUST)

- **P1 (two projection checks)**: runs YAML projection drift + prose projection drift.
- **P2 (reuse, no re-derivation)**: the checks call `compass_project.check_yaml_drift` /
  `check_prose_drift` — not a second copy.
- **P3 (read-only)**: writes nothing — no projection, source, or governed file is
  rewritten.
- **P4 (no score)**: emits explicit pass/fail + exit code; no numeric drift / health /
  confidence value.
- **P5 (specific detail)**: a failure names the drifted projection / file (actionable),
  not just "drift found"; a broken source is a named `source_parse` failure, not a
  traceback.
- **P6 (not-bootstrapped ≠ failure)**: absent `.seshat/` → exit 0 + a note.
- **P7 (boundary)**: not a `retail check` rule; adds no gate rule (count unchanged). MAY
  import pyyaml lazily; the `retail check` core stays stdlib-only.
- **P8 (no constitution read)**: reads only the kit source + its projections; never opens
  or interprets the constitution (the source-vs-constitution check was cut).

## Consumer guarantees (MAY rely on)

- **C1**: exit code is the authority — CI keys the build pass/fail off it.
- **C2**: a green `kit-lint` means the committed projections match the source — the
  compass is self-consistent with its single source. (It does NOT assert anything about
  the source vs the constitution — that check was cut; see the spec's scope-cut note.)
- **C3**: `kit-lint` reports drift; it does NOT fix it. Re-projecting is `retail init`.

## Anti-requirements (MUST NOT)

- MUST NOT parse, interpret, or even read the constitution.
- MUST NOT rewrite any file.
- MUST NOT emit a numeric score.
- MUST NOT be folded into the stdlib-only `retail check` core.
