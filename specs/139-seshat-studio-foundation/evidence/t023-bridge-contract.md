# T023 — the bridge contract suite over both adapters

**Measured 2026-08-14** against `main` at `c01aeee0`.

T023: *"Run the bridge contract suite against fake and production adapters; accept every
failure state without automatic API-key fallback."* [SC-003, SC-004]

FR-013 as amended 2026-08-04 prohibits a **silent or automatic** switch to a billed path,
not the explicitly operator-configured alternate mode of T023a.

## Result — 68 passed

| Suite | Tests | What it holds |
|---|---|---|
| `tests/unit/test_studio_agent_bridge.py` | 24 | the shared contract, over BOTH adapters |
| `tests/unit/test_studio_bridge_selection.py` | 30 | seven health states × credential present/absent |
| `tests/unit/test_studio_bridge_startup.py` | 14 | what startup reports about which bridge is driving |

Counts are **collected** cases, not `def test_` lines: the contract suite's 12 functions
each run twice (once per adapter) and the selection walk expands over its parameter grid,
which is the whole point of both files.

```
pytest tests/unit/test_studio_agent_bridge.py \
       tests/unit/test_studio_bridge_selection.py \
       tests/unit/test_studio_bridge_startup.py
68 passed
```

## Both adapters, not two classes sharing method names

The contract suite is parametrized over bridge factories, and the production entry is the
real `CodexBridge` spawning an actual child process against recorded fixtures:

```python
CodexBridge(_plan("thread_turn"), propose_plan=_plan("file_change_turn"))
```

Its own docstring states the reason it is appended to the shared list rather than given
private assertions: *"so it inherits every property the fake is held to — the difference
between a real protocol and two classes that share method names."* That is what makes this
a contract suite rather than two parallel test files.

A signed-in Codex CLI is deliberately **not** required. The scripted child replays fixtures,
so the production code path — process launch, protocol framing, notification
normalization, health transitions — runs on any machine. Live-provider acceptance is
**T036**, which is owner-gated.

### Fixture provenance is not self-certified

`tests/unit/test_codex_fixture_provenance.py` (6 passed, 1 skipped) validates the fixtures
against the schema bundle the installed CLI generates about **itself**
(`codex app-server generate-json-schema`), not against the bridge that consumes them. Where
that bundle is absent — CI runners have no Codex CLI — the schema-backed assertions **skip
explicitly rather than passing vacuously**. The one skip in this run is exactly that, on a
machine with no CLI installed.

## No automatic API-key fallback — proven by walking the whole table

`select_bridge` is parametrized over `ALL_HEALTH_STATES` — all seven of SC-004's states
(`healthy`, `missing`, `signed_out`, `incompatible`, `quota_limited`, `crashed`,
`disabled`) — **crossed with `credential_present` both False and True**.

That second axis is the load-bearing one. FR-013 forbids an *automatic* switch, and the
only way to demonstrate absence is to present a usable credential during every failure
state and confirm the answer does not move. A suite that only ran `credential_present=False`
would pass while the fail-open existed, because nothing would be available to fall back to.

The implementation makes the same point structurally: `select_bridge` accepts
`health_state` and immediately `del`s it, with the signature comment recording why the
parameter exists at all — *"so that a caller cannot pass health 'for the selector to
consider', and so the test suite can walk the whole failure table asserting the answer
never moves."*

## Falsified, not assumed

An absence-assertion that has never fired proves nothing (the T034 standard). The exact
prohibited behaviour was injected into `bridge_selection.select_bridge`:

```python
if health_state != "healthy" and alternate_credential_present:
    return BridgeSelection(
        authentication_mode="operator_configured_alternate",
        uses_billed_path=True,
        disclosure=_ALTERNATE_DISCLOSURE,
    )
```

**42 of 68 tests failed**, including the full seven-state walk and the purity test
(`test_selection_is_a_pure_function_of_its_stated_inputs`). Reverted; the suite returns to
68 passed and `git diff` on the module is empty.

A single-test failure would have been the worrying outcome — it would mean one assertion
carried the whole prohibition. Forty-two means the property is pinned from several
independent directions.

## Scope not claimed

- **SC-003's streamed turn with subscription authentication** is exercised here against the
  scripted child, which proves the ordering and framing. It does not prove a real
  subscription sign-in produces a visible final result — that is **T036**.
- The two `tests/integration/test_studio_codex_real.py` tests, which drive a genuinely
  installed CLI, cannot run without one and fail on this machine for that reason alone.
  They are part of T036's territory, not evidence withheld here.
