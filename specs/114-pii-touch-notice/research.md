# Research: Personal-Data-Touch Notice

Phase 0 -- decisions that resolve the plan's design choices. No NEEDS
CLARIFICATION remained in the spec after `/speckit-clarify`; the open items were
the OUTPUT VEHICLE and the FR-011 ENFORCEMENT MECHANISM, resolved here.

## D1 -- Output vehicle: Python composer, not skill-only

**Decision**: Implement as a Python composer (`src/retail/pii_notice.py`) plus a
CLI verb, NOT as a skill-only prose composer like F040.

**Rationale**: The kit has two established read-only-composer patterns:
- Skill-only (agent is the runtime): F040 consumer-data-dictionary,
  answerability-summary, dq-signal-interpretation -- `templates/` + a skill, no
  Python. Their verbatim-cite discipline is PROSE-enforced (skill instructions +
  a `git status` composes-only proof); there is no machine check.
- Python runtime: `approval_inbox.py`, `blocker_explainer.py`, `evidence_pack.py`
  -- `src/retail/*.py` + `cli/commands/*.py`, unit-tested.

FR-011 requires a MECHANICALLY-ENFORCEABLE guarantee (content 100% derived from
named committed fields). That is exactly the property the verification panel
named as this feature's edge over the Approver Decision Surface ("single
mechanically-enforceable echo-vs-rule seam"). A skill-only vehicle cannot
self-enforce a lint, so mirroring F040's VEHICLE would silently downgrade FR-011
to F040's prose posture and make the spec internally inconsistent. A small
deterministic Python composer over one YAML file, paired with unit tests, makes
FR-011 (and SC-002/003/005/006) checkable for free.

**Alternatives considered**:
- *Skill-only, mirroring F040* -- rejected: deletes FR-011's mechanical
  guarantee (the feature's differentiator) and contradicts the spec.
- *Skill + a separate committed verifier script* -- viable, but strictly more
  moving parts than a Python composer whose tests ARE the verifier; kept as the
  fallback if the owner prefers no new runtime module.

## D2 -- Enforcement: a decoupled unit-test verifier, NOT a gating retail check rule

**Decision**: Enforce FR-011 with a committed unit-test VERIFIER that, given any
notice + its source-map, asserts every disposition sentence is a verbatim
substring of a committed source-map field and every `pii: true` column is present
and classified. This verifier is TEST-only; it is NOT a `@register` `retail check`
rule.

**Rationale**: FR-007 forbids adding a gating `retail check` rule (the notice is
an optional companion that must never block a stage). A gating rule would
self-contradict the spec. The mechanical guarantee lives in the test suite:
composition and verification are DECOUPLED (composer writes; tests prove). This
keeps the guarantee real without introducing a gate.

**Alternatives considered**:
- *A `@register` retail check rule* -- rejected: violates FR-007 (adds a gate),
  and would change the shipped rule count / manifest (out of scope, and a
  land-on-main hazard per the kit's rule-count lockstep).
- *No enforcement, prose only (F040 posture)* -- rejected unless the owner
  consciously downgrades FR-011; flagged for the ratify ledger as the one option
  that hollows out the spec.

## D3 -- Disposition source and parsing (Clarification Q1, confirmed against fixture)

**Decision**: Read only `mappings/<table>/source-map.yaml`. Per column: `pii`,
`decision`, and the disposition. A KEPT PII column's disposition is in the
`defaults.deviations[]` block (RC4-style) whose `reason` carries the governance
string. A DROPPED PII column's disposition is its own `reason`.
`unresolved-questions.md` is NOT parsed (only cited via the RC4 `detail_in`
pointer).

**RULED (ratify OPEN-2, 2026-07-09 -- explicit `deviation_ref`):** a kept-PII
column names its governing deviation via a NEW structured `deviation_ref: <id>`
field, joined by EXACT id-match to `defaults.deviations[].id`. The matched
deviation's `reason` is the authoritative disposition text. No text heuristic; a
column with no (or an unmatched) `deviation_ref` is `undecided` (GAP), never a
guess. Implementation ADDS `deviation_ref` to `templates/source-map.yaml`
(generic, Principle VII) and back-fills the fixture (`customer_id` gains
`deviation_ref: RC4`). V7 asserts rendered-disposition-deviation-id ==
`deviation_ref`.

**Rationale**: Grounded in the committed fixture -- `retail_store_sales/
source-map.yaml` records `customer_id` as `pii: true`, `decision: keep`, with the
disposition "Q1 RESOLVED 2026-06-25 (data owner): keep, no raw PII" in the RC4
deviation block (line 44-46), cross-referenced to `unresolved-questions.md` via
`detail_in`. Single-file sourcing removes the cross-file reconciliation path;
FR-010 reduces to an INTRA-file consistency check.

**Alternatives considered**:
- *Also parse `unresolved-questions.md`* -- rejected in Q1: prose file, harder to
  echo verbatim reliably, and adds a cross-file disagreement code path.

## D4 -- "Undecided" definition (the safety-critical trigger)

**Decision**: A `pii: true` column is UNDECIDED (-> GAP) exactly when
`source-map.yaml` records no disposition string reachable for it -- i.e. neither a
column-level disposition nor a joinable `defaults.deviations` entry carries a
governance decision for that column. `decision: keep` alone is NOT a disposition
(keeping a column is a mapping choice; the PII governance decision is the RC4
disposition). An undecided PII column MUST render as GAP and MUST NOT be omitted
or phrased as cleared (FR-004, SC-003).

**Rationale**: This is the Principle-V hazard the whole feature guards. Making
"undecided" mean "no reachable disposition string" (not merely "kept") prevents a
kept-but-ungoverned PII column from reading as cleared. The `customer_id` fixture
is DECIDED (its RC4 disposition exists); a fixture that strips the RC4 block for a
`pii:true` column is the UNDECIDED test case.

## D5 -- YAML reader and repo idioms

**Decision**: Reuse the shipped idiom from `blocker_explainer.py`:
`yaml.safe_load(path.read_text(encoding="utf-8-sig"))` behind a private loader
returning `None` on any `OSError`/`UnicodeDecodeError`/`YAMLError`; a module-level
`build_pii_notice(repo_root, table)` returning a dict result with a
`read_only_proof: True` marker; a thin CLI handler with `_render_text` + a
`--format json` option, returning `0`. `yaml` is already a runtime dependency of
these shipped surfaces (no new dependency).

**Rationale**: Consistency with the surrounding read-only surfaces (PR #229) and
the CLAUDE.md "write code that reads like the surrounding code" rule. The
`utf-8-sig` read tolerates a BOM on input while output stays UTF-8 no BOM.

**Alternatives considered**:
- *A bespoke YAML parse* -- rejected: needless divergence from the shipped idiom.
