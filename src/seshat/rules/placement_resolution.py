"""HR13 -- every ``dim:`` gold_placement prefix resolves to a declared dimension.

A PER-MAP integrity gate (issue #499). ``columns[].gold_placement`` is how a
source-map says "this source column becomes an attribute of that gold dimension".
The reader that consumes it -- HR1's ``_attr_silver_types`` -- resolves the
placement prefix against the dimension's PHYSICAL bare name
(``gold_star.dimensions[].name`` / ``date_dimension.name`` with any ``<schema>.``
prefix stripped). That is the OWNER RULING: the physical name is canonical in a
placement.

Nothing enforced it, and the consumer degrades gracefully by design
(``conformed_dimension.py`` :81-82 -- an unmatched prefix simply contributes
nothing). So a placement naming a dimension that does not exist was
INDISTINGUISHABLE from a deliberate no-op: the reference map's five placements
all named LOGICAL dims (``dim:dim_product``) while the star declared PHYSICAL,
``_rss``-suffixed tables (``gold.dim_product_rss``), and every one silently
yielded ``{}``. HR1's shared-attribute type-divergence limb had nothing to
compare -- a FAIL-OPEN on a cross-star consistency rule, invisible only because
this repo has one star and that limb needs two.

HR13 makes the same mistake fail LOUDLY, at the map, on a single star.

What HR13 does (STATIC, fail-closed, per-map -- no star-count threshold):
  - Reads every committed ``mappings/<table>/source-map.yaml`` (via the shared
    ``star_discovery`` discovery so the template's placeholders and the test
    fixtures stay out of scope, exactly as HR1 sees them).
  - For each ``columns[].gold_placement`` of the form ``dim:<prefix>.<attr>``,
    ERRORs when the CONSUMER could not resolve it: either ``<prefix>`` matches no
    dimension the same map declares under ``gold_star.dimensions[]`` /
    ``gold_star.date_dimension``, or it matches one only under a normalization the
    consumer does not perform (wrong case, stray whitespace, a missing ``.``
    delimiter, an empty attribute). The acceptance test mirrors HR1's exact
    ``startswith`` match, because a gate looser than its reader certifies
    placements that still silently resolve to nothing.
  - Names the offending prefix AND the declared names it could have meant, so a
    suffix drift (``dim_product`` vs ``dim_product_rss``) reads at a glance.
  - ERRORs on a value that is neither a ``dim:`` reference NOR one of the three
    enumerated non-dimension placements (``fact_measure``, ``degenerate_dim``,
    ``dropped``). "Not a dimension placement" is a CLOSED list: accepting any
    unrecognized string as a silent non-reference is the same fail-open one level
    up, letting a MARKER typo (``DIM:``, ``dim :``, ``fact_measures``) or a
    nameless ``dim:`` / ``dim:.attr`` through while every reader ignores the value.
  - A column declaring no ``gold_placement`` key at all is out of scope (that is a
    different rule's business), never a finding here.

What HR13 NEVER does:
  - It NEVER matches a prefix fuzzily, tolerantly, or by suffix. A governance
    rule that guesses which dimension an author meant preserves the exact
    ambiguity this rule exists to remove (owner ruling: suffix-tolerant matching
    REJECTED, as was a declared-alias field -- no new schema surface).
  - It NEVER checks the ATTRIBUTE half of a placement. A dimension's attributes
    are not uniformly declared -- an RC15 ``date_dimension`` carries no
    ``attributes`` key at all, because its calendar columns are GENERATED
    (issue #491) -- so attribute-level validation would fire on correct maps.
    Prefix resolution only.
  - It NEVER rewrites a placement, renames a dimension, or decides which name a
    map SHOULD use (Principle V); it names the unresolvable reference and stops.
  - It NEVER opens a database or reads a live model (Principle VIII), NEVER
    writes a file, and NEVER emits a numeric score or an "N of M" tally
    (hard rule #9).

Non-``dim:`` placements (``fact_measure``, ``degenerate_dim``, ``dropped``) are
not dimension references and are never inspected. A compact-form map with no
``columns[]`` block contributes nothing (absence is not drift).

Mirrors the SF1/HR1/HR11 lazy-``yaml``-import discipline (kept out of the
``retail check`` static-core chain).
"""

