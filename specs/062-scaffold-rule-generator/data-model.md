# Phase 1 Data Model: Scaffold-Rule Authoring Generator + Doctor

The helper is static tooling; its "data model" is a small set of in-memory value
objects plus the repo files it reads/writes. No database, no persistence beyond
the repo text.

## Entity: WiringPlace

One of the five locations a rule id must appear in to be fully wired. Modeled as
an explicit, immutable, in-code declaration (a constant list) that is guard-tested
against the real repo.

| Field         | Meaning                                                        |
|---------------|---------------------------------------------------------------|
| `key`         | Stable short key (e.g., `register`, `import_all`, `expected_ids`, `golden`, `glossary`) |
| `label`       | Human label for reports and printed output                    |
| `target`      | The repo file(s) the place lives in                           |
| `write_mode`  | `write` (scaffold may author it) or `print` (print-only)      |

The `golden` place spans two files (rule-inventory manifest + severity-posture
record); both are `print`-only.

**Guard invariant (FR-017)**: the set of declared `WiringPlace.key`s MUST equal
the set of wiring places the repo actually has; a guard test fails on mismatch.

## Entity: RuleIdentity

The author-supplied identity of a new rule. The helper writes boilerplate around
it and NEVER invents its meaning (DEC-1).

| Field    | Meaning                                             |
|----------|-----------------------------------------------------|
| `id`     | The new rule id (validated against the id shape)    |
| `title`  | The one-line rule title (non-empty)                 |

Validation happens at the boundary (FR-010): a malformed id or empty title is
rejected before anything is written.

## Entity: ScaffoldResult

The outcome of a scaffold (author) run. Enforces the write/print split.

| Field            | Meaning                                                    |
|------------------|------------------------------------------------------------|
| `written[]`      | Files actually written: stub module, test stub, expected-id insertion |
| `printed[]`      | Instructions printed, not applied: two regen commands, one glossary row |
| `refused`        | Set (with reason) when the id is already registered / would overwrite (FR-009) |

Invariant: `written[]` NEVER contains a golden record file or the glossary file
(SC-004). If `refused` is set, `written[]` is empty (no partial writes).

## Entity: DoctorReport

The read-only output of Doctor mode.

| Field         | Meaning                                                       |
|---------------|---------------------------------------------------------------|
| `entries[]`   | One per checked rule id                                        |
| entry.`id`    | The rule id                                                    |
| entry.`places`| Map of `WiringPlace.key` -> `present` \| `missing` \| `unverifiable` |
| `has_drift`   | True if any checked id is `missing` in any place              |

- `unverifiable` is used when a place cannot be read (e.g., a golden record file
  is absent) rather than crashing (FR-015).
- `has_drift` drives Doctor's exit code (FR-014): non-zero when true.
- Doctor produces this by READING only; it holds no write capability.

## Repo files touched

| File                                   | Role in this feature | Access |
|----------------------------------------|----------------------|--------|
| `src/retail/scaffold.py`               | The helper (new)     | -      |
| `src/retail/cli.py`                    | Subcommand wiring    | write (this feature) |
| `src/retail/registry.py`               | register/all_rules   | read   |
| `src/retail/rules/__init__.py`         | place #2             | read (doctor); scaffold may write the new stub module file, PRINTS the import/__all__ edit |
| `tests/unit/test_rules_wiring.py`      | place #3             | write (id insertion) / read (doctor) |
| `docs/rules/rules-manifest.json`       | place #4a            | read only (doctor); PRINT regen cmd |
| `docs/rules/severity-posture.json`     | place #4b            | read only (doctor); PRINT regen cmd |
| `docs/glossary.md`                     | place #5             | read only (doctor); PRINT row -- NEVER written |
| `tests/unit/test_scaffold.py`          | tests (new)          | -      |

The write/print asymmetry in this table is the feature's load-bearing boundary.
