"""Tests + independent-oracle verifier for the Dashboard Gap Detector (spec 117).

The verifier sits ON the real risk (MEMORY: "verifier must sit on the risk"): an
uncovered/undecided required item must NEVER be classified `Covered`. Its oracle
(the expected status per fixture item) is HAND-DECLARED in the test, never read
back from the classifier under test (spec 114/115 independent-oracle discipline).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from seshat.coverage_status import _ENUM, STATUSES, is_member
from seshat.gap_detector import build_gap_inventory, render_view

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# fixture writers -- generic (no C086-specific value baked in; Principle VII)
# --------------------------------------------------------------------------- #
def _metric_yaml(name: str, status: str, columns: list[str]) -> str:
    cols = "\n".join(f'    - "{c}"' for c in columns) or "    []"
    return (
        f'name: "{name}"\n'
        "binds_to:\n"
        '  gold_table: "gold.fct_x"\n'
        "  columns:\n"
        f"{cols}\n"
        "readiness:\n"
        f'  status: "{status}"\n'
    )


SOURCE_MAP = """gold_star:
  fact:
    name: "gold.fct_x"
    measures:
      - "amount"
  dimensions:
    - name: "gold.dim_region_x"
      attributes:
        - "region"
  degenerate_dimensions:
    - "txn_id"
  date_dimension:
    name: "gold.dim_date_x"
"""

QUESTIONS_OPEN = """# Unresolved questions

- **Gate status:** `OPEN` -- decisions outstanding

| ID | Question | Why | Who must answer | Default | Status | Resolution |
|----|----------|-----|-----------------|---------|--------|------------|
| D1 | Is the discount policy final? | biases the rate | governance | keep | open | |
| D2 | What does a blank mean? | grain | analyst | null | open | |
"""

QUESTIONS_CLEARED = """# Unresolved questions

- **Gate status:** `CLEARED` -- all answered 2026-06-25

| ID | Question | Why | Who must answer | Default | Status | Resolution |
|----|----------|-----|-----------------|---------|--------|------------|
| D1 | Is the discount policy final? | bias | governance | keep | answered | yes |
"""


# An UNFILLED template-style gate line (placeholder value, not a real CLEARED).
QUESTIONS_TEMPLATE_PLACEHOLDER = """# Unresolved questions

- **Gate status:** `<OPEN | CLEARED>` -- fill this in

| ID | Question | Why | Who must answer | Default | Status | Resolution |
|----|----------|-----|-----------------|---------|--------|------------|
| D1 | Is the discount policy final? | bias | governance | keep | open | |
"""


def _write_table(
    root: Path, table: str, metrics: dict[str, str] | None, files: dict | None = None
) -> None:
    """Write a table's committed evidence. ``files`` overrides the source-map /
    questions defaults; a key set to None OMITS that file (the missing-input
    fixtures). A key absent uses the default committed content."""
    files = files or {}
    source_map = files["source_map"] if "source_map" in files else SOURCE_MAP
    questions = files["questions"] if "questions" in files else QUESTIONS_CLEARED
    d = root / "mappings" / table
    d.mkdir(parents=True, exist_ok=True)
    if metrics is not None:
        (d / "metrics").mkdir(exist_ok=True)
        for name, body in metrics.items():
            (d / "metrics" / f"{name}.yaml").write_text(body, encoding="utf-8")
    if source_map is not None:
        (d / "source-map.yaml").write_text(source_map, encoding="utf-8")
    if questions is not None:
        (d / "unresolved-questions.md").write_text(questions, encoding="utf-8")


def _write_intent(root: Path, name: str, body: str) -> str:
    p = root / name
    p.write_text(body, encoding="utf-8")
    return str(p)


# A pass metric M that depends on decision row D1 -- the shared setup for the
# owner-decision tests (only the supplied questions file varies).
_DEP_INTENT = (
    "questions:\n  - question: Q\n    metrics:\n"
    "      - name: M\n        depends_on: [D1]\n"
)


def _dep_metric_view(tmp_path: Path, files: dict) -> dict:
    _write_table(
        tmp_path, "widget", {"M": _metric_yaml("M", "pass", ["amount"])}, files
    )
    return build_gap_inventory(
        tmp_path, "widget", _write_intent(tmp_path, "dep.yaml", _DEP_INTENT)
    )


# The MIXED fixture: one metric per SL1 status + two dimensions + an out-of-scope.
MIXED_METRICS = {
    "CoveredMetric": _metric_yaml("CoveredMetric", "pass", ["amount"]),
    "UnapprovedMetric": _metric_yaml("UnapprovedMetric", "not_started", ["amount"]),
    "BadBindMetric": _metric_yaml("BadBindMetric", "pass", ["ghost_col"]),
}
MIXED_INTENT = """questions:
  - question: Coverage question
    metrics: [CoveredMetric, UnapprovedMetric, PlannedMetric, BadBindMetric]
    dimensions: [region, missingdim]
  - question: Inventory question
    out_of_scope: true
    metrics: [InventoryKPI]
