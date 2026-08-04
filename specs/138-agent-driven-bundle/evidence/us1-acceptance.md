# US1 acceptance evidence — T021, T022, T023

**Captured:** 2026-08-03  
**Candidate:** local `studio` branch after `624a22b`  
**Authority:** evidence only; this record grants no approval and authorizes no
publication.

## T022 — optional MCP extra absent: PASS

A new virtual environment was created outside the development repository and the
base package was installed with `pip install -e .` — no optional extra. The
environment reported:

```text
mcp_present=False
```

The real installed console entry point was then invoked against an explicit Seshat
workspace:

```text
seshat mcp --repo <workspace>
```

It exited non-zero and emitted exactly the named two-lane recovery surface:

```text
error: MCP support is optional; install it with:
       pipx install:  pipx inject seshat-bi --force "mcp>=1.28,<2"
       pip install:   pip install "seshat-bi[mcp]"
```

There was no traceback, no simulated governor response, and no claim that the MCP
loop was available. This exercises `src/seshat/cli/__init__.py::_run_mcp` through
the installed command boundary rather than by monkeypatching an import.

## T023 — governor tool authority audit: PASS

`src/seshat/governor/mcp_server.py` registers exactly these six operations from
`src/seshat/governor/service.py::OPERATIONS`:

1. `seshat_get_status`
2. `seshat_get_next_action`
3. `seshat_explain_blockers`
4. `seshat_prepare_approval_request`
5. `seshat_run_static_check`
6. `seshat_export_evidence_pack`

All six receive MCP annotations `readOnlyHint=True`, `destructiveHint=False`,
`idempotentHint=True`, and `openWorldHint=False`. The adapter contains no mutating
operation; every call delegates to a `GovernorService` read.

The service audit confirms:

- status and next-action operations project committed state but do not advance it;
- approval preparation returns `status: prepared_not_approved`, an explicit
  authority disclaimer, and a blocked outcome — it records no receipt;
- the static check gathers findings in memory and labels live validation
  `not_run`; it does not write a readiness artifact;
- evidence export builds an in-memory response and does not write an export; and
- the common response is categorical (`ok`, `blocked`, or `input_defect`) and
  contains no readiness/confidence score field.

Verification executed on Python 3.13.14:

```text
pytest --no-cov -q tests/unit/test_agent_verify_*.py \
  tests/unit/test_governor_service.py \
  tests/contract/test_mcp_governor.py \
  tests/integration/test_governor_read_only.py \
  tests/integration/test_governor_stdio_no_deadlock.py
90 passed in 3.85s
```

The key byte-preservation integration test snapshots every file in a generated
workspace, calls all six operations, and confirms after each call that the snapshot
is unchanged and `.seshat-output` was not created.

## T021 — live harness acceptance: PARTIAL, remains open

Both committed bundles passed the credential-free structural validator with no
blockers. A standalone copy of the generated distribution was then installed into
fresh client profiles outside the development checkout and used from a workspace
created by `seshat init-project`.

Codex CLI `0.146.0`:

- local marketplace install: pass;
- plugin discovery: `seshat-bi`, version `0.8.1`, enabled;
- `codex mcp list`: `seshat-governor`, command `seshat mcp`, enabled;
- `codex mcp get seshat-governor --json`: pass, stdio transport confirmed; and
- live tool call: not run because the fresh profile does not inherit the existing
  ChatGPT subscription login. Copying a live authentication file into the scratch
  profile was rejected as an unsafe credential side effect.

Claude Code `2.1.220`:

- isolated local marketplace install and plugin discovery: pass;
- session-only `--plugin-dir` load from the standalone generated bundle: pass;
- runtime discovery: `plugin:seshat-bi:seshat-governor` present;
- `claude mcp list`: `Connected`;
- `claude mcp get plugin:seshat-bi:seshat-governor`: `Connected`; and
- external model-mediated tool call: not run. The execution boundary correctly
  required destination-specific authorization before sending workspace-derived
  status to the Claude subscription service.

The first Claude health attempt reported a closed connection. Systematic diagnosis
proved this was not a bundle or server defect: the acceptance virtual environment
had been moved after installation, and its Windows `seshat.exe` console wrapper
still embedded the old interpreter path. In that environment the wrapper exited 1
with no output while `python -m seshat.cli --version` passed. A clean MCP-enabled
environment created directly at its final path produced:

```text
seshat 0.8.1
wrapper_exit=0
initialize=pass protocol=2025-06-18
tools_list=6
tool_call=pass
probe=pass
```

The raw MCP probe ran from the generated scratch workspace and called
`seshat_get_status` successfully. It proves the server and workspace binding, but
is not substituted for the still-required harness-mediated call.

T021 requires a successful harness-mediated tool call on both clients. Registration,
health, and a direct MCP call are insufficient, so the task remains unchecked.
Completion now needs explicit authorization to send the fictional scratch
workspace's categorical status to each external subscription service during one
read-only acceptance turn. No credential was copied and no default profile was
changed during this run.
