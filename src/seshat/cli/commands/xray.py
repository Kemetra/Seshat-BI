"""``seshat xray`` and ``seshat model-diff`` -- read-only PBIP model verbs.

Advisory contract: findings NEVER change the exit code. Exit 0 means the verb
ran to completion (however many findings); exit 3 means it could not run and
the payload carries ``{code, message, recovery}`` blockers (the ``seshat
analyze`` envelope shape). The diff base side is read with ``git show`` --
no checkout, no working-tree mutation.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path

from ...core import is_test_path, read_tracked_text
from ...gitutil import git_output
from ...runner import build_context
from ...tmdl import iter_model_files
from ...xray.audit import run_audit
from ...xray.bindings import read_bindings
from ...xray.diff import diff_models
from ...xray.graph import build_graph
from ...xray.render import (
    audit_payload,
    diff_payload,
    render_text_audit,
    render_text_diff,
)

_EXIT = {"completed": 0, "blocked": 3}


def _emit(payload: Mapping[str, object], output_format: str, render) -> int:
    if output_format == "json":
        # Compact separators are load-bearing: the live-repo integration test
        # matches '"outcome":"completed"' with no space.
        print(
            json.dumps(
                dict(payload),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    else:
        print(render(payload))
    return _EXIT[str(payload["outcome"])]


def _blocker(code: str, message: str, recovery: str) -> dict[str, str]:
    return {"code": code, "message": message, "recovery": recovery}


def _model_files(root: Path) -> list[tuple[str, str]]:
    ctx = build_context(root)
    return list(iter_model_files(ctx, ".tmdl"))


def _report_files(root: Path) -> list[tuple[str, str]]:
    """(path, text) for every committed report-definition JSON file."""
    ctx = build_context(root)
    out: list[tuple[str, str]] = []
    for rel in ctx.tracked_files:
        if is_test_path(rel):
            continue
        if ".Report/definition/" not in rel or not rel.endswith(".json"):
            continue
        text = read_tracked_text(root / Path(rel), encoding="utf-8-sig")
        if text is not None:
            out.append((rel, text))
    return out


def _model_label(model_files: list[tuple[str, str]]) -> str:
    dirs = sorted({path.split("/definition/")[0] for path, _ in model_files})
    return ", ".join(dirs)


def _no_model_payload() -> dict[str, object]:
    blocker = _blocker(
        "XR001",
        "no committed PBIP semantic model found",
        "commit a *.SemanticModel/definition/ folder or run from the repo root",
    )
    return audit_payload((), model="", report_scanned=False, blockers=(blocker,))


def xray_main(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    model_files = _model_files(root)
    if not model_files:
        return _emit(_no_model_payload(), args.output_format, render_text_audit)
    graph = build_graph(model_files)
    bindings = read_bindings(_report_files(root))
    payload = audit_payload(
        run_audit(graph, bindings),
        model=_model_label(model_files),
        report_scanned=bindings.report_scanned,
    )
    return _emit(payload, args.output_format, render_text_audit)


def _base_model_files(root: Path, base: str) -> list[tuple[str, str]]:
    """Model files at ``base``, via git plumbing only (read-only).

    Raises RuntimeError (from ``git_output``) on an unresolvable ref.
    """
    listing = git_output(root, "ls-tree", "-r", "--name-only", base)
    out: list[tuple[str, str]] = []
    for rel in listing.splitlines():
        if is_test_path(rel) or ".SemanticModel/definition/" not in rel:
            continue
        if not rel.endswith(".tmdl"):
            continue
        out.append((rel, git_output(root, "show", f"{base}:{rel}")))
    return out


def model_diff_main(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    try:
        base_files = _base_model_files(root, args.base)
    except RuntimeError:
        blocker = _blocker(
            "XR002",
            f"base ref {args.base!r} could not be read",
            "pass a resolvable ref, e.g. --base origin/main",
        )
        payload = diff_payload((), base=args.base, blockers=(blocker,))
        return _emit(payload, args.output_format, render_text_diff)
    changes = diff_models(base_files, _model_files(root))
    payload = diff_payload(changes, base=args.base)
    return _emit(payload, args.output_format, render_text_diff)
