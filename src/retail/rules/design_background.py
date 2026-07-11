"""Design-lint rule DL2: background-spec forbidden-dynamic-content purity (surface 2).

Surface-2 sibling of DL1 (theme JSON purity, surface 3). A Power BI page
background carries STATIC STRUCTURE ONLY -- layout containers, safe zones, grid,
chrome. It is never data: a KPI value, a dynamic title, a measure result, a data
label, a refresh stamp, a filter/slicer state, or a screenshot of a live visual
must never be baked into the static background image. This rule turns the DECLARED
boolean contract of a committed filled background spec into a CI-enforced
governance check.

It asserts the spec's OWN declared booleans against the contract declared in
``templates/background-spec.yaml``:

- every ``forbidden_dynamic_content`` key MUST be the real boolean ``false``;
  a real ``true`` is a defect (ERROR); a still-present ``<true|false>``
  placeholder or any non-boolean value is malformed (ERROR).
- every ``qa_checklist`` item MUST be the real boolean ``true``, OR ``false``
  accompanied by a recorded reason (a present, non-empty, non-placeholder reason
  string); a bare ``false`` with no reason is a finding; a placeholder or a
  non-boolean value is a finding.

The rule detects reason PRESENCE only -- it NEVER judges a reason's adequacy
(Principle V). It never inspects an image binary, never renders, never interprets
free-text meaning, never computes a score, and never self-grants readiness
(FR-005, FR-012, FR-015).

Vocabulary (7 forbidden keys + 9 qa items) is frozen VERBATIM from the two
declared blocks in ``templates/background-spec.yaml`` (Clarifications Q2) -- no
tenant/example/brand literal (Principle VII). Discovery is the generic suffix
``*.background.yaml`` (Clarifications, RESOLVED 2026-07-02; analogue of DL1's
frozen ``.theme.json``), exempting ``templates/`` (the blank copy-me template) and
the test-fixture path (via ``is_test_path``). ``yaml`` is imported LAZILY inside
the check function so the module scope stays stdlib-only (B1/B3, FR-012).
"""

from __future__ import annotations

from typing import Any, Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "DL2"

# Committed filled background specs are discovered generically by this suffix
# (never an enumerated or tenant-specific list -- Principle VII, FR-002). This is
# the frozen discovery convention resolved in the spec Clarifications (analogue of
# DL1's ``.theme.json`` suffix); the golden records encode exactly this suffix.
_BACKGROUND_SUFFIX = ".background.yaml"

# The blank copy-me template is EXEMPT from discovery entirely: its values are
# ``<true|false>`` placeholders, not real booleans (FR-002).
_TEMPLATE_PATH = "templates/background-spec.yaml"

# The template placeholder string a filled value must NOT still carry (FR: Q1/Q3).
_PLACEHOLDER = "<true|false>"

# FROZEN forbidden_dynamic_content keys -- verbatim from the two declared blocks in
# templates/background-spec.yaml (Clarifications Q2). Every one MUST be real
# ``false`` to pass; a real ``true`` is a defect. Generic only: no tenant literal.
_FORBIDDEN_KEYS: tuple[str, ...] = (
    "contains_kpi_value",
    "contains_dynamic_title",
    "contains_measure_or_metric",
    "contains_data_label_or_axis_value",
    "contains_date_or_refresh_stamp",
    "contains_filter_or_slicer_state",
    "baked_in_screenshot_of_a_visual",
)

# FROZEN qa_checklist items -- verbatim from templates/background-spec.yaml
# (Clarifications Q2). Every one MUST be real ``true``, OR ``false`` with a
# recorded reason. Generic only: no tenant literal.
_QA_ITEMS: tuple[str, ...] = (
    "is_static_structure_only",
    "no_forbidden_dynamic_content",
    "exported_at_canvas_size_1to1",
    "safe_zones_align_to_grid",
    "whitespace_preserved",
    "not_dark_behind_dense_charts",
    "contrast_sufficient_for_visuals",
    "consistent_aspect_ratio",
    "branding_is_chrome_not_data",
)

# Keys under which a per-item recorded reason may live in the qa block. A qa item
# recorded ``false`` passes only when a reason is present under one of these keys
# for that item (reason PRESENCE only, never adequacy -- Principle V).
_REASON_KEYS: tuple[str, ...] = ("reasons", "warnings")


