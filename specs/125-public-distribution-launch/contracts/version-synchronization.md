# Contract: Version Synchronization

**Contract ID**: `VSC-1`
**Requirements**: FR-005, FR-030, FR-031, FR-046

## Purpose

Ensure one owner-approved semantic version identifies the Python package, both agent integrations, generated bundle evidence, changelog/release note, tag, and GitHub Release.

## Candidate source and approval

- `project.version` in `pyproject.toml` is the planned machine-readable candidate source.
- Before owner approval it is a proposal only.
- The owner decision binds the value to a full Git SHA and validated artifact digest set.
- A sync pass does not constitute approval.

## Governed projections

The implementation's version checker MUST resolve and compare at least:

| Surface | Planned source |
|---|---|
| Python package | `pyproject.toml` `project.version` |
| Built wheel/sdist | core metadata and filenames |
| Claude plugin | `integrations/claude-code/seshat-bi/.claude-plugin/plugin.json` |
| Claude root marketplace | `.claude-plugin/marketplace.json` plugin entry |
| Claude bundle evidence | Claude `bundle-manifest.json` |
| Codex plugin | `integrations/codex/seshat-bi/.codex-plugin/plugin.json` |
| Codex repository catalog | `.agents/plugins/marketplace.json` visible plugin metadata when schema provides a version field |
| Codex bundle evidence | Codex `bundle-manifest.json` |
| Changelog | exact `[{version}]` or `v{version}` release heading |
| Release note | `docs/releases/v{major}.{minor}.md` (or approved exact version path/heading) |
| Proposed tag | `v{version}` |
| Proposed GitHub Release | `v{version}` title/tag target |

If the current official platform schema does not permit a version field in one catalog, that projection is marked `not_schema_supported` with evidence; version MUST NOT be hidden in an unsupported field.

## Rules

1. Values compare as exact normalized SemVer strings without leading `v`; tag/release projections add one leading `v` only.
2. No independent hard-coded fallback version is allowed.
3. Bundle generation reads the candidate source and writes both bundle manifests deterministically.
4. Release notes and changelog MUST describe actual surface availability and existing tag history truthfully.
5. An existing `v{version}` tag at another revision is a blocker; the checker never moves or deletes it.
6. An already-published immutable package version is a blocker; replacement requires a new version.
7. The current `v0.1.0` tag and publication-history wording must be reconciled before a Public Beta value is approved.
8. Passing synchronization does not authorize tagging or publication.

## Checker output contract

The planned checker returns:

```json
{
  "status": "pass | blocked",
  "candidate_version": "0.2.0",
  "source_revision": "<full-sha>",
  "projections": [
    {
      "surface": "claude_plugin",
      "path": "integrations/claude-code/seshat-bi/.claude-plugin/plugin.json",
      "observed": "0.2.0",
      "expected": "0.2.0",
      "status": "pass"
    }
  ],
  "blocking_reasons": []
}
```

The example value is illustrative, not ratified. Output is sorted by surface/path, contains concrete mismatches, and contains no score.

## Release workflow use

- Run before building.
- Run against built artifact metadata.
- Run before entering any credential-bearing job.
- Re-run from the exact tag revision before owner approval is consumed.
- Save sanitized output with the candidate evidence.

Any missing governed location, ambiguous version, mismatched value, or conflicting immutable version blocks publication.
