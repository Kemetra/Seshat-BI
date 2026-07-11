"""Shared version and lightweight JSON-contract helpers for ecosystem artifacts."""

from __future__ import annotations

import re
from typing import Any, Mapping

_VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class ContractError(ValueError):
    """An ecosystem artifact cannot be interpreted safely."""


def parse_schema_version(value: object) -> tuple[int, int]:
    if not isinstance(value, str):
        raise ContractError("schema_version must be a MAJOR.MINOR string")
    match = _VERSION_RE.fullmatch(value)
    if match is None:
        raise ContractError("schema_version must be a MAJOR.MINOR string")
    return int(match.group(1)), int(match.group(2))


def require_supported_schema(
    document: Mapping[str, Any], *, supported_major: int = 1
) -> tuple[int, int]:
    version = parse_schema_version(document.get("schema_version"))
    if version[0] != supported_major:
        raise ContractError(
            f"unsupported schema major {version[0]}; expected {supported_major}.x"
        )
    return version


def _is_type(value: object, expected: str) -> bool:
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: (
            isinstance(item, (int, float)) and not isinstance(item, bool)
        ),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return expected in checks and checks[expected](value)


def _validate_type(value: object, schema: Mapping[str, Any], path: str) -> list[str]:
    expected = schema.get("type")
    if expected is None:
        return []
    allowed = expected if isinstance(expected, list) else [expected]
    if any(isinstance(item, str) and _is_type(value, item) for item in allowed):
        return []
    return [f"{path}: expected {expected!r}"]


def _validate_scalar(value: object, schema: Mapping[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value is outside the allowed enumeration")
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            errors.append(f"{path}: string is too short")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            errors.append(f"{path}: string does not match the required pattern")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value is below minimum")
    return errors


def _validate_object(
    value: dict[str, Any], schema: Mapping[str, Any], path: str
) -> list[str]:
    errors = [
        f"{path}: missing required property {name!r}"
        for name in schema.get("required", [])
        if name not in value
    ]
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        errors.extend(
            f"{path}: unexpected property {name!r}"
            for name in value
            if name not in properties
        )
    for name, child_schema in properties.items():
        if name in value and isinstance(child_schema, dict):
            errors.extend(
                validate_json_contract(value[name], child_schema, f"{path}.{name}")
            )
    return errors


def _validate_array(
    value: list[Any], schema: Mapping[str, Any], path: str
) -> list[str]:
    errors: list[str] = []
    if len(value) < int(schema.get("minItems", 0)):
        errors.append(f"{path}: array has too few items")
    if schema.get("uniqueItems") is True:
        normalized = [repr(item) for item in value]
        if len(set(normalized)) != len(normalized):
            errors.append(f"{path}: array items must be unique")
    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        for index, item in enumerate(value):
            errors.extend(validate_json_contract(item, item_schema, f"{path}[{index}]"))
    return errors


def validate_json_contract(
    value: object, schema: Mapping[str, Any], path: str = "$"
) -> list[str]:
    """Validate the JSON-Schema subset used by Seshat ecosystem contracts."""
    errors = _validate_type(value, schema, path)
    if errors:
        return errors
    errors.extend(_validate_scalar(value, schema, path))
    if isinstance(value, dict):
        errors.extend(_validate_object(value, schema, path))
    elif isinstance(value, list):
        errors.extend(_validate_array(value, schema, path))
    return errors
