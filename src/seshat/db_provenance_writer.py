"""The WRITER half of #485's provenance check -- the one write R7 authorizes.

`seshat validate` deliberately wrote nothing before this: it connected, printed
findings, and set an exit code. Ruling R7 authorizes it to persist ONE committed
provenance record, and nothing else. That narrowness is the point, so this module
is the whole of the write path and it is deliberately small.

What makes the record trustworthy is that only a process holding a live
connection can produce one. This code runs after ``validate`` has already
connected, and it asks the SERVER to name its own database -- via
``Dialect.identity_query()``, resolved through the dialect layer rather than
hardcoded, because ``select current_database()`` fails on SQL Server and MySQL.
The record is written ONLY if the server's answer AGREES with the configured
database name. A hand-authored (A1-shaped) record cannot pass a check that
requires a live socket, which is why A1 stays rejected.

The digest itself is over the offline-reproducible canonical form (normalized
configured host, port, database name), NOT over the server's reported endpoint.
That is deliberate and it is the whole reason this design works: behind a DNS
alias, proxy, PgBouncer, or load balancer the server reports a backend address
the offline reader can never see, so digesting it would fire a mismatch blocker on
a correctly-configured repo. See ``db_provenance``'s module docstring. The
endpoint comparison is still made and recorded as INFORMATION, never as a digest
component and never as a gate.

Fail-closed on recording, which is the safe direction:

  * an engine whose dialect supplies no identity query -> record NOTHING;
  * a server that will not name its database (a permission-restricted role, a
    rejected query, a NULL/short row) -> record NOTHING;
  * a server whose database name DISAGREES with the configured one -> record
    NOTHING (no coherent identity exists to record);
  * an unwritable mapping directory -> record nothing and say so on stderr.

In every one of those cases the table takes the legacy ``absent`` path, which is
already safe -- it is every committed table's state today, and it keeps the
option-B caveat. A failed provenance capture must NEVER change the exit code of a
validate run whose findings already succeeded: the findings are the verb's
contract, and provenance is an addition to it.

Governing principle: prefer a false NEGATIVE (no record, caveat persists) over a
false POSITIVE (valid evidence blocked).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    """The capture timestamp, UTC, second precision.

    The only clock read in the provenance path. ``db_provenance.build_record``
    takes the timestamp as an explicit argument precisely so it stays pure and
    reproducible in a test; the impurity is isolated here.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _server_identity(runner: Any, dialect: Any) -> tuple[str | None, str] | None:
    """``(server_endpoint, database_name)`` as the SERVER reports them, or ``None``.

    ``None`` -- record nothing -- for an engine with no identity query, a query the
    server rejects, a short/missing row, or a missing DATABASE NAME. The name is
    the required component: it is what the server vouches for and what the record
    exists to confirm.

    The ENDPOINT is optional (``None`` when the server reports none, e.g. Postgres
    over a Unix socket). It is not a digest component, so its absence is not a
    reason to record nothing -- it only makes the informational
    endpoint-agreement field unknown.
    """
    query = dialect.identity_query()
    if not query:
        return None
    try:
        rows = runner.run(query)
    except Exception:  # noqa: BLE001 -- provenance must never fail the run
        return None
    if not rows or len(rows[0]) < 2:
        return None
    endpoint, database = rows[0][0], rows[0][1]
    if database is None or not str(database).strip():
        return None
    normalized_endpoint = str(endpoint).strip() if endpoint is not None else ""
    return (normalized_endpoint or None), str(database).strip()


def _endpoint_agreement(
    server_endpoint: str | None, configured_dsn: object
) -> bool | None:
    """Whether the server's reported endpoint matches the configured host.

    INFORMATION ONLY -- never a digest component and never a gate. ``None`` when
    the comparison cannot be made. A ``False`` here is normal and expected behind
    a DNS alias, proxy, PgBouncer, or load balancer; it is recorded so a human can
    SEE that deployment shape, and it deliberately changes nothing.
    """
    if not server_endpoint or not isinstance(configured_dsn, str):
        return None
    from seshat.redaction_core import dsn_host

    host = dsn_host(configured_dsn)
    if not host:
        return None
    # Compare the host portion only: the server reports "addr:port" while the
    # configured host carries no port.
    reported_host = server_endpoint.rsplit(":", 1)[0].strip().lower()
    return bool(reported_host) and reported_host == host


