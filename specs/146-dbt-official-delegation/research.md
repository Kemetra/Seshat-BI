# Research: dbt official delegation

## Repository truth

- `seshat dbt` already invokes the pinned dbt executable rather than reproducing
  compile/build/test semantics.
- Seshat uniquely owns Mapping Ready, immutable plan acceptance, shadow schemas,
  source-map citations, locks, redaction, parity, and normalized evidence.
- `dbt-workflows` currently claims generic troubleshooting without delegating it.
- The catalog already obtains `dbt-labs/dbt-agent-skills` and `dbt-mcp`, but
  activation/discovery is not proven.
- Live compile/parity and compatibility attestation remain blocked.

## Upstream truth

dbt Labs' official agent bundle provides skills for analytics engineering,
running dbt commands, tests, docs lookup, MCP configuration, and troubleshooting.
The official dbt MCP exposes dbt CLI, discovery, docs, semantic-layer, and other
tool families. Those are upstream execution/competence surfaces, not Seshat
domain logic.

## Conclusion

No runtime rewrite or deletion is justified. The remaining delta is explicit
delegation and machine-readable capability ownership.
