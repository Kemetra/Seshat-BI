"""Severity-posture observation harness + golden-record generator (feature 044).

Severity is NOT a property of a registered rule: the registry entry carries an
id and a title and no severity field, and a single rule id can emit findings in
more than one severity class depending on which violation branch fires (the
shipped SQL guard-form rule ``S4b`` emits both ERROR and WARNING). Therefore the
golden record CANNOT be read from the registry as a flat id->class map -- it is
OBSERVED by forcing each rule to fire over planted, synthetic, minimal input and
recording the set of severity classes it emits.

Record GRAIN (FR-009, advisor-resolved option (a)):
    ``rule_id -> the SORTED SET of severity classes that rule emits when forced``
A multi-class rule records the FULL set (e.g. ``["error", "warning"]``); it is
NEVER collapsed to one class. A rule that genuinely cannot be forced to fire over
a minimal synthetic fixture records an EXPLICIT no-finding marker (FR-011), never
a silent omission.

Record COVERAGE (FR-010, advisor-resolved): TWO explicitly-named sections --
  * ``registered``: one entry per registry-reachable rule (``all_rules()``);
  * ``L3:verdict_to_finding``: the non-registered L3 governance surface
    (``semantic.verdict_to_finding``: drift -> ERROR / escalate -> WARNING),
    observed in-process by driving a frozen ``Verdict`` value -- no YAML/DB/model/
    agent, so the static-first invariant (Principle VIII) holds. The L3 entry adds
    NO ``@register`` and NO new expected-rule-id (ADR-0007); the registry-reachable
    rule count is unchanged.

Deterministic serialization contract (Principle IX -- cross-platform stable):
  * the top-level object has exactly two keys: ``registered`` and ``l3``;
  * ``registered`` maps each ``rule_id`` to its severity entry; ``l3`` maps the
    single key ``L3:verdict_to_finding`` to its severity entry;
  * each severity entry is the SORTED list of severity string values
    (``"error"`` < ``"info"`` < ``"warning"`` by string value), or the explicit
    no-finding marker list ``["<no-finding>"]`` (FR-011);
  * ``json.dumps(indent=2, sort_keys=True, ensure_ascii=True)`` so key order is
    stable regardless of insertion order; a single trailing ``\\n``; UTF-8 without
    BOM; ``newline="\\n"`` on write keeps the bytes identical on Windows under
    ``core.autocrlf=true``.

This module adds NO new registered rule and NO new ``EXPECTED_RULE_ID``: it is a
generator + a test-only golden assertion, never a ``retail check`` rule.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import subprocess
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .core import Finding, RegisteredRule, Rule, RuleContext, Severity

# repo-relative location of the committed golden record (sibling of the manifest).
RECORD_REL_PATH = "docs/rules/severity-posture.json"

# The explicit marker for a rule that cannot be forced to emit a finding (FR-011).
NO_FINDING_MARKER = "<no-finding>"

# The named L3 governance-surface pseudo-rule key (FR-010).
L3_KEY = "L3:verdict_to_finding"


def _live_rules() -> tuple[RegisteredRule, ...]:
    """Return the live registered rules from a clean clear+reload of the registry.

    Mirrors the proven idiom in ``test_rules_manifest_snapshot.py``: a plain
    ``import_module`` is a no-op for an already-imported module, so the
    ``@register`` decorators would NOT re-fire after a clear -- each submodule must
    be ``importlib.reload``-ed. This is order-proof and does not depend on global
    registry state left by sibling tests.
    """
    import seshat.rules as rules_pkg
    from seshat import registry

    registry._RULES.clear()
    for info in pkgutil.iter_modules(rules_pkg.__path__):
        importlib.reload(importlib.import_module(f"seshat.rules.{info.name}"))
    rules = registry.all_rules()
    assert rules, "no rules registered -- seshat.rules submodules failed to reload"
    return rules


# ---------------------------------------------------------------------------
# Synthetic-fixture planting.
#
# Rules read content from ``ctx.repo_root / rel`` and only ever consider paths in
# ``ctx.tracked_files``. ``is_test_path`` exempts anything under ``tests/`` from
# the file-scanning rules, so to FORCE a rule to fire we materialize a throwaway
# synthetic repo in a tempdir (rooted OUTSIDE tests/) and name the planted files
# at NON-exempt paths (``warehouse/...``, ``powerbi/...``). The fixture CONTENT is
# generic (no example-domain table/column/value); the committed fixture files
# under tests/fixtures/severity/ carry the same generic content and are scanned by
# the lock test for genericity (they are is_test_path-exempt from the live rules,
# so the lock test is the only thing that checks them -- SC-007).
# ---------------------------------------------------------------------------

# Generic synthetic content building blocks. NO example-domain identifiers.
_SQL_S1 = 'SELECT 1 AS "BadIdent" FROM gold.thing;\n'
_SQL_S2 = "SELECT col_a FROM raw.thing;\n"
_SQL_S3 = "CREATE VIEW gold.plain_name AS SELECT 1;\n"
_SQL_S4A_BADNAME = "SELECT 1;\n"  # planted at warehouse/migrations/bad_name.sql
# S4b multi-class: a bronze bare CREATE (ERROR) AND a gold bare CREATE not in a
# transaction (WARNING) in one file -> the rule emits BOTH classes.
_SQL_S4B = "CREATE TABLE bronze.thing (id text);\nCREATE TABLE gold.thing (id text);\n"
_SQL_S5 = "SELECT amount_val::float8 FROM gold.thing;\n"
_SQL_S6 = "CREATE TABLE gold.dim_thing (thing_sk integer);\n"
_SQL_S7 = (
    "INSERT INTO gold.dim_date (day_key)\nSELECT DISTINCT day_key FROM gold.thing;\n"
)
_SQL_S8 = "INSERT INTO gold.dim_date (day_key) VALUES (-1);\n"

# A TMDL table file with one offending measure/column per D-rule, planted under a
# *.SemanticModel/definition/ path so iter_model_files / iter_m_sources pick it up.
_TMDL_D1 = "table T\n\tmeasure badName = 1\n\t\tdisplayFolder: F\n"
_TMDL_D2 = "table T\n\tmeasure Good = 1\n"  # no displayFolder -> D2 ERROR
_TMDL_D3 = (
    "table T\n"
    "\tmeasure OneA = SUM(T[c])\n"
    "\t\tdisplayFolder: F\n"
    "\tmeasure OneB = SUM(T[c])\n"
    "\t\tdisplayFolder: F\n"
)
_TMDL_D4 = "table T\n\tmeasure Ratio = 1 / 2\n\t\tdisplayFolder: F\n"
_TMDL_D5 = "table T\n\tcolumn val\n\t\tdataType: int64\n\t\tsummarizeBy: sum\n"
_TMDL_D6 = "table T\nrelationship rel\n\tcrossFilteringBehavior: bothDirections\n"
_TMDL_D7 = (
    "table T\n"
    "\tmeasure Ti = TOTALYTD(SUM(T[c]), T[d])\n"
    "\t\tdisplayFolder: F\n"
)  # TI use, no date-table marker -> D7 ERROR
_TMDL_D8 = (
    "table T\n"
    "\tpartition p = m\n"
    '\t\tsource = let s = Sql.Database(Server, Db), q = s{[Schema="bronze"]} in q\n'
)
_TMDL_D9 = (
    "table T\n"
    "\tmeasure Dt = IF(TODAY() > DATE(2020, 1, 1), 1, 0)\n"
    "\t\tdisplayFolder: F\n"
)
_TMDL_D10 = (
    "table T\n"
    "\tmeasure Fa = CALCULATE(SUM(T[c]), FILTER(ALL(T), T[c] > 0))\n"
    "\t\tdisplayFolder: F\n"
)
_TMDL_D11 = (
    "table T\n"
    "\tmeasure Undoc = 1\n"
    "\t\tdisplayFolder: F\n"
)  # no /// doc comment -> D11 WARNING
_TMDL_C1 = (
    "table T\n"
    "\tpartition p = m\n"
    '\t\tsource = let s = Sql.Database("a_host", "a_db") in s\n'
)

# A module-scope forbidden import in a governed rules-package path -> B1 ERROR.
_PY_B1 = "import socket\n\n\ndef f():\n    return 1\n"

# A PBIR with byConnection -> R1 ERROR.
_PBIR_R1 = '{"datasetReference": {"byConnection": {"connectionString": "x"}}}\n'

# An expressions.tmdl with a real (non-placeholder) parameter value -> G6 ERROR.
_EXPR_G6 = 'expression Server = "a-real-host" meta [IsParameterQuery=true]\n'

# A UTF-8 BOM-prefixed json file -> G3 ERROR.
_JSON_G3 = "﻿{}\n"

# A readiness-status.yaml whose current_stage is ahead of a not_started gate -> RS1.
_YAML_RS1 = (
    'table: "bronze.demo"\n'
    'current_stage: "mapping_ready"\n'
    "stages:\n"
    "  source_ready:\n"
    '    status: "pass"\n'
    "    evidence: []\n"
    "    blocking_reasons: []\n"
    "  mapping_ready:\n"
    '    status: "not_started"\n'
    "    evidence: []\n"
    "    blocking_reasons: []\n"
)

# A filled per-table scorecard with a status outside the enum -> SL1 ERROR.
_MD_SL1 = (
    "# Coverage scorecard\n\n"
    "> Table: `schema.demo` -- generic grain\n\n"
    "| KPI | Contract | Coverage status | Blocker |\n"
    "|-----|----------|-----------------|---------|\n"
    "| Demo KPI | -- | Sorta covered | -- |\n"
)

# A metric contract with an unresolved assumption (blocked + reasons) AND a settled
# gold binding -> AL1 fails loud (ERROR).
_YAML_AL1 = (
    "name: DemoMetric\n"
    "binds_to:\n"
    '  gold_table: "gold.fct_demo"\n'
    "  columns:\n"
    '    - "net_amount"\n'
    "readiness:\n"
    '  status: "blocked"\n'
    '  blocking_reasons: ["A4 gross/net denominator not ruled"]\n'
)

# A theme carrying a forbidden business-logic key -> DL1 ERRORs.
_JSON_DL1 = '{"measure": "bad"}\n'

# A background spec with a forbidden_dynamic_content key set true -> DL2 ERRORs.
_YAML_DL2 = "forbidden_dynamic_content:\n  kpi_value: true\n"

# tokens declare data_colors but the theme drifts -> DL3 ERRORs.
_YAML_DL3_TOKENS = (
    "meta: { compiles_to: demo.theme.json }\ncolors:\n  data_colors:\n    - '#111111'\n"
)
_JSON_DL3_THEME = '{"dataColors": ["#999999"]}\n'

# tokens declare a sentiment_map but the theme drifts on it -> DL8 ERRORs.
_YAML_DL8_TOKENS = (
    "meta: { compiles_to: demo.theme.json, sentiment_map: { success: good } }\n"
    "colors:\n  sentiment:\n    success: '#2E7D5B'\n"
)
_JSON_DL8_THEME = '{"good": "#000000"}\n'

# A design-review evidence record missing a required field -> DL4 ERRORs.
_MD_DL4 = "## Record\n\n- **page_id:** `p01`\n"

# A layout grid whose column arithmetic does NOT close -> DL5 ERRORs.
# usable width = 200 - 10 - 10 = 180, but 4*25 + 3*20 = 160 != 180.
_YAML_DL5 = (
    "grid_id: demo\n"
    "profiles:\n"
    '  "p":\n'
    "    canvas: { width: 200, height: 150 }\n"
    "    margin: { top: 10, right: 10, bottom: 10, left: 10 }\n"
    "    grid:\n"
    "      columns: 4\n"
    "      rows: 3\n"
    "      gutter: 20\n"
    "      column_width: 25\n"
    "      row_height: 30\n"
)

# SF1 emits BOTH classes over one synthetic repo (mirrors S4b's multi-class
# fixture): an UNDECLARED same-basename collision -> ERROR, AND a spine entry that
# no longer names a live collision -> WARNING (stale entry). Without this, SF1 is
# only ever reached via the missing-manifest ERROR path and its WARNING branch
# goes unobserved.
_YAML_SF1_SPINE = "checklists:\n  gone.md: shared\n"
_MD_SF1_DUP_A = "content A\n"
_MD_SF1_DUP_B = "content B\n"

# tokens with a text/background pair below the declared floor -> CT1 ERRORs.
_YAML_CT1 = (
    "colors:\n"
    "  background: '#FFFFFF'\n"
    "  text:\n    primary: '#CCCCCC'\n"
    "accessibility:\n  min_text_contrast_ratio: '4.5:1'\n"
)

# data_colors declared without a min_categorical_deltae floor -> CT3 opt-in
# absent -> silent skip, <no-finding> (Principle V: floor key IS the opt-in).
_YAML_CT3 = "colors:\n  data_colors:\n    - '#2FB6C4'\n    - '#12263A'\n"

# A tracked path longer than MAX_REL_PATH -> G5 ERROR. G5 reads ctx.tracked_files
# only (the path string), never disk, so the file is NOT materialized (a >260-char
# path would hit Windows MAX_PATH).
_G5_LONG_REL = "warehouse/" + ("d/" * 100) + "f.sql"

# A trivial always-parseable SQL file, tracked so ls-files based rules see content
# without triggering their own findings (G2 empty-case INFO, P1/A1 missing-path).
_SQL_TRIVIAL = "SELECT 1;\n"

# The shared TMDL table path the D-family and C1 all target.
_TMDL_TABLE_REL = "powerbi/M.SemanticModel/definition/tables/t.tmdl"


def _env_example_text() -> str:
    # A complete .env.example so C2's example-file sub-check is satisfied and the
    # ONLY finding is the tracked-.env ERROR (a focused, single-class observation).
    keys = (
        "ANALYTICS_DB_HOST=",
        "ANALYTICS_DB_PORT=5432",
        "ANALYTICS_DB_NAME=",
        "ANALYTICS_DB_USER=",
        "ANALYTICS_DB_PASSWORD=",
        "ANALYTICS_DB_SSLMODE=require",
    )
    return "\n".join(keys) + "\n"


# A tracked .env (the ".env must never be tracked" ERROR) paired with a complete
# .env.example so C2's example-file sub-check is satisfied -> a single-class ERROR.
_ENV_C2 = "SECRET=1\n"
_ENV_EXAMPLE_C2 = _env_example_text()


def _run(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo: Path) -> None:
    """git-init a throwaway synthetic repo so check-ignore / ls-files behave."""
    _run(repo, "init", "-q")
    _run(repo, "config", "user.email", "t@example.invalid")
    _run(repo, "config", "user.name", "t")


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="" so BOM/CRLF content is written byte-faithfully when a fixture
    # deliberately carries a BOM (G3); otherwise plain text.
    path.write_text(text, encoding="utf-8", newline="")


def _classes(findings: Iterable[Finding]) -> set[str]:
    out: set[str] = set()
    for f in findings:
        assert isinstance(f, Finding)
        assert isinstance(f.severity, Severity)
        out.add(f.severity.value)
    return out


@dataclass(frozen=True)
class _Fixture:
    """The synthetic-repo recipe for forcing ONE rule to fire.

    ``files`` are written to disk in order (each a ``(rel, body)`` pair).
    ``tracked`` is the ``ctx.tracked_files`` list; when left ``None`` it defaults
    to the rels from ``files`` in order (the common case). It is set explicitly
    only where it must diverge from what was written -- G5 tracks an unmaterialized
    over-length path, P2 tracks nothing and drives only ``commit_message``.
    """

    files: tuple[tuple[str, str], ...] = ()
    tracked: tuple[str, ...] | None = None
    commit_message: str | None = None

    def tracked_files(self) -> tuple[str, ...]:
        if self.tracked is not None:
            return self.tracked
        return tuple(rel for rel, _ in self.files)


def _tmdl_fixture(body: str) -> _Fixture:
    """A single-table TMDL fixture at the shared D-family / C1 path."""
    return _Fixture(files=((_TMDL_TABLE_REL, body),))


# rule_id -> the synthetic-repo recipe that forces it to fire. A rule_id absent
# from this table falls through to the default empty fixture -> no-finding marker.
_RULE_FIXTURES: dict[str, _Fixture] = {
    "S1": _Fixture(files=(("warehouse/a.sql", _SQL_S1),)),
    "S2": _Fixture(files=(("warehouse/a.sql", _SQL_S2),)),
    "S3": _Fixture(files=(("warehouse/a.sql", _SQL_S3),)),
    "S4a": _Fixture(files=(("warehouse/migrations/bad_name.sql", _SQL_S4A_BADNAME),)),
    "S4b": _Fixture(files=(("warehouse/a.sql", _SQL_S4B),)),
    "S5": _Fixture(files=(("warehouse/a.sql", _SQL_S5),)),
    "S6": _Fixture(files=(("warehouse/a.sql", _SQL_S6),)),
    "S7": _Fixture(files=(("warehouse/a.sql", _SQL_S7),)),
    "S8": _Fixture(files=(("warehouse/a.sql", _SQL_S8),)),
    "D1": _tmdl_fixture(_TMDL_D1),
    "D2": _tmdl_fixture(_TMDL_D2),
    "D3": _tmdl_fixture(_TMDL_D3),
    "D4": _tmdl_fixture(_TMDL_D4),
    "D5": _tmdl_fixture(_TMDL_D5),
    "D6": _tmdl_fixture(_TMDL_D6),
    "D7": _tmdl_fixture(_TMDL_D7),
    "D8": _tmdl_fixture(_TMDL_D8),
    "D9": _tmdl_fixture(_TMDL_D9),
    "D10": _tmdl_fixture(_TMDL_D10),
    "D11": _tmdl_fixture(_TMDL_D11),
    "C1": _tmdl_fixture(_TMDL_C1),
    "B1": _Fixture(files=(("src/seshat/rules/synthetic_probe.py", _PY_B1),)),
    "R1": _Fixture(files=(("powerbi/M.Report/definition.pbir", _PBIR_R1),)),
    "RS1": _Fixture(files=(("mappings/demo/readiness-status.yaml", _YAML_RS1),)),
    # a real (non-placeholder) parameter value -> G6 ERROR.
    "G6": _Fixture(
        files=(("powerbi/M.SemanticModel/definition/expressions.tmdl", _EXPR_G6),)
    ),
    # a UTF-8 BOM-prefixed json file -> G3 ERROR.
    "G3": _Fixture(
        files=(("powerbi/M.SemanticModel/definition/model.json", _JSON_G3),)
    ),
    # a tracked over-length path (NOT materialized) -> G5 ERROR.
    "G5": _Fixture(tracked=(_G5_LONG_REL,)),
    # an empty .gitattributes -> every required glob missing -> ERROR.
    "G4": _Fixture(files=((".gitattributes", "# empty\n"),)),
    # an empty .gitignore -> required ignores missing -> ERROR.
    "G1": _Fixture(files=((".gitignore", "\n"),)),
    # no PBIP-signature tracked file -> the INFO empty-case branch fires.
    "G2": _Fixture(files=(("warehouse/a.sql", _SQL_TRIVIAL),)),
    # a tracked .env -> the ".env must never be tracked" ERROR branch.
    "C2": _Fixture(files=((".env", _ENV_C2), (".env.example", _ENV_EXAMPLE_C2))),
    # no required layout paths tracked -> missing-path ERROR.
    "P1": _Fixture(files=(("warehouse/a.sql", _SQL_TRIVIAL),)),
    # a non-conforming commit subject supplied via the contract field.
    "P2": _Fixture(commit_message="not a conventional subject"),
    # the routes manifest is absent/untracked -> A1 fails loud (ERROR).
    "A1": _Fixture(files=(("warehouse/a.sql", _SQL_TRIVIAL),)),
    "SL1": _Fixture(files=(("mappings/demo/demo-coverage-scorecard.md", _MD_SL1),)),
    "AL1": _Fixture(files=(("mappings/demo/metrics/DemoMetric.yaml", _YAML_AL1),)),
    "DL1": _Fixture(files=(("demo.theme.json", _JSON_DL1),)),
    "DL2": _Fixture(
        files=(("mappings/demo/background/page.background.yaml", _YAML_DL2),)
    ),
    "DL3": _Fixture(
        files=(
            ("design/tokens/demo-design-tokens.yaml", _YAML_DL3_TOKENS),
            ("demo.theme.json", _JSON_DL3_THEME),
        )
    ),
    "DL8": _Fixture(
        files=(
            ("design/tokens/demo-design-tokens.yaml", _YAML_DL8_TOKENS),
            ("demo.theme.json", _JSON_DL8_THEME),
        )
    ),
    "DL4": _Fixture(files=(("reports/demo/design-review-evidence.md", _MD_DL4),)),
    "DL5": _Fixture(files=(("design/grids/demo-grid.yaml", _YAML_DL5),)),
    "SF1": _Fixture(
        files=(
            ("docs/quality/shared-spine.yaml", _YAML_SF1_SPINE),
            ("skills/pack-a/checklists/dup.md", _MD_SF1_DUP_A),
            ("skills/pack-b/checklists/dup.md", _MD_SF1_DUP_B),
        )
    ),
    "CT1": _Fixture(files=(("design/tokens/demo-design-tokens.yaml", _YAML_CT1),)),
    "CT2": _Fixture(),
    "CT3": _Fixture(files=(("design/tokens/demo-design-tokens.yaml", _YAML_CT3),)),
}


def _git_add_best_effort(repo: Path, tracked: Iterable[str]) -> None:
    """git-add each tracked rel so check-ignore / ls-files based rules see it.

    Best-effort: a path git refuses to add (e.g. the deliberately over-length G5
    path on Windows MAX_PATH) is skipped -- G5 reads ``ctx.tracked_files`` only and
    never touches git.
    """
    for rel in tracked:
        try:
            _run(repo, "add", "--force", rel)
        except subprocess.CalledProcessError:
            pass


def _observe_rule(rule_id: str, fn: Rule) -> set[str]:
    """Force one registered rule to fire over a minimal synthetic repo.

    Returns the SET of severity class string values the rule emits. An empty set
    means the rule could not be forced to fire (caller records the marker).
    """
    fixture = _RULE_FIXTURES.get(rule_id, _Fixture())
    tracked = fixture.tracked_files()
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        for rel, body in fixture.files:
            _write(repo, rel, body)

        _init_repo(repo)
        _git_add_best_effort(repo, tracked)

        ctx = RuleContext(
            repo_root=repo,
            tracked_files=tracked,
            commit_range=None,
            commit_message=fixture.commit_message,
        )
        return _classes(fn(ctx))


def _observe_l3() -> set[str]:
    """Observe the L3 governance surface in-process (no YAML/DB/model/agent).

    Drives ``semantic.verdict_to_finding`` with a ``drift`` verdict (-> ERROR) and
    an ``escalate`` verdict (-> WARNING), both constructed as frozen
    ``metric_drift.Verdict`` values, and returns the observed severity-class set.
    """
    from .metric_drift import Verdict
    from .semantic import verdict_to_finding

    out: set[str] = set()
    for status in ("drift", "escalate"):
        verdict = Verdict(status=status, detail="synthetic")
        finding = verdict_to_finding("Measure", "x:1", verdict)
        assert finding is not None, f"L3 status {status!r} produced no finding"
        assert isinstance(finding.severity, Severity)
        out.add(finding.severity.value)
    return out


def _entry(classes: set[str]) -> list[str]:
    """A record entry: the sorted class list, or the explicit no-finding marker."""
    if not classes:
        return [NO_FINDING_MARKER]
    return sorted(classes)


def build() -> dict:
    """Return the ordered observed-posture data for the CURRENT live registry.

    Generated from live observation, never a hand-typed literal. The two named
    sections are ``registered`` (one entry per rule) and ``l3`` (the single
    ``L3:verdict_to_finding`` pseudo-rule).
    """
    registered: dict[str, list[str]] = {}
    for r in sorted(_live_rules(), key=lambda r: r.id):
        registered[r.id] = _entry(_observe_rule(r.id, r.rule))
    return {
        "registered": registered,
        "l3": {L3_KEY: _entry(_observe_l3())},
    }


def serialize(data: dict) -> str:
    """Serialize record data to the stable JSON text form (Principle IX)."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def render() -> str:
    """Render the record text for the CURRENT live registry + L3 surface."""
    return serialize(build())


def write(repo_root: Path | str = ".") -> Path:
    """Write the record to ``<repo_root>/docs/rules/severity-posture.json``.

    UTF-8 without BOM and ``\\n`` line endings (``newline="\\n"`` keeps the bytes
    identical on Windows under ``core.autocrlf=true``). Returns the path.
    """
    path = Path(repo_root) / RECORD_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(), encoding="utf-8", newline="\n")
    return path
