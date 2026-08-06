"""Design-lint rule DL9: Report Intent well-formedness gate (spec 123, US1).

A verify-slot-only completeness gate. DL9 scans FILLED Report Intent instances
(``**/design/report-intent.yaml``, excluding the generic
``templates/report-intent.yaml`` blank and committed test fixtures) and asserts
each required field is PRESENT and non-placeholder, so downstream consumers
(the coordinator, the semantic audit) can trust the artifact's SHAPE before
reading its content.

DISTINCT FROM the coordinator's runtime checks (FR-003/FR-007, US2). DL9 never
resolves a ``*_metrics[].name`` reference against the metric-contract store --
that is a runtime state check the coordinator owns, not a static shape rule
(data-model.md D5: "do NOT add a static rule for ... metric-name resolution").
DL9 also never checks FR-002a blueprint<->intent traceability (that is US5's
categorical audit, not a pass/fail gate).

Required fields (structural presence-only, NEVER content-judged):
``audience``, ``supported_decision``, ``review_cadence`` non-empty; ``purpose``
one of the five FR-002 enum values; at least one ``business_questions`` entry
with a non-empty ``text`` (US1 AC#4); ``owner`` a well-formed
"Person Name (class_token)" shape; ``readiness.status: pass`` never recorded
with an empty ``evidence[]``.

Mirrors DL4's (``design_review_evidence.py``) discipline exactly: presence-only,
never content-judged, grants no approval, writes nothing. Reads YAML the way
DL6 (``design_visual_selfcheck.py``) does -- ``yaml.safe_load``, lazy import to
keep the retail-check core stdlib-only at module scope (B1/B3).

Pure static markdown/YAML read: no execution, no DB, no Power BI, no approval
grant. Generic: field names only, no tenant/brand literal (Principle VII).
"""

from __future__ import annotations

from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register
from ..rule_coverage import TEST_FIXTURES, Requirement

# The filled report-intent instances DL9 checks: the glob equivalent of
# _INSTANCE_SUFFIX below. The exempt template (templates/report-intent.yaml) has no
# design/ segment and so cannot match this glob.
REPORT_INTENT_CORPUS = Requirement(
    pattern="*/design/report-intent.yaml",
    exclude=(TEST_FIXTURES,),
    note=(
        "no filled */design/report-intent.yaml is tracked, so this rule checked no "
        "report intent and its silence is not a verified pass"
    ),
)

RULE_ID = "DL9"

_INSTANCE_SUFFIX = "/design/report-intent.yaml"
_TEMPLATE_PATH = "templates/report-intent.yaml"

# FR-002: the five report-purpose values a well-formed intent must declare.
_PURPOSE_ENUM = frozenset(
    {
        "executive",
        "monitoring",
        "diagnostic",
        "action_oriented",
        "analytical_exploration",
    }
)

# The scalar fields that must be present and non-empty (US1 AC#4 + FR-002).
_REQUIRED_SCALARS: tuple[str, ...] = (
    "audience",
    "supported_decision",
    "review_cadence",
)


def _iter_instances(ctx: RuleContext) -> list[str]:
    """Filled per-subject-area instances; the generic template + fixtures excluded."""
    return [
        p
        for p in ctx.tracked_files
        if p.endswith(_INSTANCE_SUFFIX) and p != _TEMPLATE_PATH and not is_test_path(p)
    ]


def _is_blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def _scalar_findings(doc: dict, rel: str) -> list[Finding]:
    findings: list[Finding] = []
    for field in _REQUIRED_SCALARS:
        if _is_blank(doc.get(field)):
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"report intent is missing the required {field!r} field",
                    f"{rel}:field[{field}]",
                )
            )
    return findings


def _purpose_findings(doc: dict, rel: str) -> list[Finding]:
    purpose = doc.get("purpose")
    if _is_blank(purpose):
        return [
            Finding(
                RULE_ID,
                Severity.ERROR,
                "report intent is missing the required 'purpose' field",
                f"{rel}:field[purpose]",
            )
        ]
    if purpose not in _PURPOSE_ENUM:
        return [
            Finding(
                RULE_ID,
                Severity.ERROR,
                f"report intent 'purpose' {purpose!r} is not one of the five "
                f"FR-002 values {sorted(_PURPOSE_ENUM)!r}",
                f"{rel}:field[purpose]",
            )
        ]
    return []


def _business_questions_findings(doc: dict, rel: str) -> list[Finding]:
    questions = doc.get("business_questions")
    if not isinstance(questions, list):
        questions = []
    has_real_question = any(
        isinstance(q, dict) and not _is_blank(q.get("text")) for q in questions
    )
    if has_real_question:
        return []
    return [
        Finding(
            RULE_ID,
            Severity.ERROR,
            "report intent has no business_questions entry with a filled "
            "'text' (US1 AC#4: >=1 primary business question is required "
            "to commit an intent)",
            f"{rel}:field[business_questions]",
        )
    ]


def _owner_findings(doc: dict, rel: str) -> list[Finding]:
    from ..decision_store import owner_shape_ok

    owner = doc.get("owner")
    if owner_shape_ok(owner):
        return []
    return [
        Finding(
            RULE_ID,
            Severity.ERROR,
            f"report intent 'owner' {owner!r} is not a well-formed "
            f"'Person Name (class_token)' shape",
            f"{rel}:field[owner]",
        )
    ]


def _readiness_findings(doc: dict, rel: str) -> list[Finding]:
    readiness = doc.get("readiness")
    if not isinstance(readiness, dict):
        return [
            Finding(
                RULE_ID,
                Severity.ERROR,
                "report intent is missing the required 'readiness' block",
                f"{rel}:field[readiness]",
            )
        ]
    if readiness.get("status") != "pass":
        return []
    evidence = readiness.get("evidence")
    if isinstance(evidence, list) and evidence:
        return []
    return [
        Finding(
            RULE_ID,
            Severity.ERROR,
            "report intent readiness.status is 'pass' but readiness.evidence "
            "is empty; a pass must cite evidence",
            f"{rel}:readiness.evidence",
        )
    ]


@register(
    RULE_ID,
    "A filled Report Intent record carries every required field",
    requires=(REPORT_INTENT_CORPUS,),
)
def check_report_intent(ctx: RuleContext) -> Iterable[Finding]:
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
                    f"could not parse report intent: {exc}",
                    rel,
                )
            )
            continue

        if not isinstance(doc, dict):
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    "report intent is not a YAML mapping",
                    rel,
                )
            )
            continue

        findings.extend(_scalar_findings(doc, rel))
        findings.extend(_purpose_findings(doc, rel))
        findings.extend(_business_questions_findings(doc, rel))
        findings.extend(_owner_findings(doc, rel))
        findings.extend(_readiness_findings(doc, rel))
    return findings
