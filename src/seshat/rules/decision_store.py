"""DS1-DS5: static validity checks over the project Decision Store (spec 121).

The Decision Store (``.seshat/semantic-decisions.yaml``,
``.seshat/kpi-contracts.yaml``, ``.seshat/cleaning-rules.yaml``) records the
business decisions from the Business Knowledge Interview. These rules make the
store a gate-enforced artifact:

* DS1 -- store layout / status / id / scope / confidence validity + a
  committed-value PII-shape guard (WARNING);
* DS2 -- approval-metadata completeness, named-human + authority-class shape,
  per-type authority eligibility, evidence + evidence_identity present;
* DS3 -- batch integrity: no critical decision type in a batch; exclusions and a
  valid named-human confirmation recorded;
* DS4 -- approved-record immutability (supersession-only) + supersession
  reference integrity + no two active records conflicting on one scope;
* DS5 -- verdict consistency (implemented in :mod:`seshat.decision_gate`; the
  registered DS5 rule here checks the store-side invariants a verdict rests on).

Static text/YAML read only: never opens a DB, never runs Power BI, never grants
or advances a gate, never fabricates a confidence score. Absent store => no
findings (pass-silent); the fail-closed handling of a malformed store lives in
:mod:`seshat.decision_store`.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from seshat.core import Finding, RuleContext, Severity, is_test_path
from seshat.decision_store import (
    APPROVAL_REQUIRED_FIELDS,
    CONFIDENCE_VALUES,
    STATUS_VALUES,
    Store,
    active_scope_conflicts,
    approval_is_valid,
    is_critical,
    load_authority_map,
    load_store,
    owner_shape_ok,
)
from seshat.registry import register

# The shared owner-shape, authority-map, approval-validity, and scope-conflict
# predicates live in seshat.decision_store so the DS lint rules and the runtime
# gate can never diverge on what "valid" means. This module only formats the
# findings around them.


# id slug: <type>.<scope-slug>[.<n>]  (mirrors the schema pattern). The scope-slug
# segment may carry underscores (e.g. table_grain.fct_sales), dots, and hyphens.
_ID_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9][a-z0-9._-]*$")

# Blank templates live under templates/; DS rules key on the exact .seshat/ store
# paths (via load_store), so a template can never match. Belt-and-suspenders: the
# loader's selector already excludes anything outside STORE_PATHS.

# PII value-shape heuristics for the committed-value guard (FR-005). Best-effort
# shapes with tolerant separators (dot/space/hyphen) so trivial substitution does
# not slip an obvious value past. A heuristic can only be advisory; the primary
# control is masking at interview time.
_PII_SHAPES: tuple[re.Pattern[str], ...] = (
    re.compile(r"[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # email
    re.compile(r"\b\d{3}[ .-]\d{2}[ .-]\d{4}\b"),  # SSN-like (any separator)
    re.compile(r"\b(?:\d[ -]?){12,19}\b"),  # long digit run (card/account-like)
)

# Secret/credential shapes (FR-005's "secrets, credentials" half that C2's
# connection-string patterns do not cover). A bare `password=`/`token=`/`api_key=`
# assignment in a committed store field is never legitimate.
_SECRET_SHAPES: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|token|access[_-]?key)\b\s*[:=]\s*\S+"
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{12,}"),
)

# Record fields whose value is an IDENTITY/reference where a PII or secret value is
# never legitimate -> ERROR. Free-text fields (statement, notes) stay WARNING.
_IDENTITY_FIELDS: tuple[str, ...] = ("id", "proposed_by")


def _finding(rule_id: str, message: str, locator: str, severity: Severity) -> Finding:
    return Finding(rule_id=rule_id, severity=severity, message=message, locator=locator)


def _err(rule_id: str, message: str, locator: str) -> Finding:
    return _finding(rule_id, message, locator, Severity.ERROR)


def _store_for(ctx: RuleContext) -> Store:
    tracked = tuple(p for p in ctx.tracked_files if not is_test_path(p))
    return load_store(ctx.repo_root, tracked)


def _loc(rel: str, decision_id: object) -> str:
    return f"{rel}:decisions.{decision_id}" if decision_id else rel


# ---------------------------------------------------------------------------
# DS1 -- layout / vocabulary / id / scope + PII-shape guard
# ---------------------------------------------------------------------------


def _check_decision_shape(rec: dict[str, Any], rel: str) -> list[Finding]:
    findings: list[Finding] = []
    did = rec.get("id")
    loc = _loc(rel, did)

    if not isinstance(did, str) or not _ID_RE.match(did):
        findings.append(
            _err("DS1", f"decision id {did!r} is missing or malformed", loc)
        )

    status = rec.get("status")
    if not isinstance(status, str) or status not in STATUS_VALUES:
        findings.append(
            _err(
                "DS1",
                f"decision {did!r} has invalid status {status!r} "
                f"(must be one of {sorted(STATUS_VALUES)})",
                loc,
            )
        )

    dtype = rec.get("decision_type")
    if not isinstance(dtype, str) or not dtype:
        findings.append(_err("DS1", f"decision {did!r} has no decision_type", loc))

    findings += _confidence_findings(rec.get("confidence"), status, did, loc)

    scope = rec.get("scope")
    if not _scope_is_nonempty(scope):
        findings.append(
            _err(
                "DS1",
                f"decision {did!r} scope must name at least one of "
                "tables/columns/kpis/artifacts",
                loc,
            )
        )
    return findings


def _confidence_ok(conf: object) -> bool:
    return isinstance(conf, str) and conf in CONFIDENCE_VALUES


def _confidence_findings(
    conf: object, status: object, did: object, loc: str
) -> list[Finding]:
    """A proposal MUST carry a valid confidence; any other record may omit it but
    must not carry an invalid one."""
    if status == "proposed":
        if _confidence_ok(conf):
            return []
        return [
            _err(
                "DS1",
                f"proposed decision {did!r} needs confidence "
                f"(one of {sorted(CONFIDENCE_VALUES)})",
                loc,
            )
        ]
    # Non-proposed: confidence is optional but, if present, must be valid.
    if conf is not None and not _confidence_ok(conf):
        return [_err("DS1", f"decision {did!r} has invalid confidence {conf!r}", loc)]
    return []


def _is_nonempty_list(value: object) -> bool:
    return isinstance(value, list) and bool(value)


def _scope_is_nonempty(scope: object) -> bool:
    if not isinstance(scope, dict):
        return False
    return any(
        _is_nonempty_list(scope.get(key))
        for key in ("tables", "columns", "kpis", "artifacts")
    )


def _value_leak_kind(text: object) -> str | None:
    """'secret', 'pii', or None for a string value. Secrets take precedence."""
    if not isinstance(text, str):
        return None
    if any(p.search(text) for p in _SECRET_SHAPES):
        return "secret"
    if any(p.search(text) for p in _PII_SHAPES):
        return "pii"
    return None


def _iter_record_strings(rec: dict[str, Any]):
    """Yield (path_label, value) for every committed string leaf of a record --
    top-level fields, the approval sub-dict, scope, and evidence lists. So the
    guard covers every surface DS1 can commit or the review can render, not just
    statement/notes."""
    for key, value in rec.items():
        yield from _walk_strings(str(key), value)


def _labeled_children(label: str, value: object) -> list[tuple[str, object]]:
    if isinstance(value, dict):
        return [(f"{label}.{k}", v) for k, v in value.items()]
    if isinstance(value, list):
        return [(f"{label}[{i}]", v) for i, v in enumerate(value)]
    return []


def _walk_strings(label: str, value: object):
    if isinstance(value, str):
        yield label, value
        return
    for child_label, child_value in _labeled_children(label, value):
        yield from _walk_strings(child_label, child_value)


# Free-text fields carry human prose where a shape MAY be an incidental mention ->
# WARNING. Everywhere else (identity/reference fields) a PII/secret value is never
# legitimate -> ERROR.
_FREETEXT_FIELDS: frozenset[str] = frozenset({"statement", "notes"})


def _check_pii_shape(rec: dict[str, Any], rel: str) -> list[Finding]:
    """A raw suspected-PII value or secret in ANY committed store string (FR-005).
    ERROR on identity/reference fields; WARNING on free-text (statement/notes)."""
    did = rec.get("id")
    findings: list[Finding] = []
    for label, value in _iter_record_strings(rec):
        kind = _value_leak_kind(value)
        if kind is None:
            continue
        is_freetext = label.split(".", 1)[0].split("[", 1)[0] in _FREETEXT_FIELDS
        severity = (
            Severity.WARNING if (kind == "pii" and is_freetext) else Severity.ERROR
        )
        noun = (
            "a secret/credential" if kind == "secret" else "a raw suspected-PII value"
        )
        findings.append(
            _finding(
                "DS1",
                f"decision {did!r} field {label!r} looks like it contains {noun}; "
                "mask it and cite a masked evidence artifact instead (FR-005)",
                _loc(rel, did),
                severity,
            )
        )
    return findings


def _ds1_over(store: Store) -> list[Finding]:
    findings: list[Finding] = []
    for lf in store.files:
        for problem in lf.problems:
            findings.append(_err("DS1", problem.message, problem.locator))
        for rec in lf.decisions:
            findings += _check_decision_shape(rec, lf.path)
            findings += _check_pii_shape(rec, lf.path)
        findings += _check_unique_ids(lf.decisions, lf.path)
    return findings


def _check_unique_ids(decisions: tuple[dict, ...], rel: str) -> list[Finding]:
    from collections import Counter

    counts = Counter(
        rec.get("id") for rec in decisions if isinstance(rec.get("id"), str)
    )
    return [
        _err("DS1", f"decision id {did!r} appears {count} times", _loc(rel, did))
        for did, count in counts.items()
        if count > 1
    ]


@register("DS1", "decision store layout, status, id and scope validity")
def check_ds1(ctx: RuleContext) -> Iterable[Finding]:
    return _ds1_over(_store_for(ctx))


# ---------------------------------------------------------------------------
# DS2 -- approval metadata: completeness, shape, eligibility, evidence identity
# ---------------------------------------------------------------------------


def _missing_field_findings(
    approval: dict[str, Any], did: object, loc: str
) -> list[Finding]:
    return [
        _err("DS2", f"approval for {did!r} is missing {key!r}", loc)
        for key in APPROVAL_REQUIRED_FIELDS
        if not approval.get(key)
    ]


def _is_eligibility_reason(reason: str | None) -> bool:
    return bool(reason) and ("ineligible" in reason or "eligibility" in reason)


def _owner_findings(
    rec: dict[str, Any], authority: dict[str, frozenset[str]] | None, loc: str
) -> list[Finding]:
    did = rec.get("id")
    approval = rec["approval"]  # caller guaranteed a dict
    owner = approval.get("approved_by")
    if not owner_shape_ok(owner):
        return [
            _err(
                "DS2",
                f"approval for {did!r} has invalid approved_by {owner!r}; use "
                '"Person Name (authority_class)" -- a bare role, an agent, or an '
                "unknown class does not count",
                loc,
            )
        ]
    # Shape is fine; surface only the eligibility verdict from the shared predicate.
    valid, reason = approval_is_valid(rec, authority)
    if not valid and _is_eligibility_reason(reason):
        return [_err("DS2", reason, loc)]
    return []


def _check_approval(
    rec: dict[str, Any], rel: str, authority: dict[str, frozenset[str]] | None
) -> list[Finding]:
    """Granular DS2 findings, backed by the same predicates the gate uses so the
    lint and the verdict agree on validity."""
    did = rec.get("id")
    loc = _loc(rel, did)
    if rec.get("status") != "approved":
        return []
    approval = rec.get("approval")
    if not isinstance(approval, dict):
        return [_err("DS2", f"approved decision {did!r} has no approval block", loc)]

    return (
        _missing_field_findings(approval, did, loc)
        + _owner_findings(rec, authority, loc)
        + _check_evidence_identity(approval, did, loc)
    )


def _check_evidence_identity(
    approval: dict[str, Any], did: object, loc: str
) -> list[Finding]:
    evidence = approval.get("evidence")
    identity = approval.get("evidence_identity")
    if not isinstance(evidence, list) or not isinstance(identity, dict):
        return []  # missing-field findings already emitted above
    missing = [ref for ref in evidence if isinstance(ref, str) and ref not in identity]
    if missing:
        return [
            _err(
                "DS2",
                f"approval for {did!r} cites evidence with no recorded "
                f"evidence_identity: {missing}",
                loc,
            )
        ]
    return []


@register("DS2", "decision approval metadata is complete and eligible")
def check_ds2(ctx: RuleContext) -> Iterable[Finding]:
    store = _store_for(ctx)
    authority = load_authority_map(ctx.repo_root)
    findings: list[Finding] = []
    for lf in store.files:
        for rec in lf.decisions:
            findings += _check_approval(rec, lf.path, authority)
    return findings


# ---------------------------------------------------------------------------
# DS3 -- batch integrity
# ---------------------------------------------------------------------------


@register("DS3", "decision batch integrity (no critical types; valid confirmation)")
def check_ds3(ctx: RuleContext) -> Iterable[Finding]:
    store = _store_for(ctx)
    findings: list[Finding] = []
    for lf in store.files:
        by_id = {
            rec.get("id"): rec for rec in lf.decisions if isinstance(rec.get("id"), str)
        }
        for batch in lf.batches:
            findings += _check_batch(batch, by_id, lf.path)
    return findings


def _check_batch(
    batch: dict[str, Any], by_id: dict[Any, dict], rel: str
) -> list[Finding]:
    bid = batch.get("batch_id")
    loc = f"{rel}:batches.{bid}" if bid else rel
    findings: list[Finding] = []

    if not owner_shape_ok(batch.get("confirmed_by")):
        findings.append(
            _err(
                "DS3",
                f"batch {bid!r} has invalid confirmed_by {batch.get('confirmed_by')!r}",
                loc,
            )
        )

    # FR-023: a batch MUST record the evidence presented for it.
    if not isinstance(batch.get("evidence"), list) or not batch.get("evidence"):
        findings.append(
            _err("DS3", f"batch {bid!r} records no presented evidence", loc)
        )

    findings += _check_batch_members(batch, by_id, bid, loc)
    findings += _check_batch_excluded(batch, by_id, bid, loc)
    return findings


def _check_batch_members(
    batch: dict[str, Any], by_id: dict[Any, dict], bid: object, loc: str
) -> list[Finding]:
    members = batch.get("members")
    if not isinstance(members, list) or not members:
        return [_err("DS3", f"batch {bid!r} has no members", loc)]
    findings: list[Finding] = []
    for member_id in members:
        if not isinstance(member_id, str):
            findings.append(
                _err(
                    "DS3", f"batch {bid!r} member {member_id!r} is not a string id", loc
                )
            )
            continue
        rec = by_id.get(member_id)
        if rec is None:
            findings.append(
                _err("DS3", f"batch {bid!r} member {member_id!r} not found", loc)
            )
        elif is_critical(rec.get("decision_type")):
            findings.append(
                _err(
                    "DS3",
                    f"batch {bid!r} contains critical decision {member_id!r} "
                    f"(type {rec.get('decision_type')!r}); critical decisions are "
                    "never batch-approvable",
                    loc,
                )
            )
    return findings


def _check_batch_excluded(
    batch: dict[str, Any], by_id: dict[Any, dict], bid: object, loc: str
) -> list[Finding]:
    """FR-023: each excluded item must resolve to a decision that became an
    individual `pending` question."""
    excluded = batch.get("excluded")
    if excluded is None:
        return []
    if not isinstance(excluded, list):
        return [_err("DS3", f"batch {bid!r} excluded must be a list", loc)]
    findings: list[Finding] = []
    for ex_id in excluded:
        if not isinstance(ex_id, str):
            findings.append(
                _err("DS3", f"batch {bid!r} excluded {ex_id!r} is not a string id", loc)
            )
            continue
        rec = by_id.get(ex_id)
        if rec is None:
            findings.append(
                _err("DS3", f"batch {bid!r} excluded {ex_id!r} not found", loc)
            )
        elif rec.get("status") != "pending":
            findings.append(
                _err(
                    "DS3",
                    f"batch {bid!r} excluded {ex_id!r} must become an individual "
                    f"pending question, but its status is {rec.get('status')!r}",
                    loc,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# DS4 -- supersession integrity + no conflicting active records
# ---------------------------------------------------------------------------


@register("DS4", "decision supersession integrity and no scope conflicts")
def check_ds4(ctx: RuleContext) -> Iterable[Finding]:
    store = _store_for(ctx)
    findings: list[Finding] = []
    all_ids = {
        rec.get("id")
        for lf in store.files
        for rec in lf.decisions
        if isinstance(rec.get("id"), str)
    }
    for lf in store.files:
        for rec in lf.decisions:
            findings += _check_supersession_refs(rec, all_ids, lf.path)
        findings += _check_scope_conflicts(lf.decisions, lf.path)
    return findings


def _check_supersession_refs(
    rec: dict[str, Any], all_ids: set, rel: str
) -> list[Finding]:
    did = rec.get("id")
    loc = _loc(rel, did)
    findings: list[Finding] = []
    for key in ("supersedes", "superseded_by"):
        ref = rec.get(key)
        if ref is None:
            continue
        if not isinstance(ref, str):
            findings.append(
                _err("DS4", f"decision {did!r} {key} {ref!r} must be a string id", loc)
            )
        elif ref not in all_ids:
            findings.append(
                _err("DS4", f"decision {did!r} {key} {ref!r} does not resolve", loc)
            )
    if rec.get("status") == "superseded" and not rec.get("superseded_by"):
        findings.append(
            _err("DS4", f"superseded decision {did!r} has no superseded_by", loc)
        )
    return findings


def _check_scope_conflicts(decisions: tuple[dict, ...], rel: str) -> list[Finding]:
    """Two ACTIVE (non-terminal) records of the same type on the same scope key are
    a conflict to resolve by supersession. Uses the shared predicate so the gate
    reports the identical conflict set."""
    return [
        _err(
            "DS4",
            f"conflicting active {dtype} decisions on {key!r}: "
            f"{ids}; resolve by supersession",
            _loc(rel, ids[0]),
        )
        for dtype, key, ids in active_scope_conflicts(list(decisions))
    ]


# ---------------------------------------------------------------------------
# DS5 -- verdict-consistency store invariants
# ---------------------------------------------------------------------------


@register("DS5", "decision gate verdict consistency invariants")
def check_ds5(ctx: RuleContext) -> Iterable[Finding]:
    """Store-side invariant a verdict rests on: an ``approved`` critical decision
    must carry the full, valid approval DS2 requires (so a ``pass`` verdict can
    never rest on an approval with no evidence). The verdict computation itself
    lives in :mod:`seshat.decision_gate`; this rule guards the store precondition
    that a pass cites evidence."""
    store = _store_for(ctx)
    return [
        _err(
            "DS5",
            f"approved decision {rec.get('id')!r} has no evidence; "
            "a pass may never rest on an approval without evidence",
            _loc(lf.path, rec.get("id")),
        )
        for lf in store.files
        for rec in lf.decisions
        if _approved_without_evidence(rec)
    ]


def _approved_without_evidence(rec: dict[str, Any]) -> bool:
    if rec.get("status") != "approved":
        return False
    approval = rec.get("approval")
    evidence = approval.get("evidence") if isinstance(approval, dict) else None
    return not evidence
