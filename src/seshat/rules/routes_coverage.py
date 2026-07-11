"""A3 -- route-registry coverage reconciler.

A1 (``routes.py``) validates that each routing-manifest target resolves on disk.
It never reads the knowledge map, so the boundary between the human-facing
"Route by task" table in ``docs/knowledge-map.md`` and the machine manifest
``docs/routing/routes.yaml`` is unguarded: an editor can add a task row to the map
without a manifest route (or vice versa) and nothing fails. A3 closes that gap by
asserting the two id sets are in BIJECTION.

The rule is fail-closed in BOTH directions (a map-only id AND a manifest-only id
are each an ERROR), matching A1's posture. The bijection holds on the repo today,
so A3 ships clean-on-main (zero findings) and locks the previously-unguarded
invariant against future one-sided edits.

Static and read-only: the manifest is parsed with a LAZY ``import yaml`` inside the
handler (preserving the stdlib-only invariant of the ``retail check`` core chain,
exactly as A1 does), and the map table is parsed by a hand-rolled standard-library
extractor -- NO markdown-parsing dependency is added. Any unreadable input (missing
or untracked file, malformed YAML, wrong shape, or an unlocatable map table) fails
LOUD with an ERROR, never a vacuous green.
"""

from __future__ import annotations

from typing import Iterable

from ..core import Finding, RuleContext, RuleTier, Severity
from ..registry import register

_MANIFEST = "docs/routing/routes.yaml"
_MAP = "docs/knowledge-map.md"
_MAP_SECTION = "## Route by task"


def _finding(message: str, locator: str) -> Finding:
    return Finding(
        rule_id="A3",
        severity=Severity.ERROR,
        message=message,
        locator=locator,
    )


def _map_ids(text: str) -> set[str] | None:
    """Extract the leading id token of each data row in the "Route by task" table.

    Locates the ``## Route by task`` section, reads its GFM pipe-table data rows
    (skipping the header row and the ``|---|`` separator), takes each row's first
    cell's leading whitespace-delimited token with a single trailing period
    stripped, and STOPS at the next ``## `` heading so other pipe-tables in the map
    (symptom routes, ownership) do not pollute the id set. Sub-letters are
    preserved verbatim ("12a" stays "12a"). Returns ``None`` if the section cannot
    be located, so the caller can fail loud rather than compare against an empty
    set.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == _MAP_SECTION:
            start = i + 1
            break
    if start is None:
        return None

    ids: set[str] = set()
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break  # next section -> stop
        if not stripped.startswith("|"):
            continue
        # Split the pipe row into cells; a leading/trailing '|' yields empty ends.
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        # Skip the header row ("Task") and the |---| separator row. A separator
        # cell is only dashes/colons AND contains at least one dash (so a real
        # data cell that happens to be all colons, or any cell mixing letters and
        # dashes like "1-a", is NOT mistaken for a separator and dropped).
        is_separator = bool(first) and set(first) <= {"-", ":"} and "-" in first
        if not first or first.lower() == "task" or is_separator:
            continue
        token = first.split()[0] if first.split() else ""
        if token.endswith("."):
            token = token[:-1]
        if token:
            ids.add(token)
    return ids


def _manifest_ids(ctx: RuleContext) -> set[str] | list[Finding]:
    """Collect the id of each route in the manifest, mirroring A1's lazy parse.

    Returns a list of Findings (never an id set) on any unreadable/wrong-shape
    input so the caller propagates the fail-loud ERROR.
    """
    if _MANIFEST not in ctx.tracked_files:
        return [
            _finding(
                f"route registry manifest {_MANIFEST!r} is missing or untracked; "
                f"A3 cannot verify the map<->manifest bijection",
                _MANIFEST,
            )
        ]

    import yaml  # lazy: dev/optional dep, kept out of the retail check core chain

    raw = (ctx.repo_root / _MANIFEST).read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # malformed YAML -> fail loud, never vacuous
        return [
            _finding(f"route registry manifest is not valid YAML: {exc}", _MANIFEST)
        ]

    if not isinstance(data, dict) or not isinstance(data.get("routes"), list):
        return [
            _finding(
                "route registry manifest must be a mapping with a 'routes' list",
                _MANIFEST,
            )
        ]

    # Accumulate per-route structural errors (one finding each), mirroring A1's
    # append-and-continue idiom rather than aborting on the first bad entry, so a
    # manifest with N malformed routes surfaces all N. Any structural error makes
    # the parse unreliable, so we return the findings (never a partial id set) and
    # let the caller fail loud.
    ids: set[str] = set()
    errors: list[Finding] = []
    for index, route in enumerate(data["routes"]):
        loc = f"{_MANIFEST}:route[{index}]"
        if not isinstance(route, dict):
            errors.append(_finding(f"route #{index} is not a mapping", loc))
            continue
        route_id = route.get("id")
        if route_id is None:
            errors.append(_finding(f"route #{index} has no 'id'", loc))
            continue
        ids.add(str(route_id))
    if errors:
        return errors
    return ids


@register(
    "A3",
    "Knowledge-map route ids and the routing manifest ids are in bijection",
    tier=RuleTier.KIT_SELF,
)
def check_route_coverage(ctx: RuleContext) -> Iterable[Finding]:
    # Fail-loud branches FIRST -- no unreadable input may fall through to an
    # empty-set comparison (which would be a vacuous green).
    manifest_ids = _manifest_ids(ctx)
    if isinstance(manifest_ids, list):  # the manifest could not be read -> ERRORs
        return manifest_ids

    if _MAP not in ctx.tracked_files:
        return [
            _finding(
                f"knowledge map {_MAP!r} is missing or untracked; A3 cannot verify "
                f"the map<->manifest bijection",
                _MAP,
            )
        ]

    map_text = (ctx.repo_root / _MAP).read_text(encoding="utf-8")
    map_ids = _map_ids(map_text)
    if map_ids is None:
        return [
            _finding(
                f"knowledge map {_MAP!r} has no locatable {_MAP_SECTION!r} table; "
                f"A3 cannot extract the map id set",
                _MAP,
            )
        ]

    findings: list[Finding] = []
    for mid in sorted(map_ids - manifest_ids):
        findings.append(
            _finding(
                f"route id {mid!r} appears in the knowledge map "
                f"{_MAP_SECTION!r} table but is missing from the manifest "
                f"{_MANIFEST!r} -- add the route or remove the map row",
                f"{_MAP}:{mid}",
            )
        )
    for mid in sorted(manifest_ids - map_ids):
        findings.append(
            _finding(
                f"route id {mid!r} appears in the manifest {_MANIFEST!r} but is "
                f"missing from the knowledge map {_MAP_SECTION!r} table -- add the "
                f"map row or remove the route",
                f"{_MANIFEST}:{mid}",
            )
        )
    return findings
