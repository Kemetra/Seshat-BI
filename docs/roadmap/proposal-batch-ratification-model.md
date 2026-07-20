# Proposal: Batch / Pre-Authorization Ratification Model

**Date**: 2026-07-04
**Status**: RATIFIED (Ahmed Shaaban, 2026-07-04) -- model adopted at "build+PR" reach
**Author**: agent (advisor-validated); transcribed from the owner's decision
**Relates**: `never_self_grant_approval` (hard-stop), Principle V, shipped J1
(approval-evidence-pack skill + template), `ratify-seam-not-auto-cleared` (memory)

## Ratification record (transcribed, not decided by the agent)

The owner ratified this model via an explicit AskUserQuestion selection on
2026-07-04 (the same transcribe-a-named-decision path used for the B1/I3 ratify
ledgers). The agent recorded the decision; it did not make it.

- **Adopt the model** -- YES, at **`build+PR` reach** (clean specs proceed to build
  + open a PR autonomously; the owner still reviews/merges the PR; NOT
  auto-merge-if-green).
- **Advisor role** -- VERIFY only (confirm the envelope conditions hold, record the
  check, PARK on any fail). The advisor never approves and never makes a judgment
  call.
- **The mechanical/judgment split** is confirmed as written below: pre-authorization
  covers the mechanical/eligible half only; in-spec judgment calls (align-first,
  fork-ruling class) ALWAYS escalate.

> IMPLEMENTATION NOTE (scope, pending an owner sub-decision): J1's
> `approval-evidence-pack` is a SKILL + TEMPLATE -- a documented process the agent
> follows -- NOT a `@register` rule. As-scoped, "implement the model" delivers
> *documented, agent-followed* pre-authorization, not a hard gate that
> structurally blocks a bad auto-approval. An ENFORCED split would need its own
> Python rule + spec. This doc is ratified as the ENVELOPE SEMANTICS; the
> skill-vs-enforced-rule build shape is the next owner call (see the open question
> at the end).

---

## The problem you raised

> "Change the ratifying so I can ratify one or a group of specs/ideas before its
> planning finishes -- to keep the autonomy and not destroy it when I can't keep
> eyes on the process all the time -- and I can authorize the advisor tool."

Two real needs:
1. **Autonomy without babysitting** -- a spec should be able to proceed to
   build+PR without you catching each ratify ledger in real time.
2. **Upstream authorization** -- you want to authorize a spec/group ONCE, before
   its planning finishes, and have that authorization survive into the run.

## The constraint that shapes the answer (why it can't be naive delegation)

Ratification is a **Principle-V human seam**; `never_self_grant_approval` is a
hard-stop. Two things follow:

- **The advisor may VERIFY, never APPROVE.** Handing the advisor the ratify
  authority would convert a human seam into an AI seam -- exactly what the seam
  exists to prevent. This session proved AI review is fallible: an analyze pass
  rated B1 "CONSISTENT / 0 high," then an adversarial reviewer found TWO HIGH
  defects (a silent-no-op wiring gap; a fabricated "IL1" citation). AI narrows
  what reaches you; it cannot replace you as approver.
- **This model change cannot approve itself.** Using a not-yet-ratified relaxed
  process to ratify the relaxation is the bootstrap the hard-stop blocks. So this
  is a PROPOSAL you sign under the CURRENT strict rules -- not something the agent
  self-adopts.

## The design: pre-authorization envelope + advisor-as-verifier

Not "delegate approval." Instead: **you sign a durable, named authorization
UPFRONT that says what may proceed autonomously and under what conditions; the
advisor's only job is to CHECK those conditions hold and record the check;
anything failing PARKS for you.**

### 1. The envelope (you author + sign, per spec or per group)

A committed, named authorization -- an `approval-evidence-pack` entry (reusing
shipped J1), e.g.:

