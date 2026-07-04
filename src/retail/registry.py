from __future__ import annotations

from typing import Callable

from .core import RegisteredRule, Rule, RuleTier

_RULES: list[RegisteredRule] = []


def register(
    rule_id: str, title: str, tier: RuleTier = RuleTier.WORK_REPO
) -> Callable[[Rule], Rule]:
    # tier defaults to WORK_REPO (portable): existing @register(id, title) call
    # sites keep their exact behavior. Pass tier=RuleTier.KIT_SELF on a rule that
    # checks the kit's own internal manifests so it degrades gracefully (Spec A).
    def deco(fn: Rule) -> Rule:
        _RULES.append(RegisteredRule(id=rule_id, rule=fn, title=title, tier=tier))
        return fn

    return deco


def all_rules() -> tuple[RegisteredRule, ...]:
    return tuple(_RULES)
