"""US2/SC-003: the per-table build engine resolves fail-closed to migrations.

The engine flag lives in the human-reviewed committed working set
(mappings/<table>/build-engine.yaml, FR-001/plan-review R1); only the exact
value ``dbt`` engages the dbt engine. Absent file, malformed YAML, non-mapping,
absent layer key, or any other value -> ``migrations``. No exception may leak a
path or secret. The resolver is imported through the orchestration re-export so
the SAME tested implementation the doctor uses is exercised here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tower_bi_orchestration.engine import resolve_build_engine

TABLE = "demo_table"


def _write_engine_file(root: Path, body: str) -> None:
    table_dir = root / "mappings" / TABLE
    table_dir.mkdir(parents=True, exist_ok=True)
    (table_dir / "build-engine.yaml").write_text(body, encoding="utf-8")


@pytest.mark.parametrize("layer", ["silver", "gold"])
def test_absent_file_resolves_to_migrations(tmp_path: Path, layer: str) -> None:
    (tmp_path / "mappings" / TABLE).mkdir(parents=True)
    assert resolve_build_engine(tmp_path, TABLE, layer) == "migrations"


@pytest.mark.parametrize("layer", ["silver", "gold"])
def test_explicit_migrations_resolves_to_migrations(tmp_path: Path, layer: str) -> None:
    _write_engine_file(tmp_path, "silver: migrations\ngold: migrations\n")
    assert resolve_build_engine(tmp_path, TABLE, layer) == "migrations"


@pytest.mark.parametrize("layer", ["silver", "gold"])
def test_explicit_dbt_resolves_to_dbt(tmp_path: Path, layer: str) -> None:
    _write_engine_file(tmp_path, "silver: dbt\ngold: dbt\n")
    assert resolve_build_engine(tmp_path, TABLE, layer) == "dbt"


def test_mixed_engines_resolve_independently_per_layer(tmp_path: Path) -> None:
    _write_engine_file(tmp_path, "silver: dbt\ngold: migrations\n")
    assert resolve_build_engine(tmp_path, TABLE, "silver") == "dbt"
    assert resolve_build_engine(tmp_path, TABLE, "gold") == "migrations"


@pytest.mark.parametrize(
    "body",
    [
        "silver: DBT\n",  # wrong case is not the exact token
        "silver: dbt-engine\n",  # superstring is not exact
        "silver: postgres\n",  # unrecognized value
        "silver: 42\n",  # non-string scalar
        "silver: [dbt]\n",  # non-scalar value
        "silver: {}\n",  # empty mapping value
    ],
)
def test_unrecognized_value_fails_closed_to_migrations(
    tmp_path: Path, body: str
) -> None:
    _write_engine_file(tmp_path, body)
    assert resolve_build_engine(tmp_path, TABLE, "silver") == "migrations"


@pytest.mark.parametrize(
    "body",
    [
        "silver: dbt\n  bad indent\n",  # invalid YAML
        "- just\n- a\n- list\n",  # top-level sequence, not a mapping
        "just a scalar\n",  # top-level scalar
        "",  # empty document
    ],
)
def test_malformed_document_fails_closed_to_migrations(
    tmp_path: Path, body: str
) -> None:
    _write_engine_file(tmp_path, body)
    assert resolve_build_engine(tmp_path, TABLE, "silver") == "migrations"


@pytest.mark.parametrize("bad", ["../escape", "Bad_Table", "1table", "with space"])
def test_unsafe_table_id_fails_closed(tmp_path: Path, bad: str) -> None:
    assert resolve_build_engine(tmp_path, bad, "silver") == "migrations"


def test_unsafe_layer_fails_closed(tmp_path: Path) -> None:
    _write_engine_file(tmp_path, "silver: dbt\n")
    assert resolve_build_engine(tmp_path, TABLE, "../etc") == "migrations"


def test_resolution_never_leaks_the_path_on_a_broken_file(tmp_path: Path) -> None:
    # A resolver that raised and surfaced the absolute path would leak it into a
    # traceback the unattended asset records. The contract is: never raise.
    secret_dir = tmp_path / "mappings" / TABLE
    secret_dir.mkdir(parents=True)
    (secret_dir / "build-engine.yaml").write_text("silver: dbt\n\t: broken\n")
    # Must return a value (not raise); the fail-closed default on malformed input.
    assert resolve_build_engine(tmp_path, TABLE, "silver") == "migrations"
