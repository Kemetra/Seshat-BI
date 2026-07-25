"""Validate reviewed knowledge-layer task routes against canonical resources."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import yaml

_RESOURCE_RE = re.compile(r"`([^`]+\.(?:md|json|yaml|yml))`")
_MARKDOWN_MARK_RE = re.compile(r"[*_`]")


@dataclass(frozen=True)
class RouteFinding:
    """One deterministic route-contract finding."""

    code: str
    layer: str
    task: str
    resource: str
    message: str


@dataclass(frozen=True)
class _RouteRow:
    task: str
    resources: tuple[str, ...]
    terminal: str


@dataclass(frozen=True)
class _Scenario:
    layer: str
    task: str
    resources: tuple[str, ...]
    terminal: str


@dataclass(frozen=True)
class _FindingContext:
    layer: str
    task: str


@dataclass(frozen=True)
class _ValidationContext:
    root: Path
    layer_root: Path
    finding: _FindingContext


def _clean_markdown(value: str) -> str:
    return " ".join(_MARKDOWN_MARK_RE.sub("", value).split())


def _is_separator(cells: Sequence[str]) -> bool:
    return all(cell and set(cell) <= {"-", ":"} for cell in cells)


def _route_rows(index_path: Path) -> list[_RouteRow]:
    rows: list[_RouteRow] = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 3 or _is_separator(cells[:3]):
            continue
        task = _clean_markdown(cells[0])
        if task.casefold() in {
            "task",
            "i need to...",
            "if the agent needs to...",
            "symptom",
            "symptom the agent observes",
        }:
            continue
        rows.append(
            _RouteRow(
                task=task,
                resources=tuple(_RESOURCE_RE.findall(cells[1])),
                terminal=_clean_markdown(cells[-1]),
            )
        )
    return rows


def _finding(
    context: _FindingContext,
    code: str,
    message: str,
    resource: str = "",
) -> RouteFinding:
    return RouteFinding(
        code=code,
        layer=context.layer,
        task=context.task,
        resource=resource,
        message=message,
    )


def _require_scenario_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("scenario document must declare schema_version: 1")
    return document


def _require_scenario_items(document: dict[str, Any]) -> list[dict[str, Any]]:
    scenarios = document.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("scenario document must contain a scenarios list")
    if not all(isinstance(item, dict) for item in scenarios):
        raise ValueError("every route scenario must be an object")
    return scenarios


def _scenario_list(path: Path) -> list[dict[str, Any]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _require_scenario_items(_require_scenario_document(document))


def _scenario(raw: dict[str, Any]) -> _Scenario:
    return _Scenario(
        layer=str(raw["layer"]).strip(),
        task=str(raw["task_contains"]).strip(),
        resources=tuple(str(item) for item in raw["expect_resources"]),
        terminal=str(raw["terminal_contains"]).strip(),
    )


def _cached_rows(
    layer: str,
    index_path: Path,
    row_cache: dict[str, list[_RouteRow]],
) -> list[_RouteRow]:
    rows = row_cache.get(layer)
    if rows is None:
        rows = _route_rows(index_path)
        row_cache[layer] = rows
    return rows


def _resolve_route(
    layer_root: Path,
    context: _FindingContext,
    row_cache: dict[str, list[_RouteRow]],
) -> tuple[_RouteRow | None, RouteFinding | None]:
    index_path = layer_root / "INDEX.md"
    if not index_path.is_file():
        return None, _finding(
            context,
            "missing_index",
            f"missing knowledge router: {index_path}",
            "INDEX.md",
        )

    rows = _cached_rows(context.layer, index_path, row_cache)
    matches = [row for row in rows if context.task.casefold() in row.task.casefold()]
    if not matches:
        return None, _finding(
            context,
            "missing_route",
            f"no task row contains {context.task!r}",
        )
    if len(matches) > 1:
        return None, _finding(
            context,
            "ambiguous_route",
            f"{len(matches)} task rows contain {context.task!r}",
        )
    return matches[0], None


def _validate_resource(
    context: _ValidationContext,
    resource: str,
) -> RouteFinding | None:
    resource_path = (context.layer_root / resource).resolve()
    if not resource_path.is_relative_to(context.root):
        return _finding(
            context.finding,
            "unsafe_resource",
            "routed resource escapes the repository",
            resource,
        )
    if not resource_path.is_file():
        return _finding(
            context.finding,
            "missing_resource",
            f"routed resource does not exist: {resource_path}",
            resource,
        )
    return None


def _resource_findings(
    context: _ValidationContext,
    route: _RouteRow,
    resources: tuple[str, ...],
) -> list[RouteFinding]:
    findings: list[RouteFinding] = []
    for resource in resources:
        if resource not in route.resources:
            findings.append(
                _finding(
                    context.finding,
                    "missing_resource_reference",
                    f"matched route does not name {resource!r}",
                    resource,
                )
            )
            continue
        finding = _validate_resource(context, resource)
        if finding is not None:
            findings.append(finding)
    return findings


def _terminal_finding(
    context: _FindingContext,
    route: _RouteRow,
    terminal: str,
) -> RouteFinding | None:
    if terminal.casefold() in route.terminal.casefold():
        return None
    return _finding(
        context,
        "terminal_mismatch",
        f"terminal cell does not contain {terminal!r}: {route.terminal!r}",
    )


def validate_repository(
    repo_root: Path,
    scenarios: list[dict[str, Any]],
) -> list[RouteFinding]:
    """Validate scenario-selected INDEX routes and their terminal artifacts."""

    resolved_root = repo_root.resolve()
    findings: list[RouteFinding] = []
    row_cache: dict[str, list[_RouteRow]] = {}

    for raw_scenario in scenarios:
        scenario = _scenario(raw_scenario)
        finding_context = _FindingContext(scenario.layer, scenario.task)
        layer_root = resolved_root / "skills" / scenario.layer
        context = _ValidationContext(resolved_root, layer_root, finding_context)
        route, route_finding = _resolve_route(layer_root, finding_context, row_cache)
        if route_finding is not None:
            findings.append(route_finding)
            continue

        assert route is not None
        findings.extend(_resource_findings(context, route, scenario.resources))
        terminal_finding = _terminal_finding(
            finding_context,
            route,
            scenario.terminal,
        )
        if terminal_finding is not None:
            findings.append(terminal_finding)

    return findings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate reviewed Seshat knowledge-layer routes."
    )
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def _render_text(findings: Sequence[RouteFinding]) -> str:
    if not findings:
        return "Knowledge route contracts: valid"
    return "\n".join(
        f"{item.code}: {item.layer}: {item.task}: "
        f"{item.resource or '-'}: {item.message}"
        for item in findings
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        scenarios = _scenario_list(args.scenarios)
        findings = validate_repository(args.repo, scenarios)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        findings = [
            _finding(
                _FindingContext("", ""),
                "invalid_input",
                str(exc),
            )
        ]

    if args.format == "json":
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(_render_text(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
