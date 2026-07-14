# Support matrix: Seshat BI v0.2.0

This table is the single place to check what is actually available, on what
runtime, and how far its validation goes. It distinguishes **installation and
discovery** (the plugin/package resolves and its components are visible) from
**behavior validation** (the installed surface was exercised against the governed
synthetic fixture and produced the required refusals). Discovery is not behavioral
proof.

The Python CLI (`seshat` / `retail`) and the two repository plugins are separate
distributions: PyPI provides the CLI; the plugins provide skills and governance
instructions for an agent session. Installing one does not install the other.

| Surface | Install path | Runtime requirement | Validated environment | Availability | Behavior validation | Update/uninstall validation | Limitations |
|---|---|---|---|---|---|---|---|
| Python CLI (`seshat-bi`) | `pipx install seshat-bi` (PyPI) | Python >= 3.13 | Windows + Python 3.13 | available | n/a (not an agent surface) | validated (`pipx upgrade` / `pipx uninstall`) | macOS/Linux documented as best-effort beta; not the release gate |
| Claude Code repository plugin | `/plugin marketplace add ahmed-shaaban-94/Seshat_BI` then `/plugin install seshat-bi@seshat-bi-marketplace` | Claude Code CLI | Claude Code `2.1.209`, Windows 11 | validated | validated (governed CSV check + pressure/refusal test both passed) | validated (`/plugin update`, `/plugin uninstall`, workspace preserved) | strict fresh-profile install not performed; tested with a temporary local-scope workspace with user settings excluded from the active session |
| Codex CLI repository plugin | `codex plugin marketplace add https://github.com/ahmed-shaaban-94/Seshat_BI` then `codex plugin add seshat-bi@seshat-bi-repository` | Codex CLI | current Codex CLI | partially validated | unverified (governed CSV and pressure/refusal checks not run) | unverified | install, listing, and router discovery (`@Seshat-BI`) passed; nothing beyond that |
| Codex IDE | Settings > Plugins | Codex IDE | -- | unverified | unverified | unverified | no IDE acceptance pass recorded |
| Claude public catalog | n/a | n/a | n/a | not submitted | n/a | n/a | repository marketplace availability is not a public-catalog listing |
| OpenAI public plugin listing | n/a | n/a | n/a | not submitted | n/a | n/a | repository marketplace availability is not a public-catalog listing |

## Status definitions

- **available** -- the surface installs from its public path with no owner-only step remaining.
- **validated** -- installed and exercised against the governed synthetic fixture (and, where applicable, the pressure/refusal test), with the required refusals observed.
- **partially validated** -- installation and/or discovery succeeded, but behavior, update, uninstall, or a comparable acceptance step was not run.
- **unverified** -- not yet exercised; absence of a failure is not evidence of a pass.
- **unavailable** -- not published or not reachable through any documented path.

## See also

- [User installation guide](user-install.md) -- Python CLI install, upgrade, uninstall.
- [Claude Code and Codex guide](agent-install.md) -- exact plugin commands and their validated boundaries.
- [v0.2.0 public acceptance record](../releases/v0.2.0-public-acceptance.md) -- sanitized evidence backing this table.
- [Release acceptance checklist](../operations/release-acceptance-checklist.md) -- the process this table's evidence was collected under.
