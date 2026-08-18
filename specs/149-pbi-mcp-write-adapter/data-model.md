# Phase 1 Data Model: Approval-Gated Power BI MCP Write Adapter (F016 slice 5)

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

All entities are `@dataclass(frozen=True)`. Nothing here writes to `approvals[]` or to any
readiness stage — the readiness records are **inputs**, and their fields are read verbatim.

---

## WriteRequest

An intent to mutate one declared target. Inert until every precondition clears.

| Field | Type | Notes |
|---|---|---|
| `target_id` | `str` | The declared artifact identity being mutated. |
| `mode` | `Literal["readonly", "readwrite"]` | **Defaults to `readonly`.** Never reaches `readwrite` by omission (FR-001, FR-003). |
| `operation` | `str` | The already-approved operation to execute. Never authored here (FR-011). |
| `backup_declared` | `bool` | Whether the operator explicitly declared a backup (feeds git safety). |

**Validation rules**

- `mode == "readwrite"` requires a cleared `GateVerdict`; constructing the request never
  clears it.
- An unrecognized `mode` is a refusal, not a coerced default.

---

## InvariantVerdict

The standing prohibition, evaluated **before any invocation, in every mode** (FR-002).

| Field | Type | Notes |
|---|---|---|
| `ok` | `bool` | `False` when a bypass flag is present anywhere. |
| `violation` | `str \| None` | Names where the flag was found (config vs. invocation). |

**Validation rules**

- Any occurrence of the confirmation-bypass flag (`--skipconfirmation`) in the invocation
  argv **or** in the resolved launcher config is `ok=False` — including read-only mode and
  including test fixtures.
- `--readwrite` present as a *default* (rather than an explicit opt-in) is also a violation.

**Why its own entity**: this is the one rule with no exceptions, so it is checked at a single
chokepoint (`invariants.py`) that no callsite can skip. Reviewers verify coverage by grepping
imports rather than auditing branches.

---

## GateVerdict

The four write preconditions, evaluated together. **Fail-closed.**

| Field | Type | Notes |
|---|---|---|
| `stage_pass` | `bool` | `semantic_model_ready == "pass"` for the target scope. |
| `stage_readable` | `bool` | `False` when state is absent, malformed, or unreadable. |
| `approval` | `Approval \| None` | The named-human `publish_ready` row (read verbatim). |
| `approval_names_target` | `bool` | Whether that row's note names **this** target. |
| `target_allowlisted` | `bool` | Target is in the declared allowlist. |
| `git_safe` | `bool` | Clean tree, or a declared backup. |
| `blockers` | `tuple[str, ...]` | Typed blocker identifiers, one per unmet precondition. |

**Validation rules**

- `cleared` is `True` **only** when all of: `stage_readable and stage_pass and approval is not
  None and approval_names_target and target_allowlisted and git_safe`.
- `stage_readable is False` → refusal. An unreadable gate is **never** a passing gate (FR-005).
- Every unmet precondition contributes a **distinct** blocker, so a refusal names the specific
  missing authority rather than a generic failure (FR-009).
- `blockers` non-empty ⇒ the outcome is blocking. There is no representation for a
  "warning-level" precondition failure — the type makes degradation unexpressible.

### The target-naming rule (research R3's open item, resolved)

`approval_names_target` is **not** a loose substring test. An approval note authorizes a
target only when the note contains the target's declared identity as a **whole token**
(delimited by start/end of string, whitespace, or punctuation) — so an approval naming
`sales_model` does not authorize `sales_model_v2`.

Rationale: a bare `in` check would let a loosely-worded note silently widen its own scope,
which is precisely the self-granted authority Principle V forbids. Two tests pin this: the
prefix case must refuse, and the exact-token case must clear.

---

## ResolvedTarget

