# PR #659 — CodeScene Code Health disposition

**Branch**: `149-pbi-mcp-write-adapter` · **HEAD at analysis**: `7b647561` · **Date**: 2026-08-19

The `CodeScene Code Health Review (main)` delta gate is the last red check on PR #659.
Every other check passes. This records what was fixed in code and what needs an owner
decision, so the remaining items are a deliberate ruling rather than an unexplained red gate.

## Fixed in code (4 findings)

All behaviour-preserving. The 370 `pbi_mcp` unit tests are unchanged and green throughout;
the full unit suite is 5989 passed / 31 skipped.

| Finding | Function | Before | After | Commit |
| --- | --- | --- | --- | --- |
| Missing Arguments Abstractions | `orchestrate.py` module average | 5.14 | **2.90** (threshold 4.00) | `7f5bec5f`, `7b647561` |
| Large Method | `apply_write` | 81 lines | **42** (threshold 70) | `7f5bec5f` |
| Excess Number of Function Arguments | `_execute_and_confirm` | 8 args | **2** | `7f5bec5f` |
| Excess Number of Function Arguments | `_terminate` | 11 args | **3** | `7b647561` |

Method: bundle caller seams into frozen value objects (`evidence.RunIdentity` + new
`with_tool()`, `_Execution`, `_Ending`, `_WriteRequest`), then extract (`_run_pipeline`,
`_preflight`). **Extraction order matters** — a helper taking loose parameters adds to the
argument-count numerator and re-breaks the module average, so bundling has to come first.

`_Execution` deliberately carries **no defaults**: `mcp_runner`, `validator` and `terminal`
are injection seams, and a defaulted seam is how one goes quietly dead (this PR already
paid for that defect once — see `test_a_config_carrying_the_bypass_flag_refuses_apply`).

Also added `test_intent_record_exists_before_the_mutation_runs` (`c576e062`): the
intent-before-mutation guard had no test. It is pinned by **observation** — the stub runtime
reads the evidence file at the moment it mutates — and was proven non-vacuous by removing the
guard and watching it fail, before and after the refactor.

## Needs an owner decision (4 findings)

There is **no CodeScene rules-config file in this repo**, so none of these can be expressed
as a committed config change. Each is a suppression click in the CodeScene UI.

### 1. `apply_write` — 12 arguments (max 4) — RECOMMEND SUPPRESS

That signature *is* the CLI contract (`contracts/cli-contract.md`), and the keyword-only form
is load-bearing. `test_a_config_carrying_the_bypass_flag_refuses_apply` exists precisely
because `config_state` was once accepted but never supplied — a tested-but-unreachable
branch. Collapsing 12 keywords into one request object removes the shape that makes an
unsupplied parameter visible at the call site, reintroducing that class of defect to satisfy
a metric. The function body is already a 42-line façade; only the arity is flagged.

### 2. `GateVerdict.cleared` — cyclomatic complexity 13 (threshold 9) — RECOMMEND SUPPRESS, NEVER REFACTOR

This is the single most security-critical function in the feature: the only GO signal
("The ONLY GO signal. Every component must hold; never inferred."). It is a flat 13-term
`and`-chain, one precondition per line.

Cyclomatic 13 on a 13-precondition gate **is the correct number** — the property's value *is*
the branch count. Every decomposition that satisfies the threshold (e.g.
`_authority_holds() and _target_holds() and _git_holds()`) moves preconditions out of sight of
the one function a reviewer reads to answer "what clears this gate?" The flat chain is the most
auditable form available, and auditability is the point.

### 3. `gate.evaluate` — 5 arguments (max 4) — RECOMMEND SUPPRESS

Params: `repo_root, target_id, operation_id, tree_clean, backup_ref`. Bundling the last two
into a frozen `_GitState` would drop it to 4 and would *not* weaken the gate (the
`tree_clean is None` → refuse logic reads the field, not the parameter).

It is still the wrong trade: the gate's security tests express this precondition as
`tree_clean=…, backup_ref=…` keyword pairs across ~11 assertions in
`tests/unit/test_pbi_mcp_gate_safety.py`, including the critical `tree_clean=None` never-probed
refusal. Rewriting the security test surface to gain one argument buys nothing.

### 4. `_subparser_choices` (`tests/unit/test_pbi_mcp_cli_contract.py`) — nested depth 4 (threshold 4)

A test helper, exactly at threshold. Refactor-versus-rules-config for **test files** is an
owner-level policy call, not a per-PR one.

## Reading CodeScene threads on this PR

CodeScene posts only *new* findings per review; previously-unresolved ones persist without
reappearing. Several thread anchors point past current EOF because they were filed against
pre-refactor revisions. To get the true live set, filter unresolved threads by `createdAt`
**and** confirm each finding against the current code — the raw unresolved count is
misleading in both directions.
