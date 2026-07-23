"""SC1 -- stale-marker sweep / status-claim reconciler.

Docs drift: a governance/status doc says a feature is "(planned)" long after it
shipped, or claims something is "built" that does not exist. A1 makes ROUTING claims
machine-checkable; SC1 does the same for PROSE STATUS claims. A hand-curated manifest
(``docs/quality/status-claims.yaml``) records each claim as ``doc`` + ``anchor`` (the
literal sentence asserting it), ``claimed-artifact``, and ``claimed-status``:

* ``built``   -> the artifact MUST resolve to a tracked file. A false ``built``
  (artifact absent) is an ERROR.
* ``planned`` -> the artifact must NOT exist yet. A ``planned`` claim whose artifact
  is now tracked is a STALE marker (ERROR): it shipped but the doc still says planned.

This is A1's fail-closed-both-directions shape applied to prose. SC1 ONLY checks
claims explicitly listed in the manifest (it never free-scans prose), and it verifies
the ``anchor`` is literally present in the claiming doc so the manifest entry cannot
silently point at a sentence that has moved or been deleted. It is categorical
(matches evidence or not) -- it emits no confidence score (hard rule #9).

Static and read-only: the manifest is parsed with a LAZY ``import yaml`` (preserving
the stdlib-only invariant of the ``retail check`` core chain, exactly as A1 does), and
claiming docs are read as committed text. A missing/untracked/malformed manifest, a
wrong-shape or incomplete entry, an untracked claiming doc, or an absent anchor all
fail LOUD with an ERROR, never a vacuous green.

Scope note (ratified, spec 050): SC1 covers the general prose-status-claim class
(file-exists vs built/planned). The rule-COUNT facet (e.g. a stale "N rules" claim) is
explicitly OUT of scope, delegated to a separate future sibling.
"""

from __future__ import annotations

from typing import Iterable

from ..core import Finding, RuleContext, RuleTier, Severity, read_tracked_text
from ..registry import register

_MANIFEST = "docs/quality/status-claims.yaml"
_VALID_STATUS: frozenset[str] = frozenset({"built", "planned"})
_REQUIRED_FIELDS = ("id", "doc", "anchor", "claimed-artifact", "claimed-status")


def _finding(message: str, locator: str) -> Finding:
    return Finding(
        rule_id="SC1",
        severity=Severity.ERROR,
        message=message,
        locator=locator,
    )


@register(
    "SC1",
    "Prose status claims reconcile with tracked-file evidence",
    tier=RuleTier.KIT_SELF,
)
def check_status_claims(ctx: RuleContext) -> Iterable[Finding]:
    # The manifest must be a tracked file present on disk. Absent (untracked) OR
    # tracked-but-deleted-on-disk (#430; still listed by `git ls-files`) both
    # fail loud with the SAME finding rather than passing with nothing to check
    # -- and never crash on the missing read.
    raw = None
    if _MANIFEST in ctx.tracked_files:
        raw = read_tracked_text(ctx.repo_root / _MANIFEST)
    if raw is None:
        return [
            _finding(
                f"status-claims manifest {_MANIFEST!r} is missing or untracked; "
                f"SC1 cannot reconcile status claims",
                _MANIFEST,
            )
        ]

    import yaml  # lazy: dev/optional dep, kept out of the retail check core chain

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # malformed YAML -> fail loud
        return [_finding(f"status-claims manifest is not valid YAML: {exc}", _MANIFEST)]

    if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
        return [
            _finding(
                "status-claims manifest must be a mapping with a 'claims' list",
                _MANIFEST,
            )
        ]

    tracked = set(ctx.tracked_files)
    findings: list[Finding] = []

    for index, claim in enumerate(data["claims"]):
        loc = f"{_MANIFEST}:claim[{index}]"
        if not isinstance(claim, dict):
            findings.append(_finding(f"claim #{index} is not a mapping", loc))
            continue

        missing = [f for f in _REQUIRED_FIELDS if not claim.get(f)]
        cid = claim.get("id")
        loc = f"{_MANIFEST}:{cid}" if cid else loc
        if missing:
            findings.append(
                _finding(
                    f"claim {cid or f'#{index}'} is missing required field(s): "
                    f"{', '.join(missing)}",
                    loc,
                )
            )
            continue

        status = claim["claimed-status"]
        if status not in _VALID_STATUS:
            findings.append(
                _finding(
                    f"claim {cid!r} has invalid claimed-status {status!r} "
                    f"(must be one of {sorted(_VALID_STATUS)})",
                    loc,
                )
            )
            continue

        doc = claim["doc"]
        if doc not in tracked:
            findings.append(
                _finding(
                    f"claim {cid!r} names doc {doc!r}, which is not a tracked file",
                    loc,
                )
            )
            continue

        # The anchor must literally be present in the claiming doc -- else the
        # manifest entry points at a sentence that has moved or been deleted.
        anchor = claim["anchor"]
        doc_text = read_tracked_text(ctx.repo_root / doc)
        if doc_text is None:
            # Tracked but deleted on disk (#430): fail loud rather than crash.
            findings.append(
                _finding(
                    f"claim {cid!r} names doc {doc!r}, which is tracked but missing "
                    f"on disk; the claimed anchor cannot be verified",
                    loc,
                )
            )
            continue
        if anchor not in doc_text:
            findings.append(
                _finding(
                    f"claim {cid!r} anchor is not present in {doc!r} -- the claim is "
                    f"stale or misplaced (the claimed sentence moved or was removed)",
                    f"{_MANIFEST}:{cid}",
                )
            )
            continue

        artifact = claim["claimed-artifact"]
        resolved = artifact in tracked
        if status == "built" and not resolved:
            findings.append(
                _finding(
                    f"claim {cid!r} says {artifact!r} is 'built' but it is not a "
                    f"tracked file -- the claim is false (the artifact does not exist)",
                    f"{_MANIFEST}:{cid}",
                )
            )
        elif status == "planned" and resolved:
            findings.append(
                _finding(
                    f"claim {cid!r} marks {artifact!r} 'planned' but it now exists "
                    f"(tracked) -- flip the claim to 'built' (stale planned marker)",
                    f"{_MANIFEST}:{cid}",
                )
            )

    return findings
