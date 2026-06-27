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
    dax,
    g6,
    git_meta,
    pbir,
    routes,
    sql,
)

__all__ = ["dax", "g6", "git_meta", "pbir", "routes", "sql"]
