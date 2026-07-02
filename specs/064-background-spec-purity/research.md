# Phase 0 Research: Background-Spec Forbidden-Dynamic-Content Assertion Rule

## Decision 1 -- Reuse the DL1 (design_theme.py) structural pattern

**Decision**: Model the rule directly on the shipped surface-3 theme-JSON purity
rule (`src/retail/rules/design_theme.py`, DL1, spec 060).

**Rationale**: DL1 is the near-exact structural precedent for a design-surface
static lint: generic suffix-based discovery via `ctx.tracked_files`,
`is_test_path()` exemption, a categorical present/absent check (never free-text
value guessing), one `Finding` per violation with a `file#/pointer` locator, an
unparseable file surfaced as a Finding (never a crash or silent pass), and a
single `@register(RULE_ID, ...)` decorator. Reusing it keeps the design-lint
family consistent and minimizes novel surface area.

**Alternatives considered**: Writing a bespoke rule shape -- rejected; it would
diverge from the established design-lint precedent for no benefit.

## Decision 2 -- Lazy in-function `import yaml` (stdlib-only module scope)

**Decision**: Parse the filled specs with a function-local `import yaml` inside
the check function, never at module scope.

**Rationale**: PyYAML is a dev/optional dependency and is NOT part of the
never-execute static check core. The existing YAML-reading rules
(`assumptions.py`, `parked_on.py`, `readiness_status.py`) all lazy-import yaml
inside the check function with the comment "keep the retail-check core stdlib-only
at module scope (B1/B3)". A8 reads YAML, so it MUST follow this exact pattern or
it breaks the B1/B3 never-execute / stdlib-core invariants. This is the single
material deviation from DL1 (which reads JSON via stdlib `json`).

**Alternatives considered**: Module-scope `import yaml` -- rejected; violates
B1/B3. Hand-rolling a YAML subset parser in stdlib -- rejected; unnecessary
complexity and fragility versus the sanctioned lazy-import pattern.

## Decision 3 -- Generic filled-spec discovery by a suffix convention

**Decision**: Discover committed filled background specs by a single generic
suffix convention (recommended default `*.background.yaml`), exempting
`templates/background-spec.yaml` (the blank template) and the test-fixture path.
The exact suffix literal is an OPEN owner-convention ruling (spec Clarifications);
it is represented as a single module-level constant seam.

**Rationale**: Principle VII requires generic discovery -- an enumerated or
tenant-specific path would silently miss new filled specs and couple the rule to
one tenant. DL1's fixed `.theme.json` suffix is the precedent. No committed
convention for FILLED background specs exists today, so the human owner must set
where every future page's background spec lives; the advisor recommends a
`*.background.yaml` suffix but does not freeze it (recorded OPEN). The template
itself must be exempt because its values are `<true|false>` placeholders, not real
booleans.

**Alternatives considered**: Enumerated path list -- rejected (Principle VII).
Scanning ALL `*.yaml` -- rejected; would sweep unrelated YAML (the template,
config, other specs) and produce false positives.

## Decision 4 -- Assert the DECLARED boolean contract, not key-name tokens

**Decision**: The rule asserts the template's OWN declared boolean contract:
`forbidden_dynamic_content` keys MUST parse to `false`; `qa_checklist` items MUST
parse to `true`, OR to `false` accompanied by a recorded reason string. It never
inspects an image binary, never renders, and never judges a reason's adequacy
(only its presence).

**Rationale**: This is the second material difference from DL1. DL1 flags business
meaning smuggled into key NAMES; A8 asserts the boolean VALUES the filled spec
declares. The template documents the contract verbatim ("Every check below MUST
be false to pass. A true entry is a defect" / "Each MUST be true to pass; a false
entry is a blocking reason or a recorded warning + reason"), so the rule keys onto
a declared boolean contract with no string-guessing.

**Alternatives considered**: Verifying the actual image against the declarations
-- rejected; requires opening/rendering an image binary (execution), out of scope
per Principle VIII (static-first) and Principle II (execution-only deferred).

## Decision 5 -- Boolean vocabulary frozen verbatim from the template

**Decision**: Freeze the asserted key set verbatim from
`templates/background-spec.yaml`: 7 `forbidden_dynamic_content` keys asserted
false, 9 `qa_checklist` items asserted true-or-reason (enumerated in spec
Clarifications Q2 and in [data-model.md](./data-model.md)).

**Rationale**: Deriving the vocabulary from the template's own declared contract
(not a tenant example) is the Principle-VII-clean reading and mirrors DL1's frozen
vocabulary. A future template key addition becomes a reviewed vocabulary change,
not silent drift.

**Alternatives considered**: Reading the key set dynamically from the template at
runtime -- rejected; that would let a template edit silently change what the rule
asserts, defeating the "reviewed vocabulary change" guarantee and coupling the
rule to a live file read of the template.

## Decision 6 -- Inert on an empty corpus (fail-safe latency)

**Decision**: With zero committed filled specs matching the discovery convention,
the rule emits zero findings and does not flag the absence of a filled spec.

**Rationale**: No filled background spec exists on disk today (only the blank
template). The idea explicitly assumes latent/inert value until content lands.
Flagging the absence would break the green build on day one for a rule that is by
design dormant.

**Alternatives considered**: Flag "no filled background spec exists" -- rejected;
turns a dormant rule into a spurious failure and is not the rule's job.

## Decision 7 -- ERROR severity, observed not declared

**Decision**: A declared violation (a true forbidden key, an un-reasoned false qa
item, a placeholder/non-boolean value in a discovered filled spec, an unparseable
file) is a `Severity.ERROR` finding. Severity is OBSERVED per branch from emitted
findings; no governed per-rule severity table is introduced (ratified 044).

**Rationale**: Matches the sibling DL1 posture and the template's own
"defect" / "blocking reason" wording. A declared baked-in KPI value is a
substantive defect the surface exists to prevent; advisory treatment would defeat
the rule.

**Alternatives considered**: WARNING -- rejected; downgrades the exact failure
mode the surface exists to prevent to a non-blocking note.

## Live-registry reconciliation note

The local worktree `EXPECTED_RULE_IDS` shows 41 ids (includes DL1); project
memory notes main was at 40 after the kraken merge. The TRUE registered set MUST
be reconciled at wiring time by importing `retail.rules` and calling
`registry.all_rules()` -- never a hardcoded count. The new rule id must be fresh
and non-colliding; a design-lint-namespaced id (the natural next in the DL family)
is preferred, finalized against the real live set at wiring time.
