"""Read-only Dashboard Semantic Audit (spec 123, US5, FR-017/018/019/020).

A REPORT-LEVEL coherence audit -- does the whole composed report answer its
committed Report Intent? -- DISTINCT from the shipped per-visual anti-pattern
QA (``docs/powerbi/visual-qa.md`` / the ``dashboard-qa`` workflow), which
critiques ONE visual/page's presentation defects. This module answers a
different question: does an intent question go unanswered; does a page
serve more than one purpose; does a diagnostic report show its drivers; are
guardrails/comparisons represented; and so on (FR-018). It is decision
SUPPORT, not a ``retail check`` gate (data-model.md D8) -- it grants no
approval and moves no readiness stage.

Emits ONLY the spec-fixed closed enum verbatim (FR-017), never a numeric
score/ranking (FR-020/FR-035):

    covered | incomplete | missing | conflicting | warning | blocked |
    not_applicable_with_reason

FR-020 (reuse, never recompute) is the module's central discipline. Two
checks below deliberately READ a committed artifact BY PATH and CITE its
recorded disposition rather than recomputing the shipped tool's own logic:

- ``pages_not_duplicate`` reads a RECORDED dashboard-planner-verdict fixture
  (a small YAML the coordinator/human records alongside a subject area's
  design/ directory) -- it never imports or calls ``dashboard_planner``'s
  set-relation logic itself. Re-running the planner is re-deriving a check,
  which is exactly what FR-020 forbids (the shipped tool's OUTPUT is what
  gets cited, not its algorithm re-invoked).
- ``accessibility_mobile_rtl_addressed`` reads the filled
  ``a11y-rtl-readiness-checklist.md`` and cites its recorded ``overall_status``
  roll-up -- it NEVER opens ``design/tokens/...`` to re-derive CT1 contrast
  (that is the design_contrast.py rule's job, already run once and recorded).

Everything else here is a mechanically decidable presence/set-membership
check over the in-memory Report Intent / Report Composition / page shapes the
caller supplies (mirroring how ``gap_detector`` takes a caller-supplied
page-intent): a page's ``business_question_ids`` list, a page's ``visuals``
list of ``{visual_id, visual_type}``. This module never authors or edits any
of those artifacts -- it only reads and classifies them.

Read-only: no execution, no DB, no Power BI, no approval grant, no writes.
Generic (Principle VII): no tenant/table literal anywhere in this module.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

# The spec-fixed closed enum (FR-017), verbatim. Do NOT add, remove, or rename
# a value here without updating the workflow skill md in lockstep (T028) --
# the two must never drift (mirrors the dashboard-qa / visual-qa.md pairing).
COVERED = "covered"
INCOMPLETE = "incomplete"
MISSING = "missing"
CONFLICTING = "conflicting"
WARNING = "warning"
BLOCKED = "blocked"
NOT_APPLICABLE_WITH_REASON = "not_applicable_with_reason"

CATEGORIES: frozenset[str] = frozenset(
    {
        COVERED,
        INCOMPLETE,
        MISSING,
        CONFLICTING,
        WARNING,
        BLOCKED,
        NOT_APPLICABLE_WITH_REASON,
    }
)

# Driver-visual types (spec 087 convention list, also named in
# templates/visual-spec.yaml's visual_type comment). A diagnostic report's
# drivers are evidenced by ONE of these visual types appearing somewhere in
# the composed report -- never by the intent's own driver_metrics[] list
# (that names metric ROLES, not visual evidence; data-model.md's check->
# artifact map reads "driver visual types ... / filled driver-decomposition.md").
_DRIVER_VISUAL_TYPES = frozenset(
    {"key_influencers", "decomposition_tree", "smart_narrative"}
)


class Finding(NamedTuple):
    """One Semantic Audit finding (data-model.md's Semantic Audit Finding shape).

    ``evidence`` cites committed artifact path(s) (or, for a purely in-memory
    caller-supplied shape, a human-readable pointer into that shape); NO
    numeric score/confidence field exists here BY DESIGN (FR-020/FR-035).
    """

    check: str
    category: str
    evidence: tuple[str, ...]
    owner_or_correction: str


def _load_yaml_mapping(path: Path) -> dict[str, Any] | None:
    """Load a YAML mapping; None on any read/parse failure (shipped-surface idiom,
    mirrors gap_detector._load_yaml_mapping / report_intent._load_yaml_mapping)."""
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def _owner(intent: dict[str, Any]) -> str:
    """The named owner/correction target for every finding this module emits
    (FR-019: name the responsible owner). Pulled from the intent's own
    ``owner`` field -- never hardcoded -- falling back to a named routing
    instruction if the intent carries none (never silently blank)."""
    owner = intent.get("owner")
    if isinstance(owner, str) and owner.strip():
        return owner.strip()
    return "unassigned -- report_owner must be named on the Report Intent"


# --------------------------------------------------------------------------- #
# Check 1: every intent question is covered by some page (US5 AC#1)
# --------------------------------------------------------------------------- #
def _check_every_intent_question_covered(
    intent: dict[str, Any], pages: list[dict[str, Any]], owner: str
) -> list[Finding]:
    questions = intent.get("business_questions")
    questions = questions if isinstance(questions, list) else []
    question_ids = [
        str(q.get("question_id", "")).strip()
        for q in questions
        if isinstance(q, dict) and str(q.get("question_id", "")).strip()
    ]
    covered_ids: set[str] = set()
    for page in pages:
        covered_ids.update(_str_list(page.get("business_question_ids")))

    findings: list[Finding] = []
    for qid in question_ids:
        if qid in covered_ids:
            findings.append(
                Finding(
                    check="every_intent_question_covered",
                    category=COVERED,
                    evidence=(f"report-intent.yaml:business_questions[{qid}]",),
                    owner_or_correction=owner,
                )
            )
        else:
            findings.append(
                Finding(
                    check="every_intent_question_covered",
                    category=MISSING,
                    evidence=(
                        f"report-intent.yaml:business_questions[{qid}] has no "
                        "page in report-composition.yaml naming it",
                    ),
                    owner_or_correction=(
                        f"{owner} -- author a page (or extend an existing one) "
                        f"that answers question {qid!r}"
                    ),
                )
            )
    if not question_ids:
        findings.append(
            Finding(
                check="every_intent_question_covered",
                category=BLOCKED,
                evidence=("report-intent.yaml:business_questions is empty",),
                owner_or_correction=(
                    f"{owner} -- a committed Report Intent needs >=1 business "
                    "question before this check can run (US1 AC#4)"
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------- #
# Check 2: each page has one coherent purpose (US5 AC#3 -- conflicting)
# --------------------------------------------------------------------------- #
def _check_page_single_coherent_purpose(
    pages: list[dict[str, Any]], owner: str
) -> list[Finding]:
    findings: list[Finding] = []
    for page in pages:
        page_id = str(page.get("page_id", "")).strip() or "(unnamed page)"
        qids = _str_list(page.get("business_question_ids"))
        distinct = sorted(set(qids))
        if len(distinct) <= 1:
            findings.append(
                Finding(
                    check="page_single_coherent_purpose",
                    category=COVERED,
                    evidence=(f"report-composition.yaml:pages[{page_id}]",),
                    owner_or_correction=owner,
                )
            )
        else:
            findings.append(
                Finding(
                    check="page_single_coherent_purpose",
                    category=CONFLICTING,
                    evidence=(
                        f"report-composition.yaml:pages[{page_id}] answers "
                        f"{len(distinct)} distinct intent questions "
                        f"{distinct} -- a page answers ONE business question",
                    ),
                    owner_or_correction=(
                        f"{owner} -- split page {page_id!r} into one page per "
                        "question, or confirm the questions are truly one purpose"
                    ),
                )
            )
    return findings


# --------------------------------------------------------------------------- #
# Check 3: diagnostic reports include drivers (US5 AC#2 -- incomplete)
# --------------------------------------------------------------------------- #
def _iter_page_visuals(pages: list[dict[str, Any]]) -> "Iterator[dict[str, Any]]":
    """Yield each visual dict across all pages, flattening the page/visuals nesting."""
    for page in pages:
        visuals = page.get("visuals")
        if isinstance(visuals, list):
            yield from (v for v in visuals if isinstance(v, dict))


def _has_driver_visual(pages: list[dict[str, Any]]) -> bool:
    return any(
        v.get("visual_type") in _DRIVER_VISUAL_TYPES for v in _iter_page_visuals(pages)
    )


def _check_diagnostic_has_drivers(
    intent: dict[str, Any], pages: list[dict[str, Any]], owner: str
) -> list[Finding]:
    purpose = str(intent.get("purpose", "")).strip()
    if purpose != "diagnostic":
        return [
            Finding(
                check="diagnostic_has_drivers",
                category=NOT_APPLICABLE_WITH_REASON,
                evidence=(f"report-intent.yaml:purpose={purpose!r} (not diagnostic)",),
                owner_or_correction=owner,
            )
        ]
    if _has_driver_visual(pages):
        return [
            Finding(
                check="diagnostic_has_drivers",
                category=COVERED,
                evidence=(
                    "a driver visual type "
                    f"({sorted(_DRIVER_VISUAL_TYPES)!r}) is present in the "
                    "composed report's visuals",
                ),
                owner_or_correction=owner,
            )
        ]
    return [
        Finding(
            check="diagnostic_has_drivers",
            category=INCOMPLETE,
            evidence=(
                "report-intent.yaml:purpose=diagnostic, but no page carries a "
                f"driver visual type ({sorted(_DRIVER_VISUAL_TYPES)!r}) or a "
                "filled driver-decomposition.md",
            ),
            owner_or_correction=(
                f"{owner} -- add a driver visual (key_influencers / "
                "decomposition_tree / smart_narrative) or a filled "
                "driver-decomposition.md before this diagnostic report can "
                "be considered complete"
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# Check 4 (FR-020): pages not duplicate -- reads a RECORDED planner verdict,
# never re-runs dashboard_planner's own set-relation logic.
# --------------------------------------------------------------------------- #
def _verdict_finding(
    entry: dict[str, Any], planner_verdicts_path: str | None, owner: str
) -> Finding:
    """Map one recorded dashboard-planner verdict entry to a Finding (a
    ``duplicate`` verdict -> CONFLICTING, anything else -> COVERED)."""
    page = str(entry.get("proposal_page", "")).strip() or "(unnamed page)"
    verdict = str(entry.get("verdict", "")).strip()
    of_page = str(entry.get("of_page", "")).strip()
    if verdict == "duplicate":
        return Finding(
            check="pages_not_duplicate",
            category=CONFLICTING,
            evidence=(
                f"{planner_verdicts_path}: recorded dashboard-planner "
                f"verdict for {page!r} is 'duplicate of {of_page}'",
            ),
            owner_or_correction=(
                f"{owner} -- resolve the duplicate: merge or drop "
                f"page {page!r} (duplicate of {of_page!r})"
            ),
        )
    return Finding(
        check="pages_not_duplicate",
        category=COVERED,
        evidence=(
            f"{planner_verdicts_path}: recorded dashboard-planner "
            f"verdict for {page!r} is {verdict!r}",
        ),
        owner_or_correction=owner,
    )


def _check_pages_not_duplicate(
    repo_root: Path, planner_verdicts_path: str | None, owner: str
) -> list[Finding]:
    if not planner_verdicts_path:
        return [
            Finding(
                check="pages_not_duplicate",
                category=NOT_APPLICABLE_WITH_REASON,
                evidence=("no recorded dashboard-planner-verdicts path supplied",),
                owner_or_correction=(
                    f"{owner} -- run `retail dashboard-planner` for each proposed "
                    "page and record the verdicts before this check can run"
                ),
            )
        ]
    doc = _load_yaml_mapping(repo_root / planner_verdicts_path)
    if doc is None:
        return [
            Finding(
                check="pages_not_duplicate",
                category=BLOCKED,
                evidence=(f"{planner_verdicts_path} not found or unreadable",),
                owner_or_correction=(
                    f"{owner} -- record the dashboard-planner verdict for each "
                    "proposed page at the path above"
                ),
            )
        ]
    verdicts = doc.get("verdicts")
    verdicts = verdicts if isinstance(verdicts, list) else []
    findings: list[Finding] = [
        _verdict_finding(entry, planner_verdicts_path, owner)
        for entry in verdicts
        if isinstance(entry, dict)
    ]
    if not findings:
        findings.append(
            Finding(
                check="pages_not_duplicate",
                category=BLOCKED,
                evidence=(f"{planner_verdicts_path} carries no recorded verdicts",),
                owner_or_correction=(
                    f"{owner} -- record a dashboard-planner verdict for each "
                    "proposed page"
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------- #
# Check 5 (FR-020): accessibility/mobile/RTL addressed -- reads the filled
# a11y-rtl-readiness-checklist.md and cites its recorded roll-up; NEVER
# re-derives CT1 contrast (never opens design/tokens/...).
# --------------------------------------------------------------------------- #
_ROLLUP_RE_PREFIX = "`overall_status`"


def _parse_overall_status(text: str) -> str | None:
    """Read the checklist's own recorded Roll-up `overall_status` cell.

    The filled template renders a markdown table row
    ``| `overall_status` | `<value>` -- ... |`` under the ``## Roll-up``
    heading. This reads that literal recorded value; it never inspects
    ``design/tokens/...`` or re-runs CT1 (design_contrast.py) itself.
    """
    for line in text.splitlines():
        if _ROLLUP_RE_PREFIX not in line or "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        token = cells[1].split("--")[0].strip().strip("`").strip()
        if token:
            return token
    return None


def _check_accessibility_mobile_rtl_addressed(
    repo_root: Path, a11y_checklist_path: str | None, owner: str
) -> list[Finding]:
    if not a11y_checklist_path:
        return [
            Finding(
                check="accessibility_mobile_rtl_addressed",
                category=NOT_APPLICABLE_WITH_REASON,
                evidence=("no a11y-rtl-readiness-checklist.md path supplied",),
                owner_or_correction=(
                    f"{owner} -- fill templates/a11y-rtl-readiness-checklist.md "
                    "for this page before this check can run"
                ),
            )
        ]
    text = _read_text(repo_root / a11y_checklist_path)
    if text is None:
        return [
            Finding(
                check="accessibility_mobile_rtl_addressed",
                category=MISSING,
                evidence=(f"{a11y_checklist_path} not found",),
                owner_or_correction=(
                    f"{owner} -- fill templates/a11y-rtl-readiness-checklist.md "
                    f"at {a11y_checklist_path}"
                ),
            )
        ]
    status = _parse_overall_status(text)
    if status is None:
        return [
            Finding(
                check="accessibility_mobile_rtl_addressed",
                category=BLOCKED,
                evidence=(
                    f"{a11y_checklist_path}: no recorded Roll-up 'overall_status' "
                    "found",
                ),
                owner_or_correction=(
                    f"{owner} -- record the Roll-up overall_status in "
                    f"{a11y_checklist_path}"
                ),
            )
        ]
    category = status if status in CATEGORIES else WARNING
    return [
        Finding(
            check="accessibility_mobile_rtl_addressed",
            category=category,
            evidence=(
                f"{a11y_checklist_path}: recorded Roll-up overall_status={status!r}",
            ),
            owner_or_correction=owner,
        )
    ]


# --------------------------------------------------------------------------- #
# compose (read-only; writes nothing, grants no approval, moves no stage)
# --------------------------------------------------------------------------- #
def run_semantic_audit(
    *,
    repo_root: Path | str,
    intent: dict[str, Any],
    composition: dict[str, Any],
    pages: list[dict[str, Any]],
    planner_verdicts_path: str | None = None,
    a11y_checklist_path: str | None = None,
) -> tuple[Finding, ...]:
    """Run the Dashboard Semantic Audit over one committed report.

    Parameters mirror the shipped read-only surfaces (``gap_detector``,
    ``dashboard_planner``): caller-supplied in-memory shapes for the Report
    Intent / Report Composition / per-page structural facts the audit reasons
    over (FR-018's coherence checks), plus explicit repo-relative paths for
    the TWO checks that must cite (never recompute, FR-020) an already-shipped
    tool's recorded output: the dashboard-planner verdict and the filled
    a11y/RTL checklist's roll-up.

    Returns an immutable tuple of :class:`Finding`. Grants no approval, moves
    no readiness stage, writes nothing, and never emits a numeric score
    (FR-035) -- every ``category`` is one of the seven values in
    :data:`CATEGORIES`.
    """
    root = Path(repo_root)
    owner = _owner(intent)

    findings: list[Finding] = []
    findings.extend(_check_every_intent_question_covered(intent, pages, owner))
    findings.extend(_check_page_single_coherent_purpose(pages, owner))
    findings.extend(_check_diagnostic_has_drivers(intent, pages, owner))
    findings.extend(_check_pages_not_duplicate(root, planner_verdicts_path, owner))
    findings.extend(
        _check_accessibility_mobile_rtl_addressed(root, a11y_checklist_path, owner)
    )
    return tuple(findings)
