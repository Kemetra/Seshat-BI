# Contract: Power BI intent ownership

| Intent | Seshat pre-gate | Executor | Seshat post-validation |
|---|---|---|---|
| Business/report intent | metric contracts and readiness | Seshat knowledge/governance | evidence and next action |
| Report design | approved metrics | Seshat design router | blueprint/binding review |
| Native report authoring | `dashboard_ready: pass`; official skill discoverable | Microsoft `powerbi-report-authoring` | PBIR/blueprint/static validation |
| Bounded visual formatting | semantic/dashboard context; allow-list | Seshat PBIR adapter | binding-preservation/static validation |
| Semantic-model editing | `semantic_model_ready: pass` | Microsoft semantic-model authoring + local Modeling MCP | readiness/evidence validation |
| Published-model query | governed target and safe query posture | Microsoft remote Power BI MCP | evidence interpretation |
| PBIP inspection | repository target | Seshat `pbip-xray` | findings/readiness update |
| Live publish/write | F016 gates and named approval | parked official execution adapter | validation/evidence |

Any missing gate or unavailable official executor fails closed. This contract
does not activate an upstream skill or authorize live execution.
