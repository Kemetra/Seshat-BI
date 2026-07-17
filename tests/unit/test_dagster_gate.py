"""Unit tests for the read-only Dagster gate readers (spec 134, T005/T006).

The gate readers are the most safety-critical read in the adapter: they are the
ONLY GO signal for the human-seam assets. They READ committed artifacts under
``mappings/<table>/`` and MUST expose no write path (FR-005).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from seshat.dagster_adapter import gate

pytestmark = pytest.mark.unit


UNRESOLVED_CLEARED = """# Unresolved questions -- `demo_table`

- **Table id:** `demo_table`
- **Gate status:** `CLEARED` -- all questions answered.

## Open questions (the build is blocked until these are `answered`)

| ID | Question | Why it blocks | Who answers | Default | Status | Resolution |
|----|----------|---------------|-------------|---------|--------|------------|
| Q1 | A question? | It blocks. | analyst | default | `answered` | resolved 2026-01-01 |
| Q2 | Another? | It blocks. | governance | default | `answered` | resolved 2026-01-01 |
"""

UNRESOLVED_OPEN = """# Unresolved questions -- `demo_table`

- **Table id:** `demo_table`
- **Gate status:** `OPEN`

## Open questions (the build is blocked until these are `answered`)

| ID | Question | Why it blocks | Who answers | Default | Status | Resolution |
|----|----------|---------------|-------------|---------|--------|------------|
| Q1 | A question? | It blocks. | analyst | default | `answered` | resolved |
| Q2 | Another? | It blocks. | governance | default | `open` | |
| Q3 | Third? | It blocks. | analyst | default | `open` | |
"""

READINESS = """table: "bronze.demo_table"
stages:
  mapping_ready:
    status: "pass"
    evidence: []
    blocking_reasons: []
  publish_ready:
    status: "{publish_status}"
    evidence: []
    blocking_reasons: []
approvals:
  - stage: "mapping_ready"
    owner: "Named Human (data_owner)"
    at: "2026-06-25"
    note: "accepted"
