"""The vendor subprocess environment: #658, carried across #660.

Split from `test_pbi_mcp_runner.py` because the environment allowlist is a
distinct responsibility from the runner behaviour suite -- CodeScene measured
the merged module at 13 responsibilities against a threshold of 4 once #660 and
#658 both landed in it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate, protocol, runner, session

pytestmark = pytest.mark.unit


TARGET_PATH = "powerbi/Sales.SemanticModel"
OPERATION = "measure_operations.Rename"


def _cleared_verdict(operation: str = OPERATION) -> gate.GateVerdict:
    """A verdict whose every component holds.

    Built explicitly rather than by running the gate, so this module tests the
    runner in isolation. ``cleared`` is a computed property, so this cannot
    fabricate a pass that the real fields would contradict.
    """
    return gate.GateVerdict(
        target_id="sales_model",
        authorized_operation=operation,
        authorized_path=TARGET_PATH,
        stage_readable=True,
        state_committed=True,
        stage_pass=True,
        approval=gate.Approval(
            stage="publish_ready",
            owner="Ahmed Shaaban (data_owner)",
            at="2026-08-18",
            note="approved for sales_model",
        ),
        approval_names_target=True,
        approval_names_operation=True,
        operation_binds=True,
        target_allowlisted=True,
        target_exists=True,
        git_safe=True,
        blockers=(),
    )


def _uncleared_verdict(**overrides: object) -> gate.GateVerdict:
    base = _cleared_verdict()
    fields = {
        **{k: getattr(base, k) for k in vars(base)},
        "blockers": (gate.BLOCKER_STAGE_NOT_PASS,),
        "stage_pass": False,
    }
    fields.update(overrides)
    return gate.GateVerdict(**fields)  # type: ignore[arg-type]


def _outcome(
    ok: bool = True,
    read_only: bool | None = None,
    text: str = "",
) -> protocol.ToolOutcome:
    raw = text or json.dumps({"message": "done"})
    return protocol.ToolOutcome(
        ok=ok,
        read_only_hint=read_only,
        payload=None,
        raw_text=raw,
        error=None if ok else "the vendor reported isError",
    )


class FakeSession:
    """Stands in for :class:`McpSession`; records the calls the runner makes."""

    def __init__(
        self,
        outcomes: list[protocol.ToolOutcome] | None = None,
        *,
        raise_on_handshake: bool = False,
        handshake_error: Exception | None = None,
    ):
        self.calls: list[tuple[str, dict]] = []
        self.handshaken = False
        self.closed = False
        self._outcomes = list(outcomes or [])
        self._raise_on_handshake = raise_on_handshake or handshake_error is not None
        self._handshake_error = handshake_error or session.SessionStalled(
            "no reply within deadline"
        )

    def handshake(self) -> dict:
        if self._raise_on_handshake:
            raise self._handshake_error
        self.handshaken = True
        return {"name": "powerbi-modeling-mcp", "version": "0.5.0.0"}

    def call(self, tool: str, request: dict) -> protocol.ToolOutcome:
        self.calls.append((tool, request))
        if self._outcomes:
            return self._outcomes.pop(0)
        return _outcome()

    def close(self) -> None:
        self.closed = True

    @property
    def tools(self) -> list[str]:
        return [tool for tool, _ in self.calls]

    @property
    def operations(self) -> list[str]:
        return [request.get("operation") for _, request in self.calls]


def _factory(fake: FakeSession):
    def make(**_kwargs: object) -> FakeSession:
        return fake

    return make


# --------------------------------------------------------------------------
# Issue #658: the vendor process must not inherit the parent environment
# --------------------------------------------------------------------------


def test_credentials_never_reach_the_vendor_environment() -> None:
    """Deny by default. This is the assertion that makes the helper a gate.

    The vendor runtime is external, unforked and a public preview (ADR 0018), so
    anything in the parent environment is visible to a third party. An ABSENCE
    assertion is what catches a later edit that copies the Dagster adapter's
    prefix rules over -- that helper forwards `DATABASE_URL` and `ANALYTICS_DB_*`
    BY DESIGN, because it feeds governed Seshat connections. Forwarding a database
    credential to a preview binary would be worse than inheriting it by accident,
    because it would look deliberate.

    Issue #658.
    """
    hostile = {
        "PATH": "/usr/bin",
        "SYSTEMROOT": "C:\\Windows",
        "DATABASE_URL": "postgres://u:p@host:5432/db",
        "ANALYTICS_DB_PASSWORD": "hunter2",
        "SESHAT_DBT_PROFILE": "prod",
        "AWS_SECRET_ACCESS_KEY": "AKIAsecret",
        "GITHUB_TOKEN": "ghp_realtokenvalue",
        "AZURE_CLIENT_SECRET": "s3cret",
    }

    env = runner.allowed_vendor_environment(hostile)

    leaked = sorted(set(env) - {"PATH", "SYSTEMROOT"})
    assert not leaked, f"credential-bearing variables reached the vendor: {leaked}"
    for value in ("hunter2", "AKIAsecret", "ghp_realtokenvalue", "s3cret"):
        assert value not in "".join(env.values())


def test_the_vendor_environment_keeps_what_npx_needs() -> None:
    """Positive control: a helper returning {} would satisfy the absence test.

    Measured against the real toolchain rather than guessed:
    `npx --yes cowsay@1.6.0 hi` fetches AND executes with only PATH, SYSTEMROOT
    and PATHEXT present.
    """
    source = {
        "PATH": "/usr/bin",
        "PATHEXT": ".COM;.EXE",
        "SYSTEMROOT": "C:\\Windows",
        "APPDATA": "C:\\Users\\u\\AppData\\Roaming",
        "SECRET": "nope",
    }

    env = runner.allowed_vendor_environment(source)

    assert env["PATH"] == "/usr/bin"
    assert env["PATHEXT"] == ".COM;.EXE"
    assert "SECRET" not in env


def test_no_prefix_wildcard_widens_the_vendor_allowlist() -> None:
    """The allowlist is EXACT keys only -- no prefix rules.

    A prefix rule is how an allowlist grows silently: one governed family today,
    an unrelated match tomorrow. The Dagster helper needs prefixes; this one
    forwards no connection variables at all, so it must not have them.
    """
    invented = {
        "SESHAT_ANYTHING": "x",
        "ANALYTICS_DB_HOST": "y",
        "PBI_MCP_TOKEN": "z",
        "PATH": "/usr/bin",
    }

    env = runner.allowed_vendor_environment(invented)

    assert set(env) == {"PATH"}


def test_the_real_spawn_receives_a_FILTERED_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CAPABILITY, not the shape: what actually reaches the child.

    This assertion used to read `inspect.getsource(runner._run)` for the substring
    `"env="`. #660 deleted `_run` and moved the spawn into a long-lived stdio
    transport -- so a source-substring tripwire pinned to a function NAME would
    have gone vacuous (or errored) at exactly the moment the guarded behaviour
    moved. Assert the environment the transport is CONSTRUCTED with instead, so
    the test survives the next relocation of the spawn.

    Issue #658, carried across #660.
    """
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host:5432/db")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_realtokenvalue")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.corp:3128")

    captured: dict[str, dict[str, str]] = {}

    class _Recording:
        def __init__(self, argv: list[str], cwd: Path, env: dict[str, str], **kw):
            captured["env"] = env

    monkeypatch.setattr(session, "SubprocessTransport", _Recording)
    monkeypatch.setattr(session, "McpSession", lambda transport, **kw: object())

    runner._default_session_factory(argv=["npx", "x"], cwd=tmp_path)

    env = captured["env"]
    assert "DATABASE_URL" not in env, "a credential reached the vendor spawn"
    assert "GITHUB_TOKEN" not in env
    assert "ghp_realtokenvalue" not in "".join(env.values())
    # Positive control: an empty dict would satisfy every assertion above.
    assert env.get("HTTPS_PROXY") == "http://proxy.corp:3128"
    assert "PATH" in env


