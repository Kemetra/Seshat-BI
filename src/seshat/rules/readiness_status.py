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
# The authority classes an approval owner may carry (normalized: lower-case,
# spaces/hyphens collapsed to underscore) -- exactly the four the docs/templates
# define. The named-human guarantee (Principle V / audit C4) requires the FULL
# shape "Person Name (authority_class)", e.g. "Ahmed Shaaban (data_owner)": a
# bare role token, a name with no class, or an unknown class all fail
# _owner_is_valid() -- and ONLY a shape-valid approval counts toward a stage's
# approval requirement (Codex PR#143 review: rejecting exact bare tokens alone
# still let 'Ahmed Shaaban' or 'data owner' grant a gate).
_AUTHORITY_CLASSES: frozenset[str] = frozenset(
    {
        "analyst",
        "governance",
        "data_owner",
        "metric_owner",
    }
)
# Tokens that cannot stand as the person NAME: the classes themselves plus the
# generic "owner" (also NOT a valid class -- it proves no specific authority;
# Codex PR#143 third round).
_ROLE_TOKENS: frozenset[str] = _AUTHORITY_CLASSES | {"owner"}

# "Person Name (authority_class)" -- a non-empty name part, then one parenthesized
# class. Anchored so trailing junk after the class cannot slip through.
_OWNER_SHAPE_RE = re.compile(r"^(?P<name>[^()]+?)\s*\(\s*(?P<role>[^()]+?)\s*\)$")


def _norm_token(value: str) -> str:
    """Normalize a role/name token: lower-case, runs of spaces/hyphens -> '_'."""
    return re.sub(r"[\s\-]+", "_", value.strip().lower())


def _owner_is_valid(owner: object) -> bool:
    """True only for the full named-decider shape "Person Name (authority_class)".

    Case-, whitespace- and hyphen-insensitive on the class token. Rejects a bare
    role token ("data_owner", "data owner"), a name with no class ("Ahmed
    Shaaban"), a role masquerading as the name ("owner (data_owner)"), an unknown
    or generic class ("Ada (wizard)", "Ada (owner)"), and a missing/empty/
    non-string owner -- an approval must name its decider AND the specific
    authority they acted under (audit C4)."""
    if not isinstance(owner, str):
        return False
    match = _OWNER_SHAPE_RE.match(owner.strip())
    if match is None:
        return False
    name = match.group("name").strip()
    if not name or _norm_token(name) in _ROLE_TOKENS:
        return False
    return _norm_token(match.group("role")) in _AUTHORITY_CLASSES


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


def _approved_stages(approvals: list) -> set:
    """Stage names satisfied by a shape-valid approval (named decider + authority
    class). An invalid owner is BOTH flagged by ``_check_approval_owners`` AND
    excluded here, so a legacy bare-role or name-only entry cannot keep an
    approval-required stage green (C4; Codex PR#143 review)."""
    return {
        a.get("stage")
        for a in approvals
        if isinstance(a, dict)
        and isinstance(a.get("stage"), str)
        and _owner_is_valid(a.get("owner"))
    }


def _check_approval_owners(approvals: list, rel: str) -> list[Finding]:
    """C4 enforcement: every approval must name its DECIDER + authority class."""
    findings: list[Finding] = []
    for a in approvals:
        if not isinstance(a, dict):
            continue
        if not _owner_is_valid(a.get("owner")):
            stage = a.get("stage")
            findings.append(
                _finding(
                    f"approval for stage {stage!r} has invalid owner "
                    f"{a.get('owner')!r}; record the decider by name + authority "
                    'class (e.g. "Ada Lovelace (data_owner)") -- a bare role, a '
                    "name without a class, or an unknown class does not count "
                    "toward the stage-approval requirement",
                    rel,
                )
            )
    return findings


def _check_current_stage_value(current_stage: object, rel: str) -> list[Finding]:
    if current_stage in _STAGE_ORDER:
        return []
    return [
        _finding(
            f"current_stage {current_stage!r} is not one of {list(_STAGE_ORDER)}",
            rel,
        )
    ]


def _check_evidence(
    status: str | None, evidence: list, stage_name: str, loc: str
) -> list[Finding]:
    if status == "pass" and not evidence:
        return [_finding(f"stage {stage_name!r} is pass but has no evidence[]", loc)]
    return []


def _check_blockers(
    status: str | None, blockers: list, stage_name: str, loc: str
) -> list[Finding]:
    if status == "blocked":
        if not blockers:
            return [
                _finding(
                    f"stage {stage_name!r} is blocked but has no blocking_reasons[]",
                    loc,
                )
            ]
        return []
    if blockers:
        return [
            _finding(
                f"stage {stage_name!r} is {status!r} but carries "
                "blocking_reasons[]; blockers belong on blocked stages",
                loc,
            )
        ]
    return []


def _is_approval_required_pass_without_approval(
    status: str | None, stage_name: str, approved_stages: set
) -> bool:
    return (
        status == "pass"
        and stage_name in _APPROVAL_REQUIRED
        and stage_name not in approved_stages
    )


def _check_approval_required(
    status: str | None, stage_name: str, approved_stages: set, loc: str
) -> list[Finding]:
    if not _is_approval_required_pass_without_approval(
        status, stage_name, approved_stages
    ):
        return []
    return [
        _finding(
            f"stage {stage_name!r} is pass but no matching "
            "approvals[] entry is recorded",
            loc,
        )
    ]


def _is_unrecognized_source_kind(kind: str | None) -> bool:
    # An UNRECOGNIZED source_kind must not silently fall through to the DB
    # (unaffected) path -- a typo like 'cvs' or 'spreadsheet' would bypass
    # the gate. Fail loud so the author fixes the label (re-review H3).
    return (
        kind is not None
        and kind not in _FILE_SOURCE_KINDS
        and kind not in _DB_SOURCE_KINDS
    )


