---
name: seshat-studio
description: >-
  Open Seshat Studio, the local analyst console for ONE Seshat workspace, when
  someone asks to "open Studio", "show me the workspace", "launch the console",
  or wants to see readiness, tables, and approvals in a browser instead of a
  terminal. Studio serves a single pinned workspace on loopback only, reads
  recorded state, and stops at the same human approval gates as every other
  Seshat verb. It NEVER grants an approval, advances a stage, writes a pass,
  invents evidence, or emits a numeric readiness/health/confidence score. It
  needs the optional `studio` extra; without it the launch is a named refusal
  with an install remedy, never a traceback. NOT a hosted or shared service, NOT
  a replacement for the readiness verbs, and NOT a Power BI authoring surface.
---

# Seshat Studio

The local analyst console for one Seshat workspace. It presents what the
workspace already records -- readiness by stage, tables, turns, and the
approvals a human still owes -- in a browser, on loopback, for one workspace per
process.

## Launch it by asking

Natural language is the way in. When the user says any of these, launch Studio:

- "open Studio" / "open the Studio console"
- "show me this workspace in the browser"
- "launch the analyst console"
- "I want to see the readiness board"

Confirm the workspace first, then open it. If the user is standing in the
workspace they mean, that is the one -- do not ask them to type a path they have
already chosen by being there. If the current directory is not a Seshat
workspace, say so plainly and name what is missing rather than launching into a
refusal the reader has to decode.

**One workspace per process.** Studio pins exactly one workspace at startup and
serves only that one for its lifetime. To look at a different workspace, stop the
running console and open the other one; there is no in-app workspace switcher,
and that is deliberate -- a console that could silently repoint would let a
reader act on one workspace's evidence while looking at another's.

**Reuse a running console.** If Studio is already serving this workspace, hand
the user that running instance instead of starting a second one. Two consoles on
one workspace is a state-confusion bug, not a convenience: the second process
would present its own view of files the first is also reading.

## What it shows, and what it refuses

Studio RENDERS recorded state. It does not compute a new truth:

- **Creates no truth.** It reads what the workspace records; it defines no
  meaning and sets no status.
- **Grants no approval.** It shows which gate is waiting and who owes it. It
  never records, infers, back-fills, or self-grants a sign-off -- the human
  approval seam is the whole point of the gate.
- **Advances no stage, writes no pass.** Stage transitions belong to the
  readiness verbs, which stop at their own gates.
- **Fabricates no evidence.** A missing field is shown as the honest
  not-started state, never invented.
- **Emits no score.** No numeric health, confidence, percent-ready, or maturity
  value. A request for one is DECLINED -- readiness is the recorded statuses
  plus evidence plus named blockers.
- **Redacts credentials.** Connection strings, passwords, tokens, and
  authorization headers are redacted before anything reaches the browser.

## Local only, by construction

Studio binds loopback on an OS-assigned port and serves one pinned workspace. It
is a local console for the person at the machine, not a hosted, shared, or
multi-tenant service, and it must not be exposed to a network or put behind a
tunnel to share a workspace with someone else. It loads no remote fonts,
scripts, images, or analytics.

## Which agent answers a turn

Studio's deterministic view of the workspace is always available, in every agent
health state -- readiness, tables, and approvals render whether or not an agent
is reachable.

For agent turns, Codex is the full-launch provider and is selected only when the
operator asks for it explicitly. An installed agent CLI is never selected on its
own: presence is not consent to use a provider. Claude Code stays a
deterministic-site and native-handoff integration -- Studio does not embed, hold,
or route Claude subscription credentials, and there is no Claude provider to
select.

When an agent is missing, signed out, incompatible, quota-limited, or crashed,
that is a distinct REPORTED state carrying a recovery action. Studio never
degrades silently from one provider to another, and never falls back onto a
billed path the operator did not choose.

## Relationship to the readiness verbs

Studio is a VIEW plus an agent turn surface. It does not replace the verbs:
onboarding, mapping, metric contracts, warehouse authoring, governance checks,
and live validation each still own their stage transition and their gate. When
the user's next step is a stage transition, route them to the owning verb rather
than implying the console can perform it. Studio is also not a Power BI authoring
surface -- report and model work belongs to the Power BI workflow skills.

## Troubleshooting

Technical detail lives here, below the natural-language path above.

**The console command.** The launcher is `seshat-studio`, a console script
deliberately outside the `seshat` and `retail` dispatch chain so that no web
dependency sits on the static core's import path. Useful flags: `--repo` pins the
workspace to serve, `--agent` selects which agent answers turns (the
deterministic bridge is the default), and `--no-serve` verifies the whole startup
path -- workspace, extra, assets, application -- then exits without binding a
port, which is the fastest way to tell a broken install from a broken workspace.

Exit codes follow the CLI families: `0` success, `1` usage error, `2` refusal
(missing extra, missing frontend assets).

**"It needs the optional `studio` extra."** Studio's web stack is an optional
extra, so a base install stays free of it. That refusal is expected on a base
install, and it names both install lanes. Add the extra with `pipx inject` into
the existing environment, or with `pip install` for a virtual-environment
install; prefer the lane matching how Seshat was installed. Reinstalling the
application itself is the wrong remedy -- it re-resolves the build and can
silently replace a pinned or local one.

**"The extra is installed but the web stack fails to import."** That is a broken
or incomplete environment, not a missing extra; the diagnostic distinguishes the
two and names the module that actually failed. Installing the extra again will
not fix it.

**"Studio started but the interface is blank."** The prebuilt frontend assets are
missing from the installed package. Studio reports this as a named diagnostic
rather than serving an empty page; a build that omits the frontend needs
rebuilding, not reconfiguring.

**Nothing opens in the browser.** Studio binds loopback on an OS-assigned port
and prints the address it chose. Open that address manually -- the port is not
fixed between runs, so a bookmarked address from a previous session will not
reach the current process.

## See also

- The stage-by-stage readiness flow and the verb that owns each transition: the
  `seshat-bi` router skill.
- Single-table orientation before opening a console: the `first-hour-compass`
  skill.
- The governance checker behind the gates Studio displays: the `retail-govern`
  skill.
