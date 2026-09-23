"""Severity-posture fixtures for rules that had none (audit follow-up).

Each recipe forces ONE registered rule to emit a finding over a throwaway
synthetic repo, so its severity class is pinned in the golden record instead
of the ``<no-finding>`` marker. Kept in its own module so ``severity_posture``
stays under the size limit. Content is generic (no example-domain names), and
every recipe was verified by observing the rule fire.
"""

from __future__ import annotations

# Rules that fire on an EMPTY synthetic repo: each reports its own absent input
# (a missing manifest/registry) as a finding, so the empty recipe IS the forcing
# fixture. Named explicitly so the "every rule is fixtured or allowlisted"
# posture test can tell them apart from a rule nobody wrote a fixture for.
_EMPTY_REPO_FIRES = ("A3", "AP1", "AQ1", "DF1", "DR1", "KR1", "SC1", "SC2")

EXTRA_FIXTURE_FILES: dict[str, tuple[tuple[str, str], ...]] = {
    **{rule_id: () for rule_id in _EMPTY_REPO_FIRES},
    "AD1": (
        (
            "skills/retail-kpi-knowledge/contracts/MarginRate.md",
            (
                "# MarginRate -- Metric Contract\n"
                "\n"
                "**Additivity**\n"
                "Non-additive ratio; recompute at each grain, never sum.\n"
            ),
        ),
        (
            "skills/retail-kpi-knowledge/contracts/BadTotalMarginRate.md",
            (
                "# BadTotalMarginRate -- Metric Contract\n"
                "\n"
                "**Derives from**\n"
                "BadTotalMarginRate = sum of MarginRate across branches.\n"
                "\n"
                "**Additivity**\n"
                "Fully additive across all dimensions.\n"
            ),
        ),
    ),
    "AL2": (
        (
            "mappings/t/metrics/A.yaml",
            (
                "name: A\n"
                "binds_to:\n"
                "  gold_table: gold.fct_generic\n"
                "ambiguities:\n"
                "  - id: A3\n"
                "    decision_status: decided\n"
                '    ruling: "tax excluded"\n'
            ),
        ),
        (
            "mappings/t/metrics/B.yaml",
            (
                "name: B\n"
                "binds_to:\n"
                "  gold_table: gold.fct_generic\n"
                "ambiguities:\n"
                "  - id: A3\n"
                "    decision_status: decided\n"
                '    ruling: "tax included"\n'
            ),
        ),
    ),
    "B3": (
        (
            "src/seshat/validate.py",
            ("import psycopg2\n\n\ndef run():\n    pass\n"),
        ),
    ),
    "CB1": (
        (
            "skills/retail-kpi-knowledge/contracts/SilentGrowth.md",
            (
                "# Net Sales Growth % -- Metric Contract\n"
                "\n"
                "**Business definition**\n"
                "Some definition.\n"
                "\n"
                "**Required fields**\n"
                "- Net Sales\n"
                "- sale date key\n"
                "\n"
                "**Interpretation**\n"
                "The headline growth KPI.\n"
            ),
        ),
    ),
    "CT2": (
        (
            "design/tokens/demo-design-tokens.yaml",
            (
                "meta:\n"
                '  name: "t"\n'
                "colors:\n"
                "  data_colors:\n"
                '    - "#336699"\n'
                '    - "#346699"\n'
                "accessibility:\n"
                "  min_adjacent_delta_e: 10.0\n"
            ),
        ),
    ),
    "CT3": (
        (
            "design/tokens/demo-design-tokens.yaml",
            (
                "colors:\n"
                "  data_colors:\n"
                "    - '#2FB6C4'\n"
                "    - '#2FB6C5'\n"
                "    - '#12263A'\n"
                "accessibility:\n"
                "  min_categorical_deltae: 10.0\n"
            ),
        ),
    ),
    "DL10": (
        (
            "design/grids/16x9-grid.yaml",
            (
                "grid_profiles:\n"
                "  desktop:\n"
                "    zones:\n"
                "      header: {}\n"
                "      kpi_strip: {}\n"
                "      main_insight: {}\n"
                "      diagnostic: {}\n"
                "      exception_detail: {}\n"
                "      filter_rail: {}\n"
                "      footer_status: {}\n"
            ),
        ),
        (
            "reports/blueprints/p.yaml",
            ("visuals:\n  - id: v1\n    section: not_a_zone\n"),
        ),
    ),
    "DL11": (
        (
            "design/tokens/demo.yaml",
            "grid_ref: design/grids/does-not-exist.yaml\n",
        ),
    ),
    "DL6": (
        (
            "visuals/exec_kpi_sales.yaml",
            (
                "anti_pattern_checks:\n"
                "  uses_metric_without_contract: true\n"
                "readiness:\n"
                "  blocking_reasons: []\n"
            ),
        ),
    ),
    "DL7": (
        (
            "demo-formatting-plan.md",
            (
                "# fixture\n"
                "\n"
                "| target | container | group | property | value | principle_"
                "cited | token_cited | apply_verb | status | rationale |\n"
                "|---|---|---|---|---|---|---|---|---|---|\n"
                "| page:x | objects | labels | show | true |  | number_format"
                ".integer | B | proposed | needs a principle |\n"
                "\n"
                "## Ratification\n"
                "\n"
                "- ratification.ratified_by:\n"
            ),
        ),
    ),
    "DL9": (
        (
            "warehouse/design/report-intent.yaml",
            (
                'report_id: "demo_report"\n'
                'subject_area: "mappings/demo"\n'
                'audience: "demo_manager"\n'
                'purpose: "vibes"\n'
                'supported_decision: "which things need attention this week"\n'
                'review_cadence: "weekly"\n'
                "business_questions:\n"
                '  - question_id: "q1"\n'
                '    text: "Which things are underperforming this period?"\n'
                "outcome_metrics: []\n"
                "driver_metrics: []\n"
                "guardrail_metrics: []\n"
                'owner: "A. Owner (report_owner)"\n'
                "readiness:\n"
                '  status: "not_started"\n'
                "  evidence: []\n"
                "  blocking_reasons: []\n"
                "open_questions: []\n"
            ),
        ),
    ),
    "HR1": (
        (
            "mappings/s1/source-map.yaml",
            (
                "source_id: s1\n"
                "gold_star:\n"
                "  fact: fct_a\n"
                "  dimensions:\n"
                "    - name: dim_thing\n"
            ),
        ),
        (
            "mappings/s2/source-map.yaml",
            (
                "source_id: s2\n"
                "gold_star:\n"
                "  fact: fct_b\n"
                "  dimensions:\n"
                "    - name: dim_thing\n"
            ),
        ),
    ),
    "HR11": (
        (
            "mappings/t1/source-map.yaml",
            (
                "columns:\n"
                "  - source_name: SRC_A\n"
                "    rename_to: col_a\n"
                "    unit: kg\n"
                "    currency: null\n"
                "  - source_name: SRC_B\n"
                "    rename_to: col_b\n"
                "    unit: each\n"
                "    currency: null\n"
            ),
        ),
        (
            "mappings/t1/metrics/TotalQty.yaml",
            ("name: TotalQty\nbinds_to:\n  columns:\n    - col_a\n    - col_b\n"),
        ),
    ),
    "HR12": (
        (
            "mappings/t1/source-data-contract.yaml",
            (
                "arrival:\n"
                "  cadence: daily by 6am\n"
                "restatement:\n"
                "  policy: never resends; append-only upstream\n"
            ),
        ),
    ),
    "HR13": (
        (
            "mappings/s1/source-map.yaml",
            (
                "source_id: s1\n"
                "columns:\n"
                "  - source_name: item\n"
                "    silver_type: text\n"
                '    gold_placement: "dim:dim_product.item"\n'
                "gold_star:\n"
                "  fact: fct_a\n"
                "  dimensions:\n"
                '    - name: "gold.dim_product_rss"\n'
                "      surrogate_key: product_sk\n"
            ),
        ),
    ),
    "HR4": (
        (
            "mappings/widgets/source-map.yaml",
            (
                "meta:\n"
                '  table_id: "widgets"\n'
                '  grain: "one row = one thing"\n'
                "  primary_key:\n"
                '    - "id"\n'
                '  reviewed_by: "data_owner"\n'
                "  freshness:\n"
                '    expected_cadence: "biweekly"\n'
                '    max_staleness: "some time"\n'
            ),
        ),
    ),
    "HR5": (
        (
            "mappings/demo/metrics/DemoMetric.yaml",
            (
                "name: DemoMetric\n"
                "binds_to:\n"
                '  gold_table: "gold.fct_demo"\n'
                "  columns:\n"
                '    - "qty_on_hand"\n'
                'ambiguities: [{id: "A10", decision_status: "undecided", ruli'
                'ng: "", evidence: [], number_moving: true}]\n'
            ),
        ),
    ),
    "HR6": (
        (
            "warehouse/migrations/0001_gold.sql",
            (
                "CREATE SCHEMA IF NOT EXISTS gold;\n"
                "CREATE TABLE gold.dim_thing (\n"
                "  thing_sk INT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,"
                "\n"
                "  thing_id TEXT,\n"
                "  grp TEXT,\n"
                "  CONSTRAINT thing_uq UNIQUE (thing_id)\n"
                ");\n"
                "CREATE TABLE gold.fct_thing (\n"
                "  fact_sk INT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,\n"
                "  thing_sk INT,\n"
                "  amount NUMERIC(10,2)\n"
                ");\n"
            ),
        ),
        (
            "mappings/demo/roles/DemoRole.yaml",
            (
                "name: DemoRole\n"
                "filter:\n"
                "  gold_table: gold.fct_thing\n"
                "  column: thing_sk\n"
                "readiness:\n"
                "  status: not_started\n"
                "  evidence: []\n"
                "  blocking_reasons: []\n"
            ),
        ),
    ),
    "HR7": (
        (
            "warehouse/migrations/0103_gold.sql",
            (
                "CREATE SCHEMA IF NOT EXISTS gold;\n"
                "INSERT INTO gold.fct_thing SELECT * FROM silver.thing;\n"
            ),
        ),
    ),
    "HR8": (
        (
            "warehouse/migrations/0200_gold.sql",
            (
                "CREATE SCHEMA IF NOT EXISTS gold;\n"
                "CREATE TABLE gold.dim_date (date_sk INT, full_date DATE);\n"
                "INSERT INTO gold.dim_date\n"
                "SELECT (to_char(d,'YYYYMMDD'))::int, d::date\n"
                "FROM generate_series(DATE '2022-01-01', DATE '2025-01-18', I"
                "NTERVAL '1 month') AS g(d);\n"
            ),
        ),
    ),
    "HR9": (
        (
            "powerbi/M.SemanticModel/definition/tables/fct.tmdl",
            ("table 'gold fct'\n\tcolumn amount\n\t\tdataType: double\n"),
        ),
        (
            "mappings/t1/metrics/Amount.yaml",
            (
                "binds_to:\n"
                "  gold_table: gold.fct\n"
                "  columns:\n"
                "    - amount\n"
                "    - missing_col\n"
            ),
        ),
    ),
    "KP1": (
        (
            "mappings/orders/metrics/Total.yaml",
            (
                "generic_kpi_ref: KPI-MC-02\n"
                "custom: false\n"
                "decision_refs:\n"
                "  - kpi_definition.total\n"
                "source_evidence:\n"
                "  - mappings/orders/metrics/Total.yaml\n"
            ),
        ),
    ),
    "PP1": (
        (
            "mappings/t1/handoff/bi-handoff-pack.md",
            (
                "# BI Handoff Pack\n"
                "\n"
                "## Required-section index\n"
                "\n"
                "| # | Section | Points at | Resolved? |\n"
                "|---|---------|-----------|-----------|\n"
            ),
        ),
    ),
    "R2": (
        (
            "powerbi/M.Report/definition/report.json",
            "{}\n",
        ),
    ),
    "S9": (
        (
            "warehouse/a.sql",
            (
                "SELECT NULLIF(trim(c), '') AS c FROM bronze.t WHERE c NOT IN"
                " ('x', '');\n"
            ),
        ),
    ),
}
