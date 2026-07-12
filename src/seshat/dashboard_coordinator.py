"""US2 dashboard coordinator -- the fail-closed state-inspection helper (spec 123).

The SKILL (`.claude/skills/dashboard-intelligence/SKILL.md`) is the agent-driven
coordinator: it inspects committed state, picks ONE next allowed action, invokes
the shipped capability responsible for it, and re-evaluates -- reusing
`retail dashboard-gaps`, `retail dashboard-planner`, `dashboard-design`, the
blueprint/visual-spec/composition templates, visual-to-contract binding, dashboard
QA, and the human blueprint review (FR-006/FR-007/FR-008). This module is the small,
PURE, read-only helper the SKILL leans on for the load-bearing decision: given the
committed paths, what is the ONE next allowed action, or -- if a precondition is
unmet -- a `blocked` result that names WHAT is missing/invalid, the EVIDENCE
checked, the responsible OWNER, and the ACTION that would unblock progress
(FR-034). The SKILL documents the sequencing; this helper makes the fail-closed
matrix unit-testable (memory: put the oracle ON the risk).

It reuses the shipped surfaces rather than forking them (FR-008/FR-011 -- NO new
CLI family):
- `decision_gate.verdict_for(...)` for the `report_intent` approval verdict, so the
  coordinator reads the SAME approval predicate DS2/the gate use -- it never
  re-derives approval and never self-grants it (Principle V);
- `report_intent.resolve_metric_references(...)` for the FR-003 metric-name
  resolution against the real approved contract store;
- the committed `readiness-status.yaml` for the `semantic_model_ready: pass` hard
  gate the coordinator MUST never bypass (FR-010);
- the committed `visual-contract-binding-map.md` (the same authoritative artifact
  `dashboard_planner` reads) for the zero-orphan-visual check (SC-003).

Read-only: no execution, no DB, no Power BI, no writes, no approval grant, no
readiness-status mutation. It NEVER emits `dashboard_ready: pass` -- the highest a
happy path reaches is "STOP at the human blueprint review seam" (FR-010).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, NamedTuple

from seshat.decision_gate import verdict_for
from seshat.report_intent import resolve_metric_references

_REPORT_INTENT_STAGE = "report_intent"
_INTENT_REL = "design/report-intent.yaml"
_READINESS_REL = "readiness-status.yaml"
_BINDING_REL = "design/visual-contract-binding-map.md"


# --------------------------------------------------------------------------- #
# result shapes
# --------------------------------------------------------------------------- #
class Blocked(NamedTuple):
    """A fail-closed stop (FR-034): what is missing/invalid, the evidence checked,
    the responsible owner, and the action that would unblock progress."""

    what: str
    evidence: str
    owner: str
    unblock: str


class CoordinatorResult(NamedTuple):
    """The coordinator's verdict for ONE step: either the single next allowed action
    or a blocked result. Never carries a numeric score (FR-035); never emits
    `dashboard_ready: pass` (FR-010)."""

    outcome: str  # "next_action" | "blocked"
    stage: str
    action: str | None = None
    blocked: Blocked | None = None
    evidence: tuple[str, ...] = ()


class VisualBinding(NamedTuple):
    """One measure-bearing visual row from the committed binding map."""

    visual_id: str
    business_question: str
    bound_contract: str
    field: str


class DesignTrace(NamedTuple):
    """A read-only trace of the authored design against the committed intent."""

    visuals: tuple[VisualBinding, ...]
    approved_contracts: tuple[str, ...]
    orphan_visuals: tuple[str, ...]  # visual_ids binding no approved contract
    intent_question_ids: tuple[str, ...]
    orphan_questions: tuple[str, ...]  # blueprint questions with no intent match


# --------------------------------------------------------------------------- #
# committed-state readers (None == absent/unreadable; never fabricated)
# --------------------------------------------------------------------------- #
def _load_yaml_mapping(path: Path) -> dict[str, Any] | None:
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


def _semantic_model_status(readiness: dict[str, Any] | None) -> str | None:
    """The committed `semantic_model_ready` status, or None if unreadable."""
    if not isinstance(readiness, dict):
        return None
    stages = readiness.get("stages")
    if not isinstance(stages, dict):
        return None
    stage = stages.get("semantic_model_ready")
    if not isinstance(stage, dict):
        return None
    status = stage.get("status")
    return str(status).strip() if isinstance(status, str) else None


# --------------------------------------------------------------------------- #
# binding-map parsing (the SAME authoritative artifact dashboard_planner reads)
# --------------------------------------------------------------------------- #
_H_ROW_ID = ("visual_id", "visual id")
_H_TYPE = ("visual_type", "visual type")
_H_QUESTION = ("business_question", "business question")
_H_CONTRACT = ("bound_contract", "bound contract")
_H_FIELD = ("semantic_model_field", "field")


def _cells(line: str) -> list[str] | None:
    if "|" not in line:
        return None
    raw = line.strip().strip("|").split("|")
    if len(raw) < 2:
        return None
    return [c.strip() for c in raw]


def _is_separator(cells: list[str]) -> bool:
    return all(set(c) <= {"-", ":", " "} and c for c in cells)


def _header_index(headers: list[str], needles: tuple[str, ...]) -> int | None:
    for i, head in enumerate(headers):
        low = head.lower()
        if any(n in low for n in needles):
            return i
    return None


def _cell_at(cells: list[str], idx: int | None) -> str:
    if idx is None or idx >= len(cells):
        return ""
    return cells[idx].strip().strip("`").strip()


def _binding_visuals(text: str) -> list[VisualBinding]:
    """Parse the FIRST binding-map table carrying both a visual-id and a
    bound-contract column into per-visual rows (mirrors dashboard_planner's
    table selection so the two never disagree on which table is authoritative)."""
    lines = text.splitlines()
    for start, line in enumerate(lines):
        headers = _cells(line)
        if headers is None:
            continue
        i_id = _header_index(headers, _H_ROW_ID)
        i_contract = _header_index(headers, _H_CONTRACT)
        if i_id is None or i_contract is None:
            continue
        cols = {
            "id": i_id,
            "question": _header_index(headers, _H_QUESTION),
            "contract": i_contract,
            "field": _header_index(headers, _H_FIELD),
        }
        return _rows_after(lines[start + 1 :], cols)
    return []


def _rows_after(lines: list[str], cols: dict[str, int | None]) -> list[VisualBinding]:
    rows: list[VisualBinding] = []
    for line in lines:
        cells = _cells(line)
        if cells is None:
            break  # table ends at the first non-pipe line
        if _is_separator(cells):
            continue
        vid = _cell_at(cells, cols["id"])
        if not vid or vid.lower() in ("visual_id", "visual id"):
            continue
        rows.append(
            VisualBinding(
                visual_id=vid,
                business_question=_cell_at(cells, cols["question"]),
                bound_contract=_cell_at(cells, cols["contract"]),
                field=_cell_at(cells, cols["field"]),
            )
        )
    return rows


# --------------------------------------------------------------------------- #
# approved-contract inventory (the coordinator's binding target set -- FR-003)
# --------------------------------------------------------------------------- #
def _approved_contract_names(metrics_dir: Path) -> set[str]:
    """Names of metric contracts under metrics/ with readiness.status == pass.

    An unapproved-but-present contract is NOT a valid binding target (FR-003), so it
    is excluded here -- a visual binding it reads as an orphan (SC-003)."""
    names: set[str] = set()
    if not metrics_dir.is_dir():
        return names
    for path in sorted(metrics_dir.glob("*.yaml")):
        data = _load_yaml_mapping(path)
        if data is None:
            continue
        readiness = data.get("readiness")
        status = ""
        if isinstance(readiness, dict):
            status = str(readiness.get("status", "")).strip()
        if status == "pass":
            names.add(str(data.get("name", path.stem)).strip())
    return names


def _intent_question_ids(intent: dict[str, Any]) -> list[str]:
    questions = intent.get("business_questions")
    if not isinstance(questions, list):
        return []
    out: list[str] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        qid = str(q.get("question_id", "")).strip()
        if qid:
            out.append(qid)
    return out


def _question_matches_intent(business_question: str, intent_qids: list[str]) -> bool:
    """A blueprint business_question traces to an intent question when it references
    a committed intent question id as a whole token (FR-002a)."""
    tokens = set(re.findall(r"[A-Za-z_]\w*", business_question))
    return any(qid in tokens for qid in intent_qids)


# --------------------------------------------------------------------------- #
# the read-only design trace (SC-003 + FR-002a)
# --------------------------------------------------------------------------- #
def trace_design(repo_root: Path | str, subject_area: str) -> DesignTrace:
    """Trace the authored design: which visuals bind an approved contract + mapped
    field (zero orphans, SC-003), and which blueprint questions trace to a committed
    intent question (FR-002a). Read-only; writes nothing."""
    root = Path(repo_root)
    sdir = root / subject_area
    approved = _approved_contract_names(sdir / "metrics")
    intent = _load_yaml_mapping(sdir / _INTENT_REL) or {}
    intent_qids = _intent_question_ids(intent)

    binding_text = _read_text(sdir / _BINDING_REL)
    visuals = _binding_visuals(binding_text) if binding_text else []

    orphan_visuals = tuple(
        v.visual_id for v in visuals if v.bound_contract not in approved
    )
    orphan_questions = tuple(
        v.business_question
        for v in visuals
        if not _question_matches_intent(v.business_question, intent_qids)
    )
    return DesignTrace(
        visuals=tuple(visuals),
        approved_contracts=tuple(sorted(approved)),
        orphan_visuals=orphan_visuals,
        intent_question_ids=tuple(intent_qids),
        orphan_questions=orphan_questions,
    )


# --------------------------------------------------------------------------- #
# the fail-closed sequence -- one next allowed action, else a named blocker
# --------------------------------------------------------------------------- #
def next_action(
    repo_root: Path | str,
    subject_area: str,
    tracked_files: tuple[str, ...],
) -> CoordinatorResult:
    """Inspect committed state and return the ONE next allowed action, or a blocked
    result naming what/evidence/owner/unblock (FR-034).

    Fail-closed order (stop at the FIRST unmet precondition, FR-009/FR-033):
      1. Report Intent artifact is committed and readable.
      2. Report Intent is owner-approved (read via the shipped decision gate -- no
         self-grant; an agent identity never satisfies approved_by).
      3. `semantic_model_ready: pass` (the hard gate, NEVER bypassed -- FR-010).
      4. Every intent metric resolves to an approved contract (FR-003/FR-004);
         an unresolved metric routes upstream to metric-contract definition.
      5. Zero orphan visuals -- every authored visual traces to an approved contract
         and a mapped field (SC-003).
    When all hold, the next allowed action is the HUMAN blueprint review seam; the
    coordinator never self-grants `dashboard_ready: pass` (FR-010).
    """
    root = Path(repo_root)
    sdir = root / subject_area

    intent_blocker = _check_intent_committed(sdir, subject_area)
    if intent_blocker is not None:
        return _blocked(_REPORT_INTENT_STAGE, intent_blocker)

    approval_blocker = _check_intent_approved(root, tracked_files)
    if approval_blocker is not None:
        return _blocked(_REPORT_INTENT_STAGE, approval_blocker)

    model_blocker = _check_semantic_model_ready(sdir, subject_area)
    if model_blocker is not None:
        return _blocked("semantic_model_ready", model_blocker)

    intent = _load_yaml_mapping(sdir / _INTENT_REL) or {}
    metric_blocker = _check_metrics_resolve(root, subject_area, intent)
    if metric_blocker is not None:
        return _blocked("dashboard_gaps", metric_blocker)

    orphan_blocker = _check_no_orphan_visuals(root, subject_area)
    if orphan_blocker is not None:
        return _blocked("dashboard_design", orphan_blocker)

    # All preconditions met + design authored: the single next allowed action is the
    # human blueprint review seam. The coordinator STOPS here and NEVER self-grants
    # dashboard_ready: pass (FR-010).
    return CoordinatorResult(
        outcome="next_action",
        stage="human_blueprint_review",
        action=(
            "STOP at the human blueprint review seam: an eligible named report_owner "
            "reviews the intent + blueprints + visual specs + report composition and "
            "records dashboard_blueprint_approval in the Decision Store. The "
            "coordinator never self-grants dashboard_ready: pass (Principle V)."
        ),
        evidence=(
            f"{subject_area}/{_INTENT_REL} (approved intent)",
            f"{subject_area}/{_BINDING_REL} (zero orphan visuals)",
            f"{subject_area}/{_READINESS_REL} (semantic_model_ready: pass)",
        ),
    )


def _blocked(stage: str, blocker: Blocked) -> CoordinatorResult:
    return CoordinatorResult(outcome="blocked", stage=stage, blocked=blocker)


def _check_intent_committed(sdir: Path, subject_area: str) -> Blocked | None:
    rel = f"{subject_area}/{_INTENT_REL}"
    intent = _load_yaml_mapping(sdir / _INTENT_REL)
    if intent is None:
        return Blocked(
            what="Report Intent is not committed or is unreadable",
            evidence=rel,
            owner="report_owner",
            unblock=(
                "run the report-intent-interview skill to author a committed "
                "report-intent.yaml, then record a report_intent_approval decision"
            ),
        )
    return None


def _check_intent_approved(
    root: Path, tracked_files: tuple[str, ...]
) -> Blocked | None:
    """Read the report_intent approval verdict through the SHIPPED decision gate so
    the coordinator never re-derives approval and never self-grants it."""
    verdict = verdict_for(root, tracked_files, _REPORT_INTENT_STAGE)
    if verdict.verdict == "pass":
        return None
    reasons = "; ".join(f"{b.decision_id}: {b.reason}" for b in verdict.blocking)
    return Blocked(
        what=(
            "Report Intent is not owner-approved -- the report_intent stage gate is "
            f"{verdict.verdict!r}"
        ),
        evidence=reasons or "no valid report_intent_approval decision in the store",
        owner="report_owner",
        unblock=(
            "a named report_owner records a valid report_intent_approval decision in "
            "the Decision Store (an agent identity never satisfies approved_by)"
        ),
    )


def _check_semantic_model_ready(sdir: Path, subject_area: str) -> Blocked | None:
    rel = f"{subject_area}/{_READINESS_REL}"
    readiness = _load_yaml_mapping(sdir / _READINESS_REL)
    status = _semantic_model_status(readiness)
    if status == "pass":
        return None
    return Blocked(
        what=(
            "semantic_model_ready is not 'pass' "
            f"(committed status: {status!r}) -- the hard design gate (FR-010)"
        ),
        evidence=rel,
        owner="metric_owner / data_owner",
        unblock=(
            "complete semantic_model_ready (approved metric contracts + governed "
            "model) to pass before any dashboard design; the coordinator never "
            "bypasses this gate"
        ),
    )


def _check_metrics_resolve(
    root: Path, subject_area: str, intent: dict[str, Any]
) -> Blocked | None:
    result = resolve_metric_references(intent, root)
    if not result.gaps:
        return None
    gap = result.gaps[0]
    names = ", ".join(g.name for g in result.gaps)
    return Blocked(
        what=(
            f"required metric(s) {names} have no approved metric contract "
            f"({gap.reason})"
        ),
        evidence=f"{subject_area}/metrics/ + report-intent.yaml metric references",
        owner="metric_owner",
        unblock=(
            "route upstream to metric-contract definition: a metric_owner authors and "
            "approves the missing metric contract(s); the coordinator never invents a "
            "metric"
        ),
    )


def _check_no_orphan_visuals(root: Path, subject_area: str) -> Blocked | None:
    trace = trace_design(root, subject_area)
    if not trace.orphan_visuals:
        return None
    orphans = ", ".join(trace.orphan_visuals)
    return Blocked(
        what=(
            f"orphan visual(s) {orphans}: a visual binds no approved metric contract "
            "(SC-003 requires zero orphan visuals)"
        ),
        evidence=f"{subject_area}/{_BINDING_REL}",
        owner="report_owner",
        unblock=(
            "bind each visual to exactly one approved metric contract, or drop the "
            "orphan visual; the coordinator never emits a visual with no approved "
            "contract"
        ),
    )
