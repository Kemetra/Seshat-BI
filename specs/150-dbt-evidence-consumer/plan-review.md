# Adversarial plan review: dbt evidence governance consumer

**Posture**: default-refuted. Each claim had to survive an attempt to disprove
it with repository evidence.

## Round 1 -- against the original evidence-pack design

### CONFIRMED PROBLEM: the new pack section would crash two live consumers

The plan claimed a new section was additive with no blast radius. Refuted, and
the refutation was then verified directly rather than accepted secondhand:

| Site | Code | Effect on the proposed shape |
| --- | --- | --- |
| `src/seshat/cli/commands/evidence_pack.py:21` | `f"{section['id']} {section['name']}: {section['status']}"` | `KeyError` -- the proposed section had `state`, not `status` |
| `src/seshat/evidence_pack.py:262` | `section["sources"][0] if section["sources"] else None` | `KeyError` -- the proposed section had no `sources` key |
| `tests/unit/test_evidence_pack.py:77` | pins `[section["id"] ...] == ["01".."10"]` | fails immediately |
| `docs/tools/evidence-pack-generator.md:79` | "The 10-section contract (fixed, ordered)" | a documented invariant the plan never engaged |

`docs/capabilities/capabilities.yaml:777` and `src/seshat/cli/parser_core.py:252`
restate the 10-section language, so the contract is asserted in three places.

**Verdict**: the plan's own first validation command would have failed. The
"reader-only, no blast radius" framing was false. Appending a differently-shaped
item to a list that consumers iterate and index is not additive.

**Resolution**: the evidence-pack section was dropped, not patched. Making the
section conform to the existing six-key shape was rejected because the shape's
only status values are `pass`/`blocked`, which would force a failed dbt build to
render in the readiness-shaped vocabulary that spec FR-006 forbids. Amending the
10-section contract was rejected for this spec because it converts a reader-only
change into an amendment of a documented governance contract, which deserves its
own review rather than being carried in as a side effect.

## Round 1 -- claims that survived

### CANNOT REFUTE: "no governance surface reads `dbt-evidence/`"

Exhaustive sweep across `src/`, `skills/`, `distribution/`, `docs/`, `scripts/`,
`orchestration/`, and `integrations/` found only the writer
(`src/seshat/dbt/evidence.py:760`) and the deleter (`src/seshat/reset.py`).
`agent_next`'s portfolio scan globs `mappings/*/readiness-status.yaml` only,
never `dbt-evidence/`. The premise holds.

### CANNOT REFUTE: moving the outcome mapping is safe

`orchestration/dagster/pyproject.toml` already declares a runtime dependency on
the root `seshat-bi[dbt]` package, and `dbt_build.py` already imports
`seshat.cli.commands.dbt` and `seshat.dagster_adapter.redaction`. `src/seshat`
imports nothing from `tower_bi_orchestration`. No cycle, no new boundary
crossing; the move corrects an existing backwards private-symbol dependency.

### CANNOT REFUTE: truth separation holds at the call-graph level

`GovernorService._evidence_pack()` passes the pack through opaquely. The only
approval-producing operation, `_approval_request()`, calls
`build_approval_inbox()` and never `build_evidence_pack()`. No caller feeds
evidence-pack output into a readiness or approval decision.

### No rule violation found

No registered `seshat check` rule targets evidence-pack section shape or public
constants. The 10-section contract is enforced by documentation and one pinned
test, not by a rule -- which is precisely why the adversarial pass, not the
static gate, was what caught it.

## Round 2 -- independent adversarial pass against the revised design

Run as a genuine independent pass, not self-review. Round 1 had already proven
self-review's miss rate on this spec.

### CONFIRMED PROBLEM: the caveat could SOFTEN an existing stop

The most serious finding in either round, and it runs OPPOSITE to the risk the
spec was written to guard against. The spec protected against execution success
*granting* readiness. The real exposure was execution evidence *weakening* a
stop.

Verified directly at `src/seshat/agent_next.py:855-892`:

```python
next_override  = live_override or contract_override          # 860
control_outcome = "next_action" if next_override is not None else outcome  # 862
action = next_override or _next_allowed_action(response)     # 871
...
"next_allowed_action": action,        # 877  <- REPLACED, not appended
"stop_point": _stop_point(control_response),  # 880 <- reads control_outcome
"caveats": list(response.get("caveats", [])), # 889 <- the additive channel
```

If the dbt caveat had joined the `next_override` chain, then for a table whose
`outcome` is `stop_blocked`:

