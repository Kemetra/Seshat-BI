"""The shared JSON-contract validator refuses keywords it does not implement.

It implements a SUBSET of JSON Schema. A keyword outside that subset used to be
ignored, so tightening a schema (say, adding `maxLength` or `anyOf`) would keep
passing documents the schema author meant to reject. It now fails loudly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.ecosystem_contracts import ContractError, validate_json_contract

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]

# Every schema that is validated through `validate_json_contract`.
_SHIPPED = (
    "schemas/seshat-extension-pack.schema.json",
    "schemas/seshat-pack-registry.schema.json",
    "schemas/statistical-analysis-spec.schema.json",
    "schemas/statistical-analysis-evidence.schema.json",
)


@pytest.mark.parametrize("relative", _SHIPPED)
def test_every_shipped_contract_schema_uses_only_supported_keywords(
    relative: str,
) -> None:
    schema = json.loads((_REPO / relative).read_text(encoding="utf-8"))
    validate_json_contract({}, schema)  # must not raise ContractError


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "string", "maxLength": 3},
        {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        {"type": "object", "properties": {"a": {"type": "string", "format": "x"}}},
        {"$defs": {"d": {"not": {"type": "null"}}}, "$ref": "#/$defs/d"},
        {"type": "array", "items": {"type": "object", "propertyNames": {}}},
        {"type": "object", "patternProperties": {"^x": {}}},
    ],
)
def test_an_unsupported_keyword_is_refused_not_ignored(schema: dict) -> None:
    with pytest.raises(ContractError, match="unsupported"):
        validate_json_contract("value", schema)


def test_annotation_keywords_are_accepted() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "x",
        "title": "t",
        "description": "d",
        "$comment": "c",
        "type": "string",
        "default": "a",
        "examples": ["a"],
    }
    assert validate_json_contract("a", schema) == []


def test_a_property_named_like_a_keyword_is_not_mistaken_for_one() -> None:
    schema = {"type": "object", "properties": {"maxLength": {"type": "integer"}}}
    assert validate_json_contract({"maxLength": 3}, schema) == []
