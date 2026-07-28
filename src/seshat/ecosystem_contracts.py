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


def _validate_const_enum(
    value: object, schema: Mapping[str, Any], path: str
) -> list[str]:
    errors: list[str] = []
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value is outside the allowed enumeration")
    return errors


def _validate_string(value: object, schema: Mapping[str, Any], path: str) -> list[str]:
    if not isinstance(value, str):
        return []
    errors: list[str] = []
    if len(value) < int(schema.get("minLength", 0)):
        errors.append(f"{path}: string is too short")
    pattern = schema.get("pattern")
    if isinstance(pattern, str) and re.search(pattern, value) is None:
        errors.append(f"{path}: string does not match the required pattern")
    return errors


def _validate_number(value: object, schema: Mapping[str, Any], path: str) -> list[str]:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return []
    errors: list[str] = []
    if "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: value is below minimum")
    if "maximum" in schema and value > schema["maximum"]:
        errors.append(f"{path}: value is above maximum")
    return errors


def _validate_scalar(value: object, schema: Mapping[str, Any], path: str) -> list[str]:
    return [
        *_validate_const_enum(value, schema, path),
        *_validate_string(value, schema, path),
        *_validate_number(value, schema, path),
    ]


def _required_errors(
    value: dict[str, Any], schema: Mapping[str, Any], path: str
) -> list[str]:
    return [
        f"{path}: missing required property {name!r}"
        for name in schema.get("required", [])
        if name not in value
    ]


def _additional_errors(
    value: dict[str, Any], schema: Mapping[str, Any], path: str
) -> list[str]:
    if schema.get("additionalProperties") is not False:
        return []
    properties = schema.get("properties", {})
    return [
        f"{path}: unexpected property {name!r}"
        for name in value
        if name not in properties
    ]


def _property_errors(
    value: dict[str, Any],
    properties: Mapping[str, Any],
    path: str,
    root_schema: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    for name, child_schema in properties.items():
        if name in value and isinstance(child_schema, dict):
            errors.extend(
                validate_json_contract(
                    value[name], child_schema, f"{path}.{name}", root_schema
                )
            )
    return errors


def _validate_object(
    value: dict[str, Any],
    schema: Mapping[str, Any],
    path: str,
    root_schema: Mapping[str, Any],
) -> list[str]:
    return [
        *_required_errors(value, schema, path),
        *_additional_errors(value, schema, path),
        *_property_errors(value, schema.get("properties", {}), path, root_schema),
    ]


def _unique_errors(value: list[Any], schema: Mapping[str, Any], path: str) -> list[str]:
    if schema.get("uniqueItems") is not True:
        return []
    normalized = [repr(item) for item in value]
    if len(set(normalized)) != len(normalized):
        return [f"{path}: array items must be unique"]
    return []


def _item_errors(
    value: list[Any],
    schema: Mapping[str, Any],
    path: str,
    root_schema: Mapping[str, Any],
) -> list[str]:
    item_schema = schema.get("items")
    if not isinstance(item_schema, dict):
        return []
    return [
        error
        for index, item in enumerate(value)
        for error in validate_json_contract(
            item, item_schema, f"{path}[{index}]", root_schema
        )
    ]


def _validate_array(
    value: list[Any],
    schema: Mapping[str, Any],
    path: str,
    root_schema: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if len(value) < int(schema.get("minItems", 0)):
        errors.append(f"{path}: array has too few items")
    if "maxItems" in schema and len(value) > schema["maxItems"]:
        errors.append(f"{path}: array has too many items")
    errors.extend(_unique_errors(value, schema, path))
    errors.extend(_item_errors(value, schema, path, root_schema))
    return errors


def _resolve_local_ref(
    schema: Mapping[str, Any], root_schema: Mapping[str, Any]
) -> Mapping[str, Any]:
    reference = schema.get("$ref")
    if reference is None:
        return schema
    if not isinstance(reference, str) or not reference.startswith("#/$defs/"):
        return {"type": "__invalid_local_reference__"}
    name = reference.removeprefix("#/$defs/")
    if not name or "/" in name:
        return {"type": "__invalid_local_reference__"}
    definitions = root_schema.get("$defs")
    definition = definitions.get(name) if isinstance(definitions, Mapping) else None
    if not isinstance(definition, Mapping):
        return {"type": "__invalid_local_reference__"}
    return definition


def _validate_one_of(
    value: object,
    schema: Mapping[str, Any],
    path: str,
    root_schema: Mapping[str, Any],
) -> list[str]:
    branches = schema.get("oneOf")
    if branches is None:
        return []
    if not isinstance(branches, list):
        return [f"{path}: oneOf must contain a list of schemas"]
    valid_count = sum(
        isinstance(branch, Mapping)
        and not validate_json_contract(value, branch, path, root_schema)
        for branch in branches
    )
    if valid_count == 1:
        return []
    return [f"{path}: value must validate against exactly one oneOf schema"]


def validate_json_contract(
    value: object,
    schema: Mapping[str, Any],
    path: str = "$",
    root_schema: Mapping[str, Any] | None = None,
) -> list[str]:
    """Validate the JSON-Schema subset used by Seshat ecosystem contracts."""
    root = schema if root_schema is None else root_schema
    resolved = _resolve_local_ref(schema, root)
    branch_errors = _validate_one_of(value, resolved, path, root)
    if branch_errors:
        return branch_errors
    errors = _validate_type(value, resolved, path)
    if errors:
        return errors
    errors.extend(_validate_scalar(value, resolved, path))
    if isinstance(value, dict):
        errors.extend(_validate_object(value, resolved, path, root))
    elif isinstance(value, list):
        errors.extend(_validate_array(value, resolved, path, root))
    return errors
