# Data Model: Seshat BI Public Beta Distribution

**Date**: 2026-07-13
**Purpose**: Define the release evidence, deterministic bundle, authorization, and rollback records used by the planned implementation.

This is a file-backed release model. It does not introduce a database or a second Seshat readiness engine. Release status is `state + evidence + blockers`; there is no release confidence score.

## Entity Relationships

```text
ReleaseVersion 1 ─────── 1 ReleaseCandidate
                              │
                ┌─────────────┼──────────────┐
                │             │              │
                ▼             ▼              ▼
       DistributionArtifact  GeneratedAgentBundle  ExternalAcceptanceRun
                                   │                        │
                                   ▼                        │
                         BundleManifestEntry                │
                                   ▲                        │
                                   │                        │
                    PublicKnowledgeAllowlistEntry           │
                                                            │
ReleaseCandidate 1 ─────── * PublicationApproval ◄──────────┘
         │
         └─────────────── * RollbackRecord
```

## ReleaseVersion

The one semantic version proposed for all governed surfaces.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `value` | SemVer string | yes | Canonical form without a leading `v`; no local version suffix. |
| `status` | enum | yes | `proposed`, `approved`, `superseded`; only a named owner may move to `approved`. |
| `source_revision` | full Git SHA | yes | Exact candidate revision. |
| `proposed_by` | string | yes | May be an agent or human; conveys no approval. |
| `approved_by` | named human | when approved | Must identify an eligible owner. |
| `approved_at` | UTC timestamp | when approved | Recorded with the owner decision. |
| `decision_evidence` | path/reference | when approved | Reviewable approval record bound to value and source. |

### Validation rules

- `v{value}` must not identify a different source revision in the repository.
- The value must be available for immutable package publication; an existing package file for the same value blocks reuse.
- Every governed projection must equal `value` before the candidate may be validated.
- `proposed` is never accepted as authorization for a tag, upload, release, or catalog submission.

## ReleaseCandidate

One immutable source revision plus all release artifacts and evidence.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `candidate_id` | string | yes | Stable identifier, e.g. `{version}+{short_sha}`. |
| `source_revision` | full Git SHA | yes | Must match `ReleaseVersion.source_revision`. |
| `version` | ReleaseVersion reference | yes | One-to-one. |
| `state` | enum | yes | `assembled`, `blocked`, `validated`, `partially_published`, `published`, `contained`. |
| `artifacts` | artifact references | yes | Wheel, sdist, Claude bundle, Codex bundle, and evidence manifest. |
| `audit_evidence` | reference list | yes | Registry, metadata, content, version, and documentation checks. |
| `acceptance_runs` | acceptance references | yes for validation | Python, Claude, and Codex external results. |
| `blocking_reasons` | concrete fact list | when blocked | No generic “needs work” reason. |
| `created_at` | UTC timestamp | yes | Evidence timestamp. |

### State transitions

```text
assembled ──failed check──> blocked
assembled ──all checks────> validated
blocked ───new candidate──> assembled
validated ─owner action───> partially_published
partially_published ──────> published
partially_published ─issue> contained
published ────────issue───> contained
```

- A corrected source revision creates a new candidate; it does not mutate old evidence into a pass.
- `validated` means repository and external acceptance evidence passed. It does not authorize publication.
- Surface-specific publication state is recorded separately so a partial launch cannot be described as complete.

## PublicKnowledgeAllowlistEntry

One explicit public source file and its permitted projections.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `entry_id` | string | yes | Stable unique identifier. |
| `source` | repository-relative POSIX path | yes | Literal file path; no glob, wildcard, absolute path, or traversal. |
| `classification` | enum | yes | Must be `public_knowledge`, `public_workflow`, `public_template`, or `public_metadata`. |
| `media_type` | enum | yes | Reviewed allowlist such as Markdown, YAML, JSON, or text. |
| `targets` | map | yes | Explicit Claude and/or Codex relative destination. |
| `transform` | enum | yes | Named deterministic transformation, commonly `copy-normalized-v1`. |
| `required` | boolean | yes | Missing required sources fail generation. |
| `generated_notice` | enum | yes | `comment`, `manifest_only`, or `not_supported`; never an ad hoc notice. |
| `review_reason` | string | yes | Why the file is needed by a public agent journey. |