def _iter_background_specs(ctx: RuleContext) -> list[str]:
    """Committed filled background specs, generic discovery.

    The blank template and any test-fixture path are exempt (FR-002, FR-010).
    """
    return [
        p
        for p in ctx.tracked_files
        if p.endswith(_BACKGROUND_SUFFIX)
        and p != _TEMPLATE_PATH
        and not is_test_path(p)
    ]


def _is_real_bool(value: Any, expected: bool) -> bool:
    """True only when ``value`` is the real Python boolean ``expected``.

    ``yaml.safe_load`` parses unquoted ``true``/``false`` to Python ``bool``. A
    string (placeholder or a quoted word) or a number is NOT a real boolean, so it
    never satisfies this check -- it is surfaced as malformed instead.
    """
    return isinstance(value, bool) and value is expected


def _is_placeholder(value: Any) -> bool:
    """True when ``value`` is the still-unfilled ``<true|false>`` placeholder.

    A filled spec must carry a real boolean; a value that is still the template
    placeholder string is malformed (FR: Q1/Q3). Shared by both the forbidden and
    qa checks so the placeholder test lives in exactly one place.
    """
    return isinstance(value, str) and value.strip() == _PLACEHOLDER


def _is_valid_reason(text: Any) -> bool:
    """True when ``text`` is a present, non-empty, non-placeholder reason string.

    Reason PRESENCE only -- never adequacy (Principle V, Clarifications Q3).
    """
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    return bool(stripped) and stripped != _PLACEHOLDER


def _inline_reason_present(value: Any) -> bool:
    """Inline shape: the item value is a mapping carrying a reason/warning field."""
    if not isinstance(value, dict):
        return False
    return any(_is_valid_reason(value.get(key)) for key in ("reason", "warning"))


def _sibling_reason_present(qa_block: dict, item: str) -> bool:
    """Sibling shape: a reasons/warnings mapping keyed by the item name."""
    for reason_key in _REASON_KEYS:
        sibling = qa_block.get(reason_key)
        if isinstance(sibling, dict) and _is_valid_reason(sibling.get(item)):
            return True
    return False


def _reason_present(qa_block: dict, item: str, value: Any) -> bool:
    """True if a present, non-empty, non-placeholder reason accompanies ``item``.

    Reason PRESENCE only -- the rule never judges the reason's adequacy
    (Principle V, Clarifications Q3). A reason may be attached inline (the item's
    value is a mapping carrying ``reason``) or under a sibling reasons/warnings
    mapping keyed by the item name.
    """
    return _inline_reason_present(value) or _sibling_reason_present(qa_block, item)


def _check_forbidden(block: Any, rel: str) -> Iterable[Finding]:
    """Assert every declared forbidden key is real ``false`` (FR-001, FR-003)."""
    if not isinstance(block, dict):
        yield Finding(
            rule_id=RULE_ID,
            severity=Severity.ERROR,
            message=(
                "background spec is missing or malformed its "
                "'forbidden_dynamic_content' block (must declare every forbidden "
                "key as a real boolean; see templates/background-spec.yaml)"
            ),
            locator=f"{rel}#/forbidden_dynamic_content",
        )
        return
    for key in _FORBIDDEN_KEYS:
        if key not in block:
            continue  # a missing key cannot be asserted (parse-contract detail)
        value = block[key]
        pointer = f"{rel}#/forbidden_dynamic_content/{key}"
        if _is_real_bool(value, False):
            continue  # compliant: the forbidden content is declared absent
        if _is_real_bool(value, True):
            yield Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    f"forbidden dynamic content declared present: {key!r} is "
                    f"true -- background is static structure only; move that "
                    f"content UP to a live visual (surface 1, see "
                    f"templates/background-spec.yaml)"
                ),
                locator=pointer,
            )
        elif _is_placeholder(value):
            yield Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    f"forbidden key {key!r} is not filled: still the "
                    f"'{_PLACEHOLDER}' placeholder -- a discovered filled spec must "
                    f"declare a real boolean"
                ),
                locator=pointer,
            )
        else:
            yield Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    f"forbidden key {key!r} has a non-boolean value {value!r} -- "
                    f"it must be a real true/false against the declared contract"
                ),
                locator=pointer,
            )


