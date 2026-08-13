# Support matrix: Seshat BI

The current public release is `seshat-bi==1.0.0` (single-sourced from
`pyproject.toml`; the pin is projected at release-preparation time, so actual
index availability is confirmed per release in
[the release acceptance checklist](../operations/release-acceptance-checklist.md)
— v0.7.0 was tagged but never published), externally accepted per
[the v0.3.1 public acceptance record](../releases/v0.3.1-public-acceptance.md).
Where a row cites v0.2.0 evidence
([record](../releases/v0.2.0-public-acceptance.md)), that surface was not
re-exercised at v0.3.1 and keeps its earlier boundary.

> **Bundle contents changed after the recorded acceptance passes (spec 138 US3).**
> Both plugin bundles now carry **21** skills rather than 11: the ten readiness
> verbs `.seshat/kit-source.yaml` names were added. Every acceptance claim in the
> table below was collected against the earlier 11-skill contents, so **no row's
> behavior-validation claim covers the ten newly bundled verbs** -- those claims are
> not carried forward onto the new contents.
>
> What *was* exercised against the new contents, locally, on Windows + Python 3.13:
> `seshat agent verify` for both targets reports every governed hard-stop scenario
> PASS (`no_silver_before_mapping`, `no_invented_metric_meaning`), plus
> `update_integrity` (241 generated files match their recorded `output_sha256`
> provenance) and `uninstall_integrity`. `version_compatibility` is BLOCKED for a
> pre-existing tooling reason unrelated to bundle contents -- the audit surface
> imports `scripts.check_release_versions` and `scripts/` is not an importable
> package. External harness acceptance for the new contents is **pending** and is
> the remaining US5 step.

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
| Governed statistical core (`stats`) | `pipx install "seshat-bi[stats]"` | Python >= 3.13; exact NumPy/SciPy/statsmodels pins | Windows + Python 3.13 | available in source candidate | locally validated against synthetic evidence | follows CLI environment lifecycle | public-index acceptance pending next release; derived evidence only |
| Change-point extension (`stats-change`) | install `stats`, then inject `ruptures==1.1.10` | Python >= 3.13 | Windows + Python 3.13 | available in source candidate | locally validated against synthetic series | follows CLI environment lifecycle | public-index acceptance pending next release |
| Statistical Gold adapter | add `db` to `stats`; configure gitignored `.env` | PostgreSQL + optional driver | unit-tested read-only runner | available in source candidate | compiler and mocked-runner validated; optional live proof is DSN-gated | follows CLI environment lifecycle | PostgreSQL-only initial boundary; no live claim without explicit proof |
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
