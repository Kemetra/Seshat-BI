# Phase 1 Contract: CLI surface for the Power BI MCP write adapter (F016 slice 5)

**Feature**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md)

The external interface both operators and CI bind to. Contract-tested: the emitted commands
must be **executed** in tests, not string-matched (a shape assertion goes green while the
command is broken).

---

## Where it attaches

The existing closed vocabulary lives in `src/seshat/cli/parser_pbi_mcp.py`:

```python
commands = parser.add_subparsers(dest="pbi_mcp_cmd", required=True)
for add_parser in (
    _add_doctor_parser,
    _add_generate_config_parser,
    _add_preflight_parser,
):
```

Slice 5 **extends this closed list**; it does not create a new top-level verb. Two constraints
this file inherits and must not break:

1. **Lazy-import boundary** — "importing the root CLI never imports the pbi_mcp modules"
   (module docstring). The new legs stay lazy: the parser module remains stdlib-only and must
   not import the adapter package at registration time.
2. **Closed vocabulary** — a unit test keeps the registered command list in sync with its
   source of truth. Adding a leg means updating that test deliberately, not incidentally.

### A required string change (do not miss this)

The group's help text currently reads:

> "read-only Power BI MCP doctor family: doctor / generate-config / preflight (#450 slices 2-4;
> **F016 stays parked -- no mutation path exists here**)"

That claim becomes **false** the moment a write leg registers. The contract requires updating
it in the same change that adds the leg — a help string that misdescribes the tool's authority
is a governance defect, not a cosmetic one.

---

## New leg 1: `seshat pbi-mcp plan-write`

**Purpose**: a dry run. Evaluates the invariant and all four preconditions, reports exactly
what would happen, and **mutates nothing**. This is the leg an operator runs first and the
leg CI can run safely.

```text
seshat pbi-mcp plan-write --target <target-id> [--json]
```

| Argument | Required | Meaning |
|---|---|---|
| `--target` | yes | The declared target identity to evaluate. |
| `--json` | no | Machine-readable verdict for CI consumption. |

**Behavior**

- Runs the bypass-flag invariant check first (every mode).
- Evaluates the four preconditions and reports each individually — cleared or blocked, with
  the specific blocker named.
- Writes **no** evidence record and performs **no** mutation. It is an inspection.

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | All preconditions clear; a write would be attemptable. |
| `1` | One or more preconditions unmet (each named), or an invariant violation. |

---

## New leg 2: `seshat pbi-mcp apply`

**Purpose**: the armed exception. Applies an already-approved change, validates, and records.

```text
seshat pbi-mcp apply --target <target-id> --operation <op> \
                     [--backup-declared] [--json]
```

| Argument | Required | Meaning |
|---|---|---|
| `--target` | yes | The declared, allowlisted target. |
| `--operation` | yes | The already-approved operation. Never authored by this leg. |
| `--backup-declared` | no | Operator's explicit attestation that a backup exists (satisfies the git-safety precondition when the tree is not clean). |
| `--json` | no | Machine-readable result. |

**There is deliberately no `--force`, no `--yes`, and no `--skip-*` flag.** Adding one would
be a way to reach a write without the gate, which is the thing the feature exists to prevent.

**Behavior — the ordered pipeline**

1. **Invariant check** — bypass flag present anywhere (argv or resolved config) → refuse.
2. **Gate** — all four preconditions, fail-closed on unreadable state.
3. **Target resolution** — allowlisted and exists on disk, else refuse as undefined.
4. **Git safety** — clean tree or `--backup-declared`.
5. **Execute** — `npx`-invoked official MCP, `stdin=DEVNULL`, workload-sized timeout.
6. **Post-write validation** — `seshat check` R-family; binding validation when a report is in
   scope; value validation when an expected value exists and a data leg is available.
7. **Evidence** — one record, on success **and** on every failure path.

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | Applied **and** post-write validation passed. Evidence outcome `materialized`. |
| `1` | Refused before execution (invariant or precondition). Evidence outcome `blocked`. Nothing was mutated. |
| `2` | Executed, but post-write validation **failed**. Evidence outcome `failed`. Output carries rollback guidance. |
| `3` | Executed state indeterminate (runtime stalled or died mid-write). Evidence outcome `blocked`, with rollback guidance. |

**Why `2` and `3` are distinct**: exit `2` means "we know what happened and it is invalid";
exit `3` means "we do not know whether the artifact was modified". Collapsing them would let a
caller treat an indeterminate write as a clean failure. Both are blocking.

**Guarantees any caller may rely on**

- Exit `0` **never** implies an approval was granted or a stage advanced.
- Exit `1` guarantees **no mutation was attempted**.
- Every non-zero exit is blocking; none is a warning a script may ignore.
- No stdout/stderr output contains a host, tenant, credential, or user path.

---

## What the JSON verdict contains

```json
{
  "target": "<redacted target id>",
  "mode": "readonly | readwrite",
  "outcome": "materialized | failed | skipped | blocked | deferred",
  "authority": "<fixed label>",
  "blockers": ["<typed blocker id>", "..."],
  "validation": {"checks_run": ["..."], "failed": ["..."]},
  "rollback_guidance": "<string, present whenever validation failed>"
}
```

**Forbidden in this payload** (contract-tested):

- Any numeric, maturity, or confidence score — hard rule #9.
- The readiness token `pass` as an `outcome` value.
- Any field that reports or implies a readiness stage change.
- Any unredacted host, tenant, credential, or user path.

---

## Contract tests

| Test | What it pins |
|---|---|
| Closed-vocabulary sync | The registered command list matches its source of truth, deliberately updated. |
| Lazy-import boundary | Importing the root CLI does not import the adapter package. |
| Help-text truth | The group help no longer claims "no mutation path exists here". |
| Exit-code matrix | Each of `0/1/2/3` is reachable and produced by the intended cause. |
| No-escape-hatch | No `--force` / `--yes` / `--skip-*` flag is registered on either leg. |
| Executed-not-matched | The emitted commands are actually run in tests, not string-compared. |
| Refusal is total | On exit `1`, the target artifact is byte-identical to its pre-run state. |
| Score-free payload | The JSON carries no numeric score field. |
| Redaction | No sensitive token appears in stdout, stderr, or the JSON. |