"""
MIXED_ORACLE = {
    "CoveredMetric": "Covered",
    "UnapprovedMetric": "Blocked -- needs business definition",
    "PlannedMetric": "Planned",
    "BadBindMetric": "Blocked -- missing field",
    "region": "Covered",
    "missingdim": "Blocked -- missing field",
    "InventoryKPI": "Out of scope",
}


# --------------------------------------------------------------------------- #
# the independent-oracle verifier (V1-V4)
# --------------------------------------------------------------------------- #
def _strip_cited(text: str) -> str:
    """Drop backticked spans + double-quoted verbatim citations, where committed
    names/paths/question-text live, so a leftover number means a computed score."""
    return re.sub(r'"[^"]*"', "", re.sub(r"`[^`]*`", "", text))


def _v1_all_in_enum(items: list[dict]) -> None:
    for item in items:
        assert is_member(item["status"]), f"V1: {item['status']!r} not in SL1 enum"


def _v2_never_false_covered(got: dict, expected_status_by_item: dict) -> None:
    """The CRITICAL check, against the HAND-DECLARED oracle: an item whose expected
    status is not Covered must never be classified Covered."""
    for name, expected in expected_status_by_item.items():
        assert name in got, f"V2: required item {name!r} missing from inventory"
        assert got[name]["status"] == expected, (
            f"V2: {name} -> {got[name]['status']!r}, expected {expected!r}"
        )


def _v3_blocker_present(items: list[dict]) -> None:
    for item in items:
        if item["status"] != "Covered":
            assert item["blocker"], f"V3: {item['name']} non-Covered but no blocker"


def _v4_no_numeric_token(view: dict) -> None:
    """No numeric-score TOKEN in the rendered view (hard rule #9). The header's own
    disclaimer ("emits no score") is prose, not a violation -- the check scans for
    digits and % in the non-cited residue, not for the word "score"."""
    residue = _strip_cited(render_view(view))
    assert "%" not in residue, "V4: percent token in output"
    assert not re.search(r"\b\d+(\.\d+)?\b", residue), "V4: stray number (score?)"


def assert_status_inventory_sound(view: dict, expected_status_by_item: dict) -> None:
    got = {i["name"]: i for i in view["items"]}
    _v1_all_in_enum(view["items"])
    _v2_never_false_covered(got, expected_status_by_item)
    _v3_blocker_present(view["items"])
    _v4_no_numeric_token(view)


# --------------------------------------------------------------------------- #
# US1 -- every design-blocking gap, per-item status from SL1's five
# --------------------------------------------------------------------------- #
def test_mixed_statuses(tmp_path):
    _write_table(tmp_path, "widget", MIXED_METRICS)
    intent = _write_intent(tmp_path, "intent.yaml", MIXED_INTENT)
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert_status_inventory_sound(view, MIXED_ORACLE)
    # every one of SL1's five statuses is exercised
    assert {i["status"] for i in view["items"]} == set(STATUSES)


def test_all_covered_nothing_blocks(tmp_path):
    _write_table(tmp_path, "widget", {"A": _metric_yaml("A", "pass", ["amount"])})
    intent = _write_intent(
        tmp_path,
        "clean.yaml",
        "questions:\n  - question: Q\n    metrics: [A]\n    dimensions: [region]\n",
    )
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert_status_inventory_sound(view, {"A": "Covered", "region": "Covered"})
    assert all(i["status"] == "Covered" for i in view["items"])
    assert "Nothing blocks design" in render_view(view)
    assert view["document_gaps"] == []


def test_binds_to_mismatch_not_silent_covered(tmp_path):
    # a pass contract whose binds_to column is absent from gold_star -> a gap
    _write_table(tmp_path, "widget", MIXED_METRICS)
    intent = _write_intent(
        tmp_path,
        "b.yaml",
        "questions:\n  - question: Q\n    metrics: [BadBindMetric]\n",
    )
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert view["items"][0]["status"] == "Blocked -- missing field"
    assert "ghost_col" in view["items"][0]["blocker"]


def test_unmatched_metric_is_planned_not_dropped(tmp_path):
    _write_table(tmp_path, "widget", {"A": _metric_yaml("A", "pass", ["amount"])})
    intent = _write_intent(
        tmp_path, "u.yaml", "questions:\n  - question: Q\n    metrics: [NoSuchMetric]\n"
    )
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert len(view["items"]) == 1  # never silently dropped
    assert view["items"][0]["status"] == "Planned"


# --------------------------------------------------------------------------- #
# US2 -- open owner decisions block design; answered ones do not
# --------------------------------------------------------------------------- #
def test_open_decision_blocks_dependent_metric(tmp_path):
    view = _dep_metric_view(tmp_path, {"questions": QUESTIONS_OPEN})
    item = view["items"][0]
    assert item["status"] == "Blocked -- needs business definition"
    assert "governance" in item["blocker"]  # Who must answer, verbatim
    assert "discount policy" in item["blocker"]  # question text, verbatim
    assert "unresolved-questions.md" in item["evidence_path"]


def test_answered_decision_not_a_gap(tmp_path):
    view = _dep_metric_view(tmp_path, {"questions": QUESTIONS_CLEARED})
    assert view["items"][0]["status"] == "Covered"  # answered/CLEARED -> not blocked


def test_template_gate_placeholder_not_cleared(tmp_path):
    # an unfilled `Gate status: <OPEN | CLEARED>` placeholder must NOT clear the
    # gate (Codex P2): the open row stays open and blocks its dependent metric.
    view = _dep_metric_view(tmp_path, {"questions": QUESTIONS_TEMPLATE_PLACEHOLDER})
    assert view["items"][0]["status"] == "Blocked -- needs business definition"


def test_gate_prose_before_field_not_cleared(tmp_path):
    # Codex P2: intro PROSE mentioning "Gate status: CLEARED" before the real
    # `- **Gate status:** OPEN` field bullet must NOT clear the gate.
    prose_then_open = (
        "# Unresolved questions\n\n"
        "> no silver SQL until every row is answered and `Gate status: CLEARED`.\n\n"
        "- **Gate status:** `OPEN` -- decisions outstanding\n\n"
        "| ID | Question | Why | Who must answer | Default | Status | Resolution |\n"
        "|----|----------|-----|-----------------|---------|--------|------------|\n"
        "| D1 | Is the discount policy final? | bias | governance | keep | open | |\n"
    )
    view = _dep_metric_view(tmp_path, {"questions": prose_then_open})
    assert view["items"][0]["status"] == "Blocked -- needs business definition"


def test_unknown_dependency_fails_closed(tmp_path):
    # Codex P2: a depends_on referencing a row absent from unresolved-questions.md
    # (typo / stale / deleted) is unverifiable -> Blocked, never a silent Covered.
    _write_table(
        tmp_path,
        "widget",
        {"M": _metric_yaml("M", "pass", ["amount"])},
        {"questions": QUESTIONS_CLEARED},  # has only D1
    )
    intent = _write_intent(
        tmp_path,
        "unk.yaml",
        "questions:\n  - question: Q\n    metrics:\n"
        "      - name: M\n        depends_on: [D2]\n",  # D2 does not exist
    )
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert view["items"][0]["status"] == "Blocked -- needs business definition"
    assert "D2" in view["items"][0]["blocker"]


def test_metric_only_missing_source_map_fails_closed(tmp_path):
    # Codex P2: a pass contract whose binds_to cannot be verified (source-map
    # absent) must fail closed, never a silent Covered / "nothing blocks design".
    _write_table(
        tmp_path,
        "widget",
        {"M": _metric_yaml("M", "pass", ["amount"])},
        {"source_map": None},
    )
    intent = _write_intent(
        tmp_path, "mo.yaml", "questions:\n  - question: Q\n    metrics: [M]\n"
    )
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert view["items"][0]["status"] == "Blocked -- missing field"
    assert "Nothing blocks design" not in render_view(view)
    assert any("source-map.yaml" in g for g in view["document_gaps"])


def test_unrecognized_owner_echoed_verbatim(tmp_path):
    q = QUESTIONS_OPEN.replace("governance", "wizard")
    view = _dep_metric_view(tmp_path, {"questions": q})
    assert "wizard" in view["items"][0]["blocker"]  # echoed, no invented owner class


# --------------------------------------------------------------------------- #
# US3 -- missing/unreadable input surfaced, never fabricated
# --------------------------------------------------------------------------- #
def test_no_page_intent_document_gap(tmp_path):
    _write_table(tmp_path, "widget", {"A": _metric_yaml("A", "pass", ["amount"])})
    view = build_gap_inventory(tmp_path, "widget", None)
    assert view["items"] == []  # nothing fabricated
    assert view["document_gaps"] and "page-intent" in view["document_gaps"][0]
    assert "Nothing blocks design" not in render_view(view)


def test_missing_source_map_not_covered(tmp_path):
    _write_table(
        tmp_path,
        "widget",
        {"A": _metric_yaml("A", "pass", ["amount"])},
        {"source_map": None},
    )
    intent = _write_intent(
        tmp_path, "s.yaml", "questions:\n  - question: Q\n    dimensions: [region]\n"
    )
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert view["items"][0]["status"] != "Covered"  # unclassifiable != silent pass
    assert any("source-map.yaml" in g for g in view["document_gaps"])


def test_missing_metrics_dir_document_gap(tmp_path):
    _write_table(tmp_path, "widget", None)  # no metrics/ dir
    intent = _write_intent(
        tmp_path, "m.yaml", "questions:\n  - question: Q\n    metrics: [A]\n"
    )
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert view["items"][0]["status"] != "Covered"
    assert any("metrics/" in g for g in view["document_gaps"])


def test_missing_questions_file_not_no_decisions(tmp_path):
    view = _dep_metric_view(tmp_path, {"questions": None})
    assert view["items"][0]["status"] != "Covered"
    assert any("unresolved-questions.md" in g for g in view["document_gaps"])


def test_missing_ledger_named_even_without_deps(tmp_path):
    # Codex P2 / SC-008: a missing unresolved-questions.md must be NAMED even when
    # no item depends on it -- never a silent "nothing blocks design".
    _write_table(
        tmp_path,
        "widget",
        {"A": _metric_yaml("A", "pass", ["amount"])},
        {"questions": None},
    )
    intent = _write_intent(
        tmp_path,
        "nd.yaml",
        "questions:\n  - question: Q\n    metrics: [A]\n    dimensions: [region]\n",
    )
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert any("unresolved-questions.md" in g for g in view["document_gaps"])
    assert "Nothing blocks design" not in render_view(view)


def test_unreadable_contract_is_unverifiable(tmp_path):
    # Codex P2 / FR-013: a present-but-unreadable metric contract is reported
    # unverifiable, never silently "Planned" (which hides a broken committed file).
    _write_table(tmp_path, "widget", {"M": "[ this is not valid yaml\n"})
    intent = _write_intent(
        tmp_path, "ur.yaml", "questions:\n  - question: Q\n    metrics: [M]\n"
    )
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert view["items"][0]["status"] == "Blocked -- needs business definition"
    assert "unreadable" in view["items"][0]["blocker"].lower()


# --------------------------------------------------------------------------- #
# cross-cutting: no-write proof (SC-007), vocabulary parity (SC-002), generic
# --------------------------------------------------------------------------- #
def test_module_has_no_write_call():
    src = Path("src/seshat/gap_detector.py").read_text(encoding="utf-8")
    assert "write_text" not in src
    assert ".write(" not in src
    assert "open(" not in src  # reads use Path.read_text, not open()


def test_cli_writes_nothing(tmp_path):
    from seshat.cli.commands.gap_detector import gap_detector_main

    _write_table(tmp_path, "widget", MIXED_METRICS)
    intent = _write_intent(tmp_path, "intent.yaml", MIXED_INTENT)
    tdir = tmp_path / "mappings" / "widget"
    before = {p.name for p in tdir.rglob("*")}
    args = argparse.Namespace(
        repo=str(tmp_path), table="widget", page_intent=intent, output_format="text"
    )
    assert gap_detector_main(args) == 0
    assert {p.name for p in tdir.rglob("*")} == before, "detector must write nothing"


def test_vocabulary_is_exactly_sl1(tmp_path):
    # SC-002: the detector's status set equals SL1's enum -- no minted status.
    _write_table(tmp_path, "widget", MIXED_METRICS)
    intent = _write_intent(tmp_path, "intent.yaml", MIXED_INTENT)
    view = build_gap_inventory(tmp_path, "widget", intent)
    assert {is_member(i["status"]) for i in view["items"]} == {True}
    from seshat.coverage_status import _norm

    assert {_norm(s) for s in STATUSES} == _ENUM


def test_generic_two_tables(tmp_path):
    # SC-010: same composer, two distinct tables, no per-table branch.
    _write_table(tmp_path, "widget", MIXED_METRICS)
    _write_table(tmp_path, "gadget", {"A": _metric_yaml("A", "pass", ["amount"])})
    v1 = build_gap_inventory(
        tmp_path, "widget", _write_intent(tmp_path, "i1.yaml", MIXED_INTENT)
    )
    v2 = build_gap_inventory(
        tmp_path,
        "gadget",
        _write_intent(
            tmp_path,
            "i2.yaml",
            "questions:\n  - question: Q\n    metrics: [A]\n    dimensions: [region]\n",
        ),
    )
    assert {i["status"] for i in v1["items"]} == set(STATUSES)
    assert all(i["status"] == "Covered" for i in v2["items"])
