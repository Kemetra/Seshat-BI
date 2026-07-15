# Security Scan — Seshat BI

**Date:** 2026-07-15
**Baseline audited:** `origin/main @ 5c06be9` (v0.3.1)
**Distribution surface:** PyPI package `seshat-bi` v0.3.1 · Claude Code marketplace (`.claude-plugin/marketplace.json` → `integrations/claude-code/seshat-bi/`) · Codex marketplace (`integrations/codex/seshat-bi/`)
**Method:** deterministic pre-scan (built wheel = 220 entries + sdist = 220 files inspected; **uncapped git-history credential sweep over all 629 commits**) + a 5-lens adversarial fan-out (13 agents) with a ship-or-drop gate and default-refuted per-finding verification + a completeness critic.

> **Handling note:** This committed copy **redacts the client company name**. The confidentiality item in §6 refers to it only by its internal project code (`C086`), which the owner can resolve. The un-redacted detail was delivered to the owner directly. Do not re-introduce the company name into any tracked file — see §6, "remediation spans three surfaces."

> **Remediation status (applied on branch `worktree-security-scan`, uncommitted, pending owner review):**
> - ✅ **Medium RCE `pbip-adopt-git-in-untrusted-tree` — FIXED (whole vulnerability class, not just the adopt-pbip door).** **Every** `git` call site in `src/` was classified against "can its target tree be attacker-supplied?":
>   - **Hardened** (target may be an externally-authored/`--repo`/adopted tree) with `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c protocol.ext.allow=never`: `gitutil.py` (shared wrapper — `git_output`, `git_check_ignore`, `git_log_subjects`), `pbip_adoption/_safety.py` (`_git_state`), `runner.py` (`_git_ls_files`), `readiness_projection.py` (`_source_revision`), **`portfolio_watch.py` (`_source_revision`, reached by `seshat watch --repo`)**, **`review_integration.py` (`_changed_files`, reached by `retail check --format review --repo`)**.
>   - **Annotated exempt** (target is always a throwaway synthetic repo the module git-inits itself, never external): `severity_posture.py` (`_run`/`_init_repo`).
>   - Guarded by a new regression test that sits on the risk (`test_adopting_a_project_with_a_poisoned_git_config_does_not_execute_it`) — verified RED (payload executed) → GREEN (payload blocked), plus runtime traces confirming 0 unhardened git calls remain on both the adopt-pbip path (0/12) and the `portfolio_watch` path (0/1, payload did not run).
> - ✅ **`no-security-md` — FIXED.** `SECURITY.md` added (private GitHub advisory reporting channel, supported-version statement, response SLA, scope).
> - ✅ **`actions-tag-pinned-not-sha` — FIXED.** All GitHub Actions pinned to full commit SHAs (resolved live via the GitHub API) with `# vX` comments across `ci.yml`, `release.yml`, `prepare-coordinated-release.yml`.
> - ✅ **`no-dependency-scanning` — FIXED.** `.github/dependabot.yml` added (`pip` + `github-actions`, weekly).
> - ✅ **`CODEOWNERS` (proactive) — ADDED.** Routes review of `src/`, workflows, `pyproject.toml`, and the shipped `integrations/`+`distribution/`+`.claude-plugin/` trees to the owner (advisory until branch protection requires Code Owner review).
> - ⏳ **`client-identity-in-shipped-templates` (C086) — OWNER RULING PENDING.** Not auto-scrubbed; the owner must decide whether the naming is authorized (see §6). No code change made.
> - ⏳ **Branch protection / PyPI 2FA / defensive name registration — OWNER ACTION** (outside the repo; see §6).

---

## 1. Executive summary

Seshat BI is in **good** security shape for a published, contributor-facing package. The release/CI pipeline is hardened well beyond the norm: OIDC Trusted Publishing (no long-lived token), `permissions: {}` default-deny, fork + non-tag rejection on the release path, sha256 checksum freeze/re-verify across the job boundary, isolated rebuild, and `attestations: true`. Fork PRs run under a read-only `GITHUB_TOKEN` with no secret injection. No live credentials exist in the shipped artifacts or in git history — every credential-shaped string is a synthetic fixture feeding the tool's own redaction logic, and `.env` is neither tracked nor in history.

