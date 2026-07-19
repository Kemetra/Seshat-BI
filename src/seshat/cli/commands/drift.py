"""`retail drift` handler (F014 source-drift detector runtime).

Two-mode, mirroring `validate`: without a --dsn (no observed re-profile) it
reports the deferred [PENDING LIVE RE-PROFILE] state and returns 1 -- it NEVER
fabricates a comparison (Principle VIII). A non-conformant baseline is reported
as uncomparable rather than guessed at, and a missing --baseline path is a clean
error, never a raw traceback. The live leg (build a QueryRunner, call
seshat.profile.profile, diff) is wired through the cli seams so tests patch it
without touching a real DB.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Module-level so the test suite can monkeypatch ``drift.load_drift_semantics``.
# SAFE for the lazy-import discipline: this imports only the FUNCTION NAME; the
# actual pyyaml import lives INSIDE load_drift_semantics, so importing this
# module (e.g. via `retail check`'s dispatch table build) never loads yaml.
from seshat.drift_semantics import load_drift_semantics


class _SemanticsError(Exception):
    """A --source-map path the user NAMED could not be read/parsed. Carries a
    clean, already-formatted message; the live leg turns it into stderr + rc 1
    (never a raw traceback)."""


def run_drift(args: argparse.Namespace) -> int:
    """Dispatch: read the baseline, then route to the deferred or live leg.

    Kept thin (each leg is its own function) so the guard-heavy live path does
    not turn this into a Bumpy Road / Complex Method.
    """
    from seshat.source_profile_reader import read_source_profile

    # A missing/unreadable --baseline path is a distinct failure from a
    # non-conformant one; surface it as a clean message (never a traceback),
    # matching run_validate's "actionable message, not a stack trace" posture.
    try:
        parsed = read_source_profile(args.baseline)
    except OSError as exc:
        print(
            f"retail drift: cannot read baseline {args.baseline!r}: {exc}",
            file=sys.stderr,
        )
        return 1

    if parsed.uncomparable is not None:
        print(f"retail drift: {parsed.uncomparable}", file=sys.stderr)
        return 1

    if not args.dsn:
        return _run_deferred_drift(args, parsed)
    return _run_live_drift(args, parsed)


def _emit(doc: dict, output_format: str) -> None:
    """Shared output: JSON document, or a human status + blocking-reason lines."""
    if output_format == "json":
        print(json.dumps(doc, indent=2))
        return
    n = len(doc["findings"])
    print(f"retail drift: status={doc['status']}; {n} finding(s)")
    for r in doc["blocking_reasons"]:
        print(f"  blocking_reason: {r}")


def _run_deferred_drift(args: argparse.Namespace, parsed: object) -> int:
    """No --dsn: emit a schema-valid pending document; never a fabricated diff."""
    from seshat.drift import ReportContext, to_findings_dict

    doc = to_findings_dict(
        parsed.profile,
        None,
        ReportContext(
            baseline_ref=str(args.baseline),
            evidence=[str(args.baseline)],
        ),
    )
    if getattr(args, "output_format", "text") == "json":
        _emit(doc, "json")
    print(
        "retail drift: [PENDING LIVE RE-PROFILE] -- no --dsn given, so no "
        "observed re-profile was taken. status=pending_live_reprofile + "
        "warning; no comparison fabricated. Pass --dsn to run the live leg.",
        file=sys.stderr,
    )
    return 1


def _resolve_live_config(args: argparse.Namespace, cli: object, dialect: object):
    """Resolve the engine's DB config from the (already `.env`-applied) env.

    Postgres: ``--dsn`` wins; else the env. ``os.environ`` already carries the
    workspace ``.env`` values here because ``_run_live_drift`` runs inside
    ``applied_dotenv`` (#340). None-safe. (Postgres drift is still gated on
    ``--dsn`` upstream in ``run_drift``; the `.env` application fixes engine
    selection, the non-postgres path, and the connection-env parity.)
    """
    import os

    from seshat.validate import resolve_dsn

    if cli._current_engine() == "postgres":
        return resolve_dsn({**os.environ, "DATABASE_URL": args.dsn})
    return dialect.resolve_config(dict(os.environ))


def _source_map_path(args: argparse.Namespace) -> Path | None:
    """Which source-map.yaml to load: --source-map if given (must exist, else
    _SemanticsError), else the sibling of --baseline (None if that has none)."""
    sm_arg = getattr(args, "source_map", None)
    if sm_arg is not None:
        path = Path(sm_arg)
        if not path.is_file():
            raise _SemanticsError(f"--source-map file not found: {sm_arg}")
        return path
    sibling = Path(args.baseline).parent / "source-map.yaml"
    return sibling if sibling.is_file() else None


def _resolve_semantics(args: argparse.Namespace):
    """Load returns/PII semantics for the live leg. None when no source-map is
    present (those classes stay silent). A NAMED-but-missing/malformed path
    raises _SemanticsError (a clean error, not a silent skip)."""
    path = _source_map_path(args)
    if path is None:
        return None
    try:
        return load_drift_semantics(path)
    except (OSError, ValueError) as exc:
        raise _SemanticsError(f"cannot load source-map {path}: {exc}") from exc


def _uncomparable_precondition(parsed: object) -> str | None:
    """The baseline-shape reasons a live re-profile can't run: no stated PK to
    re-prove grain on, or no schema-qualified landed table to connect to. Returns
    the reason (caller reports it + rc 1), or None when the baseline is usable."""
    if not parsed.pk_columns:
        return (
            "baseline states no candidate PK column set, so the live re-profile "
            "cannot re-prove grain on the same key. Treated as uncomparable "
            "rather than guessing a key."
        )
    if not parsed.landed_table:
        return (
            "baseline states no schema-qualified 'Landed location', so the live "
            "re-profile has no connectable target. Treated as uncomparable rather "
            "than guessing the schema (a bare name would mistarget `public`)."
        )
    return None


def _run_live_drift(args: argparse.Namespace, parsed: object) -> int:
    """Live leg: apply the workspace `.env` (#340), then re-profile and diff.

    Thin wrapper: ``applied_dotenv`` makes engine selection and connection
    resolution see the documented ``ANALYTICS_DB_*`` values for the body; a
    malformed ``.env`` fails clean (exit 1, no traceback).
    """
    from pathlib import Path

    from seshat.connection_env import ConnectionConfigError, applied_dotenv
    from seshat.dbt.redaction import EnvironmentConfigError

    try:
        with applied_dotenv(Path.cwd()):
            return _run_live_drift_body(args, parsed)
    except EnvironmentConfigError as exc:
        print(
            f"retail drift: could not read the workspace .env: {exc}",
            file=sys.stderr,
        )
        return 1
    except ConnectionConfigError as exc:
        print(
            f"retail drift: invalid database connection setting: {exc}",
            file=sys.stderr,
        )
        return 1


def _run_live_drift_body(args: argparse.Namespace, parsed: object) -> int:
    """Re-profile the SAME table on the baseline's STATED PK, diff, emit.

    Mirrors run_validate's DB-boundary discipline -- gate on the lazy driver and
    scrub every DB-boundary exception through dialect.redact(exc, config) so a DSN
    (user/host/password) NEVER leaks in a traceback. Profiling on parsed.pk_columns
    (not a guessed column) keeps baseline.pk and observed.pk on the same key, so
    grain_pk_drift can't be fabricated.
    """
    from seshat import cli
    from seshat.connection_env import as_connection_config
    from seshat.dialect import get_dialect
    from seshat.drift import ReportContext, to_findings_dict
    from seshat.profile import profile as run_profile

    # Convert an invalid engine/port setting into a clean boundary failure;
    # the re-profile body below stays outside the wrap (its ValueErrors are real).
    dialect = as_connection_config(lambda: get_dialect(cli._current_engine()))
    config = as_connection_config(lambda: _resolve_live_config(args, cli, dialect))
    if config is None:
        print(
            "retail drift: no database connection configured for the live "
            "re-profile. Pass --dsn (postgresql://...) or set the ANALYTICS_DB_* "
            "vars in your gitignored .env. Never commit a real DSN.",
            file=sys.stderr,
        )
        return 1

    if not cli._ensure_driver():
        print(
            "retail drift: the live re-profile needs the optional DB driver.\n"
            "       install it with:  pip install 'retail[db]'\n"
            "       (the deferred [PENDING LIVE RE-PROFILE] mode needs no driver).",
            file=sys.stderr,
        )
        return 1

    reason = _uncomparable_precondition(parsed)
    if reason is not None:
        print(f"retail drift: {reason}", file=sys.stderr)
        return 1

    # Returns/PII semantics from the source-map (flag > sibling; absent -> None).
    try:
        semantics = _resolve_semantics(args)
    except _SemanticsError as exc:
        print(f"retail drift: {exc}", file=sys.stderr)
        return 1

    try:
        runner = cli._make_runner(config)
        observed = run_profile(runner, parsed.landed_table, parsed.pk_columns)
    except Exception as exc:
        print(
            "retail drift: live re-profile failed at the DB boundary "
            f"({exc.__class__.__name__}): {dialect.redact(exc, config)}",
            file=sys.stderr,
        )
        return 1

    doc = to_findings_dict(
        parsed.profile,
        observed,
        ReportContext(
            baseline_ref=str(args.baseline),
            evidence=[str(args.baseline)],
            reprofiled_by="agent (seshat.profile, read-only session)",
        ),
        semantics=semantics,
    )
    _emit(doc, getattr(args, "output_format", "text"))
    return 0 if doc["status"] in ("pass", "warning") else 1
