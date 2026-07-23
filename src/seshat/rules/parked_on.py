"""DF1 -- parked-on dependency-edge reconciler.

Roadmap docs assert that certain features are PARKED ON a shared blocker (F016, the
gated Power BI execution adapter). Those park assertions drift: the cited blocker or
evidence file gets moved/renamed, the asserting sentence is edited away, or the parked
target actually ships while the doc still calls it parked. DF1 makes each park edge
machine-checkable. A hand-curated manifest (``docs/quality/parked-on.yaml``) records
each edge as ``blocked`` + ``parked_on`` + ``doc`` + ``anchor`` (the literal sentence
asserting the park) + ``evidence`` (a tracked deferred-spec/record file), with an
OPTIONAL ``shipped_when_tracked`` artifact path.

DF1 fails LOUD (ERROR) on:

* a missing/untracked/malformed manifest, a wrong-shape or incomplete edge, an
  untracked ``doc``, an ``anchor`` absent from that doc, or an untracked ``evidence``
  file (a park citing a nonexistent blocker/evidence);
* a parked-but-shipped contradiction -- if an edge declares ``shipped_when_tracked``
  and that path is now a tracked file, the target has shipped yet the park is still
  asserted.

This is SC1's fail-closed resolver shape applied to dependency edges instead of prose
status claims. It checks ONLY edges listed in the manifest (never free-scans), reads
only committed text + the tracked-file set, parses YAML lazily (preserving the
stdlib-only ``retail check`` core invariant), and is categorical (no confidence score).

IMPORTANT: DF1 maps the parked-on edges to F016; it does NOT start, wire, or vendor
F016 (gated by hard rule #6, deliberately last). It adds the seam, not the
implementation.
"""

from __future__ import annotations

from typing import Iterable

from ..core import Finding, RuleContext, RuleTier, Severity, read_tracked_text
from ..registry import register

_MANIFEST = "docs/quality/parked-on.yaml"
_REQUIRED_FIELDS = ("id", "blocked", "parked_on", "doc", "anchor", "evidence")


def _finding(message: str, locator: str) -> Finding:
    return Finding(
        rule_id="DF1",
        severity=Severity.ERROR,
        message=message,
        locator=locator,
    )


@register(
    "DF1",
    "Parked-on dependency edges reconcile with tracked-file evidence",
    tier=RuleTier.KIT_SELF,
)
def check_parked_on(ctx: RuleContext) -> Iterable[Finding]:
    # A presence-required governance manifest: absent (untracked) OR
    # tracked-but-deleted-on-disk (#430; still listed by `git ls-files`) both
    # fail closed with the SAME finding -- never a vacuous pass, never a crash.
    raw = None
    if _MANIFEST in ctx.tracked_files:
        raw = read_tracked_text(ctx.repo_root / _MANIFEST)
    if raw is None:
        return [
            _finding(
                f"parked-on manifest {_MANIFEST!r} is missing or untracked; "
                f"DF1 cannot reconcile parked-on edges",
                _MANIFEST,
            )
        ]

    import yaml  # lazy: dev/optional dep, kept out of the retail check core chain

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # malformed YAML -> fail loud
        return [_finding(f"parked-on manifest is not valid YAML: {exc}", _MANIFEST)]

    if not isinstance(data, dict) or not isinstance(data.get("edges"), list):
        return [
            _finding(
                "parked-on manifest must be a mapping with an 'edges' list", _MANIFEST
            )
        ]

    tracked = set(ctx.tracked_files)
    findings: list[Finding] = []

    for index, edge in enumerate(data["edges"]):
        loc = f"{_MANIFEST}:edge[{index}]"
        if not isinstance(edge, dict):
            findings.append(_finding(f"edge #{index} is not a mapping", loc))
            continue

        missing = [f for f in _REQUIRED_FIELDS if not edge.get(f)]
        eid = edge.get("id")
        loc = f"{_MANIFEST}:{eid}" if eid else loc
        if missing:
            findings.append(
                _finding(
                    f"edge {eid or f'#{index}'} is missing required field(s): "
                    f"{', '.join(missing)}",
                    loc,
                )
            )
            continue

        doc = edge["doc"]
        if doc not in tracked:
            findings.append(
                _finding(
                    f"edge {eid!r} names doc {doc!r}, which is not a tracked file", loc
                )
            )
            continue

        anchor = edge["anchor"]
        doc_text = read_tracked_text(ctx.repo_root / doc)
        if doc_text is None:
            # Tracked but deleted on disk (#430): the anchor cannot be verified;
            # fail loud rather than crash.
            findings.append(
                _finding(
                    f"edge {eid!r} names doc {doc!r}, which is tracked but missing on "
                    f"disk; the parked-on anchor cannot be verified",
                    loc,
                )
            )
            continue
        if anchor not in doc_text:
            findings.append(
                _finding(
                    f"edge {eid!r} anchor is not present in {doc!r} -- the parked-on "
                    f"assertion is stale or misplaced (sentence moved/removed)",
                    loc,
                )
            )
            continue

        evidence = edge["evidence"]
        if evidence not in tracked:
            findings.append(
                _finding(
                    f"edge {eid!r} cites evidence {evidence!r}, which is not a tracked "
                    f"file -- the park has no recorded deferral evidence",
                    loc,
                )
            )
            continue

        # Optional parked-but-shipped contradiction: a static ship-signal. If the
        # edge declares shipped_when_tracked and that path now exists (tracked), the
        # target has shipped yet the park is still asserted.
        shipped_path = edge.get("shipped_when_tracked")
        if shipped_path and shipped_path in tracked:
            findings.append(
                _finding(
                    f"edge {eid!r} asserts a park on {edge['parked_on']!r}, but "
                    f"{shipped_path!r} is now tracked -- the target shipped; remove or "
                    f"update the edge (parked-but-shipped contradiction)",
                    loc,
                )
            )

    return findings
