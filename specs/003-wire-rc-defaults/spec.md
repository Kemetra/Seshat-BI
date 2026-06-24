# Feature Specification: Wire static ADR cleaning defaults into retail check (S5/S6/S7)

**Feature Branch**: `003-wire-rc-defaults` (work on `main` per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Wire the statically-checkable ADR 0002 cleaning defaults (RC7 type discipline, RC14 gold star structure, RC15 contiguous date dim) into `retail check` as new SQL-family rules S5/S6/S7. Each rule ENFORCES an RC default but keeps a checker-namespace id (S*), never adopts the RC id. The D-namespace was disambiguated in feature 002; this is the unblocked slice."

## Why this feature exists

ADR 0002 named these three defaults as **statically checkable from committed SQL** (compliance
matrix Sec 7). Until feature 002 the `D`-namespace collision blocked wiring any ADR default into
the checker. With cleaning defaults now `RC*` and checker rules `D/S/...`, the path is clear:
add SQL-family rules that parse `warehouse/**/*.sql` and enforce the RC defaults.

**Naming (settled, not open):** the new rules are **S5, S6, S7** -- the checker is keyed by
artifact domain (S = SQL), and these parse SQL. Each rule *cites* the RC default it enforces in
its title/message; it MUST NOT adopt the `RC` id (that would reintroduce the collision in
reverse). Policy says *what* (RC*), the checker rule is the *enforcement* (S*).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The checker enforces type discipline (RC7) (Priority: P1)

A migration that casts money to float, or a leading-zero id to int, is caught at `retail check`
time instead of corrupting data silently.

**Why this priority**: RC7 has the one *irreversible* failure mode (an int-cast leading-zero id
loses data permanently), so it is the highest-value static check of the three.

**Independent Test**: Run S5 over a fixture migration that casts a money column to `float8` (and
an id column to `int`); assert it flags them. Run over C086's committed migration; assert clean.

**Acceptance Scenarios**:

1. **Given** a silver migration casting `amount` to `float`/`double precision`/`real`, **When**
   S5 runs, **Then** it WARNs "money/quantity cast to float; use exact NUMERIC (enforces RC7)".
2. **Given** a migration casting an id-like column (`*_id`, `*_no`) to `int`/`integer`/`bigint`,
   **When** S5 runs, **Then** it WARNs "id cast to integer may corrupt leading zeros (RC7)".
   *(Ordinal line numbers are an accepted false-positive; the warning prompts review.)*
3. **Given** C086's committed `0001_*`/`0002_*`, **When** S5 runs, **Then** zero S5 findings.

### User Story 2 - The checker enforces gold star structure (RC14) (Priority: P2)

Each `gold.dim_*` should carry a `-1` unknown member and the fact's FKs should COALESCE to -1.

**Why this priority**: structural integrity of the star; statically *partial* (the matrix says so)
-- provable enough to catch an omitted `-1` member, not a full guarantee.

**Independent Test**: Run S6 over a fixture with a `gold.dim_x` that has no `-1` INSERT; assert it
flags it. Run over C086 (6 dims, all with `-1`); assert clean.

**Acceptance Scenarios**:

1. **Given** a `CREATE TABLE gold.dim_x` with no matching `INSERT INTO gold.dim_x ... -1`,
   **When** S6 runs, **Then** it WARNs "gold.dim_x has no -1 unknown member (enforces RC14)".
2. **Given** C086's gold migration (every dim has a `-1` member insert), **When** S6 runs,
   **Then** zero S6 findings.
3. **Given** a `gold.dim_date` (which legitimately may model unknown differently), **When** S6
   runs, **Then** the rule's scope is documented and consistent (it still checks for `-1`; C086's
   dim_date HAS one, so this stays clean).

### User Story 3 - The checker enforces the contiguous date dim (RC15) (Priority: P3)

A `dim_date` built from `SELECT DISTINCT <date>` (gappy) instead of `generate_series` (contiguous)
is caught.

**Why this priority**: lowest-frequency mistake, but a clean line-level pattern check.

**Independent Test**: Run S7 over a fixture building `dim_date` via `SELECT DISTINCT sale_date`;
assert it flags it. Run over C086 (`generate_series`); assert clean.

**Acceptance Scenarios**:

1. **Given** a `dim_date` populated from `SELECT DISTINCT ... date`, **When** S7 runs, **Then** it
   WARNs "dim_date built from SELECT DISTINCT; use a contiguous generate_series calendar (RC15)".
2. **Given** C086's `dim_date` from `generate_series`, **When** S7 runs, **Then** zero S7 findings.

