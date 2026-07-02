"""SC2 -- prose rule-count claim reconciler.

Docs drift: a governance/status doc says "Currently N rules" long after the gate
grew or shrank, so the prose count no longer matches reality. SC1
(``src/retail/rules/status_claims.py``) makes prose STATUS claims (built/planned)
machine-checkable; SC2 is its sibling for the prose rule-COUNT claim, a facet SC1
explicitly delegated out of its scope.

A hand-curated manifest (``docs/quality/rule-count-claims.yaml``) records each claim
as ``id`` + ``doc`` + ``anchor`` (the literal sentence stating the count) +
``claimed-count`` (the integer the prose asserts). SC2 emits an ERROR when the claimed
count differs from the AUTHORITATIVE count.

The authoritative count is read from the committed rule-count JSON
(``docs/rules/rules-manifest.json``) with the stdlib ``json`` module -- NEVER by
importing the rules package. This preserves the stdlib-only never-execute invariant of
the ``retail check`` core chain (exactly as SC1 keeps ``yaml`` lazy) and avoids
counting rules by executing the code SC2 governs.

SC2 is:
  * stdlib-only in its core path (``yaml`` imported lazily; count via stdlib ``json``);
  * read-only (parses committed text, materializes nothing);
  * fail-loud -- a missing/untracked/malformed manifest, a wrong-shape or incomplete
    entry, an untracked claiming doc, an absent anchor, a malformed count, or an
    unreadable/non-list count source ALL emit an ERROR, never a vacuous green;
  * categorical -- the claimed count matches the authoritative count or it does not;
    it emits no confidence score (hard rule #9);
  * manifest-only -- it checks only claims listed in the manifest, never free-scanning
    prose;
  * live-state-only -- it reconciles against the count source as committed now.
"""

from __future__ import annotations

from typing import Iterable

from ..core import Finding, RuleContext, Severity
from ..registry import register

_MANIFEST = "docs/quality/rule-count-claims.yaml"
_COUNT_SOURCE = "docs/rules/rules-manifest.json"
_REQUIRED_FIELDS = ("id", "doc", "anchor", "claimed-count")


def _finding(message: str, locator: str) -> Finding:
    return Finding(
        rule_id="SC2",
        severity=Severity.ERROR,
        message=message,
        locator=locator,
    )


@register("SC2", "Prose rule-count claims reconcile with the authoritative count")
def check_rule_count_claims(ctx: RuleContext) -> Iterable[Finding]:
    # 1. The manifest must be a tracked file; if absent the gate fails loud rather
    #    than passing with nothing to check.
    if _MANIFEST not in ctx.tracked_files:
        return [
            _finding(
                f"rule-count-claims manifest {_MANIFEST!r} is missing or untracked; "
                f"SC2 cannot reconcile rule-count claims",
                _MANIFEST,
            )
        ]

    import yaml  # lazy: dev/optional dep, kept out of the retail check core chain

    raw = (ctx.repo_root / _MANIFEST).read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # malformed YAML -> fail loud
        return [
            _finding(f"rule-count-claims manifest is not valid YAML: {exc}", _MANIFEST)
        ]

    if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
        return [
            _finding(
                "rule-count-claims manifest must be a mapping with a 'claims' list",
                _MANIFEST,
            )
        ]

    # 2. Establish the authoritative count from the committed rule-count JSON, read
    #    with stdlib json (never by importing the rules package). A missing/untracked
    #    or unparseable/non-list source fails loud -- SC2 cannot compare against an
    #    unknown count.
    if _COUNT_SOURCE not in ctx.tracked_files:
        return [
            _finding(
                f"rule-count source {_COUNT_SOURCE!r} is missing or untracked; "
                f"SC2 cannot establish the authoritative count",
                _COUNT_SOURCE,
            )
        ]

    import json  # stdlib

    count_raw = (ctx.repo_root / _COUNT_SOURCE).read_text(encoding="utf-8")
    try:
        parsed = json.loads(count_raw)
    except json.JSONDecodeError as exc:
        return [
            _finding(
                f"rule-count source {_COUNT_SOURCE!r} is not valid JSON: {exc}",
                _COUNT_SOURCE,
            )
        ]
    if not isinstance(parsed, list):
        return [
            _finding(
                f"rule-count source {_COUNT_SOURCE!r} must be a JSON list of rule "
                f"entries; SC2 cannot establish the authoritative count",
                _COUNT_SOURCE,
            )
        ]
    authoritative_count = len(parsed)

    tracked = set(ctx.tracked_files)
    findings: list[Finding] = []

    for index, claim in enumerate(data["claims"]):
        loc = f"{_MANIFEST}:claim[{index}]"

        # 4a. entry must be a mapping.
        if not isinstance(claim, dict):
            findings.append(_finding(f"claim #{index} is not a mapping", loc))
            continue

        cid = claim.get("id")
        loc = f"{_MANIFEST}:{cid}" if cid else loc

        # 4b. all required fields present. id/doc/anchor must be truthy (an empty
        #     string is not a usable value); claimed-count need only be PRESENT here
        #     (0 is a valid count) -- its integer validity is checked in step 4d.
        missing = [f for f in ("id", "doc", "anchor") if not claim.get(f)]
        if "claimed-count" not in claim:
            missing.append("claimed-count")
        if missing:
            findings.append(
                _finding(
                    f"claim {cid or f'#{index}'} is missing required field(s): "
                    f"{', '.join(missing)}",
                    loc,
                )
            )
            continue

        # 4c. the claiming doc must be tracked.
        doc = claim["doc"]
        if doc not in tracked:
            findings.append(
                _finding(
                    f"claim {cid!r} names doc {doc!r}, which is not a tracked file",
                    loc,
                )
            )
            continue

        # 4d. claimed-count must be a non-negative integer (bool excluded).
        claimed = claim["claimed-count"]
        if isinstance(claimed, bool) or not isinstance(claimed, int) or claimed < 0:
            findings.append(
                _finding(
                    f"claim {cid!r} has a malformed claimed-count {claimed!r} "
                    f"(must be a non-negative integer)",
                    loc,
                )
            )
            continue

        # 4e. the anchor must literally be present in the claiming doc -- else the
        #     manifest entry points at a sentence that has moved or been deleted.
        anchor = claim["anchor"]
        doc_text = (ctx.repo_root / doc).read_text(encoding="utf-8")
        if anchor not in doc_text:
            findings.append(
                _finding(
                    f"claim {cid!r} anchor is not present in {doc!r} -- the claim is "
                    f"stale or misplaced (the claimed sentence moved or was removed)",
                    f"{_MANIFEST}:{cid}",
                )
            )
            continue

        # 4f. the comparison: claimed count must equal the authoritative count.
        if claimed != authoritative_count:
            findings.append(
                _finding(
                    f"claim {cid!r} in {doc!r} states {claimed} rules but the "
                    f"authoritative count is {authoritative_count} "
                    f"({_COUNT_SOURCE}); the prose count is stale",
                    f"{_MANIFEST}:{cid}",
                )
            )

    return findings