**No critical or high findings.** Real findings: **1 medium** (adopt-pbip executes `git` inside an untrusted project tree → fsmonitor RCE), **2 low** (no `SECURITY.md`; Actions tag-pinned not SHA-pinned), **1 info** (no dependency scanning). Separately, a **confidentiality item** the completeness pass surfaced — the shipped marketplace templates name a real client (internal code **C086**) in comment prose — is an **owner ruling**, not a code vulnerability, and aligns with the deferred NAME-sweep from PR #144.

Two candidate findings were **refuted** by adversarial verification (a claimed CODEOWNERS gap and a content-scan-governance gap → both downgraded to info/proactive).

---

## 2. What's already strong (do not re-do)

- **OIDC Trusted Publishing** in `release.yml` — no long-lived PyPI token to leak/rotate.
- **`permissions: {}` default-deny**; `id-token: write` isolated to the publish job only.
- **Fork + non-tag rejection** on release; **`persist-credentials: false`** on checkout.
- **sha256 checksum freeze + re-verification** across the job boundary; **isolated rebuild** step; `attestations: true`.
- **CI on `pull_request` (not `pull_request_target`)** — fork PRs get a read-only token, no repo secrets. Friendly-PR-summary job is opt-in and passes only GitHub-controlled values (repo slug, PR integer) as separate argv, never into a shell.
- **Robust DSN redaction** (`_redact_dsn`) — resilient to the driver-reformatted-traceback leak path.
- **`.env` hygiene** — `.env`, `.env.*`, `tmp/`, worktrees git-ignored; `.env` absent from working tree, tracked set, and **all 629 commits** of history (uncapped credential-shape sweep: clean).
- **Read-only MCP governor** — the distributed `[mcp]` stdio adapter (`src/seshat/governor/`) has **zero write/exec primitives** (no `subprocess`/`exec`/file-write/`remove`); confirmed genuinely read-only, so the MCP tool surface adds no execution risk.
- **Minimal runtime dependency surface** — `pyyaml` only; `psycopg2-binary` + dev tooling in optional extras.
- **Path containment** in the pbip code (resolve + `relative_to` + symlink rejection) and **git option-injection guarding** (`_SAFE_RANGE_RE`) on commit-range input.
- **Clean agent/plugin surface** — no instruction-smuggling, no obfuscation (base64/bidi/zero-width); the operating contract's hard-stops uniformly *constrain* the agent.

---

## 3. Findings

| Severity | ID | Title | Ships via | Fix |
|---|---|---|---|---|
| **Medium** | `pbip-adopt-git-in-untrusted-tree` | `adopt-pbip` runs `git` inside the untrusted adopted-project tree with no config hardening → fsmonitor RCE | PyPI wheel/sdist → `src/seshat/pbip_adoption/_safety.py`, reached by `seshat adopt-pbip assess/scaffold` | Run every git invocation against an adopted tree with `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c protocol.*.allow=never`, or detect VCS state without invoking the tree's own git config |
| **Low** | `no-security-md` | No `SECURITY.md` — no coordinated vulnerability-disclosure channel | Repo root (every consumer of the package + 2 marketplaces) | Add `SECURITY.md` (private reporting channel + supported versions + response SLA); link from `CONTRIBUTING.md` + issue-template config |
| **Low** | `actions-tag-pinned-not-sha` | GitHub Actions are tag-/branch-pinned, not full-SHA-pinned | `.github/workflows/{release,ci,prepare-coordinated-release}.yml` (every PR + every publish) | Pin each action to a 40-char SHA (`actions/checkout@<sha> # v5`); add Dependabot `github-actions` to bump |
| **Info** | `no-dependency-scanning` | No Dependabot/renovate config, no `pip-audit`/`safety` step | `.github/dependabot.yml` (absent); `ci.yml` has no dep-CVE scan | Add `.github/dependabot.yml` (`pip` + `github-actions`, weekly); optional non-blocking `pip-audit` step |

**Confidentiality item (owner ruling, not a security severity):** `client-identity-in-shipped-templates` — see §6.

---

## 4. Findings detail

