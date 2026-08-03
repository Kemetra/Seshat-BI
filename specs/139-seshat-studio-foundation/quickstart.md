# Quickstart and Acceptance: Seshat Studio Foundation

**Feature**: 139-seshat-studio-foundation | **Date**: 2026-08-03

This document is the implementation and release verification route. It does not
authorize implementation while the feature is draft.

## 1. Confirm the governance gate

Before touching production code, verify all of the following:

```powershell
git branch --show-current
Select-String -Path AGENTS.md -Pattern "Active Spec Kit implementation plan"
Select-String -Path specs\139-seshat-studio-foundation\spec.md -Pattern "Status"
```

Expected when implementation is authorized:

- the branch is the isolated Studio feature branch;
- the active marker points only to
  `specs/139-seshat-studio-foundation/plan.md`;
- the exact spec and plan carry a named-human ratification record;
- spec 138 is completed or formally parked, not concurrently active.

If any condition is false, stop before editing `src/`, `studio-ui/`, `pyproject.toml`,
capability sources, or generated bundles.

## 2. Prepare development prerequisites

Release platform:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev,studio,browser]"
cd studio-ui
npm ci
cd ..
```

The current planning shell does not provide Python or Codex. Run these commands in a
Windows environment where `py -3.13` is available. Node is development-only.

## 3. Run deterministic test lanes

Backend tests do not need Codex, a database, or a network:

```powershell
.\.venv\Scripts\python -m pytest tests\unit\studio -q
.\.venv\Scripts\python -m pytest tests\integration\studio -q
.\.venv\Scripts\python -m pytest tests\contract\test_studio_package_contract.py tests\contract\test_studio_capability.py -q
```

Frontend and browser tests use the fake bridge:

```powershell
cd studio-ui
npm test -- --run
npm run build
cd ..
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\python -m pytest tests\browser\test_studio_command_room.py -q
```

The browser lane must cover:

- first arrival, passing table, blocked Mapping, and malformed input;
- all seven agent health states;
- ordered stream and reconnect replay;
- paused, allowed, denied, prohibited, and repeated approvals;
- keyboard-only use, visible focus, reduced motion, contrast, names, landmarks, and
  axe critical/serious findings;
- narrow and wide viewport layouts;
- zero remote asset requests.

## 4. Exercise the fake Studio locally

```powershell
$env:SESHAT_STUDIO_AGENT = "fake"
seshat-studio --repo tests\fixtures\studio\workspace-ready --no-browser
```

Expected behavior:

1. the launcher prints one complete tokenized `127.0.0.1` URL;
2. the token exchanges once and disappears from browser history;
3. Command Room matches the fixture's canonical projection;
4. a fake question streams visible ordered events;
5. a fake technical approval pauses until explicit allow or deny;
6. stopping the process leaves no durable Studio database or credential file.

`--repo` is a support/packaging option used before server startup; no browser API
accepts it. Natural-language agent launch remains the analyst journey.

## 5. Verify package isolation and wheel contents

```powershell
.\.venv\Scripts\python -m build
.\.venv\Scripts\python -m pytest tests\contract\test_studio_package_contract.py -q
```

In a clean temporary virtual environment, install the base wheel first and verify
static Seshat imports and checks work without FastAPI/Uvicorn. Then install the same
wheel with the `studio` extra and verify:

- `seshat-studio` exists;
- frontend assets exist inside `seshat/studio/static`;
- Studio starts without `node` on `PATH`;
- absent frontend assets produce a named packaging defect;
- `retail dashboard` output remains byte-compatible with its existing tests.

## 6. Verify generated agent integrations

```powershell
.\.venv\Scripts\python scripts\export_agent_bundles.py
git diff --exit-code -- integrations\claude-code integrations\codex distribution\public-knowledge-allowlist.yaml
.\.venv\Scripts\python -m pytest tests\contract\test_generated_agent_bundles.py tests\contract\test_studio_capability.py -q
```

In clean bundle fixtures, ask each supported harness, in natural language, to open
Seshat Studio. Codex must launch the interactive adapter when available. Claude Code
must launch deterministic views and explain its native handoff without embedded
subscription credential routing.

## 7. Run external Codex subscription acceptance

Preconditions: official Codex CLI installed, signed into a ChatGPT subscription,
no OpenAI API key supplied to the Studio process, and a safe fixture workspace.

Record these facts in the acceptance evidence:

- OS, Python, Seshat BI, Studio UI build, and Codex versions;
- `AgentHealth.state` before and after connection;
- authentication method stated as Codex-managed subscription;
- successful app-server handshake and thread start;
- one read-only question with ordered event types and final response;
- one denied technical approval producing no repository change;
- environment check confirming Studio was not given an API credential;
- quota or sign-out behavior if naturally observable, never induced by spending.

Do not copy tokens, credential paths, authorization output, or raw protocol frames
into the evidence.

## 8. Run repository regression gates

```powershell
.\.venv\Scripts\python -m ruff format --check src tests
.\.venv\Scripts\python -m ruff check src tests
.\.venv\Scripts\python -m pytest -m unit -x -q
.\.venv\Scripts\python -m pytest -m integration -x -q
seshat check
seshat semantic-check
git diff --check
git status --short
```

If a live database is unavailable, report existing live boundaries as
`[PENDING LIVE PROFILE]`; never reinterpret that as a pass. Foundation itself
introduces no live-DB acceptance requirement.

## Acceptance Result

Foundation is accepted only when every SC-001 through SC-010 has cited evidence,
all applicable commands above are green, deferred external boundaries are named,
and the worktree contains no unexpected generated or secret-bearing files.
