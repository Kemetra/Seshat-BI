"""Agent Compatibility Certification (spec 129): `seshat agent verify`.

An empty public surface by design (B1/B3 posture): every submodule is
imported lazily by its caller (the CLI handler, tests), so importing this
package never pulls in a DB driver, a network client, or the dev-only
`scripts/` release-verification helpers. See `agent_verify.checks` for the
per-check functions, `agent_verify.targets` for the target registry, and
`agent_verify.record` for evidence-record assembly and the publication gate.
"""

from __future__ import annotations
