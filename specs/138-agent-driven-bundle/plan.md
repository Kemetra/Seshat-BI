# Implementation Plan: Agent-driven bundle completion

**Branch**: `138-agent-driven-bundle` | **Date**: 2026-07-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/138-agent-driven-bundle/spec.md`

**Status**: planning package authored, awaiting owner ratification — no
implementation started (spec FR-026).

## Summary

Complete the owner-ratified Option B (skill-driven packaging, 2026-07-07) that
specs 109–113 delivered docs-only. Two things reach the generated Claude Code and
Codex bundles that the compass already promises but the bundles omit: the
read-only agent governor, declared as a bundled server so the documented loop
works on install; and the skills themselves, shipped from a derived allowlist
rather than a hand-written six-name gate, behind a new fail-closed portability
transform.

The technical approach is **generation, not authoring**. Every artifact this
feature adds to a bundle is produced by `scripts/export_agent_bundles.py` from a
canonical source already in the tree. The one hand-authored change is repairing
`docs/capabilities/capabilities.yaml` so it can serve as that source, plus
rewriting 23 dev-only references inside canonical skill text.

## Technical Context

**Language/Version**: Python 3.13 (stdlib-only for the static core; the governor's
`mcp>=1.28,<2` stays an optional extra and is never imported on the check path)

**Primary Dependencies**: none added. The governor SDK is already an optional
extra; no story introduces a runtime dependency.

**Storage**: committed YAML/JSON/Markdown only. No database, no network.

**Testing**: pytest — `tests/contract/` for the surface/bundle reconciliations
(`test_generated_agent_bundles.py::test_committed_bundles_match_clean_regeneration`
is the acceptance evidence for FR-008), `tests/unit/` for the derivation and the
new portability transform.

**Target Platform**: Windows 11 + Python 3.13 is the release gate; macOS/Linux
best-effort beta, per the support matrix.

**Project Type**: distribution/packaging change to an existing CLI + agent-plugin
repository. No new component, no new service.

**Performance Goals**: not latency-bound. The one measured budget is the
per-session routing cost of the shipped skill listing (spec FR-021a / SC-010),
recorded before and after each payload story against a reviewed ceiling.

**Constraints**:
- Fail-closed everywhere: an unclassified skill, a missing bundle file, a
  dev-only path in a shipping skill, and a hand-edited generated allowlist must
  each fail the export or a contract test.
- Byte-identical regeneration is a hard acceptance condition for US2.
- Windows `MAX_PATH`: repo-relative paths stay `<= 200` chars (Constitution IX).
- No version value is touched by any story (FR-024a).

**Scale/Scope**: 5 stories; ~43 skills in each bundle at completion (from 11);
the per-file allowlist grows from 2,807 lines by generation, never by hand.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Bearing on this feature | Verdict |
|---|---|---|
| **I. Agent-First, Gate-Enforced** | This feature exists to make the agent-first interface actually reach an installed agent. Every new constraint is a machine check (export failure, contract test), not prose. The agent never judges its own compliance — `seshat check` and the contract suite do. | **Pass** — and directly advances the principle. |
| **II. Depend, Never Fork** | No skill is forked or duplicated into a bundle; every shipped file is generated from its single canonical source, and FR-006a makes a hand-edit of the generated allowlist a test failure. | **Pass** |
| **III. Medallion, Gold-Only** | Not engaged. No SQL, no schema, no Power BI binding. | **N/A** |
| **IV. Source Mapping Before Silver** | Not engaged directly, but FR-019 requires the mapping-gate hard stop to survive shipping unchanged — the gate must be as strong in a customer workspace as here. | **Pass** |
| **V. Agent Stops at Judgment Calls** | Reinforced twice: FR-011 forbids any bundled tool that grants an approval or advances a stage, and FR-024b forbids an agent selecting or ratifying a version. FR-026 blocks implementation until a named human ratifies this spec. | **Pass** |
| **VI. Defaults Then Deviations** | Not engaged (no table, no cleaning defaults). | **N/A** |
| **VII. C086 Is An Example** | Reinforced: the portability transform (FR-016/017) is precisely a check that shipped guidance carries no artifact of this development repository into a customer workspace. | **Pass** |
| **VIII. Static-First Governance** | Fully static. The portability audit and the derivation run over committed text with no database and no network. The governor extra stays lazily imported and off the check path. | **Pass** |
| **IX. Secrets and Reproducibility** | No secret is read or written. The bundled server declaration carries no credential. Generated output must stay UTF-8 without BOM and reproducible — byte-identical regeneration is the test. | **Pass** |
| **Readiness spine** | Untouched. No stage moves, no `readiness-status.yaml` is read or written, no new gate is added. | **Pass** |
| **Hard rule #9 (no fabricated score)** | SC-010 measures a size in tokens. It is explicitly recorded in the spec as a measurement, not a score, and nothing derives a confidence, health, or maturity value from it. | **Pass** |

**Result: no violations.** Complexity Tracking is therefore empty and omitted.

## Project Structure

### Documentation (this feature)

```text
specs/138-agent-driven-bundle/
├── spec.md              # feature specification (3 clarifications recorded)
├── plan.md              # this file
├── research.md          # Phase 0 output — 5 resolved unknowns
├── data-model.md        # Phase 1 output — entities and their invariants
├── quickstart.md        # Phase 1 output — how to verify each story
├── contracts/           # Phase 1 output — the three machine contracts
│   ├── ship-classification.md
│   ├── bundled-server-declaration.md
│   └── portability-audit.md
├── checklists/
│   └── requirements.md  # spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
docs/capabilities/
└── capabilities.yaml            # US2: repaired — gains the 6 knowledge roots,
                                 #      a skill_dir field, ships + classification

