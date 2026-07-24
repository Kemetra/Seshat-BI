"""Read-only Power BI MCP doctor family (issue #450, slices 2-4; F016 slot).

Three cooperating, READ-ONLY modules behind the ``seshat pbi-mcp`` narrow
command family (Option-B narrow gate, same precedent as ``seshat dagster
doctor`` / ``seshat dbt doctor``):

* ``detect``    -- environment facts, no network, no MCP call (slice 2).
* ``recommend`` -- the issue-#450 section-7 recommendation matrix as a pure
  decision function + the ``.seshat/powerbi-mcp-recommendation.yaml``
  advisory record (slice 2).
* ``generate``  -- placeholder-only ``.mcp.json`` template + generated setup
  doc, behind a secret-scan refusal (slice 3).
* ``preflight`` -- capability discovery + target-allowlist validation against
  a transport Protocol whose real implementation is deliberately absent
  (slice 4); the shipped transport reports "runtime not present" gracefully.

HARD BOUNDARIES (constitutional; see templates/pbi-mcp-adapter-contract.md):
no mutation path of any kind exists in this package. F016 stays PARKED --
mutations (slice 5) require an owner-ratified ADR and are not implemented
here. Nothing in this package grants an approval, advances a readiness
stage, or emits a numeric score.
"""

from __future__ import annotations
