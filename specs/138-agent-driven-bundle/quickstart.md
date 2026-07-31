# Quickstart: verifying Agent-driven bundle completion

**Feature**: 138-agent-driven-bundle | **Date**: 2026-07-31

How to verify each story independently. Nothing here requires a database, a
network call, or Power BI. Commands are PowerShell, run from the repository root
unless stated otherwise.

> **Nothing in this file may be run as implementation.** The spec's FR-026 blocks
> implementation until a named human ratifies. These are the verification steps
> for when it is.

---

## Before anything: the baseline must be green

```powershell
seshat check
seshat kit-lint
seshat doctor
```

Expected today: `kit-lint` reports no projection drift, `doctor` reports no
drift, and `check` reports only the pre-existing `RS1` warning about
`mappings/retail_store_sales/readiness-status.yaml`. Any *other* finding is
pre-existing damage to fix before starting, not something this feature caused.

---

## US1 — The governed loop works on install

**First, close research R1 and R2 — before writing anything.**

1. Confirm each harness starts a plugin-declared server, at the exact harness
   versions the support matrix names.
2. Confirm the working directory such a server starts in. The governor defaults
   its repository to `.`; if a harness starts servers in the plugin directory
   instead of the workspace, this story is re-scoped, not worked around.

A negative result on either is a **stop**, reported to the owner.

**Then verify:**

```powershell
# In a scratch workspace that is NOT this repository:
seshat init-project loop-check
# install the plugin on each harness, start a session, and confirm:
#   - the six read-only governor tools are present with no manual registration
#   - the governor reports on the SCRATCH workspace, not the plugin directory
```

Then remove the optional extra and repeat. Expected: a named instruction naming
what to install, no simulated governor answer, and no claim that the loop is
available.

**Acceptance**: no tool in the enabled set advances a stage, grants an approval,
writes a readiness artifact, or emits a score.

---

## US2 — Inventory and gate tell one truth

This story's whole acceptance is that **nothing changes in the output**.

```powershell
# after repairing the inventory and replacing the six-name gate,
# with ships:true on ONLY the six knowledge roots:
python scripts/export_agent_bundles.py --repo .
git diff --stat integrations/
```

**Expected: empty.** A non-empty diff means the refactor changed behaviour and is
a failure, not a new baseline.

```powershell
python -m pytest tests/contract/test_generated_agent_bundles.py -q
python -m seshat.capability_inventory --format json    # every skill entry resolves
```

Then prove the gate is still fail-closed — each of these must **fail**:

- an inventory entry marked shipping whose directory does not exist,
- a skill directory covered by no inventory entry,
- a hand-edit to the generated allowlist.

---

## US3 — The ten compass verbs are loadable

```powershell
# the portability transform must reject before it permits:
python scripts/export_agent_bundles.py --repo .   # expect failures naming
                                                  # skill + path, 23 to resolve
```

Resolve each by rewriting canonical text, then verify **both** contexts for every
rewrite:

- in this repository, the skill's behaviour is unchanged;
- in a scaffolded workspace, every path it tells the agent to read resolves.

Then, in a workspace with no Seshat development checkout:

```powershell
# install the plugin, start a session, and for each verb the compass names,
# confirm the skill loads:
#   retail-orchestrate, first-hour-compass, retail-onboard-table,
#   retail-discover-portfolio, business-knowledge-interview, source-mapping,
#   kpi-contract-builder, retail-build-warehouse, retail-validate, retail-govern
```

**Acceptance**: ten of ten load, and every hard stop observable here is
observable there. A shipped skill that reaches a judgment call still stops.

---

## US4 — Remaining consumer capabilities ship

```powershell
python scripts/export_agent_bundles.py --repo .
```

Then confirm in a fresh workspace that every consumer skill is present and that
no development-only or specification-workflow skill is — and that the absence is
caused by the recorded classification, not by a name pattern. Test this by
temporarily classifying a development-only skill as consumer-facing and
confirming it *would* ship; revert immediately.

**Routing-cost gate** (FR-021a): record the measurement before and after this
story and confirm it stays at or under the reviewed ceiling. Exceeding it fails —
it does not pass with a note.

---

## US5 — Published claims match the artifact

```powershell
seshat agent verify --target claude
seshat agent verify --target codex
python scripts/external_agent_acceptance.py --help   # then capture per its contract
```

Then confirm every changed row of `docs/install/support-matrix.md` and every list
in `docs/install/agent-install.md` is reproducible from that captured evidence,
and that no row carries an older acceptance claim forward as though it covered
the new contents.

**Out of scope, and must remain untouched**: any catalog submission, any version
value, any tag, any release.

---

## Whole-feature regression

```powershell
python scripts/export_agent_bundles.py --repo .
git status --porcelain          # generated output committed, nothing stray
seshat check ; seshat kit-lint ; seshat doctor
python -m pytest tests/contract -q
```

Run `analyze_change_set` before pushing — a required delta code-health check
fails PRs on newly-introduced smells even when every GitHub job is green.
