"""`retail value-check` handler: L4 value proxy (live recompute vs approved value).

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
Calls the shared seams (``_ensure_driver``, ``_make_runner``, ``_current_engine``,
``_safe_target_label``) via ``from seshat import cli`` -- NOT a by-value import --
so the test suite's ``monkeypatch.setattr("seshat.cli._make_runner", ...)`` still
lands on the exact attribute this handler reads at call time.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path


def _filter_to_sql(filters: object, quote: Callable[..., str]) -> str | None:
    """Translate an L3 ``filter`` list into a SQL WHERE predicate (AND-joined).

    Reuses the L3 recognized-op vocabulary (``is_not_null`` / ``is_true``); each
    column is quoted via the hardened identifier helper. Returns None for an
    unrecognized op or a malformed entry (the caller fails the check closed).
    Empty/None filter list => "TRUE" (count all rows).
    """
    if not filters:
        return "TRUE"
    if not isinstance(filters, list):
        return None
    parts: list[str] = []
    for f in filters:
        predicate = _filter_entry_to_sql(f, quote)
        if predicate is None:
            return None
        parts.append(predicate)
    return " AND ".join(parts)


def _filter_entry_to_sql(entry: object, quote: Callable[..., str]) -> str | None:
    """Map one L3 filter entry to a SQL predicate, or None if unrecognized.

    A recognized op (``is_not_null`` / ``is_true``) yields a predicate over the
    quoted column; anything else -- a non-dict entry, a missing column, or an
    unknown op -- returns None so the caller can fail the check closed.
    """
    if not isinstance(entry, dict):
        return None
    col, op = entry.get("column"), entry.get("op")
    if not col:
        return None
    qcol = quote(col, context="L4 ratio filter column")
    if op == "is_not_null":
        return f"{qcol} IS NOT NULL"
    if op == "is_true":
        return f"{qcol} = TRUE"
    return None


class _ContractError(Exception):
    """A fail-closed contract-processing failure carrying its pre-formatted message.

    Raised at the exact sites that would otherwise ``print(...); return 1`` while
    parsing a contract, so the caller can collapse the per-contract loop's error
    handling into a single ``except`` without widening any catch.
    """


def _resolve_engine_config(engine: str, args: argparse.Namespace) -> object:
    """Resolve the engine's DB config, or None if none is configured.

    Postgres: --dsn wins; else env (UNCHANGED behavior). Other engines: --dsn is
    not applicable; resolve from env only.
    """
    import os

    from seshat.dialect import get_dialect
    from seshat.validate import resolve_dsn

    if engine == "postgres":
        env = dict(os.environ)
        if args.dsn:
            env = {**env, "DATABASE_URL": args.dsn}
        return resolve_dsn(env)
    return get_dialect(engine).resolve_config(dict(os.environ))


def _parse_one_contract(
    contract_path: Path, dialect: object
) -> tuple[str, object] | None:
    """Parse one metric contract into ``(measure_name, ExpectedValue)``.

    Returns None when the contract carries no ``expected_value`` block (a skip).
    Raises ``_ContractError`` with a caller-ready message for a load/parse failure
    (fail-closed). Any other exception (e.g. a ``TypeError`` from the parser)
    propagates uncaught, exactly as before the extraction.
    """
    from seshat.value_proxy import parse_expected_value

    name = contract_path.stem
    definition, binds_to = _load_contract_doc(contract_path)
    try:
        expected = parse_expected_value(definition, binds_to)
    except ValueError as exc:
        raise _ContractError(
            f"error: contract {name}: malformed expected_value ({exc})"
        ) from exc
    if expected is None:
        return None  # no expected_value block -> skip
    if expected.aggregation == "ratio":
        expected = _resolve_ratio_filters(name, definition, expected, dialect)
    return (name, expected)


def _load_contract_doc(contract_path: Path) -> tuple[object, dict]:
    """Load a contract's ``definition`` and its top-level ``binds_to`` mapping.

    Both loads share the fail-closed "could not load contract" message. Raises
    ``_ContractError`` on any load failure (``OSError`` / ``ValueError``).
    """
    from seshat.metric_drift import load_definition

    def _fail(exc: Exception) -> _ContractError:
        return _ContractError(f"error: could not load contract {contract_path}: {exc}")

    try:
        definition = load_definition(str(contract_path))
    except (OSError, ValueError) as exc:
        raise _fail(exc) from exc
    # binds_to lives at the contract top level, not under `definition`.
    try:
        import yaml

        doc = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError) as exc:
        raise _fail(exc) from exc
    return definition, doc.get("binds_to") or {}


def _resolve_ratio_filters(
    name: str, definition: object, expected: object, dialect: object
) -> object:
    """Translate the L3 numerator/denominator filters into SQL for a ratio.

    Returns a copy of ``expected`` carrying the compiled SQL filters. Raises
    ``_ContractError`` if either filter uses an op L4 cannot recompute.
    """
    import dataclasses

    num_sql = _filter_to_sql(
        (definition or {}).get("numerator", {}).get("filter"), dialect.quote_ident
    )
    den_sql = _filter_to_sql(
        (definition or {}).get("denominator", {}).get("filter"), dialect.quote_ident
    )
    if num_sql is None or den_sql is None:
        raise _ContractError(
            f"error: contract {name}: ratio numerator/denominator filter "
            "uses an unrecognized op (L4 cannot recompute it)"
        )
    return dataclasses.replace(
        expected,
        numerator_count_sql_filter=num_sql,
        denominator_count_sql_filter=den_sql,
    )


def _load_expectations(metrics_root: Path, dialect: object) -> list[tuple[str, object]]:
    """Discover contracts under ``metrics_root`` and parse each expected_value block.

    Fail-closed: a load/parse error raises ``_ContractError`` (never a silent
    skip); a contract with no expected_value block is skipped.
    """
    expectations: list[tuple[str, object]] = []  # (measure_name, ExpectedValue)
    if not metrics_root.is_dir():
        return expectations
    for contract_path in sorted(metrics_root.glob("*/metrics/*.yaml")):
        parsed = _parse_one_contract(contract_path, dialect)
        if parsed is not None:
            expectations.append(parsed)
    return expectations


def _preflight_config(
    cli: object, engine: str, args: argparse.Namespace, metrics_root: Path
) -> object:
    """Validate the metrics dir, resolve DB config, and gate on the lazy driver.

    Returns the resolved config. Raises ``_ContractError`` (with the caller-ready
    message) for a metrics-dir escape, missing connection config, or missing DB
    driver -- so ``run_value_check`` handles all three the same fail-closed way.
    """
    # Confine --metrics-dir to the repo tree (same guard as semantic-check, #26).
    repo_resolved = Path(args.repo).resolve()
    if metrics_root != repo_resolved and not metrics_root.is_relative_to(repo_resolved):
        raise _ContractError(
            f"error: --metrics-dir {args.metrics_dir!r} escapes the repo root; "
            "it must resolve to a path inside --repo."
        )
    # Postgres: --dsn wins; else env (UNCHANGED). Other engines: env only.
    config = _resolve_engine_config(engine, args)
    if config is None:
        raise _ContractError(
            "error: no database connection configured.\n"
            "       pass --dsn (a postgresql:// connection string), or set\n"
            "       DATABASE_URL, or the ANALYTICS_DB_* vars (in your gitignored\n"
            "       .env). Never commit a real DSN."
        )
    # The DB driver is optional + lazy: only needed for a real run.
    if not cli._ensure_driver():
        raise _ContractError(
            "error: `retail value-check` needs the optional DB driver.\n"
            "       install it with:  pip install 'retail[db]'\n"
            "       (the static `retail check` core stays dependency-free)."
        )
    return config


def _recompute_findings(
    cli: object, config: object, expectations: list[tuple[str, object]], dialect: object
) -> list:
    """Build the runner and recompute each contract's expected value.

    Takes the ``cli`` module (not bound functions) so ``_make_runner`` is read at
    call time -- keeping the test suite's ``monkeypatch.setattr`` on that seam
    effective. No real DB is touched in tests (fake runner). A ``ValueError`` (an
    unsafe identifier) or any DB-boundary failure is turned into a caller-ready,
    traceback-free ``_ContractError``.
    """
    from seshat.value_proxy import check_expected_value

    try:
        runner = cli._make_runner(config)
        findings = []
        for name, expected in expectations:
            findings.extend(
                check_expected_value(runner, name, expected, dialect=dialect)
            )
    except ValueError as exc:
        # an unsafe identifier in a contract -> clean message, no traceback
        raise _ContractError(
            f"error: value-check rejected an unsafe contract identifier: {exc}"
        ) from exc
    except Exception as exc:
        raise _ContractError(
            "error: live value-check failed at the DB boundary "
            f"({exc.__class__.__name__}): {dialect.redact(exc, config)}"
        ) from exc
    return findings


def run_value_check(args: argparse.Namespace) -> int:
    """Run the L4 value proxy: recompute each contract's approved value live.

    Lazy psycopg2 (via ``_ensure_driver`` / ``_make_runner``, reused from the
    validate path) so the stdlib-only `retail check` chain never imports a driver.
    Discovers metric contracts under --metrics-dir (confined to the repo, like
    semantic-check), parses each ``definition.expected_value`` block, recomputes the
    aggregate/ratio against the live gold table, and reports a V-L4 ERROR for any
    value outside tolerance. A contract with no expected_value block is skipped; a
    malformed block is a fail-closed ERROR, never a silent skip.
    """
    from seshat import cli
    from seshat.dialect import get_dialect

    engine = cli._current_engine()
    dialect = get_dialect(engine)
    metrics_root = (Path(args.repo) / args.metrics_dir).resolve()

    # Steps 1-3: preflight (metrics-dir guard, config, driver) then discover +
    # parse each expected_value block. All fail-closed via _ContractError.
    try:
        config = _preflight_config(cli, engine, args, metrics_root)
        expectations = _load_expectations(metrics_root, dialect)
    except _ContractError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not expectations:
        print(
            "retail value-check: no contract carries a `definition.expected_value` "
            "block -- nothing to verify.",
            file=sys.stderr,
        )
        return 0

    # Step 4: connect and run each check. No real DB is touched in tests (fake runner).
    safe_host = cli._safe_target_label(engine, config)
    print(
        f"retail value-check: running L4 value checks against {safe_host}",
        file=sys.stderr,
    )
    try:
        findings = _recompute_findings(cli, config, expectations, dialect)
    except _ContractError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return _report_findings(findings)


def _report_findings(findings: list) -> int:
    """Print each finding and return the exit code (1 iff any ERROR-severity)."""
    from seshat.core import Severity
    from seshat.runner import _format

    for finding in findings:
        print(_format(finding))
    if any(f.severity is Severity.ERROR for f in findings):
        return 1
    print(
        "retail value-check: all live values match the approved contracts "
        "(0 findings).",
        file=sys.stderr,
    )
    return 0
