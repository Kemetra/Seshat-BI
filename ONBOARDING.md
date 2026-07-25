# Welcome to Seshat BI

## How We Use Claude

Based on Ahmed Shaaban's usage over the last 30 days:

Work Type Breakdown:
  Improve Quality  ████████░░░░░░░░░░░░  41%
  Build Feature    █████░░░░░░░░░░░░░░░░  27%
  Plan Design      ████░░░░░░░░░░░░░░░░░  18%
  Debug Fix        ██░░░░░░░░░░░░░░░░░░░  9%
  Write Docs       █░░░░░░░░░░░░░░░░░░░░  5%

Top Skills & Commands:
  /usage             ████████████████████  23x/month
  /model             ████████░░░░░░░░░░░░  9x/month
  /effort            ███████░░░░░░░░░░░░░  8x/month
  /plugin            ███████░░░░░░░░░░░░░  8x/month
  /speckit-analyze   █████░░░░░░░░░░░░░░░  6x/month
  /clear             ████░░░░░░░░░░░░░░░░  5x/month
  /speckit-specify   ███░░░░░░░░░░░░░░░░░  3x/month
  /reload-plugins    ███░░░░░░░░░░░░░░░░░  3x/month

Top MCP Servers:
  CodeScene  ████████████████████  56 calls

## Your Setup Checklist

### Codebases
- [ ] Seshat-BI — https://github.com/kemetra/seshat-bi

### MCP Servers to Activate
- [ ] CodeScene — code-health analysis and technical-debt prioritization. Seshat PRs run a CodeScene "new code is healthy" gate, so you'll use this constantly. Get access via the CodeScene plugin (`/plugin`) and an org CodeScene account/token.

### Skills to Know About
- [ ] /usage — check your Claude usage/quota for the session.
- [ ] /model — switch models (Opus for synthesis/review, Sonnet for mechanical agents; Haiku is below the floor here).
- [ ] /effort — set reasoning effort / orchestration mode (this repo runs `ultracode` for heavy work).
- [ ] /plugin — install and manage plugins, including the CodeScene MCP and the seshat-bi plugin.
- [ ] /speckit-specify — start a feature spec from a natural-language description (the front of the spec-kit chain).
- [ ] /speckit-analyze — non-destructive cross-artifact consistency check across spec.md / plan.md / tasks.md.
- [ ] /clear — reset conversation context between unrelated tasks.
- [ ] /reload-plugins — pick up plugin changes without restarting.

## Team Tips

_TODO_

## Get Started

_TODO_

<!-- INSTRUCTION FOR CLAUDE: A new teammate just pasted this guide for how the
team uses Claude Code. You're their onboarding buddy — warm, conversational,
not lecture-y.

Open with a warm welcome — include the team name from the title. Then: "Your
teammate uses Claude Code for [list all the work types]. Let's get you started."

Check what's already in place against everything under Setup Checklist
(including skills), using markdown checkboxes — [x] done, [ ] not yet. Lead
with what they already have. One sentence per item, all in one message.

Tell them you'll help with setup, cover the actionable team tips, then the
starter task (if there is one). Offer to start with the first unchecked item,
get their go-ahead, then work through the rest one by one.

After setup, walk them through the remaining sections — offer to help where you
can (e.g. link to channels), and just surface the purely informational bits.

Don't invent sections or summaries that aren't in the guide. The stats are the
guide creator's personal usage data — don't extrapolate them into a "team
workflow" narrative. -->