### Validation rules

- Every source is a regular tracked file within the canonical repository.
- Every destination is within its declared bundle root and is unique per target.
- An allowlist entry cannot include `.env`, local settings, a cache, approval draft, real client material, or test output.
- All references reachable from an exported skill must themselves have explicit entries.
- A new canonical file is excluded until a reviewer adds a literal entry.

## GeneratedAgentBundle

A disposable platform-specific projection created from the same allowlist.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `target` | enum | yes | `claude` or `codex`. |
| `plugin_name` | string | yes | `seshat-bi`. |
| `version` | SemVer | yes | Must equal ReleaseVersion. |
| `root` | path | yes | Claude or Codex integration root. |
| `platform_schema` | string | yes | Reviewed manifest contract/version. |
| `source_revision` | full Git SHA | yes | Source used for export. |
| `exporter_version` | string | yes | Deterministic transform identifier. |
| `manifest_digest` | SHA-256 | yes | Digest of canonicalized bundle manifest. |
| `entries` | BundleManifestEntry list | yes | Complete output inventory. |

### Validation rules

- Repeated export for the same source/exporter produces the same paths and content digests.
- A bundle contains only reviewed platform templates plus mapped allowlist entries and its manifest.
- The plugin is self-contained and has no parent-path, machine-path, or development-checkout reference.
- Platform manifests are not interchangeable.

## BundleManifestEntry

One generated output file and provenance record.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `destination` | bundle-relative POSIX path | yes | Unique, normalized, no traversal. |
| `source` | repository-relative path or template ID | yes | Exact provenance. |
| `source_digest` | SHA-256 | yes | Digest after source normalization. |
| `output_digest` | SHA-256 | yes | Digest of written bytes. |
| `transform` | string | yes | Reviewed deterministic transform. |
| `classification` | enum | yes | Mirrors allowlist/template classification. |

Entries are sorted by `destination`. Timestamps, host names, absolute paths, and nondeterministic ordering are prohibited.

## DistributionArtifact

A candidate deliverable or evidence artifact.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `artifact_type` | enum | yes | `wheel`, `sdist`, `claude_bundle`, `codex_bundle`, `evidence_manifest`. |
| `filename` | string | yes | Versioned and platform-appropriate. |
| `version` | SemVer | yes | Must match ReleaseVersion. |
| `sha256` | digest | yes | Calculated after build/export. |
| `size_bytes` | integer | yes | Non-negative. |
| `source_revision` | full Git SHA | yes | Exact immutable source. |
| `contents_evidence` | reference | yes | Required/prohibited content result. |
| `metadata_evidence` | reference | yes | Schema/render/version result. |
| `validated` | boolean | yes | True only when all contract checks pass. |

The release workflow may publish only the exact wheel/sdist digests validated by the non-credentialed jobs.

## ExternalAcceptanceRun

One public-path test in a clean environment.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `run_id` | string | yes | Unique evidence identifier. |
| `surface` | enum | yes | `python`, `claude_code`, `codex_cli`, `codex_ide`. |
| `candidate_id` | reference | yes | Exact release candidate. |
| `product_version` | string | yes | Installed Seshat version. |
| `host_product_version` | string | for agents | Exact Claude Code/Codex version and surface. |
| `install_source` | string | yes | Public URL/index/repository and immutable ref. |
| `workspace_facts` | map | yes | Must record no dev checkout and whether `AGENTS.md` exists. |
| `fixture_digest` | SHA-256 | yes | Synthetic fixture identity. |
| `actions` | ordered list | yes | Install, discover, invoke, inspect, remove where applicable. |
| `outcome_class` | enum | yes | `next_action`, `stop_blocked`, or `failed`. |
| `gate` | string | when stopped | Named human/live/readiness gate. |
| `evidence` | reference list | yes | Sanitized logs/screenshots/structured results. |
| `blocking_reasons` | list | when failed/blocked unexpectedly | Concrete facts. |
| `recorded_at` | UTC timestamp | yes | Test time. |

