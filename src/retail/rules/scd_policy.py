"""HR2 -- declared SCD type per gold dimension (spec 088, dimension history policy).

What HR2 does (STATIC, fail-closed):
  Reads each committed ``mappings/<table>/source-map.yaml`` and inspects every
  entry of its ``gold_star.dimensions[]`` list for a human-declared ``scd_type``:

  - MISSING or a placeholder value (``""``, ``null``, or a case-insensitive
    ``"tbd"``) is a Needs-decision -- HR2 emits ``Severity.ERROR`` naming the
    dimension and instructing a human to declare ``type_1`` or ``type_2``. It
    NEVER defaults an undeclared dimension to ``type_1`` -- that would silently
    reproduce the exact implicit-Type-1-by-omission gap this feature exists to
    end, one layer higher.
  - A present, non-empty, non-placeholder value that is neither ``type_1`` nor
    ``type_2`` (e.g. a typo ``"type1"`` or an out-of-scope taxonomy value like
    ``"type_3"``) is invalid -- HR2 emits ``Severity.ERROR`` naming the
    dimension and the literal invalid value.
  - A dimension declared ``type_2`` (historized) is checked against its own
    table's gold migration, ``warehouse/migrations/*create_gold_<table>_star.sql``
    (``<table>`` = the mapping-directory name). If that migration exists and
    contains, scoped to that dimension's OWN gold table, a
    ``DROP TABLE IF EXISTS <dim_table>`` paired (anywhere in the same file, not
    necessarily adjacent) with a same-file ``CREATE TABLE <dim_table>`` that
    recreates it -- in either authored form (a bare CTAS, or explicit column
    DDL followed by one or more ``INSERT INTO <dim_table> ...`` statements) --
    HR2 emits ``Severity.ERROR``: that construct discards every prior attribute
    value on each re-run, which cannot honor a Type-2 (preserve-history)
    declaration. ``<dim_table>`` is resolved by stripping an optional leading
    ``<schema>.`` prefix from both the declared ``name`` and the matched
    ``DROP``/``CREATE`` token before comparing bare identifiers, so a sibling
    ``type_1`` dimension's ordinary drop-and-rebuild elsewhere in the same file
    never fires against this dimension.
  - A dimension declared ``type_1`` (overwrite) NEVER produces a finding,
    regardless of its migration's build shape -- drop-and-rebuild is the
    correct, honored mechanism for an overwrite policy.
  - If the table's gold migration glob matches ZERO files, HR2 fires nothing
    for that dimension's build-check limb -- absence of a migration is a
    not-yet-buildable state, never a fabricated pass or fail about SQL that
    does not exist. If the glob matches MORE THAN ONE file, HR2 emits a single
    ``Severity.ERROR`` naming the table and every matched filename, rather than
    inspecting any one of them or guessing which is current.
  - ``gold_star.degenerate_dimensions[]`` and ``gold_star.date_dimension`` are
    OUT OF SCOPE: HR2 never reads or requires an ``scd_type`` on either -- a
    degenerate dim has no separate table to historize, and a generated calendar
    has no changing attribute in the SCD sense.

What HR2 NEVER does:
  - It NEVER decides, infers, recommends, or defaults a dimension's
    ``scd_type`` on a human's behalf (Principle V) -- exactly like grain, PII,
    or business-rollup judgments, this is an owner/analyst ruling made once,
    in the reviewed ``source-map.yaml``, at Mapping Ready. A missing
    declaration is always the fail-closed ERROR; it is never guessed.
  - It NEVER validates the CORRECTNESS of a hand-authored, non-drop-and-rebuild
    Type-2 pattern (an upsert / dated-row / merge migration) -- only the
    ABSENCE of any recognizable non-destructive construct is out of HR2's
    detection; whether such a pattern actually, correctly preserves history at
    the row level is a live-data question deferred to a future
    ``retail validate`` extension (Principle VIII).
  - It NEVER opens a database connection, executes, or simulates a migration
    (Principle VIII -- static only, committed text only).
  - It NEVER emits a numeric confidence/health/completeness score or an
    "N of M" tally (hard rule #9) -- output is categorical findings only, each
    naming the dimension, the table, and what is wrong.
  - It NEVER writes to ``source-map.yaml`` or any migration file -- read-only.

Landing / grandfather rule (owner ruling 2026-07-05): a source-map authored
before this feature -- one that declares ``scd_type`` on NONE of its
``gold_star.dimensions[]`` and does not opt in via ``gold_star.scd_enforced:
true`` -- is GRANDFATHERED: HR2 fires no missing-declaration ERROR against it.
The moment a map opts in (either by declaring ``scd_type`` on at least one
dimension, or by setting ``gold_star.scd_enforced: true``), the whole map is
"actively adopting SCD policy" and EVERY dimension must then carry a valid
declaration -- a partially-declared map is the fail-closed ERROR (finish the
job), so the grandfather is a one-way door that never silently re-opens. The
"invalid value" and "type_2 vs drop-and-rebuild" checks are NOT grandfathered:
a present-but-wrong declaration is always an error regardless of adoption
state. This keeps HR2 ``<no-finding>`` on the already-approved committed tree
while enforcing the policy on every new or newly-touched map going forward.

Mirrors the SF1/HR1 lazy-``yaml``-import discipline (kept out of the
``retail check`` static-core chain) and the HR7 gold-migration noise-stripped
raw-text scan discipline.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register
from ..sql import strip_sql_comments

RULE_ID = "HR2"

_VALID_VALUES = ("type_1", "type_2")
_PLACEHOLDER_VALUES = ("", "tbd")

_MAPPING_RE = re.compile(r"^mappings/([^/]+)/source-map\.yaml$")

_DROP_TABLE_RE = re.compile(
    r"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?P<name>[A-Za-z_][\w.]*)", re.IGNORECASE
)
_CREATE_TABLE_RE = re.compile(
    r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<name>[A-Za-z_][\w.]*)",
    re.IGNORECASE,
)
_INSERT_INTO_RE = re.compile(
    r"\bINSERT\s+INTO\s+(?P<name>[A-Za-z_][\w.]*)", re.IGNORECASE
)


def _resolve_bare_table(name: str) -> str:
    """Strip an optional leading ``<schema>.`` prefix; compare bare identifiers.

    ``retail_store_sales`` schema-qualifies (``gold.dim_customer_rss``) while
    the canonical template and ``demo_sample_orders`` leave ``name`` bare
    (``dim_product``); the authored migration SQL always schema-qualifies the
    physical ``DROP``/``CREATE`` token with ``gold.`` regardless (spec 088,
    Clarification C4).
    """
    return name.rsplit(".", 1)[-1].strip().lower()


def _find_gold_migrations(ctx: RuleContext, table_id: str) -> list[str]:
    """Tracked ``warehouse/migrations/*create_gold_<table_id>_star.sql`` paths."""
    suffix = f"create_gold_{table_id}_star.sql"
    return sorted(
        p
        for p in ctx.tracked_files
        if p.startswith("warehouse/migrations/") and p.endswith(suffix)
    )


def _has_drop_and_rebuild(sql_text: str, bare_table: str) -> bool:
    """True if ``sql_text`` DROPs and (CTAS or DDL+INSERT) recreates ``bare_table``.

    Scoped to one dimension's own table: a DROP and a CREATE naming the SAME
    bare identifier (schema-prefix stripped from the matched token), anywhere
    in the file -- NOT required to be textually adjacent (spec 088,
    Clarification C5, the documented ``retail-build-warehouse`` batched-drop
    gold shape). [FUTURE SCOPE -- see spec.md Clarification C3] no positive
    signal for a valid, correctly-authored Type-2 construct exists yet; only
    this negative drop-and-rebuild signal is implemented.
    """
    clean = strip_sql_comments(sql_text)
    dropped = {
        _resolve_bare_table(m.group("name")) for m in _DROP_TABLE_RE.finditer(clean)
    }
    if bare_table not in dropped:
        return False
    created = {
        _resolve_bare_table(m.group("name")) for m in _CREATE_TABLE_RE.finditer(clean)
    }
    if bare_table not in created:
        return False
    # Either authored form is in scope: a bare CREATE TABLE (CTAS or DDL) for
    # this table, recreated -- an explicit-DDL form additionally needs an
    # INSERT to actually populate it, but a CTAS already carries its own
    # SELECT, so requiring the CREATE alone (already checked above) is
    # sufficient to detect "recreates it" for either form; INSERT presence is
    # not required to flag drop-and-rebuild since CTAS never has one.
    return True


def _load_source_map(ctx: RuleContext, rel: str) -> dict | None:
    """Parse one tracked ``source-map.yaml``; ``None`` on missing/unparseable."""
    import yaml  # lazy: kept out of the retail check static-core chain

    try:
        raw = (ctx.repo_root / rel).read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _iter_declared_dimensions(data: dict) -> Iterable[tuple[str, object]]:
    """Yield ``(name, scd_type_value)`` for each ``gold_star.dimensions[]`` entry.

    ``scd_type_value`` is the raw value as authored (may be missing -> use
    ``dim.get("scd_type")`` semantics: ``None`` covers both "no key" and an
    explicit YAML null). Never reads ``degenerate_dimensions[]`` or
    ``date_dimension`` (out of HR2's scope).
    """
    gold_star = data.get("gold_star")
    if not isinstance(gold_star, dict):
        return
    dims = gold_star.get("dimensions")
    if not isinstance(dims, list):
        return
    for dim in dims:
        if not isinstance(dim, dict):
            continue
        name = dim.get("name")
        if not isinstance(name, str) or not name:
            continue
        yield name, dim.get("scd_type")


def _classify(value: object) -> str:
    """Classify a raw ``scd_type`` value into "missing" | "invalid" | a valid value."""
    if value is None:
        return "missing"
    if not isinstance(value, str):
        return "missing"  # a non-string (e.g. a stray YAML bool/number) is undeclared
    stripped = value.strip()
    if stripped.lower() in _PLACEHOLDER_VALUES:
        return "missing"
    if stripped in _VALID_VALUES:
        return stripped
    return "invalid"


def _check_table(ctx: RuleContext, rel: str) -> list[Finding]:
    findings: list[Finding] = []
    match = _MAPPING_RE.match(rel)
    if not match:
        return findings
    table_id = match.group(1)

    data = _load_source_map(ctx, rel)
    if data is None:
        return findings  # unreadable/unparseable map is another rule's concern

    # Grandfather rule (owner ruling 2026-07-05): a pre-existing map that
    # declares scd_type on NO dimension and does not opt in via
    # gold_star.scd_enforced:true is exempt from the MISSING-declaration ERROR.
    # The moment it opts in (any valid/invalid scd_type present, or the explicit
    # flag) the whole map is "adopting" and every dimension must declare one.
    dims_kinds = [(n, v, _classify(v)) for n, v in _iter_declared_dimensions(data)]
    gold_star = data.get("gold_star")
    scd_enforced = isinstance(gold_star, dict) and gold_star.get("scd_enforced") is True
    adopting = scd_enforced or any(k != "missing" for _, _, k in dims_kinds)

    type2_dims: list[str] = []
    for dim_name, raw_value, kind in dims_kinds:
        if kind == "missing":
            if not adopting:
                continue  # grandfathered: pre-existing, un-adopted map
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"dimension {dim_name!r} in {rel} has no declared "
                        "scd_type; a human must declare 'type_1' (overwrite) "
                        "or 'type_2' (historized) -- HR2 never infers or "
                        "defaults this value"
                    ),
                    locator=f"{rel}:{dim_name}",
                )
            )
        elif kind == "invalid":
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"dimension {dim_name!r} in {rel} has scd_type "
                        f"{raw_value!r}, which is neither 'type_1' nor "
                        "'type_2'"
                    ),
                    locator=f"{rel}:{dim_name}",
                )
            )
        elif kind == "type_2":
            type2_dims.append(dim_name)
        # kind == "type_1": no finding (FR-009)

    if not type2_dims:
        return findings

    migrations = _find_gold_migrations(ctx, table_id)
    if len(migrations) > 1:
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    f"ambiguous gold migration set for table {table_id!r}: "
                    "multiple files match "
                    f"warehouse/migrations/*create_gold_{table_id}_star.sql "
                    f"({', '.join(migrations)}); HR2 cannot tell which is "
                    "current, so it inspects none of them"
                ),
                locator=rel,
            )
        )
        return findings
    if not migrations:
        return findings  # not-yet-buildable (FR-008): no finding fabricated

    migration_rel = migrations[0]
    try:
        sql_text = (ctx.repo_root / migration_rel).read_text(encoding="utf-8")
    except OSError:
        return findings

    for dim_name in type2_dims:
        bare_table = _resolve_bare_table(dim_name)
        if _has_drop_and_rebuild(sql_text, bare_table):
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"dimension {dim_name!r} is declared scd_type "
                        "'type_2' (historized) in "
                        f"{rel}, but {migration_rel} builds its gold table "
                        "by drop-and-rebuild; that construct discards every "
                        "prior attribute value on each re-run and cannot "
                        "honor a type_2 declaration"
                    ),
                    locator=migration_rel,
                )
            )

    return findings


@register(RULE_ID, "declared SCD type per gold dimension")
def check_hr2(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in sorted(ctx.tracked_files):
        if is_test_path(rel):
            continue
        if not _MAPPING_RE.match(rel):
            continue
        findings.extend(_check_table(ctx, rel))
    return findings
