"""RS1 -- readiness-status contradiction linter.

The readiness spine is useful only if its recorded state is internally
consistent. RS1 checks filled per-table readiness status files
(``mappings/<table>/readiness-status.yaml``) for structural contradictions:

* every stage status is one of the four readiness words;
* ``pass`` carries evidence;
* ``blocked`` carries blocking reasons;
* non-blocked stages do not carry ``blocking_reasons[]``;
* approval-required stages cannot pass without a matching ``approvals[]`` entry;
* a FILE source (``source_ready`` block declaring ``source_kind: csv|excel``) cannot
  pass without a recorded ``source_ready`` approval -- the encoding/delimiter/header
  the mechanical numbers rest on is a ``[PROPOSED]`` inference (a wrong encoding
  silently corrupts every text column), so an owner must confirm it, exactly like the
  semantic-proposal gates. A DB source (no ``source_kind``) is unaffected;
* ``current_stage`` cannot point past an earlier blocked stage;
* a blocked current stage mirrors blockers at the top level.

It is a static text/YAML read. It never opens a DB, never runs Power BI, never
grants an approval, and never advances a stage.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

_INSTANCE_RE = re.compile(r"^mappings/[^/]+/readiness-status\.yaml$")
_STAGE_ORDER: tuple[str, ...] = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)
_STATUS_VALUES: frozenset[str] = frozenset(
    {"not_started", "blocked", "warning", "pass"}
)
_APPROVAL_REQUIRED: frozenset[str] = frozenset(
    {"mapping_ready", "semantic_model_ready", "dashboard_ready", "publish_ready"}
)
# The authority-class tokens an approval owner may carry (any spelling). An owner
# that is ONLY one of these -- a bare role with no person -- is a defect: the
# named-human guarantee (Principle V / audit C4) requires the DECIDER's name, e.g.
# "Ahmed Shaaban (data_owner)". This turns the C4 convention into an enforced rule.
_ROLE_TOKENS: frozenset[str] = frozenset(
    {
        "analyst",
        "governance",
        "data_owner",
        "data-owner",
        "metric_owner",
        "metric-owner",
        "owner",
    }
)


def _owner_is_bare_role(owner: object) -> bool:
    """True if ``owner`` is a bare authority-class token with no person name.
    Case- and whitespace-insensitive. A name + role ("Ahmed Shaaban (data_owner)")
    has content beyond the token, so it is NOT bare. A missing/empty owner is
    handled as bare too (an approval must name its decider)."""
    if not isinstance(owner, str):
        return True
    norm = owner.strip().lower()
    if not norm:
        return True
    return norm in _ROLE_TOKENS


# A source_ready block carrying one of these (normalized) source_kind values is a FILE
# source, whose pass additionally requires an owner encoding-confirmation (a
# source_ready approval). A DB source omits source_kind (or says db-table), so this
# leaves every existing table source unaffected. Extension aliases map the OOXML Excel
# labels (xlsx/xlsm) to the canonical kind so those natural labels do not slip the
# gate; legacy .xls is deliberately NOT aliased (see the note below).
_FILE_SOURCE_KINDS: frozenset[str] = frozenset({"csv", "tsv", "excel"})
_DB_SOURCE_KINDS: frozenset[str] = frozenset({"db-table", "db_table", "table", "db"})
# Only OOXML Excel extensions alias to 'excel' -- openpyxl reads .xlsx/.xlsm, NOT the
# legacy BIFF .xls. A source labelled 'xls' is therefore NOT profileable by make_excel_
# reader; leaving it unaliased means it hits the "unrecognized source_kind" finding,
# which is the correct "unsupported -- convert to .xlsx or defer" signal (Codex review).
_SOURCE_KIND_ALIASES: dict[str, str] = {
    "xlsx": "excel",
    "xlsm": "excel",
}


def _finding(message: str, locator: str) -> Finding:
    return Finding(
        rule_id="RS1",
        severity=Severity.ERROR,
        message=message,
        locator=locator,
    )


def _iter_status_files(ctx: RuleContext) -> list[str]:
    return [
        p for p in ctx.tracked_files if _INSTANCE_RE.match(p) and not is_test_path(p)
    ]


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _stage_status(stage_block: object) -> str | None:
    if isinstance(stage_block, dict):
        status = stage_block.get("status")
        if isinstance(status, str):
            return status
    return None


def _source_kind(stage_block: object) -> str | None:
    """The NORMALIZED ``source_kind`` a source_ready block may declare. Case- and
    whitespace-insensitive, with OOXML extension aliases (xlsx/xlsm -> excel), so the
    gate cannot be slipped by a natural label like 'CSV', 'Excel ', or 'xlsx'
    (adversarial re-review: a case-sensitive frozenset let those bypass H3). Legacy
    '.xls' is deliberately NOT aliased -- openpyxl cannot read BIFF .xls, so it hits
    the 'unrecognized source_kind' finding (the correct 'convert to .xlsx or defer'
    signal), which the test suite pins. Absent -> None (a DB source: the existing,
    unaffected default)."""
    if isinstance(stage_block, dict):
        kind = stage_block.get("source_kind")
        if isinstance(kind, str):
            norm = kind.strip().lower()
            if not norm:
                return None
            return _SOURCE_KIND_ALIASES.get(norm, norm)
    return None


@register("RS1", "Readiness status files are internally consistent")
def check_readiness_status_consistency(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []

    for rel in sorted(_iter_status_files(ctx)):
        try:
            raw = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(_finding(f"could not read readiness status: {exc}", rel))
            continue

        import yaml  # lazy: keep retail check import path stdlib-light

        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            findings.append(_finding(f"readiness status is not valid YAML: {exc}", rel))
            continue

        if not isinstance(data, dict):
            findings.append(_finding("readiness status must be a mapping", rel))
            continue

        stages = data.get("stages")
        if not isinstance(stages, dict):
            findings.append(
                _finding("readiness status must contain a 'stages' mapping", rel)
            )
            continue

        current_stage = data.get("current_stage")
        if current_stage not in _STAGE_ORDER:
            findings.append(
                _finding(
                    f"current_stage {current_stage!r} is not one of "
                    f"{list(_STAGE_ORDER)}",
                    rel,
                )
            )

        approvals = _as_list(data.get("approvals"))
        approved_stages = {
            a.get("stage")
            for a in approvals
            if isinstance(a, dict) and isinstance(a.get("stage"), str)
        }

        # C4 enforcement: every approval must name its DECIDER, not just a role.
        for a in approvals:
            if not isinstance(a, dict):
                continue
            if _owner_is_bare_role(a.get("owner")):
                stage = a.get("stage")
                findings.append(
                    _finding(
                        f"approval for stage {stage!r} has a bare/missing owner "
                        f"{a.get('owner')!r}; record the decider by name + authority "
                        'class (e.g. "Ada Lovelace (data_owner)"), never a role alone',
                        rel,
                    )
                )

        earliest_blocked_index: int | None = None
        for index, stage_name in enumerate(_STAGE_ORDER):
            block = stages.get(stage_name)
            loc = f"{rel}:stages.{stage_name}"
            if block is None:
                findings.append(_finding(f"stage {stage_name!r} is missing", loc))
                continue
            if not isinstance(block, dict):
                findings.append(
                    _finding(f"stage {stage_name!r} must be a mapping", loc)
                )
                continue

            status = _stage_status(block)
            evidence = _as_list(block.get("evidence"))
            blockers = _as_list(block.get("blocking_reasons"))

            if status not in _STATUS_VALUES:
                findings.append(
                    _finding(
                        f"stage {stage_name!r} has invalid status {status!r} "
                        f"(must be one of {sorted(_STATUS_VALUES)})",
                        loc,
                    )
                )
                continue

            if status == "pass" and not evidence:
                findings.append(
                    _finding(
                        f"stage {stage_name!r} is pass but has no evidence[]",
                        loc,
                    )
                )

            if status == "blocked":
                if earliest_blocked_index is None:
                    earliest_blocked_index = index
                if not blockers:
                    findings.append(
                        _finding(
                            f"stage {stage_name!r} is blocked but has no "
                            "blocking_reasons[]",
                            loc,
                        )
                    )
            elif blockers:
                findings.append(
                    _finding(
                        f"stage {stage_name!r} is {status!r} but carries "
                        "blocking_reasons[]; blockers belong on blocked stages",
                        loc,
                    )
                )

            if (
                status == "pass"
                and stage_name in _APPROVAL_REQUIRED
                and stage_name not in approved_stages
            ):
                findings.append(
                    _finding(
                        f"stage {stage_name!r} is pass but no matching "
                        "approvals[] entry is recorded",
                        loc,
                    )
                )

            # File-source encoding-confirmation gate (adversarial review H3). A
            # source_ready block that declares source_kind: csv|excel is a FILE source:
            # its mechanical numbers rest on a [PROPOSED] encoding/delimiter/header that
            # a wrong guess silently corrupts, so pass REQUIRES an owner-recorded
            # source_ready approval. A DB source omits source_kind and is unaffected.
            if stage_name == "source_ready":
                kind = _source_kind(block)
                # An UNRECOGNIZED source_kind must not silently fall through to the DB
                # (unaffected) path -- a typo like 'cvs' or 'spreadsheet' would bypass
                # the gate. Fail loud so the author fixes the label (re-review H3).
                if (
                    kind is not None
                    and kind not in _FILE_SOURCE_KINDS
                    and kind not in _DB_SOURCE_KINDS
                ):
                    findings.append(
                        _finding(
                            f"stage 'source_ready' has unrecognized source_kind "
                            f"{kind!r} -- use a file kind "
                            f"({sorted(_FILE_SOURCE_KINDS)}; xlsx/xlsm alias to excel; "
                            f"legacy .xls is unsupported -- convert to .xlsx) or a DB "
                            f"kind ({sorted(_DB_SOURCE_KINDS)}); an unknown kind must "
                            "not silently skip the file-source encoding gate",
                            loc,
                        )
                    )
                if (
                    status == "pass"
                    and kind in _FILE_SOURCE_KINDS
                    and "source_ready" not in approved_stages
                ):
                    findings.append(
                        _finding(
                            "stage 'source_ready' is a file source "
                            f"(source_kind: {kind!r}) marked pass but no source_ready "
                            "approvals[] entry confirms the encoding/delimiter/header "
                            "-- a [PROPOSED] inference cannot self-grant to pass (a "
                            "wrong encoding corrupts every text column)",
                            loc,
                        )
                    )

        if current_stage in _STAGE_ORDER and earliest_blocked_index is not None:
            current_index = _STAGE_ORDER.index(current_stage)
            if current_index > earliest_blocked_index:
                blocked_stage = _STAGE_ORDER[earliest_blocked_index]
                findings.append(
                    _finding(
                        f"current_stage {current_stage!r} skips past earlier "
                        f"blocked stage {blocked_stage!r}",
                        rel,
                    )
                )

        if current_stage in _STAGE_ORDER:
            current_block = stages.get(current_stage)
            current_status = _stage_status(current_block)
            top_blockers = _as_list(data.get("blocking_reasons"))
            if current_status == "blocked" and not top_blockers:
                findings.append(
                    _finding(
                        "current_stage is blocked but top-level "
                        "blocking_reasons[] is empty",
                        rel,
                    )
                )

    return findings
