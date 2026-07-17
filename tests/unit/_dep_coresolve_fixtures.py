"""Shared offline fixtures for the spec-136 dep_coresolve test modules.

Captured pip/PyPI output SHAPES from real invocations plus the two stub
fixtures (`stub_resolve`, `stub_pypi`). Every consumer stays deterministic and
OFFLINE (FR-017): the resolve subprocess and the PyPI JSON index are stubbed,
never contacted.
"""

from __future__ import annotations

import json

import pytest

# --------------------------------------------------------------------------- #
# Captured pip / PyPI output shapes (used by the stubs).
# --------------------------------------------------------------------------- #

# A real `pip install --dry-run --report -` JSON envelope (trimmed): the keys
# the parser reads are `install` (list) and each entry's `metadata.name/version`.
REPORT_PASS_JSON = json.dumps(
    {
        "version": "1",
        "pip_version": "26.0.1",
        "install": [
            {"metadata": {"name": "dbt-core", "version": "1.12.0"}},
            {"metadata": {"name": "sqlparse", "version": "0.5.5"}},
        ],
        "environment": {},
    }
)

# A real pip ResolutionImpossible stderr (captured from the spec-133/spec-134
# dbt-core==1.12.0 + dagster-dbt==0.29.14 conflict).
RESOLUTION_STDERR = (
    "ERROR: Cannot install dagster-dbt==0.29.14 and dbt-core==1.12.0 because "
    "these package versions have conflicting dependencies.\n\n"
    "The conflict is caused by:\n"
    "    The user requested dbt-core==1.12.0\n"
    "    dagster-dbt 0.29.14 depends on dbt-core<1.12 and >=1.7\n\n"
    "ERROR: ResolutionImpossible: for help visit "
    "https://pip.pypa.io/en/latest/topics/dependency-resolution/\n"
)

# A real network/index failure stderr (connection error signature).
INFRA_STDERR = (
    "WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, "
    "status=None)) after connection broken by 'NewConnectionError(...: Failed to "
    "establish a new connection: [Errno -3] Temporary failure in name "
    "resolution')': /simple/dbt-core/\n"
    "ERROR: Could not find a version that satisfies the requirement dbt-core\n"
    "ERROR: Network is unreachable\n"
)


def _pypi_json(name: str, versions_files: dict[str, list[dict]], info: dict) -> str:
    """Build a PyPI JSON API response body.

    ``versions_files`` maps each version string to its per-file list (each file
    is a dict that may carry a ``yanked`` flag). A release is yanked ONLY when
    ALL its files are yanked (plan-review D5, PER-FILE semantics).
    """
    return json.dumps({"info": {"name": name, **info}, "releases": versions_files})


# --------------------------------------------------------------------------- #
# Stub fixtures (the resolve subprocess + the PyPI index).
# --------------------------------------------------------------------------- #


@pytest.fixture
def stub_resolve(monkeypatch):
    """Patch dep_coresolve's resolve-subprocess seam.

    Yields a setter: call ``set(returncode=..., stdout=..., stderr=...)`` to
    program the next stubbed `pip install --dry-run --report` invocation. The
    stub NEVER launches a real subprocess, so no venv is created and nothing is
    installed into the test interpreter (SC-002).
    """
    import scripts.dep_coresolve as dc

    state = {"returncode": 0, "stdout": REPORT_PASS_JSON, "stderr": "", "calls": []}

    def fake_run_resolve(requirements, report_path):
        state["calls"].append(list(requirements))
        return dc.ResolveRun(
            returncode=state["returncode"],
            stdout=state["stdout"],
            stderr=state["stderr"],
            report_json=state["stdout"] if state["returncode"] == 0 else None,
        )

    monkeypatch.setattr(dc, "_run_resolve", fake_run_resolve)

    def _set(**kw):
        state.update(kw)

    _set.state = state  # expose recorded calls to the test
    yield _set


@pytest.fixture
def stub_pypi(monkeypatch):
    """Patch dep_coresolve's PyPI-fetch seam. Call ``set(dist, body)`` to
    program the JSON body returned for a distribution; the stub never hits the
    network (FR-017)."""
    import scripts.dep_coresolve as dc

    bodies: dict[str, str] = {}

    def fake_fetch(dist):
        if dist not in bodies:
            raise dc.InfraError(f"stub has no body for {dist}")
        return json.loads(bodies[dist])

    monkeypatch.setattr(dc, "_fetch_pypi_json", fake_fetch)

    def _set(dist, body):
        bodies[dist] = body

    yield _set
