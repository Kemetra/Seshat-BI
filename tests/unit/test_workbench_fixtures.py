"""Task 1.0 -- the shared fixtures every later spec-140 phase consumes.

These assertions exist because a fixture that only these tests can read would make the
whole feature suite green while proving nothing about the shipped readers. In
particular Task 3.5's "an uncommitted decision moves no stage, a committed one does"
proof is meaningless unless `git_workspace` is a REAL repository that can commit.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unit import _workbench_fixtures as fixtures  # noqa: E402

pytestmark = pytest.mark.unit


def test_the_client_fixture_is_authenticated_over_a_real_workspace(tmp_path: Path):
    """The client must reach a real projection route, not a stub.

    `/workspace` is the shipped Foundation route; a 200 here means bootstrap
    succeeded and the workspace was recognized by the real recognizer.
    """
    client = fixtures.studio_client(tmp_path)

    response = client.get("/api/v1/workspace")

    assert response.status_code == 200, response.text
    assert response.json()["tables"], "the fixture workspace must contain a table"


def test_an_unauthenticated_client_is_refused(tmp_path: Path):
    """Proves the 200 above came from authentication, not from an absent guard.

    Without this pair, `studio_client` could be handing back an app with security
    disabled and the first test would still pass.
    """
    unauthenticated = fixtures.unauthenticated_client(tmp_path)

    response = unauthenticated.get("/api/v1/workspace")

    assert response.status_code == 401, response.text


def test_the_git_workspace_is_a_real_repository_that_can_commit(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    fixtures.store_file(tmp_path)

    workspace.commit_all("test: initial")

    head = workspace.head_sha()
    assert len(head) == 40, f"expected a full sha, got {head!r}"


def test_head_sha_changes_between_commits(tmp_path: Path):
    """A commit must actually advance HEAD.

    Task 3.5 distinguishes uncommitted from committed state, so a `commit_all` that
    silently did nothing would make that proof vacuous.
    """
    workspace = fixtures.git_workspace(tmp_path)
    store = fixtures.store_file(tmp_path)
    workspace.commit_all("test: initial")
    first = workspace.head_sha()

    store.write_text("decisions: []\n# touched\n", encoding="utf-8")
    workspace.commit_all("test: second")

    assert workspace.head_sha() != first


def test_the_store_file_is_created_where_the_shipped_reader_looks(tmp_path: Path):
    """The path must be one of the shipped `STORE_PATHS`, not an invented location."""
    from seshat import decision_store

    store = fixtures.store_file(tmp_path)

    relative = store.relative_to(tmp_path).as_posix()
    assert relative in decision_store.STORE_PATHS, (
        f"{relative} is not a store path the gate reads: {decision_store.STORE_PATHS}"
    )


def test_the_store_file_is_readable_by_the_shipped_loader(tmp_path: Path):
    """Built from the real loader's perspective, not from a hand-rolled expectation."""
    from seshat import decision_store

    fixtures.store_file(tmp_path)

    loaded = decision_store.load_store_file(tmp_path, ".seshat/semantic-decisions.yaml")

    assert loaded.present
    assert not loaded.problems, loaded.problems
