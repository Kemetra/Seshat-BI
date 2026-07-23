"""PBIR/JSON rule R1 (relative model reference). Replaces the M1.6 stub."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

from ..core import Finding, RuleContext, Severity, is_test_path, read_tracked_text
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
        # Tracked-but-deleted-on-disk (#430): nothing to scan for a reference
        # shape, skip rather than crash. Content scan, not a presence check.
        raw = read_tracked_text(ctx.repo_root / rel, encoding="utf-8-sig")
        if raw is None:
            continue
        doc: Any = json.loads(raw)
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


# --- R2: PBIR report authoring-lint (polices what the theme-application adapter
# writes; the READ-ONLY core sibling of the companion writer, ADR 0015). It asserts
# a committed report.json is valid, keeps its $schema, references only BaseTheme
# resources that exist, and DEFINES no business logic (the report-file analogue of
# DL1's styling-only rule). It NEVER writes -- the writer is the adapter.
#
# CRITICAL distinction (why this is a WHOLE-KEY denylist, not substring containment):
# a legitimate PBIR report REFERENCES model objects inline via the query-grammar
# wrapper keys ``Measure`` / ``Expression`` / ``Column`` wherever a value is
# data-bound (a filter on a measure, a title bound to a measure). Those are
# REFERENCES to something the model already DEFINES -- expected, legal report
# content this adapter exists to enable. R2 forbids only keys that DEFINE business
# logic in the report file. So it matches the WHOLE normalized key against a
# denylist of definition-shaped keys; it does NOT do substring containment (which
# would false-positive ``Measure``/``Expression`` references and break the gate on
# the first realistic report).
_R2_FORBIDDEN_KEYS = frozenset(
    {
        "measuredefinition",
        "calculatedcolumn",
        "calculatedtable",
        "calculatedmeasure",
        "daxexpression",
        "daxmeasure",
        "sourcemapping",
        "metricdefinition",
        "sentimentthreshold",
        "relationshipdefinition",
    }
)


def _iter_report_json(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if p.endswith(".Report/definition/report.json") and not is_test_path(p)
    ]


def _normalize(key: str) -> str:
    return key.lower().replace("-", "").replace("_", "").replace(" ", "")


def _forbidden_key_finding(key: str, pointer: str, rel: str) -> Iterable[Finding]:
    if _normalize(key) not in _R2_FORBIDDEN_KEYS:
        return
    yield Finding(
        rule_id="R2",
        severity=Severity.ERROR,
        message=(
            f"report.json DEFINES business logic via key {key!r}; a "
            f"report file is layout + styling and may only REFERENCE "
            f"model objects, never define them (a definition belongs "
            f"in the semantic model / metric contract)"
        ),
        locator=f"{rel}#{pointer}/{key}",
    )


def _walk_forbidden(node: Any, pointer: str, rel: str) -> Iterable[Finding]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _forbidden_key_finding(key, pointer, rel)
            yield from _walk_forbidden(value, f"{pointer}/{key}", rel)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _walk_forbidden(item, f"{pointer}/{i}", rel)


def _check_base_theme_item(item: Any, pkg_dir: Any, locator: str) -> Iterable[Finding]:
    if not isinstance(item, dict) or item.get("type") != "BaseTheme":
        return
    sub = item.get("path")
    if not isinstance(sub, str):
        return
    if not (pkg_dir / sub).exists():
        yield Finding(
            rule_id="R2",
            severity=Severity.ERROR,
            message=(
                f"report references BaseTheme resource {sub!r} "
                f"which does not exist at its declared path"
            ),
            locator=locator,
        )


def _check_base_theme_resources(
    doc: Any, report_dir: Any, rel: str
) -> Iterable[Finding]:
    # Every BaseTheme referenced by resourcePackages must exist on disk.
    for pi, pkg in enumerate(doc.get("resourcePackages", []) or []):
        if not isinstance(pkg, dict):
            continue
        pkg_dir = report_dir / "StaticResources" / pkg.get("name", "")
        for ii, item in enumerate(pkg.get("items", []) or []):
            locator = f"{rel}#/resourcePackages/{pi}/items/{ii}/path"
            yield from _check_base_theme_item(item, pkg_dir, locator)


def _check_one_report_json(ctx: RuleContext, rel: str) -> Iterable[Finding]:
    path = ctx.repo_root / rel
    try:
        with path.open(encoding="utf-8-sig") as fh:
            doc: Any = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        yield Finding(
            rule_id="R2",
            severity=Severity.ERROR,
            message=(
                f"report.json could not be parsed as JSON "
                f"({exc.__class__.__name__}); it must be valid JSON"
            ),
            locator=f"{rel}#/",
        )
        return
    if not isinstance(doc, dict) or "$schema" not in doc:
        yield Finding(
            rule_id="R2",
            severity=Severity.ERROR,
            message="report.json is missing its $schema declaration",
            locator=f"{rel}#/$schema",
        )
        return
    report_dir = path.parent.parent  # <name>.Report/
    yield from _check_base_theme_resources(doc, report_dir, rel)
    yield from _walk_forbidden(doc, "", rel)


@register("R2", "PBIR report.json is valid, keeps its schema, and references exist")
def check_pbir_report_authoring(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in _iter_report_json(ctx):
        findings.extend(_check_one_report_json(ctx, rel))
    return findings
