"""Live-DB provenance records describe PASSING runs and are read from HEAD.

Pins the hardening on top of the #485 A2 record:

  * a validate run with ERROR findings records nothing, so it can never replace
    the record a passing run earned against another database;
  * the reader compares only a COMMITTED record, and only while the record's
    source-map digest equals the committed source-map's;
  * a record is written only for ``<repo>/mappings/<table>/source-map.yaml``;
  * the `.env` a live verb applies is the one under ``--repo``.

The "forged record" cases below write a record exactly as a claimant would: the
right labels, the digest recomputed offline from the configuration, and the
right source-map digest. A label-only forgery would prove nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import pytest

from seshat import db_provenance, db_provenance_reader, run_next
from seshat.core import Finding, Severity
from seshat.dialect import get_dialect
from tests.unit.test_db_provenance_485 import (
    _DB,
    _OTHER_DB,
    _SOURCE_MAP_TEXT,
    _commit,
    _dsn,
    _record,
    _repo,
)

pytestmark = pytest.mark.unit

_TABLE = "sales_c086_raw"
_MAP = f"mappings/{_TABLE}/source-map.yaml"


@pytest.fixture(autouse=True)
def _no_ambient_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DATABASE_URL",
        "ANALYTICS_DB_ENGINE",
        "ANALYTICS_DB_HOST",
        "ANALYTICS_DB_NAME",
        "ANALYTICS_DB_PORT",
        "ANALYTICS_DB_USER",
        "ANALYTICS_DB_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)


class _ServerFor:
    """A fake connection whose server names ``database`` for the identity query."""

    def __init__(self, database: str) -> None:
        self.database = database

    def run(self, sql: str, params: tuple = ()) -> list[tuple]:
        return [("10.0.0.5:25060", self.database)]


def _offline_digest(text: str) -> str:
    """The source-map digest, recomputed by hand the way a claimant could."""
    normalized = text.replace("\r\n", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def _forged_record(dsn: str) -> dict:
    """A correctly-labelled record built WITHOUT any live connection."""
    return {
        "schema_version": 2,
        "table": _TABLE,
        "engine": "postgres",
        "source": "server_echo",
        "outcome": "pass",
        "database_name_server_confirmed": True,
        "identity_components": list(db_provenance.IDENTITY_COMPONENTS),
        "database_identity_digest": db_provenance.digest_for_dsn(dsn),
        "digest_algorithm": "sha256-unsalted-truncated-32",
        "source_map_digest": _offline_digest(_SOURCE_MAP_TEXT),
    }


def _validate(
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
    *,
    database: str,
    findings: list[Finding],
) -> int:
    """Run the validate handler against a fake server naming ``database``."""
    from seshat import cli
    from seshat.cli.commands.validate import run_validate

    monkeypatch.setattr(cli, "_ensure_driver", lambda: True)
    monkeypatch.setattr(cli, "_load_targets", lambda _path: object())
    monkeypatch.setattr(
        cli, "_make_runner", lambda _config, **_kw: _ServerFor(database)
    )
    monkeypatch.setattr(
        "seshat.validate.run_live_checks", lambda *_a, **_kw: list(findings)
    )
    args = argparse.Namespace(
        dsn=_dsn(database=database), source_map=_MAP, repo=str(repo), prog="seshat"
    )
    return run_validate(args)


def _point_env_at(repo: Path, dsn: str) -> None:
    (repo / ".env").write_text(f"DATABASE_URL={dsn}\n", encoding="utf-8")


def test_a_failing_run_never_replaces_the_record_a_passing_run_earned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pass against A, then FAIL against B, both committed: the reader pointed at
    B must see A's record (a mismatch), never a 'verified' agreement with B."""
    repo = _repo(tmp_path, dsn=None, record=None)
    monkeypatch.chdir(repo)
    assert _validate(monkeypatch, repo, database=_DB, findings=[]) == 0
    _commit(repo)
    record_path = db_provenance.record_path(repo, _TABLE)
    earned = record_path.read_bytes()

    failing = Finding(
        rule_id="V-RC2", severity=Severity.ERROR, message="dup PK", locator="t"
    )
    assert _validate(monkeypatch, repo, database=_OTHER_DB, findings=[failing]) == 1
    _commit(repo)
    _point_env_at(repo, _dsn(database=_OTHER_DB))

    assert record_path.read_bytes() == earned
    verdict, _ = db_provenance_reader.provenance_verdict(repo, _TABLE)
    assert verdict == "mismatch"
    response = run_next.build_run_next_response(repo, _TABLE)
    kinds = {caveat["kind"] for caveat in response["caveats"]}
    assert db_provenance_reader.CAVEAT_KIND_VERIFIED not in kinds


def test_a_passing_run_records_outcome_and_the_source_map_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path, dsn=None, record=None)
    monkeypatch.chdir(repo)

    assert _validate(monkeypatch, repo, database=_DB, findings=[]) == 0

    record = json.loads(db_provenance.record_path(repo, _TABLE).read_text("utf-8"))
    assert record["outcome"] == "pass"
    assert record["source_map_digest"] == _offline_digest(_SOURCE_MAP_TEXT)