def _table_directory(source_map: str) -> str | None:
    """The ``mappings/<dir>/`` name containing ``source_map``, or ``None``.

    The provenance record is a SIBLING of the source map the run validated, so the
    directory comes from the path the operator actually passed -- never from a
    table name, which may be schema-qualified and need not equal the directory.
    """
    parent = Path(source_map).resolve().parent
    return parent.name or None


def record_live_run(
    *,
    repo_root: Path | str,
    source_map: str,
    runner: Any,
    dialect: Any,
    configured_dsn: object,
    engine: str,
    stream: Any = None,
) -> Path | None:
    """Persist ONE server-echoed provenance record for a completed live run.

    Returns the record's path, or ``None`` when nothing was recorded (with the
    reason on ``stream``). Never raises and never influences the caller's exit
    code -- see this module's docstring.

    ``configured_dsn`` is the DSN the run connected WITH, used for the
    config-derived half of the record so the offline reader has a like-for-like
    value to compare. It is only ever digested; the raw string never reaches the
    file.
    """
    from seshat import db_provenance

    out = stream if stream is not None else sys.stderr
    identity = _server_identity(runner, dialect)
    if identity is None:
        print(
            f"note: recorded no live-DB provenance for this run -- the {engine!r} "
            "connection did not report a database name this tool can confirm "
            "(the engine may supply no identity query, or the role may lack "
            "permission). Readiness surfaces keep the unverified-provenance "
            "caveat, which is the honest state.",
            file=out,
        )
        return None
    return _write(
        repo_root=repo_root,
        source_map=source_map,
        identity=identity,
        configured_dsn=configured_dsn,
        engine=engine,
        out=out,
        db_provenance=db_provenance,
    )


def _configured_parts(configured_dsn: object) -> tuple[str, str, str] | None:
    """``(host, port, database_name)`` from the DSN the run connected with.

    The canonical identity's components, decomposed by the SAME shared helpers the
    offline reader uses, so the two sides cannot drift into two canonicalizations
    of one target. ``None`` when any required part is absent.

    Only a Postgres/libpq-shaped DSN string decomposes here. A dict-config engine
    (MySQL/Snowflake) resolves no DSN string -- and both already supply no identity
    query, so this is never reached for them; it returns ``None`` rather than
    guessing if that ever changes.
    """
    from seshat.db_provenance import DEFAULT_PORT
    from seshat.redaction_core import dsn_dbname, dsn_host, dsn_port

    if not isinstance(configured_dsn, str) or not configured_dsn:
        return None
    host, name = dsn_host(configured_dsn), dsn_dbname(configured_dsn)
    if not host or not name:
        return None
    return host, dsn_port(configured_dsn) or DEFAULT_PORT, name


def _write(
    *,
    repo_root: Path | str,
    source_map: str,
    identity: tuple[str | None, str],
    configured_dsn: object,
    engine: str,
    out: Any,
    db_provenance: Any,
) -> Path | None:
    """Build and atomically write the record; report and return ``None`` on any
    failure, so a provenance problem never fails a successful validate run."""
    table_dir = _table_directory(source_map)
    configured = _configured_parts(configured_dsn)
    if table_dir is None or configured is None:
        print(
            "note: recorded no live-DB provenance for this run -- could not "
            "resolve the mapping directory and the configured host/database from "
            "the connection settings.",
            file=out,
        )
        return None
    endpoint, server_database = identity
    host, port, configured_name = configured
    try:
        record = db_provenance.build_record(
            server_database_name=server_database,
            configured_host=host,
            configured_port=port,
            configured_database_name=configured_name,
            captured_at=_now_iso(),
            table=table_dir,
            engine=engine,
            server_endpoint_agreed_with_config=_endpoint_agreement(
                endpoint, configured_dsn
            ),
        )
        path = db_provenance.write_record(repo_root, table_dir, record)
    except (OSError, ValueError, FileNotFoundError) as exc:
        # ValueError includes the server-vs-configured database-name
        # disagreement: no coherent identity exists, so record nothing.
        print(
            f"note: recorded no live-DB provenance for this run ({exc}). The "
            "validate findings above are unaffected.",
            file=out,
        )
        return None
    print(
        f"note: recorded server-echoed live-DB provenance at "
        f"{path.relative_to(Path(repo_root)).as_posix()} -- digests only, no raw "
        "host or database name. Commit it so `seshat next` / `seshat status` can "
        "verify this evidence was earned against the database you are pointed at.",
        file=out,
    )
    return path
