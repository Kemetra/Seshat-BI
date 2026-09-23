"""The Studio boundary removes bare credential shapes too (audit batch 13).

Layer one (exact secrets, credential NAMES, auth headers, DSN spans, workspace paths)
cannot see a bare token with no `key=` prefix. These tests pin the second layer --
the shipped secret-shaped table plus a bare provider-token table -- at every surface
that crosses the boundary: payload scrubbing, streamed deltas, the support bundle,
and problem details.

Sample tokens are ASSEMBLED from parts so this file never spells a committed-secret
shape the repo's own scanners would flag.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from seshat.studio import redaction
from seshat.studio.codex_protocol import _DeltaBuffer

pytestmark = pytest.mark.unit

_OPENAI = "sk-" + "proj-" + "A1b2C3d4E5f6G7h8"
_GITHUB = "gh" + "p_" + "b" * 36
_AWS = "AK" + "IA" + "IOSFODNN7EXAMPL1"
_JWT = "ey" + "JhbGciOiJIUzI1NiJ9" + ".eyJzdWIiOiIxIn0" + ".c2lnbmF0dXJl"
_GUID = "1b2c3d4e-" + "1111-2222-3333-" + "444455556666"
_PASSWORD = "S3cr" + "etPass99"
_DSN = "postgresql://" + "admin:" + _PASSWORD + "@db.example.com:5432/x"


@pytest.mark.parametrize("token", [_OPENAI, _GITHUB, _AWS, _JWT, _GUID])
def test_scrub_payload_removes_every_bare_token_shape(token: str):
    scrubbed = redaction.scrub_payload({"text": f"use {token} now"})

    assert token not in str(scrubbed)
    assert scrubbed == {"text": f"use {redaction.REDACTED} now"}


def test_contract_identifiers_are_not_blanked():
    """An id the relay correlates on must survive; blanking it breaks the decision."""
    payload = {"approval_id": _GUID, "text": _GUID}

    scrubbed = redaction.scrub_payload(payload)

    assert scrubbed == {"approval_id": _GUID, "text": redaction.REDACTED}


def test_the_workspace_path_is_relativized_before_the_home_path_rule(tmp_path: Path):
    """The home-path rule must not blank a workspace path layer one relativizes."""
    inside = tmp_path / "mappings" / "sales" / "source-map.yaml"

    scrubbed = redaction.redact_for_boundary(str(inside), workspace_root=tmp_path)

    assert scrubbed == "mappings/sales/source-map.yaml"


def test_provider_stderr_shares_the_bare_token_table():
    from seshat.studio.codex_process import redact_provider_stderr

    cleaned = redact_provider_stderr(f"auth failed for {_GITHUB} and {_AWS}")

    assert _GITHUB not in cleaned and _AWS not in cleaned


def _stream(chunks: list[str]) -> list[str]:
    buffer = _DeltaBuffer()
    scrub = redaction.redact_for_boundary
    frames = [buffer.push("item", chunk, scrub) for chunk in chunks]
    frames.append(buffer.flush("item", scrub))
    return [frame for frame in frames if frame]


@pytest.mark.parametrize(
    ("secret", "fragment"),
    [(_DSN, _PASSWORD[:3]), (_OPENAI, _OPENAI[3:8]), (_GITHUB, _GITHUB[:6])],
)
def test_a_split_credential_never_emits_a_partial_value(secret: str, fragment: str):
    message = f"connect with {secret} done"
    expected = redaction.redact_for_boundary(message)
    start = message.index(secret)

    for offset in range(start, start + len(secret) + 1):
        frames = _stream([message[:offset], message[offset:]])

        assert "".join(frames) == expected, (offset, frames)
        assert not any(fragment in frame for frame in frames), (offset, frames)


def _table(root: Path, name: str, note: str = "") -> None:
    folder = root / "mappings" / name
    folder.mkdir(parents=True)
    (folder / "readiness-status.yaml").write_text(f"table: {name}\n", encoding="utf-8")
    (folder / "source-map.yaml").write_text(f"table: {name}\n{note}", encoding="utf-8")


def test_a_bundle_keeps_every_tables_files_under_their_own_paths(tmp_path: Path):
    from seshat.studio import exports

    for name in ("alpha", "beta", "gamma"):
        _table(tmp_path, name)

    bundle = exports.build_support_bundle(tmp_path, destination=tmp_path / "b.zip")

    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        readiness = sorted(n for n in names if n.endswith("readiness-status.yaml"))
        contents = {archive.read(n).decode("utf-8").strip() for n in readiness}
    assert readiness == [
        "mappings/alpha/readiness-status.yaml",
        "mappings/beta/readiness-status.yaml",
        "mappings/gamma/readiness-status.yaml",
    ]
    assert contents == {"table: alpha", "table: beta", "table: gamma"}
    assert len(names) == len(set(names))


def test_a_planted_token_fails_the_real_bundle_scan(tmp_path: Path):
    from seshat.studio import exports

    _table(tmp_path, "alpha", note=f"note: {_GITHUB}\n")
    destination = tmp_path / "b.zip"

    with pytest.raises(exports.ScanFailed):
        exports.build_support_bundle(tmp_path, destination=destination)

    assert not destination.exists()


def test_a_readiness_read_failure_names_no_home_path(monkeypatch):
    from seshat.studio import approvals

    def _raise(*_args: object) -> None:
        raise FileNotFoundError("C:\\" + "Users\\someone\\readiness-status.yaml")

    monkeypatch.setattr(approvals, "build_table_next_document", _raise)

    reasons = approvals.forbidden_scope_for("ws", "sales")

    assert reasons
    assert "Users" not in " ".join(reasons)


def test_problem_details_are_redacted():
    pytest.importorskip("fastapi")
    from seshat.studio import agent_routes, app

    leaked = f"failed at C:\\{'Users'}\\someone\\x with {_GITHUB}"
    for problem in (app._problem, agent_routes._problem):
        body = problem(403, "t", leaked, "r").body.decode("utf-8")

        assert "someone" not in body and _GITHUB not in body, problem
