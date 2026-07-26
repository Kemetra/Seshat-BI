"""A2 machine-written, server-echoed live-DB provenance (issue #485, ruling R7).

The reproduction these tests pin, from the issue: a table whose `mappings/`
evidence records seven stages `pass` -- earned against database `Ex-1` -- still
reported `terminal_pass` after `.env` was repointed at an unrelated database
`ex-3` that had no silver/gold objects at all.

The contract, per ruling R7 and its three amendments:

  * a MISMATCHING record downgrades with the named `stale_evidence_wrong_database`
    blocker;
  * a MATCHING record drops the option-B caveat;
  * an ABSENT record keeps today's behavior plus the PR #504 option-B caveat, and
    is NEVER a blocker (the legacy path -- no committed table has a record);
  * an unresolvable configuration reports cannot-compare, never agreement;
  * NO raw host, port, or database name is ever written;
  * a proxy/alias deployment (server reports a different endpoint than the config)
    does NOT mismatch for the same database -- the false-positive guard, paired
    below with the true-positive guard so neither can be blunted alone;
  * the identity query is DIALECT-provided, never a Postgres literal.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat import db_provenance, db_provenance_reader, run_next
from seshat.dialect import get_dialect

# A worked identity: the writer connected here, so the reader must agree.
_HOST = "db-postgresql-fra1-12345.b.db.example.com"
_PORT = "25060"
_DB = "Ex-1"
_OTHER_DB = "ex-3"


def _dsn(host: str = _HOST, port: str = _PORT, database: str = _DB) -> str:
    scheme = "postgresql:" + "//"
    return f"{scheme}analyst:pw" + "@" + f"{host}:{port}/{database}"


def _record(**overrides: object) -> dict:
    record = db_provenance.build_record(
        server_database_name=_DB,
        configured_host=_HOST,
        configured_port=_PORT,
        configured_database_name=_DB,
        captured_at="2026-07-26T00:00:00+00:00",
        table="sales_c086_raw",
        engine="postgres",
        server_endpoint_agreed_with_config=True,
    )
    record.update(overrides)
    return record


def _repo(
    tmp_path: Path,
    *,
    dsn: str | None,
    record: dict | None,
    table: str = "sales_c086_raw",
) -> Path:
    """A repo with one terminal-pass table, optionally a record and a `.env`.

    The readiness file is the issue's shape: all seven stages `pass` with
    shape-valid approvals, so without provenance it reports `terminal_pass`.
    """
    mapping = tmp_path / "mappings" / table
    mapping.mkdir(parents=True)
    stages = "\n".join(
        f"  {name}:\n"
        f'    status: "pass"\n'
        f'    evidence: ["migration applied to Ex-1 (live)"]\n'
        f"    blocking_reasons: []"
        for name in run_next._STAGE_ORDER
    )
    approvals = "\n".join(
        f'  - stage: "{name}"\n'
        f'    owner: "Dana Owner (data_owner)"\n'
        f'    at: "2026-07-01"'
        for name in sorted(run_next._APPROVAL_REQUIRED)
    )
    (mapping / "readiness-status.yaml").write_text(
        f'table: "{table}"\n'
        f'source_id: "{table}"\n'
        f'current_stage: "publish_ready"\n'
        f"stages:\n{stages}\n"
        f"approvals:\n{approvals}\n",
        encoding="utf-8",
    )
    if record is not None:
        (mapping / db_provenance.RECORD_FILENAME).write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )
    if dsn is not None:
        (tmp_path / ".env").write_text(f"DATABASE_URL={dsn}\n", encoding="utf-8")
    return tmp_path


@pytest.fixture(autouse=True)
def _no_ambient_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real env vars WIN over `.env` (connection_env's documented invariant), so a
    developer's own DATABASE_URL would otherwise decide these assertions."""
    for key in (
        "DATABASE_URL",
        "ANALYTICS_DB_HOST",
        "ANALYTICS_DB_NAME",
        "ANALYTICS_DB_PORT",
        "ANALYTICS_DB_USER",
        "ANALYTICS_DB_PASSWORD",
        "ANALYTICS_DB_SSLMODE",
    ):
        monkeypatch.delenv(key, raising=False)


