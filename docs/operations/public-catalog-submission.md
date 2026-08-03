# Public catalog submission runbook (Claude + Codex)

Repository-marketplace availability (clients adding `Kemetra/Seshat-BI` directly)
is already shipped. This runbook covers the **optional** step of listing Seshat BI
in the **public discovery catalogs** so users can find it without the repo name.

**Who can do this:** the repository owner / an eligible verified publisher.
Submission is a human action in each platform's portal under a verified identity —
there is no CLI, workflow, or API for it, and it is deliberately not automated.
Both catalogs are **free**; the gate is identity verification, not payment.

Everything below is prepared and verified against the live v0.8.0 release. Copy
the listing fields into each portal form.

---

## Pre-submission checklist (all ✅ as of v0.8.0, verified 2026-08-01)

- [x] Plugin published & installable from the repo marketplace (Claude + Codex).
- [x] `plugin.json` version (`0.8.0`) matches `CHANGELOG.md` (`## [0.8.0]`) and
      git tag `v0.8.0` — version mismatch is the #1 rejection reason, so re-verify
      all three before every submission.
- [x] Valid plugin manifests present, with all seven listing fields (name,
      version, description, author, homepage, repository, license) confirmed in
      both. The manifests live **inside each bundle**, not at the repository
      root — copy these paths, not `.claude-plugin/plugin.json`:
      - Claude: `integrations/claude-code/seshat-bi/.claude-plugin/plugin.json`
      - Codex: `integrations/codex/seshat-bi/.codex-plugin/plugin.json`

      The repository root holds `.claude-plugin/marketplace.json` (the
      marketplace index, a different file) and
      `distribution/bundle-templates/*/` holds the unfilled templates. Neither
      is the artifact a catalog wants.
- [x] License present (Apache-2.0).
- [x] PyPI package live (`seshat-bi==0.8.0`) for the CLI dependency — verified via
      the PyPI JSON API and `/simple/` index, plus a clean-venv
      `pip install seshat-bi==0.8.0` that reports `seshat 0.8.0`.
- [x] GitHub Release published at annotated tag `v0.8.0`, marked Latest.
- [ ] **Owner:** complete identity verification in each portal (individual or
      business) — required before the form will accept a submission.

---

## A. Claude public plugin directory

**Portal:** <https://clau.de/plugin-directory-submission>
(read-only mirror of accepted plugins: `anthropics/claude-plugins-community`)

**Process:** submit the form → automated security scan → Anthropic approval →
listed. Do **not** open a PR against the mirror repo (auto-closed).

**Listing fields to paste:**

| Field | Value |
|---|---|
| Plugin name | `seshat-bi` |
| Marketplace source | `Kemetra/Seshat-BI` (GitHub) |
| Version | `0.8.0` |
| Author | Ahmed Shaaban |
| Homepage / Repository | `https://github.com/Kemetra/Seshat-BI` |
| License | Apache-2.0 |
| Category | Data / Productivity (BI & analytics) |

**Short description (≤ ~1 line):**
> Guarded BI readiness workflow and reviewed public knowledge for Claude Code.

**Long description:**
> Seshat BI is an agent-first Retail BI readiness system. It answers one question
> safely — *is this retail source ready to become trusted Power BI analytics?* —
> through a governed seven-stage readiness flow (Source → Mapping → Silver → Gold
> → Semantic Model → Dashboard → Publish Ready), static and live governance gates
> over SQL/TMDL/PBIR/DAX, source mapping and metric contracts that stop work when
> business meaning is unresolved, and a static HTML readiness dashboard. Readiness
> is never a faked score — it is status + evidence + blocking reasons held by a
> gate. Ships 21 skills/workflows; pairs with the `seshat-bi` PyPI CLI.

---

## B. OpenAI / Codex plugin directory

**Status (2026):** self-serve publishing to the public Codex directory is marked
"coming soon"; current public listing is a **manual review** via OpenAI's plugin
submission portal. **Identity verification is required first** — individual
verification for a personal listing, business verification to publish under a
company name.

**Form sections OpenAI asks for (prepare each):**

- **Info** — public listing details (use the name/description/category above).
- **MCP** — server + auth config. **The bundle declares one MCP server.** Both
  `integrations/codex/seshat-bi/mcp-servers.json` and the Claude equivalent
  register `seshat-governor` (`command: seshat`, `args: ["mcp"]`), backed by the
  shipped `seshat mcp` CLI command. Declare it; do not report "skills-only".
  - **Auth:** none. The server takes no credentials and no network config; its
    only argument is `--repo`, a local repository root exposed for governor
    **reads**.
  - **Transport:** stdio, launched by the host from the `seshat` CLI, which the
    user installs from PyPI (`seshat-bi`). It is not a remote/hosted server.
  - **Optional extra:** the server needs the MCP SDK extra. Absent it,
    `seshat mcp` fails closed with a named two-lane install hint rather than a
    traceback or a simulated governor — see `src/seshat/cli/__init__.py::_run_mcp`.
  - **Honest status:** the server ships and runs, but spec 138 **US1 is not
    accepted** — external harness verification (T021–T023) is still outstanding.
    If a form asks whether MCP behavior is externally verified, the answer is
    **no**. Do not claim verified behavior to a catalog under a verified identity.
- **Skills** — upload the final skill package: the `integrations/codex/seshat-bi`
  bundle (21 skills as of v0.8.0, `.codex-plugin/plugin.json` v0.8.0). Count the
  directories rather than trusting this number — the 0.7 line added
  `bi-analyst-knowledge` and `pbi-mcp-doctor`, and v0.8.0 nearly doubled the
  bundle by shipping the ten compass verbs (spec 138 US2+US3), taking both
  bundles from 11 skills to 21. Both bundles verified at 21 on 2026-08-02:

  ```sh
  ls -d integrations/codex/seshat-bi/skills/*/ | wc -l        # Codex → 21
  ls -d integrations/claude-code/seshat-bi/skills/*/ | wc -l  # Claude → 21
  ```

  Note the asymmetry: the Claude bundle lives under `claude-code/`, not
  `claude/`. A count run against `integrations/claude/...` silently returns 0.
- **Prompts** — example starting prompts (see below).
- **Testing** — test cases (see below).
- **Global** — available countries/regions (owner's choice; default: all).

**Example starting prompts:**
> - "Inspect this retail source and tell me the truthful next readiness action."
> - "Initialize a Seshat BI workspace and show the seven-stage status."
> - "Validate readiness evidence and stop at the correct human approval gate."

**Test cases:**
> - Add marketplace → install → `codex plugin list` shows `seshat-bi`.
> - Router invocation: a BI-readiness request routes into the governed flow.
> - Governed refusal: the plugin refuses to self-grant an approval / fake a score.

---

## After submission — record the outcome

Update the **current release record** in
[`release-acceptance-checklist.md`](release-acceptance-checklist.md) (the v0.8.0
record as of this revision): change "Claude public catalog: not submitted" /
"OpenAI public plugin listing: not submitted" to the actual state (`submitted` /
`under review` / `listed`) with the submission date and the public listing URL
once live. Capture sanitized evidence in a
`docs/releases/v<VERSION>-public-acceptance.md` following the prior
`*-public-acceptance.md` records.

Rollback (if a listing must be corrected/withdrawn): ask the eligible
publisher/platform to withdraw or correct only that listing — repository
marketplace removal is **not** a public delisting.
