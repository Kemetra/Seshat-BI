# US5 — published claims measured against the new contents

**Captured**: 2026-07-31; refreshed 2026-08-03 | **Scope**: the 21-skill
bundles produced by US2+US3 | **Runtime**: Windows + Python 3.13.14

US5's obligation is that no published claim outruns what was exercised. The
contents changed (11 -> 21 skills), so every earlier acceptance claim was
collected against different contents and none is carried forward.

## T068 / T069 — `seshat agent verify`

Both targets, against the regenerated bundles:

| Check | claude | codex |
|---|---|---|
| `no_silver_before_mapping` (hard stop) | PASS | PASS |
| `no_invented_metric_meaning` (hard stop) | PASS | PASS |
| `update_integrity` | PASS — 266 generated files match recorded `output_sha256` | PASS — 242 generated files match recorded `output_sha256` |
| `uninstall_integrity` | PASS | PASS |
| `version_compatibility` | PASS | PASS |
| `ide_surface` | UNAVAILABLE — Claude declares no IDE surface | PASS |

Both hard-stop scenarios reproduce with the expected `refuse`, naming the blocker
and offering the governed path instead — which is the property that matters for
shipping ten *gate-bearing* verbs.

The earlier `version_compatibility` blocker exposed a real installed-package
boundary defect: the shipped check imported the development-only
`scripts.check_release_versions` module. Commit `624a22b` moved distribution
projection checks into shipped `seshat.release_versions` while leaving tag,
release-note, changelog and publication checks in the release-only script. The
fresh target runs above now pass that check from the installed package boundary.

## T070 — external acceptance, credential-free path

`scripts/external_agent_acceptance.py --validate-bundle`:

```text
claude-code   status: pass   blockers: []
codex         status: pass   blockers: []
```

Both carry the tool's own `authority_disclaimer`: *"Validation does not authorize
publication."* Three historical sanitized fixtures (Claude CLI, Codex CLI and
Codex IDE) also reclassify with no safety blockers, but each reports
`bundle_provenance_verified: false`; none is evidence for the current bundle.

A standalone copy of both generated bundles was installed into isolated client
profiles on 2026-08-03. Plugin and MCP list/get discovery passed on Codex; plugin
and server discovery passed on Claude, whose health call then stopped because the
fresh profile was not logged in. The `--execute-cli` path therefore remains
outstanding, exactly as the live US1 harness call does. See
`evidence/us1-acceptance.md`; discovery is not upgraded into a behavioral claim.

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

- `pyproject.toml` remains `version = "0.8.1"`; this story made no version change,
  and `git diff` against its implementation base shows
  **no change** to `pyproject.toml` or `CHANGELOG.md`.
- No tag points at this work, no release was created, and no catalog submission was
  performed (FR-024, FR-024a, FR-024b).

## What US5 cannot yet claim

External harness acceptance against the new contents. That needs the installed
clients on both harnesses and is an operator action, so it is reported as pending
rather than inferred from the credential-free validation above.
