"""Generate `studio-ui/src/api/types.ts` from the Studio API contract.

`studio-api.yaml` is the single authority for the payload shapes Studio serves. Types
hand-written in TypeScript would be free to drift from it -- exactly the failure this
feature already hit once, where the contract declared a readiness status that existed
nowhere in the repository.

Generating them instead makes drift mechanical:
`tests/unit/test_studio_generated_types.py` regenerates and compares, so an
unsynchronised edit is a test failure rather than a runtime surprise the browser
discovers.

Deliberately narrow. This emits string-union aliases and interfaces for the component
schemas Studio actually serves, not a general OpenAPI-to-TypeScript compiler: a
hand-rolled subset is auditable, has no external dependency, and covers a contract we
control. Run it via `python scripts/generate_studio_types.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT = _REPO_ROOT / "specs/139-seshat-studio-foundation/contracts/studio-api.yaml"
_TARGET = _REPO_ROOT / "studio-ui/src/api/types.ts"

#: Emitted in dependency-free order so the file reads top-down.
_SCHEMAS = (
    "ReadinessStage",
    "EvidenceRef",
    "BlockingReason",
    "ActionSummary",
    "StageState",
    "TableJourney",
    "InputDefect",
    "WorkspaceIdentity",
    "AgentHealth",
    "WorkspaceSnapshot",
    "BootstrapState",
    "PreparedDecisionSummary",
    "Problem",
)

_HEADER = """/**
 * GENERATED FILE -- do not edit by hand.
 *
 * Source: specs/139-seshat-studio-foundation/contracts/studio-api.yaml
 * Regenerate: python scripts/generate_studio_types.py
 *
 * `studio-api.yaml` is the authority for every payload Studio serves. These types are
 * derived from it so the browser cannot drift from the contract; a stale copy is a
 * failing test, not a runtime surprise.
 */
"""


def _load_schemas() -> dict[str, Any]:
    import yaml

    document = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return document["components"]["schemas"]


def _scalar_type(node: dict[str, Any]) -> str:
    """Render one non-object schema node as a TypeScript type expression."""
    if "$ref" in node:
        return node["$ref"].rsplit("/", 1)[-1]
    if "const" in node:
        value = node["const"]
        return "false" if value is False else f'"{value}"'
    if "enum" in node:
        return " | ".join(f'"{value}"' for value in node["enum"])
    if "oneOf" in node:
        return " | ".join(_scalar_type(option) for option in node["oneOf"])

    declared = node.get("type")
    if isinstance(declared, list):
        return " | ".join(_primitive(name) for name in declared)
    if declared == "array":
        return f"{_scalar_type(node.get('items', {}))}[]"
    if declared == "object" and "properties" in node:
        return _inline_object(node)
    return _primitive(declared)


def _primitive(name: str | None) -> str:
    return {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "null": "null",
        "object": "Record<string, unknown>",
    }.get(name or "", "unknown")


def _inline_object(node: dict[str, Any]) -> str:
    required = set(node.get("required", ()))
    fields = [
        f"    {name}{'' if name in required else '?'}: {_scalar_type(schema)};"
        for name, schema in node["properties"].items()
    ]
    return "{\n" + "\n".join(fields) + "\n  }"


def _render(name: str, schema: dict[str, Any]) -> str:
    if "properties" not in schema:
        return f"export type {name} = {_scalar_type(schema)};\n"

    required = set(schema.get("required", ()))
    lines = [f"export interface {name} {{"]
    for field, node in schema["properties"].items():
        optional = "" if field in required else "?"
        lines.append(f"  {field}{optional}: {_scalar_type(node)};")
    lines.append("}\n")
    return "\n".join(lines)


def render_types() -> str:
    """The full generated module, as text."""
    schemas = _load_schemas()
    blocks = [_render(name, schemas[name]) for name in _SCHEMAS if name in schemas]
    return _HEADER + "\n" + "\n".join(blocks)


def main() -> int:
    generated = render_types()
    _TARGET.parent.mkdir(parents=True, exist_ok=True)
    previous = _TARGET.read_text(encoding="utf-8") if _TARGET.exists() else None
    if previous == generated:
        print(f"{_TARGET.relative_to(_REPO_ROOT).as_posix()} is already current")
        return 0
    _TARGET.write_text(generated, encoding="utf-8")
    print(f"wrote {_TARGET.relative_to(_REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
