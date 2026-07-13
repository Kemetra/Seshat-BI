# Contract: Public Knowledge Allowlist

**Contract ID**: `PKA-1`
**Planned path**: `distribution/public-knowledge-allowlist.yaml`
**Requirements**: FR-013--FR-018, FR-042, SEC-001, SEC-005

## Purpose

Define the only canonical files that may be copied into a public Claude or Codex bundle. Absence means “do not publish.” Directory membership alone never grants publication permission.

## Required document shape

```yaml
schema_version: 1
canonical_repository: ahmed-shaaban-94/Seshat_BI
canonical_roots:
  - skills/bi-sql-knowledge/SKILL.md
  - skills/bi-dax-knowledge/SKILL.md
  - skills/bi-python-knowledge/SKILL.md
  - skills/bi-bigdata-knowledge/SKILL.md
  - skills/retail-kpi-knowledge/SKILL.md
entries:
  - entry_id: retail-kpi-skill
    source: skills/retail-kpi-knowledge/SKILL.md
    classification: public_knowledge
    media_type: text/markdown
    targets:
      claude: knowledge/retail-kpi-knowledge/SKILL.md
      codex: knowledge/retail-kpi-knowledge/SKILL.md
    transform: copy-normalized-v1
    required: true
    generated_notice: comment
    review_reason: Routes public agents to governed KPI semantics.
```

The example defines shape only. Implementation must enumerate every required transitive file literally after public-content review.

## Normative rules

1. `source` and each destination MUST be a repository-relative POSIX path.
2. Paths MUST NOT contain `..`, start with `/`, contain a drive prefix, or include `*`, `?`, or recursive globs.
3. Every source MUST resolve to one tracked regular file inside the repository; symlinks are rejected.
4. Every destination MUST stay within its target bundle and be unique.
5. All five canonical Knowledge Base entrypoints and every file they transitively reference MUST have explicit entries for each bundle that exports them.
6. A file added below a canonical directory is excluded until a reviewer adds its literal entry.
7. Generated-bundle templates MUST be listed separately with stable template IDs; they cannot masquerade as canonical knowledge.
8. The allowed media types are reviewed text formats only: Markdown, plain text, JSON, and YAML unless this contract is deliberately amended.
9. Executable files are prohibited except a separately reviewed platform script explicitly named by path, digest policy, and purpose. Public Beta's narrow default is no executable agent script.
10. The allowlist MUST exclude `.env`, secrets, tokens, DSNs, machine paths, local settings, caches, worktrees, generated test output, approval drafts, client data, real PII, and unreviewed binary assets.
11. Each entry MUST record why a public agent needs the file.
12. Entries and mappings MUST be serialized in stable order.

## Export validation

The exporter MUST fail before writing a release bundle when:

- an allowlisted source is missing, untracked, a symlink, or outside the repository;
- a source or destination path violates the path rules;
- destinations collide;
- a referenced file is not explicitly allowlisted;
- a secret/PII/client/path policy scan finds a prohibited value;
- an output file has no allowlist/template provenance;
- an allowlisted required source produces no output; or
- the existing committed bundle differs from a clean regeneration.

## Determinism and provenance

- Text line endings and final-newline policy are normalized by a named versioned transform.
- JSON/YAML generated metadata uses stable key/order/encoding rules; canonical knowledge content is not semantically rewritten.
- Each output manifest records source path, destination, source digest, output digest, transform, and classification.
- Timestamps, usernames, hostnames, temporary roots, and absolute paths MUST NOT appear in output or affect digests.
- Two exports from the same source revision and exporter version MUST have identical path sets and output digests.

## Acceptance examples

| Case | Expected result |
|---|---|
| New `skills/retail-kpi-knowledge/private-notes.md` is not listed | Excluded; drift/reachability check reports explicit review needed if referenced. |
| Entry uses `skills/**` | Reject allowlist. |
| Entry maps two sources to one destination | Reject allowlist. |
| Exported skill links to unlisted `../references/x.md` | Fail closed. |
| Generated file edited by hand | Regeneration drift fails and directs edit to canonical source/template. |
| Same clean source exported twice | Identical paths and SHA-256 digests. |

## Ownership boundary

Repository reviewers approve allowlist changes through normal review. That review classifies content as eligible for a future public bundle; it does not authorize a tag, upload, release, or public plugin submission.
