"""A1 -- route registry resolution.

The two-hop routing contract (AGENTS.md -> COMPASS.md -> knowledge-map ->
skill SKILL.md -> INDEX.md -> artifact) lived only as prose tables. A1 makes it
machine-checkable: `docs/routing/routes.yaml` declares each route's targets and
a status, and this rule fails the gate when the contract is broken.

Per route:

* ``status: built``   -> EVERY target must be a tracked file. A missing target
  is a broken route (ERROR) -- the two-hop contract points at a file that is no
  longer there.
* ``status: planned`` -> the target is deferred and must NOT resolve yet. A
  ``planned`` route whose target now exists is a STALE marker (ERROR): the file
  was built but the manifest was never flipped to ``built``.
* ``status: seed``    -> the target EXISTS but is only an initial cut (an early
  seed of a layer, not a complete build). Mechanically identical to ``built``:
  EVERY target must resolve as a tracked file. The distinguishing fact of ``seed``
  vs ``planned`` is precisely that the target exists; the distinguishing fact of
  ``seed`` vs ``built`` (completeness) is a human ruling the rule NEVER makes --
  the seed -> built promotion criterion is deferred (Principle V, out of scope).

This keeps routing honest in both directions, the same fail-closed shape G6 uses
for placeholder-vs-real parameter values.

The manifest is parsed with a LAZY ``import yaml`` inside the handler -- the
stdlib-only invariant of the ``retail check`` core chain is preserved (matching
``dax_gen.load_contract`` / ``metric_drift``). A malformed or missing manifest
fails LOUD (ERROR), never vacuously green.
"""

from __future__ import annotations

from typing import Iterable

from ..core import Finding, RuleContext, RuleTier, Severity

# The registry decorator is imported, not the manifest. The manifest is read at
# rule-run time from the tracked file below.
from ..registry import register

_MANIFEST = "docs/routing/routes.yaml"
_VALID_STATUS: frozenset[str] = frozenset({"built", "planned", "seed"})
# Statuses that assert the target EXISTS: every target must resolve as a tracked
# file (a missing target is a broken route). 'seed' means "exists but is only an
# initial cut" -- the only mechanical guarantee is existence, identical to 'built';
# the completeness/promotion (seed -> built) is a human ruling the rule never makes.
_MUST_RESOLVE: frozenset[str] = frozenset({"built", "seed"})


def _finding(message: str, locator: str) -> Finding:
    return Finding(
        rule_id="A1",
        severity=Severity.ERROR,
        message=message,
        locator=locator,
    )


@register(
    "A1",
    "Route registry targets resolve or are honestly marked planned",
    tier=RuleTier.KIT_SELF,
)
def check_routes_resolve(ctx: RuleContext) -> Iterable[Finding]:
    # Read-only: the manifest must be a tracked file. If it is absent the gate
    # fails loud rather than passing with nothing to check.
    if _MANIFEST not in ctx.tracked_files:
        return [
            _finding(
                f"route registry manifest {_MANIFEST!r} is missing or untracked; "
                f"A1 cannot verify the routing contract",
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

    tracked = set(ctx.tracked_files)
    findings: list[Finding] = []

    for index, route in enumerate(data["routes"]):
        loc = f"{_MANIFEST}:route[{index}]"
        if not isinstance(route, dict):
            findings.append(_finding(f"route #{index} is not a mapping", loc))
            continue

        route_id = route.get("id")
        loc = f"{_MANIFEST}:{route_id}" if route_id else loc

        status = route.get("status")
        if status not in _VALID_STATUS:
            findings.append(
                _finding(
                    f"route {route_id!r} has invalid status {status!r} "
                    f"(must be one of {sorted(_VALID_STATUS)})",
                    loc,
                )
            )
            continue

        targets = route.get("targets", [])
        if not isinstance(targets, list):
            findings.append(
                _finding(f"route {route_id!r} 'targets' must be a list", loc)
            )
            continue

        # A 'built'/'seed' route with no targets points at nothing -> fail, never
        # pass vacuously (a 'planned' route legitimately has no resolving target yet).
        if status in _MUST_RESOLVE and not targets:
            findings.append(
                _finding(f"route {route_id!r} is {status!r} but lists no targets", loc)
            )
            continue

        for target in targets:
            resolved = target in tracked
            if status in _MUST_RESOLVE and not resolved:
                findings.append(
                    _finding(
                        f"route {route_id!r} ({status}) points at {target!r}, "
                        f"which is not a tracked file -- the route is broken",
                        loc,
                    )
                )
            elif status == "planned" and resolved:
                findings.append(
                    _finding(
                        f"route {route_id!r} is marked 'planned' but {target!r} "
                        f"now exists -- flip it to 'built' (stale planned marker)",
                        loc,
                    )
                )

    return findings
