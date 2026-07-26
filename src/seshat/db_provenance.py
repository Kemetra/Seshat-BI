"""Machine-written, server-echoed live-DB provenance (issue #485, option A2).

The trust boundary this module exists to hold:

    A qualifier is only worth adding if the party being qualified cannot author
    it.

`readiness-status.yaml` carries no machine-checkable statement of WHICH live
database earned a stage's `pass`; database names appear only as prose inside
`evidence[]`. So a table whose silver/gold evidence was earned against one
database still reports `terminal_pass` verbatim after the configured DSN is
repointed at another (#485's reproduction). Option A1 -- a hand-authored
provenance field -- was REJECTED because the only writers of that YAML are
agents and humans, so a digest computed from `.env` is forgeable without ever
opening a socket, and tool-formatted prose is strictly worse than honest
silence.

Option A2, ruled in by the owner (ruling R7 as amended), splits the work across a
trust boundary:

  * the WRITER runs inside `seshat validate`, which has already connected, and
    records digests of what the SERVER reported about the connection. The
    database asserts its own identity; the claimant never types it.
  * the READER (`next` / `status`) compares configuration only and opens NO
    connection, so the documented no-DB/no-network contracts of `run_next`,
    `agent_next`, and `status_surface` stay intact.

## The digest: ONE canonical form both sides derive, server-VALIDATED

Getting here took two corrections, both worth recording because the naive designs
are each attractive and each broken.

**A name-only digest is too weak.** Staging and production commonly share a
database NAME on different hosts, so ``sha256(dbname)`` matches for both and
cannot say which system earned the evidence -- A2's whole purpose (R7 amendment
1).

**A server-reported ENDPOINT in the digest is unusable.** The parent design note
specifies ``sha256("<host>/<dbname>")``
(`2026-07-25-live-db-provenance-design.md:163`), which silently assumes both
sides derive the host the SAME way. Once the write side is server-echoed they
cannot: a server reports its own endpoint as an ADDRESS (Postgres
``inet_server_addr()`` -> ``10.x.x.x``) while the offline reader has only the
CONFIGURED hostname (``db-xxx.ondigitalocean.com``). Behind a DNS alias, a
proxy, PgBouncer, or a load balancer the server routinely reports a BACKEND
address that the reader can never see. Folding that into the digest would fire a
mismatch blocker on correctly-configured repos -- a false positive on the exact
signal A2 exists to provide, and a check that cries wolf gets disabled (R7
amendment 3).

So the digest covers **one canonical form that BOTH sides derive independently**,
and the server echo is spent where it actually earns its keep:

  * **In the digest** (``identity_components``): the normalized CONFIGURED host,
    the port, and the database name. Both sides derive these identically -- the
    writer from the DSN it connected with, the reader from the DSN configuration
    resolves now -- so a correct setup can never look wrong.
  * **Server-VALIDATED, not server-sourced**: the database-name component is the
    one a claimant would otherwise be free to type, and it is exactly the one a
    server reports reliably. So the writer REFUSES to record unless the server's
    own ``current_database()`` answer AGREES with the configured database name
    (:func:`assert_database_name_agrees`). The recorded name is therefore
    server-confirmed even though the digest is offline-reproducible. That is what
    defeats A1's forgeability: a hand-authored record cannot pass a check that
    only a process holding a live connection can perform.
  * **Outside the digest, recorded as information**: whether the server's
    reported endpoint agreed with the configured one
    (``server_endpoint_agreed_with_config``). Useful to a human -- it names a
    proxy/alias deployment -- and deliberately inert. It never changes the digest
    and never gates anything, because a value the reader cannot reproduce must not
    decide a comparison.

**The governing principle, applied throughout:** the digest's job is to make a
WRONG database detectable without making a RIGHT one look wrong. Prefer a false
NEGATIVE (no field, the caveat persists) over a false POSITIVE (valid evidence
blocked). Every ambiguity in this module resolves that way.

**The honest limit, stated rather than hidden:** the digest's host component is
config-derived, so A2 detects a repointed CONFIGURATION -- which is precisely
what #485 reports (evidence built against `Ex-1` while `.env` points at `ex-3`).
It does not detect a case where the configuration is unchanged but DNS now
resolves the same hostname to a different server. The server echo bounds that
gap for the database name, not for the host.

## Three hard constraints, each load-bearing

  * **DIGESTS, never a raw identity.** ``ANALYTICS_DB_NAME`` is on this repo's
    own secret/redaction lists (`dagster_adapter/redaction.py`,
    `rules/git_meta.py`, `severity_posture.py`). Committing a raw host or dbname
    would trade a correctness bug for a secret-hygiene bug. A digest compares
    equal-or-not without disclosing the target, which is all the gate needs --
    and every message this module emits is likewise identifier-free.
  * **Dialect-provided identity, never a Postgres literal.** ``select
    current_database()`` FAILS on SQL Server (needs ``DB_NAME()``) and MySQL
    (needs ``DATABASE()``), and this repo supports four engines. The identity
    expression is resolved through ``Dialect.identity_query()``, beside every
    other engine-specific query. An engine that cannot name its own endpoint
    returns ``None`` and records NO provenance -- the legacy absent path, which is
    already safe. A digest that looks authoritative but cannot tell staging from
    production is worse than no field, so there is no name-only fallback.
  * **Present-only gating.** Absence carries a valid legacy meaning -- no
    committed record has provenance today -- so the comparison fires only when a
    record exists, exactly like ``source_kind`` (#120, commit ``64e3f88``). Zero
    migration; a *required* qualifier would fail every table at once.

This module is a stdlib-only leaf: it imports nothing from ``seshat`` except the
shared DSN decomposition in ``redaction_core``, emits no numeric score of any
kind, grants no stage, and writes no ``readiness-status.yaml``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .redaction_core import dsn_dbname, dsn_host, dsn_port

# The committed record's filename, a SIBLING of readiness-status.yaml under
# mappings/<table>/. Deliberately NOT a key inside readiness-status.yaml: that
# file is a hand-authored governed artifact whose comments, key order, and
# formatting a yaml.safe_load -> safe_dump round-trip destroys (measured: 26 diff
# hunks and every comment lost on mappings/retail_store_sales/), and a machine
# writer that mangles a human's artifact -- or clobbers a concurrent edit -- is a
# worse defect than the one it fixes. A sibling file is also what lets the writer
# stay atomic, the same posture as dbt/evidence.py.
RECORD_FILENAME = "db-provenance.json"

# The only source value this module will trust. A record declaring anything else
# was not produced by a process that asked the server, so it cannot be compared.
SERVER_ECHO = "server_echo"

_SCHEMA_VERSION = 1

# Digest length. A truncated hex sha256 is still far beyond collision reach for a
# set of database endpoints, and a short value keeps the committed record readable.
_DIGEST_CHARS = 32

# The canonical separator between identity components. Documented and fixed: a
# reader that canonicalizes differently computes a different digest and would
# report a false mismatch, so the ordering and separator are part of the contract.
_CANONICAL_SEPARATOR = "\x1f"  # ASCII unit separator: cannot occur in a hostname

DIGEST_ALGORITHM = "sha256-unsalted-truncated-32"

CAVEAT_KIND_UNCOMPARABLE = "db_provenance_not_comparable"
BLOCKER_ID = "stale_evidence_wrong_database"

# Every message below is deliberately identifier-free: naming the recorded or the
# configured database here would put a redacted value into terminal output and,
# for the blocker, into a surface a reader may paste into an issue.
MISMATCH_BLOCKER = (
    f"{BLOCKER_ID}: the live database that produced this table's recorded "
    "validate evidence is NOT the database the current connection resolves to "
    "(the recorded and configured target digests disagree). The recorded "
    "evidence describes a different database, so this stage's pass cannot be "
    "claimed for the database you are now pointed at. Re-run `seshat validate "
    "--source-map mappings/<table>/source-map.yaml` against the intended "
    "database, or repoint the connection; the data owner resolves which is "
    "intended."
)
UNCOMPARABLE_NO_DSN = (
    "a server-echoed database-identity record exists for this table, but no "
    "database connection is configured, so it cannot be compared -- absence of "
    "a configured DSN is NOT agreement. Set DATABASE_URL or the ANALYTICS_DB_* "
    "vars in your gitignored .env to enable the check."
)
UNCOMPARABLE_NO_DBNAME = (
    "a server-echoed database-identity record exists for this table, but the "
    "configured connection does not resolve to a comparable host and database "
    "name, so it cannot be compared -- this is NOT agreement."
)
UNCOMPARABLE_BAD_ENV = (
    "a server-echoed database-identity record exists for this table, but the "
    "workspace .env could not be read, so the configured connection cannot be "
    "resolved and the record cannot be compared -- this is NOT agreement. Fix "
    "the .env to enable the check."
)
UNCOMPARABLE_BAD_RECORD = (
    "this table has a database-identity record that is unreadable, incomplete, "
    "or was not produced by a server echo, so it cannot be compared -- this is "
    "NOT agreement. Re-run `seshat validate --source-map "
    "mappings/<table>/source-map.yaml` to rewrite it."
)


def _digest(*components: str) -> str:
    """Digest a canonicalized identity tuple.

    UNSALTED plain sha256 over the components joined by the fixed separator,
    truncated to hex. Deliberately unsalted: a salt would have to live somewhere
    both the writer and every later reader can reach, and a salt committed to a
    tracked file is not a secret -- it would add ceremony without adding
    protection while creating a new tracked-secret question. The digest's job is
    equality comparison without disclosure, and an unsalted digest does that.

    Honest about what this is NOT: a digest of a short, guessable endpoint is not
    confidential against an attacker who can enumerate candidates. It keeps the
    identifier out of a tracked file and out of terminal output, which is the
    stated secret-hygiene requirement -- it is not a cryptographic secret.

    Every component must be non-empty: a digest over a missing component would be
    a narrower identity wearing a wider one's clothes, which is exactly the
    failure amendment 1 forbids.
    """
    normalized = [component.strip() for component in components]
    if not normalized or not all(normalized):
        raise ValueError(
            "every identity component must be non-empty; a digest over a missing "
            "component cannot distinguish two systems and must not be recorded"
        )
    joined = _CANONICAL_SEPARATOR.join(normalized)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:_DIGEST_CHARS]


# The canonical identity, documented once because BOTH sides must reproduce it.
IDENTITY_COMPONENTS = ("normalized_configured_host", "port", "database_name")

# The port assumed when a DSN declares none. Fixed rather than omitted: if the
# writer's DSN spelled the default port and the reader's did not (or vice versa),
# an omitted component would digest differently for the SAME target -- a false
# positive. Defaulting makes `host/db` and `host:5432/db` canonically identical.
DEFAULT_PORT = "5432"


def identity_digest(host: str, port: str, database_name: str) -> str:
    """Digest the canonical identity: normalized host, port, database name.

    The ONE digest in the record. Derivable by the writer (from the DSN it
    connected with) and by the offline reader (from the DSN configuration
    resolves now), identically -- which is what keeps a correct setup from ever
    looking wrong. The database-name component is separately SERVER-VALIDATED at
    write time (:func:`assert_database_name_agrees`), so it cannot be typed.

    Host is lowercased by ``redaction_core.dsn_host``; port defaults via
    :func:`normalized_port`. No server-reported address is ever a component --
    see this module's docstring on why folding one in is unusable.
    """
    return _digest(host, normalized_port(port), database_name)


def normalized_port(port: object) -> str:
    """The canonical port string: the given value, or :data:`DEFAULT_PORT`."""
    text = str(port).strip() if port is not None else ""
    return text or DEFAULT_PORT


def database_names_agree(server_name: str, configured_name: str) -> bool:
    """Whether the server's own database name matches the configured one.

    Compared case-sensitively after stripping: a database name is
    case-significant in Postgres, and folding case here would let two genuinely
    different databases pass as one. Both engines that record provenance report
    the name exactly as created.
    """
    return server_name.strip() == configured_name.strip()


def assert_database_name_agrees(server_name: str, configured_name: str) -> None:
    """Raise ``ValueError`` unless the server confirms the configured DB name.

    The check that makes an offline-reproducible digest UNFORGEABLE. A record can
    only be written by a process that held a live connection and heard the server
    agree, so a hand-authored (A1-shaped) record cannot be produced by editing
    `.env`.

    Deliberately fails the WRITE rather than recording a disagreement: a record
    whose name component the server contradicts describes no coherent target, and
    per the governing principle it is better to record nothing (the safe absent
    path) than something misleading.

    The message names NEITHER value -- a raised error can reach a log.
    """
    if not database_names_agree(server_name, configured_name):
        raise ValueError(
            "the server's own database name does not match the configured "
            "database name for this connection, so no coherent provenance "
            "identity can be recorded (values withheld: they are redacted "
            "connection settings)"
        )


def configured_digest_from_env(env: dict[str, str]) -> str | None:
    """The canonical identity digest for an env mapping, or ``None``.

    Configuration only: resolves the DSN from the given env mapping via the
    driver-free ``validate.resolve_dsn`` and decomposes it with the shared
    ``redaction_core`` helpers. Opens NO connection and makes no network call, so
    a reader that calls this keeps its no-DB contract.

    ``None`` when no DSN is configured, or when the configured DSN declares no
    host or no database name. The caller MUST treat ``None`` as "cannot
    compare", never as agreement.
    """
    from .validate import resolve_dsn

    dsn = resolve_dsn(env)
    if not dsn:
        return None
    return digest_for_dsn(dsn)


def digest_for_dsn(dsn: str) -> str | None:
    """The canonical identity digest for one DSN string, or ``None``.

    The single decomposition both the writer and the reader use, so the two can
    never drift into two canonicalizations of one target -- which would be a false
    mismatch on a correct setup.
    """
    host, name = dsn_host(dsn), dsn_dbname(dsn)
    if not host or not name:
        return None
    return identity_digest(host, dsn_port(dsn) or DEFAULT_PORT, name)


def build_record(
    *,
    server_database_name: str,
    configured_host: str,
    configured_port: object,
    configured_database_name: str,
    captured_at: str,
    table: str,
    engine: str,
    server_endpoint_agreed_with_config: bool | None = None,
) -> dict[str, Any]:
    """Build the provenance record for ONE live validate run.

    Pure: returns a NEW dict, mutates nothing, and reads no clock -- the
    timestamp is an explicit argument, mirroring ``readiness_evidence``'s
    determinism rule so the writer's output is reproducible in a test.

    ``server_database_name`` MUST be the value the SERVER reported for
    ``Dialect.identity_query()``. It is CHECKED against
    ``configured_database_name`` (raising ``ValueError`` on disagreement) and is
    what makes this record unforgeable; the digest itself is computed over the
    offline-reproducible canonical form. See this module's docstring.

    ``server_endpoint_agreed_with_config`` is INFORMATION ONLY -- recorded so a
    human can see a proxy/alias deployment, never a digest component and never a
    gate. ``None`` means the comparison was not made.

    Only a digest is stored: no raw host, port, or database name reaches the
    returned dict, so a caller cannot accidentally persist one.
    """
    assert_database_name_agrees(server_database_name, configured_database_name)
    return {
        "schema_version": _SCHEMA_VERSION,
        "table": table.strip(),
        "engine": engine,
        "database_identity_digest": identity_digest(
            configured_host, normalized_port(configured_port), configured_database_name
        ),
        "identity_components": list(IDENTITY_COMPONENTS),
        "digest_algorithm": DIGEST_ALGORITHM,
        "database_name_server_confirmed": True,
        "server_endpoint_agreed_with_config": server_endpoint_agreed_with_config,
        "source": SERVER_ECHO,
        "captured_at": captured_at,
        "captured_by": "seshat validate",
        "scope": (
            "a digest of the canonical identity (normalized configured host, "
            "port, database name) of the live system that answered this table's "
            "validate run. The database-name component was CONFIRMED by the "
            "server's own report at capture time, so this record could only be "
            "written by a process holding a live connection. The digest itself is "
            "offline-reproducible on purpose, so a correctly-configured repo can "
            "never look wrong. No raw host, port, or database name is recorded."
        ),
    }


def record_path(repo_root: Path | str, table_dir: str) -> Path:
    """The committed record's path for one ``mappings/<table>/`` directory."""
    return Path(repo_root) / "mappings" / table_dir / RECORD_FILENAME


