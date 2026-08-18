# Phase 0 Research: Approval-Gated Power BI MCP Write Adapter (F016 slice 5)

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-08-18

Method: every question was answered by reading committed code, not by assuming from the ADR.
**Two of the plan's working assumptions were wrong and are corrected below** (R4, R5) — both
would have shipped as defects.

---

## R1 — The evidence status vocabulary is FIVE values, not four

**Decision**: reuse the shipped outcome vocabulary verbatim:
`materialized`, `failed`, `skipped`, `blocked`, `deferred`.

**Evidence**: `src/seshat/dagster_adapter/__init__.py:44`

```python
OUTCOMES: frozenset[str] = frozenset(
    {"materialized", "failed", "skipped", "blocked", "deferred"}
)
```

The comment above it states the governing constraint: *"NEVER the readiness token `pass`
(hard rule #9)."*

**Rationale**: the feature brief said "four-status vocabulary (materialized/failed/skipped/
blocked)". The shipped set includes a fifth, `deferred`, which this feature genuinely needs —
a write deliberately not attempted (slice-6 scope, or an unavailable data leg for
`value-check`) is `deferred`, semantically distinct from `blocked` (an authority refusal) and
`skipped` (an upstream stop). Adopting four would have forced one of those meanings onto the
wrong word.

**Alternatives considered**: define a fresh vocabulary for this adapter — rejected, it would
give the repo two evidence dialects and break reviewer intuition.

---

## R2 — The gate-reader pattern: read-only by contract, fail-closed by regex

**Decision**: mirror `src/seshat/dagster_adapter/gate.py` — a module exposing **no write
path**, returning frozen dataclasses, treating anything unparseable as MISSING.

**Evidence**: that module's docstring is explicit:

> READ-ONLY BY CONTRACT (FR-005): this module exposes no write path. … Writing any of those
> fields is a named-human action recorded by Core Authority — never by adapter code.

And on fail-closed parsing, it accepts two real committed phrasings of a gate line and then:
*"anything else stays MISSING (fail-closed)."*

**Rationale**: this is exactly our FR-005 (unreadable state must never read as passing). The
pattern is already proven against two divergent real-world phrasings, which is the failure
mode a hand-rolled parser would miss.

**Applied here**: `pbi_mcp_adapter/gate.py` exposes read-only accessors for
`semantic_model_ready` and the `publish_ready` approval row, and returns a typed
"missing/unreadable" state that the caller must treat as refusal.

---

## R3 — Approval lookup already exists and is target-agnostic

**Decision**: reuse the shipped `Approval` dataclass + `approval_for(stage)` accessor shape;
add **only** the target-name matching this feature needs.

**Evidence**: `src/seshat/dagster_adapter/gate.py`

- `class Approval` — "One named-human sign-off row from `approvals[]` — read verbatim."
- `publish_ready: str  # verbatim stage status, or "missing"`
- `def approval_for(self, stage: str) -> Approval | None`

**Rationale**: the existing reader finds *an* approval for a stage. ADR 0018 decision 2(b)
demands more — the approval's **note must name the intended target**. That matching is the
genuinely new logic and belongs in this feature; the row parsing does not.

**Gap this creates (a real risk, recorded)**: "the note names the target" needs a precise
matching rule, or it becomes a substring check that a loosely-worded note accidentally
satisfies. Deferred to the data model as an explicit validation rule rather than left to
implementer discretion.

---

## R4 — CORRECTION: do NOT route the runner through `gitutil.run_subprocess`

**Decision**: the MCP runner uses `subprocess` **with `stdin=subprocess.DEVNULL` and its own
workload-sized timeout constant** — following `dagster_adapter/runner.py`, *not*
`gitutil.run_subprocess`.

**Evidence**: `gitutil.run_subprocess`'s own docstring excludes exactly these callers:

> **Deliberately NOT routed through here** — the dbt/dagster execution runners
> (`dbt/gate.py`, `dbt/runner.py`, `dbt/scaffold/orchestrator.py`,
> `dagster_adapter/runner.py`, `cli/commands/dbt.py`). Those invoke user-authored builds that
> legitimately run longer than `SUBPROCESS_TIMEOUT`, so a shared cap would abort real work. …
> If any of them is ever exposed over stdio, give it `stdin=DEVNULL` and a timeout sized to
> that workload — do not adopt this helper's cap.