def _is_file_source_pass_without_approval(
    status: str | None, kind: str | None, approved_stages: set
) -> bool:
    return (
        status == "pass"
        and kind in _FILE_SOURCE_KINDS
        and "source_ready" not in approved_stages
    )


def _check_source_ready_file_gate(
    block: dict, status: str | None, approved_stages: set, loc: str
) -> list[Finding]:
    """File-source encoding-confirmation gate (adversarial review H3). A
    source_ready block that declares source_kind: csv|excel is a FILE source: its
    mechanical numbers rest on a [PROPOSED] encoding/delimiter/header that a wrong
    guess silently corrupts, so pass REQUIRES an owner-recorded source_ready
    approval. A DB source omits source_kind and is unaffected."""
    findings: list[Finding] = []
    kind = _source_kind(block)
    if _is_unrecognized_source_kind(kind):
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
    if _is_file_source_pass_without_approval(status, kind, approved_stages):
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
    return findings


def _check_stage(
    stage_name: str,
    block: object,
    approved_stages: set,
    rel: str,
) -> tuple[list[Finding], str | None]:
    """Check one stage block. Returns (findings, status) where status is the
    stage's status string ("pass"/"warning"/"blocked"/"not_started") when the
    block has a recognized shape and status, else ``None`` for a
    missing/non-dict/invalid-status block (mirrors the inline continue/skip
    control flow: such a block contributes no further checks). The caller only
    compares this against ``"blocked"`` for earliest-blocked tracking."""
    loc = f"{rel}:stages.{stage_name}"
    if block is None:
        return [_finding(f"stage {stage_name!r} is missing", loc)], None
    if not isinstance(block, dict):
        return [_finding(f"stage {stage_name!r} must be a mapping", loc)], None

    status = _stage_status(block)
    if status not in _STATUS_VALUES:
        return [
            _finding(
                f"stage {stage_name!r} has invalid status {status!r} "
                f"(must be one of {sorted(_STATUS_VALUES)})",
                loc,
            )
        ], None

    evidence = _as_list(block.get("evidence"))
    blockers = _as_list(block.get("blocking_reasons"))

    findings: list[Finding] = []
    findings += _check_evidence(status, evidence, stage_name, loc)
    findings += _check_blockers(status, blockers, stage_name, loc)
    findings += _check_approval_required(status, stage_name, approved_stages, loc)
    if stage_name == "source_ready":
        findings += _check_source_ready_file_gate(block, status, approved_stages, loc)

    return findings, status


def _check_skips_blocked(
    current_stage: object, earliest_blocked_index: int | None, rel: str
) -> list[Finding]:
    if current_stage not in _STAGE_ORDER or earliest_blocked_index is None:
        return []
    current_index = _STAGE_ORDER.index(current_stage)
    if current_index <= earliest_blocked_index:
        return []
    blocked_stage = _STAGE_ORDER[earliest_blocked_index]
    return [
        _finding(
            f"current_stage {current_stage!r} skips past earlier "
            f"blocked stage {blocked_stage!r}",
            rel,
        )
    ]


def _check_blocked_current_mirror(
    current_stage: object, stages: dict, data: dict, rel: str
) -> list[Finding]:
    if current_stage not in _STAGE_ORDER:
        return []
    current_block = stages.get(current_stage)
    current_status = _stage_status(current_block)
    top_blockers = _as_list(data.get("blocking_reasons"))
    if current_status == "blocked" and not top_blockers:
        return [
            _finding(
                "current_stage is blocked but top-level blocking_reasons[] is empty",
                rel,
            )
        ]
    return []


def _load_status_data(ctx: RuleContext, rel: str) -> tuple[dict | None, list[Finding]]:
    """Read + parse one readiness-status file. Returns (data, findings); data is
    None when a fail-closed finding was emitted and the caller must skip the rest
    of this file's checks (mirrors the original read/parse/shape guard continues)."""
    try:
        raw = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return None, [_finding(f"could not read readiness status: {exc}", rel)]

    import yaml  # lazy: keep retail check import path stdlib-light

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, [_finding(f"readiness status is not valid YAML: {exc}", rel)]

    if not isinstance(data, dict):
        return None, [_finding("readiness status must be a mapping", rel)]

    stages = data.get("stages")
    if not isinstance(stages, dict):
        return None, [_finding("readiness status must contain a 'stages' mapping", rel)]

    return data, []


def _check_one_status_file(ctx: RuleContext, rel: str) -> list[Finding]:
    data, findings = _load_status_data(ctx, rel)
    if data is None:
        return findings

    stages = data["stages"]
    current_stage = data.get("current_stage")
    findings += _check_current_stage_value(current_stage, rel)

    approvals = _as_list(data.get("approvals"))
    approved_stages = _approved_stages(approvals)
    findings += _check_approval_owners(approvals, rel)

    earliest_blocked_index: int | None = None
    for index, stage_name in enumerate(_STAGE_ORDER):
        stage_findings, status = _check_stage(
            stage_name, stages.get(stage_name), approved_stages, rel
        )
        findings += stage_findings
        if status == "blocked" and earliest_blocked_index is None:
            earliest_blocked_index = index

    findings += _check_skips_blocked(current_stage, earliest_blocked_index, rel)
    findings += _check_blocked_current_mirror(current_stage, stages, data, rel)

    return findings


@register("RS1", "Readiness status files are internally consistent")
def check_readiness_status_consistency(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in sorted(_iter_status_files(ctx)):
        findings += _check_one_status_file(ctx, rel)
    return findings
