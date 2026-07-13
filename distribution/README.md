# Public distribution source map

This directory contains the repository-owned inputs and sanitized fixtures for
Seshat BI public distribution. It does not authorize or perform a release.

## Canonical inputs

- `public-knowledge-allowlist.yaml` is the reviewed, literal-path publication
  policy. Globs, directory entries, traversal, and symlinks are forbidden.
- `bundle-templates/` contains platform-specific wrapper files and shared public
  operating text.
- `synthetic-retail/` is fictional acceptance input. It is not production data.

The canonical Knowledge Bases remain under `skills/`. Generated agent bundles
must never become a second authoring source.

## Generated outputs

- `integrations/claude-code/seshat-bi/` is the generated Claude Code plugin.
- `integrations/codex/seshat-bi/` is the generated Codex plugin.

Run `python scripts/export_agent_bundles.py --check` to detect drift, or run the
exporter without `--check` to regenerate both outputs deterministically. Every
generated bundle contains a provenance manifest with sorted file hashes. Edit
the canonical inputs or templates, never a generated file.

## Contributor workflow

1. Edit the canonical Knowledge Base under `skills/` or a reviewed wrapper under
   `distribution/bundle-templates/`.
2. If a public file/reference is new, add its exact path, media type, targets,
   transform, classification, and review reason to the allowlist. Never add a glob.
3. Run `python scripts/export_agent_bundles.py`.
4. Run `python scripts/export_agent_bundles.py --check` and the public distribution
   contract tests.
5. Review both manifest provenance sets and the generated diff in the same PR.

Direct edits under either generated integration root are rejected as drift. A
reviewed allowlist change classifies content for export; it does not authorize any
external publication.

## Evidence boundary

Only sanitized schemas, examples, and deterministic test evidence belong in
Git. Real marketplace profiles, tokens, build directories, external-agent
transcripts, and unsanitized acceptance evidence stay ignored. Evidence records
report status, facts, blockers, and named authority; they never report a
readiness or confidence score.