def test_the_transport_refuses_an_implicit_inherited_environment() -> None:
    """`env` is REQUIRED, so forgetting it is a TypeError, not a silent leak.

    It defaulted to None, which `Popen` reads as "inherit everything" -- the
    allowlist was one forgotten argument away from being bypassed. A caller that
    wants the ambient environment now has to say so.
    """
    import inspect

    parameter = inspect.signature(session.SubprocessTransport.__init__).parameters[
        "env"
    ]
    assert parameter.default is inspect.Parameter.empty, (
        "env has a default again, so a caller can silently inherit the parent "
        "environment and bypass the #658 allowlist"
    )


def test_proxy_routing_survives_so_npx_can_reach_the_registry() -> None:
    """Routing, not trust. A CA bundle says whether a chain VERIFIES; it never
    says which host to dial.

    Where egress is proxy-only, dropping these makes `npx` attempt a direct
    connection and fail before the vendor runtime starts -- the fetch dies, so
    no write can execute. npm honours these variables directly
    (`using-npm/config.md`).

    Codex P2 on PR #668.
    """
    source = {
        "PATH": "/usr/bin",
        "HTTP_PROXY": "http://proxy.corp:3128",
        "HTTPS_PROXY": "http://proxy.corp:3128",
        "NO_PROXY": "localhost,127.0.0.1",
    }

    env = runner.allowed_vendor_environment(source)

    assert env["HTTP_PROXY"] == "http://proxy.corp:3128"
    assert env["HTTPS_PROXY"] == "http://proxy.corp:3128"
    assert env["NO_PROXY"] == "localhost,127.0.0.1"


