"""Stable-release semantics for PyPI version strings -- stdlib only.

This module is the ONE definition of "which PyPI release counts as stable",
shared by two callers that must never disagree:

* `scripts/dep_coresolve.py` -- the spec-136 co-resolution gate and advisory
  freshness report (a repo-only CI script), and
* `seshat.integrations.resolvers` -- the `seshat integrations setup --refresh`
  resolver (shipped in the wheel).

The direction of reuse is deliberate. `scripts/` is NOT in the sdist include
list, so packaged code cannot import from it; a wheel-installed
`--refresh` would raise ImportError. So the primitives live HERE and the
script imports them, never the reverse. Keeping two copies is the failure this
extraction exists to prevent: the yanked rule below is per-file for a reason
(spec-136 plan-review D5), and a drifted second copy would silently propose a
yanked release.

`packaging` is not a guaranteed dependency, so ordering is NUMERIC rather than
lexical -- "1.10" must sort above "1.9".
"""

from __future__ import annotations

import operator
import re
from collections.abc import Iterator

# A pre-release / dev / rc marker: any release whose version string carries one
# of these is not a "stable" target.
_PRERELEASE_RE = re.compile(r"(a|b|rc|c|dev|alpha|beta|pre)\d*", re.IGNORECASE)


def parse_version(version: str) -> tuple[int, ...] | None:
    """A plain numeric release as a comparable int tuple, else None.

    None means "not a plain dotted-numeric release" -- a pre-release, dev, rc,
    or local-segment version -- which excludes it from the stable set.
    """
    core = version.strip()
    # Reject anything carrying a pre-release/dev marker or a local segment.
    if "+" in core or _PRERELEASE_RE.search(core):
        return None
    parts: list[int] = []
    for token in core.split("."):
        if not token.isdigit():
            return None
        parts.append(int(token))
    return tuple(parts) if parts else None


def release_is_yanked(files: object) -> bool:
    """Whether a release is yanked -- it has files and ALL of them are yanked.

    PER-FILE by contract (spec-136 plan-review D5). A release with no files is
    treated as not installable rather than yanked; it is excluded from the
    stable set separately, by `latest_stable`.
    """
    if not isinstance(files, list) or not files:
        return False
    return all(isinstance(f, dict) and f.get("yanked") for f in files)


def is_prerelease(version: str) -> bool:
    """Whether a version string carries a pre-release/dev/rc/local marker."""
    return parse_version(version) is None


def latest_stable(pypi_json: dict) -> str | None:
    """The highest non-yanked, non-pre-release version on PyPI, else None.

    `pypi_json` is the PyPI JSON API body, whose `releases` key maps a version
    to its per-file list.
    """
    return _highest(pypi_json, accept=lambda _version, _parsed: True)


def latest_compatible(
    pypi_json: dict, *, python_version: tuple[int, ...]
) -> str | None:
    """The highest stable release whose `requires-python` admits `python_version`.

    Compatibility beats recency: a newer release that excludes the running
    interpreter is skipped in favour of the newest one that admits it. Returns
    None when no release is both stable and compatible -- the caller refuses
    rather than installing something that cannot run.
    """
    releases = pypi_json.get("releases", {})

    def _accept(version: str, _parsed: tuple[int, ...]) -> bool:
        return python_supported(_requires_python(releases.get(version)), python_version)

    return _highest(pypi_json, accept=_accept)


def _stable_releases(pypi_json: dict) -> Iterator[tuple[str, tuple[int, ...]]]:
    """Each installable release and its parsed form, newest-ness aside.

    Excluded: a release with no files (nothing to install), a fully yanked one,
    and anything that is not a plain dotted-numeric version (pre-release, dev,
    rc, or local segment).
    """
    for version, files in pypi_json.get("releases", {}).items():
        if not isinstance(files, list) or not files:
            continue
        if release_is_yanked(files):
            continue
        parsed = parse_version(str(version))
        if parsed is not None:
            yield str(version), parsed


