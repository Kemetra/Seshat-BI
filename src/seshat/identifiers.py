"""Shared SQL identifier validation and quoting helpers.

Identifiers cannot be query parameters in PostgreSQL, so every dynamic identifier
must be validated before it is interpolated into SQL text. This module permits
only the conservative unquoted identifier subset used by the repo:

    [A-Za-z_][A-Za-z0-9_]*

Qualified names are one or two dot-separated safe identifiers. Quoting happens
after validation, so no escape path exists for quotes, comments, spaces, or SQL
statement separators.
"""

from __future__ import annotations

import re
from collections.abc import Collection

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(value: object, *, context: str = "identifier") -> str:
    """Return ``value`` as a safe single SQL identifier, or raise ``ValueError``."""
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"unsafe SQL identifier in {context}: {value!r}")
    return value


def validate_qualified_identifier(
    value: object,
    *,
    context: str = "identifier",
    min_parts: int = 1,
    max_parts: int = 2,
    allowed_schemas: Collection[str] | None = None,
) -> str:
    """Return a safe one/two-part identifier, optionally restricted by schema."""
    if not isinstance(value, str):
        raise ValueError(f"unsafe SQL identifier in {context}: {value!r}")

    parts = value.split(".")
    if not (min_parts <= len(parts) <= max_parts):
        raise ValueError(f"unsafe SQL identifier in {context}: {value!r}")
    for part in parts:
        validate_identifier(part, context=context)

    if allowed_schemas is not None:
        if len(parts) < 2 or parts[0] not in allowed_schemas:
            expected = ", ".join(sorted(allowed_schemas))
            raise ValueError(
                f"unsafe SQL identifier in {context}: {value!r} "
                f"(expected schema: {expected})"
            )

    return ".".join(parts)


def quote_identifier(value: object, *, context: str = "identifier") -> str:
    """Return a validated single SQL identifier quoted for PostgreSQL."""
    return f'"{validate_identifier(value, context=context)}"'


def quote_qualified_identifier(
    value: object,
    *,
    context: str = "identifier",
    min_parts: int = 1,
    max_parts: int = 2,
    allowed_schemas: Collection[str] | None = None,
) -> str:
    """Return a validated qualified SQL identifier quoted part-by-part."""
    validated = validate_qualified_identifier(
        value,
        context=context,
        min_parts=min_parts,
        max_parts=max_parts,
        allowed_schemas=allowed_schemas,
    )
    return ".".join(f'"{part}"' for part in validated.split("."))


def validate_bronze_table(value: object, *, context: str = "table") -> str:
    """Require the CSV loader target shape: ``bronze.<identifier>``."""
    return validate_qualified_identifier(
        value,
        context=context,
        min_parts=2,
        max_parts=2,
        allowed_schemas={"bronze"},
    )


def quote_bronze_table(value: object, *, context: str = "table") -> str:
    """Quote a validated ``bronze.<identifier>`` table name."""
    validate_bronze_table(value, context=context)
    return quote_qualified_identifier(
        value,
        context=context,
        min_parts=2,
        max_parts=2,
        allowed_schemas={"bronze"},
    )
