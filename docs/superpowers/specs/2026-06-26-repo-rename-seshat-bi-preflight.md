# Repo Rename Preflight — `Retail_Tower_analytics` → `Seshat_BI`

**Date:** 2026-06-26
**Status:** Executed (GitHub rename + remote update + local-folder rename)

## Scope

**In scope:** the mechanics of renaming the repository.

- Rename the GitHub repo `ahmed-shaaban-94/Retail_Tower_analytics` → `Seshat_BI`.
- Update the local git `origin` remote.
- Update the one hardcoded absolute path that embeds the folder name
  (`.mcp.json`) for the case where the local on-disk folder is also renamed.

**Out of scope (deliberately):**

- **Package rename.** The Python package stays `retail` / `import retail`; the
  CLI entrypoint stays `retail`. `Seshat_BI` is only a *brand alias* per the
  README naming note. Renaming the package is a separate, far riskier refactor
  and is **not** part of a repo rename.
- **Brand-string cleanup.** User-facing "Retail Tower" display strings are
  handled by a separate fresh-README rebrand on `main`, not here.
- **Historical archives.** Dated docs under `docs/superpowers/{specs,plans}/`,
  `.superpowers/sdd/`, and `specs/038-*` are point-in-time records and are not
  rewritten.

## The three names (why a "repo rename" is narrow)

| Name | What it is | Touched by a repo rename? |
|---|---|---|
| `Retail_Tower_analytics` | GitHub repo + local folder name | **Yes** — this is the rename |
| `retail` / `import retail` | Python package + CLI entrypoint | No — permanent; `Seshat_BI` is an alias |
| "Retail Tower" | Old product/brand display string | No — separate README rebrand on `main` |

## Blast radius

### Functional (breaks → must fix)

- **`.mcp.json` absolute path** — line embeds
  `C:\Users\Shaaban\Documents\GitHub\Retail_Tower_analytics\tools\powerbi-modeling-mcp\extension\server\powerbi-modeling-mcp.exe`.
  Breaks **only if the local on-disk folder is renamed**. Since the folder is
  being renamed, this path is updated to the `Seshat_BI` folder.
- **Project memory directory** (not in-repo) — auto-memory lives under
  `…\.claude-work\projects\C--Users-Shaaban-Documents-GitHub-Retail-Tower-analytics\`.
  Renaming the local folder changes the derived project key, so Claude Code
  starts fresh memory unless that directory is migrated. Out-of-repo manual step.

### GitHub-side (near-zero breakage)

- **`git remote` URL** — GitHub **auto-redirects** old URLs after a rename, so
  `git push`/`pull` keep working even before the remote is updated. Updating
  `origin` is hygiene, not urgent.

### Cosmetic (out of scope — noted, not changed)

- ~17 files reference the `Retail_Tower_analytics` token as descriptive labels
  (skill prose, workflow log strings). Stale after rename, harmless.
- 4 active surfaces carry the "Retail Tower" brand string
  (`CLAUDE.md`, `.claude/agents/powerbi-analyst.md`,
  `.claude/skills/retail-govern/SKILL.md`, `.specify/memory/constitution.md`).
  Handled by the separate README rebrand effort.

## Execution paths

### Path A — GitHub-only rename

1. `gh repo rename Seshat_BI` (run against the current repo).
2. (Optional) `git remote set-url origin https://github.com/ahmed-shaaban-94/Seshat_BI`.
3. Done. Auto-redirect covers existing clones/links. `.mcp.json` untouched.

### Path B — GitHub + local folder rename (the chosen path)

1. Path A steps 1–2.
2. Update `.mcp.json` absolute path to the new `Seshat_BI` folder.
3. Manually rename the on-disk folder `Retail_Tower_analytics` → `Seshat_BI`
   (done outside git, with the IDE/agent fully closed to avoid file locks).
4. Migrate or accept reset of the `.claude-work\projects\…` memory directory.

## Verification checklist (post-rename)

- [ ] `gh repo view ahmed-shaaban-94/Seshat_BI` resolves.
- [ ] `git remote -v` shows the `Seshat_BI` URL.
- [ ] `git push` / `git pull` succeed.
- [ ] Power BI MCP server launches (path in `.mcp.json` resolves).
- [ ] `pytest` passes (governance checker unaffected).
- [ ] `retail check` runs.

## Rollback

- GitHub rename is reversible: rename back to `Retail_Tower_analytics`
  (Settings → Rename, or `gh repo rename`). Note GitHub keeps a redirect from
  the *previous* name; renaming back clears the new-name redirect.
- `.mcp.json` path edit reverts via git.
- Local folder rename reverts by renaming the folder back.

## Follow-up (not part of this mission)

- The hardcoded absolute path in `.mcp.json` is brittle by design — any future
  move/rename breaks it. Consider a relative or env-var-based MCP command path.
