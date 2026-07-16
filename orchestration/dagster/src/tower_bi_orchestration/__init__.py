"""tower_bi_orchestration -- the Seshat BI Dagster orchestration adapter (F030).

Runs the already-approved medallion sequence unattended / in CI as an asset
graph. Authority boundary (spec 024, unchanged): the gate exit code and the
named human decide every readiness stage; this package sequences all seven
stages and DECIDES none. It reads committed approvals as its only GO signal,
fails closed at every gate, writes derived run-evidence, and never writes a
readiness ``status``, a ``Gate status``, or an ``approvals[]`` entry.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
