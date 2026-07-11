"""Read-only Personal-Data-Touch Notice composer (spec 114).

For ONE table, compose a per-column PII-disclosure notice from the committed
``mappings/<table>/source-map.yaml`` ONLY. One disclosure sentence per
``pii: true`` column, echoing the committed ``pii`` flag + ``decision`` and the
recorded governance disposition VERBATIM; an explicit GAP for any ``pii: true``
column whose disposition is not recorded.

Scope wall (the load-bearing constraints):
- Renders NO publish-safety verdict of its own; the only evaluative text is a
  verbatim, attributed echo of a committed disposition string.
- A KEPT pii:true column joins its governance disposition by an EXACT id-match on
  the column's ``deviation_ref`` field to ``defaults.deviations[].id`` (ratify
  OPEN-2). NEVER by scanning deviation prose. A kept pii:true column with no
  (or an unmatched) ``deviation_ref`` is UNDECIDED -> GAP, never a guess.
- Emits NO score/count (hard rule #9); adds NO gate; opens no DB/network.
- Reads ONLY source-map.yaml; writes ONLY ``mappings/<table>/pii-touch-notice.md``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# The composer NEVER authors a clearance verdict ("safe"/"cleared"/etc.) in its
# own voice -- the only evaluative text is a verbatim, attributed echo of a
# committed disposition. That invariant is enforced mechanically by the verifier
# (tests/unit/test_pii_notice.py, V3), which owns the closed clearance denylist.


def _load_yaml_mapping(path: Path) -> dict[str, Any] | None:
    """Load a YAML mapping; None on any read/parse failure. Mirrors the
    ``blocker_explainer._load_yaml_mapping`` idiom (utf-8-sig tolerates a BOM on
    input; output stays UTF-8 no BOM)."""
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _deviation_reason_by_id(data: dict[str, Any], ref: str) -> str | None:
    """The ``reason`` of the ``defaults.deviations[]`` entry whose ``id`` EXACTLY
    equals ``ref`` (ratify OPEN-2). None when no id matches -- never a prose
    scan, never a best-effort guess."""
    defaults = data.get("defaults")
    if not isinstance(defaults, dict):
        return None
    deviations = defaults.get("deviations")
    if not isinstance(deviations, list):
        return None
    for dev in deviations:
        if isinstance(dev, dict) and dev.get("id") == ref:
            reason = dev.get("reason")
            return reason if isinstance(reason, str) and reason else None
    return None


def _drop_finding(column: str, col: dict[str, Any]) -> dict[str, Any]:
    """A dropped pii:true column: its own ``reason`` is the disposition."""
    reason = col.get("reason")
    disposition = reason if isinstance(reason, str) and reason else None
    return {
        "column": column,
        "decision": "drop",
        "state": "decided_dropped" if disposition else "undecided",
        "disposition": disposition,
        "disposition_source": f"columns[{column}].reason" if disposition else None,
    }


def _keep_finding(
    column: str, col: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """A kept pii:true column: disposition is the deviation whose id EXACTLY
    matches ``deviation_ref``. No match -> undecided (never a prose guess)."""
    ref = col.get("deviation_ref")
    disposition = (
        _deviation_reason_by_id(data, ref) if isinstance(ref, str) and ref else None
    )
    return {
        "column": column,
        "decision": "keep",
        "state": "decided_kept" if disposition else "undecided",
        "disposition": disposition,
        "disposition_source": (
            f"defaults.deviations[{ref}].reason" if disposition else None
        ),
    }


def _conflicting_columns(columns: list[Any]) -> set[str]:
    """source_names that appear with BOTH a keep and a drop decision within the
    same file -- an intra-file contradiction the notice must GAP (FR-010), never
    silently resolve. Returns the set of contradicted names."""
    decisions: dict[str, set[str]] = {}
    for col in columns:
        if not isinstance(col, dict):
            continue
        name = col.get("source_name")
        decision = col.get("decision")
        if isinstance(name, str) and isinstance(decision, str):
            decisions.setdefault(name, set()).add(decision)
    return {name for name, ds in decisions.items() if {"keep", "drop"} <= ds}


def _inconsistent_finding(column: str) -> dict[str, Any]:
    """A pii:true column with contradictory decisions in the same file (FR-010).
    Rendered as a GAP naming both in-file loci; never a silent pick."""
    return {
        "column": column,
        "decision": "keep/drop conflict",
        "state": "inconsistent",
        "disposition": None,
        "disposition_source": f"columns[{column}] (both keep and drop entries)",
    }


def _finding_for_column(
    col: dict[str, Any], data: dict[str, Any], conflicts: set[str]
) -> dict[str, Any]:
    """Resolve one pii:true column to a finding (data-model.md).

    A source_name with contradictory decisions in the same file -> inconsistent
    (GAP, FR-010). Else drop -> decided_dropped (own reason); keep ->
    decided_kept IFF a deviation_ref exactly matches a deviation id carrying a
    reason, else undecided; any other decision -> undecided (never a guess).
    """
    column = str(col.get("source_name", ""))
    if column in conflicts:
        return _inconsistent_finding(column)
    decision = col.get("decision")
    if decision == "drop":
        return _drop_finding(column, col)
    if decision == "keep":
        return _keep_finding(column, col, data)
    return {
        "column": column,
        "decision": decision if isinstance(decision, str) else None,
        "state": "undecided",
        "disposition": None,
        "disposition_source": None,
    }


def build_pii_notice(repo_root: Path | str, table: str) -> dict[str, Any]:
    """Compose the PII-notice model for one table from its committed source-map.

    Reads ``<repo>/mappings/<table>/source-map.yaml`` ONLY. Returns the notice
    dict (never writes). ``document_gap`` is set when the source-map is
    missing/unreadable or carries no columns block.
    """
    root = Path(repo_root)
    source_path = f"mappings/{table}/source-map.yaml"
    data = _load_yaml_mapping(root / "mappings" / table / "source-map.yaml")

    if data is None:
        return {
            "table": table,
            "source_path": source_path,
            "findings": [],
            "no_pii": False,
            "document_gap": (
                f"source-map.yaml missing or unreadable (checked: {source_path})"
            ),
            "read_only_proof": True,
        }

    columns = data.get("columns")
    if not isinstance(columns, list) or not columns:
        return {
            "table": table,
            "source_path": source_path,
            "findings": [],
            "no_pii": False,
            "document_gap": (
                f"source-map.yaml has no columns block (checked: {source_path})"
            ),
            "read_only_proof": True,
        }

    conflicts = _conflicting_columns(columns)
    findings = [
        _finding_for_column(col, data, conflicts)
        for col in columns
        if isinstance(col, dict) and col.get("pii") is True
    ]

    return {
        "table": table,
        "source_path": source_path,
        "findings": findings,
        "no_pii": len(findings) == 0,
        "document_gap": None,
        "read_only_proof": True,
    }


def _render_finding(finding: dict[str, Any], source_path: str) -> str:
    """One disclosure or GAP line for a finding (ASCII, verbatim disposition)."""
    column = finding["column"]
    state = finding["state"]
    if state == "decided_kept":
        return (
            f"- {column} -- flagged pii:true, decision:keep. Recorded disposition: "
            f'"{finding["disposition"]}" '
            f"({source_path}, {finding['disposition_source']})."
        )
    if state == "decided_dropped":
        return (
            f"- {column} -- flagged pii:true, decision:drop. Recorded reason: "
            f'"{finding["disposition"]}" '
            f"({source_path}, {finding['disposition_source']})."
        )
    if state == "inconsistent":
        # FR-010: contradictory decisions in the same file -> GAP naming both
        # loci; never a silent pick, never implied clearance.
        return (
            f"- GAP: {column} -- pii:true with CONTRADICTORY decisions "
            f"(checked: {source_path} {finding['disposition_source']}). "
            f"This column is NOT cleared; the keep/drop conflict must be resolved."
        )
    # undecided -> GAP, always "NOT cleared", never a clearance token.
    return (
        f"- GAP: {column} -- pii:true with NO recorded governance disposition "
        f"(checked: {source_path} columns[{column}], defaults.deviations). "
        f"This column is NOT cleared; a named human decision is not recorded."
    )


def _header_lines(table: str, source_path: str) -> list[str]:
    return [
        f"# Personal-Data-Touch Notice -- {table}",
        "",
        f"Source: {source_path}",
        "This notice echoes committed PII flags and recorded governance dispositions.",
        "It records no new judgment, grants no approval, and moves no stage.",
        "",
    ]


_GAP_STATES = frozenset({"undecided", "inconsistent"})


def _flagged_column_lines(notice: dict[str, Any], source_path: str) -> list[str]:
    """The PII-flagged-columns section body: decided disclosure lines, then a
    Gaps section for undecided/inconsistent ones. Assumes >=1 pii:true column."""
    findings = notice["findings"]
    decided = [f for f in findings if f["state"] not in _GAP_STATES]
    gaps = [f for f in findings if f["state"] in _GAP_STATES]

    lines = [_render_finding(f, source_path) for f in decided]
    if not decided:
        lines.append("No PII-flagged column has a recorded decision yet.")
    if gaps:
        lines += ["", "## Gaps", ""]
        lines += [_render_finding(f, source_path) for f in gaps]
    return lines


def render_markdown(notice: dict[str, Any]) -> str:
    """Render the notice model to the ASCII markdown notice body (UTF-8 no BOM)."""
    source_path = notice["source_path"]
    lines = _header_lines(notice["table"], source_path)

    if notice["document_gap"] is not None:
        lines.append(
            f"GAP: document -- {notice['document_gap']}. "
            "No PII finding could be composed."
        )
        return "\n".join(lines) + "\n"

    lines += ["## PII-flagged columns", ""]
    if notice["no_pii"]:
        lines.append(
            "No column in this table is flagged as personal data (pii:true) "
            "in source-map.yaml."
        )
        return "\n".join(lines) + "\n"

    lines += _flagged_column_lines(notice, source_path)

    return "\n".join(lines) + "\n"