Natural-language wording may differ across agents. The outcome class, earliest gate, prohibited-action checks, and evidence must agree.

## PublicationApproval

A named-human authorization for one exact irreversible action.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `approval_id` | string | yes | Unique decision record. |
| `candidate_id` | reference | yes | Exact immutable candidate. |
| `version` | SemVer | yes | Exact approved value. |
| `source_revision` | full Git SHA | yes | Exact lowercase source revision reviewed by the owner. |
| `artifact_digests` | map | yes | Exact SHA-256 artifact/bundle digests authorized for this action. |
| `action` | enum | yes | `create_release_tag`, `publish_pypi`, `publish_github_release`, `publish_claude_marketplace`, `submit_claude_catalog`, `submit_openai_plugin`, or a specific external configuration/rollback action. |
| `approver` | named human | yes | Eligible owner/publisher/reviewer for the action. |
| `approved_at` | UTC timestamp | yes | Decision time. |
| `expires_at` | UTC timestamp | yes | Later than `approved_at`; prevents indefinite reuse. |
| `evidence_reviewed` | references | yes | Candidate checks and surface acceptance. |
| `constraints` | list | yes | Scope, expiry, or staged-launch limitations. |
| `scope` | string | yes | Human-readable action boundary; never a wildcard release approval. |
| `status` | enum | yes | Must be `approved` for authorization use. |
| `authority_disclaimer` | string | yes | States that other actions and changed artifacts are not authorized. |

### Validation rules

- No wildcard action and no approval “for the release generally.”
- Candidate, version, full source revision, artifact digests, and action must match exactly at use time.
- Passing CI, an agent statement, merge approval, or a prior release approval cannot substitute.
- Approval for one catalog does not authorize another catalog or PyPI.

## RollbackRecord

One surface-specific containment and recovery record.

| Field | Type | Required | Rules |
|---|---|---:|---|
| `rollback_id` | string | yes | Unique. |
| `candidate_id` | reference | yes | Defective candidate. |
| `surface` | enum | yes | One of the five public surfaces; the action must match it. |
| `trigger` | string | yes | Reproducible defect/public verification failure. |
| `actor` | named human | yes | Owner performing the separately approved containment. |
| `action` | enum | yes | Surface-specific `rollback_*` action; no cross-surface reuse. |
| `status` | enum | yes | `blocked` or `completed`, with blockers consistent with status. |
| `blockers` | list | yes | Concrete facts when blocked; empty only when completed. |
| `recorded_at` | UTC timestamp | yes | Containment evidence time. |
| `approval_id` | reference | yes | Fresh action-scoped approval bound to the same candidate. |
| `public_status` | string | optional follow-up | Truthful availability after containment. |
| `replacement_version` | proposed SemVer | optional follow-up | Must differ when immutable artifacts were published. |
| `reverification` | acceptance reference | before replacement closure | Clean public-path result. |

A rollback record contains no implied approval for a replacement publication.

## Cross-Entity Invariants

1. One candidate has one version and one source revision.
2. All artifacts and acceptance runs reference that same candidate and version.
3. Every bundle file has provenance through a reviewed template or allowlist entry.
4. A candidate cannot be `validated` with a failed artifact, missing required acceptance surface, unresolved blocker, or version mismatch.
5. A validated candidate cannot perform an irreversible action without a matching `PublicationApproval`.
6. A published immutable artifact is never overwritten; correction creates a new version/candidate.
7. Registry/readiness evidence is never represented by a fabricated confidence number.