### Edge Cases

- Tokens in comments / string literals MUST NOT trigger any rule (use the `tokenize_sql` lexer,
  which drops them) -- e.g. a comment "-- do not cast to float" must not fire S5.
- `tests/` fixtures are exempt from the live scan (via `is_test_path`), same as other file rules.
- A dim with a genuinely-different unknown convention: S6 stays a WARNING (reviewable), never ERROR.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add three SQL-family rules in `src/retail/rules/sql.py`: **S5** (enforces RC7), **S6**
  (enforces RC14), **S7** (enforces RC15). Each registered via `@register("S<n>", "<title citing RC>")`.
- **FR-002**: Each rule MUST scan only `iter_sql_files(ctx)` (tracked `warehouse/**/*.sql`), MUST
  use the `tokenize_sql` lexer (no raw line-regex that would match comments/strings), and MUST
  emit `Finding(rule_id, severity, message, locator=f"{rel}:{line}")`.
- **FR-003**: Severity is **WARNING** by default (every RC default has an "override when" clause ->
  surface for review, do not block). S5's leading-zero-id-to-int case MAY be **ERROR** only if no
  legitimate override exists; default WARNING is acceptable and preferred for v1.
- **FR-004**: Rules MUST NOT adopt the `RC` id; the rule id stays in the `S` family. The RC default
  is named in the title and message text only.
- **FR-005**: `retail check` MUST still **exit 0 on the current repo** -- C086's committed
  migrations satisfy the RC defaults, so correctly-scoped S5/S6/S7 produce zero findings on them.
  A finding on the existing gold migration means the rule is mis-scoped (RED signal).
- **FR-006**: Tests MUST be written first (TDD), use `tmp_path` fixtures (never the real tree), and
  cover pass + fail + the comment/string false-positive guard for each rule.
- **FR-007**: The rule count rises 23 -> **26**. Update the "23 rules" / id-list references in the
  constitution (Principle VIII), architecture doc, and governance spec; amend the constitution
  **v1.2.0 -> v1.3.0** (MINOR: new supporting rules, no principle redefined).
- **FR-008**: No change to existing rules (S1-S4b, D*, R1, C*, G*, P*) or their ids.

### Key Entities

- **S5/S6/S7 (checker rules)**: SQL-family static rules; ids in the checker namespace; each enforces
  one ADR `RC` default. Live in `src/retail/rules/sql.py`.
- **RC7/RC14/RC15 (ADR defaults)**: the policy each rule enforces; owned by ADR 0002, cited not adopted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `retail check` reports **26 rules** including S5, S6, S7, with all prior ids unchanged.
- **SC-002**: On the current repo, `retail check` **exits 0** (zero new findings on C086's migrations).
- **SC-003**: The unit suite grows from 187 to **187 + new S5/S6/S7 tests, all green**; each rule has
  pass + fail + lexer-false-positive coverage.
- **SC-004**: A fixture casting money->float / id->int triggers S5; a dim missing `-1` triggers S6;
  a `SELECT DISTINCT` date dim triggers S7 -- each WARNING, each naming its RC default.
- **SC-005**: Constitution at **v1.3.0**; "23 rules" -> "26 rules" everywhere it appears; Principle
  VIII id-list includes S5/S6/S7.
- **SC-006**: No diff to existing rule logic; `git diff` on `src/retail/rules/{dax,git_meta,pbir}.py`
  is empty (only `sql.py` and tests change, plus docs).

## Assumptions

- These three RC defaults are the statically-checkable set named in the compliance matrix Sec 7;
  the live ones (RC2 PK, RC16 reconciliation, RC15 coverage) remain the deferred `retail validate`
  surface, out of scope here.
- WARNING severity matches the ADR's "override when" modality; ERROR is reserved for irreversible
  cases and not required for v1.
- S6 (RC14) is acknowledged **partial/static** (per the matrix) -- it proves presence of a `-1`
  member + COALESCE pattern, not full referential correctness (that's the live surface).
- Work on `main`; constitution amendment in scope (the count + id-list live there).

## See also

- Owning policy: `docs/decisions/0002-retail-cleaning-defaults.md` (RC7, RC14, RC15).
- Which defaults are static vs live: `docs/c086-adr0002-compliance.md` Sec 7/8; worked example Sec 7/8.
- Checker contract + family: `src/retail/core.py`, `src/retail/rules/sql.py` (S1-S4b), `src/retail/sql.py` (lexer).
- Constitution Principle VIII (the 23->26 count + id-list); architecture Sec 7 (validator categories).
