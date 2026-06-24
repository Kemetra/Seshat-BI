"""PBIR/JSON rule R1 (relative model reference). Replaces the M1.6 stub."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

_ABSOLUTE = re.compile(r"^(?:[A-Za-z]:|\\|/)")


def _iter_pbir_files(ctx: RuleContext) -> list[str]:
    # Skip committed test fixtures (tests/fixtures/pbir/*) — they deliberately
    # carry absolute / byConnection references to exercise R1 and are not the
    # live report. Same exemption as the TMDL/SQL/P1 file-scanning rules.
    return [
        p
        for p in ctx.tracked_files
        if p.endswith(".Report/definition.pbir") and not is_test_path(p)
    ]


@register("R1", "PBIR model reference must be relative")
def check_pbir_relative_reference(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in _iter_pbir_files(ctx):
        path = ctx.repo_root / rel
        with path.open(encoding="utf-8-sig") as fh:
            doc: Any = json.load(fh)
        ref = doc.get("datasetReference", {}) if isinstance(doc, dict) else {}
        if "byConnection" in ref:
            findings.append(
                Finding(
                    rule_id="R1",
                    severity=Severity.ERROR,
                    message=(
                        "PBIR uses byConnection; a committed report must "
                        "reference its model byPath (relative)"
                    ),
                    locator=f"{rel}#/datasetReference/byConnection",
                )
            )
            continue
        by_path = ref.get("byPath", {}) if isinstance(ref, dict) else {}
        model_path = by_path.get("path") if isinstance(by_path, dict) else None
        if isinstance(model_path, str) and _ABSOLUTE.match(model_path):
            findings.append(
                Finding(
                    rule_id="R1",
                    severity=Severity.ERROR,
                    message=(
                        f"datasetReference.byPath.path is absolute "
                        f"({model_path!r}); must be relative"
                    ),
                    locator=f"{rel}#/datasetReference/byPath/path",
                )
            )
    return findings
