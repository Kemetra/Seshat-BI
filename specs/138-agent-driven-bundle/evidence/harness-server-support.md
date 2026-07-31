# US1 blocking research — T007, T008, T009

**Captured**: 2026-07-31 | **Machine**: Windows 11 Pro 10.0.22631
**Harness versions exercised**: `codex-cli 0.146.0`, `claude 2.1.220 (Claude Code)`

Verified **at the runtime**, via each client's own MCP list/get commands — never a
settings pane, per T007's instruction. Read-only commands only: no `mcp add` was
run (adding a server with `--env` writes literal values into config).

Note the version drift T007 flags: `docs/install/support-matrix.md` records
`0.144.5` for Codex while the installed CLI is `0.146.0`. The observations below
are against the installed versions.

## T007 / R1 — do plugins register MCP servers? **CONFIRMED, both harnesses**

### Claude Code

`claude mcp list` reports plugin-provided servers under a `plugin:<plugin>:<server>`
name:

```text
plugin:agentmemory:agentmemory: npx -y @agentmemory/mcp - OK Connected
plugin:github:github: https://api.githubcopilot.com/mcp/ (HTTP) - FAILED to connect - HTTP 400 ...
```

`claude mcp get plugin:agentmemory:agentmemory` resolves it and reports
`Scope: Dynamic config (from command line)`, `Status: Connected`. A
**stdio** plugin server (`npx -y @agentmemory/mcp`) is connected, which is the
transport a bundled `seshat mcp` would use.

### Codex

`codex mcp list` reports `github` (streamable_http, enabled). It is
**plugin-provided**: the user's `~/.codex/config.toml` declares only `node_repl`
and `codescene`, so `github` can only come from the installed `github` plugin under
`~/.codex/plugins/cache/openai-curated/`.

**A trap worth recording**: Codex does **not** namespace plugin servers the way
Claude does. Grepping `codex mcp list` for `plugin` returns **0** rows, which reads
as "Codex does not register plugin servers" and is wrong. The registration is real;
only the naming convention differs. Under T010 that distinction matters — a wrong
grep would have produced a false negative and halted the story.

## T009 / R3 — is a failed plugin server's diagnostic surfaced? **CONFIRMED on Claude, PARTIAL on Codex**

Claude surfaces a specific, actionable failure for a plugin server without being
asked:

```text
plugin:github:github: ... - FAILED to connect - HTTP 400: Streamable HTTP error:
Error POSTing to endpoint: bad request: Authorization header is badly formatted
```

That is exactly the property FR-014's degradation story needs: the user learns the
server failed and why, rather than silently losing the tools.

Codex exposes `Status` and `Auth` columns per server (`enabled`,
`Unsupported`/`Bearer token`), so a status surface exists — but **no failing Codex
plugin server was observed**, so its failure text is unverified. Recorded as
partial rather than claimed.

## T008 / R2 — what working directory does a plugin-launched server start in? **CLOSED BY DESIGN**

The question was empirically unresolvable in the order the tasks are written (below);
the owner ruled it away rather than measured. The investigation is kept because it is
why the design changed.

Neither client exposes it. `claude mcp get` reports scope and status but no cwd;
`codex mcp list`'s `Cwd` column is **unset (`-`)** for both stdio servers, which
suggests the runtime does not pin one and the child inherits the client's cwd — but
that is inference from an empty column, not an observation, and it is not evidence
enough to close a stop gate on.

**The risk is real in our code, not hypothetical.**
`src/seshat/cli/__init__.py::_run_mcp` does:

```python
server = create_server(Path(args.repo))
```

with `--repo` defaulting to `.`. `Path(".")` resolves against the *process* working
directory, so if a plugin-launched server starts in the plugin directory, the
governor reports on the plugin directory instead of the user's workspace — the
precise failure T008 exists to catch.

### A circular dependency in the task order

T008 asks for the cwd a **plugin-launched** server starts in. Observing that
requires a plugin that declares our server — which is T015–T019, and T010 gates
those on T008. The research cannot close in the order the tasks are written.

