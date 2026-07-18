"""Owner-declared gold_star fact column semantics for exact parity coverage.

The approved source map's ``gold_star.fact`` section must tag which column is
the grain/business key and which columns are the additive money measures.
Parity evidence derives the expected fact-subject set from these tags exactly
-- the same pattern as dimension-subject coverage, generalized for columns the
built graph cannot enumerate (issue #331). Fail closed: a map without the tags
blocks dbt validate/plan with a stable governance code and a remedy.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .contracts import FactBinding, GovernanceError

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")

_REMEDY = (
    "declare it in the approved source map's gold_star.fact section "
    "(see templates/source-map.yaml) and re-approve the mapping"
)


def _missing(key: str) -> GovernanceError:
    return GovernanceError(
        "DBT_FACT_SEMANTICS_MISSING",
        f"gold_star.fact.{key} is not declared; {_REMEDY}",
    )


def _invalid(message: str) -> GovernanceError:
    return GovernanceError("DBT_FACT_SEMANTICS_INVALID", message)


def _load_document(source_map: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(source_map.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise _invalid(
            f"approved source map is unreadable: {exc.__class__.__name__}"
        ) from exc
    if not isinstance(document, dict):
        raise _invalid("approved source map must be a YAML mapping")
    return document


def _fact_section(document: dict[str, Any]) -> dict[str, Any]:
    star = document.get("gold_star")
    fact = star.get("fact") if isinstance(star, dict) else None
    if not isinstance(fact, dict):
        raise _missing("business_key (gold_star.fact is absent)")
    return fact


def _is_identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(_IDENTIFIER.fullmatch(value))


def _business_key(fact: dict[str, Any]) -> str:
    value = fact.get("business_key")
    if value is None:
        raise _missing("business_key")
    if not _is_identifier(value):
        raise _invalid(
            "gold_star.fact.business_key must be a lowercase column identifier"
        )
    return value


def _require_money_entries(value: list[Any]) -> None:
    if not all(_is_identifier(item) for item in value):
        raise _invalid(
            "gold_star.fact.additive_money_measures must be lowercase "
            "column identifiers"
        )
    if len(value) != len(set(value)):
        raise _invalid(
            "gold_star.fact.additive_money_measures contains duplicate columns"
        )


def _require_money_list(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise _invalid(
            "gold_star.fact.additive_money_measures must be a non-empty list"
        )
    _require_money_entries(value)


def _money_measures(fact: dict[str, Any]) -> tuple[str, ...]:
    value = fact.get("additive_money_measures")
    if value is None:
        raise _missing("additive_money_measures")
    _require_money_list(value)
    return tuple(sorted(value))


def _require_money_are_measures(fact: dict[str, Any], money: tuple[str, ...]) -> None:
    measures = fact.get("measures")
    if not isinstance(measures, list):
        return
    extras = sorted(set(money) - {m for m in measures if isinstance(m, str)})
    if extras:
        raise _invalid(
            "gold_star.fact.additive_money_measures must be declared "
            "gold_star.fact.measures: " + ", ".join(extras)
        )


def _require_key_is_not_money(business_key: str, money: tuple[str, ...]) -> None:
    if business_key in money:
        raise _invalid(
            "gold_star.fact.business_key cannot also be an additive money "
            f"measure: {business_key}"
        )


def load_fact_semantics(source_map: Path) -> FactBinding:
    """Read the approved map's exact fact-column tags, failing closed."""

    fact = _fact_section(_load_document(source_map))
    business_key = _business_key(fact)
    money = _money_measures(fact)
    _require_money_are_measures(fact, money)
    _require_key_is_not_money(business_key, money)
    return FactBinding(business_key=business_key, additive_money_measures=money)
