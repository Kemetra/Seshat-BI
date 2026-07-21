"""`seshat profile` handler: the mechanical Stage-1 profiler as a CLI verb.

``scaffold-source`` writes a blank ``source-profile.md`` and directs the analyst
to fill the mechanical numbers (row/column count, per-column ''-OR-NULL
missingness, distinct cardinality, and the candidate-PK uniqueness proof). Those
numbers come from :func:`seshat.profile.profile`, but on a ``pipx`` install that
function is unreachable to a customer: ``import seshat`` fails from a normal
``python`` (the package lives in the isolated pipx venv) and there was no CLI
verb to run it (#400). This handler closes that gap -- it drives the SAME
``profile()`` the drift path uses, over a read-only connection, and emits the
filled markdown block (or JSON) the analyst pastes into ``source-profile.md``.

Modeled on ``commands/validate.py``: the DB driver is optional + LAZY, the
workspace ``.env`` is applied for the whole body (#340), and a missing driver /
DSN exits non-zero with an actionable message, never a raw traceback. Calls the
shared seams via ``from seshat import cli`` and ``cli.<name>(...)`` -- NOT a
by-value import -- so the test suite's ``monkeypatch.setattr("seshat.cli.
_make_runner", ...)`` still lands on the attribute this handler reads at call
time.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable


def _resolve_config(
    args: argparse.Namespace,
    engine: str,
    dialect: object,
    resolve_dsn: Callable[[dict[str, str]], str | None],
) -> object:
    """Resolve the engine's DB config from the (already `.env`-applied) env.

    Mirror of ``validate._resolve_config``: Postgres honors ``--dsn`` then the
    env; other engines resolve from env only (``--dsn`` is Postgres-only).
    """
    import os

    if engine == "postgres":
        env = dict(os.environ)
        if args.dsn:
            env = {**env, "DATABASE_URL": args.dsn}
        return resolve_dsn(env)
    return dialect.resolve_config(dict(os.environ))  # type: ignore[attr-defined]


def _parse_pk(raw: str) -> tuple[str, ...]:
    """Split the ``--pk`` value (comma-separated) into a candidate-key tuple."""
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _validate_args(args: argparse.Namespace) -> tuple[str, ...] | None:
    """Validate ``--pk`` and ``--table``; return the candidate-key tuple, or
    ``None`` after printing an actionable error (caller exits 1).

    Extracted from the handler to keep it small. ``--table`` must be EXACTLY
    ``schema.table``: ``_discover_columns`` splits on the first dot, so an
    unqualified name OR a 3-part ``database.schema.table`` (SQL Server) discovers
    zero columns while the row/PK aggregates still resolve -- an exit-0 empty
    profile (#409).
    """
    candidate_pk = _parse_pk(args.pk)
    if not candidate_pk:
        print(
            "error: --pk must name at least one column (the candidate grain key; "
            "comma-separate a composite, e.g. --pk invoice_id,line_no).",
            file=sys.stderr,
        )
        return None
    parts = args.table.split(".")
    if len(parts) != 2 or not all(parts):
        print(
            "error: --table must be exactly schema.table, e.g. bronze.<table> "
            f"(got {args.table!r}).",
            file=sys.stderr,
        )
        return None
    return candidate_pk


def _resolve_engine(args: argparse.Namespace, cli, prog: str):
    """Resolve (engine, dialect, config) for the run, or ``None`` on a clean
    failure (message already printed).

    Extracted from ``_run_profile_body`` to keep that handler small: it folds
    the engine pick, config resolution (--dsn/env), and the optional-driver
    check into one preflight that either yields the connect inputs or prints an
    actionable error and signals the caller to exit 1.
    """
    from seshat.connection_env import as_connection_config
    from seshat.dialect import get_dialect
    from seshat.validate import resolve_dsn

    engine = cli._current_engine()
    dialect = as_connection_config(lambda: get_dialect(engine))
    config = as_connection_config(
        lambda: _resolve_config(args, engine, dialect, resolve_dsn)
    )
    if config is None:
        print(
            "error: no database connection configured.\n"
            "       pass --dsn (a postgresql:// connection string), or set\n"
            "       DATABASE_URL, or the ANALYTICS_DB_* vars (in your gitignored\n"
            "       .env). Never commit a real DSN.",
            file=sys.stderr,
        )
        return None
    if not cli._ensure_driver():
        print(
            f"error: `{prog} profile` needs the optional DB driver.\n"
            f"{cli._db_extra_hint(engine)}\n"
            f"       (the static `{prog} check` core stays dependency-free).",
            file=sys.stderr,
        )
        return None
    return engine, dialect, config


def run_profile(args: argparse.Namespace) -> int:
    """Run the mechanical profiler against a real DB, honoring the workspace `.env`.

    Thin wrapper: apply the workspace ``.env`` (#340) for the whole body so
    engine selection, driver choice, and config resolution all see the
    documented ``ANALYTICS_DB_*`` values, then delegate. A malformed ``.env``
    fails clean (exit 1, no traceback).
    """
    from pathlib import Path

    from seshat.connection_env import ConnectionConfigError, applied_dotenv
    from seshat.dbt.redaction import EnvironmentConfigError

    try:
        with applied_dotenv(Path.cwd()):
            return _run_profile_body(args)
    except EnvironmentConfigError as exc:
        print(f"error: could not read the workspace .env: {exc}", file=sys.stderr)
        return 1
    except ConnectionConfigError as exc:
        print(f"error: invalid database connection setting: {exc}", file=sys.stderr)
        return 1


def _run_profile_body(args: argparse.Namespace) -> int:
    """Resolve config + driver, profile the table, render the numbers.

    The DB driver import is LAZY (via ``_ensure_driver`` / ``_make_runner``) so
    the stdlib-only ``check`` core never imports it. Engine selection follows
    ``validate``: ``ANALYTICS_DB_ENGINE`` (default ``postgres``) picks the
    Dialect; the Postgres path keeps using --dsn/DATABASE_URL verbatim.
    """
    from seshat import cli

    prog = cli._prog(args)  # brand the client typed (`seshat`/`retail`), #402

    candidate_pk = _validate_args(args)
    if candidate_pk is None:
        return 1

    resolved = _resolve_engine(args, cli, prog)
    if resolved is None:
        return 1
    return _profile_and_render(args, cli, resolved, candidate_pk)


def _profile_and_render(
    args: argparse.Namespace,
    cli,
    resolved: tuple[str, object, object],
    candidate_pk: tuple[str, ...],
) -> int:
    """Run the mechanical profile over a live connection and emit the result.

    Extracted from ``_run_profile_body`` to keep that handler small (code-health
    gate): it prints the credential-free target line, then owns the DB-boundary
    contract -- any failure is redacted through ``dialect.redact`` and reported
    with the engine-specific driver remedy, never surfaced as a raw traceback --
    then renders JSON or the pasteable markdown. Takes the ``resolved`` tuple
    ``_resolve_engine`` already returns (engine, dialect, config), not three
    loose primitives, and re-derives ``prog`` via ``cli._prog(args)``, so the
    seam stays at four arguments.
    """
    from seshat.profile import profile as run_mechanical_profile

    prog = cli._prog(args)  # brand the client typed (`seshat`/`retail`), #402
    engine, dialect, config = resolved
    safe_host = cli._safe_target_label(engine, config)
    print(
        f"{prog} profile: profiling {args.table} against {safe_host}",
        file=sys.stderr,
    )
    try:
        runner = cli._make_runner(config)
        result = run_mechanical_profile(
            runner, args.table, candidate_pk, dialect=dialect
        )
    except Exception as exc:
        print(
            "error: profiling failed at the DB boundary "
            f"({exc.__class__.__name__}): {dialect.redact(exc, config)}",
            file=sys.stderr,
        )
        print(
            "       verify the DSN, network access, the table + columns exist, "
            "and the optional DB driver:\n"
            f"{cli._db_extra_hint(engine)}",
            file=sys.stderr,
        )
        return 1

    if args.output_format == "json":
        print(_render_json(result, candidate_pk))
    else:
        print(_render_markdown(result, candidate_pk))
    return 0


def _render_json(result: object, candidate_pk: tuple[str, ...]) -> str:
    """Emit the ProfileResult as a JSON document (machine-readable)."""
    import json

    return json.dumps(
        {
            "table": result.table,
            "row_count": result.row_count,
            "column_count": result.column_count,
            "columns": [
                {
                    "name": col.name,
                    "landed_type": col.landed_type,
                    "missing_count": col.missing_count,
                    "missing_pct": round(col.missing_pct, 2),
                    "distinct_cardinality": col.distinct_cardinality,
                }
                for col in result.columns
            ],
            "pk": {
                "columns": list(candidate_pk),
                "total": result.pk.total,
                "distinct_pk": result.pk.distinct_pk,
                "null_pk": result.pk.null_pk,
                "is_unique": result.pk.is_unique,
            },
        },
        indent=2,
    )


def _render_markdown(result: object, candidate_pk: tuple[str, ...]) -> str:
    """Render the mechanical numbers as source-profile.md blocks to paste.

    Fills the *Shape*, *Per-column profile*, and *Candidate grain & candidate PK*
    sections. The numeric cells are emitted in the EXACT template/reader-accepted
    format (bare numbers, not backtick-wrapped; the ``**Candidate PK:**`` line
    stated) so a pasted profile round-trips through ``read_source_profile()`` and
    can serve as a drift baseline (PR #409 review). The semantic passes
    (code<->label 1:1, dimension fan-out, returns rule) are deliberately NOT
    emitted -- they need the table's MEANING and are a Principle-V judgment call
    the analyst records by hand.
    """
    lines: list[str] = []
    lines.append(f"## Shape  (profiled: `{result.table}`)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    # Bare numbers (not backticked): `_find_row_count` / `_COL_ROW` in
    # source_profile_reader.py match a plain `[\d,]+`, so a backtick would make
    # the pasted profile non-conformant and unusable as a drift baseline.
    lines.append(f"| Row count (landed) | {result.row_count:,} |")
    lines.append(f"| Column count (landed) | {result.column_count} |")
    lines.append("")
    lines.append("## Per-column profile")
    lines.append("")
    lines.append(
        "| Column | Type as landed | Missingness (`'' OR NULL`, count / %) "
        "| Distinct cardinality |"
    )
    lines.append("|--------|----------------|----------------|----------------|")
    for col in result.columns:
        landed = col.landed_type or "TEXT"
        lines.append(
            f"| `{col.name}` | {landed} | {col.missing_count:,} / "
            f"{col.missing_pct:.2f}% | {col.distinct_cardinality:,} |"
        )
    lines.append("")
    lines.append("## Candidate grain & candidate PK")
    lines.append("")
    # State the candidate PK the run used, in the reader's parsed form
    # (`**Candidate PK:** ( col_a, col_b )`) -- without it `_find_pk_columns`
    # returns None and the live drift path refuses the baseline (PR #409 review).
    pk_decl = ", ".join(candidate_pk)
    lines.append(f"- **Candidate PK:** `( {pk_decl} )`.")
    lines.append("- **Uniqueness proof (on the landed data):**")
    lines.append(f"  - `COUNT(*)            = {result.pk.total:,}`")
    lines.append(f"  - `COUNT(DISTINCT pk)  = {result.pk.distinct_pk:,}`")
    # Use the exact label `read_source_profile()` parses (`NULLs/empty in PK`,
    # matching the committed filled examples) so a pasted profile round-trips:
    # the wrong label would make the reader default null_pk to 0 and
    # mis-reconstruct the uniqueness state, corrupting a grain-drift comparison.
    lines.append(f"  - `NULLs/empty in PK   = {result.pk.null_pk:,}`")
    verdict = (
        "[OK] candidate PK holds on the landed data"
        if result.pk.is_unique
        else "[x] candidate PK is NOT unique on the landed data"
    )
    lines.append(f"  - {verdict}")
    lines.append("")
    lines.append(
        "> Mechanical numbers only. The semantic passes (code<->label 1:1, "
        "dimension fan-out, the authoritative returns column, money identities) "
        "are a Principle-V judgment call -- record them by hand; they are not "
        "computed here. Re-verify the PK on the TRANSFORMED silver output "
        "(ADR 0002 RC2)."
    )
    return "\n".join(lines)
