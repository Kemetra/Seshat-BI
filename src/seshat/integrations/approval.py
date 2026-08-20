"""The committed provisioning-approval gate (spec 154, issue #671).

Installing external software is a named-human decision. Before this module,
`seshat integrations setup --apply --yes` treated a CLI flag as that decision:
an agent constructing its own ``Namespace(apply=True, yes=True)`` obtained
authority no human granted. A precondition the caller supplies is not a gate.

So authority is read from committed repository state instead:

* the path is FIXED in code as :data:`PROVISIONING_APPROVALS_RELPATH` -- no flag,
  environment variable, or argument can redirect it;
* it is read at HEAD via :func:`seshat.gitstate.committed_text`, gated on
  :func:`seshat.gitstate.is_tracked_and_clean`, so an uncommitted edit is
  invisible here (the defect fixed in ``pbi_mcp_adapter/gate.py`` after bug #334,
  where a worktree-reading gate let the agent author its own approval);
* shape validity is DELEGATED to
  :func:`seshat.rules.readiness_status.approval_is_shape_valid` -- the single
  definition of "named human" across every gate-deciding surface (issue #487).
  It is not re-implemented here.

:func:`evaluate` deliberately takes no boolean: its only inputs are the repo root
and the components being requested, both derived by the caller's own machinery
rather than asserted by the caller.

Note that shape validity is necessary but NOT sufficient. The canonical validator
accepts any of the five authority classes, so an ``analyst`` approval is
shape-valid; provisioning requires ``governance`` specifically (FR-004a), and that
check lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from seshat.gitstate import committed_text, is_tracked_and_clean
from seshat.rules.readiness_status import approval_is_shape_valid

# Fixed in code on purpose: a redirectable path would let the requesting party
# choose the file that authorizes it. See contracts/pbi-mcp-write-targets.yaml's
# header for the same argument applied to the Power BI write allowlist.
PROVISIONING_APPROVALS_RELPATH = "contracts/provisioning-approvals.yaml"

# The stage token a provisioning approval is keyed by. `stage` is a keying string
# in the canonical shape, not a readiness-spine coupling.
PROVISIONING_STAGE = "provisioning"

# The one authority class that may authorize external environment/tool changes.
# NOT widened: this feature adds no sixth class to the closed set (FR-004a).
PROVISIONING_AUTHORITY = "governance"


@dataclass(frozen=True)
class ApprovalVerdict:
    """Why provisioning may or may not proceed.

    ``reason`` is categorical so callers can branch and tests can assert without
    matching prose. ``next_action`` is the human-readable remedy.
    """

    authorized: bool
    reason: str
    next_action: str
    owner: str = ""


def _record(relpath: str) -> str:
    return f"record a provisioning approval in {relpath}"


def _shape_hint() -> str:
    return (
        'a row with stage: provisioning, owner: "<Person Name> (governance)", '
        "at: <YYYY-MM-DD>, and components: [<ids>]"
    )


def _authority_class(owner: str) -> str:
    """The class token inside ``Name (class)``, normalized, or "" if absent.

    Shape validity already proved the parenthesised form is present and the class
    is one of the known set; this only has to say WHICH.
    """
    if "(" not in owner or not owner.rstrip().endswith(")"):
        return ""
    inner = owner[owner.rindex("(") + 1 : owner.rstrip().rindex(")")]
    return inner.strip().lower().replace("-", "_").replace(" ", "_")


def _rows(data: dict) -> list[dict]:
    rows = data.get("approvals")
    if not isinstance(rows, list):
        return []
    return [
        row
        for row in rows
        if isinstance(row, dict) and row.get("stage") == PROVISIONING_STAGE
    ]


def _components(row: dict) -> frozenset[str]:
    declared = row.get("components")
    if not isinstance(declared, list):
        return frozenset()
    return frozenset(str(item) for item in declared)


def _load_committed(repo_root: Path) -> tuple[dict | None, str | None]:
    """``(data, refusal_reason)`` -- exactly one of the two is set.

    ``yaml.safe_load`` is wrapped deliberately: ``dagster_adapter/gate.py`` calls
    it unguarded, so a malformed record raises out of the reader instead of
    becoming a typed refusal. Absent, unparseable and unreadable all fail closed,
    and none is reported in a way that could be mistaken for a pass.
    """
    if not is_tracked_and_clean(repo_root, PROVISIONING_APPROVALS_RELPATH):
        if not (repo_root / PROVISIONING_APPROVALS_RELPATH).exists():
            return None, "absent"
        return None, "uncommitted"
    text = committed_text(repo_root, PROVISIONING_APPROVALS_RELPATH)
    if text is None:
        return None, "absent"

    import yaml  # lazy: keeps module import dependency-light

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None, "unparseable"
    if not isinstance(data, dict):
        return None, "unparseable"
    return data, None


def evaluate(repo_root: Path, components: tuple[str, ...]) -> ApprovalVerdict:
    """Whether a committed named-human approval authorizes provisioning ``components``.

    Returns ``authorized=True`` only when ONE committed row is shape-valid, is
    keyed to the provisioning stage, carries the ``governance`` authority class,
    is not revoked, and names every requested component. Two narrower rows never
    combine into a wider authority: that would grant an authority no human
    recorded (the ``_authorizing_approval`` rule from the Power BI write gate).

    Every other outcome refuses. There is no code path in which a caller-supplied
    value produces ``authorized=True``.
    """
    relpath = PROVISIONING_APPROVALS_RELPATH
    data, refusal = _load_committed(repo_root)
    if refusal is not None:
        remedy = {
            "absent": _record(relpath),
            "uncommitted": (
                f"commit {relpath} -- the gate reads HEAD, so an uncommitted "
                "approval authorizes nothing"
            ),
            "unparseable": f"repair the YAML in {relpath}",
        }[refusal]
        return ApprovalVerdict(False, refusal, remedy)

    assert data is not None  # the refusal branch above covers the None case
    rows = _rows(data)
    if not rows:
        return ApprovalVerdict(False, "absent", _record(relpath))

    requested = frozenset(components)
    shape_valid = [row for row in rows if approval_is_shape_valid(row)]
    if not shape_valid:
        return ApprovalVerdict(
            False,
            "invalid_shape",
            f"correct the approval in {relpath}: {_shape_hint()}",
        )

    governed = [
        row
        for row in shape_valid
        if _authority_class(str(row.get("owner", ""))) == PROVISIONING_AUTHORITY
    ]
    if not governed:
        return ApprovalVerdict(
            False,
            "wrong_authority",
            (
                f"provisioning requires the {PROVISIONING_AUTHORITY} authority "
                f"class in {relpath}; another class cannot authorize installing "
                "external software"
            ),
        )

    covering = [row for row in governed if requested <= _components(row)]
    if not covering:
        live = [row for row in governed if not row.get("revoked")]
        if not live:
            return ApprovalVerdict(
                False,
                "revoked",
                f"the approval in {relpath} was revoked; record a new one",
            )
        approved = sorted(set().union(*(_components(row) for row in live)))
        return ApprovalVerdict(
            False,
            "scope_mismatch",
            (
                f"requested {sorted(requested)} but the committed approval covers "
                f"{approved}; a new approval must name every requested component"
            ),
        )

    live_covering = [row for row in covering if not row.get("revoked")]
    if not live_covering:
        return ApprovalVerdict(
            False,
            "revoked",
            f"the approval in {relpath} was revoked; record a new one",
        )

    winner = live_covering[0]
    return ApprovalVerdict(
        True,
        "authorized",
        "",
        owner=str(winner.get("owner", "")),
    )