def test_an_uncommitted_forged_record_is_not_reported_as_verified(
    tmp_path: Path,
) -> None:
    """Correct labels + an offline-computed digest, dropped into the worktree."""
    repo = _repo(tmp_path, dsn=_dsn(), record=None)
    record_path = db_provenance.record_path(repo, _TABLE)
    record_path.write_text(json.dumps(_forged_record(_dsn())), encoding="utf-8")

    verdict, _ = db_provenance_reader.provenance_verdict(repo, _TABLE)
    response = run_next.build_run_next_response(repo, _TABLE)

    assert verdict == "absent"
    kinds = {caveat["kind"] for caveat in response["caveats"]}
    assert db_provenance_reader.CAVEAT_KIND_VERIFIED not in kinds
    assert run_next._PROVENANCE_CAVEAT_KIND in kinds


def test_a_committed_forged_record_matches_and_says_it_is_no_proof(
    tmp_path: Path,
) -> None:
    """The documented limit: offline, a committed record with the right labels
    cannot be told apart from a written one. The caveat must not claim more."""
    repo = _repo(tmp_path, dsn=_dsn(), record=None)
    record_path = db_provenance.record_path(repo, _TABLE)
    record_path.write_text(json.dumps(_forged_record(_dsn())), encoding="utf-8")
    _commit(repo)

    verdict, _ = db_provenance_reader.provenance_verdict(repo, _TABLE)
    detail = db_provenance_reader.verified_caveat("gold_ready")["detail"]

    assert verdict == "match"
    assert "not a proof" in detail
    assert "COMMITTED" in detail
    assert "server's own report" not in detail


@pytest.mark.parametrize(
    "overrides",
    [{"outcome": "fail"}, {"outcome": None}, {"source_map_digest": None}],
    ids=["failed-run", "schema-1-no-outcome", "no-source-map-digest"],
)
def test_a_record_not_describing_a_passing_run_is_not_comparable(
    tmp_path: Path, overrides: dict
) -> None:
    record = {k: v for k, v in _record(**overrides).items() if v is not None}
    repo = _repo(tmp_path, dsn=_dsn(), record=record)

    verdict, detail = db_provenance_reader.provenance_verdict(repo, _TABLE)

    assert verdict == "uncomparable"
    assert detail == db_provenance.UNCOMPARABLE_BAD_RECORD


def test_a_record_over_a_since_changed_source_map_is_not_comparable(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, dsn=_dsn(), record=_record())
    (repo / _MAP).write_text(_SOURCE_MAP_TEXT + "gold_star: {}\n", encoding="utf-8")
    _commit(repo)

    verdict, detail = db_provenance_reader.provenance_verdict(repo, _TABLE)

    assert verdict == "uncomparable"
    assert detail == db_provenance.UNCOMPARABLE_STALE_MAP


def test_the_source_map_digest_ignores_checkout_line_endings_and_bom() -> None:
    lf = db_provenance.source_map_digest(_SOURCE_MAP_TEXT)

    assert db_provenance.source_map_digest(_SOURCE_MAP_TEXT.replace("\n", "\r\n")) == lf
    assert db_provenance.source_map_digest("﻿" + _SOURCE_MAP_TEXT) == lf


def test_a_foreign_source_map_with_a_colliding_directory_name_is_refused(
    tmp_path: Path,
) -> None:
    """A map OUTSIDE <repo>/mappings/ validated other targets; its run must not be
    attributed to the local table that merely shares its directory name."""
    from seshat.db_provenance_writer import LiveRunContext, record_live_run

    repo = _repo(tmp_path / "a", dsn=None, record=None)
    foreign = tmp_path / "candidate" / _TABLE / "source-map.yaml"
    foreign.parent.mkdir(parents=True)
    foreign.write_text(_SOURCE_MAP_TEXT, encoding="utf-8")
    notes = io.StringIO()

    written = record_live_run(
        LiveRunContext(
            repo_root=repo,
            source_map=str(foreign),
            runner=_ServerFor(_DB),
            dialect=get_dialect("postgres"),
            configured_dsn=_dsn(),
            engine="postgres",
            stream=notes,
        )
    )

    assert written is None
    assert not db_provenance.record_path(repo, _TABLE).exists()
    assert "mappings/<table>/source-map.yaml" in notes.getvalue()


def test_validate_applies_the_env_under_repo_not_the_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Run from elsewhere with --repo: the repo's `.env` supplies the connection."""
    from seshat import cli
    from seshat.cli.commands.validate import run_validate

    repo = _repo(tmp_path / "ws", dsn=_dsn(), record=None)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(cli, "_ensure_driver", lambda: False)

    code = run_validate(
        argparse.Namespace(dsn=None, source_map=None, repo=str(repo), prog="seshat")
    )

    assert code == 1
    err = capsys.readouterr().err
    assert "no database connection configured" not in err
    assert "needs the optional DB driver" in err
