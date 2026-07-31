# US5 — published claims measured against the new contents

**Captured**: 2026-07-31 | **Scope**: the 21-skill bundles produced by US2+US3
| **Runtime**: Windows + Python 3.13

US5's obligation is that no published claim outruns what was exercised. The
contents changed (11 -> 21 skills), so every earlier acceptance claim was
collected against different contents and none is carried forward.

## T068 / T069 — `seshat agent verify`

Both targets, against the regenerated bundles:

| Check | claude | codex |
|---|---|---|
| `no_silver_before_mapping` (hard stop) | PASS | PASS |
| `no_invented_metric_meaning` (hard stop) | PASS | PASS |
| `update_integrity` | PASS | PASS — 241 generated files match recorded `output_sha256` |
| `uninstall_integrity` | PASS | PASS |
| `version_compatibility` | BLOCKED | BLOCKED |
| `ide_surface` | UNAVAILABLE | n/a |

Both hard-stop scenarios reproduce with the expected `refuse`, naming the blocker
and offering the governed path instead — which is the property that matters for
shipping ten *gate-bearing* verbs.

**`version_compatibility` is BLOCKED for a pre-existing tooling reason, not a
content reason**: `version-compatibility audit surface is unavailable: No module
named 'scripts.check_release_versions'`. `scripts/` carries no `__init__.py`, so
that import cannot resolve; the only file this feature touched under `scripts/` is
`export_agent_bundles.py`. Recorded rather than worked around.

## T070 — external acceptance, credential-free path

`scripts/external_agent_acceptance.py --validate-bundle`:

```text
claude-code   status: pass   blockers: []
codex         status: pass   blockers: []
```

Both carry the tool's own `authority_disclaimer`: *"Validation does not authorize
publication."* The `--execute-cli` path is an explicit operator action requiring the
installed client and plugin in an isolated profile; it is **not** run here and
remains outstanding, exactly as the US1 harness runs do.

## T071 / T072 — docs corrected, no claim carried forward

- `docs/install/support-matrix.md` now states plainly that both bundles carry 21
  skills, that every acceptance claim in the table was collected against the earlier
  11-skill contents, and that **no row's behavior-validation claim covers the ten
  newly bundled verbs**. It records what *was* exercised and names the
  `version_compatibility` blocker as pre-existing.
- `docs/install/agent-install.md` now lists the ten verbs the bundles carry, states
  that each keeps its hard stops verbatim and self-grants nothing, and notes that
  bodies load on demand while only name+description is resident.

## T073 — no version moved, nothing published

- `pyproject.toml` remains `version = "0.7.1"`; `git diff` against the base shows
  **no change** to `pyproject.toml` or `CHANGELOG.md`.
- No tag points at this work, no release was created, and no catalog submission was
  performed (FR-024, FR-024a, FR-024b).

## What US5 cannot yet claim

External harness acceptance against the new contents. That needs the installed
clients on both harnesses and is an operator action, so it is reported as pending
rather than inferred from the credential-free validation above.
