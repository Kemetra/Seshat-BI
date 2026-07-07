"""Tests for `retail.status_surface` (spec 109, roadmap M4, Option B).

The status surface is a READ-ONLY projection of committed
``mappings/<table>/readiness-status.yaml`` state -- it introduces no new
readiness logic, computes no numeric score, and never fabricates a stage
grant. These tests exercise the pure ``build_status_projection`` function
directly (no CLI, no subprocess).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from retail.status_surface import build_status_projection

pytestmark = pytest.mark.unit

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "agent-status.schema.json"
)


# --- a tiny stdlib-only JSON Schema validator (no `jsonschema` dependency) --------
# Covers exactly the constructs this repo's schema uses: object/array/string/null
# types, `required`, `properties`, `additionalProperties: false`, `items`, `enum`,
# and one level of `$defs` + `$ref`. Not a general-purpose validator.


def _resolve_ref(schema: dict, root: dict) -> dict:
    ref = schema.get("$ref")
    if ref is None:
        return schema
    assert ref.startswith("#/"), f"unsupported $ref: {ref}"
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _check_type(value: object, types: object) -> bool:
    allowed = types if isinstance(types, list) else [types]
    checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "null": lambda v: v is None,
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
    }
    return any(checks[t](value) for t in allowed)


def _check_required(value: dict, schema: dict, path: str) -> list[str]:
    return [
        f"{path}: missing required key {key!r}"
        for key in schema.get("required", [])
        if key not in value
    ]


def _check_no_extra_keys(value: dict, schema: dict, path: str) -> list[str]:
    if schema.get("additionalProperties") is not False:
        return []
    allowed = set(schema.get("properties", {}))
    return [f"{path}: unexpected key {key!r}" for key in value if key not in allowed]


def _validate_named_props(
    value: dict, schema: dict, root: dict, path: str
) -> list[str]:
    props = schema.get("properties", {})
    return [
        e
        for key, subschema in props.items()
        if key in value
        for e in _validate(value[key], subschema, root, f"{path}.{key}")
    ]


def _validate_additional_props(
    value: dict, schema: dict, root: dict, path: str
) -> list[str]:
    additional = schema.get("additionalProperties")
    if not isinstance(additional, dict):
        return []
    props = schema.get("properties", {})
    return [
        e
        for key, val in value.items()
        if key not in props
        for e in _validate(val, additional, root, f"{path}.{key}")
    ]


def _validate_object(value: dict, schema: dict, root: dict, path: str) -> list[str]:
    return (
        _check_required(value, schema, path)
        + _check_no_extra_keys(value, schema, path)
        + _validate_named_props(value, schema, root, path)
        + _validate_additional_props(value, schema, root, path)
    )


def _validate_items(value: list, schema: dict, root: dict, path: str) -> list[str]:
    if "items" not in schema:
        return []
    return [
        e
        for i, item in enumerate(value)
        for e in _validate(item, schema["items"], root, f"{path}[{i}]")
    ]


def _validate_enum(value: object, schema: dict, path: str) -> list[str]:
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}: {value!r} not in enum {schema['enum']}"]
    return []


def _validate(value: object, schema: dict, root: dict, path: str = "$") -> list[str]:
    schema = _resolve_ref(schema, root)

    if "type" in schema and not _check_type(value, schema["type"]):
        got = type(value).__name__
        return [f"{path}: expected type {schema['type']}, got {got}"]

    errors = _validate_enum(value, schema, path)
    if isinstance(value, dict):
        errors += _validate_object(value, schema, root, path)
    elif isinstance(value, list):
        errors += _validate_items(value, schema, root, path)
    return errors


def assert_matches_schema(instance: dict, schema: dict) -> None:
    errors = _validate(instance, schema, schema)
    assert errors == [], f"schema violations: {errors}"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# --- fixtures ----------------------------------------------------------------

_MINIMAL_STAGES = """\
  source_ready:
    {status: "pass", evidence: ["source-profile.md"], blocking_reasons: []}
  mapping_ready:
    {status: "blocked", evidence: [], blocking_reasons: ["grain not confirmed"]}
  silver_ready: {status: "not_started", evidence: [], blocking_reasons: []}
  gold_ready: {status: "not_started", evidence: [], blocking_reasons: []}
  semantic_model_ready: {status: "not_started", evidence: [], blocking_reasons: []}
  dashboard_ready: {status: "not_started", evidence: [], blocking_reasons: []}
  publish_ready: {status: "not_started", evidence: [], blocking_reasons: []}
"""


def _write_status(tmp_path: Path, table_dir: str, *, extra: str = "") -> Path:
    rel = Path("mappings") / table_dir / "readiness-status.yaml"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""\
table: "silver.{table_dir}"
source_id: "{table_dir}"
source_family: "example_erp"
current_stage: "mapping_ready"
stages:
{_MINIMAL_STAGES}
blocking_reasons: ["grain not confirmed"]
approvals: []
next_action: "resolve open grain question"
last_checked_at: "2026-07-01"
checked_by: "agent"
{extra}
""",
        encoding="utf-8",
    )
    return path


# --- tests ---------------------------------------------------------------------


def test_empty_repo_projects_empty_tables(tmp_path: Path) -> None:
    """No mappings/*/readiness-status.yaml committed -> {"tables": []}, not an error."""
    result = build_status_projection(tmp_path)
    assert result == {"tables": []}


