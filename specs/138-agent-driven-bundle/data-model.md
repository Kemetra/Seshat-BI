# Phase 1 Data Model: Agent-driven bundle completion

**Feature**: 138-agent-driven-bundle | **Date**: 2026-07-31

Four entities. Three already exist and gain fields; one is new. No entity here
holds run state, readiness state, or any numeric score.

---

## 1. Capability entry *(existing — `docs/capabilities/capabilities.yaml`)*

One reviewed record of a thing Seshat BI can do. 93 entries today, 29 with a
skill surface.

**Existing fields**: `id`, `name`, `summary`, `state`, `authority`, `surface`,
`requirements`, `provenance`, `readiness_stage`, `command`, `documentation`,
`references`.

**Fields added by this feature** (skill-surface entries only):

| Field | Purpose | Validation |
|---|---|---|
| `skill_dir` | The directory the entry resolves to, when it differs from `id` | MUST name an existing directory. Required for the four entries whose id carries a `-skill` suffix; optional and defaulting to `id` elsewhere. |
| `ships` | Whether this skill reaches the public bundles | Boolean. No default — absence is an error, so a new skill cannot slip in unclassified. |
| `ship_classification` | Which authority placed it | One of `compass-verb`, `knowledge-root`, `consumer-capability`, `development-only`. |

**Repairs required before the field additions are meaningful**:
- Six entries MUST be added for the reviewed knowledge skills currently shipping
  and currently unlisted (`bi-sql-`, `bi-dax-`, `bi-python-`, `bi-bigdata-`,
  `retail-kpi-`, `bi-analyst-knowledge`), each with `ship_classification:
  knowledge-root` and `ships: true`.
- Four entries MUST gain `skill_dir` (`retail-govern-skill`,
  `run-next-readiness-skill`, `pbir-authoring-adapter-skill`,
  `speckit-workflow-skills`).

**Invariants**:
- Every skill-surface entry resolves to an existing directory.
- Every skill directory in the repository is covered by exactly one entry.
- `ship_classification: development-only` implies `ships: false`.
- `ship_classification: compass-verb` implies `ships: true` and implies the id or
  `skill_dir` appears in `.seshat/kit-source.yaml` verbs.

**Not held here**: no readiness state, no stage, no approval, no score.

---

## 2. Ship classification *(new — a value, not a file)*

The single input the export consults to decide whether a skill's files become
allowlist entries. It is a field on the capability entry, deliberately not a
separate registry, so there is exactly one place to look.

| Value | Meaning | Ships |
|---|---|---|
| `compass-verb` | Named in `.seshat/kit-source.yaml` as a verb the agent drives | yes |
| `knowledge-root` | A reviewed Knowledge Base the bundles already carry | yes |
| `consumer-capability` | Customer-facing, not on the compass verb list | yes |
| `development-only` | Exists to develop Seshat BI itself | no |

**State transitions**: a classification changes only by a reviewed edit to the
inventory. There is no runtime transition and no computed promotion — a skill
does not become shippable by passing a check.

---

## 3. Public knowledge allowlist *(existing — becomes generated)*

`distribution/public-knowledge-allowlist.yaml`, 2,807 lines today. Per **file**,
not per skill: each skill contributes an entry for every file it ships
(`SKILL.md`, `INDEX.md`, `README.md`, references).

**Existing entry shape**: `entry_id`, `source`, `classification`, `media_type`,
`targets.{claude,codex}`, `transform`, `required`, `generated_notice`,
`review_reason`.

**Change**: the file stops being hand-authored and becomes **generated from the
capability inventory**, while remaining committed and reviewed in the diff. Its
`policy.transforms` list gains `portability-audit-v1`. Its `canonical_roots` stops
being a hand-written six-name list and becomes the derived set.

**Invariants**:
- Regenerating from an unchanged inventory reproduces the file byte-for-byte.
- A hand-edit fails the reconciliation contract test rather than taking effect.
- `policy.absence_means_excluded: true` is preserved — the file stays
  fail-closed.

**Why it survives as an artifact**: the compact per-root diff is what a reviewer
reads to see what became shippable. Collapsing it into the 93-entry inventory
would remove that review surface (spec clarification Q1).

---

## 4. Bundled server declaration *(new)*

One shared source projected into both bundle roots, naming the read-only
governor as a component the harness starts when the plugin is enabled.

**Fields**: a server name, the command to run, and its arguments. No credential,
no path literal pointing into the plugin, and no environment secret.

**Invariants**:
- Declares exactly the six existing read-only tools' server and nothing else;
  this feature adds no tool.
- Carries no explicit repository path (research R2) — workspace resolution is by
  the CLI's existing default.
- Identical in both bundles apart from the harness-specific manifest key that
  references it.
- Exempt from the wrapper-template and knowledge-allowlist symmetry checks, by an
  exemption scoped to this artifact class alone (spec FR-013).

---

## 5. Portability finding *(new — transient, not stored)*

One instance of a shipping skill instructing an agent to read a path a scaffolded
workspace does not contain.

**Fields**: the skill, the offending path, the line, and the reason it failed.

**Lifecycle**: produced during export, reported, and never persisted. A finding
blocks the export; it is resolved by rewriting canonical text, never by recording
an exception. There is no findings file and no suppression list — a suppression
mechanism would recreate the silent-divergence failure FR-018 prohibits.

---

## Entity relationships

```text
.seshat/kit-source.yaml ──(verb ids)──▶ Capability entry ──(ships +
                                             │              classification)
                                             │
                                             ▼
                                   Public knowledge allowlist   (generated,
                                             │                   committed)
                                             ▼
                                   export_agent_bundles.py
                                             │
                          ┌──────────────────┴──────────────────┐
                          ▼                                     ▼
                 Portability finding                   Generated bundles
                 (blocks on failure)                    + Bundled server
                                                          declaration
```