`dagster_adapter/runner.py:142` confirms the pattern in practice: `timeout=_RUN_TIMEOUT_SECONDS`.

**Rationale**: the plan's input said "all subprocess calls go through `gitutil.run_subprocess`
(known stdin-deadlock trap)". That over-generalized the real lesson. The deadlock fix (issue
#557) is **`stdin=DEVNULL`**, not that specific function; the function additionally imposes a
short shared cap intended for read-only governor tools. A Power BI model write is a
user-workload-length operation — adopting the governor cap would abort legitimate writes.

**What we keep from the lesson**: never call `subprocess` bare. `stdin=DEVNULL` is
load-bearing (a child inheriting a live JSON-RPC pipe deadlocks), and an explicit timeout
converts a stall into a typed `blocked` outcome rather than an unbounded hang.

**Alternatives considered**: raise `SUBPROCESS_TIMEOUT` globally so the shared helper fits —
rejected, it would weaken the deadlock protection for every read-only governor tool to
accommodate one long-running writer.

---

## R5 — CORRECTION: `redaction_core.replace_fragments` alone is NOT sufficient

**Decision**: redact in two steps — **derive** the scrubbable forms of each secret with
`conninfo_component_values()` / `uri_component_values()`, **then** pass those forms to
`replace_fragments()`. Never call `replace_fragments` with a raw secret value alone.

**Evidence**: `replace_fragments` is a blunt substring replacer:

```python
def replace_fragments(text: str, fragments: Iterable[str], token: str) -> str:
    """Replace every fragment in ``text`` with ``token`` (no-op when absent)."""
    for fragment in fragments:
        text = text.replace(fragment, token)
```

The span awareness lives in the *deriving* helpers, which handle "the whitespace-separated
`key=value` form, spaces around `=`" and "the host in its ORIGINAL case"
(`redaction_core.py:96, 301`).

**Rationale**: the function name suggests it is the redactor; it is only the applier. Feeding
it a bare value leaves the surrounding `key=` intact, which is the fragment-vs-span leak this
repo has already been bitten by. The derived-forms helpers exist precisely to close that gap.

**Applied here**: `pbi_mcp_adapter/evidence.py` redacts through the derive-then-replace pair,
and a dedicated test asserts no host/tenant/credential/user-path token survives into a
committed record — including the `key=value` span, not just the bare value.

---

## R6 — Vendor invocation shape

**Decision**: invoke the official server via `npx` as an external, unforked dependency; ship
no binary and add no Python dependency.

**Evidence**: ADR 0018 rejected alternatives — *"Vendor/fork the MCP runtime into the package.
Rejected: Principle II (external, unforked, independently upgradeable); also a 36MB+ preview
binary is not shippable payload."*

**Note on a stale contract line**: `templates/pbi-mcp-adapter-contract.md` still describes "a
local stdio process to the **vendored** Power BI Modeling MCP binary
(`tools/powerbi-modeling-mcp/`, gitignored)". That predates the ADR's vendoring rejection.
The ADR is the governing decision, so the plan follows `npx`. **Flagged for the owner** — the
contract template's wording should be reconciled, but editing a template that other features
bind to is out of this feature's scope.

---

## R7 — Testing without a live tenant

**Decision**: a stubbed runtime built from the **real** preflight artifact shape
(`.seshat/powerbi-mcp-preflight.json`, shipped by slice 4), not a hand-invented fixture.

**Rationale**: a fixture authored from imagination proves only that the code matches the
imagination — the circular-fixture trap. Deriving the stub from the artifact a real preflight
run already writes keeps the test anchored to observed reality.

**Constraint inherited**: the CI unit job runs without app extras, so any optional import is
guarded with `importorskip` — otherwise the guarding test *skips* in CI and green proves
nothing.

---

## Open items carried into the data model

1. **Target-name matching rule** (from R3) — how precisely must an approval note name a
   target? Becomes an explicit validation rule, not implementer discretion.
2. **Contract-template wording** (from R6) — `tools/powerbi-modeling-mcp/` vendoring language
   contradicts the ratified ADR. Owner-facing note; not edited here.
