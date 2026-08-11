"""T019: committed Codex fixtures are shaped like the real protocol (FR-011, FR-024).

The risk this file exists to kill: a fixture written from the same misreading as the
client that consumes it. Such a pair agrees with itself forever and goes green while
the real provider sends something else -- the failure mode is invisible precisely
because both halves came from one author's assumption.

So the oracle here is NOT the bridge. It is the schema bundle the installed CLI
generates about itself (`codex app-server generate-json-schema`). Where that bundle is
unavailable -- CI runners have no Codex CLI -- the tests still enforce every structural
invariant that can be checked without it, and the schema-backed assertions skip
explicitly rather than passing vacuously.

The bundle is 3.4 MB and is deliberately not committed (T019 says so outright): it is
version-specific audit input, not a vendored contract.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "codex_app_server"

#: Frames Studio sends or receives on the happy path. Each must parse as JSON-RPC.
WELL_FORMED_FILES = (
    "handshake.jsonl",
    "account.jsonl",
    "login.jsonl",
    "thread_turn.jsonl",
    "approvals.jsonl",
    "incompatible.jsonl",
    "quota.jsonl",
)

#: Secret-shaped strings that must appear ONLY in the negative stderr fixture.
_SECRET_MARKERS = ("sk-", "Bearer ", "postgresql://", "OPENAI_API_KEY")


def _frames(name: str) -> Iterator[dict]:
    text = (FIXTURE_DIR / name).read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip():
            yield json.loads(line)


def test_every_well_formed_fixture_parses_as_jsonrpc() -> None:
    for name in WELL_FORMED_FILES:
        for frame in _frames(name):
            assert frame.get("jsonrpc") == "2.0", f"{name}: missing jsonrpc version"
            has_method = "method" in frame
            has_outcome = "result" in frame or "error" in frame
            assert has_method or has_outcome, f"{name}: neither a call nor a reply"


def test_malformed_fixture_is_actually_malformed() -> None:
    """A negative fixture that parses cleanly tests nothing.

    This asserts the file earns its name: at least one line must fail to parse, and at
    least one must parse yet violate the envelope. Without this, a later "tidy-up" of
    the fixture could silently defang every fail-closed test that reads it.
    """
    body = (FIXTURE_DIR / "malformed.jsonl").read_text(encoding="utf-8")
    raw = [line for line in body.splitlines() if line.strip()]
    unparseable = 0
    envelope_violations = 0
    for line in raw:
        try:
            frame = json.loads(line)
        except json.JSONDecodeError:
            unparseable += 1
            continue
        if frame.get("jsonrpc") != "2.0" or not (
            "method" in frame or "result" in frame or "error" in frame
        ):
            envelope_violations += 1
        elif isinstance(frame.get("id"), (dict, list)):
            envelope_violations += 1

    assert unparseable >= 2, "malformed.jsonl must contain unparseable lines"
    assert envelope_violations >= 2, "malformed.jsonl must contain envelope violations"


def test_no_secret_shapes_outside_the_negative_fixture() -> None:
    """Credentials may appear ONLY in stderr_secrets.txt, the redaction fixture."""
    for path in sorted(FIXTURE_DIR.glob("*")):
        if path.name in {"stderr_secrets.txt", "README.md"}:
            continue
        body = path.read_text(encoding="utf-8")
        for marker in _SECRET_MARKERS:
            assert marker not in body, f"{path.name} carries a secret shape: {marker}"


def test_negative_stderr_fixture_carries_every_secret_shape() -> None:
    """The redaction test is only as good as the shapes this fixture contains."""
    body = (FIXTURE_DIR / "stderr_secrets.txt").read_text(encoding="utf-8")
    for marker in _SECRET_MARKERS:
        assert marker in body, f"stderr fixture is missing the {marker!r} shape"


def test_studio_never_sends_an_api_key_login_variant() -> None:
    """FR-013: the subscription path is the only outbound login Studio models.

    `LoginAccountParams` is a tagged union whose `apiKey` variant sits directly beside
    `chatgpt`, so sending the billed variant is a one-word mistake. No committed
    outbound fixture may model it.
    """
    for name in WELL_FORMED_FILES:
        for frame in _frames(name):
            if frame.get("method") == "account/login/start":
                assert frame["params"]["type"] == "chatgpt"
                assert "apiKey" not in frame["params"]


def test_approval_fixtures_correlate_by_jsonrpc_id_not_approval_id() -> None:
    """The file-change approval carries no `approvalId` at all in the real schema.

    That is why the bridge contract names the JSON-RPC request id as the correlation
    authority. Pinning it here stops a future fixture from inventing an `approvalId`
    field and letting the client correlate on something the provider never sends.
    """
    approval_requests = [
        frame
        for frame in _frames("approvals.jsonl")
        if str(frame.get("method", "")).endswith("requestApproval")
    ]
    assert approval_requests, "no approval requests in the fixture"
    for frame in approval_requests:
        assert isinstance(frame["id"], int), "approval must be an addressable request"
        assert "approvalId" not in frame["params"], (
            "the stable file-change approval has no approvalId; correlating on one "
            "would invent a provider field"
        )


# -- schema-backed provenance ---------------------------------------------------- #


def _generated_schema_dir() -> Path | None:
    """Generate the real schema bundle into a temp dir, or None when unavailable.

    Deliberately returns None rather than raising: CI has no Codex CLI, and a test
    that cannot run its oracle must skip loudly rather than assert nothing.
    """
    if os.environ.get("SESHAT_SKIP_CODEX_PROBE"):
        return None
    codex = shutil.which("codex")
    if codex is None:
        return None
    out = Path(tempfile.mkdtemp(prefix="codex-schema-"))
    try:
        subprocess.run(  # noqa: S603 - fixed argv, no shell, no interpolation
            [codex, "app-server", "generate-json-schema", "--out", str(out)],
            check=True,
            capture_output=True,
            timeout=180,
            stdin=subprocess.DEVNULL,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return out if (out / "ClientRequest.json").exists() else None


def _declared_methods(schema_dir: Path) -> set[str]:
    methods: set[str] = set()
    for name in (
        "ClientRequest.json",
        "ServerRequest.json",
        "ServerNotification.json",
        "ClientNotification.json",
    ):
        document = json.loads((schema_dir / name).read_text(encoding="utf-8"))
        for variant in document.get("oneOf", []):
            method = variant.get("properties", {}).get("method", {})
            values = method.get("enum") or (
                [method["const"]] if "const" in method else []
            )
            methods.update(values)
    return methods


def test_every_fixture_method_exists_in_the_generated_schema() -> None:
    """The anti-circularity check: fixture method names come from the provider.

    Skips when the CLI is absent -- but when it is present, an invented or renamed
    method name fails here rather than surviving into the client.
    """
    schema_dir = _generated_schema_dir()
    if schema_dir is None:
        pytest.skip("codex CLI unavailable; schema-backed provenance not checked")

    declared = _declared_methods(schema_dir)
    # `some/futureRequiredMethod` is deliberately fictional: it is the fixture for an
    # unknown REQUIRED request, which must classify the adapter incompatible.
    invented_on_purpose = {"some/futureRequiredMethod", "totally/unknown/notification"}

    for name in WELL_FORMED_FILES:
        for frame in _frames(name):
            method = frame.get("method")
            if method is None or method in invented_on_purpose:
                continue
            assert method in declared, (
                f"{name}: method {method!r} is not in the installed app-server schema; "
                "the fixture was written from an assumption, not from the provider"
            )
