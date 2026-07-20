# Public catalog submission runbook (Claude + Codex)

Repository-marketplace availability (clients adding `Kemetra/Seshat-BI` directly)
is already shipped. This runbook covers the **optional** step of listing Seshat BI
in the **public discovery catalogs** so users can find it without the repo name.

**Who can do this:** the repository owner / an eligible verified publisher.
Submission is a human action in each platform's portal under a verified identity —
there is no CLI, workflow, or API for it, and it is deliberately not automated.
Both catalogs are **free**; the gate is identity verification, not payment.

Everything below is prepared and verified against the live v0.5.2 release. Copy
the listing fields into each portal form.

---

## Pre-submission checklist (all ✅ as of v0.5.2)

- [x] Plugin published & installable from the repo marketplace (Claude + Codex).
- [x] `plugin.json` version (`0.5.2`) matches `CHANGELOG.md` and git tag `v0.5.2`
      — version mismatch is the #1 rejection reason.
- [x] Valid `.claude-plugin/plugin.json` (name, version, description, author,
      homepage, repository, license) and `.codex-plugin/plugin.json` present.
- [x] License present (Apache-2.0).
- [x] PyPI package live (`seshat-bi==0.5.2`) for the CLI dependency.
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
| Version | `0.5.2` |
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
> gate. Ships 9 skills/workflows; pairs with the `seshat-bi` PyPI CLI.

---

## B. OpenAI / Codex plugin directory

**Status (2026):** self-serve publishing to the public Codex directory is marked
"coming soon"; current public listing is a **manual review** via OpenAI's plugin
submission portal. **Identity verification is required first** — individual
verification for a personal listing, business verification to publish under a
company name.

**Form sections OpenAI asks for (prepare each):**

- **Info** — public listing details (use the name/description/category above).
- **MCP** — server + auth config. Seshat's plugin is **skills-only** (no MCP
  server required); declare none.
- **Skills** — upload the final skill package: the `integrations/codex/seshat-bi`
  bundle (9 skills, `.codex-plugin/plugin.json` v0.5.2).
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

Update the **v0.5.2 record** in
[`release-acceptance-checklist.md`](release-acceptance-checklist.md): change
"Claude public catalog: not submitted" / "OpenAI public plugin listing: not
submitted" to the actual state (`submitted` / `under review` / `listed`) with the
submission date and the public listing URL once live. Capture sanitized evidence
in a `docs/releases/v0.5.2-public-acceptance.md` following the prior
`*-public-acceptance.md` records.

Rollback (if a listing must be corrected/withdrawn): ask the eligible
publisher/platform to withdraw or correct only that listing — repository
marketplace removal is **not** a public delisting.
