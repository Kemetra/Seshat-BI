"""An unreadable tracked source-map is an ERROR, not a silent drop (#511 review).

PR #511 made HR1 degrade to ``None`` on an undecodable ``source-map.yaml`` instead of
raising, matching HR13. That fixed the crash (an exception escaping ``runner.run``
aborts the WHOLE ``retail check`` run), but it inherited HR13's pre-existing gap: both
rules' loaders return ``None``, and both callers treat ``None`` exactly like "this file
is not a star", so the corrupted artifact is simply skipped.

The review finding, restated as the scenario that matters:

    Two intended stars, one map corrupts. Discovery drops it. HR1 now sees ONE star,
    hits its ``len(stars) < 2`` FR-007 early return, and reports nothing. HR13 skips
    the same file. ``retail check`` exits 0. A governance gate has stopped checking
    conformance and said nothing -- the pre-#511 exception was at least LOUD.

So the fix is not "raise again" (that takes the gate down) and not "stay silent"
(that fails open). It is a third thing: report the unreadable artifact as an ERROR
finding and keep every other rule running.

Two invariants these tests pin, because getting either backwards reintroduces a defect:

  * an unreadable map ERRORs -- on BOTH rules, and REGARDLESS of how many stars
    survive (the finding must precede HR1's star-count threshold, or it is dead code
    in exactly the 2-stars-becomes-1 case the review described);
  * a map that merely fails ``is_star`` -- compact form, a non-star mapping, the
    template's placeholders -- stays SILENT. The trigger is a failed PARSE, never a
    failed ``is_star``, or the gate starts firing on correct repos.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.conformed_dimension import check_hr1
from seshat.rules.placement_resolution import check_hr13

pytestmark = pytest.mark.unit

# A minimal, VALID star. Two of these (differing only in table/fact/dim suffix) give
# HR1 the >=2 stars its cross-star limbs need.
_STAR = (
    "source_id: {sid}\n"
    "gold_star:\n"
    "  fact: gold.fct_{sid}\n"
    "  dimensions:\n"
    "    - name: gold.dim_shared\n"
    "      surrogate_key: shared_sk\n"
    "columns:\n"
    "  - source_column: item\n"
    "    silver_type: {stype}\n"
    "    gold_placement: dim:dim_shared.item\n"
)

# Invalid UTF-8: the byte 0xff never appears in a valid UTF-8 sequence, so
# `read_text` raises UnicodeDecodeError and the loader returns None.
_UNDECODABLE = b"source_id: s2\ncomment: \xff\xfe\n"

# Valid UTF-8, invalid YAML (unclosed flow mapping) -> yaml.YAMLError -> None.
_BAD_YAML = b"source_id: s2\ngold_star: {fact: gold.fct_s2\n"


def _rel(table: str) -> str:
    return f"mappings/{table}/source-map.yaml"


def _ctx(tmp_path: Path, files: dict[str, bytes]) -> RuleContext:
    """A context whose tracked files are exactly ``files`` (rel -> raw bytes)."""
    for rel, raw in files.items():
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(sorted(files)))


def _star_bytes(sid: str, stype: str = "text") -> bytes:
    return _STAR.format(sid=sid, stype=stype).encode("utf-8")


def _errors(findings) -> list:
    return [f for f in findings if f.severity is Severity.ERROR]


def _mentions(findings, rel: str) -> list:
    """Findings naming ``rel`` in the message or the locator."""
    return [f for f in findings if rel in f.message or rel in (f.locator or "")]


# --------------------------------------------------------------------------- #
# the review scenario: 2 stars -> 1 corrupts -> must NOT exit silent           #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("corrupt", [_UNDECODABLE, _BAD_YAML], ids=["utf8", "yaml"])
def test_hr1_reports_a_corrupt_second_map_instead_of_disengaging(
    tmp_path: Path, corrupt: bytes
) -> None:
    """THE regression. Pre-fix this returned [] -- the exact silent pass reported.

    With one valid star and one corrupt map, discovery yields a single star, so HR1's
    FR-007 threshold (`len(stars) < 2`) short-circuits. If the unreadable-map check
    sits after that return it never runs, which is why the fix reports FIRST.
    """
    ctx = _ctx(tmp_path, {_rel("s1"): _star_bytes("s1"), _rel("s2"): corrupt})

    findings = list(check_hr1(ctx))

    assert _errors(findings), "a corrupt tracked source-map passed HR1 silently"
    assert _mentions(findings, _rel("s2")), "the finding must name the broken file"


@pytest.mark.parametrize("corrupt", [_UNDECODABLE, _BAD_YAML], ids=["utf8", "yaml"])
def test_hr13_reports_a_corrupt_map_instead_of_skipping_it(
    tmp_path: Path, corrupt: bytes
) -> None:
    """HR13's half of the same gap -- it skipped unreadable maps before #511 too."""
    ctx = _ctx(tmp_path, {_rel("s1"): _star_bytes("s1"), _rel("s2"): corrupt})

    findings = list(check_hr13(ctx))

    assert _errors(findings), "a corrupt tracked source-map passed HR13 silently"
    assert _mentions(findings, _rel("s2")), "the finding must name the broken file"


def test_a_lone_corrupt_map_errors_even_with_no_surviving_star(tmp_path: Path) -> None:
    """The artifact is broken regardless of whether the cross-star limbs engage.

    Zero valid stars is the strongest form of HR1's early return, so this is the
    tightest check that the finding precedes it.
    """
    ctx = _ctx(tmp_path, {_rel("s2"): _UNDECODABLE})

    assert _errors(list(check_hr1(ctx))), "a lone corrupt map must still ERROR"
    assert _errors(list(check_hr13(ctx))), "a lone corrupt map must still ERROR"


