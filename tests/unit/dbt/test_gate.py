from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pytest

from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class MappingFixture:
    table_id: str = "orders"
    mapping_status: str = "pass"
    approval: Mapping[str, str] | None = None
    gate_status: str = "CLEARED"
    question_status: str = "answered"


@dataclass(frozen=True)
class GateCase:
    mapping_status: str
    approval: Mapping[str, str]
    gate_status: str
    question_status: str
    blocker_code: str


def _approval_yaml(approval: Mapping[str, str] | None) -> str:
    if approval is None:
        approval = {
            "stage": "mapping_ready",
            "owner": "A Owner (data_owner)",
            "at": "2026-07-16",
            "note": "approved mapping",
        }
    if not approval:
        return "approvals: []"
    items = list(approval.items())
    first_key, first_value = items[0]
    return "\n".join(
        [
            "approvals:",
            f'  - {first_key}: "{first_value}"',
            *[f'    {key}: "{value}"' for key, value in items[1:]],
        ]
    )


def _readiness_yaml(fixture: MappingFixture) -> str:
    return "\n".join(
        [
            f'table: "{fixture.table_id}"',
            "stages:",
            "  mapping_ready:",
            f'    status: "{fixture.mapping_status}"',
            "    evidence:",
            "      - approved source map",
            _approval_yaml(fixture.approval),
            "",
        ]
    )


def _source_map_yaml(table_id: str) -> str:
    return "\n".join(
        [
            "meta:",
            f'  table_id: "{table_id}"',
            '  grain: "one row per order"',
            "  primary_key:",
            '    - "order_id"',
            "",
        ]
    )


def _questions_markdown(fixture: MappingFixture) -> str:
    return "\n".join(
        [
            f"# Unresolved questions -- `{fixture.table_id}`",
            "",
            f"- **Gate status:** `{fixture.gate_status}`",
            "",
            "| ID | Question | Status | Resolution |",
            "|----|----------|--------|------------|",
            f"| Q1 | Confirm grain | `{fixture.question_status}` | Owner confirmed |",
            "",
        ]
    )


def _write_mapping(repo: Path, fixture: MappingFixture | None = None) -> Path:
    fixture = fixture or MappingFixture()
    mapping = repo / "mappings" / fixture.table_id
    mapping.mkdir(parents=True)
    (mapping / "readiness-status.yaml").write_text(
        _readiness_yaml(fixture),
        encoding="utf-8",
    )
    (mapping / "source-map.yaml").write_text(
        _source_map_yaml(fixture.table_id),
        encoding="utf-8",
    )
    (mapping / "unresolved-questions.md").write_text(
        _questions_markdown(fixture),
        encoding="utf-8",
    )
    return mapping


@pytest.fixture
def approved_repo(tmp_path: Path) -> Path:
    repo = make_git_repo(tmp_path)
    _write_mapping(repo)
    commit_all(repo, "approved mapping")
    return repo


def test_mapping_gate_allows_only_the_complete_approved_state(
    approved_repo: Path,
) -> None:
    from seshat.dbt.gate import evaluate_mapping_gate, resolve_working_set

    working_set = resolve_working_set(approved_repo, "orders")
    decision = evaluate_mapping_gate(working_set)

    assert decision.allowed is True
    assert decision.mapping_status == "pass"
    assert decision.mirror_cleared is True
    assert decision.blocking_reasons == ()
    assert decision.approval is not None
    assert decision.approval.owner == "A Owner (data_owner)"
    assert decision.approval.approval_id == (
        "78058534f30ec8c975e9a236004c71dd47074e0108da258f829aec06c2f63472"
    )
    assert working_set.source_map_revision
    assert len(working_set.source_map_sha256) == 64


@pytest.mark.parametrize(
    "case",
    [
        GateCase(
            mapping_status="blocked",
            approval={
                "stage": "mapping_ready",
                "owner": "A Owner",
                "at": "2026-07-16",
                "note": "approved",
            },
            gate_status="CLEARED",
            question_status="answered",
            blocker_code="DBT_MAPPING_NOT_PASS",
        ),
        GateCase(
            mapping_status="pass",
            approval={},
            gate_status="CLEARED",
            question_status="answered",
            blocker_code="DBT_MAPPING_APPROVAL_MISSING",
        ),
        GateCase(
            mapping_status="pass",
            approval={
                "stage": "mapping_ready",
                "owner": "A Owner",
                "at": "2026-07-16",
                "note": "approved",
            },
            gate_status="BLOCKED",
            question_status="answered",
            blocker_code="DBT_MAPPING_MIRROR_BLOCKED",
        ),
        GateCase(
            mapping_status="pass",
            approval={
                "stage": "mapping_ready",
                "owner": "A Owner",
                "at": "2026-07-16",
                "note": "approved",
            },
            gate_status="CLEARED",
            question_status="open",
            blocker_code="DBT_MAPPING_QUESTIONS_OPEN",
        ),
    ],
)
def test_mapping_gate_fails_closed(
    tmp_path: Path,
    case: GateCase,
) -> None:
    from seshat.dbt.gate import evaluate_mapping_gate, resolve_working_set

    repo = make_git_repo(tmp_path)
    _write_mapping(
        repo,
        MappingFixture(
            mapping_status=case.mapping_status,
            approval=case.approval,
            gate_status=case.gate_status,
            question_status=case.question_status,
        ),
    )
    commit_all(repo, "mapping fixture")

    decision = evaluate_mapping_gate(resolve_working_set(repo, "orders"))

    assert decision.allowed is False
    assert case.blocker_code in {blocker.code for blocker in decision.blocking_reasons}