| Field | Type | Notes |
|---|---|---|
| `target_id` | `str` | Declared identity. |
| `path` | `Path` | On-disk artifact location. |
| `exists` | `bool` | `False` → refusal as an undefined artifact (never invented). |
| `report_in_scope` | `bool` | Drives whether binding validation runs post-write. |

---

## RunEvidence

Derived proof of what ran. Emitted on **both** the success and failure paths (FR-015).

| Field | Type | Notes |
|---|---|---|
| `tool` | `str` | Which runtime was invoked. |
| `mode` | `str` | `readonly` / `readwrite` as actually used. |
| `target_id` | `str` | Redacted of any path-revealing component. |
| `timestamp` | `str` | Run time. |
| `outcome` | `str` | One of `materialized`, `failed`, `skipped`, `blocked`, `deferred` (research R1). |
| `authority` | `str` | **Fixed label.** Never computed, never elevated. |
| `blockers` | `tuple[str, ...]` | Typed; empty on a clean materialization. |

**Validation rules**

- `outcome` must be in the shipped five-value vocabulary and **MUST NOT** be the readiness
  token `pass` (hard rule #9).
- The record carries **no** numeric, maturity, or confidence field of any kind (FR-017). A
  test scans emitted records for numeric fields.
- Writing a record **never** mutates a stage or `approvals[]` (FR-018). A test compares stage
  state before and after every scenario.
- All string fields pass through redaction using the **derive-then-replace** pair from
  research R5 — never `replace_fragments` with a bare value.

**State transitions**

```text
requested ──(invariant violated)──────────────► refused        → evidence(blocked)
requested ──(gate not cleared)────────────────► refused        → evidence(blocked)
requested ──(cleared)──► armed ──► executed ──► validated      → evidence(materialized)
                                    │
                                    └────────► invalidated     → evidence(failed) + rollback
                                    │
                                    └────────► stalled/died    → evidence(blocked)  + rollback
                         armed ────────────────► not attempted → evidence(deferred)
```

Every terminal state emits exactly one evidence record — including the refusals. There is no
path that mutates and reports nothing.

---

## ValidationOutcome

Post-write verdict on touched artifacts. A failure **blocks** (FR-014).

| Field | Type | Notes |
|---|---|---|
| `checks_run` | `tuple[str, ...]` | Which validations executed. |
| `failed` | `tuple[str, ...]` | Empty on success. |
| `rollback_guidance` | `str \| None` | **Required** (non-empty) whenever `failed` is non-empty. |

**Validation rules**

- `failed` non-empty **and** `rollback_guidance` empty is an invalid state the constructor
  rejects — the guidance cannot be forgotten.
- Validation runs even when the runtime reported success but touched nothing; a no-op is
  reported honestly.

---

## RuntimeCapabilityProfile

What the detected preview server actually supports. Drift is a blocker (FR-019).

| Field | Type | Notes |
|---|---|---|
| `capabilities` | `tuple[str, ...]` | Detected at preflight. |
| `protocol_version` | `str \| None` | `None` when undetectable. |
| `supported_range` | `str` | From the compatibility record; legitimately `unknown`. |
| `drifted` | `bool` | `True` when detected ≠ supported. |

**Validation rules**

- `supported_range == "unknown"` is **never** treated as compatible (FR-020).
- `drifted is True` → blocker, not a warning.

---

## Relationships

```text
WriteRequest ──requires──► InvariantVerdict   (checked first, every mode)
             ──requires──► GateVerdict ──reads──► Approval, readiness stage (READ-ONLY)
             ──resolves──► ResolvedTarget ──against──► target allowlist
             ──executes─► runtime ──profiled by──► RuntimeCapabilityProfile
             ──produces─► ValidationOutcome ──feeds──► RunEvidence
             ──always───► RunEvidence  (both success and failure paths)
```

**The invariant the whole model enforces**: no arrow runs from `RunEvidence` back to a
readiness stage or to `approvals[]`. Tool success is evidence; approval is a named human's
recorded act. The type graph makes the forbidden edge absent rather than merely discouraged.
