"""The mapping stage's unresolved-questions mirror emitter (issue #326).

A table could clear the whole readiness spine without ever producing
``mappings/<table>/unresolved-questions.md``, then hard-fail the dbt gate
(``DBT_MAPPING_MIRROR_MISSING``) and the dagster gate (Gate status MISSING).
The emitter guarantees the mirror exists: a CLEARED stub only when the
COMMITTED readiness status records a named-human mapping_ready pass in the
audited C4 owner shape (derived from git HEAD, never invented, never from an
uncommitted worktree edit), an OPEN stub otherwise, and never overwrites the
human-authored ledger.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit


_APPROVED_READINESS = """\
stages:
  mapping_ready:
    status: pass
    evidence:
      - "mappings/orders_raw/source-map.yaml reviewed and approved"
approvals:
  - stage: mapping_ready
    owner: "Dana Analyst (data_owner)"
    at: "2026-07-16"
    note: "approved"
"""


def _mapping_dir(root: Path, table: str = "orders_raw") -> Path:
    mapping_dir = root / "mappings" / table
    mapping_dir.mkdir(parents=True)
    return mapping_dir


def _committed_repo(tmp_path: Path, readiness: str, table: str = "orders_raw") -> Path:
    repo = make_git_repo(tmp_path)
    mapping_dir = _mapping_dir(repo, table)
    (mapping_dir / "readiness-status.yaml").write_text(readiness, encoding="utf-8")
    commit_all(repo, "record readiness")
    return repo


def test_open_stub_when_no_readiness_status_exists(tmp_path: Path) -> None:
    from seshat.mapping_mirror import ensure_unresolved_questions

    mapping_dir = _mapping_dir(tmp_path)

    result = ensure_unresolved_questions(tmp_path, "orders_raw")

    assert result.created is True
    assert result.status == "open-stub"
    assert result.path == mapping_dir / "unresolved-questions.md"
    text = result.path.read_text(encoding="utf-8")
    assert text.count("Gate status:") == 1
    assert "OPEN" in text


def test_cleared_stub_mirrors_a_committed_named_human_pass(tmp_path: Path) -> None:
    from seshat.mapping_mirror import ensure_unresolved_questions

    repo = _committed_repo(tmp_path, _APPROVED_READINESS)

    result = ensure_unresolved_questions(repo, "orders_raw")

    assert result.created is True
    assert result.status == "cleared-stub"
    text = result.path.read_text(encoding="utf-8")
    assert text.count("Gate status:") == 1
    assert "CLEARED" in text


def test_uncommitted_readiness_pass_never_mints_a_clearance(tmp_path: Path) -> None:
    """The Dagster source_map asset trusts a CLEARED mirror, so the derivation
    reads git HEAD only: a worktree-only (uncommitted) pass must yield an OPEN
    stub even though the file content looks fully approved."""
    from seshat.mapping_mirror import ensure_unresolved_questions

    repo = make_git_repo(tmp_path)
    mapping_dir = _mapping_dir(repo)
    (mapping_dir / "readiness-status.yaml").write_text(
        _APPROVED_READINESS, encoding="utf-8"
    )

    result = ensure_unresolved_questions(repo, "orders_raw")

    assert result.status == "open-stub"


def test_dirty_committed_readiness_never_mints_a_clearance(tmp_path: Path) -> None:
    from seshat.mapping_mirror import ensure_unresolved_questions

    pending = _APPROVED_READINESS.replace("status: pass", "status: pending")
    repo = _committed_repo(tmp_path, pending)
    # Uncommitted edit flips it to pass -- the committed truth is still pending.
    (repo / "mappings" / "orders_raw" / "readiness-status.yaml").write_text(
        _APPROVED_READINESS, encoding="utf-8"
    )

    result = ensure_unresolved_questions(repo, "orders_raw")

    assert result.status == "open-stub"


@pytest.mark.parametrize(
    "readiness",
    (
        pytest.param(
            _APPROVED_READINESS.replace("status: pass", "status: pending"),
            id="mapping-not-pass",
        ),
        pytest.param(
            _APPROVED_READINESS.replace(
                'owner: "Dana Analyst (data_owner)"', 'owner: ""'
            ),
            id="approval-without-named-owner",
        ),
        pytest.param(
            _APPROVED_READINESS.replace(
                'owner: "Dana Analyst (data_owner)"', 'owner: "agent"'
            ),
            id="agent-owner",
        ),
        pytest.param(
            _APPROVED_READINESS.replace(
                'owner: "Dana Analyst (data_owner)"', 'owner: "Dana Analyst"'
            ),
            id="owner-without-authority-class",
        ),
        pytest.param(
            _APPROVED_READINESS.replace(
                'owner: "Dana Analyst (data_owner)"', 'owner: "data_owner"'
            ),
            id="bare-role-token-owner",
        ),
        pytest.param(
            _APPROVED_READINESS.replace("stage: mapping_ready", "stage: source_ready"),
            id="approval-for-a-different-stage",
        ),
        pytest.param(
            _APPROVED_READINESS.replace(
                "    evidence:\n"
                '      - "mappings/orders_raw/source-map.yaml reviewed and'
                ' approved"\n',
                "",
            ),
            id="evidence-free-pass",
        ),
        pytest.param(
            _APPROVED_READINESS.replace(
                '      - "mappings/orders_raw/source-map.yaml reviewed and approved"\n',
                "      []\n",
            ).replace("    evidence:\n      []", "    evidence: []"),
            id="empty-evidence-list-pass",
        ),
        pytest.param(
            _APPROVED_READINESS.replace(
                "    status: pass\n",
                "    status: pass\n"
                "    blocking_reasons:\n"
                '      - "grain question reopened"\n',
            ),
            id="pass-still-carrying-blockers",
        ),
        pytest.param("not: [valid yaml\n", id="unreadable-readiness"),
    ),
)
def test_open_stub_when_pass_or_c4_approval_is_not_recorded(
    tmp_path: Path, readiness: str
) -> None:
    """CLEARED is derived, never invented: anything short of a COMMITTED
    mapping_ready pass WITH a named-human approval in the audited C4 shape
    ``Person Name (authority_class)`` yields an OPEN stub."""
    from seshat.mapping_mirror import ensure_unresolved_questions

    repo = _committed_repo(tmp_path, readiness)

    result = ensure_unresolved_questions(repo, "orders_raw")

    assert result.status == "open-stub"


def test_never_overwrites_the_human_authored_ledger(tmp_path: Path) -> None:
    from seshat.mapping_mirror import ensure_unresolved_questions

    mapping_dir = _mapping_dir(tmp_path)
    ledger = mapping_dir / "unresolved-questions.md"
    ledger.write_text("Gate status: OPEN\nhand-authored\n", encoding="utf-8")

    result = ensure_unresolved_questions(tmp_path, "orders_raw")

    assert result.created is False
    assert result.status == "already-present"
    assert ledger.read_text(encoding="utf-8") == "Gate status: OPEN\nhand-authored\n"


def test_generated_stubs_satisfy_the_dbt_gate_mirror_parser(tmp_path: Path) -> None:
    """The exact parser the dbt gate runs must read the CLEARED stub as
    (cleared, all answered) and the OPEN stub as (not cleared, all answered) --
    the stub blocks or clears the gate purely on the derived status."""
    from seshat.dbt.gate import _mirror_state
    from seshat.mapping_mirror import ensure_unresolved_questions

    repo = _committed_repo(tmp_path, _APPROVED_READINESS, table="cleared_table")
    cleared = ensure_unresolved_questions(repo, "cleared_table")
    _mapping_dir(repo, "open_table")
    open_stub = ensure_unresolved_questions(repo, "open_table")

    assert _mirror_state(cleared.path.read_text(encoding="utf-8")) == (True, True)
    assert _mirror_state(open_stub.path.read_text(encoding="utf-8")) == (False, True)


def test_generated_stubs_satisfy_the_dagster_gate_parser(tmp_path: Path) -> None:
    from seshat.dagster_adapter.gate import _read_unresolved
    from seshat.mapping_mirror import ensure_unresolved_questions

    repo = _committed_repo(tmp_path, _APPROVED_READINESS, table="cleared_table")
    ensure_unresolved_questions(repo, "cleared_table")
    _mapping_dir(repo, "open_table")
    ensure_unresolved_questions(repo, "open_table")

    assert _read_unresolved(repo / "mappings" / "cleared_table") == ("CLEARED", 0)
    assert _read_unresolved(repo / "mappings" / "open_table") == ("OPEN", 0)


def test_rejects_an_unsafe_table_id(tmp_path: Path) -> None:
    from seshat.mapping_mirror import ensure_unresolved_questions

    with pytest.raises(ValueError, match="table"):
        ensure_unresolved_questions(tmp_path, "../escape")


def test_rejects_a_table_without_a_mapping_directory(tmp_path: Path) -> None:
    """The emitter mirrors an EXISTING mapping working set; it never conjures
    a mappings/<table>/ directory for a table the mapping stage never touched."""
    from seshat.mapping_mirror import ensure_unresolved_questions

    with pytest.raises(ValueError, match="mapping"):
        ensure_unresolved_questions(tmp_path, "orders_raw")