distribution/
├── public-knowledge-allowlist.yaml   # US2: becomes GENERATED, stays committed
├── public-command-surface.yaml       # US1: gains the bundled-server class
└── bundle-templates/
    ├── claude/.claude-plugin/plugin.json   # US1: server pointer
    ├── codex/.codex-plugin/plugin.json     # US1: server pointer
    └── shared/
        └── mcp.json                        # US1: new — one source, both harnesses

scripts/
└── export_agent_bundles.py      # US2: derivation replaces the six-name gate
                                 # US3: portability-audit-v1 transform added

.claude/skills/<verb>/SKILL.md   # US3: 23 dev-only references rewritten
skills/<knowledge>/              # unchanged — already shipping

integrations/
├── claude-code/seshat-bi/       # generated output (never hand-edited)
└── codex/seshat-bi/             # generated output (never hand-edited)

tests/
├── contract/
│   ├── test_generated_agent_bundles.py   # US2: byte-identical regeneration
│   ├── test_public_command_surface.py    # US1: class exemption
│   └── test_capability_inventory.py      # US2: new — inventory/allowlist agree
└── unit/
    └── test_portability_audit.py         # US3: new — transform behaviour
```

**Structure Decision**: no new package and no new top-level directory. This is a
change to three existing surfaces — the capability inventory, the export script,
and the bundle templates — plus rewrites inside existing canonical skill text.
Adding a module would create a second place where "what ships" is decided, which
is the exact defect being removed.

## Phase sequence and parallelism

```text
LANE α  (no dependencies)        LANE β  (dependency chain)
────────────────────────         ──────────────────────────
US1  bundled governor            US2  inventory repair + derived gate
     P1                               P2   ← zero payload change
                                           │
                                           ▼
                                 US3  ten compass verbs
                                      P3   ← portability transform
                                           │
                                           ▼
                                 US4  remaining consumer skills
                                      P4
          └──────────────┬────────────────┘
                         ▼
                  US5  re-acceptance + claims
                       P5
```

- **US1 is merge-safe alone and in any order.** It touches the command surface,
  the two plugin manifests, and a new shared server file — no file US2/US3/US4
  touch.
- **US3 and US4 must fail closed without US2**, not degrade. Their `ships` flags
  are meaningless to an export that still carries the six-name assertion, so the
  derivation must be present or the export must refuse.
- **US5 is a merge point.** It can only make truthful claims once contents are
  final, so it runs last regardless of lane completion order.
- **Only one story may be in implementation at a time across specs 137 and 138**
  (FR-026). Lane parallelism describes merge safety, not concurrent work.

## Sequencing risk and its mitigation

| Risk | Mitigation |
|---|---|
| The bundled-server assumption fails on one harness | It is the single external-sourced assumption in the spec and is re-confirmed in Phase 0 (research item R1) before any US1 work. A negative result re-scopes US1 rather than triggering a workaround. |
| The inventory repair silently changes bundle output | US2 lands with `ships: true` on only the existing six; `test_committed_bundles_match_clean_regeneration` must pass unchanged. A non-identical regeneration is a failed refactor, not a new baseline. |
| A `templates/` rewrite breaks dev-repo behaviour | FR-017 resolves per reference by intent. Each rewrite is verified in both contexts: the dev repo (behaviour unchanged) and a scaffolded workspace (path resolvable). |
| The routing-cost ceiling is exceeded at US4 | The measurement is taken per story (FR-021a), so the ceiling is hit at a known story with a known increment, not discovered at the end. Splitting the distribution stays available but explicitly deferred. |
| Bundle regeneration forgotten after a skills edit | Already enforced by the existing clean-regeneration contract test; the tasks phase must place regeneration inside every story that edits canonical skill text. |

## Complexity Tracking

Not required — the Constitution Check records no violations.
