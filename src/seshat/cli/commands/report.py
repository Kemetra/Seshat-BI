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
        help="figure observations (increment A); increment B reads gold instead",
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


def _render(args: argparse.Namespace) -> Path:
    from seshat.report.bundle import build_bundle
    from seshat.report.gate import assert_renderable
    from seshat.report.layout import load_layout
    from seshat.report.model import ReportError

    repo_root = args.repo_root.resolve()
    assert_renderable(repo_root, args.table)

    layout_path = (
        args.layout
        or repo_root / "mappings" / args.table / "design" / "report-layout.yaml"
    )
    layout = load_layout(layout_path)

    if args.observations is None:
        raise ReportError(
            "no figure source: pass --observations <file>. Reading gold directly is "
            "increment B and is not built yet, so there is nothing to render from."
        )
    observations = load_observations(args.observations)
    bundle = build_bundle(
        table=args.table,
        generated_for=args.language,
        layout=layout,
        contracts=approved_contracts(repo_root, args.table),
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
