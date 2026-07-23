"""DR1 -- design-layer route path foot-gun + stale-phrase guard.

Two static, read-only honesty checks over the committed tree, both fail-loud:

1. **Path foot-gun.** A curated set of known-bad path PREFIXES that a tracked file
   must never live under -- e.g. a `.claude/worktrees/` scratch copy that is
   per-checkout and dangles for every other clone. Any tracked file whose path
   starts with a foot-gun prefix is flagged.

2. **Stale-phrase manifest.** A hand-curated manifest,
   ``docs/quality/design-stale-phrases.yaml``, lists prose phrases that are KNOWN
   STALE (a superseded verb, a "spec-only" claim about a shipped surface, a renamed
   token). Each entry is ``{doc, anchor, reason}``. DR1 is the INVERSE of SC1: SC1
   requires an anchor to be PRESENT (a moved anchor is flagged); DR1 flags an anchor
   that is STILL PRESENT (the stale phrase was never removed). ERROR when the stale
   anchor is found in its doc.

Principle discipline: DR1 DECIDES nothing (Principle V). It never rewrites a doc,
never resolves which phrasing is canonical -- it flags a curated, human-authored
list of known-stale strings and known-bad path prefixes and stops. It emits no
numeric score (hard rule #9): strictly per-hit categorical ERRORs. It is read-only
(scan ``ctx.tracked_files`` + read committed text), never executes, and reads the
manifest with a LAZY ``import yaml`` so the stdlib-only ``retail check`` core chain
is preserved (matching ``routes.py`` / ``dax_gen``). A missing/malformed manifest
fails LOUD, never vacuously green.

Scope (owner ruling, design 2026-07-03): the optional ``design-system-boundary.yaml``
two-system guard is DEFERRED until a real cross-system collision exists (YAGNI). DR1
ships the path + stale-phrase halves only.
"""

from __future__ import annotations

from typing import Iterable

from ..core import Finding, RuleContext, RuleTier, Severity, read_tracked_text
from ..registry import register

RULE_ID = "DR1"

# Manifest of known-stale prose phrases (hand-curated, like status-claims.yaml).
_STALE_MANIFEST = "docs/quality/design-stale-phrases.yaml"

# Known-bad path prefixes a tracked file must never live under. A worktree scratch
# copy is per-checkout and dangles for everyone else -- it must never be committed.
_FOOTGUN_PREFIXES: tuple[str, ...] = (".claude/worktrees/",)


def _finding(message: str, locator: str) -> Finding:
    return Finding(
        rule_id=RULE_ID, severity=Severity.ERROR, message=message, locator=locator
    )


def _check_footgun_paths(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in ctx.tracked_files:
        for prefix in _FOOTGUN_PREFIXES:
            if rel.startswith(prefix):
                findings.append(
                    _finding(
                        f"tracked path {rel!r} lives under foot-gun prefix "
                        f"{prefix!r} -- a per-checkout scratch path must not ship",
                        rel,
                    )
                )
    return findings


def _check_stale_phrases(ctx: RuleContext) -> list[Finding]:
    raw = None
    if _STALE_MANIFEST in ctx.tracked_files:
        raw = read_tracked_text(ctx.repo_root / _STALE_MANIFEST)
    if raw is None:
        # Untracked OR tracked-but-deleted-on-disk (#430) both fail loud.
        return [
            _finding(
                f"stale-phrase manifest {_STALE_MANIFEST!r} is missing or untracked; "
                f"DR1 cannot verify design prose honesty",
                _STALE_MANIFEST,
            )
        ]

    import yaml  # lazy: dev/optional dep, kept out of the retail check core chain

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return [
            _finding(f"stale-phrase manifest is not valid YAML: {exc}", _STALE_MANIFEST)
        ]

    if not isinstance(data, dict) or not isinstance(data.get("phrases"), list):
        return [
            _finding(
                "stale-phrase manifest must be a mapping with a 'phrases' list",
                _STALE_MANIFEST,
            )
        ]

    findings: list[Finding] = []
    tracked = set(ctx.tracked_files)
    for index, entry in enumerate(data["phrases"]):
        loc = f"{_STALE_MANIFEST}:phrases[{index}]"
        if not isinstance(entry, dict):
            findings.append(_finding(f"phrase entry #{index} is not a mapping", loc))
            continue
        doc = entry.get("doc")
        anchor = entry.get("anchor")
        reason = entry.get("reason", "")
        if not isinstance(doc, str) or not isinstance(anchor, str) or not anchor:
            findings.append(
                _finding(
                    f"phrase entry #{index} must have string 'doc' and non-empty "
                    f"'anchor' fields",
                    loc,
                )
            )
            continue
        if doc not in tracked:
            findings.append(
                _finding(
                    f"stale-phrase entry #{index} names doc {doc!r} which is not a "
                    f"tracked file",
                    doc,
                )
            )
            continue
        text = read_tracked_text(ctx.repo_root / doc, encoding="utf-8-sig")
        if text is None:
            # Tracked but deleted on disk (#430): the anchor cannot be verified.
            # DR1 is a "stale phrase still PRESENT" check, so a missing doc means
            # the phrase is not present -- silently skip (no false stale finding).
            continue
        if anchor in text:
            findings.append(
                _finding(
                    f"stale phrase still present in {doc!r}: {anchor!r}"
                    + (f" -- {reason}" if reason else ""),
                    doc,
                )
            )
    return findings


@register(
    RULE_ID,
    "Design-layer route path foot-gun + stale-phrase guard",
    tier=RuleTier.KIT_SELF,
)
def check_design_routes(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    findings.extend(_check_footgun_paths(ctx))
    findings.extend(_check_stale_phrases(ctx))
    return findings
