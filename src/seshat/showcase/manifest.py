"""Four-category disclosure manifest + portability normalization (US3).

The manifest is a transparency ledger, not a new evidence schema: every
category maps to vocabulary the reused projection already produces (evidence
``state``, Passport ``unavailable``, an input-defect entry). "Redacted" names
only the composer's OWN by-design portability normalizations (an absolute
path reduced to repo-relative, a private/internal URL stripped) applied
BEFORE the disclosure scan -- never the suppression of a disclosure finding
(FR-016..019; pipeline order: compose -> normalize/redact -> scan full body).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Any POSIX/Windows absolute path is disclosure-sensitive, not just a fixed
# prefix whitelist -- a workspace mounted at an unlisted root (e.g.
# "/workspace/...") must still be reduced to repo-relative form. These are
# NOT start-anchored: a path can appear anywhere in a larger string (a
# blocking reason like "see /workspace/Seshat_BI/... for details"), so both
# normalization and the residual-path check must find an embedded occurrence,
# not only a value that IS a path in its entirety. The lookbehind excludes a
# preceding ":", "/", "<", a quote, or word character so a URL's scheme
# ("https://"), an interior path segment ("http://host/dash"), an HTML/SVG
# closing tag ("</svg>"), or a self-closing tag ("...\"/>") -- all present in
# the rendered badge markup -- is never mistaken for a filesystem path (a URL
# is `_normalize_private_url`'s job instead).
_WINDOWS_ABS_RE = re.compile(r"(?<![:\w<\"'])[A-Za-z]:[\\/][^\s\"'<>]*")
_UNIX_ABS_RE = re.compile(r"(?<![:\w</\"'])/[^\s\"'<>]*")
_PRIVATE_URL_RE = re.compile(
    r"https?://(?:localhost|127\.0\.0\.1"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|[\w-]+(?:\.[\w-]+)*\.(?:internal|local))"
    r"(?::\d+)?(?:/[^\s\"'<>]*)?",
    re.IGNORECASE,
)


def _entry(
    category: str, locator: str, reason: str, original_class: str | None = None
) -> dict[str, Any]:
    return {
        "category": category,
        "locator": locator,
        "reason": reason,
        "original_class": original_class,
    }


def _repo_relative_or_none(root: Path, token: str) -> str | None:
    try:
        resolved = Path(token).resolve()
    except (OSError, ValueError):
        return None
    if not resolved.is_relative_to(root):
        # Not a workspace path: left as-is. A residual absolute path that
        # survives normalization is a blocking disclosure finding (FR-010),
        # never silently dropped or invented into a fake relative form.
        return None
    return resolved.relative_to(root).as_posix()


def _normalize_absolute_path(root: Path, value: str) -> tuple[str, bool]:
    changed = False

    def _replace(match: re.Match[str]) -> str:
        nonlocal changed
        token = match.group(0)
        relative = _repo_relative_or_none(root, token)
        if relative is None:
            return token
        changed = True
        return relative

    normalized = _WINDOWS_ABS_RE.sub(_replace, value)
    normalized = _UNIX_ABS_RE.sub(_replace, normalized)
    return normalized, changed


def _normalize_private_url(value: str) -> tuple[str, bool]:
    stripped, count = _PRIVATE_URL_RE.subn("[private URL removed]", value)
    return stripped, count > 0


def _normalize_string(
    root: Path, value: str, locator: str, redactions: list[dict[str, Any]]
) -> str:
    normalized, changed_path = _normalize_absolute_path(root, value)
    if changed_path:
        redactions.append(
            _entry(
                "redacted",
                locator,
                "absolute path reduced to repo-relative",
                "absolute_path",
            )
        )
    normalized, changed_url = _normalize_private_url(normalized)
    if changed_url:
        redactions.append(
            _entry("redacted", locator, "private/internal URL stripped", "private_url")
        )
    return normalized


def normalize_portability(
    root: Path, document: Any, *, locator: str = "$"
) -> tuple[Any, list[dict[str, Any]]]:
    """Reduce machine-local absolute paths to repo-relative form and strip
    private/internal URLs, applied BEFORE the disclosure scan (FR-019).
    Returns the normalized document plus the list of manifest ``redacted``
    entries recording every normalization -- never a silent rewrite.
    """
    redactions: list[dict[str, Any]] = []

    def _walk(value: Any, loc: str) -> Any:
        if isinstance(value, str):
            return _normalize_string(root, value, loc, redactions)
        if isinstance(value, dict):
            return {key: _walk(child, f"{loc}.{key}") for key, child in value.items()}
        if isinstance(value, list):
            return [_walk(child, f"{loc}[{i}]") for i, child in enumerate(value)]
        return value

    return _walk(document, locator), redactions


def _evidence_entry(
    table_id: str, stage: str, item: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    locator = f"{table_id}#{stage}:{item['reference']}"
    state = item["state"]
    if state == "available":
        return "included", _entry("included", locator, "evidence available")
    if state == "deferred":
        return "unavailable", _entry("unavailable", locator, "deferred live check")
    return "omitted", _entry("omitted", locator, "evidence missing")


def _table_entries(table: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    table_id = table.get("table_id", "?")
    if "input_defect" in table:
        locator = table.get("source_path", table_id)
        reason = f"input defect: {table['input_defect']}"
        return [("omitted", _entry("omitted", locator, reason))]
    return [
        _evidence_entry(table_id, stage, item)
        for stage, block in table["stages"].items()
        for item in block["evidence"]
    ]


def _lineage_entries(lineage: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any]]] = []
    for node in lineage.get("nodes", []):
        locator = node["node_id"]
        if node.get("kind") == "input_defect":
            reason = "unreadable metric contract"
            entries.append(("omitted", _entry("omitted", locator, reason)))
        else:
            reason = "metric lineage available"
            entries.append(("included", _entry("included", locator, reason)))
    return entries


def _residual_finding_for_string(value: str, locator: str) -> list[dict[str, str]]:
    if not (_WINDOWS_ABS_RE.search(value) or _UNIX_ABS_RE.search(value)):
        return []
    return [
        {
            "rule": "residual_absolute_path",
            "locator": locator,
            "message": (
                "machine-local absolute path survived portability "
                "normalization and is not safe for disclosure"
            ),
        }
    ]


def find_residual_absolute_paths(
    document: Any, *, locator: str = "$"
) -> list[dict[str, str]]:
    """Composer-owned invariant (FR-010): ``normalize_portability`` already
    rewrites every absolute path that resolves inside the workspace root, so
    any string that STILL matches an absolute-path pattern afterward is one
    that fell OUTSIDE the root (e.g. ``/workspace/client/export.csv`` or
    ``/mnt/share/raw.csv``). The shared ``scan_disclosure`` scanner's own
    absolute-path rule only recognizes a narrower fixed prefix set
    (home/Users/var/etc/opt/tmp), so it cannot be relied on alone to catch a
    residual path outside that list. This walks the ALREADY-normalized body
    and reports every such residual path as its own blocking finding, so
    generation still fails closed regardless of the shared scanner's coverage.
    """
    if isinstance(document, str):
        return _residual_finding_for_string(document, locator)
    if isinstance(document, dict):
        return [
            finding
            for key, child in document.items()
            for finding in find_residual_absolute_paths(
                child, locator=f"{locator}.{key}"
            )
        ]
    if isinstance(document, list):
        return [
            finding
            for i, child in enumerate(document)
            for finding in find_residual_absolute_paths(
                child, locator=f"{locator}[{i}]"
            )
        ]
    return []


def build_manifest(
    tables: list[dict[str, Any]],
    lineage: dict[str, Any],
    redactions: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """The four-category ledger (FR-016..018): every composed item appears
    under exactly one category, each with a locator. ``redacted`` is carried
    verbatim from the portability-normalization pass (already computed).
    """
    buckets: dict[str, list[dict[str, Any]]] = {
        "included": [],
        "unavailable": [],
        "omitted": [],
    }

    for table in tables:
        for category, entry in _table_entries(table):
            buckets[category].append(entry)
    for category, entry in _lineage_entries(lineage):
        buckets[category].append(entry)

    return {
        "included": buckets["included"],
        "unavailable": buckets["unavailable"],
        "omitted": buckets["omitted"],
        "redacted": redactions,
    }
