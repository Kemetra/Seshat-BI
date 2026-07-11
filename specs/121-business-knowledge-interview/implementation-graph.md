# Implementation Graph: Business Knowledge Interview, Decision Store, and Knowledge Contracts

**Feature**: `specs/121-business-knowledge-interview` | **Companion to**: [tasks.md](./tasks.md)

Task-level dependency DAG, serialized hotspots (same-file conflicts that forbid
parallelism), and safe parallel waves. Story colors: US2 decision store, US1
interview, US4 knowledge contracts, US5 gate verdicts, US3 review artifact.

## Task DAG

```mermaid
flowchart TD
    subgraph P1["Phase 1 - Setup"]
        T001["T001 contracts/README.md"]
        T002["T002 fixture roots"]
    end

    subgraph P2["Phase 2 - Foundational"]
        T003["T003 templates/semantic-decisions.yaml"]
        T004["T004 templates/kpi-contracts.yaml"]
        T005["T005 templates/cleaning-rules.yaml"]
        T006["T006 contracts/knowledge/approval-authority.yaml"]
        T007["T007 loader tests (failing)"]
        T008["T008 src/retail/decision_store.py loader"]
    end

    subgraph US2["Phase 3 - US2 Decision Store (P1)"]
        T009["T009 seed store fixtures"]
        T010["T010 DS1-DS4 rule tests (failing)"]
        T011["T011 DS1+DS2 rules"]
        T012["T012 DS3+DS4 rules"]
        T013["T013 registry snapshot + manifest"]
    end

    subgraph US1["Phase 4 - US1 Interview (P1)"]
        T014["T014 interview contract yaml"]
        T015["T015 interview verb SKILL.md"]
        T016["T016 kit-source + router regen"]
        T017["T017 PII scan + mask guards"]
    end

    subgraph US4["Phase 5 - US4 Knowledge Contracts (P2)"]
        T018["T018 database-to-pbip-flow.yaml"]
        T019["T019 dashboard-blueprint.yaml"]
        T020["T020 contract conformance tests"]
        T021["T021 knowledge-map routes"]
    end

    subgraph US5["Phase 6 - US5 Gate Verdicts (P3)"]
        T022["T022 verdict tests (failing)"]
        T023["T023 decision_gate.py projection"]
        T024["T024 readiness-spine projection"]
        T025["T025 DS5 rule + manifest regen"]
    end

    subgraph US3["Phase 7 - US3 Review Artifact (P2)"]
        T026["T026 review template"]
        T027["T027 determinism tests (failing)"]
        T028["T028 interview_review.py generator"]
    end

    subgraph P8["Phase 8 - Polish"]
        T029["T029 glossary"]
        T030["T030 quickstart walk"]
        T031["T031 full gate run"]
    end

    T001 --> T003 & T004 & T005 & T006
    T002 --> T009
    T003 & T004 & T005 --> T007
    T006 --> T007
    T007 --> T008

    T008 --> T009
    T009 --> T010 --> T011 --> T012 --> T013

    T008 --> T014
    T011 --> T015
    T014 --> T015 --> T016
    T008 --> T017

    T008 --> T018 & T019
    T018 & T019 --> T020
    T018 --> T021

    T013 --> T022
    T020 --> T022
    T022 --> T023 --> T024 --> T025

    T008 --> T026
    T025 --> T027
    T026 --> T027 --> T028

    T021 --> T029
    T028 --> T029 & T030
    T016 & T017 & T024 --> T030
    T029 & T030 --> T031
```

Edge rationale (non-obvious ones): `T011 -> T015` -- the interview verb instructs
approval recording, which must match the DS2 validity rules actually enforced;
`T013/T020 -> T022` -- verdict tests consume both the registered rule surface and the
per-stage blocking categories; `T025 -> T027` -- the review artifact embeds the gate
verdict (FR-025), so its tests need DS5-consistent verdict behavior.

## Serialized hotspots (same file -- never parallel)

| File | Tasks (in order) | Why serialized |
|---|---|---|
| `src/retail/rules/decision_store.py` | T011 -> T012 -> T025 | One rule module, three increments |
| `tests/unit/test_decision_store.py` | T007 -> T017 | Loader tests then mask-guard tests |
| `tests/unit/test_decision_store_rules.py` | T010 -> T025 | DS1-DS4 tests then DS5 extension |
| rule-registry snapshot + `docs/rules/rules-manifest.json` | T013 -> T025 | Manifest regenerated twice; second run must follow the first |
| `CLAUDE.md` router block + `.seshat/kit-source.yaml` | T016 only | Generated block -- single writer |
| `src/retail/decision_gate.py` | T023 -> T024 | Verdict core then spine projection |

## Parallel waves

| Wave | Tasks | Gate to enter |
|---|---|---|
| W0 | T001, T002 | -- |
| W1 | T003, T004, T005, T006 | W0 done |
| W2 | T007 | W1 done |
| W3 | T008 | T007 failing-red |
| W4 | T009, T014, T018, T019, T026 | T008 done (five files, four stories) |
| W5 | T010, T020 | T009 / T018+T019 done |
| W6 | T011 | T010 failing-red |
| W7 | T012, T017, T021 | T011 done (different files) |
| W8 | T013, T015 | T012 / T011+T014 done |
| W9 | T016, T022 | T015 / T013+T020 done |
| W10 | T023 | T022 failing-red |
| W11 | T024 | T023 done |
| W12 | T025 | T024 done |
| W13 | T027 | T025 + T026 done |
| W14 | T028 | T027 failing-red |
| W15 | T029, T030 | T028 (+T016/T017/T021/T024) done |
| W16 | T031 | everything else done |

Critical path (longest chain, 14 tasks):
`T001 -> T003 -> T007 -> T008 -> T009 -> T010 -> T011 -> T012 -> T013 -> T022 -> T023 -> T024 -> T025 -> T027 -> T028 -> T031`.
Widest safe fan-out is Wave 4 (five tasks). MVP exit (US2+US1 complete) is reached at
the end of Wave 9 (T016) without entering US5/US3 waves.
