"""``seshat reset`` handler (#433): plan -> confirm -> execute -> verify.

Exit policy: 0 on success / dry-run / clean no-op; 1 on a mid-execution
failure or residual-state verification finding; 2 on a documented refusal
(unsafe table, path escape, unreadable shared file, missing confirmation,
declined confirmation). Refusals always carry a NAMED reason. Output is
ASCII-only and never a numeric score; the prefix follows the invoked brand
(``cli._prog``, #402).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class _Console:
    """How this invocation speaks: brand prefix + output format."""

    prog: str
    output_format: str

    @property
    def as_json(self) -> bool:
        return self.output_format == "json"


def _plan_document(plan: Any, outcome: str, reason: str | None) -> dict[str, Any]:
    return {
        "table": plan.table if plan is not None else None,
        "outcome": outcome,
        "reason": reason,
        "remove_dirs": list(plan.remove_dirs) if plan is not None else [],
        "remove_files": list(plan.remove_files) if plan is not None else [],
        "shared_file_edits": [
            {
                "path": edit.path,
                "removed_rows": list(edit.removed_rows),
                "remove_file": edit.remove_file,
            }
            for edit in (plan.shared_edits if plan is not None else ())
        ],
        "preserved": list(plan.preserved) if plan is not None else [],
        "staged": [],
        "staging_note": None,
        "verification_findings": [],
        "post_reset": None,
    }


def _bullets(rows: list[str], empty: str) -> list[str]:
    return rows or [empty]


def _edit_lines(shared_edits: Any) -> list[str]:
    if not shared_edits:
        return ["  (none)"]
    return [
        f"  - {edit.path} -- "
        f"{'remove file' if edit.remove_file else 'remove rows'}: "
        f"{', '.join(edit.removed_rows)}"
        for edit in shared_edits
    ]


def _render_plan_text(plan: Any, prog: str, repo: str) -> str:
    lines = [
        f"{prog} reset: plan for table '{plan.table}' (repo: {repo})",
        "removes (directories):",
    ]
    lines += _bullets([f"  - {rel}/" for rel in plan.remove_dirs], "  (none)")
    lines.append("removes (files):")
    lines += _bullets([f"  - {rel}" for rel in plan.remove_files], "  (none)")
    lines.append("shared-file edits (only this table's rows):")
    lines += _edit_lines(plan.shared_edits)
    lines.append("preserves:")
    lines += _bullets(
        [f"  - {rel} (bronze landing)" for rel in plan.preserved],
        "  (no bronze landing found)",
    )
    lines.append(
        "never touched: the live database; other tables' files; orchestration/dagster/"
    )
    return "\n".join(lines)


def _emit_refusal(console: _Console, reason: str, detail: str) -> int:
    if console.as_json:
        print(
            json.dumps(
                {"outcome": "refused", "reason": reason, "detail": detail},
                sort_keys=True,
            )
        )
    else:
        print(f"{console.prog} reset: refused ({reason}) -- {detail}", file=sys.stderr)
    return 2


def _emit_nothing_to_reset(console: _Console, plan: Any) -> int:
    if console.as_json:
        print(json.dumps(_plan_document(plan, "nothing_to_reset", None)))
    else:
        print(
            f"{console.prog} reset: nothing to reset -- no derived artifacts "
            f"found for table '{plan.table}'"
        )
    return 0


def _emit_dry_run(console: _Console, document: dict[str, Any], plan_text: str) -> int:
    if console.as_json:
        print(json.dumps(document, indent=2, sort_keys=True))
    else:
        print(plan_text)
        print(f"{console.prog} reset: dry run -- nothing was removed")
    return 0


def _refusal_detail(reason: str) -> str:
    if reason == "confirmation_required":
        return (
            "stdin is not interactive and --yes was not passed; refusing "
            "rather than hanging (pass --yes to confirm in automation)"
        )
    return "confirmation declined; nothing was removed"


def _confirmed(console: _Console, plan_text: str) -> str | None:
    """None when confirmed; else the named refusal reason."""
    if not console.as_json:
        print(plan_text)
    if not _stdin_is_interactive():
        return "confirmation_required"
    try:
        answer = input(
            f"{console.prog} reset: remove these paths and stage the deletions? [y/N] "
        )
    except EOFError:
        return "declined"
    return None if answer.strip().lower() in ("y", "yes") else "declined"


def _stdin_is_interactive() -> bool:
    """Fail closed rather than hang: without a real interactive stdin the
    confirmation cannot be asked, so the caller must pass --yes."""
    stdin = sys.stdin
    if stdin is None or stdin.closed:
        return False
    isatty = getattr(stdin, "isatty", None)
    try:
        return bool(isatty()) if callable(isatty) else False
    except (OSError, ValueError):
        return False


def _post_reset_state(repo: str, table: str) -> dict[str, Any]:
    from seshat.run_next import build_run_next_response

    response = build_run_next_response(Path(repo), table)
    return {"stage": response.get("stage"), "outcome": response.get("outcome")}


def _finish(console: _Console, document: dict[str, Any]) -> int:
    findings = document["verification_findings"]
    if console.as_json:
        print(json.dumps(document, indent=2, sort_keys=True))
    else:
        _print_result_text(console, document, findings)
    return 1 if findings else 0


def _print_result_text(
    console: _Console, document: dict[str, Any], findings: list[str]
) -> None:
    prog = console.prog
    removed_count = len(document["remove_dirs"]) + len(document["remove_files"])
    print(
        f"{prog} reset: table '{document['table']}' reset -- "
        f"{removed_count} path(s) removed, "
        f"{len(document['shared_file_edits'])} shared file(s) edited"
    )
    if document["staging_note"]:
        print(f"{prog} reset: note -- {document['staging_note']}")
    else:
        print(f"{prog} reset: deletions staged (safe for `{prog} check`)")
    post = document["post_reset"] or {}
    print(
        f"{prog} reset: `{prog} next --table {document['table']}` now reports "
        f"stage={post.get('stage')} outcome={post.get('outcome')}"
    )
    for finding in findings:
        print(f"{prog} reset: residual state -- {finding}", file=sys.stderr)


def _emit_execution_error(console: _Console, exc: Any) -> int:
    print(f"{console.prog} reset: error -- {exc}", file=sys.stderr)
    for rel in exc.removed:
        print(f"{console.prog} reset: already removed -- {rel}", file=sys.stderr)
    return 1


def _execute_and_finish(
    console: _Console, args: argparse.Namespace, plan: Any, document: dict[str, Any]
) -> int:
    from seshat.reset import (
        ResetError,
        ResetExecutionError,
        execute_reset,
        verify_reset,
    )

    try:
        report = execute_reset(args.repo, plan)
    except ResetError as exc:
        return _emit_refusal(console, exc.reason, str(exc))
    except ResetExecutionError as exc:
        return _emit_execution_error(console, exc)

    document["outcome"] = "reset"
    document["staged"] = list(report.staged)
    document["staging_note"] = report.staging_note
    document["verification_findings"] = list(verify_reset(args.repo, plan.table, plan))
    document["post_reset"] = _post_reset_state(args.repo, plan.table)
    return _finish(console, document)


def reset_main(args: argparse.Namespace) -> int:
    from seshat import cli
    from seshat.reset import ResetError, plan_reset

    console = _Console(cli._prog(args), getattr(args, "output_format", "text"))
    try:
        plan = plan_reset(args.repo, args.table)
    except ResetError as exc:
        return _emit_refusal(console, exc.reason, str(exc))

    if plan.is_empty:
        return _emit_nothing_to_reset(console, plan)

    document = _plan_document(plan, "plan", None)
    plan_text = _render_plan_text(plan, console.prog, args.repo)
    if args.dry_run:
        return _emit_dry_run(console, document, plan_text)

    if not args.yes:
        refusal = _confirmed(console, plan_text)
        if refusal is not None:
            return _emit_refusal(console, refusal, _refusal_detail(refusal))

    return _execute_and_finish(console, args, plan, document)


__all__ = ["reset_main"]