# --- the reported defect: a repointed .env must downgrade -------------------


def test_mismatching_record_downgrades_with_the_named_blocker(tmp_path: Path) -> None:
    """The issue's repro: evidence earned on Ex-1, `.env` now points at ex-3."""
    root = _repo(tmp_path, dsn=_dsn(database=_OTHER_DB), record=_record())

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    assert response["outcome"] == "stop_blocked", response
    assert response["stage"] == "silver_ready"  # the first live-materialization stage
    assert any(
        db_provenance.BLOCKER_ID in reason for reason in response["blocking_reasons"]
    ), response["blocking_reasons"]


def test_mismatch_is_reported_by_the_agent_surface_too(tmp_path: Path) -> None:
    """`next --format agent` is what the reporter ran, and `readiness_state` is
    derived from `outcome` there -- so the run_next fix must reach it."""
    from seshat.agent_next import build_agent_next_document

    root = _repo(tmp_path, dsn=_dsn(database=_OTHER_DB), record=_record())

    document = build_agent_next_document(root, "sales_c086_raw")

    assert document["readiness_state"] != "pass", document["readiness_state"]
    assert any(
        db_provenance.BLOCKER_ID in reason for reason in document["blocking_reasons"]
    ), document["blocking_reasons"]


def test_matching_record_drops_the_option_b_caveat(tmp_path: Path) -> None:
    """A machine that connected vouched for this target -- the caveat is satisfied."""
    root = _repo(tmp_path, dsn=_dsn(), record=_record())

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    assert response["outcome"] == "terminal_pass", response
    kinds = {caveat["kind"] for caveat in response["caveats"]}
    assert run_next._PROVENANCE_CAVEAT_KIND not in kinds
    assert db_provenance_reader.CAVEAT_KIND_VERIFIED in kinds, kinds
    assert response["blocking_reasons"] == []


def test_absent_record_keeps_legacy_behavior_and_the_option_b_caveat(
    tmp_path: Path,
) -> None:
    """The legacy path -- every committed table today. Never a blocker (PR #504)."""
    root = _repo(tmp_path, dsn=_dsn(), record=None)

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    assert response["outcome"] == "terminal_pass", response
    assert response["blocking_reasons"] == []
    kinds = {caveat["kind"] for caveat in response["caveats"]}
    assert run_next._PROVENANCE_CAVEAT_KIND in kinds, kinds


def test_absent_record_is_not_a_blocker_even_with_no_configuration(
    tmp_path: Path,
) -> None:
    """Absence of BOTH a record and a DSN is the legacy path, not a failure."""
    root = _repo(tmp_path, dsn=None, record=None)

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    assert response["outcome"] == "terminal_pass"
    assert response["blocking_reasons"] == []


# --- cannot-compare: absence is never agreement ----------------------------


def test_record_present_but_no_dsn_reports_cannot_compare(tmp_path: Path) -> None:
    root = _repo(tmp_path, dsn=None, record=_record())

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    assert response["outcome"] == "terminal_pass"  # not a blocker
    caveats = {c["kind"]: c["detail"] for c in response["caveats"]}
    assert db_provenance.CAVEAT_KIND_UNCOMPARABLE in caveats, caveats
    assert "NOT agreement" in caveats[db_provenance.CAVEAT_KIND_UNCOMPARABLE]


def test_record_present_but_dsn_has_no_database_reports_cannot_compare(
    tmp_path: Path,
) -> None:
    scheme = "postgresql:" + "//"
    root = _repo(
        tmp_path,
        dsn=f"{scheme}analyst:pw" + "@" + f"{_HOST}:{_PORT}/",
        record=_record(),
    )

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    caveats = {c["kind"] for c in response["caveats"]}
    assert db_provenance.CAVEAT_KIND_UNCOMPARABLE in caveats, caveats


def test_a_malformed_env_cannot_crash_next(tmp_path: Path) -> None:
    """`next` has never raised on a readiness read and must not start."""
    root = _repo(tmp_path, dsn=_dsn(), record=_record())
    (root / ".env").write_text("this is not = a valid\x00 env\n", encoding="utf-8")

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    assert response["outcome"] in {"terminal_pass", "stop_blocked"}
    assert isinstance(response["caveats"], list)


