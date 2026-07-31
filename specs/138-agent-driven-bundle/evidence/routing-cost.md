# T004/T005 — routing-cost measurement and baseline

**Captured**: 2026-07-31 | **HEAD**: `258cb8e` | **Tool**:
`scripts/measure_bundle_routing_cost.py` | **Spec**: FR-021a, SC-010, research R5

## Method

The routing cost is the material an agent must hold merely to **know which skills
exist** — each shipped skill's `name` and `description` frontmatter — before it
invokes any of them. Skill bodies are excluded by design: they load on demand
(FR-021b), so body size is not a per-session cost.

Exact figures are characters and bytes. `tokens_approx = chars // 4` uses one
fixed divisor so successive runs stay comparable; the ceiling governs the
**trend**, and the divisor must never change between runs.

This is a **size**, not a score. Nothing derives a confidence, health, maturity or
completeness value from it (hard rule #9).

## Baseline (11 skills, as shipped today)

| Harness | Skills | Chars | Bytes | tokens_approx |
|---|---:|---:|---:|---:|
| claude | 11 | 2,317 | 2,317 | 579 |
| codex | 11 | 2,317 | 2,317 | 579 |

Identical across harnesses, as FR-009 requires.

## Projection

| Stage | Skills | Chars | tokens_approx | Growth |
|---|---:|---:|---:|---:|
| today | 11 | 2,317 | 579 | — |
| after US3 (+10 compass verbs) | 21 | 8,899 | 2,224 | 3.8× |
| after US4 (+22 consumer skills) | 43 | 29,014 | 7,253 | **12.5×** |

## The finding that matters

**The skills queued to ship have descriptions roughly four times longer than the
ones already shipping.** Currently-bundled skills average **211** chars of
routing metadata; the 32 candidates average **834** (median 845). Every one of
the 32 exceeds 400 chars — the concentration is total, not driven by a few
outliers.

Top contributors:

| Chars | Story | Skill |
|---:|---|---|
| 1,218 | US4 | approval-evidence-pack |
| 1,195 | US4 | consumer-data-dictionary |
| 1,161 | US4 | run-next-readiness |
| 1,148 | US4 | cross-table-lineage |
| 1,109 | US4 | capabilities |
| 1,099 | US4 | retail-scaffold |
| 1,042 | US4 | approval-console |

The cause is legible: these descriptions were written to disambiguate among **50**
skills inside a development repository, where heavy qualification earns its
keep. The bundle's existing descriptions were written for a set of eleven.

**This is exactly why the Q2 clarification chose "measure, then decide."** A 12.5×
growth is not what "bodies load on demand, so it's only descriptions" intuitively
suggests, and it would not have been caught by shipping first.

## T006 — the ceiling is an owner decision

FR-021a requires a reviewed ceiling, and states that splitting the distribution
"MUST NOT be undertaken unless a recorded measurement shows the ceiling cannot
otherwise be met." That measurement now exists, so the decision is informed.

| Option | Ceiling | Effect | Cost |
|---|---|---|---|
| **A — accept** | ~8,000 tokens | Ship all 43; ~7.3k tokens resident per session | None. Largest per-session cost. |
| **B — trim descriptions** | ~2,500 tokens | Rewrite 32 canonical descriptions toward the bundle's existing ~211-char norm | Touches canonical source; **risks degrading routing accuracy in this 50-skill development repository**, where the verbosity currently earns its keep. |
| **C — split core + extended** | ~2,500 core | Core plugin (verbs + knowledge), extended plugin (analysis, dashboard, lineage, dictionary) | A permanent second distribution surface and a version-pairing problem between them. |

**Recommendation: A, with B applied selectively to the seven skills over 1,000
chars.** That lands near ~6,000 tokens without a distribution split and without
rewriting descriptions whose length is doing real disambiguation work. Option C
stays available and now has the measurement FR-021a demanded, should the owner
weigh the session cost more heavily.

## T006 — RULED

**Ceiling: 6,000 `tokens_approx` per bundle.** Option **A+** — accept the
43-skill set, and trim the seven descriptions exceeding 1,000 chars toward the
bundle's existing norm.

- **ruled_by**: Ahmed Shaaban (owner)
- **ruled_on**: 2026-07-31
- **recorded_by**: the agent transcribed an owner-directed ruling; it did not
  self-grant (Principle V).

**Rationale as ruled**: avoid a second distribution surface, and avoid rewriting
descriptions whose length is doing real disambiguation work among 50
development-repo skills. Trimming only the seven largest recovers most of the
excess at the least risk to routing accuracy.

**The seven in scope** (US4): `approval-evidence-pack` (1,218),
`consumer-data-dictionary` (1,195), `run-next-readiness` (1,161),
`cross-table-lineage` (1,148), `capabilities` (1,109), `retail-scaffold` (1,099),
`approval-console` (1,042). Together **7,972** chars.

**How far the trim must go, arithmetically:**

| Trim target | Seven become | Recovered | Projected total | tokens_approx | Meets 6,000? |
|---|---:|---:|---:|---:|---|
| to the 845-char median | 5,915 | 2,057 | 26,957 | 6,739 | **no** |
| to ~600 chars | 4,200 | 3,772 | 25,242 | 6,310 | **no** |
| to the ~211-char bundle norm | 1,477 | 6,495 | 22,519 | **5,629** | **yes** |

So trimming the seven to the **existing bundle norm** meets the ceiling with
~370 tokens of headroom; trimming merely to the median does not. If the seven
cannot be cut that far without losing disambiguation, the shortfall must be made
up from the next tier rather than by raising the ceiling.

The measurement at T064 is authoritative; the ceiling is the constraint, and this
table is the plan for meeting it.

**Option C remains available and now has its measurement**, should the ceiling
prove unmeetable at T064. It is not authorised here.

**Status: T006 CLOSED.** Payload stories may proceed to their measurement
checkpoints against the 6,000 ceiling.