Two ways out, both for the owner to choose:

1. **Answer it empirically** with a throwaway scratch plugin declaring a trivial
   stdio server that prints its cwd, installed into an isolated profile and removed
   afterwards. Resolves R2 for real, and costs one scratch plugin.
2. **Design the question away.** Do not depend on the cwd at all: have the bundled
   declaration pass an explicit workspace root, or have the server resolve the root
   from the client's workspace rather than `.`. Then R2's answer cannot break the
   loop whichever way it falls, and `--repo .` stops being load-bearing.

Option 2 is the agent's recommendation: it removes a class of failure rather than
measuring it, and the measurement would still leave `--repo .` correct-by-accident.

### RULED — remove the cwd dependency (option 2), and DONE

- **ruled_by**: Ahmed Shaaban (owner)
- **ruled_on**: 2026-07-31
- **recorded_by**: the agent transcribed an owner-directed ruling after presenting
  both options with their costs. It did not self-grant (Principle V).

Implemented in `src/seshat/workspace_root.py`, tested by
`tests/unit/test_workspace_root.py` (6 tests):

- `--repo` **no longer defaults to `.`** (`cli/parser.py`). Absent the flag, the
  workspace is DISCOVERED by walking up from the working directory.
- The cwd is only a **starting point**, never the answer.
- Discovery either finds a workspace or **fails by name**, printing the directory it
  rejected, the markers it looked for, and how to fix it. A governor that cannot
  identify its workspace does not answer questions about one.
- An explicit `--repo` is still honoured -- FR-014 keeps the manual lane -- but it is
  **validated**, so a typo fails instead of silently degrading into discovery.
- Recognition markers derive from `workspace_init._EMPTY_DIRS` plus `.seshat`, not a
  hand-copied list, so a change to what `init-project` scaffolds cannot leave the
  recogniser behind. A workspace built by `init-project` alone (no `.seshat/`) is
  still recognised.
- Resolution happens **before** server construction and outside the optional-extra
  `ImportError` guard: an unidentifiable workspace is a different failure from a
  missing extra and must not be reported as one.

Observed end to end:

```text
$ cd <a non-workspace directory>   # the R2 failure, made harmless
$ seshat mcp
error: <scratch>/fake-plugin-dir is not a Seshat workspace: none of .seshat, mappings,
warehouse/migrations, powerbi, reports, evidence is present. Run `seshat init-project`
(or `seshat init`) there, or pass `--repo <workspace>` explicitly. The governor does
not fall back to the working directory, because reporting readiness for the wrong
tree is worse than refusing.
```

**R2 is now irrelevant to correctness.** Whatever working directory a harness gives a
plugin-launched server, the governor either identifies a real workspace or refuses by
name. T008 is closed by design, and the bundled declaration can carry no repository
path argument (T014) because none is needed.

## T010 — STOP GATE: CLEARED by owner ruling, not self-cleared

- **T007: positive** — plugins register MCP servers on both harnesses, confirmed at
  the runtime.
- **T009: positive on Claude, partial on Codex** — a Codex failure text remains
  unobserved and is not claimed.
- **T008: closed by design** — the cwd dependency is removed, so R2's answer no
  longer bears on correctness.

The gate was **reported** with both options and their costs; the owner chose. The
agent implemented no workaround (the chosen option is a design change to a shipped
verb's argument handling, ruled explicitly, not a patch around a failing check) and
re-scoped nothing.

**Still outstanding for US1**, and unchanged by this ruling: T011–T014 (tests),
T015–T020 (the declaration itself, its two manifest pointers, the artifact class, the
projection and the install doc) and T021–T023 (verification on both harnesses in a
scratch workspace). T021–T023 need installed clients, so they remain operator-run.

One carry-forward for T014: the wrapper key must be the camelCase `mcpServers`. One
platform's published example uses snake_case `mcp_servers`, which is unparsed and
yields a server that silently never loads — the failure mode hardest to notice,
since nothing errors.
