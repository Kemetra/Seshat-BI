# Compass-Driven model — senior-engineer + analyst review

> Adversarial review of `distribution-ideas.md`. 15 concerns raised across 3 lenses
> (governance-fit, fact-verification, analyst-value); 12 verified against real files;
> **11 survived** (1 blocker REFUTED, the rest CONFIRMED/PLAUSIBLE and grounded).
> Reviewed 2026-07-02. This is a critique of the NOTE, not a shipped spec — every
> finding is a "fix before speccing" item.

## Verdict in one line

The **model is sound**; the **note oversells it and mis-files it against F024**. Nothing
here kills Compass-Driven — but four things must change before it becomes a spec, and the
analyst-value lens says the *sequencing* is backwards.

## CONFIRMED — must fix before speccing

1. **[governance, high] F024 mis-classification.** The note admits F024 "wasn't built for"
   meta-level kit tools, then still labels `init`/generator as "Product Module." A Product
   Module by definition *consumes Core Authority* (a closed set: readiness status, maps,
   metric contracts, approvals, assumptions, questions — spec 018:122). `init`/generator
   consume the *canonical kit source*, not Core Authority — so they fail the category's own
   input test. **Fix:** open a new spec that either adds a 6th "kit/meta" category (Principle
   VI amendment path, spec 018:485) or formally rules meta-file tools in-scope for Product
   Module. Don't paper it with a "new axis" aside.

2. **[governance, high] AGENTS.md/CLAUDE.md as "projections" is unsafe as written.** Both are
   constitution-governed with a named-human amendment path (constitution.md:22, 156, 512–522).
   CLAUDE.md carries repo law with **no upstream generator** (secrets/.env baseline, exact PBIP
   `.gitignore` baseline, Windows MAX_PATH, line-endings). A blanket `retail sync` regeneration
   could clobber that law or route a constitutional change around the amendment procedure.
   **Fix:** fence the generated region (CLAUDE.md *already* demonstrates the pattern with its
   `<!-- SPECKIT START/END -->` block), exempt the hand-authored/constitution-owned region, and
   forbid regeneration from bypassing constitution.md:512–522.

3. **[fact, high] "spec 001 excludes a CLI installer = human wizard" is a misread.** Spec 001
   excludes *all* install runtime from that docs-only slice; the text draws **no human-vs-agent
   line** — that distinction is the note's own invention. **Fix:** justify `init` as *new scope
   in a later slice*, not as "what the 001 exclusion was really about." (Won't survive a
   speckit-analyze consistency pass otherwise.)

4. **[fact, medium] The `.specify/` precedent is half-overstated.** It proves *scaffold-then-let-
   agent-drive* (true, strong). It does **not** precedent *agent-invocation* — `.specify/` was
   created by a **human** running `specify init --here` (a CLI installer, i.e. the very pattern
   the note's table puts in the "excluded" column). **Fix:** split the precedent — keep the
   steady-state half, drop/footnote the "agent invokes the scaffolder" half (unprecedented here).

5. **[fact, medium] "Codex has no skill system" is an uncited external premise stated as fact** —
   and it's the model's *entire load-bearing why*. The repo can't confirm/refute it (no
   `codex.manifest.json`; `speckit.manifest.json` ≠ Codex). **Fix:** hedge it ("external premise,
   verify at build time"); don't hinge a foundational decision on an unchecked claim.

## CONFIRMED — analyst-value (the sequencing critique)

6. **[analyst, high] First-run shows a green gate on emptiness, not a dashboard.** README's
   Quickstart payoff is `seshat check → exit 0 == governance-clean`; `init` only adds
   orientation files on top. Five minutes in, "the machine tells the agent about the machine" —
   no result the analyst can show. **Fix:** make the first-run path end on a *visible artifact*
   from the user's (or a sample) table — a profile, a mapped grain, a metric contract.

7. **[analyst, high] The one thing an analyst would clone on day one — a worked example — is
   ignored by the bootstrap.** `c086-pharmacy.md` and `retail-store-sales.md` (full spine to
   Dashboard Ready) exist, but `init` lays down compass/projections/manifests and never surfaces
   them. **Fix:** `init` should offer "clone this worked example as your starting point."

8. **[analyst, high] Drift linter + checksummed manifests are kit-author hygiene dressed as
   value.** They only ever tell an analyst "the plumbing is consistent," never "your numbers are
   right." **Fix:** keep them entirely backstage as maintenance CI; never a user-facing step.

9. **[analyst, medium] "Agent drives, human just approves" oversells the relief.** The hard_stops
   the agent won't self-grant (grain, PII, metric policy, no-fabricated-confidence) ARE the hard
   retail-BI judgment. The agent removes *ordering and ceremony*, not *thinking*. **Fix:** say so
   up front — "you still own grain/PII/metric policy; the agent handles sequence and plumbing."

## PLAUSIBLE — judgment calls, weigh don't blindly apply

10. **[governance] "Core-Authority-adjacent" isn't a real F024 tier** and the note never
    reconciles the kit source *up* to the constitution. Partly overstated (the note is openly
    pre-spec, not "smuggling"), but the residue is real: use a real category or explicit
    amendment when spec'd. (Overlaps finding 1.)

11. **[analyst] "Phase-1 is all invisible plumbing" — infra-first vs value-first sequencing.**
    A legitimate design choice (the value verbs already exist and Phase-1 is their substrate),
    but the adopter's-eye critique that day-one should show the tool doing their job once is
    sound product advice. (Overlaps findings 6–7.)

## REFUTED — do NOT act on

- **[analyst, blocker — REFUTED] "Dual-harness parity has zero analyst value, so the model is
  built for the toolmaker."** Refuted: parity is what lets a Codex user drive the *same*
  analyst-producing verbs a Claude Code user does — it's infrastructure *for* analyst value on a
  second harness, not a vendor concern with no user payoff. The premise is real; the "zero value"
  conclusion is wrong.

## What survives unscathed (verified CLEAN)

- `pyproject.toml` extras + `retail` entry point — accurate.
- AGENTS.md "no separate run-state engine" — accurate; the compass-is-not-a-state-store scoping
  is correct and important.
- COMPASS.md "answer what stage first" spine — faithfully paraphrased.
- The core model (one canonical source → projections, package-driven update, compass as
  harness-neutral router) is **not refuted** by any finding.
