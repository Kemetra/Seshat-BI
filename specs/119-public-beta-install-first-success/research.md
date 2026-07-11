# Phase 0 Research: Install to First Success

All `NEEDS CLARIFICATION` from Technical Context are resolved below. Each decision records
what was chosen, why, and the alternatives rejected.

---

## R1 — Public Claude Code marketplace install syntax (FR-015) — **VERIFIED**

**Decision**: The public plugin flow is:

- **Add the marketplace (from a GitHub repo)**:
  - In-session: `/plugin marketplace add <owner>/<repo>`
  - Headless/CLI: `claude plugin marketplace add <owner>/<repo>`
  - Any git host also works: `/plugin marketplace add https://gitlab.com/org/plugins.git`
- **Install the plugin**: `/plugin install <plugin-name>@<marketplace-name>`
  (for Seshat: `/plugin install seshat-bi@seshat-bi-marketplace`)
- **Update / refresh**: `/plugin marketplace update`
- **`marketplace.json` plugin source** may be a local path (dev only:
  `"source": "./seshat-bi"`) **or** a hosted git source:
  `"source": { "source": "github", "repo": "owner/plugin-repo" }` (optionally with `ref`).

**Rationale**: Command **forms** verified against the current Claude Code documentation
(`code.claude.com/docs`, fetched 2026-07-11). This is the FR-015 plan-phase gate the task
explicitly required: the existing repo's *local* draft command
`claude plugin marketplace add ./integrations/claude-code` uses the **directory** source
type, which the docs mark **"for development only."** The public command replaces the
local path with a **GitHub `owner/repo` shorthand**, so publication requires the
marketplace to be reachable at a hosted git repo — it is **not** the same command with a
different path.

