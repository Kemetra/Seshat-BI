"""Design-lint rule DL6: visual-spec anti-pattern self-check consistency (A9).

A single-spec consistency check. DL6 scans FILLED ``visual-spec.yaml`` instances
(excluding the generic ``templates/visual-spec.yaml`` blank and test fixtures)
and asserts an INTERNAL invariant: if a visual self-attests an anti-pattern
(any ``anti_pattern_checks`` key set ``true``), it MUST record at least one real
``readiness.blocking_reasons`` entry -- a flagged defect with no stated "why" is
an internally inconsistent spec.

SCOPE (deliberately narrow, per the A9 ruling). DL6 checks ONE spec against
ITSELF only. It does NOT reconcile the ``anti_pattern_checks`` key SET against
the numbered anti-pattern prose (docs/powerbi/visual-qa.md) -- that cross-file
parity is B1's job and is left to it. It does NOT map a specific true key to a
specific reason (the reasons are free text; inferring that mapping would be
fabrication). It only asserts the EXISTENCE pairing: any true -> some reason.

Never fabricates and never grants: DL6 reads committed YAML, decides nothing
about whether the visual is good, and never writes an approval or a readiness
status. Pure static read -- no execution, no DB, no Power BI (Principle VIII).
Generic: key/field names only, no tenant/brand literal (Principle VII).
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "DL6"

# Filled visual-spec DISCOVERY convention (shared -- A4/A11 will reuse this glob
# when they are built; the binding decision for those rules is made then, but the
# path shape is anchored here). A filled spec is a YAML file that is EITHER named
# visual-spec.yaml OR lives under a `visuals/` | `visual-specs/` directory with an
# arbitrary basename -- the latter is the documented page-blueprint convention
# (templates/dashboard-page-blueprint.yaml:200 shows spec_ref
# `.../visuals/<visual_id>.yaml`).
# The path predicate is intentionally generous: the real false-positive guard is
# the content check below (a file with no `anti_pattern_checks` mapping is skipped),
# and `anti_pattern_checks` is distinctive (design-review-evidence uses the distinct
# key `anti_patterns_checked`). The generic template + committed test fixtures are
# always excluded.
_BARE_INSTANCE = "visual-spec.yaml"
_INSTANCE_SUFFIX = "/visual-spec.yaml"
_TEMPLATE_PATH = "templates/visual-spec.yaml"
_SPEC_DIR_RE = re.compile(r"(^|/)(visuals|visual-specs)/[^/]+\.ya?ml$")

# An angle-bracket token (the G6/PP1 unfilled-placeholder convention). A
# blocking_reasons entry that is only a placeholder is not a real reason.
_PLACEHOLDER_RE = re.compile(r"<[^>]+>")


def _iter_instances(ctx: RuleContext) -> list[str]:
    """Filled per-visual instances; the generic template + fixtures are excluded."""
    out: list[str] = []
    for p in ctx.tracked_files:
        if p == _TEMPLATE_PATH or is_test_path(p):
            continue
        if (
            p == _BARE_INSTANCE
            or p.endswith(_INSTANCE_SUFFIX)
            or _SPEC_DIR_RE.search(p)
        ):
            out.append(p)
    return out


def _is_real_reason(entry: object) -> bool:
    """True if a blocking_reasons entry is a filled, non-placeholder string."""
    if not isinstance(entry, str):
        return False
    stripped = entry.strip().strip("`").strip()
    if not stripped:
        return False
    return not _PLACEHOLDER_RE.search(entry)


@register(
    RULE_ID,
    "A visual-spec that self-attests an anti-pattern records a blocking reason",
)
def check_visual_spec_selfcheck(ctx: RuleContext) -> Iterable[Finding]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope (B1/B3)

    findings: list[Finding] = []
    for rel in sorted(_iter_instances(ctx)):
        try:
            with (ctx.repo_root / rel).open(encoding="utf-8-sig") as fh:
                doc = yaml.safe_load(fh)
        except (OSError, yaml.YAMLError) as exc:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"could not parse visual-spec: {exc}",
                    rel,
                )
            )
            continue

        if not isinstance(doc, dict):
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    "visual-spec is not a YAML mapping",
                    rel,
                )
            )
            continue

        checks = doc.get("anti_pattern_checks")
        if not isinstance(checks, dict):
            # No self-check block, or malformed -> nothing to reconcile here.
            # (Presence of the block is not DL6's concern; DL4/schema owns shape.)
            continue

        # Existence pairing, not per-key mapping: any TRUE self-attested
        # anti-pattern requires at least one real blocking reason. `is True`
        # (not truthiness) so a leftover "<placeholder>" string is not a defect.
        attested = [k for k, v in checks.items() if v is True]
        if not attested:
            continue

        readiness = doc.get("readiness")
        reasons = (
            readiness.get("blocking_reasons") if isinstance(readiness, dict) else None
        )
        reason_list = reasons if isinstance(reasons, list) else []
        if not any(_is_real_reason(r) for r in reason_list):
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"visual-spec self-attests anti-pattern(s) "
                    f"{sorted(attested)!r} (anti_pattern_checks true) but records "
                    f"no readiness.blocking_reasons entry stating why; a flagged "
                    f"defect must carry a reason",
                    f"{rel}:readiness.blocking_reasons",
                )
            )
    return findings