def read_record(path: Path) -> dict[str, Any] | None:
    """Read one provenance record, or ``None`` when absent.

    Absence returns ``None`` (the legacy path). A file that exists but is
    unreadable/malformed returns the sentinel ``{}`` so the caller can report
    "cannot compare" rather than silently treating corruption as absence -- a
    corrupt record is a fact worth surfacing, not a licence to pass.
    """
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError):
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def comparable_digest(record: dict[str, Any] | None) -> str | None:
    """The digest an OFFLINE reader may compare, or ``None``.

    ``None`` for an absent record; for a record whose ``source`` is not
    ``server_echo`` or whose ``database_name_server_confirmed`` is not ``True``
    (either shape means the value was not vouched for by a live connection --
    exactly the A1 shape the ruling rejects, so it is never compared as if it
    were); for a record whose ``identity_components`` are not the canonical set
    (a digest over different components is not comparable with ours, and
    pretending otherwise would be a false mismatch); and for a record with no
    digest at all.
    """
    if not isinstance(record, dict):
        return None
    if record.get("source") != SERVER_ECHO:
        return None
    if record.get("database_name_server_confirmed") is not True:
        return None
    components = record.get("identity_components")
    if not isinstance(components, list) or tuple(components) != IDENTITY_COMPONENTS:
        return None
    digest = record.get("database_identity_digest")
    if not isinstance(digest, str) or not digest.strip():
        return None
    return digest.strip()