**VERIFIED discovery-location constraint (load-bearing for R4)**: the docs state that
by-repo `add owner/repo` looks for **`.claude-plugin/marketplace.json` at the repository
root** ("Add a GitHub repository that contains a `.claude-plugin/marketplace.json` file
using the `owner/repo` format"; troubleshooting: "verify … that
`.claude-plugin/marketplace.json` exists at the path"). The current repo deliberately
parks its manifest at `integrations/claude-code/.claude-plugin/marketplace.json` (a
**subdirectory**, per the plugin README). So a bare `add ahmed-shaaban-94/Seshat_BI` would
NOT discover the existing manifest — this is a technical constraint on R4 independent of
clone size, carried as an open implementation decision below.

**Still open (implementation-phase, not a first-success blocker)**: which of the three
R4 manifest-location options is chosen (root manifest / remote-URL source / mirror repo).

**Alternatives considered**:
- *Present the local `marketplace add ./…` path as the public command* — REJECTED; it is
  the dev-only directory source and would be a false public claim (violates SC-008 and the
  task's explicit warning).
- *Assume `@marketplace` suffix is optional* — REJECTED; install is
  `<plugin>@<marketplace>`, and the marketplace `name` is public-facing.

**Implication for FR-016**: because the public marketplace source is a hosted git repo,
the plan must decide whether Seshat needs a *separate* repo (R4).

---

## R2 — Distribution name vs import module name (FR-009 / FR-009a)

**Decision**: Distribution (PyPI project) = **`seshat-bi`**; import module = **`seshat`**;
console scripts = **both `seshat` and `retail`**. (Owner-directed, 2026-07-11.)

**Rationale**: The three names are independent in Python packaging. `seshat-bi` is the
safe, already-advertised distribution name (docs + roadmap M2 already say
`pipx install seshat-bi`); a bare `seshat` on PyPI is a generic single word at high risk
of being taken/contested and unverifiable at spec time. The *import module* carries the
clean brand internally (`import seshat`, `python -m seshat.cli`). The user never types
the import name — they type `seshat` (console script) and `pipx install seshat-bi` once.

**Alternatives considered**:
- *`seshat` everywhere* — REJECTED for the distribution: PyPI name-availability risk would
  only surface at publish time and could break the entire quickstart.
- *Keep `retail` as distribution* — REJECTED: the docs already advertise `seshat-bi`; a
  `retail` PyPI name contradicts the brand and the roadmap.

---

## R3 — `retail` → `seshat` rename mechanism (FR-010, clarified 2026-07-11)

**Decision**: Rename the package `src/retail/` → `src/seshat/`, point both console scripts
at `seshat.cli:main`, and keep a **thin `retail` compatibility shim module** that
re-exports `seshat` so `import retail` and `python -m retail.cli` keep resolving for at
least one deprecation cycle.

**Rationale**: Lower risk than rewriting every reference in lockstep; honors the original
"preserve the module" intent; and — decisively — keeps the Claude Code plugin's documented
**fallback** `python -m retail.cli <verb>` working without regenerating the plugin mirror
at the same moment. First success uses the `seshat` console script, which is unaffected by
the module name.

**Alternatives considered**:
- *Rewrite all `retail` references to `seshat` with no shim* — REJECTED (clarified): higher
  risk, breaks the plugin fallback until the mirror is regenerated, and provides no
  deprecation runway for external `import retail` users.

**Acceptance hook**: a test asserts `python -m retail.cli check` and `import retail` still
resolve post-rename (shim present).

---

## R4 — Where does the marketplace manifest live / does Seshat need a separate repo? (FR-016)

**Decision (default + constraint)**: Prefer keeping the plugin **canonical in `Seshat_BI`**
(Principle II; task's "prefer `Seshat_BI` canonical"). But R1 established a hard technical
constraint: by-repo `add owner/repo` discovers **only a repo-ROOT
`.claude-plugin/marketplace.json`**, and the current manifest is in a subdirectory. So the
single-repo default requires resolving *how* the manifest is reached. Three options, to be
decided at implementation:

| Option | How the public add works | Trade-off |
|--------|--------------------------|-----------|
| **(a) Root manifest** | add a repo-root `.claude-plugin/marketplace.json` (or `metadata.pluginRoot` pointing at `integrations/claude-code/seshat-bi`); `add ahmed-shaaban-94/Seshat_BI` | keeps one repo; adds a root-level Claude-plugin file to the BI kit |
| **(b) Remote-URL source** | `/plugin marketplace add <raw-url-to>/integrations/claude-code/.claude-plugin/marketplace.json` | one repo, manifest stays put; docs note URL-marketplaces have relative-path limitations |
| **(c) Generated one-way mirror repo** | a separate distribution repo whose ROOT holds the manifest; `add <owner>/<mirror-repo>` | cleanest consumer UX (no BI-kit clone); the ONLY permitted separate-repo shape — regenerated from `Seshat_BI`, never a second source of truth |

**Rationale**: The docs support all three source types. Principle II and the task favor the
single-repo default (a) or (b); option (c) is justified only if consumers should not clone
the whole BI kit, and then strictly as a generated mirror with a one-way release process.
Plugin references (including the `python -m retail.cli` fallback) are regenerated from
source, never hand-forked, in every option.

**Alternatives considered**:
- *Assume `add ahmed-shaaban-94/Seshat_BI` works as-is* — REJECTED: verified it would not
  discover the subdirectory manifest (R1).
- *Immediately split into a standalone repo* — REJECTED as the default: premature; option
  (c) remains available if clone-size evidence warrants.

---

## R5 — `pipx` install / inject / upgrade / uninstall semantics (FR-001, FR-008, FR-021)

**Decision**: User path is `pipx install seshat-bi` (isolated app venv, `seshat`/`retail`
on PATH via `pipx ensurepath`). Optional DB extras are added with
`pipx inject seshat-bi <extra-driver>` **or** `pipx install "seshat-bi[db]"`. Upgrade is
`pipx upgrade seshat-bi`; uninstall is `pipx uninstall seshat-bi`. `pip install seshat-bi`
is documented as the alternative. `uv tool install` is a documented nice-to-have, not
required for first success.

**Rationale**: `pipx` gives a clean, isolated, user-facing install that keeps dev/live-test
deps out (FR-012) and is what M2 already advertises. Documenting the exact upgrade/uninstall
verbs satisfies FR-021's "upgrade and uninstall documentation."

**Alternatives considered**:
- *`pip install --user`* — documented as alternative but not primary (PATH + isolation are
  murkier than pipx).

---

## R6 — Optional extras documentation (FR-011 / FR-012)

**Decision**: Document the already-present extras as-is: `db` (PostgreSQL/DB validation),
`mssql`, `mysql`, `snowflake`, `files` (file profiling). Do **not** document `dev` or
`livetest` on the user path (they are contributor-only). Normal first install installs
none of them.

**Rationale**: `pyproject.toml` already defines all six extras with meticulous "CI installs
none of these" comments; the spec documents, it does not redesign. The driver-free import
path (Principle VIII) is preserved by construction.

---

## R7 — Cross-platform test scope (FR-007 / SC-002, clarified 2026-07-11)

**Decision**: Windows is the **only gate-required** first-success smoke target. macOS/Linux
first-success steps are documented and covered by a **best-effort, non-blocking** CI job.

**Rationale**: Matches the input's "tested where practical" and SC-001's Windows framing;
avoids over-committing to a cross-platform CI gate for a beta while still exercising the
other platforms.

---

## R8 — Rollback (FR-022, clarified 2026-07-11)

**Decision**: Two documented paths. **Package**: withdraw/yank the broken version and
revert users to the prior good release. **Plugin**: revert the generated one-way mirror to
the prior released tag/commit and re-issue a corrected version; if withdrawn, the
truthful-status label drops back to draft/beta.

**Rationale**: Symmetric, honest recovery for each artifact; preserves the truthful-status
discipline (SC-008) throughout.

---

## Reuse ledger (what this feature does NOT rebuild)

- **Spec 108** — versioning policy, `CHANGELOG.md` discipline, and the install smoke test +
  CI `smoke` job. Reused as the release-quality substrate.
- **Spec 107** — `seshat init-project` fresh-workspace scaffolder. Consumed as-is.
- **Specs 109 / 080** — `status --format json` / `next --format agent`. Consumed as-is.
- **Specs 110–113** — Option-B packaging/discovery over shipped skills. The plugin surfaces
  these; this feature does not re-document their capabilities.
- **Ratified Option B** — skill-driven packaging; no new CLI verbs.

## Sources

- [Create and distribute a plugin marketplace — Claude Code Docs](https://code.claude.com/docs/en/plugin-marketplaces)
- [Discover and install prebuilt plugins — Claude Code Docs](https://code.claude.com/docs/en/discover-plugins)

---

## Implementation reuse and decision ledger (2026-07-11)

- **T001 / Spec 108 reuse:** `docs/operations/versioning-policy.md`, `CHANGELOG.md`, and the CI smoke job are reused. The smoke harness now builds both wheel and sdist, performs an isolated `pipx` installation, exercises C1/C4/C5/C6, and asserts that developer, live-test, DB-driver, and file-reader modules are absent from the normal install.
- **T003 / extras boundary:** `db`, `mssql`, `mysql`, `snowflake`, and `files` remain user-path optional extras. `dev` and `livetest` remain contributor-only. No extra changed its dependency list.
- **T014 / R4 decision:** choose **option (a), repository-root manifest**. `.claude-plugin/marketplace.json` is canonical in `Seshat_BI` and references `./integrations/claude-code/seshat-bi`. This follows the documented root-manifest discovery rule, keeps one authoritative repository, and requires no mirror repository or publication action.
- **T019:** not applicable under the root-manifest decision; no mirror exists. If a future mirror is needed, it must be generated one-way from this repository and all plugin references regenerated from source.
- **T030:** the constitution Scope-Boundaries "NO CLI installer" follow-up remains explicitly flagged for human amendment/ratification. This implementation does not edit `constitution.md`.
- **Version record:** the distribution rename is listed under `CHANGELOG.md` Unreleased. The on-disk version remains `0.1.0` pending the owner’s required version-bump decision; the agent did not self-grant that approval.