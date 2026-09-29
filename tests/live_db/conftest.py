"""Fixtures + honest-skip precondition chain for the local live-validation suite.

Spec 082 (``specs/082-postgres-live-validation-suite/``); the precondition contract
is ``contracts/live-pass-contract.md``.

The single load-bearing rule (FR-009, hard "no hidden live pass"): a live check may
report a completed live outcome ONLY when ALL five preconditions hold. Any failure
collapses to ``pytest.skip(reason=<named reason>)`` -- never a pass, never a silent
omission, never a swallowed exception. The five named reasons are mutually distinct
so a reviewer can tell which precondition failed without reading source.

testcontainers is imported LAZILY inside ``_start_container`` (never at module
scope), and each live_db test module ``pytest.importorskip``s it, so pytest can
COLLECT this suite even when the ``livetest`` extra is not installed (e.g. in CI,
which installs only ``dev``). Collection-import failure would be a hard error, not a
skip -- the lazy import + importorskip is what keeps the honest-skip promise real.
"""

from __future__ import annotations

import importlib.metadata
import json
import os
import pathlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

import pytest

_SEEDS_DIR = pathlib.Path(__file__).parent / "seeds"

# The five named precondition-failure reasons (contracts/live-pass-contract.md).
# Kept as a module constant so the runtime chain and the US4 mock tests agree on the
# exact strings (a reviewer acts on these; genericness would defeat FR-014).
REASON_DOCKER = "docker not available"
REASON_DRIVER = "driver not installed"
REASON_CONTAINER = "container failed to start"
REASON_PORT = "port conflict"
REASON_SEED = "seed failed"
REASON_DBT_PENDING = "[PENDING LIVE PROFILE]"


def dbt_runtime_available() -> bool:
    """Return whether the exact governed dbt pair and executable are installed."""

    try:
        from seshat.dbt import DBT_CORE_VERSION, DBT_POSTGRES_VERSION
        from seshat.dbt.runner import resolve_dbt_executable

        installed = (
            importlib.metadata.version("dbt-core"),
            importlib.metadata.version("dbt-postgres"),
        )
        resolve_dbt_executable()
    except (
        ImportError,
        importlib.metadata.PackageNotFoundError,
        OSError,
        RuntimeError,
    ):
        return False
    return installed == (DBT_CORE_VERSION, DBT_POSTGRES_VERSION)


@dataclass(frozen=True)
class ContainerHandle:
    """A ready, seeded ephemeral Postgres container (data-model.md section 3).

    ``dsn`` is valid only for the container's lifetime; never logged unredacted.
    """

    dsn: str


@dataclass(frozen=True)
class LiveParityRow:
    assertion_id: str
    passed: bool


@dataclass(frozen=True)
class LiveBlocker:
    assertion_id: str | None


@dataclass(frozen=True)
class LiveDbtEvidence:
    outcome: str
    parity: tuple[LiveParityRow, ...]
    blocking_reasons: tuple[LiveBlocker, ...]


