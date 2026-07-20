"""Child-only environment loading and recursive dbt boundary redaction."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

from seshat.redaction_core import replace_fragments, uri_components

DBT_ENVIRONMENT_KEYS = (
    "SESHAT_DBT_HOST",
    "SESHAT_DBT_PORT",
    "SESHAT_DBT_USER",
    "SESHAT_DBT_PASSWORD",
    "SESHAT_DBT_DBNAME",
    "SESHAT_DBT_SCHEMA",
    "SESHAT_DBT_SSLMODE",
)

# Not every governed dbt env var is a secret. Three carry non-secret connection
# METADATA whose values are short, public, and dictionary-like, so redacting them
# corrupts the tool's own governed evidence by rewriting innocent substrings:
#   - SESHAT_DBT_SCHEMA  (e.g. "seshat_dbt_shadow"): a non-production target
#     namespace with a public default; appears verbatim and REQUIRED in evidence
#     (target.schemas.<layer> = <schema>_<layer>, pattern ^[a-z_][a-z0-9_]*$).
#     Redacting it turned "seshat_dbt_shadow_silver" into "<redacted>_silver".
#   - SESHAT_DBT_SSLMODE (e.g. "require"): an English word; redacting "require"
#     mangled the governed const "none; named-human approval required".
#   - SESHAT_DBT_PORT    (e.g. "25060"): a bare number that can collide with any
#     digits in the payload.
# These are still loaded into the child env (load_child_environment) but excluded
# from the redaction secret set. Genuine credentials -- host, user, password,
# dbname -- stay redacted.
_NON_SECRET_ENVIRONMENT_KEYS = frozenset(
    {"SESHAT_DBT_SCHEMA", "SESHAT_DBT_SSLMODE", "SESHAT_DBT_PORT"}
)
_SECRET_ENVIRONMENT_KEYS = tuple(
    key for key in DBT_ENVIRONMENT_KEYS if key not in _NON_SECRET_ENVIRONMENT_KEYS
)

_RUNTIME_ENVIRONMENT_KEYS = (
    "COMSPEC",
    "LANG",
    "LC_ALL",
    "PATH",
    "PATHEXT",
    "PYTHONIOENCODING",
    "PYTHONUTF8",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "WINDIR",
)

_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class EnvironmentConfigError(ValueError):
    """A malformed local `.env` file that cannot be loaded safely."""


def _dotenv_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise EnvironmentConfigError(".env could not be read as UTF-8") from exc


def _unquote_dotenv_value(value: str, number: int) -> str:
    if not value.startswith(("'", '"')):
        return _unquoted_dotenv_value(value, number)
    quote = value[0]
    _validate_closing_quote(value, quote, number)
    return value[1:-1]


def _unquoted_dotenv_value(value: str, number: int) -> str:
    if value.endswith(("'", '"')):
        raise EnvironmentConfigError(
            f".env line {number} has a mismatched quoted value"
        )
    return value


def _validate_closing_quote(value: str, quote: str, number: int) -> None:
    if len(value) < 2 or not value.endswith(quote):
        raise EnvironmentConfigError(f".env line {number} has an unclosed quoted value")


def _split_dotenv_assignment(line: str, number: int) -> tuple[str, str]:
    if "=" not in line:
        raise EnvironmentConfigError(f".env line {number} is not KEY=VALUE")
    key, value = (part.strip() for part in line.split("=", 1))
    return key, value


def _validate_dotenv_key(key: str, number: int) -> None:
    if not _ENV_KEY.fullmatch(key):
        raise EnvironmentConfigError(f".env line {number} has an invalid key")


def _dotenv_entry(number: int, source: str) -> tuple[str, str] | None:
    line = source.strip()
    if not line or line.startswith("#"):
        return None
    key, value = _split_dotenv_assignment(line, number)
    _validate_dotenv_key(key, number)
    return key, _unquote_dotenv_value(value, number)


def dotenv_values(path: Path) -> dict[str, str]:
    """Parse a `.env` file into a key->value dict (dependency-free).

    Public because live-connection resolution (issue #340) reuses this exact
    governed parser rather than adding python-dotenv. Raises
    ``EnvironmentConfigError`` on a malformed file or a duplicate key.
    """
    values: dict[str, str] = {}
    for number, source in enumerate(_dotenv_lines(path), start=1):
        entry = _dotenv_entry(number, source)
        if entry is None:
            continue
        key, value = entry
        if key in values:
            raise EnvironmentConfigError(f".env contains duplicate key {key}")
        values[key] = value
    return values


# Backwards-compatible private alias: existing callers imported the underscore
# name; keep it pointing at the now-public function so nothing breaks.
_dotenv_values = dotenv_values


def load_child_environment(repo_root: Path) -> dict[str, str]:
    """Return only runtime and governed dbt values without mutating the process."""

    source = dict(os.environ)
    path = repo_root / ".env"
    if path.is_file():
        source.update(_dotenv_values(path))
    allowed = (*_RUNTIME_ENVIRONMENT_KEYS, *DBT_ENVIRONMENT_KEYS)
    return {key: source[key] for key in allowed if key in source}


def secret_values(environment: Mapping[str, str]) -> tuple[str, ...]:
    """Return non-empty governed dbt CREDENTIAL values, longest first.

    Excludes the shadow schema name (SESHAT_DBT_SCHEMA): it is a non-secret target
    namespace that must survive verbatim in governed evidence -- see
    _SECRET_ENVIRONMENT_KEYS."""

    values = {environment.get(key, "") for key in _SECRET_ENVIRONMENT_KEYS}
    return tuple(sorted((value for value in values if value), key=len, reverse=True))


def _replace_path(text: str, path: Path, token: str) -> str:
    raw = str(path.resolve(strict=False)).rstrip("\\/")
    variants = {raw, raw.replace("\\", "/"), raw.replace("/", "\\")}
    for variant in sorted(variants, key=len, reverse=True):
        text = text.replace(variant, token)
    pattern = re.compile(rf"{re.escape(token)}[^\s\"']*")
    return pattern.sub(lambda match: match.group(0).replace("\\", "/"), text)


def _sanitize_text(text: str, secrets: tuple[str, ...], repo_root: Path) -> str:
    ordered = tuple(
        sorted({value for value in secrets if value}, key=len, reverse=True)
    )
    text = replace_fragments(text, ordered, "<redacted>")
    text = replace_fragments(text, uri_components(ordered), "<redacted>")
    text = _replace_path(text, repo_root, "<repo>")
    return _replace_path(text, Path.home(), "<home>")


def _sanitize_mapping(
    value: Mapping[object, object], secrets: tuple[str, ...], repo_root: Path
) -> dict[object, object]:
    return {
        sanitize(key, secrets, repo_root): sanitize(item, secrets, repo_root)
        for key, item in value.items()
    }


def _sanitize_tuple(
    value: tuple[object, ...], secrets: tuple[str, ...], repo_root: Path
) -> tuple[object, ...]:
    return tuple(sanitize(item, secrets, repo_root) for item in value)


def _sanitize_list(
    value: list[object], secrets: tuple[str, ...], repo_root: Path
) -> list[object]:
    return [sanitize(item, secrets, repo_root) for item in value]


def sanitize(value: object, secrets: tuple[str, ...], repo_root: Path) -> object:
    """Recursively remove governed secrets and absolute machine paths."""

    if isinstance(value, str):
        return _sanitize_text(value, secrets, repo_root)
    return _sanitize_collection(value, secrets, repo_root)


def _sanitize_collection(
    value: object, secrets: tuple[str, ...], repo_root: Path
) -> object:
    if isinstance(value, Mapping):
        return _sanitize_mapping(value, secrets, repo_root)
    if isinstance(value, tuple):
        return _sanitize_tuple(value, secrets, repo_root)
    if isinstance(value, list):
        return _sanitize_list(value, secrets, repo_root)
    return value
