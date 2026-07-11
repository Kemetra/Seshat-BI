# Implementation Plan: Seshat BI Public Beta — Install to First Success

**Branch**: `119-public-beta-install-first-success` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/119-public-beta-install-first-success/spec.md`

## Summary

Turn Seshat BI from a developer-only editable GitHub install into a user-facing Python
distribution with a tested, database-free first-success experience and a public Claude
Code plugin install/update story — **without** adding CLI verbs, publishing anything, or
creating a second product architecture. The primary requirement: a new external user
reaches a working `seshat check` on a fresh workspace in under 10 minutes on Windows,
then starts the skill-driven Claude Code workflow and receives a truthful Source Ready
action. Technical approach: (1) rename the packaging identity (distribution `seshat-bi`,
import module `retail`→`seshat`, both console scripts kept, `retail` compat shim);
(2) reuse spec 108's release readiness (versioning/changelog/smoke test); (3) author the
README quickstart + `docs/install/*` set; (4) document the public plugin flow with the
**verified** marketplace syntax; (5) define upgrade/uninstall/rollback. First-success
(User Story 1) is independently shippable and does **not** depend on the module rename.

## Technical Context

**Language/Version**: Python 3.13 (matches current `requires-python = ">=3.13"`).

**Primary Dependencies**: runtime `pyyaml>=6` only (unchanged). Build backend `hatchling`.
Optional extras already present: `db` (psycopg2-binary), `mssql`, `mysql`, `snowflake`,
`files` (openpyxl); dev-only `dev` (pytest/ruff), `livetest` (testcontainers). No new
runtime dependency is introduced.

**Storage**: N/A for first success (static, git-aware, filesystem only). Optional DB
(any Postgres via DSN; SQL Server/MySQL/Snowflake via the Dialect seam) is the explicit
later step, credentials in git-ignored `.env` only.

**Testing**: pytest (`-m unit` is the CI gate); the existing 900+-test suite must stay
green across the rename. Spec 108's install smoke test (build → clean-env install →
assert console scripts + `seshat check`) is the release-quality harness this plan reuses.

**Target Platform**: Windows is the gate-required first-success target (clarified
2026-07-11); macOS/Linux documented + best-effort non-blocking CI.

**Project Type**: Single Python project (CLI gate + agent skills), packaged as one
distribution. Not web/mobile.

**Performance Goals**: New-Windows-user time-to-first-success < 10 minutes (SC-001);
`seshat --help` / `status` / `next` / `check` succeed 100% in a clean env with no DB
(SC-002).

**Constraints**: No new CLI verbs (ratified Option B); no fabricated readiness / no
numeric score; secrets only in `.env`; Windows `MAX_PATH` (repo-relative ≤ 200 chars,
Principle IX); no "published" claim before a real artifact; no second authoritative repo.

**Scale/Scope**: Docs + packaging metadata + a bounded `retail`→`seshat` rename with a
compat shim. No new runtime features. Estimated surface: `pyproject.toml`, `src/` module
rename + shim, `docs/install/*` (3 files), top-level `README.md` section, plugin docs
under `integrations/claude-code/`, and reuse of the existing CI smoke job.

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.7.0. Must pass before Phase
0; re-checked after Phase 1.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| **I. Agent-First, Gate-Enforced** | **PASS / reinforced** | The plan packages the *skill-driven* product; the agent + skills stay the interface, the CLI stays the narrow gate. First success ends at `seshat check` (the gate) and a truthful `next` (evidence, no self-granted pass). Adds no rule and weakens no gate. |
| **II. Depend, Never Fork** | **PASS** | No Power BI execution adapter work; no `pbi-cli` reliance. The Claude Code plugin is a distribution surface for existing skills, and (if a separate repo is needed) a **generated one-way mirror**, never a fork/second source of truth (FR-016). |
| **III. Medallion, Postgres-First, Gold-Only** | **PASS / untouched** | No warehouse/schema/read-surface change. DB is optional and later; the extras documentation matches the ratified multi-engine read-only seam (amendment 1.7.0). |
| **IV. Source Mapping Before Silver** | **PASS / untouched** | First success stops at Source Ready onboarding; no silver/gold work. |
| **V. Agent Stops at Judgment Calls** | **PASS / reinforced** | `next` returns the truthful next allowed action with no fabricated readiness; publication + spec ratification remain named-human seams the plan does not cross. |
| **VI–VII. Defaults / C086-is-example** | **PASS / N/A** | No cleaning defaults or worked-example schema touched. |
| **VIII. Static-First, Live Deferred** | **PASS** | First success is stdlib-only, driver-free, CI-able; DB drivers stay optional + lazy; normal install pulls no driver (FR-012). |
| **IX. Secrets & Reproducibility** | **PASS / reinforced** | `.env`-only credentials (FR-005/013), UTF-8-no-BOM tracked text, short Windows paths, no secret/machine-path in artifacts (SC-007). Directly serves this principle. |

**Scope-Boundaries clause ("NO CLI installer")**: This clause scopes the *Phase 0/1
foundation* slice and predates roadmap M2. The **installable user experience is M2**,
which was ratified and unblocked (roadmap owner-lock 2026-07-07) and delivered under the
ratified **Option B** skill-driven decision. Packaging the already-shipped skills is
therefore *not* the forbidden "CLI installer" (which meant adding an installer *in that
early slice*), and this plan adds **no new CLI verb**. No violation — recorded here for
traceability rather than in Complexity Tracking.

**Result: PASS. No principle violated; several are reinforced. Complexity Tracking table
is empty (no justified violations).**

**Follow-up flagged (NOT done here — human ratification seam, Principle governance
procedure point 4)**: the constitution's Scope-Boundaries "NO CLI installer" line is a
Phase-0/1-slice boundary that shipped reality (M1/M2, Option B) has superseded. It SHOULD
be amended (PATCH/MINOR) to reflect the installable user experience so the constitution
does not read as contradicting shipped work. The agent does **not** edit `constitution.md`;
this is recorded for a human amendment. `/speckit.analyze` should stress-test this
constitution↔plan reconciliation as the single most challengeable line here.

**Open implementation decision (not a first-success blocker)**: R4 manifest-discovery
location — by-repo `add owner/repo` discovers only a repo-ROOT
`.claude-plugin/marketplace.json`, but the current manifest is in a subdirectory. The
plan carries three options (root manifest / remote-URL source / generated mirror repo);
the choice is made at implementation, gated behind ratification.

## Project Structure

### Documentation (this feature)

```text
specs/119-public-beta-install-first-success/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output — decisions incl. VERIFIED plugin syntax
├── data-model.md        # Phase 1 output — packaging/plugin/doc entities
├── quickstart.md        # Phase 1 output — the tested first-success walkthrough
├── contracts/           # Phase 1 output — the first-success command contract
│   └── first-success-cli.md
├── checklists/
│   └── requirements.md  # /speckit.specify output (present)
├── spec.md              # /speckit.specify + /speckit.clarify output (present)
└── tasks.md             # /speckit.tasks output (NOT created by /speckit.plan)
```

### Source Code (repository root — files this feature touches)

```text
pyproject.toml                       # [project].name retail -> seshat-bi;
                                     #   wheel packages src/retail -> src/seshat;
                                     #   [project.scripts] both -> seshat.cli:main
src/
├── seshat/                          # renamed from src/retail/ (whole package)
│   └── cli/ ...                     # python -m seshat.cli <verb>
└── retail/                          # THIN compat shim (re-exports seshat) — one
                                     #   deprecation cycle; keeps `import retail`
                                     #   and `python -m retail.cli` resolving (FR-010)
tests/                               # every `import retail` / `python -m retail.cli`
                                     #   reference updated; shim-resolution test added
docs/
├── install/
│   ├── user-install.md              # exists — reconcile into the quickstart + labels
│   ├── developer-install.md         # NEW (M2 deliverable) — editable/dev install
│   └── agent-install.md             # NEW (M2 deliverable) — agent/plugin reference
README.md                            # NEW quickstart section (value + 3 steps + tabs
                                     #   + try-without-db + connect-db + use-with-claude
                                     #   + truthful status + expected output + top errors)
integrations/claude-code/
├── README.md                        # public marketplace flow (verified syntax) + status
├── .claude-plugin/marketplace.json  # source label truthful (draft/beta); mirror plan
└── seshat-bi/                       # plugin: python -m retail.cli fallback -> shim-safe;
                                     #   references regenerated from source (one-way mirror)
.github/workflows/ci.yml             # REUSE spec 108 smoke job; extend to assert
                                     #   seshat-bi build + seshat/retail scripts (+ best-
                                     #   effort non-blocking mac/linux leg)
CHANGELOG.md                         # REUSE spec 108 changelog discipline (rename entry)
docs/operations/versioning-policy.md # REUSE spec 108 policy (record the rename bump)
```

**Structure Decision**: Single-project Python distribution. The one structural change is
the `src/retail/` → `src/seshat/` package rename plus a thin `src/retail/` compat-shim
package (FR-010). Everything else is docs and packaging metadata layered over the existing
tree; no new runtime module, no new CLI verb, no new test framework.

## Phase 0 — Research (see research.md)

Resolved unknowns: (R1) **public Claude Code marketplace install syntax** — VERIFIED
against `code.claude.com/docs` July 2026; (R2) distribution vs import naming; (R3) rename
mechanism (compat shim); (R4) separate-repo mirror necessity; (R5) `pipx` install/inject/
upgrade/uninstall semantics; (R6) extras documentation; (R7) cross-platform test scope;
(R8) rollback. No `NEEDS CLARIFICATION` remains.

## Phase 1 — Design & Contracts

- **data-model.md** — the packaging/plugin/doc/readiness entities and their validation
  rules (the "data" here is metadata + doc structure, not a DB schema).
- **contracts/first-success-cli.md** — the observable command contract the first-success
  journey depends on (inputs, expected outputs, exit codes) — the acceptance oracle for
  User Story 1, expressed against already-shipped verbs.
- **quickstart.md** — the copy-pasteable, Windows-first walkthrough that IS the tested
  first-success path (the artifact SC-001/SC-002 measure).
- **Agent context update** — the SPECKIT pointer block in the repo `CLAUDE.md` is updated
  to reference this plan.

**Post-Design Constitution re-check**: unchanged — PASS. The design adds no runtime, no
verb, no gate; it reinforces Principles I, V, VIII, IX.
