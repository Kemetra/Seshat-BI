"""`seshat readiness-diff` handler: readiness state compared across two revisions.

The comparison MATH lives in :mod:`seshat.readiness_diff` and never touches git.
This handler is the revision-reading seam around it -- the same split as
``profile.py`` (math behind a QueryRunner) and ``file_profile.py`` (math behind a
FrameReader).

Content is read from the two REVISIONS (``git show <rev>:<path>``), never from the
worktree, for the same reason ``portfolio_watch`` does: the answer must follow what
a reviewer would fetch, so a local scribble can neither manufacture nor revoke a
reported change.

``yaml`` is imported LAZILY inside the loader (as rule A3 does), so the
stdlib-only ``check`` core never acquires it at import time.

Exit code is 0 for any successfully rendered comparison -- INCLUDING one that
reports a regression. This is a read-only reporting surface, not a gate: it adds
no `blocking_reasons[]` entry and grants no approval. Only a boundary failure
(bad revision, unsafe range, unreadable repo) exits 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_STATUS_FILE = "readiness-status.yaml"


def _table_of(path: str) -> str:
    """``mappings/<table>/readiness-status.yaml`` -> ``<table>``."""
    parts = path.split("/")
    return parts[1] if len(parts) > 2 else path


def _load_at_revision(repo: Path, revision: str) -> dict[str, object]:
    """``{table -> parsed readiness document}`` as COMMITTED at ``revision``.

    A file that is present but unparseable maps to ``None``; the diff core treats
    that as "contributes nothing" rather than aborting, so one malformed table
    cannot blind a reviewer to every other table's changes.
    """
    import yaml  # lazy: keeps the stdlib-only check core free of a YAML dependency

    from seshat.gitutil import git_output

    listing = git_output(
        repo, "ls-tree", "-r", "--name-only", revision, "--", "mappings"
    )
    documents: dict[str, object] = {}
    for path in listing.splitlines():
        if not path.endswith(f"/{_STATUS_FILE}"):
            continue
        raw = git_output(repo, "show", f"{revision}:{path}")
        try:
            documents[_table_of(path)] = yaml.safe_load(raw)
        except yaml.YAMLError:
            documents[_table_of(path)] = None
    return documents


def _resolve_revisions(args: argparse.Namespace) -> tuple[str, str] | None:
    """The (base, head) pair from either the range form or --base/--head.

    Exactly one form is accepted: silently preferring one over the other would
    make a caller who passed both believe something they did not ask for.
    """
    raw_range = getattr(args, "range", None)
    base = getattr(args, "base", None)
    head = getattr(args, "head", None)

    if raw_range:
        if base or head:
            print(
                "error: pass either BASE..HEAD or the --base/--head pair, not both.",
                file=sys.stderr,
            )
            return None
        return _split_range(raw_range)

    if not base or not head:
        print(
            "error: give a range (BASE..HEAD) or both --base and --head.",
            file=sys.stderr,
        )
        return None
    return base, head


def _split_range(raw_range: str) -> tuple[str, str] | None:
    """Validate and split ``BASE..HEAD``; ``None`` after printing the error.

    ``validate_commit_range`` is the shipped safety check -- the expression is
    refused here rather than handed to git.
    """
    from seshat.gitutil import validate_commit_range

    try:
        validate_commit_range(raw_range)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None
    if ".." not in raw_range:
        print(
            f"error: {raw_range!r} is not a range; expected BASE..HEAD.",
            file=sys.stderr,
        )
        return None
    left, _, right = raw_range.partition("..")
    if not left or not right:
        print(
            f"error: {raw_range!r} is missing a side; expected BASE..HEAD.",
            file=sys.stderr,
        )
        return None
    return left, right


def _render_json(result: object, base: str, head: str) -> str:
    return json.dumps(
        {
            "base": base,
            "head": head,
            "has_regression": result.has_regression,
            "tables_added": list(result.tables_added),
            "tables_removed": list(result.tables_removed),
            "current_stage_changes": [
                {
                    "table": move.table,
                    "base_stage": move.base_stage,
                    "head_stage": move.head_stage,
                    "is_regression": move.is_regression,
                }
                for move in result.current_stage_changes
            ],
            "stage_changes": [
                {
                    "table": change.table,
                    "stage": change.stage,
                    "base_status": change.base_status,
                    "head_status": change.head_status,
                    "is_regression": change.is_regression,
                }
                for change in result.stage_changes
            ],
            "blockers_added": [list(item) for item in result.blockers_added],
            "blockers_removed": [list(item) for item in result.blockers_removed],
            "approvals_added": [
                {"table": a.table, "stage": a.stage, "owner": a.owner, "at": a.at}
                for a in result.approvals_added
            ],
            "approvals_removed": [
                {"table": a.table, "stage": a.stage, "owner": a.owner, "at": a.at}
                for a in result.approvals_removed
            ],
            "note": (
                "read-only projection of committed readiness state; it grants no "
                "approval and never sets a readiness stage"
            ),
        },
        indent=2,
    )


def _tag(is_regression: bool) -> str:
    return "regression" if is_regression else "change"


def _table_lines(result: object, head: str) -> list[str]:
    return [
        f"[table-] {table} (no readiness file at {head})"
        for table in result.tables_removed
    ] + [
        f"[table+] {table} (new readiness file at {head})"
        for table in result.tables_added
    ]


def _stage_lines(result: object) -> list[str]:
    moves = [
        f"[{_tag(move.is_regression)}] {move.table} current_stage: "
        f"{move.base_stage} -> {move.head_stage}"
        for move in result.current_stage_changes
    ]
    statuses = [
        f"[{_tag(change.is_regression)}] {change.table} {change.stage}: "
        f"{change.base_status} -> {change.head_status}"
        for change in result.stage_changes
    ]
    return moves + statuses


def _blocker_lines(result: object) -> list[str]:
    return [
        f"[blocker+] {table} {stage}: {reason}"
        for table, stage, reason in result.blockers_added
    ] + [
        f"[blocker-] {table} {stage}: {reason}"
        for table, stage, reason in result.blockers_removed
    ]


def _approval_lines(result: object) -> list[str]:
    """Added approvals, then REMOVED ones tagged as regressions.

    A lost approval is called out as a regression: the evidence a stage rested on
    is gone, and a reviewer must not merge that away unnoticed.
    """
    return [
        f"[approval+] {a.table} {a.stage} ({a.owner}, {a.at})"
        for a in result.approvals_added
    ] + [
        f"[regression] approval REMOVED: {a.table} {a.stage} ({a.owner}, {a.at})"
        for a in result.approvals_removed
    ]


def _body_lines(result: object, head: str) -> list[str]:
    """The change body, or the single no-change line."""
    if result.is_empty:
        return ["no readiness change between these revisions."]
    return (
        _table_lines(result, head)
        + _stage_lines(result)
        + _blocker_lines(result)
        + _approval_lines(result)
    )


def _render_text(result: object, base: str, head: str) -> str:
    lines = [f"readiness-diff: {base}..{head}"]
    lines += _body_lines(result, head)
    lines.append("")
    if result.has_regression:
        lines.append(
            "REGRESSION present: committed readiness moved backwards. This is "
            "evidence for the human review, not a gate."
        )
    lines.append(
        "this is a read-only projection of committed state; it grants no approval "
        "and never sets a readiness stage."
    )
    return "\n".join(lines)


def readiness_diff_main(args: argparse.Namespace) -> int:
    """Compare committed readiness state between two revisions."""
    from seshat.readiness_diff import diff_readiness

    revisions = _resolve_revisions(args)
    if revisions is None:
        return 1
    base, head = revisions

    repo = Path(getattr(args, "repo", "."))
    try:
        base_docs = _load_at_revision(repo, base)
        head_docs = _load_at_revision(repo, head)
    except RuntimeError as exc:
        print(
            f"error: could not read a git revision ({exc}). Both revisions must "
            "exist in this repository.",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        print(f"error: could not run git in {repo}: {exc}", file=sys.stderr)
        return 1

    result = diff_readiness(base_docs, head_docs)
    if getattr(args, "output_format", "text") == "json":
        print(_render_json(result, base, head))
    else:
        print(_render_text(result, base, head))
    return 0
