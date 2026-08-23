"""Design-lint rule DL11: a design pointer that names a real target resolves to one.

The design corpora carry ten ``*_ref`` keys. The suffix does NOT mean "file path" --
enumerated by hand against the real key set rather than assumed from the convention,
they fall into three buckets:

* repo-relative FILE paths -- ``grid_ref``, ``theme_ref``, ``tokens_ref`` and
  ``spec_ref``. ``spec_ref`` carries BOTH concrete values (the blueprint template
  names ``templates/background-spec.yaml``) and unfilled ``<placeholders>``; the
  placeholder filter already excuses the latter, so guarding the key costs no false
  errors and stops a renamed spec from dangling.
* intra-file TOKEN pointers -- ``value_typography_ref``, ``label_typography_ref``
  and ``background_ref``. Each is a DOTTED KEY PATH into the design-token file
  (``typography.scale_pt.kpi_value``), not a file, and resolves against the file
  that DECLARES it rather than the union of every tracked token document.
* not resolvable here -- ``blueprint_ref`` and ``source_file_ref``
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

from pathlib import PurePosixPath
from typing import Any, Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register
from ..rule_coverage import TEST_FIXTURES, any_tracked_file
from .yaml_tree import load, read, strings_for

RULE_ID = "DL11"

_SCANNED_ROOTS = ("design/", "templates/", "reports/", "contracts/report/")

# The census must claim exactly what the rule EXAMINES. Accepting any `design/*`
# file (including non-YAML, which `_scanned_files` rejects) while omitting the
# `reports/` and `contracts/report/` roots it does scan was wrong in both
# directions: a repo of only `reports/` pointers read as unevaluable, and a repo of
# only `design/*.md` read as evaluated and clean without a document being examined.
REF_CORPUS = any_tracked_file(
    *(f"{root}**/*.{suffix}" for root in _SCANNED_ROOTS for suffix in ("yaml", "yml")),
    exclude=(TEST_FIXTURES,),
    note=(
        "no non-fixture YAML is tracked under any scanned design root, so this rule "
        "resolved no pointer and its silence is not a pass"
    ),
)

# Hand-verified scope. Widening either set silently is what produces false errors.
FILE_REF_KEYS = frozenset({"grid_ref", "theme_ref", "tokens_ref", "spec_ref"})
TOKEN_REF_KEYS = frozenset(
    {"value_typography_ref", "label_typography_ref", "background_ref"}
)

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


def _is_committed(target: str, tracked: frozenset[str]) -> bool:
    """Whether ``target`` names a tracked repo-relative file.

    Asks the COMMIT, not the filesystem. `.exists()` accepts three things DL11 must
    reject: a file present only in one working tree, an absolute path (``repo_root /
    "/abs"`` discards the root entirely, so the check silently escapes the repo), and
    a ``../`` path climbing out of it. Normalized to posix before comparison because
    ``ctx.tracked_files`` is git's forward-slash form on every platform.
    """
    candidate = PurePosixPath(target.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        return False
    return str(candidate) in tracked


def _file_findings(rel: str, doc: Any, tracked: frozenset[str]) -> Iterable[Finding]:
    for target in sorted(_claims(doc, FILE_REF_KEYS)):
        if not _is_committed(target, tracked):
            yield _finding(
                rel, f"pointer target is not a committed repo file: {target}"
            )


def _token_findings(
    rel: str, doc: Any, token_docs: list[Any], is_token_file: bool
) -> Iterable[Finding]:
    """Every dotted token claim that does not resolve where it must.

    These are INTRA-file pointers, so a token file's OWN claims resolve against that
    file -- not against the union of every tracked token document, which let a
    dangling path pass because a sibling token file happened to define it. A claim
    made from outside the token corpus resolves against that corpus.

    An absent token corpus does NOT excuse the claims either. `REF_CORPUS` is
    satisfied by any design or template file, so the census never surfaces the gap,
    and skipping the claims let a dangling pointer pass whenever the token file was
    missing or unparseable -- the claim is unresolved either way.
    """
    targets = [doc] if is_token_file else token_docs
    where = "its own file" if is_token_file else "any token file"
    for dotted in sorted(_claims(doc, TOKEN_REF_KEYS)):
        if not targets:
            yield _finding(
                rel,
                f"token pointer has no token document to resolve against: {dotted}",
            )
        elif not any(_resolves_in(target, dotted) for target in targets):
            yield _finding(rel, f"token pointer does not resolve in {where}: {dotted}")


@register(
    RULE_ID,
    "Design file and token pointers resolve to a committed target",
    requires=(REF_CORPUS,),
)
def ref_resolution(ctx: RuleContext) -> Iterable[Finding]:
    token_docs = _token_documents(ctx)
    tracked = frozenset(rel.replace("\\", "/") for rel in ctx.tracked_files)
    for rel in _scanned_files(ctx):
        document = read(ctx.repo_root / rel)
        if document.failed:
            yield _finding(
                rel, "file could not be parsed, so its pointers are unchecked"
            )
            continue
        yield from _file_findings(rel, document.data, tracked)
        yield from _token_findings(
            rel, document.data, token_docs, _TOKEN_FILE_HINT in rel
        )
