# Data model: Integration control-plane convergence

## Component.required_paths

An immutable tuple of repository-relative POSIX paths expected inside an
installed upstream payload.

Rules:

- empty by default;
- each value is non-empty and relative;
- backslashes, absolute paths, and `..` segments are invalid;
- meaningful primarily for GitHub skill bundles in this phase;
- owned only by `catalog.py`.

## Canonical outcome

`SetupOutcome` contains profile, `ComponentPlan` rows, lock result, notes, and a
derived `needs_action` property. It remains the only plan/apply result model.

## Compatibility projection

`IntegrationResult(name, status, detail)` is a loss-limited projection:

| Compatibility field | Canonical source |
| --- | --- |
| `name` | `ComponentPlan.component` |
| `status` | `ComponentPlan.status` |
| `detail` | `ComponentPlan.detail` |

Profile, channel, pin, and source remain available through the canonical API;
the legacy three-field type does not invent substitutes.