def test_a_non_server_echo_record_is_never_compared_as_if_it_were(
    tmp_path: Path,
) -> None:
    """A1's shape: a digest a claimant could type. Never trusted as a match."""
    forged = _record(source="hand_authored")
    root = _repo(tmp_path, dsn=_dsn(), record=forged)

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    kinds = {c["kind"] for c in response["caveats"]}
    assert db_provenance_reader.CAVEAT_KIND_VERIFIED not in kinds, kinds
    assert db_provenance.CAVEAT_KIND_UNCOMPARABLE in kinds, kinds


def test_a_record_without_server_confirmation_is_not_trusted(tmp_path: Path) -> None:
    root = _repo(
        tmp_path, dsn=_dsn(), record=_record(database_name_server_confirmed=False)
    )

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    kinds = {c["kind"] for c in response["caveats"]}
    assert db_provenance_reader.CAVEAT_KIND_VERIFIED not in kinds
    assert db_provenance.CAVEAT_KIND_UNCOMPARABLE in kinds


def test_a_corrupt_record_reports_cannot_compare_not_absence(tmp_path: Path) -> None:
    """Corruption is a fact worth surfacing, not a licence to take the pass path."""
    root = _repo(tmp_path, dsn=_dsn(), record=None)
    path = root / "mappings" / "sales_c086_raw" / db_provenance.RECORD_FILENAME
    path.write_text("{not json", encoding="utf-8")

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    kinds = {c["kind"] for c in response["caveats"]}
    assert db_provenance.CAVEAT_KIND_UNCOMPARABLE in kinds, kinds


# --- secret hygiene: no raw identifier may ever be written -----------------


def test_no_raw_host_port_or_database_name_is_ever_written(tmp_path: Path) -> None:
    """R7's hard constraint: ANALYTICS_DB_NAME is on this repo's redaction lists,
    so committing a raw host or dbname would trade a correctness bug for a
    secret-hygiene bug. Greps the ACTUAL written artifact."""
    mapping = tmp_path / "mappings" / "sales_c086_raw"
    mapping.mkdir(parents=True)

    path = db_provenance.write_record(tmp_path, "sales_c086_raw", _record())
    written = path.read_text(encoding="utf-8")

    assert _HOST not in written
    assert _DB not in written
    assert "analyst" not in written  # the DSN user, for good measure
    assert "pw" not in written
    # The port must not appear either: with host and dbname digested, a raw port
    # is the one component that would still narrow the target.
    assert _PORT not in written
    assert db_provenance.identity_digest(_HOST, _PORT, _DB) in written


def test_no_message_this_feature_emits_names_a_database(tmp_path: Path) -> None:
    """Blockers and caveats reach terminals and pasted issue bodies."""
    root = _repo(tmp_path, dsn=_dsn(database=_OTHER_DB), record=_record())

    response = run_next.build_run_next_response(root, "sales_c086_raw")
    text = json.dumps(response)

    assert _HOST not in text
    assert _OTHER_DB not in text
    # `Ex-1` appears only inside the fixture's own hand-written evidence prose,
    # which this feature does not author; the blocker itself must be clean.
    assert all(_DB not in reason for reason in response["blocking_reasons"])


def test_the_write_never_touches_readiness_status_yaml(tmp_path: Path) -> None:
    """R7 authorizes ONE record. It must not author a stage status."""
    root = _repo(tmp_path, dsn=_dsn(), record=None)
    status = root / "mappings" / "sales_c086_raw" / "readiness-status.yaml"
    before = status.read_bytes()

    db_provenance.write_record(root, "sales_c086_raw", _record())

    assert status.read_bytes() == before


def test_the_writer_refuses_to_create_a_mapping_directory(tmp_path: Path) -> None:
    """`validate` is not an onboarding verb."""
    with pytest.raises(FileNotFoundError):
        db_provenance.write_record(tmp_path, "never_onboarded", _record())
    assert not (tmp_path / "mappings").exists()


# --- amendment 3: comparable offline, and the false-positive guard ---------


