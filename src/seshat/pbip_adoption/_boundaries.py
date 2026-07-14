"""Content-safety and readiness-gap scanning over discovered project files.

Distinct from structural discovery: these helpers read file *contents* to raise
governance facts (credential-like literals, non-gold sources) and to record
which committed readiness artifacts are missing.  Every fact carries fixed
prose only -- the offending literal is detected, never echoed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ._facts import _Fact
from ._safety import (
    _CONNECTION_LITERAL,
    _CREDENTIAL_LITERAL,
    _FileRecord,
    _read_text,
)

_NON_GOLD_SOURCE = re.compile(
    r"(?i)(?:schema\s*=\s*['\"](?!gold['\"]|gold\b)|\b(?:bronze|silver)\.)"
)


def _add_missing_governance_facts(root: Path, facts: list[_Fact]) -> None:
    checks = (
        (
            "source-profile",
            "mappings/*/source-profile.md",
            "No committed Source Ready profile was found.",
        ),
        (
            "source-map",
            "mappings/*/source-map.yaml",
            "No approved source mapping was found.",
        ),
        (
            "metric-contract",
            "mappings/*/metrics/*.yaml",
            "No metric contract was found.",
        ),
        (
            "approval-record",
            "mappings/*/readiness-status.yaml",
            "No committed readiness or approval record was found.",
        ),
    )
    for name, pattern, detail in checks:
        if not list(root.glob(pattern)):
            facts.append(
                _Fact(
                    id=f"missing:{name}",
                    classification="missing",
                    category="readiness",
                    subject=name.replace("-", " "),
                    detail=detail,
                    reason=detail,
                    required_authority="data_owner"
                    if name == "source-profile"
                    else "analyst",
                )
            )


def _scan_literal_boundaries(
    root: Path, records: Iterable[_FileRecord], facts: list[_Fact]
) -> None:
    for record in records:
        suffix = Path(record.artifact).suffix.lower()
        if suffix not in {".tmdl", ".pbir", ".json", ".m"}:
            continue
        text = _read_text(root / Path(record.artifact))
        if text is not None:
            _scan_one_text(record.artifact, text, facts)


def _scan_one_text(artifact: str, text: str, facts: list[_Fact]) -> None:
    if _CREDENTIAL_LITERAL.search(text):
        facts.append(
            _Fact(
                id=f"blocked:C2:{artifact}",
                classification="blocked",
                category="governance",
                subject="credential-like literal",
                detail="Credential-like source content was detected and redacted "
                "from this assessment.",
                artifact=artifact,
                rule_id="C2",
                required_authority="governance",
            )
        )
    elif _CONNECTION_LITERAL.search(text):
        facts.append(
            _Fact(
                id=f"blocked:C1:{artifact}",
                classification="blocked",
                category="governance",
                subject="literal connection detail",
                detail="A literal connection detail was detected and redacted "
                "from this assessment.",
                artifact=artifact,
                rule_id="C1",
                required_authority="governance",
            )
        )
    if _NON_GOLD_SOURCE.search(text):
        facts.append(
            _Fact(
                id=f"blocked:D8:{artifact}",
                classification="blocked",
                category="governance",
                subject="non-gold semantic-model source",
                detail="A semantic-model source outside the gold schema was detected.",
                artifact=artifact,
                rule_id="D8",
                required_authority="governance",
            )
        )
