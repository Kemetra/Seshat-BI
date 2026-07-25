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
    *,
    code: str,
    layer: str,
    task: str,
    resource: str = "",
    message: str,
) -> RouteFinding:
    return RouteFinding(
        code=code,
        layer=layer,
        task=task,
        resource=resource,
        message=message,
    )


def _scenario_list(path: Path) -> list[dict[str, Any]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("scenario document must declare schema_version: 1")
    scenarios = document.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("scenario document must contain a scenarios list")
    if not all(isinstance(item, dict) for item in scenarios):
        raise ValueError("every route scenario must be an object")
    return scenarios


def validate_repository(
    repo_root: Path,
    scenarios: list[dict[str, Any]],
) -> list[RouteFinding]:
    """Validate scenario-selected INDEX routes and their terminal artifacts."""

    resolved_root = repo_root.resolve()
    findings: list[RouteFinding] = []
    row_cache: dict[str, list[_RouteRow]] = {}

    for scenario in scenarios:
        layer = str(scenario["layer"]).strip()
        task = str(scenario["task_contains"]).strip()
        expected_resources = scenario["expect_resources"]
        terminal = str(scenario["terminal_contains"]).strip()
        layer_root = resolved_root / "skills" / layer
        index_path = layer_root / "INDEX.md"
        if not index_path.is_file():
            findings.append(
                _finding(
                    code="missing_index",
                    layer=layer,
                    task=task,
                    resource="INDEX.md",
                    message=f"missing knowledge router: {index_path}",
                )
            )
            continue

        rows = row_cache.setdefault(layer, _route_rows(index_path))
        matches = [row for row in rows if task.casefold() in row.task.casefold()]
        if not matches:
            findings.append(
                _finding(
                    code="missing_route",
                    layer=layer,
                    task=task,
                    message=f"no task row contains {task!r}",
                )
            )
            continue
        if len(matches) > 1:
            findings.append(
                _finding(
                    code="ambiguous_route",
                    layer=layer,
                    task=task,
                    message=f"{len(matches)} task rows contain {task!r}",
                )
            )
            continue

        route = matches[0]
        for raw_resource in expected_resources:
            resource = str(raw_resource)
            if resource not in route.resources:
                findings.append(
                    _finding(
                        code="missing_resource_reference",
                        layer=layer,
                        task=task,
                        resource=resource,
                        message=f"matched route does not name {resource!r}",
                    )
                )
                continue

            resource_path = (layer_root / resource).resolve()
            if not resource_path.is_relative_to(resolved_root):
                findings.append(
                    _finding(
                        code="unsafe_resource",
                        layer=layer,
                        task=task,
                        resource=resource,
                        message="routed resource escapes the repository",
                    )
                )
            elif not resource_path.is_file():
                findings.append(
                    _finding(
                        code="missing_resource",
                        layer=layer,
                        task=task,
                        resource=resource,
                        message=f"routed resource does not exist: {resource_path}",
                    )
                )

        if terminal.casefold() not in route.terminal.casefold():
            findings.append(
                _finding(
                    code="terminal_mismatch",
                    layer=layer,
                    task=task,
                    message=(
                        f"terminal cell does not contain {terminal!r}: "
                        f"{route.terminal!r}"
                    ),
                )
            )

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
                code="invalid_input",
                layer="",
                task="",
                message=str(exc),
            )
        ]

    if args.format == "json":
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(_render_text(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
