"""`retail drift` handler (F014 source-drift detector runtime).

Two-mode, mirroring `validate`: without a --dsn (no observed re-profile) it
reports the deferred [PENDING LIVE RE-PROFILE] state and returns 1 -- it NEVER
fabricates a comparison (Principle VIII). A non-conformant baseline is reported
as uncomparable rather than guessed at, and a missing --baseline path is a clean
error, never a raw traceback. The live leg (build a QueryRunner, call
retail.profile.profile, diff) is wired through the cli seams so tests patch it
without touching a real DB.
"""

from __future__ import annotations

import argparse
import json
import sys


def run_drift(args: argparse.Namespace) -> int:
    """Dispatch: read the baseline, then route to the deferred or live leg.

    Kept thin (each leg is its own function) so the guard-heavy live path does
    not turn this into a Bumpy Road / Complex Method.
    """
    from retail.source_profile_reader import read_source_profile

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
    from retail.drift import ReportContext, to_findings_dict

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
    """Resolve the engine's DB config (Postgres: --dsn wins; else env). None-safe."""
    import os

    from retail.validate import resolve_dsn

    if cli._current_engine() == "postgres":
        return resolve_dsn({**os.environ, "DATABASE_URL": args.dsn})
    return dialect.resolve_config(dict(os.environ))


def _run_live_drift(args: argparse.Namespace, parsed: object) -> int:
    """Live leg: re-profile the SAME table on the baseline's STATED PK, diff, emit.

    Mirrors run_validate's DB-boundary discipline -- gate on the lazy driver and
    scrub every DB-boundary exception through dialect.redact(exc, config) so a DSN
    (user/host/password) NEVER leaks in a traceback. Profiling on parsed.pk_columns
    (not a guessed column) keeps baseline.pk and observed.pk on the same key, so
    grain_pk_drift can't be fabricated.
    """
    from retail import cli
    from retail.dialect import get_dialect
    from retail.drift import ReportContext, to_findings_dict
    from retail.profile import profile as run_profile

    dialect = get_dialect(cli._current_engine())
    config = _resolve_live_config(args, cli, dialect)
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

    if not parsed.pk_columns:
        print(
            "retail drift: baseline states no candidate PK column set, so the "
            "live re-profile cannot re-prove grain on the same key. Treated as "
            "uncomparable rather than guessing a key.",
            file=sys.stderr,
        )
        return 1

    try:
        runner = cli._make_runner(config)
        observed = run_profile(runner, parsed.profile.table, parsed.pk_columns)
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
            reprofiled_by="agent (retail.profile, read-only session)",
        ),
    )
    _emit(doc, getattr(args, "output_format", "text"))
    return 0 if doc["status"] in ("pass", "warning") else 1
