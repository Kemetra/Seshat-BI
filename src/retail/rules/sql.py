"""SQL rules (S1–S4b, plus D8 schema tokens). Added in M2; stub for M1.6 wiring."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from ..core import Finding, RuleContext, Severity
from ..registry import register
from ..sql import SqlToken, iter_sql_files, stale_schema_tokens, tokenize_sql

_SNAKE = re.compile(r"^[a-z_][a-z0-9_]*$")
# quoted/bracketed identifier in a declaration position
_QUOTED = re.compile(r'"([^"]*)"|\[([^\]]*)\]')
EXEMPT_S2 = frozenset({"warehouse/README.md"})


def _read(ctx: RuleContext, rel: str) -> str:
    return (ctx.repo_root / rel).read_text(encoding="utf-8")


@register("S1", "snake_case SQL identifiers")
def s1_snake_case_identifiers(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        text = _read(ctx, rel)
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in _QUOTED.finditer(line):
                ident = m.group(1) if m.group(1) is not None else m.group(2)
                if not _SNAKE.match(ident):
                    findings.append(
                        Finding(
                            rule_id="S1",
                            severity=Severity.ERROR,
                            message=f"non-snake_case identifier {ident!r}",
                            locator=f"{rel}:{lineno}",
                        )
                    )
    return findings


@register("S2", "medallion schema names")
def s2_medallion_schemas(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        if rel in EXEMPT_S2:
            continue
        text = _read(ctx, rel)
        for token, line in stale_schema_tokens(text):
            if token in ("raw", "marts"):
                findings.append(
                    Finding(
                        rule_id="S2",
                        severity=Severity.ERROR,
                        message=f"stale schema {token!r}; use bronze/silver/gold",
                        locator=f"{rel}:{line}",
                    )
                )
    return findings


@register("S3", "vw_ prefix on views")
def s3_vw_prefix(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        toks = [t for t in tokenize_sql(_read(ctx, rel)) if t.text]
        for idx, tok in enumerate(toks):
            if tok.text.upper() != "VIEW":
                continue
            # the view name is the next identifier; skip a schema qualifier
            nxt = toks[idx + 1] if idx + 1 < len(toks) else None
            if nxt is None:
                continue
            # gold.vw_x -> name token is two ahead (skip "gold" and ".")
            if idx + 3 < len(toks) and toks[idx + 2].text == ".":
                name_tok = toks[idx + 3]
            else:
                name_tok = nxt
            if not name_tok.text.lower().startswith("vw_"):
                findings.append(
                    Finding(
                        rule_id="S3",
                        severity=Severity.ERROR,
                        message=f"view {name_tok.text!r} missing vw_ prefix",
                        locator=f"{rel}:{name_tok.line}",
                    )
                )
    return findings


_MIGRATION_NAME = re.compile(r"^\d{4}_.+\.sql$")


@register("S4a", "migration filename + numbering")
def s4a_migration_numbering(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    migrations = [
        rel for rel in iter_sql_files(ctx) if rel.startswith("warehouse/migrations/")
    ]
    numbers: dict[int, str] = {}
    for rel in migrations:
        name = PurePosixPath(rel).name
        if not _MIGRATION_NAME.match(name):
            findings.append(
                Finding(
                    rule_id="S4a",
                    severity=Severity.ERROR,
                    message=(
                        f"migration filename {name!r} must match" r" ^\d{4}_.+\.sql$"
                    ),
                    locator=rel,
                )
            )
            continue
        num = int(name[:4])
        if num in numbers:
            findings.append(
                Finding(
                    rule_id="S4a",
                    severity=Severity.ERROR,
                    message=f"duplicate migration number {num:04d}",
                    locator=rel,
                )
            )
        else:
            numbers[num] = rel
    if numbers:
        ordered = sorted(numbers)
        for prev, cur in zip(ordered, ordered[1:]):
            if cur != prev + 1:
                findings.append(
                    Finding(
                        rule_id="S4a",
                        severity=Severity.ERROR,
                        message=(
                            f"non-contiguous migration numbering: gap between "
                            f"{prev:04d} and {cur:04d}"
                        ),
                        locator=numbers[cur],
                    )
                )
    return findings


def _is_guarded(toks: list[SqlToken], idx: int) -> bool:
    """True if the CREATE/ALTER/DROP at toks[idx] is an accepted guarded form."""
    verb = toks[idx].text.upper()
    # window of the next few keyword tokens, upper-cased
    tail = [t.text.upper() for t in toks[idx : idx + 8]]
    joined = " ".join(tail)
    if verb == "CREATE":
        return "OR REPLACE VIEW" in joined or "IF NOT EXISTS" in joined
    if verb == "ALTER":
        return "IF EXISTS" in joined or "IF NOT EXISTS" in joined
    if verb == "DROP":
        return "IF EXISTS" in joined
    return False


@register("S4b", "migration guard form")
def s4b_guard_form(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        toks = [t for t in tokenize_sql(_read(ctx, rel)) if t.text]
        for idx, tok in enumerate(toks):
            if tok.text.upper() not in ("CREATE", "ALTER"):
                continue
            if _is_guarded(toks, idx):
                continue
            findings.append(
                Finding(
                    rule_id="S4b",
                    severity=Severity.WARNING,
                    message=(
                        f"bare {tok.text.upper()} is not an accepted guarded "
                        "form (use IF [NOT] EXISTS / OR REPLACE VIEW)"
                    ),
                    locator=f"{rel}:{tok.line}",
                )
            )
    return findings
