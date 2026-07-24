# Phase C verification record (spec 021, T017)

Phase C = the read-only `seshat narrative-check` verb (US3). This records the
Success-Criteria walk required by T017. Phase B (US2, the dashboard-design
gate + three-way binding map) is deliberately NOT built here (owner-gated: it
arms enforced behavior off a still-Draft spec).

## What shipped in Phase C

- `src/seshat/narrative_check.py` — read-only checker for
  `mappings/<table>/narrative-brief.md` against the FROZEN
  `seshat.narrative-brief/v1` schema (derivation-route.md). NamedTuple findings,
  fail-closed on missing/malformed input, worst-first status rollup
  (`pass`/`blocked`), `grants_approval` structurally always False.
- `seshat narrative-check --table <t> [--report DIR] --format {text,json}` —
  wired via the house three-touch pattern (parser fn + call + lazy dispatch).
- `tests/unit/test_narrative_check.py` + `test_narrative_check_cli.py` — the
  three SC-003 outcome classes.

## Scope boundary (honest seam)

The checker validates the BRIEF only. The visual<->question binding-map orphan
checks (orphan visual, page-missing-question) require the three-way map authored
by Phase B / T010, which does not exist yet. Those two fixtures are visible
`@pytest.mark.skip` in the test file — never a silent pass over an absent map.
Brief-absence is fail-closed input (FR-008); binding-map absence is out of this
verb's scope, not fail-closed.

## Success Criteria

- **SC-001 (grounded cites)** — VERIFIED. The checker's grounded-only rule
  (`ungrounded_cite`) rejects any cite not among the declared contracts or the
  committed profile's dimensions; the clean-brief fixture and the worked-example
  walk both cite only grounded ids.
- **SC-002 (zero orphan visuals / zero bare-total headlines on the worked
  example)** — VERIFIED end to end. The full brief the shipped
  `example-specialty-retail.md` teaches (flow-style YAML, all Q1-Q7, a real
  [GAP], guardrail-bearing framings, named overview comparisons) passes the
  checker with `status: pass`, `grants_approval: False`. Confirms the pack's own
  canonical example passes its own checker (no skill/checker contradiction) and
  that flow-style YAML parses.
- **SC-003 (three outcome classes, no silent-nothing)** — VERIFIED by the test
  suite: clean -> `pass`/exit 0; each single mutation -> exactly its named
  finding/`blocked`/exit 1; missing/unreadable/malformed -> fail-closed
  `blocked` naming the problem. `test_never_silent_nothing` pins FR-008.
- **SC-004 (four #452 sub-gaps each have a named countermeasure)** — TRACED:

  | #452 sub-gap | Phase-A route countermeasure | Phase-C checker enforcement |
  |---|---|---|
  | 1. No decision-questions | derivation-route.md (decisions-not-metrics; grounded-only) | `ungrounded_cite` |
  | 2. No comparison framing | 8 framing-*.md cards + headline rule | `bare_total_headline`, `missing_guardrail_basis` |
  | 3. No story order | story-order.md (overview->change->why_where->action) | `story_order_incomplete`, `story_order_mismatch`, `empty_overview` |
  | 4. Not domain-specific | grounded in committed profile + domain packs; example-specialty-retail.md | grounding ties cites to the actual profile |

## Gate results (local)

- `ruff format --check` + `ruff check` on all new/edited files: clean.
- `seshat check` (static gate): exit 0 (pre-existing non-blocking RS1 warning
  only, unrelated to this change).
- Library + CLI tests: 24 passed, 2 skipped (Phase-B deferrals).
- Full `pytest -m unit` suite: <recorded at commit time>.
