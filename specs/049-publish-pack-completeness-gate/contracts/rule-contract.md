# Rule Contract: Publish-pack completeness gate (PP1)

The checkable contract for the single static rule. Each item is directly testable
against synthetic generic handoff-pack source strings + a fake `RuleContext`. No
domain artifact appears in any fixture.

## Behavioral contract

- **C1 (placeholder unfilled -> flag)**: Given a committed instance pack with a
  required section whose resolution value still matches the `<...>` placeholder
  form, the rule emits exactly one Finding naming that pack and section.
- **C2 (GAP unfilled -> flag)**: Given a committed instance pack with a required
  section whose structured "Resolved?" cell is the literal token `GAP`, the rule
  emits exactly one Finding naming that pack and section. The GAP signal is read
  from the structured resolution position, NOT a free-text substring -- the word
  "gap" in a caveat sentence produces NO Finding (C2b).
- **C3 (missing section -> flag)**: Given a committed instance pack that omits a
  required-section heading/index row entirely, the rule emits a Finding naming the
  missing required section.
- **C4 (fully filled -> no Finding)**: Given a committed instance pack where every
  required section is present and resolved (no remaining placeholder, no `GAP`), the
  rule emits NO Finding for that pack.
- **C5 (template + fixtures excluded)**: The generic template
  `templates/handoff/bi-handoff-pack.md` and any committed pack under `tests/`
  produce NO Finding (the include filter selects only `mappings/*/handoff/...`; the
  `is_test_path()` exemption skips fixtures).
- **C6 (empty tree -> no Finding)**: On a tracked-file set containing no
  `mappings/<table>/handoff/bi-handoff-pack.md`, the rule emits no Finding (silent
  pass).
- **C7 (unreadable pack -> fail loud)**: A selected pack that cannot be read emits a
  Finding (fail loud) rather than crashing the gate or silently passing.
- **C8 (Principle V boundary)**: The publish-approval check asserts only
  presence-and-non-placeholder of the approval slot. No code path reads the
  approving owner, the date, or the sign-off legitimacy, and no code path writes any
  approval. (Verified by inspection + a test asserting a filled approval slot
  produces no approval-slot Finding without inspecting its contents.)
- **C9 (genuinely wired)**: The live registry id set, the regenerated
  `docs/rules/rules-manifest.json`, and `EXPECTED_RULE_IDS` agree exactly after the
  rule is added; AND at least one test invokes the rule directly on a known-bad
  fixture and observes a non-empty Finding set (closes the wiring-latent-gap).
- **C10 (generic / no domain artifact)**: The rule, its required-section-set
  constant, and every fixture reference only generic section labels and the
  placeholder/GAP convention -- no specific table, column, KPI, or PII rule; the
  c086 worked-example answers are never inlined.
- **C11 (uniform severity)**: Every Finding the rule emits carries the same
  severity. Recommended ERROR (proven-incomplete, fail-closed, matching G6/B1/B3);
  confirmed at the ratify gate. The rule adds no new `Severity` tier.

## Non-functional contract

- **C12 (static-only)**: The rule introduces no third-party dependency and performs
  no network or database access; it reads committed text via the existing
  `RuleContext`. Verified by running the static checker with psycopg2 / network
  absent.
- **C13 (no fork)**: The rule reuses the `G6` placeholder-detection mechanism (the
  `<...>` regex) rather than defining a second placeholder parser.
- **C14 (no production write)**: The rule modifies no committed handoff pack,
  template, or readiness file, and moves no readiness stage to pass.

## Ratify-gate confirmations (not settled by the workflow)

- Final required-section-set membership (recommended: the six index rows a-f at
  index granularity).
- Severity posture (recommended: ERROR).
- The readiness-stage assignment + roadmap provenance row (Principle V -- Open for
  human).
- The publish-safety boundary confirmation (Principle V -- Open for human; C8 is the
  asserted boundary the human ratifies).
