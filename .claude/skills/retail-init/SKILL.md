---
name: retail-init
description: >-
  Bootstrap the Compass-Driven kit and lead a NEW user to a first visible result on
  THEIR own table in the Seshat BI repo. Use when someone asks to "set up the kit",
  "initialize seshat", "onboard me / get me started", or runs `retail init`. The AGENT
  performs this: it writes the backstage substrate (compass router + fenced
  AGENTS.md/CLAUDE.md regions + manifests) via the substrate-only `retail init` CLI,
  DELEGATES the worked-example offer + human-seam list to `first-hour-compass`, and
  ROUTES into `retail-onboard-table` for the Stage-1 read-only profile (grain
  candidates + column types over a live DB, or `[PENDING LIVE PROFILE]` without one).
  It is NOT a terminal wizard, stores no run-state, fetches no remote, self-grants no
  approval, and emits no confidence score.
---

# retail-init

The install-time front door for the Compass-Driven kit. Its one job is to turn a
fresh `pip install` into a first visible result on the user's own table — leading
with analyst value, keeping the substrate backstage. **You (the agent) perform this
flow; the `retail init` CLI only writes substrate and prints the next step.** This is
Phase-1 Step 1-2 of `docs/roadmap/distribution-ideas.md`.

## Scope + non-negotiables (read first)

- **Agent-first, not a wizard (Principle I).** The `retail init` CLI is
  substrate-writing ONLY — it writes `.seshat/` + the fenced regions and prints the
  next step. It never prompts, shows a menu, or emits a profile. The delegate → route
  → profile flow is YOU performing this skill over the existing prose verbs.
- **Delegate, never fork (anti-fork).** The worked-example offer, the human-seam
  list, and the single-table orientation card belong to `first-hour-compass` — its
  single source. The Stage-1 profile belongs to `retail-onboard-table`. Do NOT
  restate any of them here; route into them.
- **No run-state (FR-005).** `compass.yaml` declares the orientation protocol and
  points at per-table `readiness-status.yaml`; it stores no `current_stage`. There is
  no repo-level stage.
- **Fence-only writes (FR-006/FR-007).** The substrate write touches only the
  `<!-- SESHAT-KIT START -->…<!-- SESHAT-KIT END -->` region of AGENTS.md / CLAUDE.md;
  everything outside is hand-authored / constitution-owned and stays byte-identical.
- **Stop at judgment (Principle V).** Grain, PII publish-safety, business
  rollup/segment, product identity are the human's — surfaced (via
  `first-hour-compass`) and STOPPED on, never self-granted.
- ASCII only, UTF-8 no BOM.

## The flow (what you perform)

1. **Bootstrap the substrate.** Run `retail init` (or `retail init --repo <path>`).
   It writes `.seshat/compass.yaml` + manifests and projects the `SESHAT-KIT` fenced
   regions of AGENTS.md / CLAUDE.md, then prints the next step. Do NOT narrate the
   substrate as steps — it is backstage.
2. **Set expectations honestly (FR-009).** State up front: *the agent handles the
   sequence and the plumbing; you still own the judgment seams.* Surface the seam
   wording from `first-hour-compass` (its single source) — do not re-type a divergent
   list.
3. **Delegate the worked-example offer.** Route into `first-hour-compass`, which
   presents `c086-pharmacy` (build-to-Gold) and `retail-store-sales` (full
   seven-stage spine) and takes the user's pick as a narrative pattern to steer by
   (not a file template).
4. **Route into the profile.** Hand the user's named table to `retail-onboard-table`
   (the Source → Mapping front door, which owns the Stage-1 read-only profile). The
   agent-visible first result is the grain candidates + column types it returns.
5. **Degrade honestly when there's no DB.** The Stage-1 profile is DB-backed
   (`profile.py` over a `QueryRunner`). If no `db` extra / DSN is configured, report
   the boundary and the enable steps (`pip install 'retail[db]'`; set `DATABASE_URL`
   or `ANALYTICS_DB_*` in the gitignored `.env`), mark profile numbers `[PENDING LIVE
   PROFILE]`, author the source-map / orientation structure, and STAY USEFUL — never
   traceback, never fake a pass. There is no CSV/Excel profiler (YAGNI).

## What `init` does NOT do

- Does not profile, open a DB, prompt, or show a menu (that is the CLI's hard
  boundary — substrate only).
- Does not advance a readiness stage, write an `approvals[]` entry, or emit a numeric
  health / confidence / percent-ready score (FR-010; hard rule #9).
- Does not fetch from a remote or auto-execute pulled content — kit self-update
  (`sync`, Phase-3) and channel-driven fetch (Phase-4) are later, gated slices
  (FR-011).
- Does not rewrite any hand-authored / constitution-owned content; on a malformed
  fence it STOPS and reports rather than force a rewrite.

## Idempotent re-run

Running `retail init` again on a bootstrapped repo re-projects only the fenced
regions, reports "already bootstrapped", and never duplicates a fence or clobbers the
hand-authored region.

## See also

- The delegated verbs: `.claude/skills/first-hour-compass/SKILL.md` (offer + seams +
  card), `.claude/skills/retail-onboard-table/SKILL.md` (Stage-1 profile).
- The router it writes: `.seshat/compass.yaml`; its canonical source:
  `.seshat/kit-source.yaml`.
- The design + resolved decisions: `docs/roadmap/distribution-ideas.md`;
  `specs/070-retail-init-bootstrap/`.
- The conductor for the later medallion stages: `.claude/skills/retail-orchestrate/SKILL.md`.
