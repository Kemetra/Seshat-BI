"""H1 -- additivity-consistency lineage rule (spec 068).

A new OFF-SPINE retail-check integrity rule (a sibling of the shipped
assumption-ledger rule AL1) that statically cross-reads two committed
define-layer facts per metric -- its declared ADDITIVITY classification and its
DERIVATION-lineage edges -- and ERRORs when a metric's additivity is COMPOSED
illegally per a small CLOSED, generic legality table.

Read source (Clarifications Q2 / FR-009): the committed define-layer PROSE
corpus under ``skills/retail-kpi-knowledge/contracts/*.md``, reached by a
generic glob (no worked-example path is hardcoded). Each contract carries a
``**Additivity**`` heading whose prose opens with a closed-vocabulary word
("Fully additive" / "Semi-additive" / "Non-additive") and, when derived, a
``**Derives from**`` heading whose prose states the composition.

Legality (FR-006, generic retail arithmetic; the exact matrix is FR-012, OPEN
for owner ratification -- the seed table below encodes only settled generic
facts):

  - a NON-additive (ratio/percentage/average) child by a DIRECT SUM -> ILLEGAL
  - a SEMI-additive component into a PLAIN-SUM parent               -> ILLEGAL
  - a NON-additive child recomputed base-over-base (a ratio ``a / b``) -> LEGAL

Principle V (FR-004/FR-005): the rule acts ONLY on the exact committed
classification words; a metric that participates in a derivation edge but whose
class is absent or out-of-vocabulary is ERRORed as absent/ambiguous and NEVER
inferred. A composition whose kind is not explicitly stated is treated as
UNKNOWN and yields NO verdict (never assume SUM). The rule never picks a winner,
invents an edge, or re-classifies a metric -- it only surfaces the
inconsistency for a human owner to resolve.

It is a pure static text read (stdlib ``re`` only), never executes, opens no
connection, renders no visual, emits ERROR-only categorical findings (no score),
and modifies no artifact. On the current committed corpus it finds nothing.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "AD1"

# The generic define-layer prose corpus (Clarifications Q2). Generic glob, no
# worked-example path. The reference TEMPLATE in the tree is exempt (blank shape).
_CORPUS_RE = re.compile(r"^skills/retail-kpi-knowledge/contracts/[^/]+\.md$")
_TEMPLATE_RE = re.compile(
    r"^skills/retail-kpi-knowledge/references/.*template.*\.md$", re.I
)

# Closed additivity vocabulary (FR-004). Assigned ONLY by matching one exact
# word; an absent or out-of-vocabulary class is ABSENT_OR_AMBIGUOUS, never real.
_FULLY = "FULLY_ADDITIVE"
_SEMI = "SEMI_ADDITIVE"
_NON = "NON_ADDITIVE"
_ABSENT = "ABSENT_OR_AMBIGUOUS"

# Match the additivity vocabulary word (case-insensitive, hyphen-tolerant).
_VOCAB = (
    (re.compile(r"\bfully[ -]additive\b", re.I), _FULLY),
    (re.compile(r"\bsemi[ -]additive\b", re.I), _SEMI),
    (re.compile(r"\bnon[ -]additive\b", re.I), _NON),
)

_ADDITIVITY_HEADING_RE = re.compile(r"(?im)^\**additivity\**\s*$")
_DERIVES_HEADING_RE = re.compile(r"(?im)^\**derives from\**\s*$")
_METRIC_TITLE_RE = re.compile(r"(?im)^#\s+(.+?)\s+--\s+Metric Contract\s*$")

# A direct-sum composition stated in prose: "sum of <Parent>" or "SUM(<Parent>)".
_DIRECT_SUM_RE = re.compile(r"(?i)\bsum\s*(?:of|\()\s*([A-Z][A-Za-z0-9_]+)")
# A base-over-base ratio recompute explicitly stated: "<A> / <B>".
_RATIO_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]+)\s*/\s*([A-Z][A-Za-z0-9_]+)\b")


def _iter_corpus(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if _CORPUS_RE.match(p) and not _TEMPLATE_RE.match(p) and not is_test_path(p)
    ]


def _heading_body(text: str, heading_re: re.Pattern) -> str:
    """Return prose from just after a heading to the next blank line or heading."""
    m = heading_re.search(text)
    if not m:
        return ""
    rest = text[m.end() :]
    out: list[str] = []
    for line in rest.splitlines():
        stripped = line.strip()
        if not out and not stripped:
            continue  # skip blank lines immediately after the heading
        if not stripped:
            break  # blank line ends the block
        if stripped.startswith("#") or re.match(r"^\*\*[^*]+\*\*\s*$", stripped):
            break  # next heading ends the block
        out.append(stripped)
    return " ".join(out)


def _classify(additivity_prose: str) -> str:
    hits = {klass for pat, klass in _VOCAB if pat.search(additivity_prose)}
    if len(hits) == 1:
        return next(iter(hits))
    return _ABSENT  # zero matches (absent) or more than one (ambiguous)


def _metric_name(text: str, rel: str) -> str:
    m = _METRIC_TITLE_RE.search(text)
    if m:
        return m.group(1).strip()
    return rel.rsplit("/", 1)[-1].removesuffix(".md")


@register(
    RULE_ID, "Metric additivity is not composed illegally with its lineage parents"
)
def check_additivity_consistency(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []

    # Pass 1: read every contract's classification + derivation prose.
    classes: dict[str, str] = {}
    derivations: list[tuple[str, str, str]] = []  # (child, parents_prose, locator)
    for rel in sorted(_iter_corpus(ctx)):
        try:
            text = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=f"could not read define-layer contract: {exc}",
                    locator=rel,
                )
            )
            continue
        name = _metric_name(text, rel)
        classes[name] = _classify(_heading_body(text, _ADDITIVITY_HEADING_RE))
        derives = _heading_body(text, _DERIVES_HEADING_RE)
        if derives:
            derivations.append((name, derives, rel))

    # Pass 2: check each explicitly-stated composition edge against the legality table.
    for child, prose, locator in derivations:
        # A base-over-base ratio recompute (a / b) is LEGAL by construction; skip.
        is_ratio_recompute = bool(_RATIO_RE.search(prose))

        for sum_match in _DIRECT_SUM_RE.finditer(prose):
            parent = sum_match.group(1)
            if is_ratio_recompute:
                # Prose states a ratio recompute; a "sum of" mention inside a
                # ratio is not a direct-sum verdict -- unknown, no verdict.
                continue
            parent_class = classes.get(parent, _ABSENT)
            if parent_class == _ABSENT:
                # US2 / FR-004: a metric on an edge with no recognizable class ->
                # ERROR absent/ambiguous; NEVER infer a class or a verdict from it.
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        severity=Severity.ERROR,
                        message=(
                            f"'{child}' composes '{parent}' by direct sum but"
                            f" '{parent}' has an absent or ambiguous additivity"
                            " classification -- a human owner must classify it;"
                            " the rule never infers a class (Principle V)"
                        ),
                        locator=locator,
                    )
                )
            elif parent_class in (_NON, _SEMI):
                kind = (
                    "non-additive (ratio/average)"
                    if parent_class == _NON
                    else "semi-additive"
                )
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        severity=Severity.ERROR,
                        message=(
                            f"illegal composition: '{child}' sums '{parent}', which is"
                            f" {kind} and must never be composed by a direct sum --"
                            " resolve the classification or the composition; the rule"
                            " never picks a winner (Principle V)"
                        ),
                        locator=locator,
                    )
                )
            # parent_class == _FULLY summed by an additive parent -> LEGAL, no finding.
    return findings