@pytest.mark.parametrize("table_id", ["", "../orders", "Orders", "orders-1", "a/b"])
def test_working_set_rejects_unsafe_table_ids(
    approved_repo: Path, table_id: str
) -> None:
    from seshat.dbt.contracts import GovernanceError
    from seshat.dbt.gate import resolve_working_set

    with pytest.raises(GovernanceError) as exc:
        resolve_working_set(approved_repo, table_id)

    assert exc.value.code == "DBT_TABLE_ID_INVALID"


def test_working_set_rejects_a_dirty_source_map(approved_repo: Path) -> None:
    from seshat.dbt.contracts import GovernanceError
    from seshat.dbt.gate import resolve_working_set

    source_map = approved_repo / "mappings/orders/source-map.yaml"
    source_map.write_text(source_map.read_text(encoding="utf-8") + "# changed\n")

    with pytest.raises(GovernanceError) as exc:
        resolve_working_set(approved_repo, "orders")

    assert exc.value.code == "DBT_SOURCE_MAP_DIRTY"


def test_working_set_rejects_an_untracked_source_map(tmp_path: Path) -> None:
    from seshat.dbt.contracts import GovernanceError
    from seshat.dbt.gate import resolve_working_set

    repo = make_git_repo(tmp_path)
    mapping = _write_mapping(repo)
    (mapping / "source-map.yaml").unlink()
    commit_all(repo, "mapping without map")
    (mapping / "source-map.yaml").write_text("meta: {}\n", encoding="utf-8")

    with pytest.raises(GovernanceError) as exc:
        resolve_working_set(repo, "orders")

    assert exc.value.code == "DBT_SOURCE_MAP_UNTRACKED"


def test_mapping_gate_reports_malformed_readiness_yaml(approved_repo: Path) -> None:
    from seshat.dbt.gate import evaluate_mapping_gate, resolve_working_set

    readiness = approved_repo / "mappings/orders/readiness-status.yaml"
    readiness.write_text("stages: [not: valid", encoding="utf-8")
    commit_all(approved_repo, "malformed readiness")

    decision = evaluate_mapping_gate(resolve_working_set(approved_repo, "orders"))

    assert decision.allowed is False
    assert {blocker.code for blocker in decision.blocking_reasons} == {
        "DBT_READINESS_INVALID"
    }


def _blocked_then_worktree_cleared(tmp_path: Path) -> Path:
    """Commit a blocked mapping, then edit ONLY the worktree into a passing one."""
    repo = make_git_repo(tmp_path)
    blocked = MappingFixture(
        mapping_status="blocked",
        approval={},
        gate_status="OPEN",
        question_status="open",
    )
    mapping = _write_mapping(repo, blocked)
    commit_all(repo, "blocked mapping")
    passing = MappingFixture()
    (mapping / "readiness-status.yaml").write_text(
        _readiness_yaml(passing), encoding="utf-8"
    )
    (mapping / "unresolved-questions.md").write_text(
        _questions_markdown(passing), encoding="utf-8"
    )
    return repo


def test_uncommitted_approval_and_clearance_do_not_unlock_the_gate(
    tmp_path: Path,
) -> None:
    from seshat.dbt.gate import evaluate_mapping_gate, resolve_working_set

    repo = _blocked_then_worktree_cleared(tmp_path)

    decision = evaluate_mapping_gate(resolve_working_set(repo, "orders"))

    assert decision.allowed is False
    assert decision.approval is None
    assert decision.mirror_cleared is False
    assert "DBT_MAPPING_UNCOMMITTED" in {
        blocker.code for blocker in decision.blocking_reasons
    }


@pytest.mark.parametrize(
    "relative", ["readiness-status.yaml", "unresolved-questions.md"]
)
def test_one_dirty_governed_file_blocks_the_gate(
    approved_repo: Path, relative: str
) -> None:
    from seshat.dbt.gate import evaluate_mapping_gate, resolve_working_set

    path = approved_repo / "mappings/orders" / relative
    path.write_text(path.read_text(encoding="utf-8") + "# edit\n", encoding="utf-8")

    decision = evaluate_mapping_gate(resolve_working_set(approved_repo, "orders"))

    assert decision.allowed is False
    assert "DBT_MAPPING_UNCOMMITTED" in {
        blocker.code for blocker in decision.blocking_reasons
    }


def test_gate_parses_the_committed_blob_not_the_worktree(
    approved_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove the net: with the cleanliness probe disabled, the committed read
    alone must still ignore a worktree-only edit."""
    from seshat.dbt import gate

    readiness = approved_repo / "mappings/orders/readiness-status.yaml"
    readiness.write_text("stages: [not: valid", encoding="utf-8")
    monkeypatch.setattr(gate, "is_tracked_and_clean", lambda root, rel: True)

    decision = gate.evaluate_mapping_gate(
        gate.resolve_working_set(approved_repo, "orders")
    )

    assert decision.allowed is True


def test_real_worked_example_mapping_gate_is_allowed() -> None:
    from seshat.dbt.gate import evaluate_mapping_gate, resolve_working_set

    root = Path(__file__).resolve().parents[3]
    decision = evaluate_mapping_gate(resolve_working_set(root, "retail_store_sales"))

    assert decision.allowed is True
    assert decision.blocking_reasons == ()


def test_fixture_git_state_is_clean(approved_repo: Path) -> None:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=approved_repo,
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )
    assert result.stdout == ""
