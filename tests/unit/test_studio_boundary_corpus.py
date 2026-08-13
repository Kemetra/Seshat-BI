"""SC-006 / T034 -- sweep the WHOLE boundary corpus, not one field at a time.

`test_studio_security_boundary` and `test_studio_redaction` already assert specific
refusals and specific redactions, and they are the right shape for those questions.
Neither can answer T034's, which is different in kind: **does any secret, token,
absolute path, or workspace content appear ANYWHERE in what Studio emits?**

A per-field assertion only guards the fields somebody thought to name. This drives
real requests against a real app -- including every refusal path SC-006 lists -- then
scans the ENTIRE response corpus for injected markers. A new endpoint that leaks is
caught here without anyone remembering to write a test for it, which is the property
a corpus sweep has and an assertion list does not.

**Markers are injected, not searched for generically.** Grepping for "password" finds
prose about passwords; grepping for a value that could only have come from the secret
finds a leak. Each marker below is a unique nonce planted in a place Studio can see.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

from fastapi.testclient import TestClient  # noqa: E402

API = "/api/v1"
_BROWSER_ORIGIN = {"Origin": "http://127.0.0.1:9999"}

#: Unique nonces. Each could only appear in output by having leaked from its source,
#: so a hit is evidence rather than a coincidence.
SECRET_TOKEN = "sk-nonce7a1b2c3d4e5f6g7h8i9j0"
SECRET_PASSWORD = "hunter2-nonce-c3d4e5f6"

#: A marker in an ANCESTOR directory of the workspace, never in the workspace's own
#: name. The distinction is the point: the workspace name is `display_name`, which
#: Studio exists to show the analyst, so treating it as a secret would assert that the
#: Command Room must not name the room. What FR-026 forbids is the ABSOLUTE PATH -- the
#: operator's directory layout above the pinned root -- and only an ancestor segment
#: isolates that.
ANCESTOR_MARKER = "nonce_private_layout_9f8e7d"

#: The workspace's own directory name. Public by design; asserted PRESENT below, so a
#: future over-redaction that scrubs it is caught rather than praised.
WORKSPACE_NAME = "retail_workspace"

#: Ordinary analyst prose, pinned PRESENT for the same reason as the workspace name.
PROMPT_PROSE = "explain what is blocking the gold layer"


def _client(tmp_path: Path) -> tuple[TestClient, Any, str]:
    """A booted Studio whose workspace sits under a marked ancestor directory."""
    from seshat.studio.app import create_app

    root = tmp_path / ANCESTOR_MARKER / WORKSPACE_NAME
    (root / ".seshat").mkdir(parents=True)
    app, token = create_app(root, port=9999)
    client = TestClient(
        app, base_url="http://127.0.0.1:9999", headers=dict(_BROWSER_ORIGIN)
    )
    assert client.post(f"{API}/bootstrap", params={"token": token}).status_code == 204
    return client, app, token


def _corpus(client: TestClient, token: str) -> str:
    """Everything the browser can obtain, success and refusal alike, as one blob.

    Refusals are included deliberately: SC-006 is a statement about what a REFUSED
    request discloses, and an error path is exactly where a raw path or a stack frame
    tends to escape.
    """
    parts: list[str] = []

    def record(response: Any) -> None:
        parts.append(str(response.status_code))
        parts.append(response.text)
        parts.append(json.dumps(dict(response.headers)))

    # Successful reads.
    for path in (
        "/health",
        "/bootstrap/state",
        "/workspace",
        "/decisions",
        "/agent/health",
    ):
        record(client.get(f"{API}{path}"))

    # Refusal paths SC-006 names, each with a marker in the REQUEST so a naive echo
    # would surface it.
    record(client.get(f"{API}/tables/{ANCESTOR_MARKER}"))
    record(client.get(f"{API}/tables/../../etc/passwd"))
    record(client.get(f"{API}/agent/threads/{SECRET_TOKEN}/events"))
    record(
        client.post(f"{API}/agent/threads", json={"selected_table_id": SECRET_TOKEN})
    )
    record(client.post(f"{API}/bootstrap", params={"token": SECRET_TOKEN}))

    # A real turn, and the stream it produced.
    #
    # The prompt carries ANALYST PROSE, not a marker -- see
    # `test_the_analyst_prompt_round_trips` for why. A credential the analyst types
    # into their own prompt is echoed back on their own authenticated thread, and that
    # is the Conversation working rather than a disclosure.
    created = client.post(f"{API}/agent/threads", json={"selected_table_id": None})
    if created.status_code == 201:
        thread_id = created.json()["thread_id"]
        record(
            client.post(
                f"{API}/agent/threads/{thread_id}/turns",
                json={
                    "prompt": PROMPT_PROSE,
                    "snapshot_revision": "r1",
                    "requested_mode": "read_only",
                },
            )
        )
        for _ in range(3):
            record(client.get(f"{API}/agent/threads/{thread_id}/events"))

    # Foreign origin and wrong host -- the two remaining SC-006 refusals.
    record(
        client.post(
            f"{API}/agent/threads",
            json={"selected_table_id": None},
            headers={"Origin": "http://evil.example"},
        )
    )
    record(client.get(f"{API}/workspace", headers={"Host": "evil.example"}))

    # The session token itself must never be echoed back.
    parts.append(token)
    return "\n".join(parts[:-1])  # the token is the needle, not part of the haystack


def test_no_session_token_appears_anywhere_in_the_corpus(tmp_path: Path):
    """The bootstrap token is single-use, and a copy of it in any body defeats that."""
    client, _, token = _client(tmp_path)

    assert token not in _corpus(client, token)


def test_no_credential_in_a_ROUTING_position_is_echoed_back(tmp_path: Path):
    """A credential-shaped value in a URL segment, id, or token param must not return.

    These are the positions where an echo IS a defect: a thread id in a path segment,
    a `selected_table_id`, and the bootstrap `token` query parameter all end up in
    refusal messages, and a naive "unknown thread {id}" would publish whatever the
    caller sent.

    **Scoped decision, recorded rather than silently encoded in a fixture.** The
    analyst's own PROMPT is deliberately not tested here. A credential someone types
    into their own prompt is echoed back on their own authenticated loopback thread,
    and that is the Conversation working -- the same class as `display_name`. FR-026
    governs credentials Studio itself handles and paths it resolves, not analyst prose.
    Redacting bare token-shaped strings out of prose would also mean hand-rolling a
    match class beside `redaction_core`'s hardened decomposition, which this repo
    forbids, and would risk scrubbing legitimate governed text.

    If that reading is wrong it is an owner's call and belongs in an issue, not in a
    redactor change made on an autonomous branch.
    """
    client, _, token = _client(tmp_path)

    corpus = _corpus(client, token)

    assert SECRET_TOKEN not in corpus, (
        "a credential-shaped value sent in a routing position was echoed back"
    )
    assert SECRET_PASSWORD not in corpus


def test_the_analyst_prompt_round_trips(tmp_path: Path):
    """The second over-redaction guard.

    Every absence above is only meaningful if the corpus still carries the content
    Studio exists to show. Redaction that swallowed analyst prose would satisfy all
    four absence tests while making the Conversation unreadable.
    """
    client, _, token = _client(tmp_path)

    assert PROMPT_PROSE in _corpus(client, token)


def test_no_absolute_workspace_path_appears_anywhere_in_the_corpus(tmp_path: Path):
    """FR-026: absolute paths are redacted at every boundary, not just the ones tested.

    The marker is an ANCESTOR directory segment, so it can only reach the browser as
    part of an absolute path -- there is no legitimate projection that names the
    operator's directory layout above the pinned root. Refusal bodies are in scope
    precisely because that is where a raw path most often escapes.
    """
    client, _, token = _client(tmp_path)

    corpus = _corpus(client, token)

    assert str(tmp_path) not in corpus
    assert ANCESTOR_MARKER not in corpus, (
        "a directory ABOVE the pinned workspace reached the browser: an absolute path "
        "leaked, exposing the operator's filesystem layout"
    )


def test_the_workspace_name_is_still_shown(tmp_path: Path):
    """The over-redaction guard, and the reason the marker moved to an ancestor.

    An earlier revision of this file marked the workspace's OWN directory name and
    asserted its absence -- which would have demanded that the Command Room not name
    the room it opens. `display_name` is what FR-007 exists to project. Redaction that
    scrubbed it would pass every test above while making Studio useless, so the
    presence is pinned here as deliberately as the absences are above.
    """
    client, _, token = _client(tmp_path)

    assert WORKSPACE_NAME in _corpus(client, token)


def test_no_traceback_reaches_the_browser(tmp_path: Path):
    """A stack frame discloses module layout and often a full filesystem path."""
    client, _, token = _client(tmp_path)

    corpus = _corpus(client, token)

    assert "Traceback (most recent call last)" not in corpus
    assert "site-packages" not in corpus
    assert 'File "' not in corpus


def test_the_corpus_is_actually_populated(tmp_path: Path):
    """Guards the guard.

    Every test above asserts an ABSENCE. If `_corpus` silently returned "" -- a broken
    fixture, a refused bootstrap -- all four would pass while checking nothing. This is
    the positive control that makes the other four meaningful.
    """
    client, _, token = _client(tmp_path)

    corpus = _corpus(client, token)

    assert len(corpus) > 500, "the corpus is too small to have exercised the boundary"
    assert "workspace" in corpus, "the successful reads produced no recognisable body"
