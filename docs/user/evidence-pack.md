# Evidence pack — user guide (roadmap M9)

> **Delivery under Option B (skill-driven).** A user-facing walkthrough of the
> *already-shipped* evidence-pack skills — no new CLI verb, no new capability. The
> interface stays agent + skills (hard rule #1). Decision:
> `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`.

## What an evidence pack is

An evidence pack is the product output that packages the committed evidence behind a
readiness stage — the artifacts, the checks that passed, and the blocking reasons that
remain — so a **named human** can review it and sign off. It **packages** evidence for a
sign-off; it never **grants** the sign-off (verify-slot-only, Principle V).

## The skills that produce it (already shipped)

- **`evidence-pack-generator`** (roadmap F028) — assembles the evidence pack for a stage:
  what artifacts exist, which checks passed (`seshat check` / `retail validate` exit
  codes), and the standing blockers. Categorical status + named blockers only — **never a
  fabricated confidence/health/maturity score.**
- **`approval-evidence-pack`** (roadmap F035, spec 063) — the approval-stage evidence pack
  with the empty `approvals[]` slot a named human fills. It is structurally verify-slot-
  only: it presents the evidence and leaves the approval for the owner to sign.

## The flow

You drive this by talking to the agent:

1. **Generate the pack** — run `evidence-pack-generator` (or `approval-evidence-pack` for
   an approval-stage gate) for the stage you're reviewing.
2. **It lands in `evidence/`** — in a workspace scaffolded by `seshat init-project`, the
   pack is written to the `evidence/` directory (already present in the scaffold).
3. **Review and sign** — you read the pack and, at an approval gate, fill the
   `approvals[]` entry by name. The agent cannot fill it (an agent-shaped value is a
   self-ratify and the gate rejects it).

## Hard stops (the guide never suggests bypassing these)

- **Verify-slot-only** — an evidence pack never grants approval; it packages evidence for
  a human to sign (Principle V, `never_self_grant_approval`).
- **No fabricated score** — status is categorical (ready / blocked) with named blockers,
  never a number (hard rule #9).

## Next

An approved evidence pack feeds the publish/handoff flow — but publish/execution stays
gated behind Semantic Model Ready and a named-human approval (F016, hard rule #6). See the
[readiness model](../readiness/readiness-model.md) and the BI-delivery guide (roadmap M10,
`docs/user/bi-delivery.md`).
