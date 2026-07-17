"""Unit-suite conftest: registers the shared spec-136 dep_coresolve stub
fixtures so test modules take them as parameters without imports."""

from tests.unit._dep_coresolve_fixtures import (  # noqa: F401
    stub_pypi,
    stub_resolve,
)
