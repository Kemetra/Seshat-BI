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
import posixpath
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path, PurePosixPath

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


def _is_report_file(rel: str) -> bool:
    """Report-side files X-Ray reads: PBIR definition JSON + the .pbir manifest.

    ``definition.pbir`` sits BESIDE ``definition/`` (note: no trailing slash),
    so a ``".Report/definition/"`` filter missed it -- and with it the
    ``datasetReference`` that resolves report ownership.
    """
    if ".Report/" not in rel:
        return False
    return rel.endswith(".pbir") or (
        ".Report/definition/" in rel and rel.endswith(".json")
    )


def _report_files(root: Path) -> list[tuple[str, str]]:
    """(path, text) for every committed report-definition file X-Ray reads."""
    ctx = build_context(root)
    out: list[tuple[str, str]] = []
    for rel in ctx.tracked_files:
        if is_test_path(rel) or not _is_report_file(rel):
            continue
        text = read_tracked_text(root / Path(rel), encoding="utf-8-sig")
        if text is not None:
            out.append((rel, text))
    return out


def _model_label(model_files: list[tuple[str, str]]) -> str:
    return ", ".join(_by_model(model_files))


def _by_model(
    model_files: list[tuple[str, str]],
) -> dict[str, list[tuple[str, str]]]:
    """Group model files by their ``*.SemanticModel`` directory, sorted.

    Auditing every model through ONE graph let identically-named tables,
    columns, and measures from unrelated models resolve across each other and
    overwrite the graph's name-keyed maps (PR #550 review). Each model gets
    its own graph.
    """
    grouped: dict[str, list[tuple[str, str]]] = {}
    for path, text in model_files:
        grouped.setdefault(path.split("/definition/")[0], []).append((path, text))
    return {key: grouped[key] for key in sorted(grouped)}


def _report_root(path: str) -> str:
    """The ``<X>.Report`` directory a report file lives under."""
    marker = ".Report/"
    index = path.find(marker)
    return path[: index + len(marker) - 1] if index != -1 else path


def _declared_model(
    report_root: str, report_files: list[tuple[str, str]]
) -> str | None:
    """The model directory a report's ``definition.pbir`` points at, or None.

    PBIR associates a report with its model through
    ``datasetReference.byPath.path`` (a path relative to the report folder), so
    a report whose DIRECTORY STEM differs from the model's is still owned by it.
    Pairing on stem alone discarded such a report's bindings entirely and then
    reported its bound fields as unreferenced (PR #550 review).
    """
    for path, text in report_files:
        if path != f"{report_root}/definition.pbir":
            continue
        try:
            reference = json.loads(text)
        except ValueError:
            return None
        by_path = reference.get("datasetReference", {}).get("byPath", {})
        declared = by_path.get("path") if isinstance(by_path, dict) else None
        if not isinstance(declared, str):
            return None
        # Relative to the report folder; normalize away "../" segments.
        return PurePosixPath(
            posixpath.normpath(posixpath.join(report_root, declared))
        ).as_posix()
    return None


def _paired_report(
    model_dir: str, report_files: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    """The report files belonging to ``model_dir``.

    Ownership comes from each report's ``definition.pbir`` when it declares one;
    otherwise it falls back to the PBIP stem convention (Power BI Desktop writes
    ``<Stem>.SemanticModel`` beside ``<Stem>.Report``). Bindings are never
    shared globally -- another model's report must not count as evidence that
    THIS model's column is used.
    """
    stem_prefix = f"{model_dir.removesuffix('.SemanticModel')}.Report/"

    def owns(path: str) -> bool:
        declared = _declared_model(_report_root(path), report_files)
        if declared is not None:
            return declared == model_dir  # an explicit declaration is authoritative
        return path.startswith(stem_prefix)

    return [(path, text) for path, text in report_files if owns(path)]


def _no_model_payload() -> dict[str, object]:
    blocker = _blocker(
        "XR001",
        "no committed PBIP semantic model found",
        "commit a *.SemanticModel/definition/ folder or run from the repo root",
    )
    return audit_payload((), model="", report_scanned=False, blockers=(blocker,))


def _qualified(finding, model_dir: str, qualify: bool):
    """Prefix a finding's locator with its model dir when >1 model was audited."""
    if not qualify:
        return finding
    return replace(finding, locator=f"{model_dir}: {finding.locator}")


def xray_main(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    model_files = _model_files(root)
    if not model_files:
        return _emit(_no_model_payload(), args.output_format, render_text_audit)
    report_files = _report_files(root)
    grouped = _by_model(model_files)
    qualify = len(grouped) > 1
    findings = []
    scanned: list[bool] = []
    for model_dir, files in grouped.items():
        owned = _paired_report(model_dir, report_files)
        # The .pbir is an ownership manifest, not binding evidence: excluding it
        # keeps report_scanned meaning "actual report content was read".
        bindings = read_bindings([(p, t) for p, t in owned if not p.endswith(".pbir")])
        scanned.append(bindings.report_scanned)
        findings.extend(
            _qualified(f, model_dir, qualify)
            for f in run_audit(build_graph(files), bindings)
        )
    payload = audit_payload(
        findings,
        model=", ".join(grouped),
        # Conservative AND: one model's scanned report says nothing about
        # another's, so the degraded wording applies unless ALL were scanned.
        report_scanned=all(scanned),
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