def _highest(pypi_json: dict, *, accept) -> str | None:
    """The highest stable release passing `accept`, over the PyPI releases map."""
    candidates = [
        (version, parsed)
        for version, parsed in _stable_releases(pypi_json)
        if accept(version, parsed)
    ]
    if not candidates:
        return None
    # `max` keeps the FIRST maximal element, matching the strict `>` this
    # replaced: two strings parsing to the same tuple resolve to the earlier one.
    return max(candidates, key=lambda candidate: candidate[1])[0]


def _requires_python(files: object) -> str:
    """The `requires_python` marker declared by a release's files.

    PyPI records it per file; every file of one release declares the same
    marker in practice, so the first non-empty one is the release's.
    """
    if not isinstance(files, list):
        return ""
    for entry in files:
        if isinstance(entry, dict):
            marker = entry.get("requires_python")
            if marker:
                return str(marker)
    return ""


def artifact_sha256(files: object, version_files: object = None) -> str | None:
    """The SHA256 of a release's preferred artifact, when PyPI reports one.

    A wheel is preferred over an sdist because that is what an install would
    fetch. Returns None when no digest is published -- recorded as null in the
    lock file rather than fabricated.
    """
    candidates = version_files if version_files is not None else files
    if not isinstance(candidates, list):
        return None
    published = _published_digests(candidates)
    wheel = next((digest for kind, digest in published if kind == "bdist_wheel"), None)
    return wheel or (published[0][1] if published else None)


def _published_digests(candidates: list) -> list[tuple[str, str]]:
    """`(packagetype, sha256)` for each non-yanked file that publishes a digest."""
    digests: list[tuple[str, str]] = []
    for entry in candidates:
        if not isinstance(entry, dict) or entry.get("yanked"):
            continue
        digest = (entry.get("digests") or {}).get("sha256")
        if digest:
            digests.append((str(entry.get("packagetype")), str(digest)))
    return digests


def python_supported(marker: str, python_version: tuple[int, ...]) -> bool:
    """Whether `marker` (a PEP 440 `requires-python` string) admits the version.

    Deliberately a SMALL evaluator over the comparison forms PyPI actually
    carries for `requires-python` (`>=`, `>`, `<=`, `<`, `!=`, `==`, `~=`).
    An empty or unparseable marker is permissive -- an unreadable constraint is
    not evidence of incompatibility, and the co-resolution solver remains the
    authority on whether a set installs.
    """
    if not marker or not marker.strip():
        return True
    for clause in marker.split(","):
        clause = clause.strip()
        if not clause:
            continue
        if not _clause_admits(clause, python_version):
            return False
    return True


_OPERATORS = ("~=", "===", "==", "!=", ">=", "<=", ">", "<")


def _clause_admits(clause: str, python_version: tuple[int, ...]) -> bool:
    for op in _OPERATORS:
        if clause.startswith(op):
            return _compare(op, clause[len(op) :].strip(), python_version)
    return True


def _compatible_release(left: tuple[int, ...], bound: tuple[int, ...]) -> bool:
    """PEP 440 `~=`: at least `bound`, and equal on all but the last component."""
    return left >= bound and left[:-1] == bound[:-1]


# One comparison per PEP 440 operator, keyed by the operator itself. An operator
# absent here is permissive, matching the module's "unreadable is not evidence of
# incompatibility" posture.
_COMPARISONS = {
    "==": operator.eq,
    "===": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "~=": _compatible_release,
}


def _compare(op: str, raw: str, actual: tuple[int, ...]) -> bool:
    bound = _loose_version(raw)
    if bound is None:
        return True
    # Compare on the shared prefix so ">=3.9" admits (3, 13) and "==3.13"
    # admits (3, 13, 2) -- PyPI markers are written at 2 components.
    width = len(bound)
    left = actual[:width] + (0,) * max(0, width - len(actual))
    comparison = _COMPARISONS.get(op)
    return True if comparison is None else comparison(left, bound)


def _loose_version(raw: str) -> tuple[int, ...] | None:
    """A dotted-numeric bound, tolerating a trailing `.*` wildcard."""
    text = raw.strip().rstrip("*").rstrip(".")
    if not text:
        return None
    parts: list[int] = []
    for token in text.split("."):
        if not token.isdigit():
            return None
        parts.append(int(token))
    return tuple(parts) if parts else None
