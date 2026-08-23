"""Design-lint rule DL11: a design pointer that names a real target resolves to one.

The design corpora carry ten ``*_ref`` keys. The suffix does NOT mean "file path" --
enumerated by hand against the real key set rather than assumed from the convention,
they fall into three buckets:

* repo-relative FILE paths -- ``grid_ref``, ``theme_ref``.
* an intra-file TOKEN pointer -- ``value_typography_ref``
  (``typography.scale_pt.kpi_value``): a DOTTED KEY PATH into the design-token
  file, not a file.
* not resolvable here -- ``blueprint_ref``, ``spec_ref``, ``source_file_ref``
  (``<placeholders>`` in the templates), ``store_ref`` and ``model_ref``
  ("a path-or-id" in the F009/F010 stores, so a bare id is legitimate), and
  ``qa_ref`` (a prose design-doc name, e.g. ``visual-qa``), and
  ``sentiment_color_ref`` -- which carries TWO value languages: a dotted token path
  in the token file (``colors.sentiment``) and free prose in a filled blueprint
  (``theme ok/warn/fail``). One key, two grammars, so no single resolver is correct
  for it; DL11's first run on the real corpus surfaced this, and the honest response
  is to drop the key rather than loosen the rule until the prose passes -- a rule
  widened to swallow prose would also swallow a genuinely broken dotted path.

DL11 guards the THREE it can resolve. Guarding all ten as paths would emit false
ERRORs on seven, and a gate that cries wolf gets switched off. The seven are named
above rather than silently skipped, so this docstring claims no more than the code
delivers.

A pointer whose value is an unfilled ``<placeholder>`` or the documented literal
``none`` is not a claim about a target and is not reported -- templates ship
deliberately unfilled.

Reads committed YAML/JSON existence only: no execution, no DB, no Power BI. Field
names only, no tenant or brand literal (Principle VII).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register
from ..rule_coverage import TEST_FIXTURES, any_tracked_file
from .yaml_tree import load, strings_for

REF_CORPUS = any_tracked_file(
    "design/*",
    "templates/*",
    exclude=(TEST_FIXTURES,),
    note=(
        "no non-fixture design or template file is tracked, so this rule resolved "
        "no pointer and its silence is not a pass"
    ),
)

RULE_ID = "DL11"

# Hand-verified scope. Widening either set silently is what produces false errors.
FILE_REF_KEYS = frozenset({"grid_ref", "theme_ref"})
TOKEN_REF_KEYS = frozenset({"value_typography_ref"})

_SCANNED_ROOTS = ("design/", "templates/", "reports/", "contracts/report/")
_TOKEN_FILE_HINT = "design/tokens/"
# A value that makes no claim about a target: an unfilled template slot, or the
# documented literal for "there deliberately isn't one".
_NOT_A_CLAIM = frozenset({"none", "n/a", ""})


def _claims(node: Any, keys: frozenset[str]) -> set[str]:
    """Values under ``keys`` that actually assert a resolvable target.

    An unfilled ``<placeholder>`` and the documented ``none`` assert nothing, so
    they are not claims and cannot dangle.
    """
    found = set()
    for value in strings_for(node, *keys):
        if value.lower() in _NOT_A_CLAIM:
            continue
        if value.startswith("<") and value.endswith(">"):
            continue
        found.add(value)
    return found


def _scanned_files(ctx: RuleContext) -> Iterable[str]:
    return (
        rel
        for rel in ctx.tracked_files
        if rel.startswith(_SCANNED_ROOTS)
        and rel.endswith((".yaml", ".yml"))
        and not is_test_path(rel)
    )


def _token_documents(ctx: RuleContext) -> list[Any]:
    """Every committed design-token document a dotted pointer may resolve into."""
    candidates = (rel for rel in _scanned_files(ctx) if _TOKEN_FILE_HINT in rel)
    loaded = (load(ctx.repo_root / rel) for rel in candidates)
    return [doc for doc in loaded if isinstance(doc, dict)]


def _resolves_in(doc: Any, dotted: str) -> bool:
    node = doc
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def _finding(rel: str, message: str) -> Finding:
    return Finding(
        rule_id=RULE_ID, severity=Severity.ERROR, message=message, locator=rel
    )


def _file_findings(repo_root: Path, rel: str, doc: Any) -> Iterable[Finding]:
    for target in sorted(_claims(doc, FILE_REF_KEYS)):
        if not (repo_root / target).exists():
            yield _finding(rel, f"pointer target does not exist: {target}")


def _token_findings(rel: str, doc: Any, token_docs: list[Any]) -> Iterable[Finding]:
    # No token file tracked means nothing to resolve against, which is a coverage
    # gap the census reports rather than a dangling pointer.
    for dotted in sorted(_claims(doc, TOKEN_REF_KEYS)) if token_docs else ():
        if not any(_resolves_in(doc_, dotted) for doc_ in token_docs):
            yield _finding(
                rel, f"token pointer does not resolve in any token file: {dotted}"
            )


@register(
    RULE_ID,
    "Design file and token pointers resolve to a committed target",
    requires=(REF_CORPUS,),
)
def ref_resolution(ctx: RuleContext) -> Iterable[Finding]:
    token_docs = _token_documents(ctx)
    for rel in _scanned_files(ctx):
        doc = load(ctx.repo_root / rel)
        yield from _file_findings(ctx.repo_root, rel, doc)
        yield from _token_findings(rel, doc, token_docs)
