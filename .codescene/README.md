# CodeScene rules configuration

`code-health-rules.json` holds this repo's **scoped** exceptions to CodeScene's default
Code Health thresholds. JSON carries no comments, so every entry must be justified here.

Keep exceptions rare and narrow. Prefer fixing the code: on PR #659, four of five findings
turned out to be genuinely fixable once measured with the CLI, and only one needed an entry
below. A threshold override is the right tool only when the flagged shape is load-bearing —
when changing it would remove a property the code exists to guarantee.

Validate after any edit:

```bash
cs rules-config validate
cs check-rules <path>        # confirm which rule set a file matches
cs delta origin/main <branch>  # the measure the CI gate uses
```

## Entries

### `function_max_arguments` = 12 — `src/seshat/pbi_mcp_adapter/orchestrate.py`

**Added** 2026-08-19 (PR #659, F016 slice 5).

`orchestrate.apply_write` takes 12 keyword-only arguments against a default max of 4. That
signature **is** the CLI contract in `specs/149-pbi-mcp-write-adapter/contracts/cli-contract.md`,
and the explicit keyword form is load-bearing rather than untidy: each governed input
(`target_id`, `operation_id`, `timestamp`, `tree_clean`, `backup_ref`, `argv`, `config_state`,
`dry_run`) is visible at the call site in `cli/commands/pbi_mcp.py`.

`tests/unit/test_pbi_mcp_cli_contract.py::test_a_config_carrying_the_bypass_flag_refuses_apply`
exists because `config_state` was once accepted by `apply_write` but never supplied by the CLI —
a tested-but-unreachable branch that left a machine-local `.mcp.json` carrying
`--skipconfirmation` undetected on a write. Collapsing these keywords into a single request
object removes exactly the shape that made that gap visible, so the metric would be satisfied by
reintroducing the class of defect the test guards.

Measured alternatives before choosing this (all via `cs review`):

- Grouping the three test-injection knobs (`mcp_runner`, `validator`, `capability_profile`,
  none of which the production CLI passes) reaches **10** arguments — still over 4.
- Collapsing the governed keywords clears the finding but loses the call-site visibility above.

The function body is not the problem and is not exempted: `apply_write` is a 42-line façade
that bundles the request and delegates to `_run_pipeline`. Only the arity is excepted, only in
this file — `cs check-rules` on any sibling returns "No matching rule found".

**Retire this entry if** the CLI contract stops requiring the keywords to be individually
visible at the call site.
