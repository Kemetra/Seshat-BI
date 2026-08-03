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

- local marketplace install: pass;
- plugin discovery: `seshat-bi@seshat-bi-marketplace`, version `0.8.1`, enabled;
- MCP discovery: `plugin:seshat-bi:seshat-governor` present; and
- health/tool call: blocked because the fresh profile is not logged in. Claude
  reported `Not logged in · Please run /login`; the health surface therefore
  reported a closed connection and is not claimed as a pass.

T021 requires a successful runtime tool call on both harnesses. Discovery alone is
insufficient, so the task remains unchecked. Completion needs either an interactive
login in each isolated profile or explicit permission to install the standalone
plugin temporarily into each already-authenticated default profile. No credential
was copied and no default profile was changed during this run.