class LiveDbtProject:
    """Disposable Git checkout bound to one ephemeral Postgres database."""

    _MUTATIONS = {
        "delete_fact": """
            DELETE FROM gold.fct_sales_rss
            WHERE transaction_id = (
                SELECT min(transaction_id) FROM gold.fct_sales_rss
            );
        """,
        "duplicate_business_key": """
            ALTER TABLE gold.fct_sales_rss
                DROP CONSTRAINT uq_fct_rss_transaction_id;
            WITH ids AS (
                SELECT min(transaction_id) AS keep_id,
                       max(transaction_id) AS change_id
                FROM gold.fct_sales_rss
            )
            UPDATE gold.fct_sales_rss AS fact
            SET transaction_id = ids.keep_id
            FROM ids
            WHERE fact.transaction_id = ids.change_id;
        """,
        "change_money": """
            UPDATE gold.fct_sales_rss
            SET total_spent = total_spent + 1.00
            WHERE transaction_id = (
                SELECT min(transaction_id) FROM gold.fct_sales_rss
            );
        """,
        "remove_unknown_member": """
            ALTER TABLE gold.fct_sales_rss
                DROP CONSTRAINT fk_fct_rss_product;
            DELETE FROM gold.dim_product_rss WHERE product_sk = -1;
        """,
    }

    def __init__(
        self,
        repo_root: pathlib.Path,
        dsn: str,
        environment: dict[str, str],
    ) -> None:
        self.repo_root = repo_root
        self.dsn = dsn
        self.environment = environment

    def _cli(
        self,
        command: str,
        *arguments: str,
        expected_codes: set[int] | None = None,
    ) -> dict:
        expected = expected_codes or {0}
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "seshat.cli",
                "dbt",
                command,
                *arguments,
                "--repo",
                str(self.repo_root),
                "--format",
                "json",
            ],
            cwd=self.repo_root,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=300,
        )
        assert completed.returncode in expected, (
            f"governed dbt {command} returned {completed.returncode}"
        )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"governed dbt {command} did not return JSON") from exc
        assert isinstance(payload, dict)
        return payload

    def verify_prerequisites(self) -> None:
        self._cli("doctor")
        self._cli("validate", "--table", "retail_store_sales")

    def _reset_migration_oracle(self) -> None:
        _run_sql_file(
            self.dsn,
            self.repo_root
            / "warehouse/migrations/0003_create_silver_retail_store_sales.sql",
        )
        _run_sql_file(
            self.dsn,
            self.repo_root
            / "warehouse/migrations/0004_create_gold_retail_store_sales_star.sql",
        )
        # 0010 is 0004's follow-up (unpadded month/day labels); the oracle must
        # apply it so it matches the dbt shadow model, which emits FM labels.
        _run_sql_file(
            self.dsn,
            self.repo_root
            / "warehouse/migrations/0010_fix_gold_retail_store_sales_date_labels.sql",
        )

    def _evidence(self, result: dict) -> LiveDbtEvidence:
        relative = result.get("evidence_path")
        assert isinstance(relative, str) and relative
        payload = json.loads((self.repo_root / relative).read_text(encoding="utf-8"))
        return LiveDbtEvidence(
            outcome=payload["outcome"],
            parity=tuple(
                LiveParityRow(row["assertion_id"], row["passed"])
                for row in payload["parity"]
            ),
            blocking_reasons=tuple(
                LiveBlocker(row.get("assertion_id"))
                for row in payload["blocking_reasons"]
            ),
        )

    def _build(self, table_id: str, mutation: str | None) -> LiveDbtEvidence:
        assert table_id == "retail_store_sales"
        self._reset_migration_oracle()
        plan = self._cli("plan", "--table", table_id)
        digest = plan.get("digest")
        assert isinstance(digest, str) and len(digest) == 64
        if mutation is not None:
            sql = self._MUTATIONS[mutation]
            _run_sql(self.dsn, sql)
        result = self._cli(
            "build",
            "--table",
            table_id,
            "--accept-plan",
            digest,
            expected_codes={0, 1},
        )
        return self._evidence(result)

    def build(self, table_id: str) -> LiveDbtEvidence:
        return self._build(table_id, None)

    def build_with_mutation(
        self, mutation: str, table_id: str = "retail_store_sales"
    ) -> LiveDbtEvidence:
        assert mutation in self._MUTATIONS
        return self._build(table_id, mutation)


def docker_available() -> tuple[bool, str | None]:
    """Pure, mockable Docker-availability probe.

    Returns ``(True, None)`` when a Docker client can be constructed and pinged,
    else ``(False, REASON_DOCKER)``. Imports the docker client lazily so this
    module collects without the ``livetest`` extra. Never raises: any failure is
    reported as unavailable, so the caller skips honestly rather than erroring.
    """
    try:
        import docker  # lazy: only when actually probing
    except Exception:
        return (False, REASON_DOCKER)
    try:
        client = docker.from_env()
        client.ping()
        return (True, None)
    except Exception:
        return (False, REASON_DOCKER)


def driver_available() -> tuple[bool, str | None]:
    """Pure, mockable psycopg2-availability probe (precondition #2).

    Distinct from Docker availability: the pytest environment may have Docker but
    not the ``db`` extra. Returns ``(True, None)`` or ``(False, REASON_DRIVER)``.
    """
    try:
        import psycopg2  # noqa: F401  -- import-presence probe only
    except Exception:
        return (False, REASON_DRIVER)
    return (True, None)


def _run_sql_file(dsn: str, sql_path: pathlib.Path) -> None:
    """Execute a .sql file against ``dsn`` via psycopg2 (precondition #4 helper).

    Raises on any SQL error so the fixture can map it to REASON_SEED. psycopg2 is
    imported lazily -- this helper is only reached after ``driver_available()`` held.
    """
    import psycopg2  # lazy

    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text(encoding="utf-8"))
    finally:
        conn.close()


def _run_sql(dsn: str, sql: str) -> None:
    """Execute inline synthetic-test SQL without exposing the ephemeral DSN."""
    import psycopg2  # lazy

    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.close()


