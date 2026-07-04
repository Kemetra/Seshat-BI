"""Rule package.

Importing this package imports every rule submodule so that each module's
``@register(...)`` decorators fire exactly once. The runner does
``import retail.rules`` at startup before calling ``registry.all_rules()``.

Add a new submodule to the import list below when you add a new rule group;
that is the *only* wiring step required for new rules to be discovered.
"""

from __future__ import annotations

# Side-effecting imports: each module registers its rules on import.
from . import (  # noqa: F401  (imported for side effects)
    additivity_consistency,
    answerability_reconciler,
    assumption_coherence,
    assumptions,
    dax,
    design_background,
    design_contrast,
    design_grid_closure,
    design_review_evidence,
    design_routes,
    design_theme,
    design_theme_fidelity,
    design_visual_selfcheck,
    g6,
    git_meta,
    live_surface_boundary,
    never_execute,
    parked_on,
    pbir,
    publish_pack,
    readiness_status,
    routes,
    routes_coverage,
    rule_ap1,
    rule_count_claims,
    rule_sf1,
    scorecard,
    sql,
    status_claims,
)

__all__ = [
    "additivity_consistency",
    "answerability_reconciler",
    "assumption_coherence",
    "assumptions",
    "dax",
    "design_background",
    "design_contrast",
    "design_grid_closure",
    "design_review_evidence",
    "design_routes",
    "design_theme",
    "design_theme_fidelity",
    "design_visual_selfcheck",
    "g6",
    "git_meta",
    "live_surface_boundary",
    "never_execute",
    "parked_on",
    "pbir",
    "publish_pack",
    "readiness_status",
    "routes",
    "routes_coverage",
    "rule_ap1",
    "rule_count_claims",
    "rule_sf1",
    "scorecard",
    "sql",
    "status_claims",
]