def _qa_false_finding(
    block: dict, item: str, value: Any, pointer: str
) -> Finding | None:
    """Finding for a real-``false`` qa item, or ``None`` when a reason is recorded.

    A false value is accepted only when a reason is recorded in the sibling
    reasons/warnings mapping (the shape the template documents); reason PRESENCE
    only, never adequacy (Principle V).
    """
    if _reason_present(block, item, value):
        return None  # a reasoned warning is accepted (reason PRESENCE only)
    return Finding(
        rule_id=RULE_ID,
        severity=Severity.ERROR,
        message=(
            f"qa item {item!r} is false with no recorded reason -- a false "
            f"item must carry a blocking reason or a recorded warning + "
            f"reason (see templates/background-spec.yaml)"
        ),
        locator=pointer,
    )


def _qa_item_finding(
    block: dict, item: str, value: Any, pointer: str
) -> Finding | None:
    """Classify one qa item's value into its single finding (or ``None`` if OK).

    A qa item is a real boolean; a false value is accepted only when a reason is
    recorded in the sibling reasons/warnings mapping (the shape the template
    documents). Any other shape (dict, placeholder, other scalar) falls through to
    a non-boolean finding -- mirroring _check_forbidden, which also treats a
    non-boolean value as a defect.
    """
    if _is_real_bool(value, True):
        return None  # compliant
    if _is_real_bool(value, False):
        return _qa_false_finding(block, item, value, pointer)
    if _is_placeholder(value):
        return Finding(
            rule_id=RULE_ID,
            severity=Severity.ERROR,
            message=(
                f"qa item {item!r} is not filled: still the '{_PLACEHOLDER}' "
                f"placeholder -- a discovered filled spec must declare a real "
                f"boolean"
            ),
            locator=pointer,
        )
    return Finding(
        rule_id=RULE_ID,
        severity=Severity.ERROR,
        message=(
            f"qa item {item!r} has a non-boolean value {value!r} -- it must "
            f"be a real true/false against the declared contract"
        ),
        locator=pointer,
    )


def _check_qa(block: Any, rel: str) -> Iterable[Finding]:
    """Assert every declared qa item is real ``true`` or ``false``+reason (FR-001)."""
    if not isinstance(block, dict):
        yield Finding(
            rule_id=RULE_ID,
            severity=Severity.ERROR,
            message=(
                "background spec is missing or malformed its 'qa_checklist' block "
                "(must declare every item as a real boolean, or false with a "
                "recorded reason; see templates/background-spec.yaml)"
            ),
            locator=f"{rel}#/qa_checklist",
        )
        return
    for item in _QA_ITEMS:
        if item not in block:
            continue  # a missing item cannot be asserted (parse-contract detail)
        pointer = f"{rel}#/qa_checklist/{item}"
        finding = _qa_item_finding(block, item, block[item], pointer)
        if finding is not None:
            yield finding


@register(RULE_ID, "Background spec declares no baked-in dynamic content")
def check_background_purity(ctx: RuleContext) -> Iterable[Finding]:
    # Lazy in-function import keeps the static check core stdlib-only (B1/B3,
    # FR-012): yaml is a non-stdlib dependency and must never be a module-scope
    # import in a governed rule.
    import yaml

    findings: list[Finding] = []
    for rel in _iter_background_specs(ctx):
        path = ctx.repo_root / rel
        try:
            with path.open(encoding="utf-8-sig") as fh:
                doc: Any = yaml.safe_load(fh)
        except (OSError, yaml.YAMLError) as exc:
            # FR-009: a committed filled spec that cannot be parsed is surfaced as
            # a finding -- never a crash, never a silent pass.
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"background spec could not be parsed as YAML "
                        f"({exc.__class__.__name__}); it cannot be verified and "
                        f"must be valid YAML"
                    ),
                    locator=f"{rel}#/",
                )
            )
            continue
        if not isinstance(doc, dict):
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        "background spec did not parse to a mapping; it cannot "
                        "declare the forbidden_dynamic_content / qa_checklist "
                        "contract"
                    ),
                    locator=f"{rel}#/",
                )
            )
            continue
        findings.extend(_check_forbidden(doc.get("forbidden_dynamic_content"), rel))
        findings.extend(_check_qa(doc.get("qa_checklist"), rel))
    return findings
