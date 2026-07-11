"""SF1 -- cross-layer checklist fork detector (spec 086, idea I3).

As more cross-layer checklists appear under ``skills/**/checklists/``, two skills
can carry the SAME-basename checklist that has silently DIVERGED (a fork). Nothing
declares which same-basename files are intentionally shared (must stay identical)
vs intentionally distinct (per-layer specialization) -- so a fork cannot be told
apart from drift.

SF1 globs ``skills/**/checklists/*.md`` from ``ctx.tracked_files``, groups by
basename, and reconciles every 2+-skill collision against the HUMAN-AUTHORED
``docs/quality/shared-spine.yaml`` (``shared`` = all copies MUST be byte-identical;
``distinct`` = copies MAY differ). Fail-closed on: an UNDECLARED collision, a
``shared`` basename whose copies drift, a value that is not ``shared``/``distinct``,
and a missing/unparseable manifest. WARN on a stale entry and a moot ``distinct``.

The manifest is HUMAN-AUTHORED: SF1 only READS it. It NEVER writes/generates the
manifest and NEVER rules a fork shared-vs-distinct -- that cross-layer identity
call is a Principle-V human judgment. Static, ``ctx.tracked_files`` only, no
execution, no DB, no numeric score. ``yaml`` is imported LAZILY (kept out of the
retail check static-core chain, mirroring SC1/SC2/parked_on).
"""

from __future__ import annotations

import hashlib
import re
from typing import Iterable

from ..core import Finding, RuleContext, RuleTier, Severity, is_test_path
from ..registry import register

RULE_ID = "SF1"

SPINE_REL = "docs/quality/shared-spine.yaml"
# Match the DOCUMENTED recursive scope skills/**/checklists/*.md (Codex #182 P2a):
# one-or-more path segments may sit between skills/ and checklists/ (a nested pack
# like skills/vendor/bi-python-knowledge/checklists/agg.md), not exactly one.
_CHECKLIST_RE = re.compile(r"^skills/(?:[^/]+/)+checklists/[^/]+\.md$")
_VALID_VALUES = ("shared", "distinct")


def _basename(rel: str) -> str:
    return rel.rsplit("/", 1)[-1]


def _sha256(ctx: RuleContext, rel: str) -> str | None:
    try:
        data = (ctx.repo_root / rel).read_bytes()
    except OSError:
        return None
    return hashlib.sha256(data).hexdigest()


def _collect(ctx: RuleContext) -> dict[str, list[str]]:
    """basename -> sorted list of tracked checklist paths (test paths exempt)."""
    groups: dict[str, list[str]] = {}
    for rel in ctx.tracked_files:
        if _CHECKLIST_RE.match(rel) and not is_test_path(rel):
            groups.setdefault(_basename(rel), []).append(rel)
    for paths in groups.values():
        paths.sort()
    return groups


@register(RULE_ID, "cross-layer checklist fork detector", tier=RuleTier.KIT_SELF)
def check_sf1(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []

    # --- load the human-authored manifest (fail-closed on missing/unparseable) --
    if SPINE_REL not in set(ctx.tracked_files):
        return [
            Finding(
                RULE_ID,
                Severity.ERROR,
                f"shared-spine manifest not found as a tracked file: {SPINE_REL} "
                f"(SF1 has no contract to check against)",
                SPINE_REL,
            )
        ]

    import yaml  # lazy: dev/optional dep, kept out of the retail check core chain

    try:
        raw = (ctx.repo_root / SPINE_REL).read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError) as exc:  # malformed/unreadable -> fail loud
        return [
            Finding(
                RULE_ID,
                Severity.ERROR,
                f"could not read/parse {SPINE_REL}: {exc}",
                SPINE_REL,
            )
        ]

    declared: dict[str, str] = {}
    if isinstance(data, dict) and isinstance(data.get("checklists"), dict):
        declared = {str(k): v for k, v in data["checklists"].items()}
    elif data is not None:
        findings.append(
            Finding(
                RULE_ID,
                Severity.ERROR,
                f"{SPINE_REL} must have a top-level 'checklists:' mapping",
                SPINE_REL,
            )
        )

    # --- FR-008b: any declared value must be exactly shared|distinct ------------
    for basename, value in sorted(declared.items()):
        if value not in _VALID_VALUES:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"shared-spine entry {basename!r} has value {value!r}; "
                    f"must be one of {_VALID_VALUES}",
                    f"{SPINE_REL}:{basename}",
                )
            )

    groups = _collect(ctx)
    collisions = {b: paths for b, paths in groups.items() if len(paths) >= 2}

    # --- collisions: undeclared / shared-drift / moot-distinct ------------------
    for basename in sorted(collisions):
        paths = collisions[basename]
        value = declared.get(basename)
        if value is None:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"undeclared cross-layer checklist collision {basename!r} in "
                    f"{len(paths)} skills ({', '.join(paths)}); declare it "
                    f"'shared' or 'distinct' in {SPINE_REL}",
                    f"{SPINE_REL}:{basename}",
                )
            )
            continue
        if value not in _VALID_VALUES:
            continue  # already ERRORed on the bad value above
        hashes = {p: _sha256(ctx, p) for p in paths}
        distinct_hashes = {h for h in hashes.values() if h is not None}
        if value == "shared" and len(distinct_hashes) > 1:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"'shared' checklist {basename!r} has diverging copies: "
                    + "; ".join(
                        f"{p} ({(h or 'unreadable')[:12]})" for p, h in hashes.items()
                    ),
                    f"{SPINE_REL}:{basename}",
                )
            )
        elif value == "distinct" and len(distinct_hashes) == 1:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.WARNING,
                    f"'distinct' checklist {basename!r} now has byte-identical "
                    f"copies -- the distinct declaration is moot; consider "
                    f"'shared' or removing a copy",
                    f"{SPINE_REL}:{basename}",
                )
            )

    # --- stale entries: declared but no longer a collision ----------------------
    for basename in sorted(declared):
        if basename not in collisions:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.WARNING,
                    f"shared-spine entry {basename!r} no longer names a live "
                    f"cross-layer collision (a copy was removed or renamed); "
                    f"remove the stale entry",
                    f"{SPINE_REL}:{basename}",
                )
            )

    return findings
