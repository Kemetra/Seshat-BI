# Contract: First-Success CLI Surface

The observable command contract the first-success journey (User Story 1 / P1) depends on.
It is expressed against **already-shipped** verbs (no new verb is introduced). This is the
acceptance oracle: each row is a testable input → expected output/exit-code assertion,
runnable in a clean environment with **no database and no Power BI Desktop**.

Console command is `seshat` (alias `retail`); the module fallback is `python -m seshat.cli`
(and `python -m retail.cli` via the compat shim).

| # | Command | Precondition | Expected output (contract) | Exit |
|---|---------|--------------|----------------------------|------|
| C1 | `seshat --help` | package installed | usage text listing subcommands incl. `init-project`, `status`, `next`, `check` | 0 |
| C2 | `seshat init-project <name>` | writable CWD, `<name>` absent | creates the fresh workspace tree (spec 107); prints created paths + next step | 0 |
| C3 | `cd <name> && git init` | workspace created | git repo initialized (required by git-aware rules) | 0 |
| C4 | `seshat status --format json` | inside fresh workspace | JSON `{"tables": []}` (empty projection); no numeric score | 0 |
| C5 | `seshat next --format agent` | inside fresh workspace | agent next-action document: `current_stage` = Source Ready onboarding, `readiness_state` not_started, `evidence[]`/`blocking_reasons[]` present, `next_allowed_action` set, **no** fabricated pass, **no** numeric score | 0 |
| C6 | `seshat check` | inside fresh workspace (git-init'd) | static gate over the workspace: governance-clean | 0 |

## Negative / actionable-error contract (FR-006)

| # | Condition | Expected behavior | Exit |
|---|-----------|-------------------|------|
| E1 | Python missing / wrong version | quickstart prerequisite check (or install error) names required Python version + how to install | non-0 |
| E2 | `seshat` not on PATH after install | documented remediation (`pipx ensurepath`) + module fallback (`python -m seshat.cli`) | n/a (doc) |
| E3 | Git missing when running `check`/`next` | error names Git as the missing prerequisite | non-0 |
| E4 | Package install broken/absent | actionable error; never a silent or misleading success | non-0 |

## Backward-compat contract (FR-010)

| # | Command | Expected | Exit |
|---|---------|----------|------|
| B1 | `python -m retail.cli check --repo .` | resolves via the `retail` compat shim; behaves identically to `python -m seshat.cli check` | 0 |
| B2 | `import retail` (Python) | resolves (shim re-exports `seshat`) | n/a |

## Truthfulness invariants (assert across C4–C6, all phases)

- No fabricated readiness pass (SC-004).
- No numeric confidence score anywhere in output (FR-004).
- No database or Power BI Desktop required for C1–C6 (FR-003, SC-002).
- No credential written to any tracked file (FR-005/FR-013).

## Plugin install contract (User Story 2 / P2) — verified syntax (R1)

| # | Command | Expected | 
|---|---------|----------|
| P1 | `/plugin marketplace add <owner>/<repo>` (or `claude plugin marketplace add <owner>/<repo>`) | registers the Seshat marketplace from its hosted git repo |
| P2 | `/plugin install seshat-bi@seshat-bi-marketplace` | installs the plugin; the Seshat skill + `/seshat-*` commands load (FR-017) |
| P3 | `/plugin marketplace update` | refreshes the local marketplace copy |

> The local dev-only form `claude plugin marketplace add ./integrations/claude-code`
> (directory source) MUST NOT be presented as the public command (FR-015, SC-008).
