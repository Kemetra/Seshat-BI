"""Fail-closed truthfulness tests for the capability inventory (spec 118).

The O1-O8 oracle machinery (feeder readers + detectors) lives in the sibling
``_capability_oracle`` module -- split out so neither file carries too many
responsibilities. This file holds only the pytest cases and their local
assertion helpers.

The oracle sits ON the truthfulness risk (a false ``shipped`` /
``publicly-released``) and reads ground truth from the FEEDER sources directly,
never via the builder (repo lesson ``verifier-must-sit-on-the-risk``). Fixtures
under ``tests/unit/fixtures/capability_inventory/<name>/`` each isolate exactly
one failure mode.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from seshat import capability_feeders as feeders
from seshat.capability_inventory import build_inventory, render_human, render_json
from tests.unit import _capability_oracle as oracle

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "capability_inventory"


def _assert_closed_schema(records: list[dict]) -> None:
    for record in records:
        assert set(record) == oracle.DECLARED_RECORD_FIELDS, record


# ---------------------------------------------------------------------------
# Anti-circularity guard: the oracle must not import the code under test.
# ---------------------------------------------------------------------------


_BANNED_UNDER_TEST = {"seshat.capability_feeders", "seshat.capability_inventory"}
_BANNED_SUBMODULES = {"capability_feeders", "capability_inventory"}


def _imported_module_targets(node: ast.AST) -> set[str]:
    """The set of import targets a single AST import node names, normalized so a
    ``from seshat import capability_feeders`` reads as ``seshat.capability_feeders``
    (matching the dotted ``import seshat.capability_feeders`` / ``from
    seshat.capability_feeders import x`` shapes)."""
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}
    if isinstance(node, ast.ImportFrom) and node.module:
        base = {node.module}
        if node.module == "seshat":
            base |= {
                f"seshat.{a.name}" for a in node.names if a.name in _BANNED_SUBMODULES
            }
        return base
    return set()


def test_oracle_does_not_import_code_under_test() -> None:
    """The oracle's independence is structural: ``_capability_oracle`` must not
    import ``capability_feeders`` or ``capability_inventory`` (else it would
    learn ground truth from the code it checks -- circular)."""
    tree = ast.parse(Path(oracle.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        imported |= _imported_module_targets(node)
    assert not (imported & _BANNED_UNDER_TEST), imported & _BANNED_UNDER_TEST


# ---------------------------------------------------------------------------
# What MUST PASS: the real committed manifest
# ---------------------------------------------------------------------------


def test_real_manifest_passes_all_eight_oracle_checks() -> None:
    problems = oracle.oracle_all_clear(_REPO_ROOT)
    for check_name, found in problems.items():
        assert found == [], f"{check_name} found real-manifest problems: {found}"

    first = render_json(build_inventory(_REPO_ROOT))
    second = render_json(build_inventory(_REPO_ROOT))
    assert first == second, "machine form is not byte-identical across two runs"


# ---------------------------------------------------------------------------
# O1 -- orphan reference
# ---------------------------------------------------------------------------


def test_o1_orphan_reference_fails() -> None:
    problems = oracle.find_orphans(_FIXTURES_ROOT / "orphan")
    assert any("rules_manifest" in p or "ZZ-does-not-exist" in p for p in problems), (
        problems
    )
    assert any("orphan skill" in p for p in problems), problems


# ---------------------------------------------------------------------------
# O2 -- unlisted (a real wired representation no entry references)
# ---------------------------------------------------------------------------


def test_o2_unlisted_wired_command_fails() -> None:
    problems = oracle.find_unlisted(_FIXTURES_ROOT / "unlisted")
    assert any("unlisted-command" in p for p in problems), problems


def test_o2_reference_coverage_not_entry_per_representation() -> None:
    """One entry whose references cover a command + skill + verb for the SAME
    capability must NOT read as under-covering the other two."""
    problems = oracle.find_unlisted(_FIXTURES_ROOT / "good")
    assert problems == [], problems


# ---------------------------------------------------------------------------
# O3 -- false-shipped (fail-closed)
# ---------------------------------------------------------------------------


def test_o3_false_shipped_fails_closed() -> None:
    problems = oracle.find_false_shipped(_FIXTURES_ROOT / "false_shipped")
    assert any("fixture-false-shipped" in p for p in problems), problems


def test_o3_real_shipped_entries_all_have_positive_signal() -> None:
    assert oracle.find_false_shipped(_REPO_ROOT) == []


def test_o3_spec_only_f_number_gives_no_ship_signal() -> None:
    """A roadmap F-number whose OWN row is spec-only must NOT read as a ship
    signal, even if SHIPPED rows sit nearby (the fragile-window hole)."""
    assert oracle.roadmap_row_is_shipped("F029", _REPO_ROOT) is True
    assert oracle.roadmap_row_is_shipped("F030", _REPO_ROOT) is True
    for spec_only in ("F031", "F032", "F033"):
        assert oracle.roadmap_row_is_shipped(spec_only, _REPO_ROOT) is False


# ---------------------------------------------------------------------------
# O4 -- false-released (fail-closed)
# ---------------------------------------------------------------------------


def test_o4_false_released_fails_closed() -> None:
    problems = oracle.find_false_released(_FIXTURES_ROOT / "false_released")
    assert any("fixture-false-released" in p for p in problems), problems


def test_o4_real_manifest_has_no_unbacked_public_release() -> None:
    assert oracle.find_false_released(_REPO_ROOT) == []


# ---------------------------------------------------------------------------
# O5 -- feeder contradiction
# ---------------------------------------------------------------------------


def test_o5_contradiction_fails() -> None:
    problems = oracle.find_contradictions(_FIXTURES_ROOT / "contradiction")
    assert any("fixture-contradicting-rule-title" in p for p in problems), problems


def test_o5_real_manifest_has_no_contradiction() -> None:
    assert oracle.find_contradictions(_REPO_ROOT) == []


# ---------------------------------------------------------------------------
# O6 -- axis / score violation (incl. nested numerics)
# ---------------------------------------------------------------------------


def test_o6_axis_violation_fails() -> None:
    problems = oracle.find_axis_violations(_FIXTURES_ROOT / "axis_violation")
    assert any("state" in p and "advisory" in p for p in problems), problems
    assert any("maturity_score" in p or "numeric" in p for p in problems), problems


def test_o6_real_manifest_has_no_axis_or_score_violation() -> None:
    assert oracle.find_axis_violations(_REPO_ROOT) == []


# ---------------------------------------------------------------------------
# O7 -- closed schema
# ---------------------------------------------------------------------------


def test_o7_closed_schema_on_good_fixture() -> None:
    _assert_closed_schema(build_inventory(_FIXTURES_ROOT / "good"))


# ---------------------------------------------------------------------------
# O8 -- invalid readiness_stage
# ---------------------------------------------------------------------------


def test_o8_invalid_stage_is_not_a_valid_token() -> None:
    valid = oracle.valid_stage_tokens(_REPO_ROOT)
    assert "not_a_real_stage" not in valid


def test_o8_real_manifest_stage_tokens_all_valid() -> None:
    assert oracle.find_invalid_stage(_REPO_ROOT) == []


# ---------------------------------------------------------------------------
# US1 -- grouping by fixed precedence, no numeric score, ASCII output (T006)
# ---------------------------------------------------------------------------

_VALID_GROUPS = {
    "available-now",
    "requires-db-or-extra",
    "agent-companion",
    "human-gated",
    "deferred",
}


def _assert_exactly_one_valid_group(records: list[dict]) -> None:
    for record in records:
        assert record["group"] in _VALID_GROUPS


def _assert_available_now_axes(records: list[dict]) -> None:
    """Available-now holds only shipped + agent-runnable + empty-requirements."""
    for record in records:
        if record["group"] != "available-now":
            continue
        assert record["state"] == "shipped"
        assert record["authority"] == "agent-runnable"
        assert record["requirements"] == []


def _assert_requires_db_axes(records: list[dict]) -> None:
    """Requires-DB/extra holds only shipped, non-human-gated entries WITH a
    requirement (deferred/human-gated rank higher and land elsewhere)."""
    for record in records:
        if record["group"] != "requires-db-or-extra":
            continue
        assert record["requirements"] != []
        assert record["state"] == "shipped"
        assert record["authority"] != "human-gated"


def test_grouping_by_precedence() -> None:
    records = build_inventory(_FIXTURES_ROOT / "good")
    by_id = {r["id"]: r for r in records}

    assert by_id["fixture-available-now"]["group"] == "available-now"
    assert by_id["fixture-requires-db"]["group"] == "requires-db-or-extra"
    assert by_id["fixture-companion-skill"]["group"] == "agent-companion"
    assert by_id["fixture-human-gated"]["group"] == "human-gated"
    # Human-gated AND db-requiring -> higher-ranked group (Human-gated).
    assert by_id["fixture-human-gated-and-db"]["group"] == "human-gated"
    assert by_id["fixture-deferred"]["group"] == "deferred"
    # Deferred AND db-requiring -> Deferred, not Requires-DB.
    assert by_id["fixture-deferred-and-db"]["group"] == "deferred"

    _assert_exactly_one_valid_group(records)
    _assert_available_now_axes(records)
    _assert_requires_db_axes(records)


def test_no_numeric_score() -> None:
    records = build_inventory(_FIXTURES_ROOT / "good")
    for record in records:
        for value in record.values():
            assert not isinstance(value, (int, float)) or isinstance(value, bool), (
                record
            )
    rendered = render_human(records).lower()
    for hint in oracle.NUMERIC_FIELD_HINTS:
        assert hint not in rendered, f"{hint!r} leaked into rendered human output"


def test_output_ascii() -> None:
    rendered = render_human(build_inventory(_FIXTURES_ROOT / "good"))
    assert rendered.isascii()
    assert "→" not in rendered  # no unicode arrow
    assert "—" not in rendered  # no unicode em-dash


def test_empty_group_states_none() -> None:
    """A fixture with zero deferred entries states the Deferred group as empty
    rather than omitting or fabricating a row."""
    rendered = render_human(build_inventory(_FIXTURES_ROOT / "false_shipped"))
    assert "Deferred / not shipped" in rendered
    assert "(none)" in rendered


def test_empty_manifest_renders_all_groups_as_none() -> None:
    records = build_inventory(_FIXTURES_ROOT / "empty")
    assert records == []
    rendered = render_human(records)
    for heading in (
        "Available now",
        "Requires database or optional dependency",
        "Agent / companion",
        "Human-gated",
        "Deferred / not shipped",
    ):
        assert heading in rendered
    assert rendered.count("(none)") == 5


# ---------------------------------------------------------------------------
# US2 -- machine form determinism, closed schema, entry-point resolution (T009)
# ---------------------------------------------------------------------------


def test_json_determinism() -> None:
    records = build_inventory(_FIXTURES_ROOT / "good")
    assert render_json(records) == render_json(records)


def test_json_closed_schema() -> None:
    payload = json.loads(render_json(build_inventory(_FIXTURES_ROOT / "good")))
    _assert_closed_schema(payload)


def test_entrypoint_resolves() -> None:
    """Every shipped record's non-null command is a real _DISPATCH key; every
    documentation path exists -- checked against the REAL repo."""
    dispatch_keys = oracle.dispatch_keys_via_ast(_REPO_ROOT)
    for record in build_inventory(_REPO_ROOT):
        if record["state"] == "shipped" and record["command"] is not None:
            assert record["command"] in dispatch_keys, record
        doc = record["documentation"]
        assert doc and (_REPO_ROOT / doc).exists(), (
            f"{record['id']}: missing doc {doc!r}"
        )


def test_json_output_ascii() -> None:
    assert render_json(build_inventory(_FIXTURES_ROOT / "good")).isascii()


# ---------------------------------------------------------------------------
# US3 -- human-gated / deferred / provenance truthfulness (T011)
# ---------------------------------------------------------------------------


def test_human_gated_not_automated() -> None:
    records = build_inventory(_FIXTURES_ROOT / "good")
    by_id = {r["id"]: r for r in records}
    assert by_id["fixture-human-gated"]["group"] == "human-gated"
    rendered = render_human(records)
    section = rendered.split("Human-gated", 1)[1].split("Deferred", 1)[0]
    assert "(human action)" in section
    assert "retail check" not in section  # no automated command implied


def test_deferred_never_shipped_group() -> None:
    records = build_inventory(_FIXTURES_ROOT / "good")
    by_id = {r["id"]: r for r in records}
    entry = by_id["fixture-deferred"]
    assert entry["group"] == "deferred"
    assert entry["state"] == "deferred"
    rendered = render_human(records)
    deferred_section = rendered.split("Deferred / not shipped", 1)[1]
    available_section = rendered.split("Available now", 1)[1].split(
        "Requires database", 1
    )[0]
    assert entry["name"] in deferred_section
    assert entry["name"] not in available_section


def test_provenance_verbatim_never_upgraded() -> None:
    records = build_inventory(_FIXTURES_ROOT / "good")
    by_id = {r["id"]: r for r in records}
    assert by_id["fixture-unrecorded-provenance"]["provenance"] == "unrecorded"
    assert "publicly-released" not in render_human(records)


# ---------------------------------------------------------------------------
# US5 -- no new CLI verb; no write/DB; no readiness-status read (T015)
# ---------------------------------------------------------------------------


def test_no_new_cli_verb() -> None:
    from seshat.cli import _DISPATCH
    from seshat.cli.parser import _build_parser

    assert "capabilities" not in _DISPATCH
    assert "capabilities" not in _build_parser().format_help()


_BANNED_DRIVER_MODULES = {
    "psycopg2",
    "pyodbc",
    "mysql.connector",
    "snowflake.connector",
}


def _open_mode_arg(node: ast.Call) -> ast.expr | None:
    """The ``mode`` value of an ``open(...)`` call (keyword or positional 2nd
    arg), or None (``open(path)`` defaults to read)."""
    for kw in node.keywords:
        if kw.arg == "mode":
            return kw.value
    for arg in node.args[1:2]:
        return arg
    return None


def _write_attr_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Attribute) and func.attr in ("write_text", "write_bytes"):
        return func.attr
    return None


def _open_call_writes(func: ast.expr, node: ast.Call) -> bool:
    if not (isinstance(func, ast.Name) and func.id == "open"):
        return False
    mode_arg = _open_mode_arg(node)
    if not (isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str)):
        return False
    return "w" in mode_arg.value


def _assert_no_write_calls(tree: ast.Module, mod_name: str) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        write_attr = _write_attr_name(node.func)
        assert write_attr is None, f"{mod_name} calls {write_attr} -- write path found"
        assert not _open_call_writes(node.func, node), f"{mod_name}: open() write mode"


def _assert_no_driver_imports(tree: ast.Module, mod_name: str) -> None:
    """No banned DB-driver import at MODULE SCOPE (top-level statements only)."""
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in _BANNED_DRIVER_MODULES, mod_name
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module not in _BANNED_DRIVER_MODULES, mod_name


def test_no_write_no_db() -> None:
    import seshat.capability_feeders as feeders_module
    import seshat.capability_inventory as module

    for mod in (module, feeders_module):
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        _assert_no_write_calls(tree, mod.__name__)
        _assert_no_driver_imports(tree, mod.__name__)


def test_reads_no_readiness_state() -> None:
    """FR-011: the module reads no PER-TABLE ``mappings/<table>/readiness-status.yaml``
    run-state. ``templates/readiness-status.yaml`` (the stage-token vocabulary,
    D5) is a different, sanctioned file. The banned marker is the per-table glob
    + the run-state keys every readiness-consuming surface uses."""
    import seshat.capability_feeders as feeders_module
    import seshat.capability_inventory as module

    for mod in (module, feeders_module):
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "mappings" not in source
        assert "current_stage" not in source
        assert "blocking_reasons" not in source
        assert "next_action" not in source


# ---------------------------------------------------------------------------
# Generic / no hardcoded onboarded-table token (T018); README distinction (T017)
# ---------------------------------------------------------------------------


def test_generic_no_hardcoded_table() -> None:
    banned_tokens = ("c086", "C086", "retail_store_sales")
    sources = [
        Path(feeders.__file__).read_text(encoding="utf-8"),
        (_REPO_ROOT / "src" / "seshat" / "capability_inventory.py").read_text(
            encoding="utf-8"
        ),
        (_REPO_ROOT / "docs" / "capabilities" / "capabilities.yaml").read_text(
            encoding="utf-8"
        ),
    ]
    for token in banned_tokens:
        for source in sources:
            assert token not in source


def test_readme_names_four_authorities() -> None:
    """SC-008 / FR-017: the README names status, next, doctor, AND check."""
    readme = (_REPO_ROOT / "docs" / "capabilities" / "README.md").read_text(
        encoding="utf-8"
    )
    for authority in ("seshat status", "seshat next", "seshat doctor", "retail check"):
        assert authority in readme, f"README does not name {authority!r}"
