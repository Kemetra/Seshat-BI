"""The single unresolved-questions mirror parser shared by the dbt and Dagster gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.unresolved_mirror import AMBIGUOUS, MISSING, parse_mirror

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]

_HEADER = (
    "| ID | Question | Why it blocks | Who must answer "
    "| Proposed default (if unanswered) | Status | Resolution |\n"
    "|----|----------|---------------|-----------------"
    "|----------------------------------|--------|------------|\n"
)


def _mirror(rows: str, gate: str = "- **Gate status:** `CLEARED`") -> str:
    return f"# Unresolved questions\n\n{gate}\n\n{_HEADER}{rows}"


def test_open_row_with_trailing_whitespace_is_not_answered() -> None:
    row = "| Q1 | q | why | analyst | default | `open` | n/a |  \n"
    state = parse_mirror(_mirror(row))
    assert state.open_rows == 1
    assert state.cleared is False


def test_only_the_exact_answered_token_counts() -> None:
    rows = (
        "| Q1 | q | why | analyst | default | `resolved` | x |\n"
        "| Q2 | q | why | analyst | default | `n/a` | x |\n"
        "| Q3 | q | why | analyst | default | `unanswered` | x |\n"
        "| Q4 | q | why | analyst | default | `answered` | x |\n"
    )
    assert parse_mirror(_mirror(rows)).open_rows == 3


def test_status_column_is_located_from_the_header() -> None:
    text = (
        "- **Gate status:** `CLEARED`\n\n"
        "| ID | Status | Question | Resolution |\n"
        "|----|--------|----------|------------|\n"
        "| Q1 | `answered` | q | `open` |\n"
    )
    state = parse_mirror(text)
    assert state.open_rows == 0
    assert state.cleared is True


def test_question_row_without_a_status_header_counts_as_open() -> None:
    text = "- **Gate status:** `CLEARED`\n\n| Q1 | q | `answered` | x |\n"
    assert parse_mirror(text).open_rows == 1


@pytest.mark.parametrize(
    "gate",
    ["## Gate status: CLEARED", "- **Gate status:** `CLEARED`", "Gate status: CLEARED"],
)
def test_bullet_heading_and_plain_forms_are_read(gate: str) -> None:
    assert parse_mirror(_mirror("", gate)).gate_status == "CLEARED"


def test_missing_and_duplicate_gate_status_never_clear() -> None:
    assert parse_mirror(_mirror("", "no marker here")).gate_status == MISSING
    doubled = "- **Gate status:** `CLEARED`\n## Gate status: OPEN"
    assert parse_mirror(_mirror("", doubled)).gate_status == AMBIGUOUS


def test_inline_mention_is_not_a_gate_status_marker() -> None:
    text = "> the gate reads `Gate status: CLEARED` only when...\n"
    assert parse_mirror(text).gate_status == MISSING


def _committed_mirrors() -> list[str]:
    return sorted(
        path.parent.name
        for path in (_REPO / "mappings").glob("*/unresolved-questions.md")
    )


@pytest.mark.parametrize("table", _committed_mirrors())
def test_every_committed_mirror_gets_one_verdict_from_both_gates(table: str) -> None:
    """The dbt gate and the Dagster gate must read each committed mirror alike."""
    from seshat.dagster_adapter.gate import read_gate_state
    from seshat.dbt.gate import evaluate_mapping_gate, resolve_working_set

    dagster = read_gate_state(_REPO, table)
    dbt = evaluate_mapping_gate(resolve_working_set(_REPO, table))
    dbt_mirror_ok = not {
        blocker.code
        for blocker in dbt.blocking_reasons
        if blocker.code in {"DBT_MAPPING_MIRROR_BLOCKED", "DBT_MAPPING_QUESTIONS_OPEN"}
    }
    if dagster.gate_status == "UNCOMMITTED":
        pytest.skip("mirror carries local edits in this checkout")
    assert dbt.mirror_cleared == (dagster.gate_status == "CLEARED")
    assert dbt_mirror_ok == dagster.silver_permitted
