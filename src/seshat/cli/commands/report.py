"""``seshat report`` -- render an approved design as HTML, Excel or PDF.

Gated on ``dashboard_ready: pass``. Increment A takes its figures from an
``--observations`` file; increment B replaces that flag with a gold query at the
same seam, so nothing below changes when it lands.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

_FORMATS = ("html", "xlsx", "pdf")
_DEFAULT_OUTPUT = Path(".seshat-output") / "report"
_SUFFIX = {"html": ".html", "xlsx": ".xlsx", "pdf": ".pdf"}

EXIT_OK = 0
EXIT_HARNESS_ERROR = 1
EXIT_REFUSED = 2


def build_report_parser() -> argparse.ArgumentParser:
    """The standalone parser, sharing ONE flag definition with the subcommand.

    The two used to be separate and had drifted: `seshat report --from-gold` failed
    as an unrecognized argument while this parser accepted it.
    """
    from seshat.cli.parser_core import add_report_arguments

    parser = argparse.ArgumentParser(
        prog="seshat report",
        description=(
            "Render an approved design as HTML, Excel or PDF. Every figure cites "
            "the approved metric contract it came from."
        ),
    )
    add_report_arguments(parser)
    return parser


def report_main(args: argparse.Namespace) -> int:
    # Both from `model`, which imports no optional extra. Importing
    # SurfaceRenderFailed from `seshat.report.html` made jinja2 mandatory for every
    # invocation, so a refusal that renders nothing -- a blocked gate, no figure
    # source -- died with ModuleNotFoundError instead of printing its guidance.
    from seshat.report.model import ReportError, SurfaceRenderFailed

    try:
        written = _render(args)
    except (ReportError, SurfaceRenderFailed) as exc:
        # SurfaceRenderFailed subclasses RuntimeError rather than ReportError, so
        # without it a documented option -- any --language the bundle has no
        # rendering for -- produced a traceback instead of the promised refusal.
        print(f"[FAIL] {exc}", flush=True)
        return EXIT_REFUSED
    except OSError as exc:
        print(f"[FAIL] {exc}", flush=True)
        return EXIT_HARNESS_ERROR
    print(f"[OK] wrote {written}", flush=True)
    return EXIT_OK


def approved_contracts(repo_root: Path, table: str) -> dict[str, str]:
    """Contract id -> path, for the contracts that are actually APPROVED.

    File presence is not approval. A draft, blocked, or malformed contract sitting
    in ``metrics/`` was previously exposed by its stem alone, so an observation
    could cite it and the report would advertise governed provenance for a metric
    nobody signed off. Each file's own ``readiness.status`` decides, and anything
    other than ``pass`` is left out -- which makes every observation citing it
    refuse.
    """
    from seshat.report.model import ReportError

    directory = repo_root / "mappings" / table / "metrics"
    if not directory.is_dir():
        return {}
    approved: dict[str, str] = {}
    for path in sorted(directory.glob("*.yaml")):
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ReportError(f"cannot read contract {path}: {exc}") from exc
        if _contract_is_approved(loaded):
            approved[path.stem] = str(path.relative_to(repo_root))
    return approved


def _contract_is_approved(loaded: object) -> bool:
    if not isinstance(loaded, dict):
        return False
    readiness = loaded.get("readiness")
    if not isinstance(readiness, dict):
        return False
    return readiness.get("status") == "pass"


def load_observations(path: Path, *, expect_table: str | None = None) -> list[dict]:
    """The figures and their values, with the document's identity checked.

    ``expect_table`` closes a hole that document-level identity existed to close:
    two tables can share visual and contract ids, so an observations file written
    for one could be rendered under the other's name, and the cover would state the
    requested table while publishing the other's figures with apparently valid
    provenance.
    """
    loaded = _document(path)
    _assert_declares_table(loaded, path, expect_table)
    return [_observation(entry, path) for entry in _entries(loaded, path)]


def _document(path: Path) -> dict:
    """The parsed file, refusing an unreadable one and anything but a document."""
    from seshat.report.model import ReportError

    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ReportError(f"cannot read observations {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ReportError(
            f"observations {path} is not a mapping; it must be a document with an "
            "`observations:` list and the `table:` it was produced for"
        )
    return loaded


def _entries(loaded: dict, path: Path) -> list:
    """The observations list. An empty one renders nothing, so it refuses."""
    from seshat.report.model import ReportError

    entries = loaded.get("observations")
    if not isinstance(entries, list) or not entries:
        raise ReportError(f"{path} declares no observations")
    return entries


def _assert_declares_table(loaded: dict, path: Path, expect_table: str | None) -> None:
    from seshat.report.model import ReportError

    if expect_table is None:
        return
    declared = loaded.get("table")
    if not declared:
        raise ReportError(
            f"observations {path} names no `table:`. It has to say which table it was "
            f"produced for, so it cannot be rendered under another one -- add "
            f"`table: {expect_table}` if that is what it holds."
        )
    if str(declared) != expect_table:
        raise ReportError(
            f"observations {path} was produced for {str(declared)!r}, not "
            f"{expect_table!r}. Two tables can share visual and contract ids, so the "
            "cover would name one table while publishing the other's figures."
        )


def _observation(entry: object, path: Path) -> dict[str, object]:
    from seshat.report.model import ReportError

    if not isinstance(entry, dict):
        raise ReportError(f"{path} has a non-mapping observation")
    raw = entry.get("value")
    if raw is None:
        return {**entry, "value": None}
    return {**entry, "value": _exact_decimal(raw, entry.get("visual_id"), path)}


def _exact_decimal(raw: object, visual_id: object, path: Path) -> Decimal:
    """Parse a governed figure, refusing every form that is not exact.

    A YAML float has ALREADY lost precision by the time it reaches here --
    ``safe_load`` converted it to binary before this code ran, so wrapping it in
    ``Decimal`` preserves the rounded value, not the authored one. The refusal has
    to happen on the type.

    ``NaN`` and ``Infinity`` are valid ``Decimal`` values and neither is a figure:
    ``NaN`` would publish as a governed number, and infinity reaches ``quantize()``
    and raises where a refusal belongs.
    """
    from seshat.report.model import ReportError

    if isinstance(raw, float):
        raise ReportError(
            f"observation {visual_id!r} in {path} writes {raw!r} as a YAML float, "
            "which lost precision before this check could run. Quote it "
            f'(`value: "{raw!r}"`) so the authored decimal is preserved exactly.'
        )
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError) as exc:
        raise ReportError(
            f"observation {visual_id!r} value {raw!r} is not an exact decimal: {exc}"
        ) from exc
    if not value.is_finite():
        raise ReportError(
            f"observation {visual_id!r} value {raw!r} is not a finite number. A "
            "report states what was measured; NaN and infinity are not measurements."
        )
    return value


# Every incoherent combination of the figure-source flags, and what to say about
# it. Kept as data so adding a source is one entry rather than another branch, and
# so no combination can be left silently resolving to a default -- preferring one
# source silently is how a report shows warehouse numbers to someone who believes
# they rendered a file.
_INCOHERENT: tuple[tuple[str, str], ...] = (
    (
        "from_gold and observations",
        "--from-gold and --observations both name a source of figures. Pass one: "
        "--from-gold reads the warehouse, --observations reads the file.",
    ),
    (
        "from_gold and not plan",
        "--from-gold needs --figure-plan <file>: the warehouse supplies values, but "
        "which figures to render and how to format them is not something a table "
        "can say.",
    ),
    (
        "plan and not from_gold",
        "--figure-plan carries no values, so it renders nothing on its own. Add "
        "--from-gold to fill it from the warehouse.",
    ),
    (
        "neither",
        "no figure source: pass --observations <file> to render from a file, or "
        "--from-gold --figure-plan <file> to read the warehouse.",
    ),
)


def _figure_source_faults(args: argparse.Namespace) -> set[str]:
    """Which of the named incoherent combinations this invocation matches."""
    gold = bool(args.from_gold)
    plan = args.figure_plan is not None
    observations = args.observations is not None
    return {
        name
        for name, present in (
            ("from_gold and observations", gold and observations),
            ("from_gold and not plan", gold and not plan),
            ("plan and not from_gold", plan and not gold),
            ("neither", not gold and not observations),
        )
        if present
    }


def _assert_one_figure_source(args: argparse.Namespace) -> None:
    """Exactly one source of figures, chosen explicitly."""
    from seshat.report.model import ReportError

    faults = _figure_source_faults(args)
    for name, refusal in _INCOHERENT:
        if name in faults:
            raise ReportError(refusal)


def _live_observations(
    args: argparse.Namespace, repo_root: Path
) -> list[dict[str, object]]:
    """Resolve the plan's figures against gold, through the governed bindings.

    All that is left here is the driver: reading the plan, checking it against the
    signed bindings, and loading the contracts are domain concerns and live in
    :mod:`seshat.report.plan`.
    """
    from seshat import cli
    from seshat.dialect import get_dialect
    from seshat.report.binding import binding_map_path, load_binding_map
    from seshat.report.model import ReportError
    from seshat.report.plan import (
        contract_payloads,
        figure_requests,
        load_figure_plan,
    )

    binding_map = load_binding_map(
        binding_map_path(repo_root, args.table), expect_table=args.table
    )
    requests = figure_requests(load_figure_plan(args.figure_plan), binding_map)
    contracts = contract_payloads(repo_root, args.table)
    if not cli._ensure_driver():
        raise ReportError(
            "--from-gold needs the optional DB driver. Install it with "
            '`pip install "seshat-bi[db]"`. Rendering from --observations needs no '
            "driver."
        )
    engine = cli._current_engine()
    config = _connection_config(args, engine)
    if config is None:
        raise ReportError(
            "--from-gold found no database connection configured. Pass --dsn (a "
            "postgresql:// connection string), or set DATABASE_URL, or the "
            "ANALYTICS_DB_* vars in your gitignored .env -- never a committed one. "
            "Connecting on libpq's ambient defaults could read an unintended "
            "database and publish its numbers under this table's name."
        )
    return _read_gold(requests, contracts, get_dialect(engine), config)


def _connection_config(args: argparse.Namespace, engine: str) -> object:
    """The connection, resolved the same way `value-check` resolves it.

    Postgres: ``--dsn`` wins, else the environment. Every other engine resolves
    from the environment through its own dialect (``--dsn`` is Postgres-only).
    Returns None when nothing is configured, which the caller refuses on.
    """
    import os

    from seshat.dialect import get_dialect
    from seshat.validate import resolve_dsn

    if engine != "postgres":
        return get_dialect(engine).resolve_config(dict(os.environ))
    env = dict(os.environ)
    if args.dsn:
        env = {**env, "DATABASE_URL": args.dsn}
    return resolve_dsn(env)


def _read_gold(
    requests: list, contracts: dict, dialect: object, config: object
) -> list[dict[str, object]]:
    """Read the figures, turning every DB-boundary failure into a refusal.

    A driver exception is not an ``OSError``, so without this it left the handler
    as a traceback -- carrying the host, user and database the driver reformats
    into its own message. The dialect's own redactor scrubs the config out of it,
    and the caller reports it as a refusal with the deferred-mode guidance.
    """
    from seshat import cli
    from seshat.report.model import ReportError
    from seshat.report.observe import observe

    try:
        runner = cli._make_runner(config)
        return observe(runner, requests, contracts, dialect=dialect)
    except ReportError:
        # A contract this module refuses to compile is not a boundary failure.
        raise
    except Exception as exc:
        raise ReportError(
            "--from-gold failed at the DB boundary "
            f"({exc.__class__.__name__}): {dialect.redact(exc, config)}. Verify the "
            "DSN, network access and the gold objects the contracts bind to."
        ) from exc


def _governed_bindings(repo_root: Path, table: str) -> dict[str, str] | None:
    """visual_id -> contract, from the signed binding map, or None if there is none.

    ``None`` is not "no constraint by choice": it means the table has no committed
    binding map at all, and the bundle then falls back to checking only that a cited
    contract is approved. A table that HAS a map gets the exact pair checked.
    """
    from seshat.report.binding import binding_map_path, load_binding_map

    path = binding_map_path(repo_root, table)
    if not path.is_file():
        return None
    binding_map = load_binding_map(path, expect_table=table)
    return {binding.visual_id: binding.contract for binding in binding_map.bindings}


def _definitions(repo_root: Path, table: str) -> dict[str, dict]:
    """The parsed contracts, for the facts an observation must not restate."""
    from seshat.report.plan import contract_payloads

    return contract_payloads(repo_root, table)


def _render(args: argparse.Namespace) -> Path:
    from seshat.report.bundle import ApprovedDesign, build_bundle
    from seshat.report.gate import assert_renderable
    from seshat.report.layout import load_layout
    from seshat.report.vocabulary import load_vocabulary, vocabulary_path

    repo_root = args.repo_root.resolve()
    assert_renderable(repo_root, args.table)

    layout_path = (
        args.layout
        or repo_root / "mappings" / args.table / "design" / "report-layout.yaml"
    )
    layout = load_layout(layout_path)

    _assert_one_figure_source(args)
    if args.from_gold:
        observations = _live_observations(args, repo_root)
    else:
        observations = load_observations(args.observations, expect_table=args.table)
    bundle = build_bundle(
        table=args.table,
        # The AUDIENCE, not the locale. `generated_for` is printed on the cover and
        # recorded in Excel provenance, so passing the language stamped every report
        # as generated for "en".
        generated_for=args.audience,
        design=ApprovedDesign(
            layout=layout,
            contracts=approved_contracts(repo_root, args.table),
            bindings=_governed_bindings(repo_root, args.table),
            definitions=_definitions(repo_root, args.table),
        ),
        observations=observations,
    )
    vocabulary = load_vocabulary(vocabulary_path(repo_root, args.table), args.language)
    return _write(args, bundle, layout, vocabulary)


def _write(args: argparse.Namespace, bundle, layout, vocabulary) -> Path:
    destination = args.output / f"{args.table}{_SUFFIX[args.format]}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "html":
        from seshat.report.html import HtmlReportRenderer

        surface = HtmlReportRenderer().render(bundle, layout, vocabulary)
        destination.write_text(surface.document, encoding="utf-8")
        return destination
    if args.format == "xlsx":
        from seshat.report.excel import ExcelReportRenderer

        surface = ExcelReportRenderer().render(bundle, layout, vocabulary)
        destination.write_bytes(surface.workbook_bytes)
        return destination
    from seshat.report.chromium import build_printer
    from seshat.report.pdf import PdfReportRenderer

    surface = PdfReportRenderer(build_printer()).render(bundle, layout, vocabulary)
    destination.write_bytes(surface.pdf_bytes)
    return destination