```yaml
# authorized by: <your name>, 2026-07-04
batch_authorization:
  scope: [B1, I3]            # or "the design-lint wave", a named group
  may_proceed_to: build+PR   # NOT auto-merge unless you also grant that
  conditions:                # ALL must hold, checked by the advisor per spec
    - adversarial_review: 0 critical, 0 high
    - no_open_principle_v_judgment_call   # see the split below
    - envelope_holds: [no execution, no numeric score, no gate self-grant,
                       no doc/prose rewrite by the agent]
    - local_gate_green: [ruff, pytest -m unit, seshat check, retail kit-lint]
  on_any_condition_fail: PARK for owner   # never proceed on a miss
```

### 2. The advisor's authorized role (VERIFY, record -- never decide)

For each spec in scope, the advisor confirms every condition and writes the result
into the SAME recorded-decision surface J1 already uses (it transcribes a check
against YOUR pre-set criteria; it never supplies the ratification or makes a
judgment call). Pass -> proceed within the granted scope. Fail -> park.

### 3. The split that makes it safe -- MECHANICAL vs JUDGMENT

Pre-authorization can only cover the **mechanical/eligible** half. It can NEVER
pre-clear an in-spec **judgment call**:

| PRE-AUTHORIZABLE (envelope covers) | ALWAYS ESCALATE (you decide, per spec) |
|---|---|
| 5-place wiring, count lockstep | B1's align-first vs synonym-map (edits your prose) |
| adversarial review clean | I3's shared-vs-distinct fork ruling (a cross-layer identity call) |
| no-execution / no-score envelope | authoring any contract manifest (shared-spine.yaml) |
| local gate green | anything resolving grain / PII / product identity |

This is why "ratify BEFORE planning finishes" is safe ONLY for the mechanical
envelope: signing a spec whose judgment seam is still open would be a blank check
on a decision not yet surfaced. **The envelope authorizes "proceed with the clean
mechanical build"; it does not make the judgment calls.**

### Concretely for the two live specs

- **B1 (085)**: eligible for the envelope EXCEPT its one judgment seam (align-first
  + the visual-qa.md prose edit). If you pre-authorize B1 and separately make the
  align-first call, the rest (scaffold, wiring, tests, PR) can run autonomously
  under advisor verification.
- **I3 (086)**: NOT envelope-eligible yet -- its core is a judgment (rule the fork
  shared/distinct) + an authored manifest. Pre-authorization can't cover that; it
  stays "escalate" until you author the spine. Honest example of the split.

## What this buys you

- You authorize **once, upfront**, for a spec or a whole group.
- The run proceeds to build+PR **without** you watching, as long as it stays clean.
- The advisor keeps it honest by **checking**, and **parks** anything that isn't --
  so a failure surfaces for you instead of proceeding wrong.
- The human seam is preserved: authority always traces to your named, pre-recorded
  decision; judgment calls always reach you.

## Owner decisions

1. ~~**Ratify this model**~~ -- **DONE** 2026-07-04 (Ahmed Shaaban): adopted.
2. ~~Default `may_proceed_to`~~ -- **DONE**: `build+PR` (owner reviews/merges).
3. ~~Confirm the MECHANICAL/JUDGMENT split~~ -- **DONE**: confirmed as written.

## OPEN -- the next owner call (build shape)

**Skill (documented process) vs enforced rule (a hard gate).** J1's
`approval-evidence-pack` is a SKILL + TEMPLATE the agent FOLLOWS; it cannot
structurally block a mis-scoped auto-approval. Two build shapes:

- **(a) Documented-skill extension** (what J1 is): author an
  `approval-envelope` skill + template capturing the envelope semantics + the
  advisor-verify step. Small, matches the shipped J1 pattern, but the split is
  *agent-followed*, not enforced.
- **(b) Enforced rule**: a `@register` rule that reads a committed envelope file
  and FAILS if a spec marked auto-authorized still carries an open judgment seam.
  Real teeth, but bigger -- it needs its OWN spec + adversarial review, and can
  only partially enforce (it can't judge "is this an align-first-class call?").

The implementation, whichever shape, goes through the SAME spec -> adversarial-review
discipline B1/I3 got, and is NEVER solo-merged (this is the highest-stakes code in
the repo -- a mis-encoded envelope silently widens what auto-approves). Recommended:
start with (a) to make the process durable, and only escalate to (b) if you want
structural enforcement.