def test_writer_and_reader_derive_the_same_digest_for_a_direct_connection() -> None:
    """The core amendment-3 requirement: both sides reproduce one canonical form."""
    written = _record()["database_identity_digest"]
    read = db_provenance.configured_digest_from_env({"DATABASE_URL": _dsn()})

    assert written == read


def test_the_default_port_canonicalizes_across_dsn_spellings() -> None:
    """`host/db` and `host:5432/db` are the SAME target and must digest alike --
    otherwise a DSN respelled without the default port would false-mismatch."""
    scheme = "postgresql:" + "//"
    bare = f"{scheme}u:p" + "@" + f"{_HOST}/{_DB}"
    explicit = f"{scheme}u:p" + "@" + f"{_HOST}:{db_provenance.DEFAULT_PORT}/{_DB}"

    assert db_provenance.digest_for_dsn(bare) == db_provenance.digest_for_dsn(explicit)


def test_host_case_does_not_change_the_digest() -> None:
    """Hostnames are case-insensitive; the same target must digest identically."""
    assert db_provenance.digest_for_dsn(_dsn(host=_HOST.upper())) == (
        db_provenance.digest_for_dsn(_dsn(host=_HOST.lower()))
    )


def test_a_proxy_deployment_does_not_mismatch_for_the_same_database(
    tmp_path: Path,
) -> None:
    """AMENDMENT 3's false-positive guard.

    Behind a DNS alias / proxy / PgBouncer / load balancer the SERVER reports a
    backend address the offline reader can never see. That disagreement is
    recorded as information and must NOT change the digest -- otherwise a
    correctly-configured repo is blocked, which is worse than the original gap.
    """
    proxied = _record(server_endpoint_agreed_with_config=False)
    root = _repo(tmp_path, dsn=_dsn(), record=proxied)

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    assert response["outcome"] == "terminal_pass", response
    assert response["blocking_reasons"] == []
    kinds = {c["kind"] for c in response["caveats"]}
    assert db_provenance_reader.CAVEAT_KIND_VERIFIED in kinds, kinds


def test_a_genuinely_different_database_still_mismatches(tmp_path: Path) -> None:
    """The true-positive half of amendment 3's pairing: fixing the false positive
    must not blunt the real signal. Paired with the proxy test above deliberately."""
    root = _repo(
        tmp_path,
        dsn=_dsn(database=_OTHER_DB),
        record=_record(server_endpoint_agreed_with_config=False),
    )

    response = run_next.build_run_next_response(root, "sales_c086_raw")

    assert response["outcome"] == "stop_blocked", response
    assert any(
        db_provenance.BLOCKER_ID in reason for reason in response["blocking_reasons"]
    )


def test_a_different_host_serving_the_same_database_name_mismatches() -> None:
    """AMENDMENT 1's requirement: staging and production commonly share a database
    NAME, so a name-only digest could not tell them apart. The host is a
    component, so it can."""
    staging = db_provenance.digest_for_dsn(_dsn(host="staging.db.example.com"))
    production = db_provenance.digest_for_dsn(_dsn(host="prod.db.example.com"))

    assert staging != production


def test_the_server_must_confirm_the_configured_database_name() -> None:
    """What makes an offline-reproducible digest unforgeable: only a process
    holding a live connection can satisfy this, so an A1-shaped hand-authored
    record cannot be produced by editing `.env`."""
    with pytest.raises(ValueError) as excinfo:
        db_provenance.build_record(
            server_database_name="actually_this_one",
            configured_host=_HOST,
            configured_port=_PORT,
            configured_database_name=_DB,
            captured_at="2026-07-26T00:00:00+00:00",
            table="sales_c086_raw",
            engine="postgres",
        )
    # The error can reach a log, so it must name neither value.
    assert "actually_this_one" not in str(excinfo.value)
    assert _DB not in str(excinfo.value)


def test_a_digest_over_a_missing_component_is_refused() -> None:
    """A narrower identity must never wear a wider one's clothes."""
    with pytest.raises(ValueError):
        db_provenance.identity_digest("", _PORT, _DB)
    with pytest.raises(ValueError):
        db_provenance.identity_digest(_HOST, _PORT, "")


