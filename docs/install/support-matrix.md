# Support matrix: Seshat BI

The current public release is `seshat-bi==0.5.1` (single-sourced from
`pyproject.toml`), externally accepted per
[the v0.3.1 public acceptance record](../releases/v0.3.1-public-acceptance.md).
Where a row cites v0.2.0 evidence
([record](../releases/v0.2.0-public-acceptance.md)), that surface was not
re-exercised at v0.3.1 and keeps its earlier boundary.

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
| Python CLI (`seshat-bi`) | `pipx install seshat-bi` (PyPI) | Python >= 3.13 | Windows + Python 3.13 | available (v0.3.1: clean-venv public-index install, first success, uninstall preservation) | n/a (not an agent surface) | validated (`pipx upgrade` / `pipx uninstall` at v0.2.0; `pip uninstall` preservation re-verified at v0.3.1) | macOS/Linux documented as best-effort beta; not the release gate |
| Claude Code repository plugin | `/plugin marketplace add Kemetra/Seshat-BI` then `/plugin install seshat-bi@seshat-bi-marketplace` | Claude Code CLI | Claude Code `2.1.211`, Windows 11 (v0.3.1) | validated | validated at v0.3.1 (governed CSV check + pressure/refusal test both passed, headless sessions) | validated at v0.3.1 (`plugin update`, scope-targeted `plugin uninstall`, workspace preserved) | strict fresh-profile install not performed (authenticated operator profile + temporary local-scope workspace); namespaced slash-command discovery verified interactively at v0.2.0, not re-exercised headlessly |
| Codex CLI repository plugin | `codex plugin marketplace add https://github.com/Kemetra/Seshat-BI` then `codex plugin add seshat-bi@seshat-bi-repository` | Codex CLI | codex-cli `0.144.5`, Windows 11 (v0.3.1) | validated | validated at v0.3.1 (governed CSV check + pressure/refusal test both passed via `codex exec`) | validated at v0.3.1 (`marketplace upgrade`, `plugin remove` with marketplace-qualified name, workspace preserved) | Codex IDE path unverified |
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
- [v0.3.1 public acceptance record](../releases/v0.3.1-public-acceptance.md) -- sanitized evidence backing this table.
- [v0.2.0 public acceptance record](../releases/v0.2.0-public-acceptance.md) -- earlier evidence for surfaces not re-exercised at v0.3.1.
- [Release acceptance checklist](../operations/release-acceptance-checklist.md) -- the process this table's evidence was collected under.
