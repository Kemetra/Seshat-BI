"""Unit-suite conftest: registers shared fixtures so test modules take them as
parameters without importing them.

The `noqa: F401` is load-bearing on every entry here: ruff sees an unused
import, but pytest needs the name BOUND in conftest for fixture discovery.
Removing one as dead code silently breaks its consumers.
"""

from tests.unit._dep_coresolve_fixtures import (  # noqa: F401
    stub_pypi,
    stub_resolve,
)
from tests.unit._pbi_mcp_orchestrate_fixtures import (  # noqa: F401
    ready_repo,
)
