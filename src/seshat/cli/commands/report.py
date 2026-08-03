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
    parser = argparse.ArgumentParser(
        prog="seshat report",
        description=(
            "Render an approved design as HTML, Excel or PDF. Every figure cites "
            "the approved metric contract it came from."
        ),
    )
    parser.add_argument("--table", required=True)
    parser.add_argument("--format", required=True, choices=_FORMATS)
    parser.add_argument("--language", default="en")
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument(
        "--layout",
        type=Path,
        default=None,
        help="print overlay; defaults to mappings/<table>/design/report-layout.yaml",
    )
    parser.add_argument(
        "--observations",
        type=Path,
        default=None,
        help="figures WITH values, read offline; no database is contacted",
    )
    parser.add_argument(
        "--from-gold",
        action="store_true",
        help="read every figure's value from the warehouse; needs --figure-plan",
    )
    parser.add_argument(
        "--figure-plan",
        type=Path,
        default=None,
        help="which figures to render and how to format them, carrying NO values",
    )
    parser.add_argument(
        "--dsn",
        default=None,
        help="Postgres DSN for --from-gold; falls back to the workspace environment",
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def report_main(args: argparse.Namespace) -> int:
    from seshat.report.model import ReportError

    try:
        written = _render(args)
    except ReportError as exc:
        print(f"[FAIL] {exc}", flush=True)
        return EXIT_REFUSED
    except OSError as exc:
        print(f"[FAIL] {exc}", flush=True)
        return EXIT_HARNESS_ERROR
    print(f"[OK] wrote {written}", flush=True)
    return EXIT_OK


def approved_contracts(repo_root: Path, table: str) -> dict[str, str]:
    """Contract id -> path, read from the table's committed metric contracts.

    The id is the file stem, which is what a binding map cites. A table with no
    approved contracts yields an empty mapping, and every observation then refuses.
    """
    directory = repo_root / "mappings" / table / "metrics"
    if not directory.is_dir():
        return {}
    return {
        path.stem: str(path.relative_to(repo_root))
        for path in sorted(directory.glob("*.yaml"))
    }


def load_observations(path: Path) -> list[dict[str, object]]:
    from seshat.report.model import ReportError

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ReportError(f"cannot read observations {path}: {exc}") from exc
    entries = payload.get("observations")
    if not isinstance(entries, list) or not entries:
        raise ReportError(f"{path} declares no observations")
    return [_observation(entry, path) for entry in entries]


def _observation(entry: object, path: Path) -> dict[str, object]:
    from seshat.report.model import ReportError

    if not isinstance(entry, dict):
        raise ReportError(f"{path} has a non-mapping observation")
    raw = entry.get("value")
    if raw is None:
        return {**entry, "value": None}
    try:
        # str() first: a YAML float would already have lost precision.
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError) as exc:
        raise ReportError(
            f"observation {entry.get('visual_id')!r} value {raw!r} is not an exact "
            f"decimal: {exc}"
        ) from exc
    return {**entry, "value": value}


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
    from seshat.report.binding import binding_map_path, load_binding_map
    from seshat.report.model import ReportError
    from seshat.report.observe import observe
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
    return observe(cli._make_runner(_dsn(args)), requests, contracts)


def _dsn(args: argparse.Namespace) -> object:
    """The connection, resolved the same way `value-check` resolves it."""
    import os

    from seshat.validate import resolve_dsn

    env = dict(os.environ)
    if args.dsn:
        env = {**env, "DATABASE_URL": args.dsn}
    return resolve_dsn(env)


def _render(args: argparse.Namespace) -> Path:
    from seshat.report.bundle import ApprovedDesign, build_bundle
    from seshat.report.gate import assert_renderable
    from seshat.report.layout import load_layout

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
        observations = load_observations(args.observations)
    bundle = build_bundle(
        table=args.table,
        generated_for=args.language,
        design=ApprovedDesign(
            layout=layout, contracts=approved_contracts(repo_root, args.table)
        ),
        observations=observations,
    )
    return _write(args, bundle, layout)


def _write(args: argparse.Namespace, bundle, layout) -> Path:
    destination = args.output / f"{args.table}{_SUFFIX[args.format]}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "html":
        from seshat.report.html import HtmlReportRenderer

        surface = HtmlReportRenderer().render(bundle, layout, args.language)
        destination.write_text(surface.document, encoding="utf-8")
        return destination
    if args.format == "xlsx":
        from seshat.report.excel import ExcelReportRenderer

        surface = ExcelReportRenderer().render(bundle, layout, args.language)
        destination.write_bytes(surface.workbook_bytes)
        return destination
    from seshat.report.chromium import build_printer
    from seshat.report.pdf import PdfReportRenderer

    surface = PdfReportRenderer(build_printer()).render(bundle, layout, args.language)
    destination.write_bytes(surface.pdf_bytes)
    return destination
