"""Shared star-discovery primitives (issue #418).

A TOP-LEVEL module (sibling of ``seshat.core``), deliberately NOT under
``seshat.dbt``: it is consumed by both the ``seshat.rules`` static-core gate
(HR1) and the ``seshat.dbt`` scaffold, and importing it must never drag
``seshat.dbt`` onto the base-CLI import path (spec 135 T003 / spec 134 FR-001 --
``import seshat.cli`` loads no governed dbt adapter). Placing it here keeps both
consumers above it and the CLI-laziness contract intact.

Pure and dependency-free: NO database driver, NO ``seshat.rules`` /
``RuleContext`` import, and ``yaml`` is never needed here (callers parse YAML
themselves and inject a ``load`` callable). Both HR1 (worktree read via its
``RuleContext``) and ``seshat dbt scaffold`` (committed ``git show HEAD:`` read)
consume this, so the governance gate and the generator can never disagree on
what a star is, how a star id resolves, or which dimensions a star declares.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from seshat.core import is_test_path

_MAPPING_RE = re.compile(r"^mappings/([^/]+)/source-map\.yaml$")


def source_map_table(rel: str) -> str | None:
    """The ``<table>`` a ``mappings/<table>/source-map.yaml`` path names, else None.

    The ONE definition of "this path is a source-map" (issue #499). ``discover_stars``
    returns documents keyed by star id and discards the path, so a rule whose finding
    must point at the FILE (HR13) needs this predicate rather than a second regex --
    duplicating the shape is how the gate and the generator drift apart.
    """
    m = _MAPPING_RE.match(rel)
    return m.group(1) if m else None


def bare_dim_name(name: object) -> str | None:
    """Bare dimension name: strip an optional ``<schema>.`` prefix, lowercased."""
    if not isinstance(name, str) or not name.strip():
        return None
    return name.rsplit(".", 1)[-1].strip().lower()


# The attribute set an RC15 date dimension carries, declared ONCE so neither the
# readers nor the BUILDERS invent their own (issues #491 and #497). A Seshat date
# dimension is a CONTIGUOUS calendar generated over the approved span -- these
# columns are DERIVED from the calendar, not mapped from a source column, so no
# `columns[].gold_placement` can ever point at them. That is precisely why a reader
# that only looks at declared attributes reports every date attribute absent (#491).
#
# This is the FULL calendar and the default set. A map MAY narrow which of these
# columns its star materializes via `date_dimension.attributes` -- resolved for
# every consumer by `resolve_date_attributes` below, never by a consumer's own list.
#
# The surrogate key is NOT here: it is declared per-map as
# `date_dimension.surrogate_key` and read from there.
#
# Kept in sync with the reference star `warehouse/migrations/0004_*.sql`
# (gold.dim_date_rss), which is the de-facto definition of a Seshat calendar.
# `tests/unit/test_issue_regression_491.py` asserts the two agree, so this cannot
# drift silently.
#
# ORDER MATTERS for the build half (issue #497): a generated dbt model's SELECT
# list IS its governed output contract, and the committed `_models.yml` column
# order is reviewed. So the declaration is an ordered TUPLE in the reference DDL's
# own column order, and the set below is DERIVED from it -- one declaration, two
# shapes, and a reader that needs order never has to invent one (sorting would
# yield `day` first and make it the business key, which is not a calendar's key).
RC15_CALENDAR_COLUMNS: tuple[str, ...] = (
    "full_date",
    "year",
    "quarter",
    "month",
    "month_name",
    "day",
    "day_name",
    "iso_week",
    "is_weekend",
)

RC15_CALENDAR_ATTRIBUTES: frozenset[str] = frozenset(RC15_CALENDAR_COLUMNS)


class CalendarContractError(ValueError):
    """A ``date_dimension`` declares an attribute the RC15 calendar cannot build."""


def resolve_date_attributes(date_dim: object) -> tuple[str, ...]:
    """The ordered calendar attributes ONE date dimension carries (issue #497).

    THE single resolver for "what columns does this date dimension have". Both
    consumers call it -- ``dbt/scaffold/model_plan`` to BUILD the model and
    ``gap_detector`` to decide which columns a star makes AVAILABLE -- so the
    generator and the reader can never disagree about a calendar. Before this
    existed, ``model_plan`` held a private six-entry ``_DATE_COLUMNS`` tuple that
    silently omitted ``month_name``/``day_name``/``is_weekend``, which
    ``warehouse/migrations/0004_*.sql`` builds: the same approved map produced a
    structurally DIFFERENT date dimension on the two build paths, and nothing
    detected it (the parity audit compares values only -- issue #492). A second
    hardcoded list IS that defect, so neither consumer may keep one.

    Returns the surrogate-key-FREE attribute tuple, in emission order. The
    surrogate key is declared per-map as ``surrogate_key`` and each consumer adds
    it in the position its own surface needs (the builder emits it first, so the
    date-spine SQL renderer stays dispatchable on ``columns[0]``).

    DEFAULT WHEN ``attributes`` IS ABSENT: the full ``RC15_CALENDAR_COLUMNS``. This
    upholds the #491 ruling (a date dimension's attributes are the RC15 GENERATED
    calendar set plus its declared surrogate key) and it is the set the reference
    migration DDL builds. No tracked map declares ``attributes``, so this default
    governs every existing map -- which is exactly why it must equal the migrations
    set rather than the old six, or the divergence would only move.

    A DECLARED ``attributes`` list NARROWS the calendar to those columns, in the
    declared order. Because both consumers resolve through here, narrowing stays
    consistent: the reader stops claiming a column the builder no longer builds.
    Honoring the key in ONE consumer is what the #491 ruling forbade; honoring it
    in the shared resolver is what makes it safe.

    An attribute OUTSIDE the RC15 set raises ``CalendarContractError``. RC15 is the
    authority for what a calendar CONTAINS; ``attributes`` selects from it and
    cannot invent a column. The calendar is generated by ``generate_series`` over
    the approved span, so an off-contract attribute has no source column to derive
    from and nothing could build it -- fail closed rather than let the two surfaces
    drift apart again.
    """
    if not isinstance(date_dim, dict):
        return ()
    resolved = _declared_calendar_names(date_dim.get("attributes"))
    if not resolved:
        return RC15_CALENDAR_COLUMNS
    _reject_off_contract(resolved)
    return resolved


def _declared_calendar_names(declared: object) -> tuple[str, ...]:
    """A ``date_dimension.attributes`` value as de-duplicated, stripped names.

    Empty tuple means "nothing usable was declared", which the caller reads as
    "use the default calendar" -- absent, null, a non-list, and a list of blanks
    are all the same instruction.
    """
    names = [declared] if isinstance(declared, str) else declared
    if not isinstance(names, list):
        return ()
    return tuple(
        dict.fromkeys(n.strip() for n in names if isinstance(n, str) and n.strip())
    )


def _reject_off_contract(names: tuple[str, ...]) -> None:
    """Fail closed on any name RC15 cannot generate (see the resolver's docstring)."""
    unknown = [n for n in names if n not in RC15_CALENDAR_ATTRIBUTES]
    if not unknown:
        return
    listed = ", ".join(repr(n) for n in unknown)
    raise CalendarContractError(
        f"date_dimension declares attribute(s) {listed} that are not part of "
        f"the RC15 generated calendar ({', '.join(RC15_CALENDAR_COLUMNS)}). A "
        "calendar is generated over the approved span, so there is no source "
        "column to derive these from; drop them or extend the governed "
        "calendar contract."
    )


def star_id(document: dict, table_dir: str) -> str:
    """The governed star id: ``meta.table_id`` -> ``source_id`` -> ``table_dir``."""
    meta = document.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("table_id"), str):
        return meta["table_id"]
    if isinstance(document.get("source_id"), str):
        return document["source_id"]
    return table_dir


def is_star(document: dict) -> bool:
    gs = document.get("gold_star")
    return isinstance(gs, dict) and gs.get("fact") is not None


def _add_dim(out: dict[str, dict], raw: object, *, overwrite: bool) -> None:
    if not isinstance(raw, dict):
        return
    b = bare_dim_name(raw.get("name"))
    if not b:
        return
    if overwrite:
        out[b] = raw
    else:
        out.setdefault(b, raw)


def star_dimensions(document: dict) -> dict[str, dict]:
    """bare-name -> raw dim dict (explicit dims + date_dimension; degenerate excluded).

    Explicit dims are last-wins; the standalone ``date_dimension`` is first-wins
    (never displaces an explicit dim). Degenerate dimensions are never traversed.
    """
    out: dict[str, dict] = {}
    gs = document.get("gold_star")
    if not isinstance(gs, dict):
        return out
    dims = gs.get("dimensions")
    if isinstance(dims, list):
        for dim in dims:
            _add_dim(out, dim, overwrite=True)
    _add_dim(out, gs.get("date_dimension"), overwrite=False)
    return out


# The reserved key under which a per-star dimension map records WHICH bare name that
# star reaches through its `date_dimension` slot (issue #497). Not a legal bare
# dimension name (`bare_dim_name` lowercases and strips, and a dim name is a SQL
# identifier), so it can never collide with a real entry.
#
# Carried INSIDE the per-star map rather than beside it on purpose: a separate
# optional argument can be omitted by a caller, and an omitted classification
# silently degrades a calendar to an entity dim -- which is exactly the asymmetry
# this key exists to make impossible.
DATE_SLOT_KEY = "#date_slot"


def star_dimension_view(document: dict) -> dict[str, dict]:
    """:func:`star_dimensions` plus the star's date-slot classification (#497).

    The value under :data:`DATE_SLOT_KEY` is the bare name this star declares as its
    ``date_dimension`` (or ``None``), so a cross-star consumer can resolve EACH
    side's attributes by the build path that side actually uses. Reading a date
    dimension's ``attributes`` raw expands a defaulted calendar to nothing; applying
    a calendar default to an ENTITY dim invents columns ``_dimension_model`` never
    builds. Both are wrong, in opposite directions.
    """
    view: dict[str, dict] = dict(star_dimensions(document))
    view[DATE_SLOT_KEY] = {"name": date_dimension_name(document)}
    return view


def date_slot_of(star_view: dict[str, dict] | None) -> str | None:
    """The date-slot bare name recorded in a per-star dimension view, if any."""
    if not isinstance(star_view, dict):
        return None
    marker = star_view.get(DATE_SLOT_KEY)
    return marker.get("name") if isinstance(marker, dict) else None


def date_dimension_name(document: dict) -> str | None:
    """The bare name of the star's ``gold_star.date_dimension``, if it owns that
    slot outright (issue #497).

    Needed because a date dimension's attribute set is RESOLVED (the RC15 default
    when the map declares none) while an entity dimension's is exactly what it
    declares. Any consumer comparing attributes ACROSS stars -- the conformed-reuse
    reconciler included -- must know which rule applies, or a defaulted calendar
    reads as carrying ZERO attributes and reconciliation draws the wrong conclusion
    in BOTH directions: a default-full owner looks like it carries nothing, and a
    narrowed owner wrongly passes against a default-full reuser.

    Decided by the SLOT, not by guessing at shape. Returns ``None`` when an
    explicit ``dimensions[]`` entry shadows the date name, because
    :func:`star_dimensions` is last-wins for explicit dims -- the dict that survives
    is then the ENTITY dim and must be reconciled as one.
    """
    slot: dict[str, dict] = {}
    gs = document.get("gold_star")
    _add_dim(
        slot, gs.get("date_dimension") if isinstance(gs, dict) else None, overwrite=True
    )
    # `star_dimensions` is last-wins for explicit dims, so the date slot only
    # survives if no explicit entry shadows its name -- compare by identity.
    resolved = star_dimensions(document)
    return next(
        (b for b, raw in slot.items() if resolved.get(b) is raw),
        None,
    )


def discover_stars(
    tracked_files: Iterable[str],
    load: Callable[[str], dict | None],
) -> dict[str, dict]:
    """``{star_id: document}`` for every non-test ``mappings/<dir>/source-map.yaml``
    that ``load`` returns and that ``is_star``.

    ``load`` (returning ``None`` on any parse/read failure) is the caller's I/O
    strategy -- HR1 reads the worktree via its ``RuleContext``; scaffold reads the
    committed HEAD blob via ``git show``. Keeping I/O injected leaves this module
    dependency-free and lets both callers share one definition of star identity.
    """
    found: dict[str, dict] = {}
    for rel in sorted(tracked_files):
        if is_test_path(rel):
            continue
        table = source_map_table(rel)
        if table is None:
            continue
        data = load(rel)
        if data is None or not is_star(data):
            continue
        found[star_id(data, table)] = data
    return found
