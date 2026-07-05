"""HR1 -- cross-star conformed-dimension conformance (spec 087, Principle III).

A MODEL-LEVEL gate, orthogonal to the per-table readiness spine. Constitution
Principle III says ``gold`` MUST be a Kimball star -- "fact + conformed
dimensions". Per-table rules check one star in isolation; nothing checks that a
dimension shared across MORE THAN ONE star (e.g. ``dim_product`` in both a sales
star and a returns star) is actually the SAME dimension. HR1 closes that gap.

What HR1 does (STATIC, fail-closed; engages only when >=2 stars exist):
  - Discovers each star by reading every committed
    ``mappings/<table>/source-map.yaml`` that carries a ``gold_star.fact`` key,
    and collects that star's dimension names from ``gold_star.dimensions[]``
    plus any standalone ``gold_star.date_dimension``. Degenerate dimensions are
    OUT OF SCOPE (per-star transaction ids, never shared lookups).
  - Reads the NEW human-authored declaration file
    ``docs/quality/conformed-dimension-map.yaml`` -- a mapping
    ``dimensions: {<name>: {status: conformed|distinct, stars: [...]}}``.
  - FR-006 (undeclared collision): a bare dimension NAME that appears in
    ``gold_star.dimensions[]`` of 2+ stars but is NOT declared in the map
    (neither ``conformed`` nor ``distinct``) is a ``Severity.ERROR`` -- a human
    must rule whether the same-named dims are one shared dimension or coincidental.
  - Bad value: a declaration whose ``status`` is neither ``conformed`` nor
    ``distinct`` is a ``Severity.ERROR`` (mirrors SF1's bad-value posture).
  - FR-005 (conformed divergence): a dimension declared ``conformed`` whose
    surrogate_key or a shared attribute's silver_type DIVERGES across the stars
    it covers is a ``Severity.ERROR``. Graceful degradation: only fields present
    on BOTH sides of a pair are compared; a field absent on either side is
    silently excluded (never a divergence, never a crash) -- the two committed
    instances use materially different (rich vs compact) schema shapes.
  - A dimension declared ``distinct`` never fires (deliberately separate).

What HR1 NEVER does:
  - It NEVER decides whether same-named dims ARE one business dimension
    (Principle V) -- that ``conformed``/``distinct`` ruling is a human modelling
    judgment authored once in the map. A missing declaration is the fail-closed
    ERROR, never a guessed verdict.
  - It NEVER adds a key to ``source-map.yaml`` (the declaration lives only in
    ``conformed-dimension-map.yaml``); NEVER opens a DB or reads a live model
    (Principle VIII); NEVER emits a numeric score or an "N of M" tally
    (hard rule #9); NEVER writes any file (read-only).

Mirrors the SF1/HR2 lazy-``yaml``-import discipline (kept out of the
``retail check`` static-core chain).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "HR1"

_MAPPING_RE = re.compile(r"^mappings/([^/]+)/source-map\.yaml$")
_MAP_FILE = "docs/quality/conformed-dimension-map.yaml"
_VALID_STATUS = ("conformed", "distinct")


def _bare(name: object) -> str | None:
    """Bare dimension name: strip an optional ``<schema>.`` prefix, lowercased."""
    if not isinstance(name, str) or not name.strip():
        return None
    return name.rsplit(".", 1)[-1].strip().lower()


def _load_yaml(ctx: RuleContext, rel: str) -> dict | None:
    import yaml  # lazy: kept out of the retail check static-core chain

    try:
        data = yaml.safe_load((ctx.repo_root / rel).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _star_id(data: dict, table_dir: str) -> str:
    meta = data.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("table_id"), str):
        return meta["table_id"]
    if isinstance(data.get("source_id"), str):
        return data["source_id"]
    return table_dir


def _is_star(data: dict) -> bool:
    gs = data.get("gold_star")
    return isinstance(gs, dict) and gs.get("fact") is not None


def _star_dimensions(data: dict) -> dict[str, dict]:
    """Map bare-name -> the raw dimension dict for one star (dims + date_dimension).

    Degenerate dimensions are excluded (never traversed).
    """
    out: dict[str, dict] = {}
    gs = data.get("gold_star")
    if not isinstance(gs, dict):
        return out
    dims = gs.get("dimensions")
    if isinstance(dims, list):
        for dim in dims:
            if isinstance(dim, dict):
                b = _bare(dim.get("name"))
                if b:
                    out[b] = dim
    date_dim = gs.get("date_dimension")
    if isinstance(date_dim, dict):
        b = _bare(date_dim.get("name"))
        if b:
            out.setdefault(b, date_dim)
    return out


def _attr_silver_types(data: dict, dim_name: str) -> dict[str, str]:
    """Resolve {attr: silver_type} for a dim via columns[] gold_placement joins.

    Rich form only; compact form has no columns[] block -> empty (the type limb
    is a graceful no-op there).
    """
    cols = data.get("columns")
    if not isinstance(cols, list):
        return {}
    prefix = f"dim:{dim_name}."
    out: dict[str, str] = {}
    for col in cols:
        if not isinstance(col, dict):
            continue
        placement = col.get("gold_placement")
        stype = col.get("silver_type")
        if (
            isinstance(placement, str)
            and placement.startswith(prefix)
            and isinstance(stype, str)
        ):
            out[placement[len(prefix) :]] = stype
    return out


def _load_declarations(ctx: RuleContext) -> tuple[dict[str, dict], list[Finding]]:
    """Parse the map -> ({bare_name: {status, entry}}, bad-value findings)."""
    findings: list[Finding] = []
    if _MAP_FILE not in ctx.tracked_files:
        return {}, findings
    data = _load_yaml(ctx, _MAP_FILE)
    if data is None:
        return {}, findings
    raw = data.get("dimensions")
    if not isinstance(raw, dict):
        return {}, findings
    decls: dict[str, dict] = {}
    for name, entry in raw.items():
        b = _bare(name)
        if b is None or not isinstance(entry, dict):
            continue
        status = entry.get("status")
        if status not in _VALID_STATUS:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"conformed-dimension declaration for {name!r} has status "
                        f"{status!r}, which is neither 'conformed' nor 'distinct'"
                    ),
                    locator=f"{_MAP_FILE}:{name}",
                )
            )
            continue
        decls[b] = {"status": status, "entry": entry}
    return decls, findings


def _conformed_divergence(bare: str, stars: dict[str, dict]) -> str | None:
    """Return a human-readable divergence description across >=2 stars, or None.

    Compares surrogate_key and shared-attribute silver_type; only fields present
    on BOTH sides of any pair are compared (graceful degradation).
    """
    # surrogate_key divergence (only among stars that declare one)
    keys = {
        sid: dim.get("surrogate_key")
        for sid, (dim, _data) in stars.items()
        if isinstance(dim.get("surrogate_key"), str)
    }
    if len(set(keys.values())) > 1:
        pairs = ", ".join(f"{sid}={keys[sid]!r}" for sid in sorted(keys))
        return f"surrogate_key differs across stars ({pairs})"
    # shared-attribute silver_type divergence. gold_placement in a source-map is
    # written with the BARE dim name (e.g. "dim:dim_product.item"), so resolve the
    # placement prefix from _bare(dim name), NOT the schema-qualified declared name.
    typemaps: dict[str, dict[str, str]] = {}
    for sid, (dim, data) in stars.items():
        dim_bare = _bare(dim.get("name")) or bare
        typemaps[sid] = _attr_silver_types(data, dim_bare)
    # attributes shared by 2+ stars whose type is known on both
    all_attrs: set[str] = set()
    for tm in typemaps.values():
        all_attrs |= set(tm)
    for attr in sorted(all_attrs):
        present = {sid: tm[attr] for sid, tm in typemaps.items() if attr in tm}
        if len(present) >= 2 and len(set(present.values())) > 1:
            pairs = ", ".join(f"{sid}={present[sid]!r}" for sid in sorted(present))
            return f"attribute {attr!r} silver_type differs across stars ({pairs})"
    return None


@register(RULE_ID, "cross-star conformed-dimension conformance")
def check_hr1(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []

    # 1. discover stars
    stars: dict[str, dict] = {}  # star_id -> source-map dict
    for rel in sorted(ctx.tracked_files):
        if is_test_path(rel):
            continue
        m = _MAPPING_RE.match(rel)
        if not m:
            continue
        data = _load_yaml(ctx, rel)
        if data is None or not _is_star(data):
            continue
        stars[_star_id(data, m.group(1))] = data

    # FR-007: engage only when >1 star exists
    if len(stars) < 2:
        return findings

    # 2. bare-name -> {star_id: (dim_dict, source_map_dict)} across all stars
    name_to_stars: dict[str, dict[str, tuple]] = {}
    for sid, data in stars.items():
        for bare, dim in _star_dimensions(data).items():
            name_to_stars.setdefault(bare, {})[sid] = (dim, data)

    decls, decl_findings = _load_declarations(ctx)
    findings.extend(decl_findings)

    # 3. per bare-name that appears in >=2 stars
    for bare, star_map in sorted(name_to_stars.items()):
        if len(star_map) < 2:
            continue  # not a cross-star name -> nothing to conform
        decl = decls.get(bare)
        if decl is None:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"dimension {bare!r} appears in more than one star but is "
                        "not declared in docs/quality/conformed-dimension-map.yaml; "
                        "a human must rule it 'conformed' (one shared dimension) or "
                        "'distinct' (deliberately separate)"
                    ),
                    locator=f"{_MAP_FILE}:{bare}",
                )
            )
            continue
        if decl["status"] == "distinct":
            continue  # deliberately separate -- never fires
        # conformed: verify grain/key/type agree across the covered stars
        divergence = _conformed_divergence(bare, star_map)
        if divergence is not None:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"dimension {bare!r} is declared 'conformed' but {divergence}; "
                        "a conformed dimension must be identical across every star"
                    ),
                    locator=f"{_MAP_FILE}:{bare}",
                )
            )

    return findings