"""


def _make_table(
    root: Path, table: str, unresolved: str, publish_status: str = "not_started"
) -> None:
    tdir = root / "mappings" / table
    tdir.mkdir(parents=True)
    (tdir / "unresolved-questions.md").write_text(unresolved, encoding="utf-8")
    (tdir / "readiness-status.yaml").write_text(
        READINESS.format(publish_status=publish_status), encoding="utf-8"
    )
    (tdir / "source-map.yaml").write_text("table: demo\n", encoding="utf-8")


class TestReadGateState:
    def test_cleared_gate_with_zero_open_rows(self, tmp_path: Path) -> None:
        _make_table(tmp_path, "demo_table", UNRESOLVED_CLEARED)
        state = gate.read_gate_state(tmp_path, "demo_table")
        assert state.gate_status == "CLEARED"
        assert state.open_rows == 0

    def test_open_gate_counts_open_rows(self, tmp_path: Path) -> None:
        _make_table(tmp_path, "demo_table", UNRESOLVED_OPEN)
        state = gate.read_gate_state(tmp_path, "demo_table")
        assert state.gate_status == "OPEN"
        assert state.open_rows == 2

    def test_heading_style_gate_status_is_read(self, tmp_path: Path) -> None:
        """The demo_sample_orders instance on main writes the gate as an H2
        heading (`## Gate status: CLEARED`), not a bold bullet -- both real
        committed phrasings must parse (review finding)."""
        heading_form = (
            "# Unresolved questions -- `demo_table`\n\n"
            "## Gate status: CLEARED\n\n"
            "- every question answered by the named owner.\n"
        )
        _make_table(tmp_path, "demo_table", heading_form)
        state = gate.read_gate_state(tmp_path, "demo_table")
        assert state.gate_status == "CLEARED"
        assert state.silver_permitted is True

    def test_unanswered_status_cell_counts_as_open(self, tmp_path: Path) -> None:
        """'unanswered' contains the substring 'answered' -- the cell must be
        an exact token match (review finding)."""
        tricky = UNRESOLVED_OPEN.replace("| `open` |", "| `unanswered` |")
        _make_table(tmp_path, "demo_table", tricky)
        state = gate.read_gate_state(tmp_path, "demo_table")
        assert state.open_rows == 2

    def test_missing_artifacts_report_missing(self, tmp_path: Path) -> None:
        (tmp_path / "mappings").mkdir()
        state = gate.read_gate_state(tmp_path, "absent_table")
        assert state.gate_status == "MISSING"
        assert state.open_rows == 0
        assert state.approvals == ()
        assert state.publish_ready == "missing"

    def test_approvals_read_verbatim(self, tmp_path: Path) -> None:
        _make_table(tmp_path, "demo_table", UNRESOLVED_CLEARED)
        state = gate.read_gate_state(tmp_path, "demo_table")
        assert len(state.approvals) == 1
        approval = state.approvals[0]
        assert approval.stage == "mapping_ready"
        assert approval.owner == "Named Human (data_owner)"
        assert approval.at == "2026-06-25"

    def test_publish_ready_read_verbatim(self, tmp_path: Path) -> None:
        _make_table(tmp_path, "demo_table", UNRESOLVED_CLEARED, publish_status="pass")
        state = gate.read_gate_state(tmp_path, "demo_table")
        assert state.publish_ready == "pass"

    def test_silver_permitted_only_when_cleared_and_zero_open(
        self, tmp_path: Path
    ) -> None:
        _make_table(tmp_path, "demo_table", UNRESOLVED_CLEARED)
        assert gate.read_gate_state(tmp_path, "demo_table").silver_permitted is True
        other = tmp_path / "other"
        _make_table(other, "demo_table", UNRESOLVED_OPEN)
        assert gate.read_gate_state(other, "demo_table").silver_permitted is False

    def test_approval_for_stage_lookup(self, tmp_path: Path) -> None:
        _make_table(tmp_path, "demo_table", UNRESOLVED_CLEARED)
        state = gate.read_gate_state(tmp_path, "demo_table")
        assert state.approval_for("mapping_ready") is not None
        assert state.approval_for("semantic_model_ready") is None


class TestListMappedTables:
    def test_lists_only_dirs_with_source_map(self, tmp_path: Path) -> None:
        _make_table(tmp_path, "alpha", UNRESOLVED_CLEARED)
        (tmp_path / "mappings" / "not_a_table").mkdir()
        (tmp_path / "mappings" / "README.md").write_text("x", encoding="utf-8")
        assert gate.list_mapped_tables(tmp_path) == ["alpha"]

    def test_missing_mappings_dir_is_empty(self, tmp_path: Path) -> None:
        assert gate.list_mapped_tables(tmp_path) == []


class TestReadOnlyGuarantee:
    """FR-005: the gate module must expose NO write path."""

    def test_no_public_write_functions(self) -> None:
        for name, obj in inspect.getmembers(gate, inspect.isfunction):
            if name.startswith("_"):
                continue
            assert not name.startswith(
                ("write", "set_", "update", "clear", "approve", "grant")
            ), f"gate module exposes a mutating function: {name}"

    def test_module_source_never_writes_files(self) -> None:
        source = inspect.getsource(gate)
        assert ".write_text(" not in source
        assert ".write_bytes(" not in source
        assert "yaml.dump" not in source
        assert "open(" not in source.replace("read_text(", "")

    def test_gate_state_is_immutable(self, tmp_path: Path) -> None:
        _make_table(tmp_path, "demo_table", UNRESOLVED_CLEARED)
        state = gate.read_gate_state(tmp_path, "demo_table")
        with pytest.raises((AttributeError, TypeError)):
            state.gate_status = "CLEARED"  # type: ignore[misc]