def test_a_record_declaring_other_identity_components_is_not_compared() -> None:
    """A digest over a different component set is not comparable with ours;
    pretending it is would be a false mismatch."""
    record = _record(identity_components=["database_name"])

    assert db_provenance.comparable_digest(record) is None


# --- amendment 2: the identity query is DIALECT-provided -------------------


@pytest.mark.parametrize("engine", ["postgres", "sqlserver"])
def test_engines_that_can_name_their_endpoint_supply_an_identity_query(
    engine: str,
) -> None:
    query = get_dialect(engine).identity_query()

    assert isinstance(query, str) and query.strip()


@pytest.mark.parametrize("engine", ["mysql", "snowflake"])
def test_engines_that_cannot_confirm_an_endpoint_record_nothing(engine: str) -> None:
    """The legacy absent path, which claims nothing -- deliberately preferred over
    a name-only digest that could not tell staging from production."""
    assert get_dialect(engine).identity_query() is None


def test_the_postgres_identity_query_is_not_assumed_by_other_engines() -> None:
    """AMENDMENT 2: `select current_database()` FAILS on SQL Server and MySQL, so
    no Postgres literal may be hardcoded into the provenance path."""
    postgres = get_dialect("postgres").identity_query()
    sqlserver = get_dialect("sqlserver").identity_query()

    assert postgres is not None and sqlserver is not None
    assert "current_database()" in postgres
    assert "current_database()" not in sqlserver
    assert "DB_NAME()" in sqlserver


def test_the_writer_consults_the_dialect_rather_than_hardcoding_sql() -> None:
    """Proves the seam is used: a dialect returning None writes nothing, and one
    returning a query has that exact query run against the connection."""
    from seshat import db_provenance_writer

    class _NoIdentity:
        def identity_query(self) -> str | None:
            return None

    class _Recorder:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def run(self, sql: str, params: tuple = ()) -> list[tuple]:
            self.queries.append(sql)
            return [("10.0.0.5:25060", _DB)]

    runner = _Recorder()
    assert db_provenance_writer._server_identity(runner, _NoIdentity()) is None
    assert runner.queries == []  # no query was invented for an opted-out engine

    identity = db_provenance_writer._server_identity(runner, get_dialect("postgres"))
    assert identity == ("10.0.0.5:25060", _DB)
    assert runner.queries == [get_dialect("postgres").identity_query()]


def test_a_server_that_reports_no_database_name_records_nothing() -> None:
    from seshat import db_provenance_writer

    class _Blank:
        def run(self, sql: str, params: tuple = ()) -> list[tuple]:
            return [(None, None)]

    assert (
        db_provenance_writer._server_identity(_Blank(), get_dialect("postgres")) is None
    )


def test_a_null_endpoint_still_records_because_it_is_not_a_digest_component() -> None:
    """Postgres over a Unix socket reports a NULL endpoint. The database name is
    the required component, so the record is still written -- only the
    informational endpoint-agreement field becomes unknown."""
    from seshat import db_provenance_writer

    class _SocketConn:
        def run(self, sql: str, params: tuple = ()) -> list[tuple]:
            return [(None, _DB)]

    identity = db_provenance_writer._server_identity(
        _SocketConn(), get_dialect("postgres")
    )

    assert identity == (None, _DB)
    assert db_provenance_writer._endpoint_agreement(None, _dsn()) is None


def test_a_rejected_identity_query_never_fails_the_run() -> None:
    from seshat import db_provenance_writer

    class _Denied:
        def run(self, sql: str, params: tuple = ()) -> list[tuple]:
            raise RuntimeError("permission denied for function inet_server_addr")

    assert (
        db_provenance_writer._server_identity(_Denied(), get_dialect("postgres"))
        is None
    )


# --- the status text surface reports the same verdicts ---------------------


def test_status_text_reports_the_mismatch(tmp_path: Path) -> None:
    from seshat.cli.commands.status import _render_text
    from seshat.status_surface import build_status_projection

    root = _repo(tmp_path, dsn=_dsn(database=_OTHER_DB), record=_record())

    rendered = _render_text(build_status_projection(root), "seshat", root)

    assert db_provenance.BLOCKER_ID in rendered


