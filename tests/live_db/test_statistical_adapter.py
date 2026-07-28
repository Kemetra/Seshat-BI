"""Optional live proof for the read-only governed statistical Gold adapter."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

pytest.importorskip("testcontainers")

from seshat.dialect import PostgresDialect  # noqa: E402
from seshat.statistical.contracts import Outcome  # noqa: E402
from seshat.statistical.providers.gold import GoldProvider  # noqa: E402
from seshat.statistical.runtime import run_analysis  # noqa: E402
from seshat.statistical.schema import load_analysis_spec  # noqa: E402
from seshat.validate import make_psycopg2_runner  # noqa: E402

pytestmark = [pytest.mark.live_db, pytest.mark.statistics]

_ROOT = Path(__file__).parents[2]
_FIXTURE = _ROOT / "tests/fixtures/statistical/full_flow"
_FORBIDDEN = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|MERGE)\b",
    re.IGNORECASE,
)


class _RecordingRunner:
    def __init__(self, runner) -> None:
        self.runner = runner
        self.statements: list[str] = []

    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        self.statements.append(sql)
        return self.runner.run(sql, params)


def _materialize_synthetic_gold(dsn: str) -> None:
    import psycopg2

    values = [(float(index),) for index in range(1, 37)]
    connection = psycopg2.connect(dsn)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE gold.sample_orders (
                    metric_value double precision NOT NULL
                )
                """
            )
            cursor.executemany(
                "INSERT INTO gold.sample_orders (metric_value) VALUES (%s)",
                values,
            )
        connection.commit()
    finally:
        connection.close()


@pytest.mark.seed("seed_clean.sql")
def test_gold_provider_computes_from_a_read_only_live_session(
    live_db_container, tmp_path: Path
) -> None:
    repo = tmp_path / "statistical-live"
    shutil.copytree(_FIXTURE, repo)
    spec_path = repo / "mappings/sample_orders/analyses/weekly_signal.analysis.yaml"
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace("kind: local_csv", "kind: gold"),
        encoding="utf-8",
    )
    _materialize_synthetic_gold(live_db_container.dsn)

    live_runner = make_psycopg2_runner(live_db_container.dsn)
    assert live_runner.run("SELECT current_setting('transaction_read_only')") == [
        ("on",)
    ]
    recording = _RecordingRunner(live_runner)

    evidence = run_analysis(
        repo,
        load_analysis_spec(spec_path, repo),
        GoldProvider(recording, PostgresDialect()),
    )

    assert evidence.outcome is Outcome.COMPUTED
    assert evidence.input_provenance["provider_kind"] == "gold"
    assert evidence.input_provenance["input_count"] == 36
    assert len(recording.statements) == 2
    assert all(
        sql.lstrip().upper().startswith("SELECT") for sql in recording.statements
    )
    assert all(_FORBIDDEN.search(sql) is None for sql in recording.statements)
