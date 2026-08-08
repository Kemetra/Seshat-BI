# Contract: Dagster intent ownership

| Intent | Seshat pre-gate | Executor/owner | Seshat afterward |
|---|---|---|---|
| Decide whether orchestration fits | readiness and complexity assessment | Seshat | one next action |
| Governed medallion run | per-asset readiness/approval gates | Dagster through `seshat dagster` | derived run evidence and blockers |
| Assets/jobs/project authoring | official skill discoverable | Dagster `dagster-expert` | apply Seshat gates if entering governed flow |
| Schedules/sensors/automation | official skill discoverable | Dagster `dagster-expert` | Seshat automations remain stopped until named approval |
| Generic CLI/debugging | official skill discoverable | Dagster `dagster-expert` | no fabricated readiness effect |
| Publish | `publish_ready: pass` | parked official Power BI executor | Dagster never publishes |

Missing discovery, live credentials, gate evidence, or approval fails closed.