def compare(
    record: dict[str, Any] | None, configured: str | None
) -> tuple[str, str | None]:
    """Compare a recorded provenance record against the configured digest.

    Returns ``(verdict, detail)`` where ``verdict`` is one of:

      * ``"absent"``       -- no record: the legacy path. The caller keeps
        today's behavior plus the shipped option-B caveat. NEVER a blocker; no
        committed record carries provenance, so gating on absence would fail
        every table at once.
      * ``"match"``        -- record and configuration agree. The option-B caveat
        is satisfied and drops: a machine that connected recorded this target,
        and recorded the server's own view of itself beside it.
      * ``"mismatch"``     -- they disagree. The caller downgrades with the named
        blocker. Never a fabricated pass and never a silent pass.
      * ``"uncomparable"`` -- a record exists but the comparison could not be
        made (no configured DSN, no resolvable host/database in it, or an
        unreadable/incomplete/non-server-echo record). ``detail`` says which.
        Absence of a configured DSN is NOT agreement, so this is reported.

    ``detail`` is ``None`` only for ``absent`` and ``match``. No verdict's detail
    ever names a host or a database.
    """
    if record is None:
        return "absent", None
    digest = comparable_digest(record)
    if digest is None:
        return "uncomparable", UNCOMPARABLE_BAD_RECORD
    if configured is None:
        return "uncomparable", UNCOMPARABLE_NO_DSN
    if digest == configured:
        return "match", None
    return "mismatch", MISMATCH_BLOCKER


def write_record(repo_root: Path | str, table_dir: str, record: dict[str, Any]) -> Path:
    """Atomically write ONE provenance record; return its path.

    The single write ruling R7 authorizes, and nothing more. It writes the
    sibling ``db-provenance.json`` only -- it never touches
    ``readiness-status.yaml``, never authors a stage ``status``, and never grants
    a readiness stage. Refuses when ``mappings/<table>/`` does not exist rather
    than creating the spine directory: `validate` is not an onboarding verb.

    Atomic replace (write a temp sibling, then ``Path.replace``) so a crashed run
    can never leave a half-written record that the reader would then report as
    corrupt.
    """
    directory = Path(repo_root) / "mappings" / table_dir
    if not directory.is_dir():
        raise FileNotFoundError(
            f"mappings/{table_dir}/ does not exist; `validate` records provenance "
            "for an already-onboarded table and does not create the mapping "
            "directory"
        )
    path = directory / RECORD_FILENAME
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return path
