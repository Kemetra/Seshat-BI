"""Least-privilege environment forwarding for Dagster child processes."""

from __future__ import annotations

from collections.abc import Mapping

_EXACT_KEYS = frozenset(
    {
        "COMSPEC",
        "DAGSTER_HOME",
        "DATABASE_URL",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PATHEXT",
        "PYTHONIOENCODING",
        "PYTHONPATH",
        "PYTHONUTF8",
        "REQUESTS_CA_BUNDLE",
        "SESHAT_RAW_LANDING_DIR",
        "SSL_CERT_FILE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
        "WINDIR",
    }
)
_PREFIXES = ("ANALYTICS_DB_", "SESHAT_DBT_")


def allowed_child_environment(source: Mapping[str, str]) -> dict[str, str]:
    """Return only OS runtime and governed Seshat connection variables."""
    return {
        key: value
        for key, value in source.items()
        if key.upper() in _EXACT_KEYS or key.upper().startswith(_PREFIXES)
    }
