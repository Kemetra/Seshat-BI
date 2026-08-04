from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from .core import RegisteredRule, Rule, RuleTier

if TYPE_CHECKING:  # annotation-only, mirroring core.py
    from .rule_coverage import Requirement

_RULES: list[RegisteredRule] = []


def register(
    rule_id: str,
    title: str,
    tier: RuleTier = RuleTier.WORK_REPO,
    *,
    requires: tuple["Requirement", ...] = (),
) -> Callable[[Rule], Rule]:
    # tier defaults to WORK_REPO (portable): existing @register(id, title) call
    # sites keep their exact behavior. Pass tier=RuleTier.KIT_SELF on a rule that
    # checks the kit's own internal manifests so it degrades gracefully (Spec A).
    #
    # `requires` is KEYWORD-ONLY and defaults to (): all 50 existing call sites
    # compile untouched and land in CoverageState.UNDECLARED, which is honest --
    # "we cannot yet establish whether this rule ran" -- rather than a silent pass.
    # Declaring it migrates a rule into the coverage census (rule_coverage.py).
    def deco(fn: Rule) -> Rule:
        _RULES.append(
            RegisteredRule(
                id=rule_id, rule=fn, title=title, tier=tier, requires=requires
            )
        )
        return fn

    return deco


def all_rules() -> tuple[RegisteredRule, ...]:
    return tuple(_RULES)