def test_empty_projection_validates_against_schema(tmp_path: Path) -> None:
    assert_matches_schema(build_status_projection(tmp_path), _load_schema())


def test_single_table_projects_current_stage_evidence_blockers(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders")
    result = build_status_projection(tmp_path)
    assert len(result["tables"]) == 1
    table = result["tables"][0]
    assert table["table"] == "silver.orders"
    assert table["source_path"] == "mappings/orders/readiness-status.yaml"
    assert table["current_stage"] == "mapping_ready"
    assert table["next_action"] == "resolve open grain question"
    assert table["blocking_reasons"] == ["grain not confirmed"]
    assert table["stages"]["source_ready"]["status"] == "pass"
    assert table["stages"]["source_ready"]["evidence"] == ["source-profile.md"]
    assert table["stages"]["mapping_ready"]["status"] == "blocked"
    assert table["stages"]["mapping_ready"]["blocking_reasons"] == [
        "grain not confirmed"
    ]


def test_populated_projection_validates_against_schema(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders")
    _write_status(tmp_path, "customers")
    assert_matches_schema(build_status_projection(tmp_path), _load_schema())


def test_multiple_tables_are_sorted_deterministically(tmp_path: Path) -> None:
    _write_status(tmp_path, "zeta")
    _write_status(tmp_path, "alpha")
    result = build_status_projection(tmp_path)
    paths = [t["source_path"] for t in result["tables"]]
    assert paths == sorted(paths)


def test_no_field_is_a_numeric_score(tmp_path: Path) -> None:
    """Hard rule #9 / Principle V: never fabricate a confidence/health/maturity
    score. Walk the whole projection and assert no key named like a score carries
    a bare number (categorical status + named blockers only)."""
    _write_status(tmp_path, "orders")
    result = build_status_projection(tmp_path)
    dumped = json.dumps(result)
    for banned in ("score", "confidence", "health", "maturity"):
        assert banned not in dumped.lower(), f"found banned scoring term: {banned!r}"


def test_malformed_yaml_is_skipped_not_fatal(tmp_path: Path) -> None:
    """A read-only projection must not crash on a malformed source file; malformed
    entries are skipped (RS1 -- the check gate -- is the place that fails loud on
    malformed readiness-status.yaml; the status surface stays a best-effort, never-
    crashing projection)."""
    bad = tmp_path / "mappings" / "broken" / "readiness-status.yaml"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("table: [unterminated\n  bad: : :\n", encoding="utf-8")
    _write_status(tmp_path, "orders")
    result = build_status_projection(tmp_path)
    tables = [t["table"] for t in result["tables"]]
    assert tables == ["silver.orders"]


def test_malformed_stage_is_skipped_not_masked(tmp_path: Path) -> None:
    """A file that parses fine but has ONE bad stage block (non-string status /
    non-dict block): the bad stage is dropped from `stages`, the good stage still
    projects, and `current_stage` is passed through verbatim (never cross-validated
    or defaulted -- that would be new logic RS1 owns, not this projection)."""
    rel = Path("mappings") / "partial" / "readiness-status.yaml"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """\
table: "silver.partial"
current_stage: "mapping_ready"
stages:
  source_ready:
    status: "pass"
    evidence: ["profiled.md"]
  mapping_ready:
    status: 42
  broken_block: "not-a-mapping"
""",
        encoding="utf-8",
    )
    result = build_status_projection(tmp_path)
    table = result["tables"][0]
    # current_stage passed through verbatim, NOT reconciled against the dropped stage
    assert table["current_stage"] == "mapping_ready"
    # the good stage projects
    assert "source_ready" in table["stages"]
    assert table["stages"]["source_ready"]["status"] == "pass"
    # the malformed stages are ABSENT (skipped), not defaulted to a fabricated status
    assert "mapping_ready" not in table["stages"]
    assert "broken_block" not in table["stages"]
    # and the whole projection still validates against the committed schema
    assert_matches_schema(result, _load_schema())


def test_non_dict_stages_block_projects_empty(tmp_path: Path) -> None:
    """A `stages:` that is not a mapping (e.g. a scalar/list) yields an empty
    stages projection, not a crash."""
    rel = Path("mappings") / "weird" / "readiness-status.yaml"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        'table: "silver.weird"\nstages: "not-a-mapping"\n', encoding="utf-8"
    )
    result = build_status_projection(tmp_path)
    assert result["tables"][0]["stages"] == {}


def test_missing_current_stage_and_next_action_project_as_null(tmp_path: Path) -> None:
    rel = Path("mappings") / "sparse" / "readiness-status.yaml"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """\
table: "silver.sparse"
stages: {}
""",
        encoding="utf-8",
    )
    result = build_status_projection(tmp_path)
    table = result["tables"][0]
    assert table["current_stage"] is None
    assert table["next_action"] is None
    assert table["blocking_reasons"] == []
    assert table["stages"] == {}


def test_projection_is_deterministic_across_calls(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders")
    first = build_status_projection(tmp_path)
    second = build_status_projection(tmp_path)
    assert first == second


def test_does_not_write_any_file(tmp_path: Path) -> None:
    """Read-only guarantee (B1/B3, FR-004): calling the projection must not create,
    modify, or delete anything under the repo root."""
    _write_status(tmp_path, "orders")
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    build_status_projection(tmp_path)
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after