def test_both_rules_agree_on_which_files_are_unreadable(tmp_path: Path) -> None:
    """#508's thesis, extended: two rules reading the same file must not disagree.

    #511 aligned their exception tuples; this pins that they also agree on the
    CONSEQUENCE -- one may not report where its twin stays silent.
    """
    ctx = _ctx(
        tmp_path,
        {
            _rel("s1"): _star_bytes("s1"),
            _rel("s2"): _UNDECODABLE,
            _rel("s3"): _BAD_YAML,
        },
    )

    hr1_named = {_rel("s2"), _rel("s3")}
    for rule in (check_hr1, check_hr13):
        named = {rel for rel in hr1_named if _mentions(list(rule(ctx)), rel)}
        assert named == hr1_named, f"{rule.__name__} missed one of {hr1_named}"


# --------------------------------------------------------------------------- #
# the other half: a PARSEABLE non-star must stay silent                        #
# --------------------------------------------------------------------------- #


def test_a_compact_non_star_map_is_not_reported(tmp_path: Path) -> None:
    """The trigger is a failed PARSE, never a failed ``is_star``.

    A compact-form map (no ``gold_star``) is a legitimate committed artifact -- it
    parses fine and is simply not a star. Firing here would break correct repos,
    which is the false-positive half of the fix.
    """
    compact = b"source_id: s2\ncolumns:\n  - source_column: item\n"
    ctx = _ctx(tmp_path, {_rel("s1"): _star_bytes("s1"), _rel("s2"): compact})

    assert _mentions(list(check_hr1(ctx)), _rel("s2")) == []
    assert _mentions(list(check_hr13(ctx)), _rel("s2")) == []


def test_an_empty_map_is_not_reported_as_unreadable(tmp_path: Path) -> None:
    """``yaml.safe_load("")`` returns None, but that is not a READ failure.

    The loaders funnel "parsed to a non-dict" through the same ``None`` return as a
    genuine parse error, so an empty file is the edge case most likely to produce a
    false positive. An empty committed map is a different rule's business.
    """
    ctx = _ctx(tmp_path, {_rel("s1"): _star_bytes("s1"), _rel("s2"): b""})

    assert _mentions(list(check_hr1(ctx)), _rel("s2")) == []
    assert _mentions(list(check_hr13(ctx)), _rel("s2")) == []


def test_two_valid_stars_still_produce_no_unreadable_finding(tmp_path: Path) -> None:
    """The happy path stays clean -- no finding invented for a readable repo."""
    ctx = _ctx(tmp_path, {_rel("s1"): _star_bytes("s1"), _rel("s2"): _star_bytes("s2")})

    for rule in (check_hr1, check_hr13):
        for finding in rule(ctx):
            assert "could not be read" not in finding.message, finding.message


def test_a_bom_prefixed_map_is_never_called_unreadable(tmp_path: Path) -> None:
    """#508 corrected the BOM premise; this keeps the new gate off that path.

    PyYAML strips a leading U+FEFF itself and both loaders now use ``utf-8-sig``, so
    a BOM'd map is fully readable. A gate that called it corrupt would fire on every
    Windows-authored map -- the exact false positive class this repo cares about.
    """
    ctx = _ctx(
        tmp_path,
        {
            _rel("s1"): _star_bytes("s1"),
            _rel("s2"): b"\xef\xbb\xbf" + _star_bytes("s2"),
        },
    )

    for rule in (check_hr1, check_hr13):
        assert _mentions(list(rule(ctx)), _rel("s2")) == []


# --------------------------------------------------------------------------- #
# the crash guarantee #511 bought must survive this change                     #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("corrupt", [_UNDECODABLE, _BAD_YAML], ids=["utf8", "yaml"])
def test_neither_rule_raises_on_an_unreadable_map(
    tmp_path: Path, corrupt: bytes
) -> None:
    """``runner.run`` calls ``registered.rule(ctx)`` UNGUARDED.

    Reporting must not be implemented by re-raising: an exception here aborts the
    entire ``retail check`` run and reports NOTHING, which is the defect #511 fixed.
    Both rules must return findings, not throw.
    """
    ctx = _ctx(tmp_path, {_rel("s1"): _star_bytes("s1"), _rel("s2"): corrupt})

    for rule in (check_hr1, check_hr13):
        findings = list(rule(ctx))  # must not raise
        assert all(f.rule_id in {"HR1", "HR13"} for f in findings)


def test_a_readable_star_is_still_evaluated_alongside_a_corrupt_sibling(
    tmp_path: Path,
) -> None:
    """Degradation must be PER-FILE, not per-run.

    A corrupt map may not suppress HR13's real findings on the maps that DO parse --
    otherwise one broken file blinds the gate to every other file's defects.
    """
    broken_placement = (
        "source_id: s1\n"
        "gold_star:\n"
        "  fact: gold.fct_s1\n"
        "  dimensions:\n"
        "    - name: gold.dim_shared\n"
        "columns:\n"
        "  - source_column: item\n"
        "    silver_type: text\n"
        "    gold_placement: dim:dim_nonexistent.item\n"
    ).encode("utf-8")
    ctx = _ctx(tmp_path, {_rel("s1"): broken_placement, _rel("s2"): _UNDECODABLE})

    findings = list(check_hr13(ctx))

    assert _mentions(findings, _rel("s2")), "the corrupt file must be reported"
    assert any("dim_nonexistent" in f.message for f in findings), (
        "a corrupt sibling suppressed a real finding on a readable map"
    )