def test_status_text_drops_the_caveat_on_a_match(tmp_path: Path) -> None:
    from seshat.cli.commands.status import _render_text
    from seshat.status_surface import build_status_projection

    root = _repo(tmp_path, dsn=_dsn(), record=_record())

    rendered = _render_text(build_status_projection(root), "seshat", root)

    assert "unverified_db_provenance" not in rendered
    assert db_provenance_reader.CAVEAT_KIND_VERIFIED in rendered


def test_status_text_keeps_the_option_b_caveat_when_absent(tmp_path: Path) -> None:
    from seshat.cli.commands.status import _render_text
    from seshat.status_surface import build_status_projection

    root = _repo(tmp_path, dsn=_dsn(), record=None)

    rendered = _render_text(build_status_projection(root), "seshat", root)

    assert "unverified_db_provenance" in rendered


def test_status_json_stays_verbatim_and_carries_no_derived_field(
    tmp_path: Path,
) -> None:
    """The closed `schemas/agent-status.schema.json` contract is untouched: R7
    explicitly did not authorize projecting this field into the output JSON."""
    from seshat.status_surface import build_status_projection

    root = _repo(tmp_path, dsn=_dsn(database=_OTHER_DB), record=_record())

    projection = build_status_projection(root)
    text = json.dumps(projection)

    assert db_provenance.BLOCKER_ID not in text
    assert "database_identity_digest" not in text
    assert set(projection["tables"][0]) == {
        "table",
        "source_path",
        "current_stage",
        "stages",
        "blocking_reasons",
        "next_action",
    }


# --- the DSN decomposition helpers ----------------------------------------


@pytest.mark.parametrize(
    ("dsn", "host", "port", "database"),
    [
        (_dsn(), _HOST, _PORT, _DB),
        (
            "host=db.example.com port=5433 dbname=analytics user=u",
            "db.example.com",
            "5433",
            "analytics",
        ),
        (
            "host='db.example.com' dbname='analytics'",
            "db.example.com",
            None,
            "analytics",
        ),
        (
            "postgresql:///analytics?host=db.example.com",
            "db.example.com",
            None,
            "analytics",
        ),
    ],
)
def test_the_shared_decomposition_handles_every_supported_dsn_shape(
    dsn: str, host: str, port: str | None, database: str
) -> None:
    """psycopg2 connects with all of these, so the reader must decompose all of
    them -- and via the ONE hardened helper set, never a second parser."""
    from seshat.redaction_core import dsn_dbname, dsn_host, dsn_port

    assert dsn_host(dsn) == host
    assert dsn_dbname(dsn) == database
    assert dsn_port(dsn) == port


def test_a_percent_encoded_database_name_decodes_to_the_server_form() -> None:
    from seshat.redaction_core import dsn_dbname

    scheme = "postgresql:" + "//"
    assert dsn_dbname(f"{scheme}u:p" + "@" + "h/my%20db") == "my db"


def test_the_decomposition_is_total_on_a_malformed_dsn() -> None:
    """Every function in redaction_core is total; a reader must never raise."""
    from seshat.redaction_core import dsn_dbname, dsn_host, dsn_port

    malformed = "postgresql://[not-an-ipv6/db"
    assert dsn_host(malformed) is None
    assert dsn_dbname(malformed) is None
    assert dsn_port(malformed) is None


def test_digests_are_not_reversible_to_the_identity() -> None:
    """A digest, never a raw identity -- the whole secret-hygiene premise."""
    digest = db_provenance.identity_digest(_HOST, _PORT, _DB)

    assert _HOST not in digest
    assert _DB not in digest
    assert len(digest) == 32


def test_no_numeric_score_is_emitted_anywhere_in_the_record() -> None:
    """Hard rule #9 / Principle V: never a confidence, health, or maturity value.

    `schema_version` is deliberately exempt and deliberately asserted as the ONLY
    exemption: it is a format version, not an assessment of the table. Anything
    else numeric would read as a score, which is what the rule forbids.
    """
    record = _record()
    numeric = {
        key
        for key, value in record.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    assert numeric == {"schema_version"}, numeric
    for banned in ("score", "confidence", "health", "maturity", "rating"):
        assert not any(banned in key for key in record), banned
