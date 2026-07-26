"""Regression tests for issue #499 (no gold_placement prefix ever resolved).

`columns[].gold_placement` values in the reference map named LOGICAL dimensions
(`dim:dim_product`) while `gold_star.dimensions[].name` / `date_dimension.name`
are PHYSICAL, schema-qualified and `_rss`-suffixed (`gold.dim_product_rss`). HR1
resolves a placement prefix from the PHYSICAL bare name -- deliberately, per its
own docstring -- so the two NEVER matched and `_attr_silver_types` returned `{}`
for EVERY dimension in the map.

Nobody noticed because the reader degrades gracefully and HR1's shared-attribute
type-divergence limb needs attributes shared by 2+ stars. This repo has ONE star,
so the empty typemap had nothing to compare -- a FAIL-OPEN on a cross-star
consistency rule, invisible until a second star lands.

Resolution (owner ruling): the PHYSICAL name is canonical in a placement. The
map's placements now name the physical dim, AND new rule HR13 ERRORs on any
`dim:` prefix that resolves to no declared dimension, so a typo is no longer
indistinguishable from a deliberate no-op.

Deliberately NOT done: suffix-tolerant / fuzzy prefix matching (fuzzy matching in
a governance rule preserves the exact ambiguity the assertion removes) and a
declared-alias field (new schema surface). Both were rejected by the ruling.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]
_REFERENCE_MAP = "mappings/retail_store_sales/source-map.yaml"


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _load_reference_map() -> dict:
    """The committed reference source-map, parsed."""
    import yaml

    return yaml.safe_load((_REPO / _REFERENCE_MAP).read_text(encoding="utf-8-sig"))


def _declared_dims(document: dict) -> list[dict]:
    """Every dimension the map declares: explicit dims plus the date dimension."""
    star = document["gold_star"]
    dims = list(star.get("dimensions") or [])
    date_dim = star.get("date_dimension")
    if isinstance(date_dim, dict):
        dims.append(date_dim)
    return dims


def _write(tmp_path: Path, rel: str, text: str) -> str:
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return rel


def _ctx(tmp_path: Path, *rel: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rel))


@dataclass(frozen=True)
class Star:
    """The parameters of a minimal one-dimension star fixture.

    Grouped into one value object rather than passed as six positional/keyword
    arguments, so the builder takes ONE parameter at every call site and adding a
    knob later does not widen the signature.

    ``placements`` maps source column -> gold_placement; ``types`` maps the same
    source column -> silver_type (defaulting to ``text``).
    """

    sid: str = "s1"
    fact: str = "fct_a"
    dim_name: str = "gold.dim_product_rss"
    surrogate: str = "product_sk"
    placements: Mapping[str, str] = field(default_factory=dict)
    types: Mapping[str, str] = field(default_factory=dict)


def _star_yaml(star: Star) -> str:
    """Render a `Star` as source-map YAML text."""
    lines = [f"source_id: {star.sid}"]
    if star.placements:
        lines.append("columns:")
        for col, placement in star.placements.items():
            lines.append(f"  - source_name: {col}")
            lines.append(f"    silver_type: {star.types.get(col, 'text')}")
            lines.append(f'    gold_placement: "{placement}"')
    lines += [
        "gold_star:",
        f"  fact: {star.fact}",
        "  dimensions:",
        f'    - name: "{star.dim_name}"',
        f"      surrogate_key: {star.surrogate}",
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# The reported defect: not one placement resolved                             #
# --------------------------------------------------------------------------- #


def test_every_declared_dimension_resolves_its_mapped_attributes() -> None:
    """The bug: `_attr_silver_types` returned {} for EVERY dimension in the map.

    All five declared dimensions must now yield a non-empty typemap from the
    committed map's own placements.
    """
    from seshat.rules.conformed_dimension import _attr_silver_types
    from seshat.star_discovery import bare_dim_name, star_dimensions

    document = _load_reference_map()
    dims = star_dimensions(document)
    assert len(dims) == 5, f"expected 5 declared dimensions, got {sorted(dims)}"

    empty = []
    for bare, dim in dims.items():
        resolved = _attr_silver_types(document, bare_dim_name(dim["name"]) or bare)
        if not resolved:
            empty.append(bare)

    assert empty == [], f"dimensions still resolving no attributes at all: {empty}"


@pytest.mark.parametrize(
    ("dim_bare", "expected"),
    [
        ("dim_customer_rss", {"customer_id": "text"}),
        ("dim_product_rss", {"category": "text", "item": "text"}),
        ("dim_payment_method_rss", {"payment_method": "text"}),
        ("dim_location_rss", {"location": "text"}),
        ("dim_date_rss", {"full_date": "date"}),
    ],
)
def test_each_dimension_resolves_exactly_its_mapped_columns(
    dim_bare: str, expected: dict[str, str]
) -> None:
    """Per-dimension proof, pinning the resolved attribute names AND their types."""
    from seshat.rules.conformed_dimension import _attr_silver_types

    assert _attr_silver_types(_load_reference_map(), dim_bare) == expected


def test_no_placement_in_the_reference_map_names_an_undeclared_dimension() -> None:
    """Every `dim:` prefix in the committed map resolves to a declared dimension."""
    from seshat.rules.placement_resolution import _unresolved_placements

    assert _unresolved_placements(_load_reference_map()) == []


def test_the_reference_map_uses_physical_not_logical_dim_names() -> None:
    """The ruling: PHYSICAL is canonical -- every prefix IS a declared dim name.

    Stated as the governance invariant (the prefix set is a subset of the declared
    physical names) rather than a string-suffix check, which would only encode one
    star's `_rss` naming accident. Uses the production prefix parser so the test
    cannot drift from the code it guards.
    """
    from seshat.rules.placement_resolution import _placement_prefix

    document = _load_reference_map()
    prefixes = {
        p
        for c in document["columns"]
        if (p := _placement_prefix(c.get("gold_placement"))) is not None
    }
    declared = {d["name"].rsplit(".", 1)[-1] for d in _declared_dims(document)}

    assert prefixes, "the reference map declares no dim: placements at all"
    assert prefixes <= declared, (
        f"placements name dimensions the star does not declare: {prefixes - declared}; "
        "the physical declared name is canonical per the #499 ruling"
    )
    # and the logical (unsuffixed) forms the map used to carry are gone
    assert not (prefixes & {"dim_product", "dim_customer", "dim_date"})


# --------------------------------------------------------------------------- #
# HR13: an unresolvable prefix now FAILS LOUDLY                               #
# --------------------------------------------------------------------------- #


def test_hr13_errors_on_an_unresolvable_placement_prefix(tmp_path: Path) -> None:
    """The real defect: a typo was indistinguishable from a deliberate no-op."""
    from seshat.rules.placement_resolution import check_hr13

    rel = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name="gold.dim_product_rss",
                placements={
                    "item": "dim:dim_product.item"
                },  # LOGICAL -> resolves to none
            )
        ),
    )
    findings = list(check_hr13(_ctx(tmp_path, rel)))

    assert len(findings) == 1
    assert findings[0].rule_id == "HR13"
    assert findings[0].severity is Severity.ERROR
    assert "dim_product" in findings[0].message
    # the finding must name the declared alternative so a suffix drift is obvious
    assert "dim_product_rss" in findings[0].message
    assert findings[0].locator.startswith("mappings/s1/source-map.yaml")


def test_hr13_clears_a_placement_naming_the_physical_dim(tmp_path: Path) -> None:
    from seshat.rules.placement_resolution import check_hr13

    rel = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name="gold.dim_product_rss",
                placements={"item": "dim:dim_product_rss.item"},
            )
        ),
    )
    assert list(check_hr13(_ctx(tmp_path, rel))) == []


def test_hr13_resolves_a_prefix_against_the_date_dimension(tmp_path: Path) -> None:
    """`date_dimension` is a declared dimension too, not only `dimensions[]`."""
    from seshat.rules.placement_resolution import check_hr13

    text = (
        "source_id: s1\n"
        "columns:\n"
        "  - source_name: transaction_date\n"
        "    silver_type: date\n"
        '    gold_placement: "dim:dim_date_rss.full_date"\n'
        "gold_star:\n"
        "  fact: fct_a\n"
        "  date_dimension:\n"
        '    name: "gold.dim_date_rss"\n'
        "    surrogate_key: date_sk\n"
    )
    rel = _write(tmp_path, "mappings/s1/source-map.yaml", text)

    assert list(check_hr13(_ctx(tmp_path, rel))) == []


def test_hr13_never_validates_the_attribute_half(tmp_path: Path) -> None:
    """Prefix-only by design: an RC15 date dim declares NO `attributes` key.

    Attribute-level validation would fire on a correct map, because a date
    dimension's calendar columns are GENERATED, not declared (#491).
    """
    from seshat.rules.placement_resolution import check_hr13

    rel = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name="gold.dim_product_rss",
                # `not_a_declared_attribute` is not in any attributes[] -- still fine
                placements={"item": "dim:dim_product_rss.not_a_declared_attribute"},
            )
        ),
    )
    assert list(check_hr13(_ctx(tmp_path, rel))) == []


@pytest.mark.parametrize("placement", ["fact_measure", "degenerate_dim", "dropped"])
def test_hr13_ignores_non_dimension_placements(tmp_path: Path, placement: str) -> None:
    """EVERY legitimate non-dimension placement must pass silently.

    This is the false-positive guard on the closed-list hardening: the three legal
    non-dim values are enumerated in `_NON_DIM_PLACEMENTS`, and if that list ever
    drifts from `templates/source-map.yaml` this test fails rather than a valid map
    suddenly ERRORing. These three are the WHOLE exempt set -- a nameless `dim:` is
    NOT exempt (see `test_hr13_reports_a_marker_level_typo`).
    """
    from seshat.rules.placement_resolution import check_hr13

    rel = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name="gold.dim_product_rss",
                placements={"col": placement},
            )
        ),
    )
    assert list(check_hr13(_ctx(tmp_path, rel))) == []


@pytest.mark.parametrize(
    ("declared", "placement"),
    [
        # placement is SHORTER than the declared name (the real #499 shape)
        ("gold.dim_product_rss", "dim:dim_product.item"),
        # placement is LONGER than the declared name (the mirror image)
        ("gold.dim_product", "dim:dim_product_rss.item"),
    ],
)
def test_hr13_never_matches_a_prefix_by_suffix_tolerance(
    tmp_path: Path, declared: str, placement: str
) -> None:
    """The REJECTED alternative must stay rejected, in BOTH directions.

    Fuzzy/suffix-tolerant matching in a governance rule preserves the exact
    ambiguity the assertion exists to remove. Parametrized over both orderings so
    the test would catch suffix tolerance introduced either way -- a single
    direction would be satisfied by the plain unresolvable-prefix case.
    """
    from seshat.rules.placement_resolution import check_hr13

    rel = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name=declared,
                placements={"item": placement},
            )
        ),
    )
    findings = list(check_hr13(_ctx(tmp_path, rel)))

    assert len(findings) == 1, "a near-miss prefix must NOT be tolerated"


# --------------------------------------------------------------------------- #
# The gate must be no LOOSER than the reader it protects                      #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "placement",
    [
        "dim:DIM_Product_RSS.item",  # wrong case
        "dim: dim_product_rss.item",  # leading whitespace in the prefix
        "dim:dim_product_rss .item",  # trailing whitespace in the prefix
        "dim:dim_product_rss",  # no delimiter, so no attribute
        "dim:dim_product_rss.",  # delimiter but EMPTY attribute
        "dim:gold.dim_product_rss.item",  # schema-qualified: prefix is 'gold'
    ],
)
def test_hr13_reports_every_shape_the_consumer_cannot_resolve(
    tmp_path: Path, placement: str
) -> None:
    """A gate looser than its reader certifies placements that resolve to nothing.

    Each shape below names the declared dimension only under a normalization HR1's
    exact `startswith(f"dim:{name}.")` match does NOT perform, so the consumer
    contributes nothing (or, for the trailing dot, a bogus empty-string attribute --
    worse than nothing, since it enters HR1's cross-star comparison set). All must
    ERROR, or #499's fail-open survives inside the very rule meant to close it.
    """
    from seshat.rules.conformed_dimension import _attr_silver_types
    from seshat.rules.placement_resolution import check_hr13

    text = _star_yaml(
        Star(
            sid="s1",
            fact="fct_a",
            dim_name="gold.dim_product_rss",
            placements={"item": placement},
        )
    )
    rel = _write(tmp_path, "mappings/s1/source-map.yaml", text)

    import yaml

    document = yaml.safe_load(text)
    resolved = _attr_silver_types(document, "dim_product_rss")
    assert resolved in ({}, {"": "text"}), (
        f"premise broken: the consumer DOES resolve {placement!r} -> {resolved}"
    )

    findings = list(check_hr13(_ctx(tmp_path, rel)))
    assert len(findings) == 1, f"HR13 accepted {placement!r}, which resolves nothing"


def test_hr13_distinguishes_an_undeclared_dim_from_a_malformed_reference(
    tmp_path: Path,
) -> None:
    """The message must not send an author hunting the wrong thing.

    A correctly-named dimension typed in the wrong CASE is not "undeclared" -- saying
    so would be false and misdirecting. Two causes, two messages.
    """
    from seshat.rules.placement_resolution import check_hr13

    undeclared = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name="gold.dim_product_rss",
                placements={"i": "dim:nope.item"},
            )
        ),
    )
    malformed = _write(
        tmp_path,
        "mappings/s2/source-map.yaml",
        _star_yaml(
            Star(
                sid="s2",
                fact="fct_b",
                dim_name="gold.dim_product_rss",
                placements={"i": "dim:DIM_PRODUCT_RSS.item"},
            )
        ),
    )

    (a,) = list(check_hr13(_ctx(tmp_path, undeclared)))
    assert "does not declare" in a.message
    assert "dim_product_rss" in a.message  # names the alternatives

    (b,) = list(check_hr13(_ctx(tmp_path, malformed)))
    assert "does not declare" not in b.message, (
        "the dimension IS declared; only the reference form is wrong"
    )
    assert "same case" in b.message


@pytest.mark.parametrize(
    "placement",
    [
        "DIM:dim_product_rss.item",  # marker upper-cased
        "Dim:dim_product_rss.item",  # marker title-cased
        "dim :dim_product_rss.item",  # space before the colon
        " dim:dim_product_rss.item",  # leading space on the whole value
        "dims:dim_product_rss.item",  # misspelled marker
        "dim.dim_product_rss.item",  # '.' instead of ':'
        "fact_measures",  # typo'd non-dim value
        "FACT_MEASURE",  # wrong case
        "degenerate",  # truncated
        "droped",  # misspelled
        "",  # empty string is not a legal value
        "totally_unknown_value",
        # a `dim:` naming NO dimension: the enum is `dim:<dim_name>.<attr>`, so a
        # nameless reference is not legal either, and HR1 resolves nothing from it.
        "dim:",
        "dim:.attr",
        "dim:.",
    ],
)
def test_hr13_reports_a_marker_level_typo(tmp_path: Path, placement: str) -> None:
    """A "not a dimension placement" verdict must come from a CLOSED list.

    A MARKER typo is the same fail-open as a bad prefix, one level up: HR1 resolves
    nothing from `DIM:dim_product_rss.item`, so if HR13 shrugs and calls it "some
    other kind of placement" the value silently does nothing in every reader. Only
    the three enumerated non-dim values may pass; anything else is reported --
    including a nameless `dim:`, whose exemption would be an arbitrary hole in the
    closed list.
    """
    from seshat.rules.conformed_dimension import _attr_silver_types
    from seshat.rules.placement_resolution import check_hr13

    star = Star(placements={"item": placement})
    text = _star_yaml(star)
    rel = _write(tmp_path, "mappings/s1/source-map.yaml", text)

    import yaml

    assert _attr_silver_types(yaml.safe_load(text), "dim_product_rss") == {}, (
        "premise broken: the consumer resolves this value after all"
    )

    findings = list(check_hr13(_ctx(tmp_path, rel)))
    assert len(findings) == 1, f"HR13 silently accepted {placement!r}"
    assert "not a legal placement value" in findings[0].message


def test_the_non_dim_placement_enum_matches_the_template() -> None:
    """The closed list is only safe while it agrees with the documented enum.

    `templates/source-map.yaml` states the enum; if a value is added there and not
    here, HR13 would ERROR on a valid map. Pin the two together.
    """
    from seshat.rules.placement_resolution import _NON_DIM_PLACEMENTS

    template = (_REPO / "templates" / "source-map.yaml").read_text(encoding="utf-8-sig")
    line = next(
        ln for ln in template.splitlines() if "gold_placement  fact_measure" in ln
    )
    documented = {
        tok.strip()
        for tok in line.split("gold_placement", 1)[1].split("|")
        if tok.strip() and "dim:" not in tok
    }

    assert documented == _NON_DIM_PLACEMENTS, (
        f"template enum {documented} != rule's closed list {_NON_DIM_PLACEMENTS}"
    )


def test_hr13_does_not_crash_on_an_undecodable_map(tmp_path: Path) -> None:
    """A rule degrades on an unreadable artifact; it never takes the gate down.

    `UnicodeDecodeError` is a ValueError, not an OSError, so an exception tuple
    catching only OSError lets one bad byte in any committed map propagate out and
    crash the whole `retail check` run. Mirrors HR11's posture.

    "Degrades" means "does not RAISE", not "reports nothing": dropping the map in
    silence is a fail-open, so an unreadable map is an ERROR finding (#511 review),
    pinned in `test_issue_regression_511_unreadable_map.py`. The crash guarantee is
    asserted directly here rather than via `== []`, which pinned the fail-open.
    """
    from seshat.core import Severity
    from seshat.rules.placement_resolution import check_hr13

    rel = "mappings/s1/source-map.yaml"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(
        b"source_id: s1\ncomment: \xff\xfe bad utf8\ngold_star:\n  fact: f\n"
    )

    findings = list(check_hr13(_ctx(tmp_path, rel)))  # must not raise

    assert [f for f in findings if f.severity is Severity.ERROR], (
        "an unreadable map was dropped without being reported"
    )
    assert all(rel in (f.locator or "") for f in findings)


def test_hr13_is_silent_on_a_compact_map_with_no_columns(tmp_path: Path) -> None:
    """Absence is not drift -- the compact form declares no placements at all."""
    from seshat.rules.placement_resolution import check_hr13

    text = (
        "source_id: s1\n"
        "gold_star:\n"
        "  fact: fct_order_line\n"
        "  dimensions:\n"
        '    - name: "dim_product"\n'
    )
    rel = _write(tmp_path, "mappings/s1/source-map.yaml", text)

    assert list(check_hr13(_ctx(tmp_path, rel))) == []


def test_hr13_engages_on_a_single_star(tmp_path: Path) -> None:
    """The whole point: HR1 needs 2+ stars, so the assertion cannot live there.

    A per-map integrity defect must be caught on a one-star repo -- which is the
    state that hid this bug for the entire life of the reference map.
    """
    from seshat.rules.conformed_dimension import check_hr1
    from seshat.rules.placement_resolution import check_hr13

    rel = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name="gold.dim_product_rss",
                placements={"item": "dim:dim_product.item"},
            )
        ),
    )
    ctx = _ctx(tmp_path, rel)

    assert list(check_hr1(ctx)) == [], "HR1 correctly stays inert on one star"
    assert len(list(check_hr13(ctx))) == 1, "HR13 must fire regardless of star count"


def test_hr13_skips_the_template_and_test_fixtures(tmp_path: Path) -> None:
    """The template's placeholder placements are not a real map's defect."""
    from seshat.rules.placement_resolution import check_hr13

    body = _star_yaml(
        Star(
            sid="s1",
            fact="fct_a",
            dim_name="gold.dim_product_rss",
            placements={"item": "dim:nope.item"},
        )
    )
    template = _write(tmp_path, "templates/source-map.yaml", body)
    fixture = _write(tmp_path, "tests/fixtures/sourcemap/filled.source-map.yaml", body)

    assert list(check_hr13(_ctx(tmp_path, template, fixture))) == []


def test_hr13_names_every_offending_placement_not_just_the_first(
    tmp_path: Path,
) -> None:
    from seshat.rules.placement_resolution import check_hr13

    rel = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name="gold.dim_product_rss",
                placements={
                    "item": "dim:dim_product.item",
                    "category": "dim:dim_category.category",
                },
            )
        ),
    )
    findings = list(check_hr13(_ctx(tmp_path, rel)))

    assert len(findings) == 2
    assert {"dim_product", "dim_category"} <= {
        w.strip("'\",") for f in findings for w in f.message.split()
    }


# --------------------------------------------------------------------------- #
# The real regression: HR1's type limb now actually WORKS                     #
# --------------------------------------------------------------------------- #


def test_hr1_type_limb_reports_divergence_across_two_stars(tmp_path: Path) -> None:
    """THE fail-open proof.

    Two stars share a conformed dimension whose `item` attribute has a DIFFERENT
    silver_type on each side. With logical placements this limb compared two empty
    typemaps and silently passed; with physical placements it must REPORT.
    """
    from seshat.rules.conformed_dimension import check_hr1

    a = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name="gold.dim_product_rss",
                placements={"item": "dim:dim_product_rss.item"},
                types={"item": "text"},
            )
        ),
    )
    b = _write(
        tmp_path,
        "mappings/s2/source-map.yaml",
        _star_yaml(
            Star(
                sid="s2",
                fact="fct_b",
                dim_name="gold.dim_product_rss",
                placements={"item": "dim:dim_product_rss.item"},
                types={"item": "numeric(12,2)"},  # DIVERGENT
            )
        ),
    )
    decl = _write(
        tmp_path,
        "docs/quality/conformed-dimension-map.yaml",
        "dimensions:\n  dim_product_rss:\n    status: conformed\n    stars: [s1, s2]\n",
    )
    findings = list(check_hr1(_ctx(tmp_path, a, b, decl)))

    assert len(findings) == 1, f"type divergence went undetected: {findings}"
    assert findings[0].rule_id == "HR1"
    assert findings[0].severity is Severity.ERROR
    assert "item" in findings[0].message
    assert "silver_type differs" in findings[0].message
    assert "text" in findings[0].message and "numeric(12,2)" in findings[0].message


def test_hr1_type_limb_is_inert_when_placements_are_logical(tmp_path: Path) -> None:
    """The PRE-FIX behavior, pinned as the thing that must never come back.

    Same two divergent stars, but each map's placement names the LOGICAL dim. Both
    typemaps resolve empty, so HR1 compares nothing and passes -- a fail-open. This
    test documents that HR13 is what makes this state unreachable in a committed
    map: the maps below would ERROR at HR13 before HR1 ever ran.
    """
    from seshat.rules.conformed_dimension import check_hr1
    from seshat.rules.placement_resolution import check_hr13

    a = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name="gold.dim_product_rss",
                placements={"item": "dim:dim_product.item"},  # logical
                types={"item": "text"},
            )
        ),
    )
    b = _write(
        tmp_path,
        "mappings/s2/source-map.yaml",
        _star_yaml(
            Star(
                sid="s2",
                fact="fct_b",
                dim_name="gold.dim_product_rss",
                placements={"item": "dim:dim_product.item"},  # logical
                types={"item": "numeric(12,2)"},  # DIVERGENT, but never compared
            )
        ),
    )
    decl = _write(
        tmp_path,
        "docs/quality/conformed-dimension-map.yaml",
        "dimensions:\n  dim_product_rss:\n    status: conformed\n    stars: [s1, s2]\n",
    )
    ctx = _ctx(tmp_path, a, b, decl)

    # HR1 alone: fail-open, exactly as before the fix.
    assert list(check_hr1(ctx)) == []
    # HR13 is the gate that stops this tree from ever being committed.
    assert len(list(check_hr13(ctx))) == 2


def test_hr1_type_limb_clears_when_the_shared_type_agrees(tmp_path: Path) -> None:
    """The limb must not fire on agreement -- it compares, it does not just alarm."""
    from seshat.rules.conformed_dimension import check_hr1

    a = _write(
        tmp_path,
        "mappings/s1/source-map.yaml",
        _star_yaml(
            Star(
                sid="s1",
                fact="fct_a",
                dim_name="gold.dim_product_rss",
                placements={"item": "dim:dim_product_rss.item"},
                types={"item": "text"},
            )
        ),
    )
    b = _write(
        tmp_path,
        "mappings/s2/source-map.yaml",
        _star_yaml(
            Star(
                sid="s2",
                fact="fct_b",
                dim_name="gold.dim_product_rss",
                placements={"item": "dim:dim_product_rss.item"},
                types={"item": "text"},  # agrees
            )
        ),
    )
    decl = _write(
        tmp_path,
        "docs/quality/conformed-dimension-map.yaml",
        "dimensions:\n  dim_product_rss:\n    status: conformed\n    stars: [s1, s2]\n",
    )
    assert list(check_hr1(_ctx(tmp_path, a, b, decl))) == []


# --------------------------------------------------------------------------- #
# #491 coherence: the two fixes cover disjoint attribute sets                  #
# --------------------------------------------------------------------------- #


def test_the_491_generated_calendar_set_is_not_reachable_via_placements() -> None:
    """#491's approach is NOT made redundant by this fix.

    #491 resolves a date dimension's NINE generated calendar attributes, which have
    no source column and therefore no placement. This fix resolves the ONE mapped
    column that lands on the date dim (`full_date`). The sets are disjoint apart
    from that overlap, so nothing about #491's generated-calendar approach becomes
    unnecessary and it must not be ripped out.
    """
    from seshat.rules.conformed_dimension import _attr_silver_types
    from seshat.star_discovery import RC15_CALENDAR_ATTRIBUTES

    resolved = set(_attr_silver_types(_load_reference_map(), "dim_date_rss"))

    assert resolved == {"full_date"}
    # eight of the nine generated attributes remain unreachable via placements
    assert RC15_CALENDAR_ATTRIBUTES - resolved == {
        "year",
        "quarter",
        "month",
        "month_name",
        "day",
        "day_name",
        "iso_week",
        "is_weekend",
    }