from __future__ import annotations

from collections.abc import Iterable

from seshat import star_discovery as _stars

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "HR13"

_DIM_PREFIX = "dim:"

# The COMPLETE set of non-dimension placement values, per templates/source-map.yaml:
#   gold_placement  fact_measure | "dim:<dim_name>.<attr>" | degenerate_dim | dropped
# Enumerated (never inferred) because "not a dimension reference" must be a CLOSED
# list: treating any unrecognized string as a silent non-reference is how a marker
# typo (`DIM:`, `dim :`, `fact_measures`) slips past the gate while the reader
# resolves nothing from it -- the same fail-open one level up from a bad prefix.
_NON_DIM_PLACEMENTS = frozenset({"fact_measure", "degenerate_dim", "dropped"})


def _load_yaml(ctx: RuleContext, rel: str) -> dict | None:
    import yaml  # lazy: kept out of the retail check static-core chain

    try:
        data = yaml.safe_load((ctx.repo_root / rel).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        # UnicodeDecodeError is a ValueError, NOT an OSError: without it an
        # undecodable byte in ANY committed map propagates out of the rule and
        # crashes the whole `retail check` run. Mirrors HR11's exception tuple
        # (currency_unit.py) -- a rule degrades on an unreadable artifact, it never
        # takes the gate down.
        return None
    return data if isinstance(data, dict) else None


def _is_unreadable(ctx: RuleContext, rel: str) -> bool:
    """Did this file fail to READ/PARSE, as opposed to parsing to a non-dict?

    ``_load_yaml`` collapses two very different outcomes into one ``None``: a genuine
    read failure (undecodable bytes, invalid YAML) versus a successful parse that is
    simply not a mapping -- an EMPTY file (``yaml.safe_load("") is None``), a bare
    scalar, a top-level list. Only the first is a broken artifact a governance gate
    must report; the second is a different rule's business, and firing on it would
    flag committed maps that are merely not stars.

    Same encoding and exception tuple as ``_load_yaml``, and the twin of HR1's
    helper -- the two rules must agree on what "unreadable" means (#508).
    """
    import yaml  # lazy: kept out of the retail check static-core chain

    try:
        yaml.safe_load((ctx.repo_root / rel).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return True
    return False


def _placement_prefix(placement: object) -> str | None:
    """The dim name a ``dim:<prefix>.<attr>`` placement references, else ``None``.

    ``None`` means "carries no resolvable dimension name" -- either not a ``dim:``
    value at all, or a ``dim:`` with an EMPTY prefix (``"dim:"``, ``"dim:.attr"``).
    It does NOT mean "legal": ``_is_malformed_value`` decides legality, and it treats
    a nameless ``dim:`` as malformed.

    The accepted SHAPE must be exactly what the consumer parses, or HR13 certifies
    placements that still resolve to nothing -- the very fail-open this rule closes.
    HR1's ``_attr_silver_types`` matches ``placement.startswith(f"dim:{name}.")``:
    case-sensitive, whitespace-sensitive, and requiring a literal ``.`` with a
    non-empty attribute after it. So this returns the prefix VERBATIM (no
    lowercasing, no stripping, no schema-splitting) and demands the same delimiter.
    Requiring the delimiter is not validating the attribute half -- an unterminated
    ``dim:dim_product_rss`` resolves nothing for the reader, and a trailing-dot
    ``dim:dim_product_rss.`` is worse than nothing: it injects a bogus empty-string
    attribute into HR1's cross-star comparison set.
    """
    if not isinstance(placement, str) or not placement.startswith(_DIM_PREFIX):
        return None
    return placement[len(_DIM_PREFIX) :].partition(".")[0] or None


def _is_malformed_value(placement: object) -> bool:
    """Is this placement neither a known non-dim value NOR a well-formed ``dim:`` ref?

    The gate must be no looser than the reader (this PR's thesis), and "not a
    dimension placement" has to be a CLOSED list to hold that line. A marker typo
    -- ``DIM:dim_product_rss.item``, ``dim :dim_product_rss.item``,
    ``fact_measures`` -- is not a legal placement in any reading, and HR1 resolves
    nothing from it, so it must be REPORTED rather than waved through as "some other
    kind of placement". Only the three enumerated non-dim values pass silently.

    A ``dim:`` carrying NO dimension name (``"dim:"``, ``"dim:.attr"``) is malformed
    for the same reason: the documented enum is ``dim:<dim_name>.<attr>``, so a
    nameless reference is not a legal value, and HR1 resolves nothing from it either.
    Exempting it would be an arbitrary hole in the closed list.
    """
    if not isinstance(placement, str):
        return True  # a non-string placement is not a legal value either
    if placement in _NON_DIM_PLACEMENTS:
        return False
    if not placement.startswith(_DIM_PREFIX):
        return True
    return _placement_prefix(placement) is None  # `dim:` naming no dimension


def _declared_bare_names(document: dict) -> set[str]:
    """Bare names of every dimension the map declares (explicit + date)."""
    return set(_stars.star_dimensions(document))


def _resolves(placement: str, prefix: str, declared: set[str]) -> bool:
    """Would the CONSUMER resolve this placement against a declared dimension?

    Reproduces HR1's ``placement.startswith(f"dim:{name}.")`` test against each
    declared name, then requires a non-empty attribute after the delimiter. Anything
    this returns False for contributes nothing to the reader (or, on a trailing dot,
    contributes a bogus empty-string attribute), so HR13 must report it.
    """
    if prefix not in declared:
        return False
    consumer_prefix = f"{_DIM_PREFIX}{prefix}."  # exactly HR1's match string
    if not placement.startswith(consumer_prefix):
        return False
    attribute = placement[len(consumer_prefix) :]
    return attribute != ""


def _unresolved_placements(document: dict) -> list[tuple[str, str | None]]:
    """``(placement, prefix|None)`` for each placement the consumer cannot resolve.

    Three ways a placement fails, all of which leave the reader with nothing:
      1. a ``dim:`` prefix naming no declared dimension;
      2. a ``dim:`` prefix that DOES name one, but in a shape the consumer's exact,
         case-sensitive ``startswith`` match rejects (wrong case, stray whitespace,
         no ``.`` delimiter, empty attribute);
      3. a value that is not a legal placement at all -- a MARKER-level typo
         (``DIM:``, ``dim :``, ``fact_measures``) or a ``dim:`` naming no dimension
         (``"dim:"``, ``"dim:.attr"``). ``prefix`` is ``None`` for these; there is
         no dimension name to report against.

    Case 3 is the closed-list half: silently accepting any unrecognized string as
    "not a dimension placement" is the same fail-open as case 1, one level up.
    """
    cols = document.get("columns")
    if not isinstance(cols, list):
        return []  # compact form has no columns[] -- absence is not drift
    declared = _declared_bare_names(document)
    out: list[tuple[str, str | None]] = []
    for col in cols:
        if not isinstance(col, dict) or "gold_placement" not in col:
            continue  # a column declaring no placement is out of scope, not a defect
        placement = col["gold_placement"]
        if _is_malformed_value(placement):
            out.append((_render(placement), None))
            continue
        prefix = _placement_prefix(placement)
        if prefix is None:
            continue  # one of the three enumerated non-dim values -> legal, silent
        assert isinstance(placement, str)  # guaranteed by _placement_prefix
        if not _resolves(placement, prefix, declared):
            out.append((placement, prefix))
    return out


def _render(placement: object) -> str:
    """A placement as safe display text (it may be any YAML scalar, not just str)."""
    return placement if isinstance(placement, str) else repr(placement)


def _finding(
    rel: str, placement: str, prefix: str | None, declared: set[str]
) -> Finding:
    """Name the offender AND why it does not resolve.

    Three distinct causes, so three distinct messages -- telling an author their
    correctly-named dimension "is not declared" because they typed the wrong CASE
    would send them hunting the wrong thing.
    """
    known = ", ".join(sorted(declared)) if declared else "(none declared)"
    if prefix is None:
        legal = ", ".join(sorted(_NON_DIM_PLACEMENTS))
        return Finding(
            rule_id=RULE_ID,
            severity=Severity.ERROR,
            message=(
                f"gold_placement {placement!r} is not a legal placement value: it is "
                f"neither one of {legal} nor a 'dim:<dimension>.<attribute>' "
                f"reference. Check the marker itself for a case or spacing typo "
                f"(e.g. 'DIM:' or 'dim :' instead of 'dim:'); as written, every "
                f"reader silently ignores it"
            ),
            locator=f"{rel}:columns[].gold_placement",
        )
    # `declared` is lowercased/stripped by star_dimensions, while `prefix` is the
    # VERBATIM text. Match the two the same way to tell "this dimension exists but
    # the reference is malformed" apart from "no such dimension" -- the whole point
    # of splitting the message.
    canonical = _stars.bare_dim_name(prefix)
    if canonical in declared:
        reason = (
            f"names declared dimension {canonical!r} but not in the form the reader "
            f"resolves: the placement must be exactly "
            f"'dim:{canonical}.<attribute>' -- same case, no surrounding "
            f"whitespace, and a non-empty attribute after the '.'"
        )
    else:
        reason = (
            f"references dimension {prefix!r}, which this map does not declare; a "
            f"placement prefix MUST be the PHYSICAL bare name of a dimension under "
            f"gold_star.dimensions[].name or gold_star.date_dimension.name (schema "
            f"prefix stripped). Declared here: {known}"
        )
    return Finding(
        rule_id=RULE_ID,
        severity=Severity.ERROR,
        message=f"gold_placement {placement!r} {reason}",
        locator=f"{rel}:columns[].gold_placement",
    )


def _unreadable_finding(rel: str) -> Finding:
    """A tracked source-map that cannot be read is a broken governance artifact."""
    return Finding(
        rule_id=RULE_ID,
        severity=Severity.ERROR,
        message=(
            f"{rel} could not be read as YAML (undecodable bytes or invalid syntax); "
            "its gold_placement values cannot be checked, so the file must be fixed "
            "or removed"
        ),
        locator=rel,
    )


def _star_maps(ctx: RuleContext) -> tuple[list[tuple[str, dict]], list[Finding]]:
    """``(rel_path, document)`` for every committed source-map that IS a star, plus an
    ERROR finding for every tracked source-map path that failed to read/parse.

    ``discover_stars`` keys by star id and discards the path, but a finding must
    point at the FILE to fix, so this walks the same paths applying the SAME shared
    predicates (``source_map_table``, ``is_test_path``, ``is_star``) -- which keeps
    the template's placeholder placements and the test fixtures out of scope exactly
    as HR1 sees them, without a second copy of the path shape.

    Skipping an unreadable map silently made a corrupted, tracked governance artifact
    indistinguishable from "nothing to check here" -- a fail-open. Reporting is gated
    on ``_is_unreadable``, never on ``is_star`` being ``False``, so a legitimate
    compact-form or non-star map (which PARSES fine) stays silent.
    """
    found: list[tuple[str, dict]] = []
    findings: list[Finding] = []
    for rel in sorted(ctx.tracked_files):
        if is_test_path(rel) or _stars.source_map_table(rel) is None:
            continue
        document = _load_yaml(ctx, rel)
        if document is None and _is_unreadable(ctx, rel):
            findings.append(_unreadable_finding(rel))
            continue
        # A parseable non-mapping (empty file, bare scalar, top-level list) also
        # loads as None -- not reported, and not a star either.
        if document is None or not _stars.is_star(document):
            continue
        found.append((rel, document))
    return found, findings


@register(
    RULE_ID,
    "every dim: gold_placement prefix resolves to a declared dimension",
    requires=(_stars.SOURCE_MAP_CORPUS,),
)
def check_hr13(ctx: RuleContext) -> Iterable[Finding]:
    star_maps, findings = _star_maps(ctx)
    for rel, document in star_maps:
        declared = _declared_bare_names(document)
        for placement, prefix in _unresolved_placements(document):
            findings.append(_finding(rel, placement, prefix, declared))
    return findings