### Medium — `pbip-adopt-git-in-untrusted-tree`
**File:** `src/seshat/pbip_adoption/_safety.py` L171–193 (`_git_state`), reached via `_assess.py` (L241/L186) and `_seams.py` (L50/L110 → `runner.py` L25 `git ls-files`, `readiness_projection.py` `git rev-parse HEAD`).

**Attack.** A user extracts an attacker-crafted "PBIP project" (shared zip / repo / marketplace sample) that **bundles a poisoned `.git` directory** whose `config` sets `[core] fsmonitor = <shell command>`, then runs `seshat adopt-pbip assess <dir>`. `_git_state(root)` runs `git rev-parse` then `git status --porcelain --untracked-files=all` with `cwd` inside that tree; `_seams.py` also runs `git ls-files` and `git rev-parse HEAD` there. Because the **victim owns the extracted files**, git's `safe.directory` dubious-ownership guard does **not** fire, so git reads the tree's own config and executes the attacker's `fsmonitor` command → arbitrary code execution in the victim's shell. The verifier reproduced this with a live PoC (repo-local `core.fsmonitor` set to a shell command; `git status` executed the payload).

**Two corrections to the original write-up** (verdict unchanged): (1) a `git clone` delivery vector is **wrong** — clone never fetches the remote's `.git/config`; the only viable delivery is an **extracted archive bundling a poisoned `.git`**. (2) The `hooksPath` half is **inert** here — `status`/`rev-parse`/`ls-files` don't run hooks; the confirmed exec is **fsmonitor-only** (the `hooksPath=/dev/null` fix remains good defense-in-depth). `.git` is skipped for file *reading* (`_safe_files`), but git is still *executed* in the tree.

**Fix.** Harden every git invocation that runs against an adopted/untrusted tree:
```
git -c core.fsmonitor=false -c core.hooksPath=/dev/null -c protocol.*.allow=never <subcommand>
```
Apply to `_git_state` in `_safety.py` **and** the `runner.py` / `readiness_projection.py` calls reached via `_seams.py`. Severity stays **medium**: confirmed RCE in a tool whose explicit job is running git against externally-authored trees, but gated by a real precondition (victim must extract *and* run `adopt-pbip` on a tree carrying a malicious `.git`).

### Low — `no-security-md`
`SECURITY.md` is absent (verified via `git ls-tree -r origin/main`); `CONTRIBUTING.md`, PR template, and `ISSUE_TEMPLATE/*` all ship. `ISSUE_TEMPLATE/config.yml` has `blank_issues_enabled: true` and no security contact, so a vulnerability reporter is steered toward a **public issue**, widening the zero-day window. **Fix:** add `SECURITY.md` with a private channel (GitHub private vulnerability reporting or a security email), supported-version statement, first-response SLA; link from `CONTRIBUTING.md` and add as a contact link in `ISSUE_TEMPLATE/config.yml`.

### Low — `actions-tag-pinned-not-sha`
`release.yml` L125 uses `pypa/gh-action-pypi-publish@release/v1` (a mutable **branch** ref) inside the `id-token: write` publish job; other steps + `ci.yml` + `prepare-coordinated-release.yml` use `@v5/@v6/@v4` tags. A retargeted tag/branch would run in the OIDC-privileged publish path and in every PR CI. **Fix:** pin to 40-char SHAs + Dependabot. **Low** — blast radius already constrained by `permissions:{}`, fork/non-tag rejection, checksum freeze/recheck, read-only fork tokens, and all-first-party/PyPA actions. Defense-in-depth.

### Info — `no-dependency-scanning`
No `.github/dependabot.yml`/renovate; `ci.yml` has no `pip-audit`/`safety`/Snyk/Trivy step. Latent, not an active exploit. **Fix:** add `.github/dependabot.yml` (`pip` + `github-actions`, weekly); optional non-blocking `pip-audit`. **Info** — runtime dep surface is `pyyaml` only; risk concentrated in dev/CI extras + unpinned tags (latter covered above).

---

## 5. Recommended hardening (prioritized)

**[F]** = addresses a finding · **[P]** = proactive best-practice.

