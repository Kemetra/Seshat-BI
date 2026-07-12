# Portfolio survey fixtures

All fixtures in this directory are synthetic. They exercise the contract-driven
discovery flow without carrying facts from a worked example or a real source.

Seeded scenario classes:

- `db-schema/`: metadata for at least five reachable database tables.
- `file-folder/`: metadata for a folder containing CSV and Excel sources.
- `partial/`: reachable objects whose metadata is partly unavailable.
- `pii-hints/`: column-name and declared-type hints that may indicate PII; no
  source values are stored.

Golden surveys are review targets for the agent-authored artifact. They are not
outputs of a second profiler.
