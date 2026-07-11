# Phase 1 Data Model: Install to First Success

The "data" for this feature is **packaging metadata, plugin manifest fields, documentation
structure, and the readiness answer shape** — not a database schema. Each entity below
lists its fields, the validation rules drawn from the requirements, and its lifecycle.

---

## Entity: Python Distribution

The user-facing installable artifact.

| Field | Value / rule | Source |
|-------|--------------|--------|
| `distribution_name` | `seshat-bi` | FR-009 |
| `import_module` | `seshat` (renamed from `retail`) | FR-009a |
| `compat_shim_module` | `retail` (thin re-export of `seshat`; ≥1 deprecation cycle) | FR-010 |
| `console_scripts` | `seshat` and `retail`, both → `seshat.cli:main` | FR-002 |
| `version` | per spec 108 versioning policy; bump recorded in `CHANGELOG.md` | FR-008 |
| `runtime_deps` | `pyyaml>=6` only | (unchanged) |
| `optional_extras` | `db`, `mssql`, `mysql`, `snowflake`, `files` (user); `dev`, `livetest` (contributor-only) | FR-011/FR-012 |
| `artifacts` | wheel + source distribution (sdist) | FR-008/FR-021 |

**Validation rules**:
- A normal install MUST NOT pull `dev`, `livetest`, or any DB driver (FR-012).
- Built artifacts MUST contain no secret, credential, token, or machine-specific path
  (FR-013, SC-007).
- `import retail` and `python -m retail.cli <verb>` MUST still resolve after the rename
  (FR-010).

**Lifecycle**: build (wheel+sdist) → clean-env install → `seshat --help` verifies →
upgrade (`pipx upgrade`) / uninstall (`pipx uninstall`) → rollback (yank + revert prior
good) on breakage.

---

## Entity: Fresh Project Workspace

The tree produced by `seshat init-project <name>` (spec 107).

| Field | Rule | Source |
|-------|------|--------|
| directory layout | `mappings/`, `warehouse/{bronze,silver,gold}/`, `powerbi/`, `reports/`, `evidence/`, `README.md`, `.env.example`, `.gitignore`, `.gitattributes` | spec 107 (consumed as-is) |
| governance state | `seshat check` exit 0 (governance-clean) | FR-005 |
| credential handling | `.env` only, git-ignored; `.env.example` is the tracked template | FR-005/FR-013 |
| readiness state | empty projection: `status --format json` → `{"tables": []}` | FR-003 |

**Validation rules**: creating the workspace requires no DB and no Power BI Desktop
(FR-003); `git init` is required before `check`/`next` (git-aware rules).

---

## Entity: Readiness Answer (first-run `next`)

The truthful next-action document returned on a fresh workspace.

| Field | Rule | Source |
|-------|------|--------|
| `current_stage` / `readiness_state` | Source Ready onboarding; `not_started`, never a fabricated pass | FR-004 |
| `next_allowed_action` | the conservative first onboarding action | FR-004 |
| `evidence[]` / `blocking_reasons[]` | present; a pass (none here) would require evidence | Principle spine |
| numeric score | MUST be absent | FR-004, SC-004 |

**Validation rules**: no fabricated readiness pass; no numeric confidence score; no
database prompt on the first run.

---

## Entity: Claude Code Plugin (`seshat-bi`)

| Field | Rule | Source |
|-------|------|--------|
| `plugin.name` | `seshat-bi` | (existing) |
| `marketplace.name` | `seshat-bi-marketplace` | (existing) |
| exposed components | the Seshat skill + the `/seshat-*` commands | FR-017 |
| CLI invocation | primary = `seshat` console script; fallback = `python -m retail.cli` (shim-safe) | FR-010 |
| `status_label` | truthful: draft \| beta \| released — matches reality | FR-018 |
| distribution model | canonical in `Seshat_BI`; if split, a generated **one-way mirror** only | FR-016 |
| public install | `/plugin marketplace add <owner>/<repo>` → `/plugin install seshat-bi@seshat-bi-marketplace`; update `/plugin marketplace update` | FR-015 (verified R1) |

**Validation rules**: no badge/link/wording implies public availability before publication
(FR-018, SC-008); plugin references regenerated from source, never hand-forked (FR-016);
the local dev-only `marketplace add ./…` path is never presented as the public command.

**Lifecycle**: draft (local-verified, today) → beta (published to a hosted marketplace) →
released; rollback = revert mirror to prior tag + status downgrade (FR-022).

---

## Entity: Documentation Entry Path

| Field | Rule | Source |
|-------|------|--------|
| README section | one-sentence value; 3-step quickstart near top; Windows / macOS-Linux separated; "Try without a database"; "Connect your database"; "Use with Claude Code"; truthful status label; expected output; top-N troubleshooting | FR-019 |
| `docs/install/user-install.md` | exists; reconcile into quickstart + labels (truthful) | FR-020 |
| `docs/install/developer-install.md` | NEW — editable/dev install, cleanly separated from user path | FR-020 (M2 deliverable) |
| `docs/install/agent-install.md` | NEW — agent/plugin reference | FR-020 (M2 deliverable) |

**Validation rules**: the user-facing quickstart MUST NOT require reading `AGENTS.md`, the
constitution, the roadmap, or any internal spec before first success (FR-020, SC-005); no
"published" claim before a real artifact (SC-008).

---

## State transition: user journey (readiness of the *user*, not the data)

```
discovered → installed → command-confirmed → workspace-created → first-success-verified
   → (P2) plugin-active → workflow-started
   → (P3, optional) database-connected
```

Each transition has an actionable-error exit if a prerequisite (Python, Git, plugin,
package install) is missing (FR-006).
