from __future__ import annotations

from typing import Callable

from .core import RegisteredRule, Rule

_RULES: list[RegisteredRule] = []


def register(rule_id: str, title: str) -> Callable[[Rule], Rule]:
    def deco(fn: Rule) -> Rule:
        _RULES.append(RegisteredRule(id=rule_id, rule=fn, title=title))
        return fn

    return deco


def all_rules() -> tuple[RegisteredRule, ...]:
    return tuple(_RULES)