def seed_container(handle: ContainerHandle, scenario_file: str) -> None:
    """Run schema.sql then the named scenario .sql against the container.

    Raises on SQL error (the fixture maps that to a REASON_SEED skip). Kept as a
    standalone function so a US4 test can mock it to force the seed-failure path.
    """
    _run_sql_file(handle.dsn, _SEEDS_DIR / "schema.sql")
    _run_sql_file(handle.dsn, _SEEDS_DIR / scenario_file)


def _start_container():
    """Start an ephemeral Postgres container, returning (dsn, stop_callable).

    testcontainers is imported HERE, lazily -- never at module scope -- so this file
    collects without the ``livetest`` extra installed. Raises on start failure; the
    fixture maps a timeout/start error to REASON_CONTAINER and a bind error to
    REASON_PORT.
    """
    from testcontainers.postgres import PostgresContainer  # lazy

    container = PostgresContainer("postgres:16-alpine")
    container.start()
    dsn = container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    return dsn, container.stop


@pytest.fixture
def live_db_container(request):
    """The single fixture every US1-US3 live test depends on.

    Walks the five preconditions in contract order; on the first failure it
    ``pytest.skip``s with that precondition's named reason. Only when all hold does
    it yield a ready, seeded ``ContainerHandle``. Teardown always stops the
    container, even on a mid-test failure.

    The scenario seed file is passed via ``@pytest.mark.seed("seed_clean.sql")`` on
    the test (or defaults to ``seed_clean.sql``).
    """
    marker = request.node.get_closest_marker("seed")
    scenario_file = marker.args[0] if marker else "seed_clean.sql"

    ok, reason = docker_available()
    if not ok:
        pytest.skip(reason)
    ok, reason = driver_available()
    if not ok:
        pytest.skip(reason)

    try:
        dsn, stop = _start_container()
    except Exception as exc:  # start/bind failure -> honest skip, never a pass
        text = str(exc).lower()
        if "port" in text or "address already in use" in text or "bind" in text:
            pytest.skip(REASON_PORT)
        pytest.skip(REASON_CONTAINER)
        return  # unreachable; keeps type-checkers happy

    handle = ContainerHandle(dsn=dsn)
    try:
        try:
            seed_container(handle, scenario_file)
        except Exception:
            pytest.skip(REASON_SEED)
        yield handle
    finally:
        stop()


def _dbt_child_environment(dsn: str, repo_root: pathlib.Path) -> dict[str, str]:
    parsed = urlsplit(dsn)
    assert parsed.hostname and parsed.port and parsed.username and parsed.password
    database = parsed.path.lstrip("/")
    assert database
    environment = dict(os.environ)
    environment.update(
        {
            "SESHAT_DBT_HOST": parsed.hostname,
            "SESHAT_DBT_PORT": str(parsed.port),
            "SESHAT_DBT_USER": unquote(parsed.username),
            "SESHAT_DBT_PASSWORD": unquote(parsed.password),
            "SESHAT_DBT_DBNAME": database,
            "SESHAT_DBT_SCHEMA": "seshat_live_shadow",
            "SESHAT_DBT_SSLMODE": "disable",
            "PYTHONPATH": str(repo_root / "src"),
        }
    )
    return environment


@pytest.fixture(scope="module")
def live_dbt_project(tmp_path_factory):
    """One disposable database + checkout for the feature-133 parity suite."""
    if not dbt_runtime_available():
        pytest.skip(f"{REASON_DBT_PENDING}: install the pinned dbt extra")
    ok, reason = docker_available()
    if not ok:
        pytest.skip(f"{REASON_DBT_PENDING}: {reason}")
    ok, reason = driver_available()
    if not ok:
        pytest.skip(f"{REASON_DBT_PENDING}: {reason}")

    try:
        dsn, stop = _start_container()
    except Exception as exc:
        text = str(exc).lower()
        detail = (
            REASON_PORT
            if ("port" in text or "address already in use" in text or "bind" in text)
            else REASON_CONTAINER
        )
        pytest.skip(f"{REASON_DBT_PENDING}: {detail}")

    source_root = pathlib.Path(__file__).resolve().parents[2]
    checkout = tmp_path_factory.mktemp("dbt-live") / "repo"
    handle = ContainerHandle(dsn=dsn)
    try:
        seed_container(handle, "dbt_retail_store_sales.sql")
        clone = subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-hardlinks",
                str(source_root),
                str(checkout),
            ],
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=120,
        )
        assert clone.returncode == 0, "temporary local Git clone failed"
        shutil.copy2(checkout / "profiles.example.yml", checkout / "profiles.yml")
        project = LiveDbtProject(
            checkout,
            dsn,
            _dbt_child_environment(dsn, source_root),
        )
        project.verify_prerequisites()
        yield project
    finally:
        stop()