- `action` -- the blocked table's `"STOP -- stage ... is blocked; resolve the
  recorded blocking_reasons ..."` sentence would be **displaced** by the dbt
  `CAUTION --` text.
- `control_outcome` would flip to `"next_action"`, so `_stop_point` skips its
  `stop_blocked` branch and falls through to the generic per-stage sentence.
- FR-017's non-STOP mandate would then defeat `_is_stopped()`'s third signal
  (`action.startswith("STOP")`), compounding the loss.

Two of five surfaced fields would still be protected, because `_is_stopped()` is
passed the RAW `response` and `outcome` is emitted verbatim at line 887. But
`next_allowed_action` and `stop_point` -- the two fields a human or agent is
most likely to read and act on -- are not behind that gate.

**Why this was newly dangerous rather than pre-existing**: the two existing
overrides are gated to `terminal_pass or post_gold_stage`
(`_live_validation_next_override:618`, `_contract_next_override:589`), so
neither can fire on a blocked table today. FR-002 gated the dbt caveat on
nothing, which would have widened a currently-unreachable hole to every stage.

**Zero existing test would have caught it.** No fixture in
`tests/unit/test_agent_next.py` pairs a `stop_blocked` or `approval_required`
table with any winning override; all `next_allowed_action` assertions are
`startswith`/substring, never exact-match.

**Resolution**: FR-019 makes the dbt signal additive-only -- it appends to the
existing `caveats` list and never joins the `next_override` chain. FR-020 states
the guarantee as a testable property. FR-001 was corrected: it had pointed at
`_live_validation_next_override()`, a REPLACEMENT function, as the model to
mirror -- which is what steered toward the unsafe design. Task T005a tests it by
whole-document diff.

### CONFIRMED: the classifier's proposed home is a hotspot

`src/seshat/portfolio_watch.py` is 1227 lines, already ~1.5x the ~800-line
convention this repository cites when deciding to split files. No CI rule
enforces it today, so it is a hygiene risk rather than a build breaker.

**Resolution**: FR-021 places the classifier in a new sibling module.

### CONFIRMED, accepted: an MCP consumer sees two fields of differing strength

`governor/service.py:144-159` derives its `outcome` from the document's raw
`outcome`, so its blocked verdict is immune to softening. It also emits
`next_action` verbatim. Under FR-019 these can no longer disagree, because the
action string is never overwritten by the dbt signal.

### CANNOT REFUTE: no exact-literal test breaks

All `next_allowed_action` assertions use `startswith` or substring containment.
A new additive caveat entry breaks none of them.

### Constraint found and folded in: the `STOP` prefix is load-bearing

`agent_next._is_stopped()` (`src/seshat/agent_next.py:812-816`) returns true
when the emitted action string begins with `STOP`, suppressing all downstream
guidance. Its docstring records a past defect in which dbt install/init/doctor
steps rendered directly beneath a STOP. A dbt caveat that begins with `STOP`
would therefore silently suppress unrelated guidance.

**Resolution**: spec FR-017 requires a non-STOP prefix for informational
caveats, mirroring the existing `CAUTION --` wording, and task T005 tests the
property against `_is_stopped()` itself rather than a restatement of its rule.

### Constraint found and folded in: override precedence

`next_override = live_override or contract_override`
(`src/seshat/agent_next.py:858-860`) is an existing, deliberate ordering.

**Resolution**: spec FR-018 forbids reordering it.

### Reuse found: the state vocabulary already exists

`portfolio_watch.py:107` already defines `STATE_UNREADABLE = "unreadable"`.

**Resolution**: the classifier reuses it rather than declaring a second spelling
of the same state.

## Residual risks accepted

- **The reviewer-facing gap remains.** A human reading an evidence pack still
  cannot see a dbt build. This is a deliberate deferral, recorded in Out of
  Scope, not an oversight.
- **`blocked` appears in two vocabularies.** It is both an execution state and a
  readiness four-status token. Mitigated structurally: the classifier never
  opens `readiness-status.yaml` and never writes a stage `status` key, so the
  word cannot arrive where a stage verdict is read.
- **dbt activation remains `blocked`.** The reader's contract is over the
  record, not over a live run, so it is testable today; but no live end-to-end
  proof exists until activation clears.

## Verdict

The plan is **implementable as specified after two rounds**, contingent on human
ratification.

Neither round was cosmetic. Round 1 refuted the evidence-pack design outright
(it would have crashed two consumers and failed its own first validation
command). Round 2 refuted the composition of the replacement design (it would
have softened a blocked table's STOP with no test to catch it). Both defects
were found by an independent adversarial pass and missed by self-review, which
is the reason the gate exists.