1. **[F] Fix the adopt-pbip RCE** — harden git invocations against adopted trees. Highest priority; only finding that executes attacker code.
2. **[F] Add `SECURITY.md`** — private disclosure channel + supported versions + SLA; link from `CONTRIBUTING.md` and issue-template config.
3. **[F] Add `.github/dependabot.yml`** — `pip` + `github-actions`, weekly.
4. **[F] SHA-pin GitHub Actions** — 40-char SHAs with `# vX` comments; Dependabot keeps them current.
5. **[P] Add `CODEOWNERS`** — route review of `src/`, `.github/workflows/`, and shipped `integrations/**` to the owner. (Enforced only once branch protection requires it — see §6.)
6. **[P] Add a content-scan CI step for the shipped plugin tree** — statically screen added/edited `integrations/**` markdown/YAML/`SKILL.md`/`CLAUDE.md`/`AGENTS.md` for (a) prompt-injection patterns and (b) confidentiality leaks (real client/company names, internal project codes). Closes the structural blind spot: the existing allowlist `--check` is a *fidelity* gate, not a *safety* gate — edits to an already-allowlisted agent-instruction file currently ship unscanned. Consider a `retail check` rule.
7. **[P] PR-template security checkbox** — "no secrets / no real client identifiers / no injected agent instructions."

---

## 6. Coverage & limits

**Scanned (5 lenses + completeness critic):** secrets & artifact (shipped surfaces + history sweep — **clean**), contributor governance (`no-security-md`, `no-dependency-scanning`; refuted CODEOWNERS + content-scan gaps), prompt injection (169 plugin files + bundle-templates — **clean**), python execution (import dispatch, subprocess, path containment, YAML — one RCE finding), supply-chain/CI (3 workflows + 3 release scripts — hardened; tag-pinning residual).

**Completeness critic — one genuine blind spot the 5 lenses could not see (confidentiality modality):**
- **`client-identity-in-shipped-templates`** — `integrations/claude-code/seshat-bi/templates/metric-contract.yaml` (mirrored in `integrations/codex/seshat-bi/templates/metric-contract.yaml`) names a **real client company** in comment prose, tied to internal project code **C086**. ~10 references across shipped integration files; published to two marketplaces. **Not a credential and not code-exec** — but a real customer identity tied to an internal project code, shipping to consumers. Aligns with the **deferred, owner-gated NAME-sweep from PR #144** (client c086 DATA layer removed from `main`; name sweep deferred).
  - **Owner action:** rule whether this disclosure is authorized. If not, remediation **spans three surfaces, not one** — "scrub the templates" alone is insufficient:
    1. **Shipped templates + plugin tree** — sweep the full `integrations/**` + `distribution/bundle-templates/**` + worked-example tree for real company/person/financial identifiers and scrub.
    2. **Git history** — the C086 history purge is **already owner-gated/deferred** (per PR #144 follow-up); the name persists in history and a purge is a separate, owner-authorized rewrite.
    3. **This report** — the un-redacted version names the company; keep it owner-only (this committed copy is redacted to the `C086` code).
  - Recommendation 6 (§5) would catch this class going forward.

**Modality not exercised (registry-level, outside repo content):**
- **PyPI typosquatting** — `seshat-bi` and confusable neighbors (`seshat`, `seshatbi`, `seshat_bi`, `seshat-ai`) are unclaimed-namespace risk. A short registry follow-up can recommend defensive claims. Forward-looking; not a defect in the current artifact.

**Requires owner action OUTSIDE the repo (unverifiable by file inspection):**
- **Branch protection** — `release.yml` checks `ref_protected`, but CODEOWNERS/CI gates are advisory until branch protection is configured in GitHub settings. Enable required-status-checks + required review (+ required CODEOWNERS review once added) on `main`.
- **PyPI settings** — confirm 2FA is enforced on the account and Trusted Publisher is scoped to the exact repo + workflow; verify no stale long-lived token remains on the project.
- **Defensive name registration** — consider claiming confusable PyPI names (typosquat item above).

**Verified clean — dismissals hold:** wheel `entry_points` target only internal `seshat.cli:main`/`retail` (no plugin-group registration → no hijack surface); `demo.js`/`demo.css` hand-authored (not vendored/minified third-party); Apache-2.0 declared with `LICENSE` shipped in wheel + sdist; zero `.md` knowledge files ship under `src/`; codex `plugin.json` is inert declarative metadata (no hooks/MCP/commands/remote services); unicode/bidi/zero-width in shipped names covered by the injection lens.
