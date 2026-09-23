"""Read-only Approver Decision Surface (spec 115).

For ONE table, re-sequence the ALREADY-COMMITTED readiness evidence into a
refutation-first reading view for the human signer: what would make them REFUSE
first (blocked/warning stages, unmet approvals, OPEN unresolved-questions rows),
reassurance (pass stages, recorded approvals, answered questions) last. Ordered
by the SHIPPED fixed category rank (readiness_classify.CATEGORY_RANK); NEVER a
synthesized priority (hard rule #9).

Scope wall:
- WRITES NOTHING, grants no approval, moves no stage. F027 approval-console owns
  the write-back. This module only RE-ORDERS committed evidence. (Structural: no
  file-write call exists here.)
- Reads ONLY the two committed artifacts; opens no DB/network.
- Emits no score/count; adds no gate.
- Generic (Principle VII): per-table over committed files; no hardcoded names.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .readiness_classify import classify, rank_of
from .readiness_spine import (
    STAGE_ORDER,
    approval_required,
    load_status_mapping,
    stage_approval_valid,
    stage_has_valid_approval,
)

# unresolved-questions "Who must answer" -> refutation category (Clarification Q2).
# By the COMMITTED owner column, never by scanning free-text question prose.
_GOVERNANCE_OWNERS: frozenset[str] = frozenset(
    {"governance", "data-owner", "data owner"}
)


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _refutation_item(source: str, category: str, reason: str, **extra: str) -> dict:
    return {
        "kind": "refutation",
        "category": category,
        "rank": rank_of(category),
        "reason": reason,
        "source": source,
        **extra,
    }


def _blocked_stage_items(
    stage: str, block: dict[str, Any], source_path: str
) -> list[dict[str, Any]]:
    """Refusal items for a blocked/warning stage: one per blocking reason."""
    if block.get("status") not in ("blocked", "warning"):
        return []
    return [
        _refutation_item(
            f"{source_path} stages.{stage}", classify(reason)[0], reason, stage=stage
        )
        for reason in _as_str_list(block.get("blocking_reasons"))
    ]


def _unmet_approval_item(
    data: dict[str, Any], stage: str, block: dict[str, Any], source_path: str
) -> dict[str, Any] | None:
    """A refusal item when an approval-requiring stage is pass but unapproved."""
    is_unmet = (
        block.get("status") == "pass"
        and approval_required(stage, block)
        and not stage_has_valid_approval(data.get("approvals"), stage)
    )
    if not is_unmet:
        return None
    return _refutation_item(
        f"{source_path} stages.{stage}/approvals[]",
        "approval",
        f"{stage} is pass but has no valid recorded approval",
        stage=stage,
    )


def _stage_refusals(data: dict[str, Any], source_path: str) -> list[dict[str, Any]]:
    """Refusal items from stages: blocked/warning reasons + unmet approvals (Q1)."""
    stages = data.get("stages")
    if not isinstance(stages, dict):
        return []
    items: list[dict[str, Any]] = []
    for stage in STAGE_ORDER:
        block = stages.get(stage)
        if not isinstance(block, dict):
            continue
        items.extend(_blocked_stage_items(stage, block, source_path))
        unmet = _unmet_approval_item(data, stage, block, source_path)
        if unmet is not None:
            items.append(unmet)
    return items


def _question_category(owner: str) -> str:
    """Refutation category for an OPEN question by its committed owner (Q2)."""
    if owner.strip().lower() in _GOVERNANCE_OWNERS:
        return "approval"
    # analyst / other -> keyword-classify the owner word into grain/readiness.
    return classify(owner)[0]


def _ruled_question_ids(data: dict[str, Any]) -> set[str]:
    """Question ids a committed, eligible approvals[] note names as a whole token."""
    notes = [
        a["note"]
        for a in data.get("approvals") or []
        if isinstance(a, dict)
        and isinstance(a.get("note"), str)
        and stage_approval_valid(a.get("stage"), a)
    ]
    return {tok for note in notes for tok in re.findall(r"[A-Za-z0-9_.-]+", note)}


def _question_reason(row: dict[str, str], ruled: set[str]) -> str | None:
    """None when the row is settled; else the text a signer must weigh.

    A Status cell saying ``answered`` is free markdown (the forgeable one-token
    trust PR #516 was reverted over), so it hides the row only when a committed
    approval names the question id; otherwise the row stays in the refusal case,
    labelled unverified (audit F080)."""
    question = row.get("question", "")
    if row.get("status", "").strip().lower() != "answered":
        return question
    if row.get("id", "") in ruled:
        return None
    return f"self-reported answered (unverified -- no approval names it): {question}"


def _open_question_refusals(
    rows: list[dict[str, str]], source_path: str, data: dict[str, Any]
) -> list[dict[str, Any]]:
    ruled = _ruled_question_ids(data)
    items: list[dict[str, Any]] = []
    for row in rows:
        reason = _question_reason(row, ruled)
        if reason is None:
            continue
        owner = row.get("owner", "")
        items.append(
            _refutation_item(
                f"{source_path} question {row.get('id', '?')}",
                _question_category(owner),
                reason,
                owner=owner,
            )
        )
    return items


def _pass_stage_reassurance(
    data: dict[str, Any], source_path: str
) -> list[dict[str, Any]]:
    stages = data.get("stages")
    if not isinstance(stages, dict):
        return []
    return [
        {"kind": "pass_stage", "detail": stage, "source": source_path}
        for stage in STAGE_ORDER
        if isinstance(stages.get(stage), dict) and stages[stage].get("status") == "pass"
    ]


def _approval_reassurance(
    data: dict[str, Any], source_path: str
) -> list[dict[str, Any]]:
    approvals = data.get("approvals")
    if not isinstance(approvals, list):
        return []
    return [
        {
            "kind": "valid_approval",
            "detail": f"{a.get('stage')} by {a.get('owner')} at {a.get('at')}",
            "source": f"{source_path} approvals[]",
        }
        for a in approvals
        if isinstance(a, dict) and stage_approval_valid(a.get("stage"), a)
    ]


def _reassurance(data: dict[str, Any], source_path: str) -> list[dict[str, Any]]:
    return _pass_stage_reassurance(data, source_path) + _approval_reassurance(
        data, source_path
    )


def _cell(raw: str) -> str:
    """Normalize a markdown table cell: strip whitespace and surrounding markdown
    emphasis (backticks, asterisks) so a value like `` `answered` `` compares as
    'answered'. The committed fixtures backtick their status/id cells."""
    return raw.strip().strip("`* ").strip()


def _parse_open_questions(text: str) -> list[dict[str, str]]:
    """Parse the Open-questions markdown table. Returns one dict per data row with
    id/question/owner/status. Tolerant of surrounding prose and markdown-formatted
    cells; a row is a line with >= 6 pipe-delimited cells whose first cell is not a
    header/separator."""
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        raw_cells = line.strip().strip("|").split("|")
        if len(raw_cells) < 6:
            continue
        cells = [_cell(c) for c in raw_cells]
        first = cells[0].lower()
        if first in ("id", "") or set(raw_cells[0].strip()) <= {"-", ":", " "}:
            continue  # header or separator row
        rows.append(
            {
                "id": cells[0],
                "question": cells[1],
                "owner": cells[3],
                "status": cells[5],
            }
        )
    return rows


def build_approver_view(repo_root: Path | str, table: str) -> dict[str, Any]:
    """Compose the refutation-first view for one table (read-only, writes nothing)."""
    root = Path(repo_root)
    tdir = root / "mappings" / table
    status_rel = f"mappings/{table}/readiness-status.yaml"
    questions_rel = f"mappings/{table}/unresolved-questions.md"

    missing: list[str] = []
    data = load_status_mapping(tdir / "readiness-status.yaml")
    if data is None:
        missing.append(status_rel)
        data = {}

    q_path = tdir / "unresolved-questions.md"
    try:
        q_text = q_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        q_text = None
        missing.append(questions_rel)

    refusal = _stage_refusals(data, status_rel)
    if q_text is not None:
        refusal += _open_question_refusals(
            _parse_open_questions(q_text), questions_rel, data
        )
    # stable, deterministic: fixed enum rank, then lexical tie-break (no computed value)
    refusal.sort(key=lambda i: (i["rank"], i["source"], i["reason"]))

    return {
        "table": table,
        "refusal_case": refusal,
        "reassurance": _reassurance(data, status_rel),
        "missing_inputs": missing,
        "read_only_proof": True,
    }


def _refusal_line(item: dict[str, Any]) -> str:
    owner = f", owner: {item['owner']}" if item.get("owner") else ""
    return f"- [{item['category']}] {item['reason']} ({item['source']}{owner})"


_HEADER = (
    "Read this before you sign. It re-orders committed readiness evidence:\n"
    "what would make you REFUSE first, reassurance last. It records nothing,\n"
    "grants no approval, and moves no stage."
)


def _refusal_section(refusal: list[dict[str, Any]]) -> list[str]:
    head = ["## What would make you refuse (top = weigh first)", ""]
    if not refusal:
        return head + [
            "Nothing in the refusal case: no blocked or warning stage, no unmet "
            "approval, no open question was found in the committed evidence."
        ]
    return head + [_refusal_line(i) for i in refusal]


def _reassurance_section(reassurance: list[dict[str, Any]]) -> list[str]:
    head = ["## Reassurance (recorded positives)", ""]
    if not reassurance:
        return head + ["No recorded pass stage or approval yet."]
    return head + [f"- {r['kind']}: {r['detail']} ({r['source']})" for r in reassurance]


def _missing_input_note(path: str) -> str:
    if path.endswith("unresolved-questions.md"):
        tail = (
            " -- open questions could NOT be read (this is NOT the same as "
            "'no open questions')"
        )
    else:
        tail = " -- readiness state could not be read"
    return f"- {path} not found{tail}."


def _missing_section(missing: list[str]) -> list[str]:
    if not missing:
        return []
    return ["", "## Inputs not available", ""] + [
        _missing_input_note(p) for p in missing
    ]


def render_view(view: dict[str, Any]) -> str:
    """Render the ASCII reading view (UTF-8 no BOM). Writes nothing."""
    lines = [f"# Approver Decision Surface -- {view['table']}", "", _HEADER, ""]
    lines += _refusal_section(view["refusal_case"])
    lines += [""] + _reassurance_section(view["reassurance"])
    lines += _missing_section(view["missing_inputs"])
    return "\n".join(lines) + "\n"