def test_lowercase_proxy_keys_reach_the_child_in_their_source_spelling() -> None:
    """The non-obvious half: three allowlist entries cover SIX variables.

    The filter compares `key.upper()`, so the Unix lowercase forms match, and the
    emitted dict keeps the SOURCE spelling -- `http_proxy` must arrive as
    `http_proxy`, because that is the form Unix tooling reads. Upper-casing the
    key on the way out would silently break exactly the platform that uses it.

    This is a PLATFORM-AGNOSTIC assertion: it passes on Windows and Linux alike,
    because the helper is given an explicit dict rather than `os.environ`.
    """
    source = {"http_proxy": "http://proxy.corp:3128", "no_proxy": "localhost"}

    env = runner.allowed_vendor_environment(source)

    assert env == {"http_proxy": "http://proxy.corp:3128", "no_proxy": "localhost"}


def test_an_authenticated_proxy_is_forwarded_verbatim() -> None:
    """Deliberate, and NOT a regression of #658.

    An authenticated proxy URL carries `user:pw@`. Forwarding it is required for
    the hop this subprocess is about to make on the caller's behalf -- unlike
    `DATABASE_URL`, which the vendor has no business seeing at all. Stripping the
    userinfo would route to the proxy and earn a 407, so there is no sanitized
    form that still works.

    Pinning it means a later "harden the proxy value" edit has to argue with a
    test instead of quietly breaking proxy-only egress.
    """
    source = {"HTTPS_PROXY": "http://svc:s3cret@proxy.corp:3128", "PATH": "/usr/bin"}

    env = runner.allowed_vendor_environment(source)

    assert env["HTTPS_PROXY"] == "http://svc:s3cret@proxy.corp:3128"


def test_the_proxy_keys_did_not_widen_the_allowlist_to_a_prefix() -> None:
    """Adding routing keys must not have introduced a `*_PROXY` prefix rule.

    Exact keys only: a neighbouring variable that merely LOOKS proxy-shaped stays
    out, so the deny-by-default posture is unchanged by this fix.
    """
    source = {
        "PROXY_PASSWORD": "hunter2",
        "ALL_PROXY": "socks5://nope:1080",
        "HTTPS_PROXY_EXTRA": "x",
        "PATH": "/usr/bin",
    }

    env = runner.allowed_vendor_environment(source)

    assert set(env) == {"PATH"}
    assert "hunter2" not in "".join(env.values())
