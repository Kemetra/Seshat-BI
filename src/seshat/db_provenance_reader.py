"""The READER half of #485's provenance check -- configuration only, no DB.

`next` and `status --format text` both need one answer to one question: does the
database identity recorded for this table agree with the database the current
configuration resolves to? This module computes that answer ONCE so the two
surfaces cannot drift into two sentences (or two verdicts) for one condition --
the #487 failure mode the shipped caveat's own docstring already names.

Contract, inherited from every caller and deliberately not weakened:

  * **No DB, no network.** The comparison reads `.env` + the process env through
    ``connection_env.connection_environment`` and resolves a DSN STRING with the
    driver-free ``validate.resolve_dsn``. It never connects. ``run_next`` /
    ``agent_next`` / ``status_surface`` keep their no-DB/no-network contracts.
  * **Never raises.** A malformed `.env` raises ``EnvironmentConfigError`` from
    the governed parser; ``next`` has never raised on a readiness read and must
    not start, so that degrades to "cannot compare" rather than crashing the
    surface.
  * **Present-only.** No record -> the legacy path (today's behavior plus the
    shipped option-B caveat). A record is required before anything is gated.
  * **Identifier-free output.** No caveat or blocker returned from here names a
    host or a database name.
"""

from __future__ import annotations

from pathlib import Path

from seshat import db_provenance

# The shared kinds. `verified` is emitted so a reader can see that the check RAN
# and agreed, rather than inferring agreement from the absence of a caveat.
CAVEAT_KIND_VERIFIED = "db_provenance_verified"
_VERIFIED_DETAIL = (
    "stage {stage!r} is pass and this table's COMMITTED live-database provenance "
    "record -- written by a validate run whose live checks passed, over the "
    "committed source-map -- carries a configuration digest equal to the one the "
    "current connection resolves to. This is a configuration comparison, not a "
    "proof: the record is a committed file, as trustworthy as the commit that "
    "introduced it"
)


def _configured_digest(repo_root: Path | str) -> tuple[str | None, str | None]:
    """``(digest, uncomparable_detail)`` for the configured connection.

    Never raises. Each failure mode gets its OWN sentence -- a malformed `.env` is
    not the same condition as a DSN that declares no database name, and one
    wording for two conditions is the drift this module exists to prevent:

      * a `.env` that cannot be read -> ``UNCOMPARABLE_BAD_ENV``;
      * no DSN configured at all -> ``(None, None)``, which ``compare`` reports as
        ``UNCOMPARABLE_NO_DSN`` (kept there so the "absence is not agreement"
        wording lives beside the verdict that uses it);
      * a DSN with no resolvable host/database -> ``UNCOMPARABLE_NO_DBNAME``.
    """
    from seshat.connection_env import ConnectionConfigError
    from seshat.dbt.redaction import EnvironmentConfigError

    try:
        from seshat.connection_env import connection_environment

        env = connection_environment(repo_root)
    except (EnvironmentConfigError, ConnectionConfigError, OSError, ValueError):
        # A reporting surface that crashes on a bad .env is a regression in its
        # own right; degrade to "cannot compare" with the reason named.
        return None, db_provenance.UNCOMPARABLE_BAD_ENV

    from seshat.validate import resolve_dsn

    if not resolve_dsn(env):
        return None, None  # no DSN at all: compare() names that condition
    digest = db_provenance.configured_digest_from_env(env)
    if digest is None:
        return None, db_provenance.UNCOMPARABLE_NO_DBNAME
    return digest, None


def provenance_verdict(repo_root: Path | str, table_dir: str) -> tuple[str, str | None]:
    """``(verdict, detail)`` for one ``mappings/<table_dir>/``.

    Verdicts are ``db_provenance.compare``'s: ``absent`` / ``match`` /
    ``mismatch`` / ``uncomparable``. ``absent`` means no record exists, which is
    every table on `main` today -- the legacy path.

    The record is read FIRST and the configuration only when a record exists, so
    a repo with no provenance records does no `.env` or git work at all and the
    overwhelmingly common path stays exactly as cheap as before.

    The record and the source-map are read from the COMMITTED tree (``HEAD``),
    never the worktree: a record an agent writes into the working tree is not
    evidence until it is committed, where it is reviewable like any other change.
    An uncommitted record reads as ``absent`` -- the legacy path, which claims
    nothing.
    """
    record = _committed_record(Path(repo_root), table_dir)
    if record is None:
        return "absent", None
    configured, uncomparable_detail = _configured_digest(repo_root)
    if configured is None and uncomparable_detail is not None:
        return "uncomparable", uncomparable_detail
    return db_provenance.compare(
        record, configured, _committed_map_digest(Path(repo_root), table_dir)
    )


def _committed_text(repo_root: Path, relative: str) -> str | None:
    """``HEAD:./<relative>`` via the hardened git runner; ``None`` on any failure.

    The ``./`` makes the path relative to ``repo_root`` even when that is a
    subdirectory of a larger repository. Not a repository, no git, or a path
    absent from HEAD all read as ``None``.
    """
    from seshat.gitstate import run_git

    try:
        shown = run_git(repo_root.resolve(), "show", f"HEAD:./{relative}")
    except (OSError, ValueError):
        return None
    return shown.stdout if shown.returncode == 0 else None


def _committed_record(repo_root: Path, table_dir: str) -> dict | None:
    """The committed provenance record, ``{}`` if malformed, ``None`` if absent.

    Cheap path first: no worktree file means no git call (a record deleted from
    the worktree but still committed then reads as absent -- the safe direction).
    """
    if not db_provenance.record_path(repo_root, table_dir).is_file():
        return None
    raw = _committed_text(
        repo_root, f"mappings/{table_dir}/{db_provenance.RECORD_FILENAME}"
    )
    return None if raw is None else db_provenance.parse_record(raw)


def _committed_map_digest(repo_root: Path, table_dir: str) -> str | None:
    """The digest of the committed ``source-map.yaml``, or ``None``."""
    raw = _committed_text(repo_root, f"mappings/{table_dir}/source-map.yaml")
    return None if raw is None else db_provenance.source_map_digest(raw)


def verified_caveat(stage_name: str) -> dict[str, str]:
    """The caveat stating the provenance check RAN and agreed for ``stage_name``."""
    return {
        "kind": CAVEAT_KIND_VERIFIED,
        "detail": _VERIFIED_DETAIL.format(stage=stage_name),
    }


def uncomparable_caveat(detail: str) -> dict[str, str]:
    """The caveat stating a record exists but could not be compared."""
    return {"kind": db_provenance.CAVEAT_KIND_UNCOMPARABLE, "detail": detail}
